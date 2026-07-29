"""
Task 1c (secondary): S&P 500 under the Global OECD CCI, same placebo design.

sp500 is not in the admissible 23-market panel - it fails the reverse-Granger
screen (US equity returns move the GDP-weighted global aggregate), so this is
NOT a clean test: endogeneity biases the placebo toward passing (the trigger
partly contains the thing it's being used to explain), so only a FAILURE here
is interpretable. A pass tells us nothing, since it could be genuine
information or feedback and this design cannot separate the two.

Same design as placebo_1000.py: rss_single/tar_fit/improvement, B=1000,
config.SEED_PLACEBO_T1, spec=1, adaptive grid via global_cci_study._grid_bounds
(sp500 has no prior fit in the panel since it never passed screening, so this
computes one directly from data/combined/monthly_panel.csv's eq_sp500 column).

Output: outputs/rebuilt/placebo_sp500_global.csv

Usage:
    python scripts/placebo_sp500_global.py
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                                    # noqa: E402
from global_cci_study import load_global_cci_pair, _grid_bounds    # noqa: E402
from threshold_bootstrap import moving_block_indices                 # noqa: E402
from placebo_1000 import improvement                                  # noqa: E402


def main():
    B = config.B_PLACEBO
    rng = np.random.default_rng(config.SEED_PLACEBO_T1)

    y, z, dates = load_global_cci_pair("sp500", config.START, None)
    dep, x, zt = np.diff(y), y[:-1], z[1:]
    n = len(dep)
    z_min, z_max, _gl, mg = _grid_bounds(z)

    real_impr, real_c1, real_c2 = improvement(dep, x, zt, z_min, z_max, mg)
    mu, sd = float(dep.mean()), float(dep.std(ddof=1))
    y0 = float(y[0])

    print(f"S&P500 under Global OECD CCI | B={B} | seed={config.SEED_PLACEBO_T1}")
    print(f"T={n}, grid=[{z_min:.1f},{z_max:.1f}] min_gap={mg}  "
          f"real={real_impr:.3f}%  (c1={real_c1:.2f}, c2={real_c2:.2f})")
    print("NOTE: sp500 fails the reverse-Granger screen - endogeneity biases this "
          "test toward passing. Only a failure is interpretable.\n")

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
            "market": "sp500_global", "dgp": dgp, "T": n,
            "real_rss_impr": round(real_impr, 3),
            "null_rss_p50": round(float(np.percentile(a, 50)), 3),
            "null_rss_p95": round(float(np.percentile(a, 95)), 3),
            "emp_p_rss": round(emp_p, 4),
            "real_pctile": round(pctile, 1),
        }
        rows.append(row)
        print(f"  {dgp:<8} null p50={row['null_rss_p50']:.3f}  p95={row['null_rss_p95']:.3f}  "
              f"emp_p={row['emp_p_rss']:.4f}  pctile={row['real_pctile']:.1f}")

    out = os.path.join(config.ensure_rebuilt_dir(), "placebo_sp500_global.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
