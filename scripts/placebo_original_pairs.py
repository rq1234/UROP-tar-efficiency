"""
Apply the exact placebo design already used for the main 23-market panel
(scripts/placebo_1000.py: A5/C13/C14, "block12 3/23, iid 9/23") to the two
ORIGINAL Ahmed & Satchell (2018) market-trigger pairings, instead of the
global-CCI panel:

  S&P 500 with the Michigan Consumer Sentiment Index (Table 7, spec=1 row)
  FTSE 100 with the VIX                              (Table 8, spec=1 row)

WHY: the main-panel result (3 of 23 indices distinguishable from a
12-month block-resampled null) could be a property of this panel and its
common trigger, or a property of the estimator itself. Farid, an author of
the original paper, will ask which. Running the identical placebo procedure
on the pairings the estimator was originally built for answers that.

This reuses src/replicate.py's own data loading (load_pair) and its own
grid specification for each pairing (NOT the adaptive grid_bounds() used for
the global-CCI panel) - the point is to test the estimator on the setup it
was designed for, unchanged. It reuses scripts/placebo_1000.py's rss_single/
tar_fit/improvement functions directly (not reimplemented), so the placebo
mechanics are identical to the main-panel run: iid null ~ Normal(mean, sd)
of the market's own returns; block12 null = moving-block resample (block=12)
of the market's own returns, preserving volatility clustering. B=1000,
config.SEED_PLACEBO_T1 - the same seed already recorded for this placebo
work, so this is not a new stochastic decision.

Output: outputs/rebuilt/placebo_original_pairs.csv

Usage:
    python scripts/placebo_original_pairs.py
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                                # noqa: E402
from replicate import load_pair, TABLE7_SPECS, TABLE8_SPECS   # noqa: E402
from threshold_bootstrap import moving_block_indices           # noqa: E402
from placebo_1000 import rss_single, tar_fit, improvement       # noqa: E402, F401

# Pull the exact spec=1 ("w/mov drift", switching drift - the main paper's
# primary specification) row for each pairing, unchanged from replicate.py.
SP500_MCSI = next(r for r in TABLE7_SPECS if r[0] == "eq_sp500" and r[7] == 1)
FTSE_VIX = next(r for r in TABLE8_SPECS if r[0] == "eq_ftse100" and r[7] == 1)

MONTHLY_PANEL = os.path.join(ROOT, "data", "combined", "monthly_panel.csv")
DAILY_PANEL = os.path.join(ROOT, "data", "combined", "daily_panel.csv")


def run_pairing(label, panel_path, spec_row, trigger_col, B, rng):
    equity_col, start, end, z_min, z_max, gl, mg, spec, mode, spec_label, skip, tlag = spec_row
    y, z = load_pair(panel_path, equity_col, trigger_col, start, end, skip=skip, trigger_lag=tlag)
    dep, x, zt = np.diff(y), y[:-1], z[1:]
    n = len(dep)
    T = len(y)

    real_impr, real_c1, real_c2 = improvement(dep, x, zt, z_min, z_max, mg)
    mu, sd = float(dep.mean()), float(dep.std(ddof=1))
    y0 = float(y[0])

    print(f"\n{label}: T={T}, spec={spec} ({spec_label}), grid=[{z_min},{z_max}] "
          f"gl={gl} min_gap={mg}")
    print(f"  real RSS improvement = {real_impr:.3f}%  (c1={real_c1:.2f}, c2={real_c2:.2f})")

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
            "pairing": label, "dgp": dgp, "T": T,
            "real_rss_impr": round(real_impr, 3),
            "null_rss_p50": round(float(np.percentile(a, 50)), 3),
            "null_rss_p95": round(float(np.percentile(a, 95)), 3),
            "emp_p_rss": round(emp_p, 4),
            "real_pctile": round(pctile, 1),
        }
        rows.append(row)
        print(f"  {dgp:<8} null p50={row['null_rss_p50']:.3f}  p95={row['null_rss_p95']:.3f}  "
              f"emp_p={row['emp_p_rss']:.4f}  real sits at pctile {row['real_pctile']:.1f}")
    return rows


def main():
    B = config.B_PLACEBO
    rng = np.random.default_rng(config.SEED_PLACEBO_T1)
    print(f"Placebo on the original Ahmed & Satchell pairings | B={B} | "
          f"seed={config.SEED_PLACEBO_T1}")

    all_rows = []
    all_rows += run_pairing("S&P500+MCSI", MONTHLY_PANEL, SP500_MCSI, "mcsi", B, rng)
    all_rows += run_pairing("FTSE100+VIX", DAILY_PANEL, FTSE_VIX, "vix", B, rng)

    out = os.path.join(config.ensure_rebuilt_dir(), "placebo_original_pairs.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
