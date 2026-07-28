"""
Fetch Shiller CAPE (Cyclically Adjusted Price-to-Earnings Ratio, P/E10) from Yale.

CAPE = current price / 10-year average of real earnings.
High CAPE = expensive / overvalued markets = bubble risk.
No sign convention change needed (high CAPE maps directly to EXP state in the TAR model).

Source: Robert Shiller's online data, updated monthly.
URL: http://www.econ.yale.edu/~shiller/data/ie_data.xls
Sheet: "Data", skiprows=7.
Date column format: YYYY.MM stored as a float (e.g. 1990.01 = Jan 1990, 1990.10 = Oct 1990).
CAPE column header: "P/E10" (also referred to as CAPE or Shiller PE).

Output: data/sentiment/cape_monthly.csv  (date, cape)

Usage:
    cd src && python collect_cape.py
"""

import os
import sys
import numpy as np
import pandas as pd

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentiment")
CAPE_PATH     = os.path.join(SENTIMENT_DIR, "cape_monthly.csv")
URL           = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"


def _parse_shiller_date(d):
    """
    Convert Shiller date float (e.g. 1990.01 or 1990.1) to month-end Timestamp.
    Format is YYYY.MM where MM is zero-padded; as a float Oct = .10 → .1.
    """
    s = f"{float(d):.2f}"   # ensures "1990.10" not "1990.1"
    yr = int(s[:4])
    mo = int(s[5:7])
    if mo < 1 or mo > 12:
        return pd.NaT
    return pd.Timestamp(year=yr, month=mo, day=1) + pd.offsets.MonthEnd(0)


def collect_cape():
    print(f"Fetching Shiller IE data from:\n  {URL}")
    print("(This may take a moment — ~2 MB Excel file) ...", end="", flush=True)

    try:
        raw = pd.read_excel(URL, sheet_name="Data", skiprows=7, engine="xlrd")
    except Exception:
        # xlrd only supports .xls; openpyxl handles .xlsx
        raw = pd.read_excel(URL, sheet_name="Data", skiprows=7)

    print(f" loaded {len(raw)} rows, {len(raw.columns)} columns")

    # -------------------------------------------------------------------------
    # Identify date and CAPE columns
    # -------------------------------------------------------------------------
    # Shiller's spreadsheet has unnamed columns; the first is always the date
    # and the CAPE column is labelled "P/E10" or "CAPE" depending on vintage.
    date_col = raw.columns[0]
    cape_col  = None
    for c in raw.columns:
        if str(c).strip().upper() in ("P/E10", "CAPE", "CYCLICALLY ADJUSTED P/E"):
            cape_col = c
            break
    if cape_col is None:
        # Fall back: look for a column named something like "P/E10*"
        for c in raw.columns:
            if "10" in str(c) and ("P/E" in str(c).upper() or "PE" in str(c).upper()):
                cape_col = c
                break
    if cape_col is None:
        raise ValueError(
            f"Could not find CAPE (P/E10) column. Available: {list(raw.columns)}"
        )

    print(f"  Date column : '{date_col}'")
    print(f"  CAPE column : '{cape_col}'")

    # -------------------------------------------------------------------------
    # Parse and clean
    # -------------------------------------------------------------------------
    df = raw[[date_col, cape_col]].copy()
    df.columns = ["date_raw", "cape"]
    df = df.dropna(subset=["date_raw"])

    # Drop non-numeric date rows (header repetitions, notes at the bottom)
    df = df[pd.to_numeric(df["date_raw"], errors="coerce").notna()].copy()
    df["cape"] = pd.to_numeric(df["cape"], errors="coerce")

    df["date"] = df["date_raw"].apply(_parse_shiller_date)
    df = df.dropna(subset=["date", "cape"])
    df = df.set_index("date")[["cape"]].sort_index()

    # Keep full history (from 1871); the study will slice to 1990+
    df.index.name = "date"

    print(f"\nMonthly CAPE: {len(df)} obs  "
          f"({df.index[0].strftime('%Y-%m')} to {df.index[-1].strftime('%Y-%m')})")
    print(f"  mean={df['cape'].mean():.2f}  std={df['cape'].std():.2f}  "
          f"min={df['cape'].min():.2f}  max={df['cape'].max():.2f}")

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------
    os.makedirs(SENTIMENT_DIR, exist_ok=True)
    df.to_csv(CAPE_PATH)
    print(f"Saved:   {os.path.abspath(CAPE_PATH)}")

    # -------------------------------------------------------------------------
    # Sanity checks (1990+ subsample)
    # -------------------------------------------------------------------------
    sub = df.loc["1990":]
    print("\nSanity checks (1990–present):")

    dotcom_peak = sub.loc["1999":"2001", "cape"].max()
    print(f"  Dot-com peak > 40?       "
          f"{dotcom_peak > 40:>5}   (1999–2001 max={dotcom_peak:.1f})")

    gfc_trough = sub.loc["2008":"2010", "cape"].min()
    print(f"  GFC trough < 15?         "
          f"{gfc_trough < 15:>5}   (2008–2010 min={gfc_trough:.1f})")

    current = sub.iloc[-1]["cape"]
    print(f"  Current reading > 30?    "
          f"{current > 30:>5}   (latest={current:.1f}  as of {sub.index[-1].strftime('%Y-%m')})")

    return df


if __name__ == "__main__":
    collect_cape()
