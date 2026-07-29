"""
Within-market, trigger-swapped placebo: same market, same sample, same
estimator - only the trigger changes (global CCI vs the market's own
national CCI). Tests whether the main panel's 3-of-23 block-null result is a
transportability finding (global trigger fails, national trigger succeeds, in
the SAME market) rather than a property of these particular markets or of the
estimator.

Only ATHEX (Greek CCI) and BIST100 (Turkish CCI) are reproducible from this
codebase: country_cci_study.py's TARGET_MARKETS = {"athex": "GRC", "bist100":
"TUR"} is the only country-CCI mapping that exists, and market_config.py:104
explicitly documents China (Shanghai/SZSE) as excluded - no OECD CCI data
covers China. Table 5.2's Shanghai/SZSE "Country CCI" rows were never
reproduced by this pipeline (verify_paper.py's B4 check only validates the
Greece/Turkey rows) and cannot be run here without a China sentiment series
this repo does not have.

Design: for each market, restrict BOTH triggers to the SAME matched-window
months (same month-intersection logic as dependence_corrections.x4_matched_
window() / scripts/fig5_matched_window.py), fit each trigger's own adaptive
grid (global_cci_study._grid_bounds, spec=1 - the same country_cci_study.py
uses for both triggers), then run the identical placebo design already used
for the main panel (placebo_1000.py's rss_single/tar_fit/improvement; B=1000;
config.SEED_PLACEBO_T1 - same seed already recorded for this placebo work).

Output: outputs/rebuilt/placebo_trigger_swap.csv

Usage:
    python scripts/placebo_trigger_swap.py
"""
import csv
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                                    # noqa: E402
from global_cci_study import load_global_cci_pair, _grid_bounds   # noqa: E402
from threshold_bootstrap import moving_block_indices                # noqa: E402
from placebo_1000 import improvement                                 # noqa: E402

MARKETS = [("athex", "GRC"), ("bist100", "TUR")]


def matched_window(market, oecd_code):
    """Same intersection logic as dependence_corrections.x4_matched_window():
    restrict to months present in the country-CCI file."""
    y, z, dates = load_global_cci_pair(market, config.START, None)
    months = pd.to_datetime(dates).to_period("M")
    cpath = os.path.join(config.DATA, "sentiment", f"oecd_cci_{oecd_code}.csv")
    cs = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
    cs.index = pd.to_datetime(cs.index).to_period("M")
    keep = np.array([m in set(cs.index) for m in months])
    ym = y[keep]
    zm_global = z[keep]
    zm_country = cs.reindex(months[keep]).to_numpy(dtype=float)
    return ym, zm_global, zm_country


def run_trigger(label, y, z, B, rng):
    dep, x, zt = np.diff(y), y[:-1], z[1:]
    n = len(dep)
    z_min, z_max, _gl, mg = _grid_bounds(z)

    real_impr, real_c1, real_c2 = improvement(dep, x, zt, z_min, z_max, mg)
    mu, sd = float(dep.mean()), float(dep.std(ddof=1))
    y0 = float(y[0])

    print(f"  {label}: T={n}, grid=[{z_min:.1f},{z_max:.1f}] min_gap={mg}  "
          f"real={real_impr:.3f}%  (c1={real_c1:.2f}, c2={real_c2:.2f})")

    rows = []
    for dgp in ("iid", "block12"):
        null = []
        for _ in range(B):
            if dgp == "iid":
                r = rng.normal(mu, sd, size=n)
            else:
                r = dep[moving_block_indices(n, 12, rng)]
            y_b = np.concatenate(([y0], y0 + np.cumsum(r)))
            d_b, x_b = np.diff(y_b), y_b[:-1]
            imp, _, _ = improvement(d_b, x_b, zt, z_min, z_max, mg)
            null.append(imp)
        a = np.asarray(null, dtype=float)
        emp_p = float(np.mean(a >= real_impr))
        pctile = float(100.0 * np.mean(a < real_impr))
        row = {
            "label": label, "dgp": dgp, "T": n,
            "real_rss_impr": round(real_impr, 3),
            "null_rss_p50": round(float(np.percentile(a, 50)), 3),
            "null_rss_p95": round(float(np.percentile(a, 95)), 3),
            "emp_p_rss": round(emp_p, 4),
            "real_pctile": round(pctile, 1),
        }
        rows.append(row)
        print(f"    {dgp:<8} null p50={row['null_rss_p50']:.3f}  p95={row['null_rss_p95']:.3f}  "
              f"emp_p={row['emp_p_rss']:.4f}  pctile={row['real_pctile']:.1f}")
    return rows


def main():
    B = config.B_PLACEBO
    rng = np.random.default_rng(config.SEED_PLACEBO_T1)
    print(f"Trigger-swap placebo | B={B} | seed={config.SEED_PLACEBO_T1}\n")

    all_rows = []
    for market, code in MARKETS:
        ym, z_global, z_country = matched_window(market, code)
        print(f"{market.upper()} matched window, T={len(ym)}:")
        all_rows += run_trigger(f"{market}_global", ym, z_global, B, rng)
        all_rows += run_trigger(f"{market}_country({code})", ym, z_country, B, rng)
        print()

    print("SKIPPED: shanghai, szse - no China sentiment series exists in this repo "
          "(market_config.py:104 documents China as excluded from OECD CCI coverage); "
          "Table 5.2's Shanghai/SZSE Country-CCI rows were never reproduced by "
          "verify_paper.py's B4 check and cannot be run without fabricating a trigger.")

    out = os.path.join(config.ensure_rebuilt_dir(), "placebo_trigger_swap.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
