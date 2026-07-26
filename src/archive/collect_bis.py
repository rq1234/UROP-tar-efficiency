"""
Parse BIS credit-to-GDP gap data and save per-market monthly interpolated series.

Source: data/sentiment/bis.csv
  BIS WS_CREDIT_GAP 1.0 — credit-to-GDP gaps in percentage points.
  Wide format: country-name rows x quarterly-date columns.
  skiprows=3 to skip BIS metadata header rows.

Interpolation: quarterly -> monthly via linear interpolation within each quarter.
The HP-filtered gap changes slowly; linear interpolation introduces negligible distortion.

Output: data/sentiment/bis_monthly_{market}.csv  (date, gap) for each of 17 markets.

Usage:
    cd src && python collect_bis.py
"""

import os
import sys
import pandas as pd

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
BIS_PATH      = os.path.join(SENTIMENT_DIR, "bis.csv")

COUNTRY_MAP = {
    "United States":  "sp500",
    "United Kingdom": "ftse100",
    "Germany":        "dax",
    "Japan":          "nikkei225",
    "China":          "shanghai",
    "Hong Kong SAR":  "hangseng",
    "India":          "nifty50",
    "Canada":         "tsx",
    "Australia":      "asx200",
    "Brazil":         "bovespa",
    "Spain":          "ibex35",
    "Singapore":      "sti",
    "South Africa":   "jse",
    "Netherlands":    "aex",
    "Mexico":         "ipc",
    "Israel":         "ta125",
    "Malaysia":       "klci",
    # excluded: cac40/France, kospi/Korea, smi/Switzerland, jkse/Indonesia
    # (failed quarterly exogeneity gate)
}


def load_bis_raw():
    """Load BIS CSV, return DataFrame indexed by quarterly dates, columns = country names."""
    raw = pd.read_csv(BIS_PATH, skiprows=3, index_col=0)
    raw.columns = pd.to_datetime(raw.columns)
    raw = raw.T.sort_index()
    raw = raw.apply(pd.to_numeric, errors="coerce")
    return raw


def interpolate_to_monthly(quarterly_series):
    """Linearly interpolate a quarterly gap series to month-end frequency."""
    s = quarterly_series.dropna().sort_index()
    if len(s) < 2:
        return None
    # Reindex to month-end, then interpolate
    monthly_idx = pd.date_range(s.index[0], s.index[-1], freq="ME")
    monthly = s.reindex(monthly_idx.union(s.index)).interpolate(method="linear")
    return monthly.reindex(monthly_idx)


def collect_bis():
    raw = load_bis_raw()
    print(f"BIS data: {len(raw)} quarterly obs  "
          f"({raw.index[0].strftime('%Y-%m-%d')} to {raw.index[-1].strftime('%Y-%m-%d')})")
    print(f"Saving monthly interpolated series for {len(COUNTRY_MAP)} markets...\n")

    os.makedirs(SENTIMENT_DIR, exist_ok=True)

    for bis_name, market in COUNTRY_MAP.items():
        if bis_name not in raw.columns:
            print(f"  WARNING: '{bis_name}' not in BIS data — skipping {market}")
            continue

        quarterly = raw[bis_name].dropna()
        monthly   = interpolate_to_monthly(quarterly)
        if monthly is None or monthly.empty:
            print(f"  {market:<14} ({bis_name}): insufficient data")
            continue

        monthly.name = "gap"
        monthly.index.name = "date"
        out_path = os.path.join(SENTIMENT_DIR, f"bis_monthly_{market}.csv")
        monthly.to_frame().to_csv(out_path)

        recent = monthly.iloc[-1]
        peak   = monthly.max()
        trough = monthly.min()
        print(f"  {market:<14} ({bis_name:<18})  "
              f"{len(monthly):>4} monthly obs  "
              f"peak={peak:>+7.1f}pp  trough={trough:>+7.1f}pp  "
              f"latest={recent:>+7.1f}pp ({monthly.index[-1].strftime('%Y-%m')})")

    print(f"\nDone. Files saved to {os.path.abspath(SENTIMENT_DIR)}")

    # Sanity checks on US gap
    us_path = os.path.join(SENTIMENT_DIR, "bis_monthly_sp500.csv")
    if os.path.exists(us_path):
        us = pd.read_csv(us_path, index_col=0, parse_dates=True)["gap"]
        housing_peak = us.loc["2005":"2007"].max()
        gfc_trough   = us.loc["2008":"2009"].min()
        print(f"\nUS sanity checks:")
        print(f"  Housing bubble peak (2005-07): {housing_peak:+.1f}pp  "
              f"{'OK' if housing_peak > 5 else 'WARNING: expected >5pp'}")
        print(f"  GFC trough (2008-09):          {gfc_trough:+.1f}pp  "
              f"{'OK' if gfc_trough < -2 else 'WARNING: expected <-2pp'}")


if __name__ == "__main__":
    collect_bis()
