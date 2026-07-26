"""
Granger exogeneity tests for TAR trigger variables.

Tests whether each trigger (VIX, MCSI, BAA spread) is predetermined
with respect to equity returns — a prerequisite for valid regime classification.

Verdicts:
  ADMISSIBLE    — trigger does not Granger-cause returns (clean exogeneity)
  PREDETERMINED — Granger-causes returns but is temporally prior via lagging
                  (valid for use as trigger; mechanical link documented)
  REJECTED      — genuine endogeneity; trigger should not be used

Usage:
    python exogeneity.py           # full 27-market study
    python exogeneity.py validate  # known-answer validation pairs only
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

MONTHLY_PANEL = os.path.join(os.path.dirname(__file__), "..", "data", "combined", "monthly_panel.csv")
DAILY_PANEL   = os.path.join(os.path.dirname(__file__), "..", "data", "combined", "daily_panel.csv")


# ---------------------------------------------------------------------------
# Core Granger test
# ---------------------------------------------------------------------------

def granger_f_test(y_ret, z, n_lags):
    """
    F-test for Granger causality: does z Granger-cause y_ret?

    H0: lagged z coefficients are jointly zero (z does NOT Granger-cause y)

    Both y_ret and z must be stationary (use returns, not log levels).

    Parameters
    ----------
    y_ret  : np.ndarray — equity returns (np.diff of log prices)
    z      : np.ndarray — trigger series, same length as y_ret
    n_lags : int        — number of lags for both y and z

    Returns
    -------
    F, p_value
    """
    T = len(y_ret)
    start = n_lags
    n = T - start

    target = y_ret[start:]

    # Build lag matrices (both aligned to target)
    Y_lags = np.column_stack([y_ret[start - i - 1 : T - i - 1] for i in range(n_lags)])
    Z_lags = np.column_stack([z[start - i - 1 : T - i - 1]     for i in range(n_lags)])

    ones = np.ones((n, 1))

    # Restricted model: target ~ 1 + y_lags
    X_r    = np.hstack([ones, Y_lags])
    b_r, _, _, _ = np.linalg.lstsq(X_r, target, rcond=None)
    RSS_r  = float(np.dot(target - X_r @ b_r, target - X_r @ b_r))

    # Unrestricted model: target ~ 1 + y_lags + z_lags
    X_u    = np.hstack([ones, Y_lags, Z_lags])
    b_u, _, _, _ = np.linalg.lstsq(X_u, target, rcond=None)
    RSS_u  = float(np.dot(target - X_u @ b_u, target - X_u @ b_u))

    q  = n_lags                # number of restrictions (z lag coefficients)
    k  = X_u.shape[1]          # unrestricted parameter count
    df = n - k

    if df <= 0 or RSS_u <= 0:
        return np.nan, np.nan

    F       = ((RSS_r - RSS_u) / q) / (RSS_u / df)
    p_value = float(1.0 - stats.f.cdf(F, q, df))
    return float(F), p_value


def test_exogeneity(y_ret, z, n_lags, trigger_lag=0, alpha=0.05):
    """
    Test whether z (as used by the model) Granger-causes y_ret.

    trigger_lag : apply the same lag Farid applies before using z in the TAR model.
                  This tests the *predetermined* trigger, not the raw series.
                  0 for monthly triggers (MCSI), 1 for S&P500+VIX, 2 for FTSE100+VIX.

    Verdicts
    --------
    ADMISSIBLE    — z does not Granger-cause y at alpha (clean exogeneity)
    PREDETERMINED — z Granger-causes y but trigger_lag > 0, so it was observed
                    before the return it classifies. Model is still valid; document
                    the mechanical link (e.g. VIX derived from S&P500 options).
    REJECTED      — z Granger-causes y with trigger_lag=0 (genuine endogeneity)
    """
    # Apply trigger lag via array slicing (same as load_pair)
    if trigger_lag > 0:
        z     = z[:-trigger_lag]
        y_ret = y_ret[trigger_lag:]

    # Align lengths
    min_len = min(len(y_ret), len(z))
    y_ret = y_ret[-min_len:]
    z     = z[-min_len:]

    F, p = granger_f_test(y_ret, z, n_lags)
    if np.isnan(p) or p > alpha:
        verdict = 'ADMISSIBLE'
    elif trigger_lag > 0:
        verdict = 'PREDETERMINED'   # fails strict exogeneity but lag ensures timing validity
    else:
        verdict = 'REJECTED'
    return {'verdict': verdict, 'F': F, 'p_value': p, 'n_lags': n_lags,
            'trigger_lag': trigger_lag, 'T': min_len}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_returns(panel_path, equity_col, start, end):
    """Load log returns for an equity index from a panel CSV."""
    panel = pd.read_csv(panel_path, index_col="date", parse_dates=True)
    prices = panel[equity_col].dropna().loc[start:end]
    return np.diff(np.log(prices.values))


def _load_trigger(panel_path, trigger_col, start, end):
    """Load trigger series from a panel CSV."""
    panel = pd.read_csv(panel_path, index_col="date", parse_dates=True)
    return panel[trigger_col].dropna().loc[start:end].values


# ---------------------------------------------------------------------------
# Step 2a — Validate on known pairs
# ---------------------------------------------------------------------------

VALIDATION_PAIRS = [
    # (label,                panel,          equity_col,    trigger_col,  start,     end,       n_lags, trigger_lag)
    # VIX + MCSI — known answers from Farid's paper (all should be ADMISSIBLE/PREDETERMINED)
    ("S&P500  vs VIX",       DAILY_PANEL,   "eq_sp500",   "vix",        "1990-02", "2015-06", 5,      1),
    ("S&P500  vs MCSI",      MONTHLY_PANEL, "eq_sp500",   "mcsi",       "1978-01", "2015-06", 4,      0),
    ("FTSE100 vs VIX",       DAILY_PANEL,   "eq_ftse100", "vix",        "1990-02", "2015-06", 5,      2),
    ("FTSE100 vs MCSI",      MONTHLY_PANEL, "eq_ftse100", "mcsi",       "1984-01", "2015-06", 4,      0),
    # BAA credit spread — external economic indicator, not derived from equity prices
    ("S&P500  vs BAA sprd",  DAILY_PANEL,   "eq_sp500",   "baa_spread", "1990-02", "2015-06", 5,      1),
    ("FTSE100 vs BAA sprd",  DAILY_PANEL,   "eq_ftse100", "baa_spread", "1990-02", "2015-06", 5,      2),
]


def run_validation():
    """
    Run exogeneity test on 4 known pairs using the same trigger_lag as the TAR model.
    ADMISSIBLE or PREDETERMINED are both acceptable — REJECTED means genuine endogeneity.
    """
    print(f"{'Pair':<25}  {'Verdict':<14}  {'F':>7}  {'p-value':>8}  {'T':>6}  {'lag':>4}")
    print("-" * 72)

    all_ok = True
    for label, panel, equity_col, trigger_col, start, end, n_lags, tlag in VALIDATION_PAIRS:
        y_ret = _load_returns(panel, equity_col, start, end)
        z     = _load_trigger(panel, trigger_col, start, end)
        res   = test_exogeneity(y_ret, z, n_lags, trigger_lag=tlag)

        ok   = res['verdict'] in ('ADMISSIBLE', 'PREDETERMINED')
        if not ok:
            all_ok = False
        flag = "  ✓" if ok else "  ✗ UNEXPECTED"
        print(f"{label:<25}  {res['verdict']:<14}  {res['F']:>7.3f}  {res['p_value']:>8.4f}"
              f"  {res['T']:>6}  {tlag:>4}{flag}")

    print()
    if all_ok:
        print("Harness validated ✓  (PREDETERMINED = predetermined via lagging, model valid)")
    else:
        print("WARNING: REJECTED result — genuine endogeneity, debug before extending")


# ---------------------------------------------------------------------------
# Full study — all 27 markets × 3 triggers
# ---------------------------------------------------------------------------

# (trigger_label, panel, trigger_col, start, end, n_lags, trigger_lag)
# trigger_lag=1 for daily (VIX/BAA), 0 for monthly (MCSI)
FULL_TRIGGERS = [
    ("VIX",        DAILY_PANEL,   "vix",        "1990-02", "2015-06", 5, 1),
    ("MCSI",       MONTHLY_PANEL, "mcsi",        "1978-01", "2015-06", 4, 0),
    ("BAA spread", DAILY_PANEL,   "baa_spread",  "1990-02", "2015-06", 5, 1),
]


def run_full_study():
    """
    Run exogeneity test for all 27 markets against VIX, MCSI, and BAA spread.
    Prints a market × trigger table and pass-rate summary.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from market_config import MARKETS

    markets = list(MARKETS.keys())

    # Header
    trig_labels = [t[0] for t in FULL_TRIGGERS]
    print(f"{'Market':<14}  {'Country':<14}", end="")
    for lbl in trig_labels:
        print(f"  {lbl:<14}", end="")
    print()
    print("-" * (14 + 16 + len(trig_labels) * 16))

    counts = {lbl: 0 for lbl in trig_labels}
    totals = {lbl: 0 for lbl in trig_labels}

    for name in markets:
        country = MARKETS[name]['country']
        eq_col  = f"eq_{name}"
        row = f"{name:<14}  {country:<14}"

        for trig_label, panel, trig_col, start, end, n_lags, tlag in FULL_TRIGGERS:
            try:
                y_ret = _load_returns(panel, eq_col, start, end)
                z     = _load_trigger(panel, trig_col, start, end)
                if len(y_ret) < 20 or len(z) < 20:
                    cell = f"  {'SKIP (short)':<14}"
                else:
                    res  = test_exogeneity(y_ret, z, n_lags, trigger_lag=tlag)
                    v    = res['verdict']
                    ok   = v in ('ADMISSIBLE', 'PREDETERMINED')
                    totals[trig_label] += 1
                    if ok:
                        counts[trig_label] += 1
                    cell = f"  {v:<14}"
            except Exception:
                cell = f"  {'ERROR':<14}"
            row += cell

        print(row)

    # Summary
    print()
    print(f"{'Trigger':<14}  {'Pass':>6}  {'Total':>6}  {'Rate':>7}")
    print("-" * 38)
    for lbl in trig_labels:
        t = totals[lbl]
        c = counts[lbl]
        rate = f"{100*c/t:.0f}%" if t > 0 else "N/A"
        print(f"{lbl:<14}  {c:>6}  {t:>6}  {rate:>7}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        run_validation()
    else:
        run_full_study()
