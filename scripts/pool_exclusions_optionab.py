"""
pool_exclusions_optionab.py - Round 2 (Robustness round 2, R2-R4d).

Rebuilds:
  horizon_test_exclusions.csv     R2/R3b - pooled 12m means under market-exclusion rules
  appendixD_optionAB_agreement.csv R4    - per-market Option A (full-sample) vs
                                            Option B (frozen at INSAMPLE_END) agreement

R1 (expn_check.csv) is already rebuilt by horizon_episodes.py - the export note
that every EXP month has a full 12m forward window is confirmed there, so it is
not repeated here.

R3a (return basis) has no CSV target: results/exports/README.md records it as a
sentence for Section 3.3 ("local currency; price-return index close; nominal"),
sourced from src/collect_data.py:44,47 - documented, not computed.

Key findings, from results/exports/README.md Robustness round 2:

  R2   Excluding Greece+Turkey, then also Japan, then also Spain: pooled means
       stay within ~1pp of baseline and MR>RW>EXP ordering/significance survive.
  R3b  Excluding Turkey+Argentina instead: same ordering, RW baseline falls
       ~1.75pp (as expected once the frontier market drops out).
  R4   Option A vs B panel agreement 88.17% full / 84.63% post-2015 (in-sample
       cutoff 2015-06, not 2015-12). Of the disagreeing months, 38.8% sit within
       0.25 CCI units of a threshold - the "boundary months" figure.

Usage:  python scripts/pool_exclusions_optionab.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                              # noqa: E402
from horizon_episodes import load_all       # noqa: E402
from threshold_bootstrap import grid_bounds  # noqa: E402


def pooled_custom(data, h, full_excl, exp_only_excl):
    """Same pooling rule as horizon_episodes.pooled, with a configurable
    full-market exclusion (dropped from every band) on top of the usual
    EXP-only exclusion (dropped from the pooled EXP cell only)."""
    buckets = {0: [], 1: [], 2: []}
    for mkt, d in data.items():
        if mkt in full_excl:
            continue
        f = d["fwd"][h]
        ok = ~np.isnan(f)
        for lab in (0, 1, 2):
            if lab == 2 and mkt in exp_only_excl:
                continue
            sel = ok & (d["state"] == lab)
            if sel.any():
                buckets[lab].append(f[sel])
    return {k: np.concatenate(v) if v else np.array([]) for k, v in buckets.items()}


def r2_r3b_exclusions():
    from scipy import stats as sps  # noqa: E402

    data = load_all()
    japan = set(config.EXCLUDED_EXP_MARKETS)  # {"nikkei225"}

    rules = [
        ("R2a_12m", "exclude Greece+Turkey (21 mkts, Japan-EXP still excluded)",
         {"athex", "bist100"}, japan),
        ("R2b_12m", "also exclude Japan entirely (20 mkts)",
         {"athex", "bist100", "nikkei225"}, set()),
        ("R2c_12m", "also exclude Spain (19 mkts)",
         {"athex", "bist100", "nikkei225", "ibex35"}, set()),
        ("R3b_12m", "exclude Turkey+Argentina",
         {"bist100", "merval"}, japan),
    ]

    rows = []
    for name, note, full_excl, exp_only in rules:
        b = pooled_custom(data, 12, full_excl, exp_only)
        mr, rw, ex = b[1], b[0], b[2]
        p_mr = float(sps.ttest_ind(mr, rw, equal_var=False).pvalue)
        p_ex = float(sps.ttest_ind(ex, rw, equal_var=False).pvalue)
        nmk = len(data) - len(full_excl)
        rows.append({"run": name, "note": note,
                     "MR": round(float(mr.mean()), 4), "RW": round(float(rw.mean()), 4),
                     "EXP": round(float(ex.mean()), 4),
                     "nMR": len(mr), "nRW": len(rw), "nEXP": len(ex),
                     "pMRRW": round(p_mr, 6), "pEXRW": round(p_ex, 6), "nmk": nmk})
        print(f"  {name}: MR {rows[-1]['MR']:+.2f}  RW {rows[-1]['RW']:+.2f}  "
              f"EXP {rows[-1]['EXP']:+.2f}  ({nmk} mkts)")
    return rows


def r4_optionAB_agreement():
    """Per-market Option A (full-sample, panel c1/c2) vs Option B (frozen at
    INSAMPLE_END, applied out of sample) agreement, full sample and post-2015."""
    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS                  # noqa: E402
    import pandas as pd

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    cut = pd.Period(config.INSAMPLE_END, "M")
    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates).to_period("M")
        c1_a, c2_a = float(p["c1"]), float(p["c2"])
        a = _assign_states(z[1:], c1_a, c2_a)

        insample = np.array([m <= cut for m in months])
        yb, zb = y[insample], z[insample]
        zmin, zmax, mg = grid_bounds(zb)
        c1_b, c2_b = optimal_from_parts(np.diff(yb), yb[:-1], zb[1:], zmin, zmax,
                                        config.GRID_LENGTH, mg)
        b = _assign_states(z[1:], c1_b, c2_b)

        post = np.asarray(months[1:] > cut)
        n_full, n_post = len(a), int(post.sum())
        agree_full = 100.0 * float((a == b).mean())
        agree_post = (100.0 * float((a[post] == b[post]).mean())) if n_post else ""

        rows.append({"market": mkt, "country": MARKETS[mkt]["country"],
                     "c1_A": round(c1_a, 3), "c2_A": round(c2_a, 3),
                     "c1_B": round(c1_b, 3), "c2_B": round(c2_b, 3),
                     "agree_full_pct": round(agree_full, 2),
                     "agree_post2015_pct": round(agree_post, 2) if agree_post != "" else "",
                     "n_full": n_full, "n_post2015": n_post})

    mean_full = np.mean([r["agree_full_pct"] for r in rows])
    mean_post = np.mean([r["agree_post2015_pct"] for r in rows if r["agree_post2015_pct"] != ""])
    print(f"  R4: mean agreement (per-market avg) full {mean_full:.2f}%  "
          f"post-2015 {mean_post:.2f}%")
    return rows


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
    print("Round 2 - pool exclusions and Option A/B agreement (R2, R3b, R4)\n")
    write("horizon_test_exclusions.csv", r2_r3b_exclusions())
    write("appendixD_optionAB_agreement.csv", r4_optionAB_agreement())


if __name__ == "__main__":
    main()
