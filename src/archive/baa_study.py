"""
S&P500 returns with BAA credit spread as trigger â€” exploratory analysis.

Tests whether the TAR model, run with BAA spread LEVELS as trigger (consistent
with Farid's levels approach), identifies distinct regimes during:
  - 2005-07: credit euphoria (BAA spread at historic lows ~1.5%)
  - 2008-09: financial crisis (BAA spread spiked to ~5-6%)

Uses returns formulation (mode='returns') matching Table 8 setup.

Usage:
    cd src
    python baa_study.py
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from replicate import DAILY_PANEL_PATH, load_pair
from estimate import find_optimal_thresholds, standard_errors, _assign_states

EQUITY  = "eq_sp500"
TRIGGER = "baa_spread"
START   = "1990-02"
END     = "2015-06"
TLAG    = 1
MODE    = "returns"
GRIDLEN = 200
MIN_GAP = 6


def _regime_dates(y, z, c1, c2, panel_path, start, end):
    """Reconstruct date-indexed regime classification from the clean pair."""
    panel = pd.read_csv(panel_path, index_col="date", parse_dates=True)
    pair  = panel[[EQUITY, TRIGGER]].dropna().loc[start:end]

    state = _assign_states(z[1:], c1, c2)
    n     = len(state)
    dates = pair.index[1 : n + 1]

    df = pd.DataFrame({"trigger": z[1 : n + 1], "state": state}, index=dates)
    df["regime"] = df["state"].map({1: "MR", 0: "RW", 2: "EXP"})
    return df


def episode_overlap(regime_df, label, period_start, period_end):
    """Print regime breakdown for a named episode."""
    ep    = regime_df.loc[period_start:period_end]
    total = len(ep)
    if total == 0:
        print(f"  {label}: no data in window")
        return
    print(f"\n  {label}  ({period_start} â†’ {period_end},  {total} trading days)")
    for regime in ["MR", "RW", "EXP"]:
        n = (ep["regime"] == regime).sum()
        bar = "â–ˆ" * int(20 * n / total)
        print(f"    {regime}: {n:4d} ({100*n/total:5.1f}%)  {bar}")
    dominant = ep["regime"].value_counts().index[0]
    print(f"    â†’ dominant regime: {dominant}")


def run_spec(spec, label):
    """Run grid search + episode overlap for one drift specification."""
    print(f"\n{'='*60}")
    print(f"  spec={spec}  ({label})  trigger=BAA levels")
    print(f"{'='*60}")

    y, z = load_pair(DAILY_PANEL_PATH, EQUITY, TRIGGER, START, END, trigger_lag=TLAG)
    print(f"  T={len(y)},  BAA range [{z.min():.3f}, {z.max():.3f}]")

    z_min = max(0.3, z.min() - 0.1)
    z_max = min(8.0, z.max() + 0.1)

    print(f"  Grid: [{z_min:.2f}, {z_max:.2f}]  n={GRIDLEN}  min_gap={MIN_GAP}")
    print("  Searching...", flush=True)

    opt = find_optimal_thresholds(y, z, z_min, z_max, GRIDLEN, MIN_GAP, spec, MODE)
    res = standard_errors(y, z, opt["c1"], opt["c2"], spec, MODE)

    T = len(y)
    print(f"\n  Optimal thresholds:  c1={opt['c1']:.3f}  c2={opt['c2']:.3f}")
    print(f"  {'State':<6}  {'Î²':>8}  {'SE':>8}  {'n':>5}  {'%':>6}")
    print(f"  {'-'*42}")
    for s, beta, se, n in [
        ("MR",  res["beta1"], res["se1"], res["n1"]),
        ("RW",  res["beta2"], res["se2"], res["n2"]),
        ("EXP", res["beta3"], res["se3"], res["n3"]),
    ]:
        se_str = f"{se:.4f}" if not np.isnan(se) else "N/A"
        print(f"  {s:<6}  {beta:>8.4f}  {se_str:>8}  {n:>5}  {100*n/T:>5.1f}%")

    counts = [res["n1"], res["n2"], res["n3"]]
    if max(counts) / T > 0.96 or min(counts) / T < 0.02:
        print("\n  âš   DEGENERATE REGIME: one state dominates")
    else:
        print("\n  Regime counts look reasonable âœ“")

    regime_df = _regime_dates(y, z, opt["c1"], opt["c2"], DAILY_PANEL_PATH, START, END)
    print("\n  Episode overlap:")
    episode_overlap(regime_df, "Credit euphoria", "2005-01", "2007-12")
    episode_overlap(regime_df, "Financial crisis", "2008-01", "2009-12")
    episode_overlap(regime_df, "Post-crisis",      "2010-01", "2012-12")

    return opt, res, regime_df


if __name__ == "__main__":
    for spec, label in [(2, "constant drift"), (1, "switching drift"), (0, "no drift")]:
        run_spec(spec, label)

