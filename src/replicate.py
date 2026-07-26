"""
Replication of Tables 7 and 8 from Ahmed & Satchell (2018).

Table 7 — monthly equity indices with MCSI trigger.
Table 8 — daily equity indices with VIX trigger.

Usage:
    python replicate.py       # Table 7
    python replicate.py 8     # Table 8
"""

import os
import numpy as np
import pandas as pd
from estimate import find_optimal_thresholds, standard_errors

PANEL_PATH       = os.path.join(os.path.dirname(__file__), "..", "data", "combined", "monthly_panel.csv")
DAILY_PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "combined", "daily_panel.csv")


def load_pair(panel_path, equity_col, trigger_col, start, end,
              skip=0, trigger_lag=0):
    """
    Load (y, z) arrays from a panel CSV for a given date window.

    y = log of equity price
    z = trigger series (e.g. MCSI or VIX)

    trigger_lag : int — align trigger so z[t] = trigger[t - trigger_lag].
                  Applied via array slicing AFTER dropna, so pre-existing NaN
                  holes in the trigger do not propagate into the lagged series.
                  1 for S&P500+VIX (daily), 2 for FTSE100+VIX (London timezone).

    skip : int — drop this many observations from the start after all alignment.
    """
    panel = pd.read_csv(panel_path, index_col="date", parse_dates=True)
    # dropna FIRST so pre-existing NaN gaps don't propagate during lag slicing
    pair  = panel[[equity_col, trigger_col]].dropna()
    pair  = pair.loc[start:end]
    log_p = np.log(pair[equity_col].values).astype(float)
    trig  = pair[trigger_col].values.astype(float)
    # Apply lag via array slicing — loses exactly trigger_lag observations
    if trigger_lag > 0:
        y = log_p[trigger_lag:]
        z = trig[:-trigger_lag]
    else:
        y = log_p
        z = trig
    if skip > 0:
        y = y[skip:]
        z = z[skip:]
    return y, z


# ---------------------------------------------------------------------------
# Table 7 specifications
#
# Each row: (equity_col, start, end, z_min, z_max, gridlength, min_gap,
#            spec, mode, label)
#
# spec  1 = switching drift   (gridsearchchk.m intercept=1)
# spec  2 = constant drift    (gridsearchchk.m intercept=2)
# spec  0 = no drift          (gridsearchchk.m intercept=0)
#
# mode 'returns' — both indices: Δy(t) = α + β·y(t-1) + ε
# Paper Section 4.2: returns used for both to ensure stationarity and SE consistency.
#
# Grid range [57, 110] and gridlength=100 taken directly from optimalz.m /
# optimalzchk.m. min_gap=4 matches j+4 in MATLAB's inner loop.
# ---------------------------------------------------------------------------
TABLE7_SPECS = [
    # (equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, trigger_lag)
    ("eq_sp500",   "1978-01", "2015-06", 57, 110, 100, 4, 1, "returns", "S&P500  w/mov drift",   0, 0),
    ("eq_sp500",   "1978-01", "2015-06", 57, 110, 100, 4, 2, "returns", "S&P500  w/const drift", 0, 0),
    ("eq_sp500",   "1978-01", "2015-06", 57, 110, 100, 4, 0, "returns", "S&P500  w/out drift",   0, 0),
    ("eq_ftse100", "1984-01", "2015-06", 57, 110, 100, 4, 1, "returns", "FTSE100 w/mov drift",   0, 0),
    ("eq_ftse100", "1984-01", "2015-06", 57, 110, 100, 4, 2, "returns", "FTSE100 w/const drift", 0, 0),
    ("eq_ftse100", "1984-01", "2015-06", 57, 110, 100, 4, 0, "returns", "FTSE100 w/out drift",   0, 0),
]

# ---------------------------------------------------------------------------
# Table 8 specifications — daily S&P500 and FTSE100 with VIX trigger
#
# Grid params from optimalvix.m: z_min=10, z_max=70, gridlength=200, min_gap=6 (j+6).
# VIX lag: 1 day for S&P500, 2 days for FTSE100 (London closes before US VIX publishes).
# ---------------------------------------------------------------------------
TABLE8_SPECS = [
    # (equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, trigger_lag)
    ("eq_sp500",   "1990-02", "2015-06", 10, 70, 200, 6, 1, "returns", "S&P500  w/mov drift",   0, 1),
    ("eq_sp500",   "1990-02", "2015-06", 10, 70, 200, 6, 2, "returns", "S&P500  w/const drift", 0, 1),
    ("eq_sp500",   "1990-02", "2015-06", 10, 70, 200, 6, 0, "returns", "S&P500  w/out drift",   0, 1),
    ("eq_ftse100", "1990-02", "2015-06", 10, 70, 200, 6, 1, "returns", "FTSE100 w/mov drift",   0, 2),
    ("eq_ftse100", "1990-02", "2015-06", 10, 70, 200, 6, 2, "returns", "FTSE100 w/const drift", 0, 2),
    ("eq_ftse100", "1990-02", "2015-06", 10, 70, 200, 6, 0, "returns", "FTSE100 w/out drift",   0, 2),
]


def _fmt_beta(beta, se, tstat, n, T):
    """Format a beta with SE in parentheses, significance star, and obs %."""
    import math
    pct = f"{100 * n / T:.0f}%"
    if math.isnan(se):
        return f"{beta:8.4f}   (N/A ) [{pct:>4}]"
    if abs(tstat) >= 1.96:
        sig = "**"
    elif abs(tstat) >= 1.645:
        sig = "*"
    else:
        sig = ""
    return f"{beta:8.4f}{sig:<2} ({se:.4f}) [{pct:>4}]"


def replicate_table7(panel_path=PANEL_PATH):
    """Run all six rows of Table 7 and print results for comparison."""
    trigger = "mcsi"

    print(f"{'Label':<25}  {'c1':>5} {'c2':>6}  "
          f"{'State 1 (MR)':<22}  {'State 2 (RW)':<22}  {'State 3 (EXP)':<22}")
    print(f"{'':25}  {'':5} {'':6}  "
          f"{'α  β**(SE)[n%]':<22}  {'α  β(SE)[n%]':<22}  {'α  β**(SE)[n%]':<22}")
    print("-" * 105)

    for equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, tlag in TABLE7_SPECS:
        y, z = load_pair(panel_path, equity_col, trigger, start, end, skip=skip, trigger_lag=tlag)
        T = len(y)
        print(f"  {label}: T={T}", flush=True)

        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, mode)
        res = standard_errors(y, z, opt['c1'], opt['c2'], spec, mode)

        b1, b2, b3 = res['beta1'], res['beta2'], res['beta3']

        # Alpha: for spec=2 shared drift stored in alpha2 (RW slot); show in MR column
        a1 = res['alpha2'] if spec == 2 else res['alpha1']
        a2 = 0.0          if spec == 2 else res['alpha2']
        a3 = res['alpha3']

        s1 = _fmt_beta(b1, res['se1'], res['tstat1'], res['n1'], T)
        s2 = _fmt_beta(b2, res['se2'], res['tstat2'], res['n2'], T)
        s3 = _fmt_beta(b3, res['se3'], res['tstat3'], res['n3'], T)

        print(f"{label:<25}  {opt['c1']:>5.1f} {opt['c2']:>6.1f}  "
              f"{a1:7.4f} {s1}  {a2:7.4f} {s2}  {a3:7.4f} {s3}")
        print()


def replicate_table8(panel_path=DAILY_PANEL_PATH):
    """Run all six rows of Table 8 (daily S&P500 and FTSE100 with VIX trigger)."""
    trigger = "vix"

    print(f"{'Label':<25}  {'c1':>5} {'c2':>6}  "
          f"{'State 1 (MR)':<22}  {'State 2 (RW)':<22}  {'State 3 (EXP)':<22}")
    print(f"{'':25}  {'':5} {'':6}  "
          f"{'α  β**(SE)[n%]':<22}  {'α  β(SE)[n%]':<22}  {'α  β**(SE)[n%]':<22}")
    print("-" * 105)

    for equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, tlag in TABLE8_SPECS:
        y, z = load_pair(panel_path, equity_col, trigger, start, end,
                         skip=skip, trigger_lag=tlag)
        T = len(y)
        print(f"  {label}: T={T}, z range [{z.min():.1f}, {z.max():.1f}]", flush=True)

        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, mode)
        res = standard_errors(y, z, opt['c1'], opt['c2'], spec, mode)

        b1, b2, b3 = res['beta1'], res['beta2'], res['beta3']
        a1 = res['alpha2'] if spec == 2 else res['alpha1']
        a2 = 0.0          if spec == 2 else res['alpha2']
        a3 = res['alpha3']

        s1 = _fmt_beta(b1, res['se1'], res['tstat1'], res['n1'], T)
        s2 = _fmt_beta(b2, res['se2'], res['tstat2'], res['n2'], T)
        s3 = _fmt_beta(b3, res['se3'], res['tstat3'], res['n3'], T)

        print(f"{label:<25}  {opt['c1']:>5.1f} {opt['c2']:>6.1f}  "
              f"{a1:7.4f} {s1}  {a2:7.4f} {s2}  {a3:7.4f} {s3}")
        print()


if __name__ == "__main__":
    import sys
    table = sys.argv[1] if len(sys.argv) > 1 else "7"
    if table == "8":
        replicate_table8()
    else:
        replicate_table7()
