"""
round04_placebo_stability.py - Round 4 T1 (placebo grid search, B=50) and
T2 (scale-adjusted rolling-threshold stability). T3 (China CCI) and T4
(pre-1990 era) have no CSV target reachable here - T3 needs a live FRED pull
(no API key configured; see ASSUMPTIONS.md A4.8) and T4 is a text finding
with "no paper change" per results/exports/README.md.

Rebuilds:
  placebo_thresholds.csv       T1 - all 1,150 individual placebo runs (23x50)
  placebo_summary.csv          T1 - per-market percentiles and band share
  stability_scale_adjusted.csv T2 - rolling-threshold range, normalised by
                                     sigma and span, for MCSI/US-CCI/global-CCI

Key findings, from results/exports/README.md Round 4:

  T1  Location is partly mechanical (25.5% of 1,150 placebo (c1,c2) pairs land
      inside the real cluster bands 97.02-98.45 & 101.19-102.43), but the fit
      is not: real markets' RSS improvement sits at a median 94th percentile
      of their placebo distributions (18/23 >= 90th). Seed=20260721, B=50 -
      this is the ORIGINAL run Round 10 P9 later superseded at B=1000 with a
      block-resampled null (round10_placebo.py); reproduced here as run, not
      as the final word (see placebo_1000.csv / ASSUMPTIONS.md A3.3-style note).
  T2  Normalising rolling-threshold ranges by each trigger's sigma and span
      REMOVES the CCI's apparent stability advantage: c1 range/sigma global
      4.12 > MCSI 3.32 > US-CCI 2.84; range/span global 0.86 > MCSI 0.74 >
      US-CCI 0.65 - the raw "4.8 vs 46 units" comparison was a scale artefact.

Usage:  python scripts/round04_placebo_stability.py [--B 50]
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
from fastgrid import fast_grid_rss_parts, fit_spec1              # noqa: E402
from round10_bootstrap import grid_bounds                        # noqa: E402

# Real cluster bands, from GROUND_TRUTH section 6 / Round 4 T1 (same
# constants round10_placebo.py uses for the B=1000 supersession).
BAND_C1 = (97.02, 98.45)
BAND_C2 = (101.19, 102.43)


def rss_single(dep):
    return float(np.sum((dep - dep.mean()) ** 2))


def tar_fit(dep, x, zt, z_min, z_max, min_gap):
    grid = np.linspace(z_min, z_max, config.GRID_LENGTH)
    rss, i_idx, j_idx = fast_grid_rss_parts(dep, x, zt, grid, min_gap)
    k = int(np.argmin(rss))
    return float(rss[k]), float(grid[i_idx[k]]), float(grid[j_idx[k]])


def t1_placebo(B):
    from global_cci_study import load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rng = np.random.default_rng(config.SEED_PLACEBO_T1)
    thresholds, summary = [], []
    print(f"Round 4 T1 placebo | B={B} | seed={config.SEED_PLACEBO_T1}\n")

    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        dep, x, zt = np.diff(y), y[:-1], z[1:]
        z_min, z_max, min_gap = grid_bounds(z)

        r0 = rss_single(dep)
        rss_real, c1_real, c2_real = tar_fit(dep, x, zt, z_min, z_max, min_gap)
        impr_real = 100.0 * (r0 - rss_real) / r0
        fit_real = fit_spec1(dep, x, zt, c1_real, c2_real)

        mu, sd, y0 = float(dep.mean()), float(dep.std(ddof=1)), float(y[0])
        plac_c1, plac_c2, plac_impr, in_band = [], [], [], 0
        for sim in range(B):
            r = rng.normal(mu, sd, size=len(dep))
            y_b = np.concatenate(([y0], y0 + np.cumsum(r)))
            d_b, x_b = np.diff(y_b), y_b[:-1]
            r0_b = rss_single(d_b)
            rss_b, c1_b, c2_b = tar_fit(d_b, x_b, zt, z_min, z_max, min_gap)
            impr_b = 100.0 * (r0_b - rss_b) / r0_b
            fit_b = fit_spec1(d_b, x_b, zt, c1_b, c2_b)

            thresholds.append({"market": mkt, "sim": sim, "c1": round(c1_b, 4),
                               "c2": round(c2_b, 4), "rss_impr_pct": round(impr_b, 4),
                               "b_MR": round(float(fit_b["beta"][1]), 6),
                               "b_EX": round(float(fit_b["beta"][2]), 6)})
            plac_c1.append(c1_b); plac_c2.append(c2_b); plac_impr.append(impr_b)
            if BAND_C1[0] <= c1_b <= BAND_C1[1] and BAND_C2[0] <= c2_b <= BAND_C2[1]:
                in_band += 1

        pc1, pc2, pi = np.asarray(plac_c1), np.asarray(plac_c2), np.asarray(plac_impr)
        summary.append({
            "market": mkt, "real_c1": round(c1_real, 3), "real_c2": round(c2_real, 3),
            "real_rss_impr_pct": round(impr_real, 4),
            "plac_c1_p5": round(float(np.percentile(pc1, 5)), 3),
            "plac_c1_p25": round(float(np.percentile(pc1, 25)), 3),
            "plac_c1_p50": round(float(np.percentile(pc1, 50)), 3),
            "plac_c1_p75": round(float(np.percentile(pc1, 75)), 3),
            "plac_c1_p95": round(float(np.percentile(pc1, 95)), 3),
            "plac_c2_p5": round(float(np.percentile(pc2, 5)), 3),
            "plac_c2_p50": round(float(np.percentile(pc2, 50)), 3),
            "plac_c2_p95": round(float(np.percentile(pc2, 95)), 3),
            "band_share_pct": round(100.0 * in_band / B, 1),
            "real_c1_pctile": round(100.0 * float(np.mean(pc1 < c1_real)), 1),
            "real_c2_pctile": round(100.0 * float(np.mean(pc2 < c2_real)), 1),
            "real_rss_pctile": round(100.0 * float(np.mean(pi < impr_real)), 1),
            "plac_rss_p50": round(float(np.percentile(pi, 50)), 4),
            "plac_rss_p95": round(float(np.percentile(pi, 95)), 4),
        })
        print(f"  {mkt:<11} real impr {impr_real:6.3f}  pctile {summary[-1]['real_rss_pctile']:5.1f}  "
              f"band_share {summary[-1]['band_share_pct']:5.1f}%")

    med = float(np.median([s["real_rss_pctile"] for s in summary]))
    ge90 = sum(1 for s in summary if s["real_rss_pctile"] >= 90)
    total_band = sum(1 for t in thresholds
                     if BAND_C1[0] <= t["c1"] <= BAND_C1[1] and BAND_C2[0] <= t["c2"] <= BAND_C2[1])
    print(f"\n  T1: median real RSS percentile {med:.0f}  ({ge90}/{len(summary)} >= 90th)")
    print(f"  T1: {total_band}/{len(thresholds)} placebo pairs "
          f"({100.0 * total_band / len(thresholds):.1f}%) land inside the real cluster bands")
    return thresholds, summary


def t2_scale_adjusted():
    """Rolling 10-yr/1-yr-step threshold ranges for MCSI, US-CCI and global-CCI,
    normalised by each trigger's sigma and span. CAPE is skipped - the archived
    rolling CSV has no trigger series (per results/exports/README.md)."""
    import pandas as pd

    from bubble_now import FULL_END, PAIR_SPECS, load_pair_with_dates  # noqa: E402
    from country_cci_study import load_cci_pair                        # noqa: E402
    from global_cci_study import _grid_bounds, load_global_cci_pair    # noqa: E402
    from rolling_thresholds import rolling_windows                     # noqa: E402

    rows = []

    # MCSI - reuse bubble_now's SP500_MCSI pair spec.
    spec = next(s for s in PAIR_SPECS if s[-1] == "SP500_MCSI")
    freq, eq, trig, start, z_min, z_max, gl, mg, sp, tlag, label = spec
    y, z, dates = load_pair_with_dates(config.MONTHLY_PANEL, eq, trig, start, FULL_END, tlag)
    windows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, sp)
    rows.append(("MCSI", z, windows))

    # US-CCI (sp500 + OECD USA CCI) - adaptive grid, same convention as V1/V3.
    y, z, dates = load_cci_pair("sp500", "USA", start=config.START)
    z_min, z_max, gl, mg = _grid_bounds(z)
    windows = rolling_windows(y, z, pd.DatetimeIndex(dates), z_min, z_max, gl, mg, 1)
    rows.append(("US_CCI", z, windows))

    # global_CCI (sp500 + the paper's own aggregate) - adaptive grid.
    y, z, dates = load_global_cci_pair("sp500", config.START, None)
    z_min, z_max, gl, mg = _grid_bounds(z)
    windows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    rows.append(("global_CCI", z, windows))

    out = []
    for label, z, windows in rows:
        if not windows:
            print(f"  T2: {label} - no rolling windows (series too short), skipped")
            continue
        c1s = np.array([w[1] for w in windows])
        c2s = np.array([w[2] for w in windows])
        sigma, span = float(z.std(ddof=1)), float(z.max() - z.min())
        c1_range, c2_range = float(c1s.max() - c1s.min()), float(c2s.max() - c2s.min())
        out.append({"trigger": label, "sigma": round(sigma, 3), "span": round(span, 3),
                    "c1_range": round(c1_range, 3), "c2_range": round(c2_range, 3),
                    "c1_range_over_sigma": round(c1_range / sigma, 3),
                    "c2_range_over_sigma": round(c2_range / sigma, 3),
                    "c1_range_over_span": round(c1_range / span, 3),
                    "c2_range_over_span": round(c2_range / span, 3)})
        print(f"  T2 {label:<12} sigma={sigma:.2f} span={span:.2f}  "
              f"c1_range/sigma={out[-1]['c1_range_over_sigma']}  "
              f"c1_range/span={out[-1]['c1_range_over_span']}")
    return out


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
    ap.add_argument("--B", type=int, default=config.B_PLACEBO_T1)
    args = ap.parse_args()

    t0 = time.time()
    thresholds, summary = t1_placebo(args.B)
    write("placebo_thresholds.csv", thresholds)
    write("placebo_summary.csv", summary)

    print("\nRound 4 T2 scale-adjusted rolling-threshold stability\n")
    write("stability_scale_adjusted.csv", t2_scale_adjusted())
    print(f"\n  done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
