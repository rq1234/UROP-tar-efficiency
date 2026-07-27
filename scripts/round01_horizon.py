"""
round01_horizon.py - the horizon and episode layer.

Rebuilds:
  horizon_test.csv            Table 6.1 - pooled forward returns by band  (A9, A10, B2)
  horizon_test_per_market.csv pool composition behind the table
  horizon_test_exp_phase.csv  Table 6.2 - early vs late EXP split
  F6_within_market_means.csv  per-market band means               (C29 sign test)
  episodes_exp.csv            the 30 explosive episodes            (A13, C37)
  expn_check.csv              R1 - why n_EXP is constant across horizons

All deterministic. Every one should reproduce its export exactly.

MEMBERSHIP RULE (results/exports/README.md Item 2, applied uniformly):

  All 23 markets in global_cci_all_markets.csv. Each month is classified
  MR/RW/EXP by the GLOBAL CCI against that market's own full-sample Option-A
  thresholds. Forward cumulative log-returns are pooled across the 23 markets.
  Japan's EXP months are excluded from the pooled EXP cell ONLY - its c2=99.87
  is degenerate, so 61% of its months would be "EXP". Japan's MR and RW months
  are kept.

That exclusion lives in config.EXCLUDED_EXP_MARKETS rather than buried inside a
private helper, which is where it was (src/horizon_test.py:145).

The p-values here are RAW. Forward windows overlap month to month, so the
effective N is smaller than the nominal n; treat them as directional. The
dependence-corrected versions are Round 7 (X1, X2) and Round 10 (P5).

Usage:  python scripts/round01_horizon.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def load_all():
    """Per-market state, dates and forward returns at every horizon."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS                  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    data = {}
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        state = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))
        logp = y[1:]
        months = pd.to_datetime(dates[1:]).to_period("M")
        fwd = {}
        for h in config.HORIZONS:
            f = np.full(len(state), np.nan)
            if len(logp) > h:
                f[:-h] = 100.0 * (logp[h:] - logp[:-h])
            fwd[h] = f
        data[mkt] = {"country": MARKETS[mkt]["country"], "state": state,
                     "months": months, "fwd": fwd, "T": len(state)}
    return data


def pooled(data, h):
    """Pooled forward returns by band at horizon h, honouring the Japan rule."""
    buckets = {0: [], 1: [], 2: []}
    for mkt, d in data.items():
        f = d["fwd"][h]
        ok = ~np.isnan(f)
        for lab in (0, 1, 2):
            if lab == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                continue
            sel = ok & (d["state"] == lab)
            if sel.any():
                buckets[lab].append(f[sel])
    return {k: np.concatenate(v) if v else np.array([]) for k, v in buckets.items()}


def spells(mask):
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


def main():
    from scipy import stats as sps  # noqa: E402

    data = load_all()
    out_dir = config.ensure_rebuilt_dir()
    print("Round 1 horizon layer - deterministic\n")

    # ---- horizon_test.csv -------------------------------------------------
    rows = []
    for h in config.HORIZONS:
        b = pooled(data, h)
        mr, rw, ex = b[1], b[0], b[2]
        p_mr = sps.ttest_ind(mr, rw, equal_var=False).pvalue
        p_ex = sps.ttest_ind(ex, rw, equal_var=False).pvalue
        p_an = sps.f_oneway(mr, rw, ex).pvalue
        rows.append({"horizon_m": h,
                     "MR_mean_pct": round(float(mr.mean()), 4), "n_MR": len(mr),
                     "RW_mean_pct": round(float(rw.mean()), 4), "n_RW": len(rw),
                     "EXP_mean_pct": round(float(ex.mean()), 4), "n_EXP": len(ex),
                     "MR_vs_RW_p": round(float(p_mr), 6),
                     "EXP_vs_RW_p": round(float(p_ex), 6),
                     "ANOVA_p": round(float(p_an), 6)})
    write(out_dir, "horizon_test.csv", rows)
    r12 = rows[-1]
    print(f"  12m: MR {r12['MR_mean_pct']} (n={r12['n_MR']})  "
          f"RW {r12['RW_mean_pct']} (n={r12['n_RW']})  "
          f"EXP {r12['EXP_mean_pct']} (n={r12['n_EXP']})")

    # ---- horizon_test_per_market.csv --------------------------------------
    pm = [{"market": m, "country": d["country"], "T": d["T"],
           "n_MR": int((d["state"] == 1).sum()),
           "n_RW": int((d["state"] == 0).sum()),
           "n_EXP": int((d["state"] == 2).sum())} for m, d in data.items()]
    write(out_dir, "horizon_test_per_market.csv", pm)

    # ---- F6_within_market_means.csv ---------------------------------------
    f6 = []
    for m, d in data.items():
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        rec = {"market": m, "country": d["country"]}
        for lab, name in ((1, "MR"), (0, "RW"), (2, "EXP")):
            sel = ok & (d["state"] == lab)
            rec[f"mean_{name}_pct"] = round(float(f[sel].mean()), 3) if sel.any() else ""
            rec[f"n_{name}"] = int(sel.sum())
        f6.append(rec)
    write(out_dir, "F6_within_market_means.csv", f6)
    mr_gt = sum(1 for r in f6 if r["mean_MR_pct"] != "" and r["mean_MR_pct"] > r["mean_RW_pct"])
    ex_lt = sum(1 for r in f6 if r["mean_EXP_pct"] != "" and r["n_EXP"] > 0
                and r["market"] not in config.EXCLUDED_EXP_MARKETS
                and r["mean_EXP_pct"] < r["mean_RW_pct"])
    n_ex = sum(1 for r in f6 if r["n_EXP"] > 0
               and r["market"] not in config.EXCLUDED_EXP_MARKETS)
    print(f"  F6 sign test: MR>RW in {mr_gt}/{len(f6)};  EXP<RW in {ex_lt}/{n_ex} ex-Japan")

    # ---- episodes_exp.csv --------------------------------------------------
    eps = []
    for m, d in data.items():
        if m in config.EXCLUDED_EXP_MARKETS:
            continue
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        rw_sel = ok & (d["state"] == 0)
        rw_base = float(f[rw_sel].mean())
        for s, L in spells(d["state"] == 2):
            seg, segok = f[s:s + L], ok[s:s + L]
            if not segok.any():
                continue
            mean_ep = float(seg[segok].mean())
            eps.append({"market": m, "country": d["country"],
                        "start": str(d["months"][s]), "end": str(d["months"][s + L - 1]),
                        "length_months": L,
                        "ep_mean_12m_pct": round(mean_ep, 3),
                        "own_RW_mean_12m_pct": round(rw_base, 3),
                        "excess_pp": round(mean_ep - rw_base, 3)})
    write(out_dir, "episodes_exp.csv", eps)
    exc = np.array([e["excess_pp"] for e in eps])
    tt = sps.ttest_1samp(exc, 0.0)
    in97 = sum(1 for e in eps if e["start"][:4] in ("1997", "1998", "1999", "2000"))
    print(f"  episodes: {len(eps)}, mean excess {exc.mean():+.2f}pp, "
          f"t={tt.statistic:.2f} p={tt.pvalue:.4f}, {int((exc < 0).sum())} negative, "
          f"{in97} start in 1997-2000")

    # ---- horizon_test_exp_phase.csv ---------------------------------------
    ph = []
    for h in config.HORIZONS:
        early, late = [], []
        for m, d in data.items():
            if m in config.EXCLUDED_EXP_MARKETS:
                continue
            f = d["fwd"][h]
            for s, L in spells(d["state"] == 2):
                half = -(-L // 2)              # ceil(L/2)
                e, l = f[s:s + half], f[s + half:s + L]
                early.append(e[~np.isnan(e)])
                late.append(l[~np.isnan(l)])
        e = np.concatenate([a for a in early if a.size]) if early else np.array([])
        l = np.concatenate([a for a in late if a.size]) if late else np.array([])
        ph.append({"horizon_m": h,
                   "early_EXP_mean_pct": round(float(e.mean()), 4), "n_early": len(e),
                   "late_EXP_mean_pct": round(float(l.mean()), 4), "n_late": len(l),
                   "early_vs_late_p": round(float(
                       sps.ttest_ind(e, l, equal_var=False).pvalue), 6)})
    write(out_dir, "horizon_test_exp_phase.csv", ph)

    # ---- expn_check.csv ----------------------------------------------------
    ck = []
    for m, d in data.items():
        exp_idx = np.flatnonzero(d["state"] == 2)
        last = str(d["months"][exp_idx[-1]]) if exp_idx.size else ""
        end = str(d["months"][-1])
        gap = float((d["months"][-1] - d["months"][exp_idx[-1]]).n) if exp_idx.size else ""
        ck.append({"market": m, "n_EXP": int(exp_idx.size), "last_EXP_month": last,
                   "sample_end": end, "gap_months": gap,
                   "contributes": m not in config.EXCLUDED_EXP_MARKETS and exp_idx.size > 0})
    write(out_dir, "expn_check.csv", ck)
    gaps = [c["gap_months"] for c in ck if c["contributes"] and c["gap_months"] != ""]
    print(f"  expn_check: min gap to sample end among contributing markets = "
          f"{min(gaps):.0f} months -> every EXP month has a full 12m window")


def write(out_dir, name, rows):
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
