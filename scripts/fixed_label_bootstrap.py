"""
fixed_label_bootstrap.py - C34/C35: fixed-label moving-block bootstrap.

The biggest remaining gap, cited five times in the paper (abstract, Sec 3.1,
twice in Sec 6.3/D.4). config.SEED_FIXED_LABEL_BLOCK = 12345 is defined but
was never used anywhere before this script.

"Fixed-label" means the MR/RW/EXP labels are the panel's committed
full-sample states, held FIXED - never re-estimated per bootstrap draw
(contrast scripts/threshold_bootstrap.py, which re-estimates thresholds on
every draw). Only the DATA (returns) is block-resampled.

Targets (verification_manifest.md C34/C35, corroborated by
results/exports/README.md's F4/F5 session notes):
  MR-RW gap:  +6.6pp;  block p 0.211/0.31/0.35 (L=12/24/36); DK p ~= 0.18
  EXP-RW gap: -15.5pp; block p 0.083/0.049/0.026;            DK p ~= 0.040 (11 lags)

Methodology, matching the README's own F4/F5 log and p5_publag()'s existing
convention (not replaced with a "more rigorous" percentile bootstrap or
per-draw DK refit, which would very likely reproduce DIFFERENT numbers than
the manifest cites):
  - one joint regression fwd12 ~ const + MR_dummy + EXP_dummy (RW is the
    reference group), fit ONCE on the full sample with Driscoll-Kraay -
    that single fit gives both target DK coefficients directly.
  - block-bootstrap p-values via a NORMAL APPROXIMATION on the bootstrap
    standard error of a plain-OLS refit (2*norm.sf(|baseline coef|/SE)),
    same formula p5_publag() already uses - not a percentile bootstrap.
  - TRUE row-level block resampling over CALENDAR MONTHS, shared across all
    23 markets in the same draw (not 23 independent per-market resamples -
    tested first and rejected: resampling each market on its own destroys
    the cross-market correlation a block bootstrap needs to preserve, and
    gives absurdly small bootstrap SEs / near-zero p-values). Uses
    moving_block_indices (threshold_bootstrap.py) over the list of distinct
    months, then gathers every market's rows for each resampled month WITH
    REPEATS - unlike p5_publag()'s month-membership mask (np.isin), which
    silently collapses a month resampled twice into a single occurrence
    instead of duplicating its rows. That collapsing is the bug this
    script exists to fix.

Usage:  python scripts/fixed_label_bootstrap.py [--B 1000]
"""

import argparse
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                                          # noqa: E402
from horizon_episodes import load_all                   # noqa: E402
from min_regime_wald_recursive import dk_ols             # noqa: E402
from threshold_bootstrap import moving_block_indices     # noqa: E402


def market_frames(data):
    """Per-market, NaN-filtered (state, fwd12, month_ordinal) arrays, with
    the EXP dummy zeroed for EXCLUDED_EXP_MARKETS - the fixed labels this
    whole script treats as given."""
    frames = {}
    for mkt, d in data.items():
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        state = d["state"][ok]
        mr = (state == 1).astype(float)
        if mkt in config.EXCLUDED_EXP_MARKETS:
            ex = np.zeros(len(state), dtype=float)
        else:
            ex = (state == 2).astype(float)
        t = np.asarray([m.ordinal for m in d["months"]])[ok]
        frames[mkt] = {"mr": mr, "ex": ex, "fwd12": f[ok], "t": t}
    return frames


def pooled_design(frames, mr_arr_key="mr", ex_arr_key="ex", fwd_key="fwd12"):
    ys, Xs, ts = [], [], []
    for mkt, fr in frames.items():
        n = len(fr[fwd_key])
        ys.append(fr[fwd_key])
        Xs.append(np.column_stack([np.ones(n), fr[mr_arr_key], fr[ex_arr_key]]))
        ts.append(fr["t"])
    return np.concatenate(ys), np.vstack(Xs), np.concatenate(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=config.B_BOOTSTRAP)
    args = ap.parse_args()

    print(f"Fixed-label moving-block bootstrap | B={args.B} | "
         f"seed={config.SEED_FIXED_LABEL_BLOCK}\n")

    data = load_all()
    frames = market_frames(data)

    # Baseline: one joint DK fit on the full sample - gives both target coefficients.
    y, X, t = pooled_design(frames)
    baseline = dk_ols(y, X, t)
    # columns: 0=const, 1=MR, 2=EXP
    b_mr, b_ex = float(baseline.params[1]), float(baseline.params[2])
    p_mr_dk, p_ex_dk = float(baseline.pvalues[1]), float(baseline.pvalues[2])
    print(f"  baseline (DK, {config.DK_LAGS} lags): MR {b_mr:+.3f} (p={p_mr_dk:.4f})  "
         f"EXP {b_ex:+.3f} (p={p_ex_dk:.4f})")

    # Group ROW INDICES by calendar month, across the whole pooled dataset - this is
    # what makes the block resample a GLOBAL calendar-time resample (every market
    # shares the same resampled months, preserving cross-market correlation) rather
    # than 23 independent per-market resamples (which destroys it and gives absurdly
    # small bootstrap SEs, as tested and rejected before settling on this design).
    by_month = {}
    for i, mo in enumerate(t):
        by_month.setdefault(int(mo), []).append(i)
    months = np.asarray(sorted(by_month))
    row_lists = [np.asarray(by_month[m]) for m in months]

    rng = np.random.default_rng(config.SEED_FIXED_LABEL_BLOCK)
    from scipy import stats as sps  # noqa: E402

    rows = []
    for L in config.BLOCK_LENGTHS:
        mr_draws, ex_draws = [], []
        for _ in range(args.B):
            month_idx = moving_block_indices(len(months), L, rng)
            # TRUE resampling with repeats: a month drawn twice contributes its rows
            # twice, unlike p5_publag()'s np.isin membership mask (the bug this
            # script exists to fix), which would only ever include it once.
            idx = np.concatenate([row_lists[k] for k in month_idx])
            y_b, X_b = y[idx], X[idx]
            beta = np.linalg.lstsq(X_b, y_b, rcond=None)[0]
            mr_draws.append(float(beta[1]))
            ex_draws.append(float(beta[2]))

        mr_arr, ex_arr = np.asarray(mr_draws), np.asarray(ex_draws)
        mr_se, ex_se = mr_arr.std(ddof=1), ex_arr.std(ddof=1)
        p_mr = float(2 * sps.norm.sf(abs(b_mr) / mr_se)) if mr_se > 0 else ""
        p_ex = float(2 * sps.norm.sf(abs(b_ex) / ex_se)) if ex_se > 0 else ""
        rows.append({"gap": "MR_RW", "block_length": L, "coef": round(b_mr, 4),
                    "DK_p": round(p_mr_dk, 4), "block_SE": round(float(mr_se), 4),
                    "block_p": round(p_mr, 4) if p_mr != "" else "",
                    "seed": config.SEED_FIXED_LABEL_BLOCK, "B": args.B})
        rows.append({"gap": "EXP_RW", "block_length": L, "coef": round(b_ex, 4),
                    "DK_p": round(p_ex_dk, 4), "block_SE": round(float(ex_se), 4),
                    "block_p": round(p_ex, 4) if p_ex != "" else "",
                    "seed": config.SEED_FIXED_LABEL_BLOCK, "B": args.B})
        print(f"  L={L:>2}: MR block_p={p_mr:.4f}  EXP block_p={p_ex:.4f}"
             if p_mr != "" and p_ex != "" else f"  L={L}: degenerate SE")

    path = os.path.join(config.ensure_rebuilt_dir(), "fixed_label_bootstrap.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  -> fixed_label_bootstrap.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
