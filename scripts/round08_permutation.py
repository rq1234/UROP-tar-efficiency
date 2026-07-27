"""
round08_permutation.py - Round 8 Y2: circular-shift permutation test.

Rebuilds `permutation_exp.csv`.

This is the strongest evidence in the paper for the explosive discount, and the
one that does NOT rely on the 30-episodes-independent assumption.

Spec, from results/exports/README.md Round 8 Y2:

  "episode-mean-excess p = 0.0000 (i.e. 0 of 5000 circular-shift nulls were as
   negative as the observed -15.04pp; observed sits at the 0th percentile, null
   mean +0.05pp, sd 3.99). Pooled EXP-RW gap -15.49pp: same, 0/5000, p=0.0000.
   Randomly re-timing each market's explosive spells (preserving spell count,
   length, and every return-autocorrelation feature) DESTROYS the discount - so
   the result is carried by the ALIGNMENT of the labels with forward returns,
   not by cross-market correlation or independence assumptions.
   Seed=20260722, B=5000."

DESIGN
------
The null re-times the labels, not the returns. For each market the state
sequence is rotated by a random offset (a circular shift), which preserves
exactly: the number of EXP spells, each spell's length, the total EXP months,
and every autocorrelation property of the return series - because the returns
are never touched. Only the alignment between labels and forward returns is
broken.

Two statistics, both recomputed under every shift:
  episode_mean_excess_pp  mean over EXP episodes of (episode 12m forward return
                          minus that market's own RW baseline)
  pooled_EXP_RW_gap_pp    pooled 12m mean over EXP months minus pooled RW mean

Japan is excluded from the EXP side throughout (config.EXCLUDED_EXP_MARKETS).

Usage:  python scripts/round08_permutation.py [--B 5000]
"""

import argparse
import csv
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def spells(mask):
    """Contiguous runs of True as (start, length) pairs."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j - i + 1))
            i = j + 1
        else:
            i += 1
    return out


def build():
    """Per-market states and 12m forward returns, aligned."""
    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    data = {}
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        state = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))
        logp = y[1:]                       # price level aligned with state
        h = 12
        fwd = np.full(len(state), np.nan)
        fwd[:-h] = 100.0 * (logp[h:] - logp[:-h])
        data[mkt] = {"state": state, "fwd": fwd}
    return data


def statistics(data, shifts=None):
    """Both statistics, optionally under a per-market circular shift of the labels."""
    ep_excess, exp_pool, rw_pool = [], [], []
    for mkt, d in data.items():
        st = d["state"]
        if shifts is not None:
            st = np.roll(st, shifts[mkt])
        fwd = d["fwd"]
        ok = ~np.isnan(fwd)

        rw_sel = ok & (st == 0)
        if not rw_sel.any():
            continue
        rw_base = float(fwd[rw_sel].mean())
        rw_pool.append(fwd[rw_sel])

        if mkt in config.EXCLUDED_EXP_MARKETS:
            continue                        # Japan: excluded from the EXP side
        exp_mask = st == 2
        sel = ok & exp_mask
        if sel.any():
            exp_pool.append(fwd[sel])
        for s, L in spells(exp_mask):
            seg = fwd[s:s + L]
            seg = seg[~np.isnan(seg)]
            if seg.size:
                ep_excess.append(float(seg.mean()) - rw_base)

    if not ep_excess or not exp_pool or not rw_pool:
        return np.nan, np.nan, 0
    gap = float(np.concatenate(exp_pool).mean()) - float(np.concatenate(rw_pool).mean())
    return float(np.mean(ep_excess)), gap, len(ep_excess)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=config.B_PERMUTATION)
    args = ap.parse_args()

    print(f"Round 8 Y2 circular-shift permutation | B={args.B} | "
          f"seed={config.SEED_ROUND_8_10}\n")
    data = build()
    obs_ep, obs_gap, n_ep = statistics(data)
    print(f"  observed episode mean excess : {obs_ep:+.3f} pp  over {n_ep} episodes")
    print(f"  observed pooled EXP-RW gap   : {obs_gap:+.3f} pp\n")

    rng = np.random.default_rng(config.SEED_ROUND_8_10)
    markets = list(data)
    lengths = {m: len(data[m]["state"]) for m in markets}

    null_ep, null_gap, t0 = [], [], time.time()
    for b in range(args.B):
        shifts = {m: int(rng.integers(0, lengths[m])) for m in markets}
        e, g, _ = statistics(data, shifts)
        if not np.isnan(e):
            null_ep.append(e)
            null_gap.append(g)
        if (b + 1) % 1000 == 0:
            print(f"    {b + 1}/{args.B} draws  ({time.time() - t0:.0f}s)")

    rows = []
    for name, obs, arr in (("episode_mean_excess_pp", obs_ep, null_ep),
                           ("pooled_EXP_RW_gap_pp", obs_gap, null_gap)):
        a = np.asarray(arr, dtype=float)
        p_le = float(np.mean(a <= obs))
        rows.append({
            "statistic": name,
            "observed": round(obs, 3),
            "n_obs_episodes": float(n_ep) if name.startswith("episode") else "",
            "null_mean": round(float(a.mean()), 3),
            "null_sd": round(float(a.std(ddof=1)), 3),
            "null_p05": round(float(np.percentile(a, 5)), 3),
            "null_p50": round(float(np.percentile(a, 50)), 3),
            "perm_p_le_obs": round(p_le, 4),
            "observed_percentile": round(float(100.0 * np.mean(a < obs)), 1),
            "B": args.B, "seed": config.SEED_ROUND_8_10,
        })
        n_as_extreme = int(np.sum(a <= obs))
        print(f"\n  {name}")
        print(f"    observed {obs:+.3f}   null mean {a.mean():+.3f} sd {a.std(ddof=1):.3f}")
        print(f"    {n_as_extreme} of {len(a)} null draws are as negative as observed "
              f"-> p = {p_le:.4f}")

    out = os.path.join(config.ensure_rebuilt_dir(), "permutation_exp.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  -> permutation_exp.csv ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
