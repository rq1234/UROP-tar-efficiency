from dotenv import load_dotenv
load_dotenv()

"""
========================================================================
DATA COLLECTOR  —  cross-market efficiency project
========================================================================
Fetches fresh data from free online sources and stores:

    data/equity/      DAILY closes, one CSV per index     (date, price)
    data/sentiment/   at NATIVE frequency per series      (date, value)
    data/combined/    two panels:
                        monthly_panel.csv  — equity month-end + monthly triggers
                        daily_panel.csv    — equity daily    + daily triggers

TWO FREQUENCIES ARE INTENTIONAL (matches the paper):
    Monthly : equity resampled to month-end  +  MCSI and other monthly triggers
              (Table 7 equivalent — limited by MCSI's monthly publication)
    Daily   : equity at native daily close   +  VIX and other daily triggers
              (Table 8 equivalent — more observations, higher-frequency)

------------------------------------------------------------------------
"""

import os
import pandas as pd

EQUITY_DIR    = "data/equity"
SENTIMENT_DIR = "data/sentiment"
COMBINED_DIR  = "data/combined"

# All configuration lives in market_config.py — edit there, not here
from market_config import MARKETS, SENTIMENT_MONTHLY, SENTIMENT_DAILY
EQUITY_INDICES = {name: m["ticker"] for name, m in MARKETS.items()}


# ========================================================================
# FETCHERS
# ========================================================================

def fetch_equity(name, ticker):
    """Fetch daily closes from Yahoo Finance. Returns (date, price) DataFrame."""
    import yfinance as yf
    df = yf.download(ticker, start="1975-01-01", interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df[["Close"]].rename(columns={"Close": "price"})
    out.index.name = "date"
    return out.dropna()


def fetch_fred(name, code, api_key):
    """Fetch any FRED series at its native frequency."""
    from fredapi import Fred
    fred = Fred(api_key=api_key)
    s = fred.get_series(code, observation_start="1975-01-01")
    s.index = pd.to_datetime(s.index)
    s = s.dropna().sort_index()
    out = s.to_frame(name=name)
    out.index.name = "date"
    return out


# ========================================================================
# PANEL BUILDERS
# ========================================================================

def to_month_end(daily_series):
    """
    Resample a daily price series to month-end closing value.
    This is what the paper uses: the last trading day of each month.
    """
    return daily_series.resample("ME").last().dropna()


def build_monthly_panel(equity_frames, sentiment_frames):
    """
    Monthly panel: equity month-end closes + monthly triggers.
    Columns: eq_<name> for equities, trigger name for sentiments.
    """
    cols = {}
    for name, df in equity_frames.items():
        monthly = to_month_end(df["price"])
        monthly.index = monthly.index + pd.offsets.MonthEnd(0)  # force strict ME
        monthly = monthly.groupby(monthly.index).last()  # drop any duplicate dates
        cols[f"eq_{name}"] = monthly
    for name, df in sentiment_frames.items():
        # snap monthly trigger to month-end convention too
        s = df.iloc[:, 0]
        s.index = s.index + pd.offsets.MonthEnd(0)
        s = s.groupby(s.index).last()  # drop any duplicate dates
        cols[name] = s

    if not cols:
        return None
    panel = pd.DataFrame(cols).sort_index()
    panel.index.name = "date"
    return panel


def build_daily_panel(equity_frames, sentiment_frames):
    """
    Daily panel: equity daily closes + daily triggers.
    Inner join on trading days where both equity and trigger exist.
    """
    cols = {}
    for name, df in equity_frames.items():
        cols[f"eq_{name}"] = df["price"]
    for name, df in sentiment_frames.items():
        cols[name] = df.iloc[:, 0]

    if not cols:
        return None
    panel = pd.DataFrame(cols).sort_index()
    panel.index.name = "date"
    return panel


# ========================================================================
# MAIN
# ========================================================================

def print_summary(name, df, freq):
    n = len(df)
    start = df.index.min().date()
    end = df.index.max().date()
    print(f"  {name:<14} {freq:<8} {n:>5} obs  {start} -> {end}")


def collect_all(fred_api_key=None):
    os.makedirs(EQUITY_DIR,    exist_ok=True)
    os.makedirs(SENTIMENT_DIR, exist_ok=True)
    os.makedirs(COMBINED_DIR,  exist_ok=True)

    key = fred_api_key or os.environ.get("FRED_API_KEY")

    # ---- Step 1: Equity indices (daily) --------------------------------
    print("=" * 65)
    print("STEP 1 — Equity indices (stored daily)")
    print("=" * 65)
    equity_frames = {}
    for name, ticker in EQUITY_INDICES.items():
        try:
            df = fetch_equity(name, ticker)
        except Exception as e:
            print(f"  {name:<14} FAILED: {e}")
            continue

        path = f"{EQUITY_DIR}/{name}.csv"
        df.to_csv(path)
        equity_frames[name] = df
        print_summary(f"{name}", df, "daily")

    # ---- Step 2: Monthly sentiment / triggers --------------------------
    print("\n" + "=" * 65)
    print("STEP 2 — Monthly sentiment triggers (FRED)")
    print("=" * 65)
    monthly_sentiment = {}
    if key:
        for name, code in SENTIMENT_MONTHLY.items():
            try:
                df = fetch_fred(name, code, key)
                df.to_csv(f"{SENTIMENT_DIR}/{name}_monthly.csv")
                monthly_sentiment[name] = df
                print_summary(name, df, "monthly")
            except Exception as e:
                print(f"  {name:<14} FAILED: {e}")
    else:
        print("  No FRED_API_KEY set — skipping monthly FRED series.")

    # ---- Step 3: Daily sentiment / triggers ----------------------------
    print("\n" + "=" * 65)
    print("STEP 3 — Daily triggers (FRED)")
    print("=" * 65)
    daily_sentiment = {}
    if key:
        for name, code in SENTIMENT_DAILY.items():
            try:
                df = fetch_fred(name, code, key)
                df.to_csv(f"{SENTIMENT_DIR}/{name}_daily.csv")
                daily_sentiment[name] = df
                print_summary(name, df, "daily")
            except Exception as e:
                print(f"  {name:<14} FAILED: {e}")
    else:
        print("  No FRED_API_KEY set — skipping daily FRED series.")

    # ---- Step 4: Build combined panels ---------------------------------
    print("\n" + "=" * 65)
    print("STEP 4 — Combined panels")
    print("=" * 65)

    # Monthly panel: equity month-end + monthly triggers
    monthly_panel = build_monthly_panel(equity_frames, monthly_sentiment)
    if monthly_panel is not None:
        path = f"{COMBINED_DIR}/monthly_panel.csv"
        monthly_panel.to_csv(path)
        full = monthly_panel.dropna()
        print(f"  monthly_panel.csv")
        print(f"    {monthly_panel.shape[0]} months x {monthly_panel.shape[1]} series")
        print(f"    Full overlap (all series): {full.index.min().date() if len(full) else 'none'}"
              f" -> {full.index.max().date() if len(full) else 'none'}")
        print(f"    Columns: {list(monthly_panel.columns)}")

    print()

    # Daily panel: equity daily + daily triggers
    daily_panel = build_daily_panel(equity_frames, daily_sentiment)
    if daily_panel is not None:
        path = f"{COMBINED_DIR}/daily_panel.csv"
        daily_panel.to_csv(path)
        full = daily_panel.dropna()
        print(f"  daily_panel.csv")
        print(f"    {daily_panel.shape[0]} trading days x {daily_panel.shape[1]} series")
        print(f"    Full overlap (all series): {full.index.min().date() if len(full) else 'none'}"
              f" -> {full.index.max().date() if len(full) else 'none'}")
        print(f"    Columns: {list(daily_panel.columns)}")

    print("\nDone. Re-run any time to refresh to latest available data.")
    return equity_frames, monthly_sentiment, daily_sentiment


if __name__ == "__main__":
    collect_all()
