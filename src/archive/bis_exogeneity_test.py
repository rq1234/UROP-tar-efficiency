"""
BIS Credit-to-GDP Gap â€” Quarterly Exogeneity Gate Test

Tests whether the BIS credit-to-GDP gap is exogenous to equity returns
at quarterly frequency. This is the gate test before any monthly interpolation:
if equity returns Granger-cause the credit gap, the gap is endogenous and
useless as a TAR trigger.

Two Granger tests per market:
  Reverse (gate): does equity return predict delta(credit gap)?  -> PASS = exogenous
  Forward (diagnostic): does delta(credit gap) predict equity returns? -> PASS = informative

BIS data: data/sentiment/bis.csv
  Wide format, quarterly dates as columns, country names as rows.
  skiprows=3 to skip BIS metadata header.

Usage:
    cd src && python bis_exogeneity_test.py
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from exogeneity  import granger_f_test
from replicate   import PANEL_PATH
from market_config import MARKETS
from bubble_now  import TABLES_DIR

BIS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment", "bis.csv")

# Map BIS country names -> equity market IDs
COUNTRY_MAP = {
    "United States":    "sp500",
    "United Kingdom":   "ftse100",
    "Germany":          "dax",
    "France":           "cac40",
    "Japan":            "nikkei225",
    "China":            "shanghai",
    "Hong Kong SAR":    "hangseng",
    "Korea":            "kospi",
    "India":            "nifty50",
    "Canada":           "tsx",
    "Australia":        "asx200",
    "Brazil":           "bovespa",
    "Spain":            "ibex35",
    "Switzerland":      "smi",
    "Singapore":        "sti",
    "Chinese Taipei":   "twse",
    "South Africa":     "jse",
    "Netherlands":      "aex",
    "Mexico":           "ipc",
    "Indonesia":        "jkse",
    "Israel":           "ta125",
    "Malaysia":         "klci",
}

N_LAGS = 4   # 4 quarters = 1 year lookback
ALPHA  = 0.05


def load_bis():
    """Return BIS credit-to-GDP gap as a DataFrame: index=quarter-end date, columns=market IDs."""
    raw = pd.read_csv(BIS_PATH, skiprows=3, index_col=0)
    # Dates are columns; values are credit gap in pp
    raw.columns = pd.to_datetime(raw.columns)
    raw = raw.T.sort_index()          # index = date, columns = country names
    raw = raw.apply(pd.to_numeric, errors="coerce")

    # Keep only countries we can map to equity markets
    mapped = {}
    available = []
    for bis_name, market in COUNTRY_MAP.items():
        if bis_name in raw.columns:
            mapped[market] = raw[bis_name].dropna()
            available.append(bis_name)
        else:
            print(f"  WARNING: '{bis_name}' not found in BIS data")

    print(f"Loaded BIS data: {len(raw)} quarterly obs "
          f"({raw.index[0].strftime('%Y-%m-%d')} to {raw.index[-1].strftime('%Y-%m-%d')})")
    print(f"Matched {len(mapped)}/22 markets ({len(available)} BIS country names found)")
    return mapped


def load_quarterly_equity():
    """Return quarterly log-returns for all 23 equity markets (sum of monthly log-returns)."""
    panel = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    quarterly = {}
    for market in MARKETS:
        col = f"eq_{market}"
        if col not in panel.columns:
            continue
        prices = panel[col].dropna()
        monthly_ret = np.log(prices / prices.shift(1)).dropna()
        # Sum monthly log-returns to quarterly
        q_ret = monthly_ret.resample("QE").sum()
        q_ret = q_ret[q_ret != 0].dropna()   # drop quarters with no data
        quarterly[market] = q_ret
    return quarterly


def run_tests():
    print(f"\n{'='*75}")
    print("BIS CREDIT-TO-GDP GAP â€” QUARTERLY EXOGENEITY GATE")
    print("Reverse test: equity return -> delta(gap)  [PASS = gap is exogenous]")
    print("Forward test: delta(gap) -> equity return  [PASS = gap is informative]")
    print(f"n_lags={N_LAGS}  alpha={ALPHA}")
    print(f"{'='*75}")
    print(f"{'Market':<14} {'Country':<18} {'T':>4}  "
          f"{'Rev-F':>7} {'Rev-p':>7} {'Gate':>5}  "
          f"{'Fwd-F':>7} {'Fwd-p':>7} {'Predictive'}")
    print("-" * 80)

    bis_data = load_bis()
    equity_q = load_quarterly_equity()

    rows = []
    for market, info in MARKETS.items():
        if market not in bis_data or market not in equity_q:
            continue

        gap   = bis_data[market]
        eq    = equity_q[market]

        # Align on common quarterly dates
        df = pd.DataFrame({"eq": eq, "gap": gap}).dropna()
        if len(df) < 20:
            print(f"{market:<14} {info['country']:<18} {'<20 obs â€” skip':>50}")
            continue

        y_eq  = df["eq"].values
        z_gap = np.diff(df["gap"].values)   # delta(gap) for stationarity

        # Trim to same length after differencing
        y_eq_trim = y_eq[1:]
        n = min(len(y_eq_trim), len(z_gap))
        y_eq_trim = y_eq_trim[-n:]
        z_gap     = z_gap[-n:]

        try:
            rev_F, rev_p = granger_f_test(z_gap, y_eq_trim, N_LAGS)
            fwd_F, fwd_p = granger_f_test(y_eq_trim, z_gap, N_LAGS)
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")
            continue

        gate       = "PASS" if rev_p > ALPHA else "FAIL"
        predictive = "YES " if fwd_p < ALPHA else "no  "

        print(f"{market:<14} {info['country']:<18} {n:>4}  "
              f"{rev_F:>7.3f} {rev_p:>7.4f} {gate:>5}  "
              f"{fwd_F:>7.3f} {fwd_p:>7.4f} {predictive}")

        rows.append({
            "market":      market,
            "country":     info["country"],
            "T":           n,
            "rev_F":       round(rev_F, 3),
            "rev_p":       round(rev_p, 4),
            "gate":        gate,
            "fwd_F":       round(fwd_F, 3),
            "fwd_p":       round(fwd_p, 4),
            "predictive":  predictive.strip(),
        })

    # Summary
    passed = sum(1 for r in rows if r["gate"] == "PASS")
    pred   = sum(1 for r in rows if r["predictive"] == "YES")
    print(f"\n{passed}/{len(rows)} markets pass exogeneity gate.")
    print(f"{pred}/{len(rows)} markets show forward predictability from credit gap.")

    # Save
    os.makedirs(TABLES_DIR, exist_ok=True)
    df_out = pd.DataFrame(rows)
    out_path = os.path.join(TABLES_DIR, "bis_exogeneity_quarterly.csv")
    df_out.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    if passed == len(rows):
        print("\nAll markets pass -> credit gap is exogenous. "
              "Proceed to monthly interpolation and TAR pipeline.")
    elif passed == 0:
        print("\nNo markets pass -> credit gap is endogenous to equity returns. "
              "Do not proceed to TAR estimation.")
    else:
        print(f"\nMixed results: proceed with the {passed} passing markets only.")


if __name__ == "__main__":
    run_tests()

