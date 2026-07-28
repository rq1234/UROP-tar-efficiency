"""
Fetch ANFCI (Chicago Fed Adjusted National Financial Conditions Index) from FRED.

ANFCI is a weekly z-score measuring US financial conditions, business-cycle adjusted.
Positive = tight conditions (stress). Negative = loose conditions (complacency).
Updated weekly (Wednesday release for the prior Friday week-end).

FRED series: ANFCI  â€”  available from 1971-01-07 to present.

Aggregation: weekly â†’ monthly by taking the last weekly value in each calendar month.

NOTE: anfci_study.py negates ANFCI at load time (z = -ANFCI) so that:
  High z = loose conditions = bubble risk â†’ EXP state
  Low z  = tight conditions = crisis     â†’ MR state

Output: data/sentiment/anfci_monthly.csv  (date, anfci)

Usage:
    cd src && python collect_anfci.py
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from collect_data import fetch_fred

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentiment")
ANFCI_PATH    = os.path.join(SENTIMENT_DIR, "anfci_monthly.csv")


def collect_anfci():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("ERROR: FRED_API_KEY not set. Add it to your .env file.")
        return None

    print("Fetching ANFCI from FRED ...", end="", flush=True)
    df = fetch_fred("anfci", "ANFCI", api_key)
    weekly = df["anfci"].dropna().sort_index()
    print(f" {len(weekly)} weekly obs  "
          f"({weekly.index[0].strftime('%Y-%m-%d')} to {weekly.index[-1].strftime('%Y-%m-%d')})")

    # Aggregate: last weekly observation per calendar month
    monthly = weekly.resample("ME").last().dropna()
    monthly.name = "anfci"
    monthly.index.name = "date"

    print(f"Monthly: {len(monthly)} obs | "
          f"mean={monthly.mean():.4f}  std={monthly.std():.4f}  "
          f"min={monthly.min():.4f}  max={monthly.max():.4f}")

    os.makedirs(SENTIMENT_DIR, exist_ok=True)
    monthly.to_frame().to_csv(ANFCI_PATH)
    print(f"Saved:   {os.path.abspath(ANFCI_PATH)}")

    # Quick sanity checks
    print("\nSanity checks:")
    print(f"  Mean near 0?          {abs(monthly.mean()) < 0.5:>5}   (mean={monthly.mean():.4f})")
    print(f"  Std near 1?           {0.5 < monthly.std() < 2.0:>5}   (std={monthly.std():.4f})")

    if "2008-01" in monthly.index.strftime("%Y-%m").tolist():
        gfc_peak = monthly.loc["2008":"2009"].max()
        print(f"  GFC peak > +1?        {gfc_peak > 1.0:>5}   (2008-09 max={gfc_peak:.4f})")

    if "2020-01" in monthly.index.strftime("%Y-%m").tolist():
        covid_peak = monthly.loc["2020-01":"2020-06"].max()
        print(f"  COVID spike > +1?     {covid_peak > 1.0:>5}   (2020 H1 max={covid_peak:.4f})")

    if "2005-01" in monthly.index.strftime("%Y-%m").tolist():
        pre_gfc_min = monthly.loc["2005":"2007"].min()
        print(f"  Pre-GFC calm < 0?     {pre_gfc_min < 0.0:>5}   (2005-07 min={pre_gfc_min:.4f})")

    return monthly


if __name__ == "__main__":
    collect_anfci()

