"""
rank_stability_permutation.py - Round 8, all of Y1-Y4.

Rebuilds `rank_stability_drift.csv` (Y1, and Y4's extra columns) and
`permutation_exp.csv` (Y2). Y3 has no CSV target of its own - it is a
cross-check against horserace_label_vs_trailing.csv (Round 7 X3), printed
here if that file has already been built.

Spec, from results/exports/README.md Round 8:

  Y1 (rank stability, no-drift, spec=0) - DOES NOT support the intended
   defense: "ranking NOT robust: Spearman 0.050; top-8 preserved 2/8;
   bottom-8 preserved 3/8." The no-drift optimiser places DEGENERATE
   thresholds (c2 < 100, the CCI mean) for several markets - the
   reshuffling reflects the pathology of the no-drift model, not a
   credible alternative ordering.
  Y4 (fair comparison, constant-drift, spec=2) - still not robust:
   Spearman 0.417 (p=0.048), mean RW-share change 9.1pp; top-8 preserved
   4/8, bottom-8 5/8. Constant-drift is not degenerate (c2<100 for only 1
   market vs 5 under no-drift) so this is the fair A&S comparison.
  Y2 (circular-shift permutation) - STRONG win, unchanged from before:

  "episode-mean-excess p = 0.0000 (i.e. 0 of 5000 circular-shift nulls were as
   negative as the observed -15.04pp; observed sits at the 0th percentile, null
   mean +0.05pp, sd 3.99). Pooled EXP-RW gap -15.49pp: same, 0/5000, p=0.0000.
   Randomly re-timing each market's explosive spells (preserving spell count,
   length, and every return-autocorrelation feature) DESTROYS the discount - so
   the result is carried by the ALIGNMENT of the labels with forward returns,
   not by cross-market correlation or independence assumptions.
   Seed=20260722, B=5000."
  Y3 (MR horse-race, symmetry with X3) - confirmed: MR coef +3.31 (p=0.42)
   without trailing return -> +2.66 (p=0.45) with trailing; both
   insignificant under DK. Same numbers as X3's a_regime_only/c_both MR
   rows (dependence_corrections.py) - not re-estimated here.

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

Usage:  python scripts/rank_stability_permutation.py [--B 5000]
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


def y1_y4_rank_stability():
    """Re-estimate all 23 markets under spec=0 (no-drift) and spec=2
    (constant-drift); rank by RW share and compare to the spec=1 baseline
    already in the panel. Uses the slow src.estimate estimator - fastgrid
    implements spec=1 only."""
    from estimate import _assign_states, find_optimal_thresholds  # noqa: E402
    from global_cci_study import _grid_bounds, load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    recs = {}
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        z_min, z_max, gl, mg = _grid_bounds(z)

        st_drift = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))
        rw_drift = 100.0 * float((st_drift == 0).mean())

        opt0 = find_optimal_thresholds(y, z, z_min, z_max, gl, mg,
                                       config.SPEC_NO_DRIFT, config.MODE)
        st0 = _assign_states(z[1:], opt0["c1"], opt0["c2"])
        rw0 = 100.0 * float((st0 == 0).mean())

        opt2 = find_optimal_thresholds(y, z, z_min, z_max, gl, mg,
                                       config.SPEC_CONSTANT_DRIFT, config.MODE)
        st2 = _assign_states(z[1:], opt2["c1"], opt2["c2"])
        rw2 = 100.0 * float((st2 == 0).mean())

        recs[mkt] = {"market": mkt, "rw_pct_drift": round(rw_drift, 2),
                     "rw_pct_nodrift": round(rw0, 2),
                     "c1_nodrift": round(opt0["c1"], 3), "c2_nodrift": round(opt0["c2"], 3),
                     "rw_pct_constdrift": round(rw2, 2),
                     "c1_constdrift": round(opt2["c1"], 3), "c2_constdrift": round(opt2["c2"], 3)}
        print(f"  {mkt:<11} drift {rw_drift:5.1f}%  nodrift {rw0:5.1f}%  constdrift {rw2:5.1f}%")

    def add_ranks(key, out_key):
        order = sorted(recs, key=lambda m: -recs[m][key])
        for rank, mkt in enumerate(order, 1):
            recs[mkt][out_key] = rank

    add_ranks("rw_pct_drift", "rank_drift")
    add_ranks("rw_pct_nodrift", "rank_nodrift")
    add_ranks("rw_pct_constdrift", "rank_constdrift")

    from scipy import stats as sps  # noqa: E402
    mkts = list(recs)
    rho0 = sps.spearmanr([recs[m]["rank_drift"] for m in mkts],
                         [recs[m]["rank_nodrift"] for m in mkts])
    rho2 = sps.spearmanr([recs[m]["rank_drift"] for m in mkts],
                         [recs[m]["rank_constdrift"] for m in mkts])
    degen0 = sum(1 for m in mkts if recs[m]["c2_nodrift"] < 100.0)
    degen2 = sum(1 for m in mkts if recs[m]["c2_constdrift"] < 100.0)
    print(f"\n  Y1: Spearman(drift, nodrift) = {rho0.statistic:.3f} (p={rho0.pvalue:.2f}); "
          f"{degen0}/23 markets have c2<100 (degenerate) under no-drift")
    print(f"  Y4: Spearman(drift, constdrift) = {rho2.statistic:.3f} (p={rho2.pvalue:.2f}); "
          f"{degen2}/23 markets have c2<100 under constant-drift")

    fieldnames = ["market", "rw_pct_drift", "rw_pct_nodrift", "c1_nodrift", "c2_nodrift",
                  "rank_drift", "rank_nodrift", "rw_pct_constdrift", "c1_constdrift",
                  "c2_constdrift", "rank_constdrift"]
    return [{k: recs[m][k] for k in fieldnames} for m in mkts]


def y3_mr_horserace_check():
    """No CSV target - Y3 is X3's MR row, reproduced in dependence_corrections.py."""
    path = os.path.join(config.REBUILT, "horserace_label_vs_trailing.csv")
    if not os.path.exists(path):
        print("  Y3: skipped - run dependence_corrections.py first to build "
              "horserace_label_vs_trailing.csv (X3), which Y3 reuses.")
        return
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    a = next(r for r in rows if r["model"] == "a_regime_only" and r["term"] == "MR")
    c = next(r for r in rows if r["model"] == "c_both" and r["term"] == "MR")
    print(f"  Y3: MR coef {float(a['coef']):+.2f} (p={a['dk_p']}) without trailing -> "
          f"{float(c['coef']):+.2f} (p={c['dk_p']}) with trailing (from X3, not re-estimated)")


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


def write(name, rows):
    if not rows:
        return
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=config.B_PERMUTATION)
    args = ap.parse_args()

    print("Round 8 Y1/Y4 rank stability under spec=0 / spec=2\n")
    write("rank_stability_drift.csv", y1_y4_rank_stability())
    print()
    y3_mr_horserace_check()

    print(f"\nRound 8 Y2 circular-shift permutation | B={args.B} | "
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
