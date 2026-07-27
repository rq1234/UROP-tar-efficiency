"""
round10_placebo.py - Round 10 Priority 9: placebo at B=1000 with a vol-clustering null.

Rebuilds `placebo_1000.csv`.

WHY THIS ONE MATTERS
--------------------
It REVISES a headline verdict. Round 4 T1 ran 50 iid placebo draws per market
and concluded "threshold placement is DISTINGUISHABLE from trigger-driven".
Round 10 P9 raised B to 1000 and added a block-resampled null that preserves
volatility clustering and heavy tails, and found:

  "against an iid null the real RSS improvement exceeds it (emp p<0.05) in 9/23
   (median real pctile 91); against a block-resampled (vol-clustering,
   heavy-tailed) null, only 3/23 (median 80). So against a realistic null the
   TAR fit is largely not distinguishable from chance - the earlier T1
   'distinguishable' claim does not hold and must be softened; do not claim a
   random walk 'cannot' reproduce the fit."

DESIGN
------
Per market, generate B placebo log-price paths matched to that market's own
length, drift and volatility, then run the IDENTICAL spec=1 grid search of each
placebo path against the REAL global CCI. The trigger is never simulated - only
the price path - so this isolates "could a series with no regime structure earn
these thresholds against this trigger?".

  iid      returns drawn iid Normal(mean, sd) from the market's own returns
  block12  moving-block resample of the market's actual returns, block 12,
           which preserves volatility clustering and fat tails

Statistic: percentage RSS improvement from splitting, relative to a single
no-split RW fit (alpha = mean return, beta = 0):

    rss_impr = 100 * (RSS_single - RSS_TAR) / RSS_single

Reported per market and DGP: the real value, the null median and 95th
percentile, the empirical p (share of null draws at least as good as the real
one), the real value's percentile in the null, and the share of placebo
(c1,c2) pairs landing inside the real cluster bands.

Seed: config.SEED_PLACEBO_T1 (20260721), the seed recorded for the placebo work.

Usage:  python scripts/round10_placebo.py [--B 1000] [--markets a,b]
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

import config                                                   # noqa: E402
from fastgrid import fast_grid_rss_parts                        # noqa: E402
from round10_bootstrap import grid_bounds, moving_block_indices  # noqa: E402

# Real cluster bands, from GROUND_TRUTH section 6 / Round 4 T1.
BAND_C1 = (97.02, 98.45)
BAND_C2 = (101.19, 102.43)


def rss_single(dep):
    """RSS of the no-split fit: alpha = mean(dep), beta = 0."""
    return float(np.sum((dep - dep.mean()) ** 2))


def tar_fit(dep, x, zt, z_min, z_max, min_gap):
    """Best TAR RSS on the grid, plus the winning thresholds."""
    grid = np.linspace(z_min, z_max, config.GRID_LENGTH)
    rss, i_idx, j_idx = fast_grid_rss_parts(dep, x, zt, grid, min_gap)
    k = int(np.argmin(rss))
    return float(rss[k]), float(grid[i_idx[k]]), float(grid[j_idx[k]])


def improvement(dep, x, zt, z_min, z_max, min_gap):
    r0 = rss_single(dep)
    r1, c1, c2 = tar_fit(dep, x, zt, z_min, z_max, min_gap)
    return 100.0 * (r0 - r1) / r0, c1, c2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=config.B_PLACEBO)
    ap.add_argument("--markets", type=str, default="")
    args = ap.parse_args()

    from global_cci_study import load_global_cci_pair            # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))
    if args.markets:
        want = set(args.markets.split(","))
        panel = [p for p in panel if p["market"] in want]

    rng = np.random.default_rng(config.SEED_PLACEBO_T1)
    rows, t0 = [], time.time()

    print(f"Round 10 Priority 9 placebo | B={args.B} | seed={config.SEED_PLACEBO_T1}")
    print(f"{len(panel)} markets x 2 nulls, real global CCI held fixed\n")

    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        dep = np.diff(y)
        x = y[:-1]
        zt = z[1:]
        n = len(dep)
        z_min, z_max, min_gap = grid_bounds(z)

        real_impr, _, _ = improvement(dep, x, zt, z_min, z_max, min_gap)
        mu, sd = float(dep.mean()), float(dep.std(ddof=1))
        y0 = float(y[0])

        for dgp in ("iid", "block12"):
            null, in_band = [], 0
            for _ in range(args.B):
                if dgp == "iid":
                    r = rng.normal(mu, sd, size=n)
                else:
                    r = dep[moving_block_indices(n, 12, rng)]
                # rebuild a log-price path so x is the placebo's own lagged level
                y_b = np.concatenate(([y0], y0 + np.cumsum(r)))
                d_b, x_b = np.diff(y_b), y_b[:-1]
                imp, c1_b, c2_b = improvement(d_b, x_b, zt, z_min, z_max, min_gap)
                null.append(imp)
                if (BAND_C1[0] <= c1_b <= BAND_C1[1]
                        and BAND_C2[0] <= c2_b <= BAND_C2[1]):
                    in_band += 1

            a = np.asarray(null, dtype=float)
            emp_p = float(np.mean(a >= real_impr))
            pctile = float(100.0 * np.mean(a < real_impr))
            rows.append({
                "market": mkt, "dgp": dgp,
                "real_rss_impr": round(real_impr, 3),
                "null_rss_p50": round(float(np.percentile(a, 50)), 3),
                "null_rss_p95": round(float(np.percentile(a, 95)), 3),
                "emp_p_rss": round(emp_p, 4),
                "real_pctile": round(pctile, 1),
                "band_share_pct": round(100.0 * in_band / args.B, 1),
            })
        print(f"  {mkt:<11} real {real_impr:6.3f}   "
              f"iid p={rows[-2]['emp_p_rss']:.3f}  block12 p={rows[-1]['emp_p_rss']:.3f}")

    out = os.path.join(config.ensure_rebuilt_dir(), "placebo_1000.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print()
    for dgp in ("iid", "block12"):
        sub = [r for r in rows if r["dgp"] == dgp]
        beat = sum(1 for r in sub if r["emp_p_rss"] < 0.05)
        med = float(np.median([r["real_pctile"] for r in sub]))
        print(f"  {dgp:<8} real beats null at p<0.05 in {beat}/{len(sub)}   "
              f"median real percentile {med:.0f}")
    print(f"\n  -> placebo_1000.csv ({len(rows)} rows, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
