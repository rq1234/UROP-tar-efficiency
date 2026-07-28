"""
threshold_bootstrap.py - Round 10 Priority 1: full-pipeline threshold uncertainty.

Rebuilds `threshold_bootstrap.csv` and `pooled_bootstrap_gaps.csv`.

DESIGN (recovered verbatim from paper_numbers_manifest row P1_boot_design):

    "full grid RE-ESTIMATED each draw (validated fast grid==repo); B=1000;
     seed=20260722; wild=Rademacher on spec-1 residuals (x,z fixed);
     block=moving-block of (dep,x,z) triples, grid bounds recomputed per draw;
     CIs=2.5/97.5 pctile"

and P1_pooled_gaps_ci:

    "pooled 12m gaps, calendar-month cross-section resample + full
     re-estimation (B=1000): 95% CI"

So, per market and per scheme:
  wild     - fit spec=1 at the baseline thresholds, then dep* = fitted + resid*eta
             with eta ~ Rademacher{-1,+1}. x and z stay fixed, which is what makes
             this the *conditional* scheme: it conditions on the observed CCI path.
  block-L  - moving-block resample of (dep, x, z) triples with block length L,
             for L in 12/24/36. The trigger is resampled too, so grid bounds are
             recomputed from the resampled z on every draw.

Every draw re-runs the COMPLETE grid search - thresholds and labels are
re-estimated, never held fixed. That is the whole point of the exercise, and it
is only affordable because scripts/fastgrid.py is ~300x faster than the
reference implementation.

Outputs go to outputs/rebuilt/. results/exports/ is never touched.

Usage:  python scripts/threshold_bootstrap.py [--B 1000] [--markets a,b,c]
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

import config                                          # noqa: E402
from fastgrid import fit_spec1, optimal_from_parts     # noqa: E402

SCHEMES = ("wild", "block12", "block24", "block36")
PCTILES = (2.5, 97.5)


def grid_bounds(z):
    """Same rule as src/global_cci_study._grid_bounds; recomputed per draw for block."""
    mu, sigma = float(np.mean(z)), float(np.std(z))
    z_min = round(mu - config.GRID_SIGMA * sigma, 2)
    z_max = round(mu + config.GRID_SIGMA * sigma, 2)
    step = (z_max - z_min) / (config.GRID_LENGTH - 1)
    min_gap = max(config.MIN_GAP_FLOOR, int(config.MIN_BAND_POINTS / step))
    return z_min, z_max, min_gap


def moving_block_indices(n, block, rng):
    """Indices for a moving-block resample of length n with the given block size."""
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, max(1, n - block + 1), size=n_blocks)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
    return np.clip(idx, 0, n - 1)


def one_market(market, y, z, B, rng):
    """Bootstrap one market under all four schemes."""
    dep = np.diff(y)
    x = y[:-1]
    zt = z[1:]
    n = len(dep)

    z_min0, z_max0, min_gap0 = grid_bounds(z)
    c1_0, c2_0 = optimal_from_parts(dep, x, zt, z_min0, z_max0,
                                    config.GRID_LENGTH, min_gap0)
    base = fit_spec1(dep, x, zt, c1_0, c2_0)

    rows = []
    for scheme in SCHEMES:
        draws = {k: [] for k in ("c1", "c2", "MR", "RW", "EXP", "bMR", "bRW", "bEXP")}
        boundary = degenerate = 0

        for _ in range(B):
            if scheme == "wild":
                eta = rng.choice(np.array([-1.0, 1.0]), size=n)
                d_b = base["fitted"] + base["resid"] * eta
                x_b, z_b = x, zt
                z_min, z_max, min_gap = z_min0, z_max0, min_gap0
            else:
                L = int(scheme.replace("block", ""))
                idx = moving_block_indices(n, L, rng)
                d_b, x_b, z_b = dep[idx], x[idx], zt[idx]
                # trigger is resampled, so the grid must be rebuilt from it
                z_min, z_max, min_gap = grid_bounds(z_b)

            c1_b, c2_b = optimal_from_parts(d_b, x_b, z_b, z_min, z_max,
                                            config.GRID_LENGTH, min_gap)
            fit = fit_spec1(d_b, x_b, z_b, c1_b, c2_b)
            n_mr, n_rw, n_ex = fit["n"]
            tot = n_mr + n_rw + n_ex

            # a draw sitting on the grid edge, or with an empty outer band
            if c1_b <= z_min + 1e-9 or c2_b >= z_max - 1e-9:
                boundary += 1
            if n_mr == 0 or n_ex == 0:
                degenerate += 1

            draws["c1"].append(c1_b)
            draws["c2"].append(c2_b)
            draws["MR"].append(100.0 * n_mr / tot)
            draws["RW"].append(100.0 * n_rw / tot)
            draws["EXP"].append(100.0 * n_ex / tot)
            draws["bMR"].append(fit["beta"][1])
            draws["bRW"].append(fit["beta"][0])   # forced 0 in spec=1; kept for shape
            draws["bEXP"].append(fit["beta"][2])

        row = {"market": market, "scheme": scheme, "n_ok": B,
               "boundary_frac": round(boundary / B, 4),
               "degenerate_frac": round(degenerate / B, 4)}
        for key in ("c1", "c2", "MR", "RW", "EXP", "bMR", "bRW", "bEXP"):
            a = np.asarray(draws[key], dtype=float)
            lo, hi = np.percentile(a, PCTILES)
            row[f"{key}_lo"] = round(float(lo), 4)
            row[f"{key}_hi"] = round(float(hi), 4)
            row[f"{key}_med"] = round(float(np.median(a)), 4)
        rows.append(row)
    return rows, (c1_0, c2_0)


def pooled_gaps(panel, loader, B, rng):
    """Pooled 12m gaps under a calendar-month cross-section resample.

    Resamples calendar months (not markets), so cross-market dependence within a
    month is preserved, and re-estimates every market's thresholds on the
    resampled sample before recomputing the pooled gaps.
    """
    import pandas as pd

    series = {}
    for p in panel:
        mkt = p["market"]
        y, z, dates = loader(mkt)
        dep = np.diff(y)
        x = y[:-1]
        zt = z[1:]
        d = pd.to_datetime(dates[1:])
        fwd = np.full(len(dep), np.nan)
        logp = y[1:]
        h = 12
        fwd[:-h] = 100.0 * (logp[h:] - logp[:-h])
        series[mkt] = dict(dep=dep, x=x, zt=zt, months=d.to_period("M"), fwd=fwd)

    all_months = sorted({m for s in series.values() for m in s["months"]})
    all_months = np.array(all_months)

    mr_gaps, ex_gaps = [], []
    for _ in range(B):
        pick = rng.integers(0, len(all_months), size=len(all_months))
        chosen = set(all_months[pick])
        mr_v, rw_v, ex_v = [], [], []
        for mkt, s in series.items():
            keep = np.array([m in chosen for m in s["months"]])
            if keep.sum() < 50:
                continue
            d_b, x_b, z_b = s["dep"][keep], s["x"][keep], s["zt"][keep]
            f_b = s["fwd"][keep]
            z_min, z_max, min_gap = grid_bounds(z_b)
            c1_b, c2_b = optimal_from_parts(d_b, x_b, z_b, z_min, z_max,
                                            config.GRID_LENGTH, min_gap)
            st = np.zeros(len(z_b), dtype=int)
            st[z_b < c1_b] = 1
            st[z_b > c2_b] = 2
            ok = ~np.isnan(f_b)
            for lab, bucket in ((1, mr_v), (0, rw_v), (2, ex_v)):
                if lab == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                    continue           # Japan's EXP months are excluded from the pooled cell
                sel = ok & (st == lab)
                if sel.any():
                    bucket.append(f_b[sel])
        if not (mr_v and rw_v and ex_v):
            continue
        mr_m = np.concatenate(mr_v).mean()
        rw_m = np.concatenate(rw_v).mean()
        ex_m = np.concatenate(ex_v).mean()
        mr_gaps.append(mr_m - rw_m)
        ex_gaps.append(ex_m - rw_m)

    out = []
    for name, arr in (("MR_RW_gap", mr_gaps), ("EXP_RW_gap", ex_gaps)):
        a = np.asarray(arr, dtype=float)
        lo, hi = np.percentile(a, PCTILES)
        out.append({"stat": name, "mean": round(float(a.mean()), 3),
                    "ci_lo": round(float(lo), 3), "ci_hi": round(float(hi), 3)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=config.B_BOOTSTRAP)
    ap.add_argument("--markets", type=str, default="")
    ap.add_argument("--skip-pooled", action="store_true")
    args = ap.parse_args()

    from global_cci_study import load_global_cci_pair    # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))
    if args.markets:
        want = set(args.markets.split(","))
        panel = [p for p in panel if p["market"] in want]

    out_dir = config.ensure_rebuilt_dir()
    rng = np.random.default_rng(config.SEED_ROUND_8_10)

    print(f"Round 10 Priority 1 bootstrap | B={args.B} | seed={config.SEED_ROUND_8_10}")
    print(f"{len(panel)} markets x {len(SCHEMES)} schemes, full grid re-estimated per draw\n")

    rows, t0 = [], time.time()
    for p in panel:
        mkt = p["market"]
        t1 = time.time()
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        mrows, (c1, c2) = one_market(mkt, y, z, args.B, rng)
        rows.extend(mrows)
        print(f"  {mkt:<11} baseline c1={c1:.3f} c2={c2:.3f}   "
              f"{time.time() - t1:6.1f}s")

    path = os.path.join(out_dir, "threshold_bootstrap.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {path}  ({len(rows)} rows, {time.time() - t0:.0f}s)")

    if not args.skip_pooled:
        print("\npooled calendar-month gaps ...")
        t1 = time.time()
        g = pooled_gaps(panel, lambda m: load_global_cci_pair(m, config.START, None),
                        args.B, rng)
        gpath = os.path.join(out_dir, "pooled_bootstrap_gaps.csv")
        with open(gpath, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["stat", "mean", "ci_lo", "ci_hi"])
            w.writeheader()
            w.writerows(g)
        for r in g:
            print(f"  {r['stat']:<12} {r['mean']:+.3f} [{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]")
        print(f"wrote {gpath}  ({time.time() - t1:.0f}s)")


if __name__ == "__main__":
    main()
