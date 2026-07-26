"""
Parse the official OECD Global Composite BCI from the SDMX CSV download.

Source file: data/sentiment/oecd_bci.csv
  Downloaded from OECD.Stat: MEI_CLI dataset, REF_AREA=OECD, MEASURE=BCICP,
  ADJUSTMENT=AA (amplitude-adjusted, long-run average = 100).

Relevant columns in the SDMX export:
  TIME_PERIOD : YYYY-MM date string
  OBS_VALUE   : BCI value (100 = long-run average)

Sign convention: high BCI = business optimism = bubble risk (EXP). No negation.

Output: data/sentiment/bci_monthly.csv  (date, bci)

Usage:
    cd src && python collect_bci.py
"""

import os
import pandas as pd

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
SOURCE_PATH   = os.path.join(SENTIMENT_DIR, "oecd_bci.csv")
BCI_PATH      = os.path.join(SENTIMENT_DIR, "bci_monthly.csv")


def collect_bci():
    if not os.path.exists(SOURCE_PATH):
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_PATH}\n"
            "Download from OECD.Stat: MEI_CLI, REF_AREA=OECD, MEASURE=BCICP, AA."
        )

    raw = pd.read_csv(SOURCE_PATH)
    s = raw.set_index("TIME_PERIOD")["OBS_VALUE"].dropna()
    s.index = pd.to_datetime(s.index.astype(str) + "-01") + pd.offsets.MonthEnd(0)
    s = s.sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = "bci"
    s.index.name = "date"

    print(f"OECD Global BCI: {len(s)} monthly obs  "
          f"({s.index[0].strftime('%Y-%m')} to {s.index[-1].strftime('%Y-%m')})")
    print(f"  mean={s.mean():.3f}  std={s.std():.3f}  "
          f"min={s.min():.3f}  max={s.max():.3f}")
    print(f"  Current (latest): {s.iloc[-1]:.3f}  "
          f"as of {s.index[-1].strftime('%Y-%m')}")

    s.to_frame().to_csv(BCI_PATH)
    print(f"Saved: {os.path.abspath(BCI_PATH)}")

    print("\nSanity checks (1990-present):")
    sub = s.loc["1990":]
    dotcom_peak  = sub.loc["1999":"2001"].max()
    gfc_trough   = sub.loc["2008":"2009"].min()
    covid_trough = sub.loc["2020-01":"2020-06"].min()
    print(f"  Dot-com peak > 101?   {dotcom_peak > 101:>5}   (1999-2001 max={dotcom_peak:.3f})")
    print(f"  GFC trough < 98?      {gfc_trough < 98:>5}   (2008-09 min={gfc_trough:.3f})")
    print(f"  COVID trough < 98?    {covid_trough < 98:>5}   (2020 H1 min={covid_trough:.3f})")

    return s


if __name__ == "__main__":
    collect_bci()
