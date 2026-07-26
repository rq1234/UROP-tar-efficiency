"""
OECD Consumer Confidence Indicator (CCI) downloader.

Fetches monthly OECD CCI from FRED (source: OECD via FRED).
FRED series pattern: CSCICP03{2-letter-ISO}M665S
Requires FRED_API_KEY in .env (same key used by collect_data.py).

CCI is amplitude-adjusted and centred at 100 by construction.
Typical range is roughly 96-104 per country.

Outputs:
  data/sentiment/oecd_cci_{CODE}.csv   — one file per country (date, cci)
  data/sentiment/oecd_cci_all.csv      — wide table (date × country)
  data/sentiment/oecd_cci_coverage.csv — coverage + recommended TAR grid bounds

Usage:
    python collect_oecd.py
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from market_config import OECD_CCI_MARKETS, MARKETS
from collect_data import fetch_fred

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")

# Analysis window for coverage and grid bound calculations
WINDOW_START = "1990-01"
WINDOW_END   = "2015-06"
MIN_OBS      = 240     # ~20 years monthly
MAX_MISSING  = 0.10    # 10%

# OECD 3-letter -> ISO 2-letter country code mapping (for FRED series IDs)
_OECD_TO_ISO2 = {
    "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR",
    "JPN": "JP", "KOR": "KR", "CAN": "CA", "AUS": "AU",
    "ESP": "ES", "CHE": "CH", "NLD": "NL", "MEX": "MX",
    "ISR": "IL", "GRC": "GR", "TUR": "TR",
    "ITA": "IT", "IRL": "IE", "BEL": "BE", "AUT": "AT",
    "PRT": "PT", "SWE": "SE", "FIN": "FI", "DNK": "DK",
    "NOR": "NO", "CHL": "CL", "COL": "CO", "IND": "IN",
    "NZL": "NZ", "POL": "PL", "CZE": "CZ",
}

# FRED series IDs for OECD CCI (Consumer Confidence, amplitude-adjusted, monthly)
# Pattern: CSCICP03{ISO2}M665S
OECD_CCI_FRED = {
    market: f"CSCICP03{_OECD_TO_ISO2[code]}M665S"
    for market, code in OECD_CCI_MARKETS.items()
    if code in _OECD_TO_ISO2
}


def collect_all_cci():
    """
    Fetch CCI for all OECD markets via FRED, save files, and print coverage report.
    Requires FRED_API_KEY environment variable.
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("ERROR: FRED_API_KEY not set. Add it to your .env file.")
        return

    os.makedirs(SENTIMENT_DIR, exist_ok=True)

    series_dict = {}

    print(f"Fetching OECD CCI (via FRED) for {len(OECD_CCI_FRED)} markets...\n")

    for market, fred_id in OECD_CCI_FRED.items():
        code    = OECD_CCI_MARKETS[market]
        country = MARKETS.get(market, {}).get("country", market)
        print(f"  {market:<14} ({code}) {fred_id:<22}  ", end="", flush=True)

        try:
            time.sleep(1.0)   # stay well within FRED rate limits
            df = fetch_fred(market, fred_id, api_key)
            s  = df.iloc[:, 0].dropna()
            s.name = code

            path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{code}.csv")
            s.to_frame(name="cci").to_csv(path)
            series_dict[code] = s

            window = s.loc[WINDOW_START:WINDOW_END]
            print(f"{s.index[0].strftime('%Y-%m')} -> {s.index[-1].strftime('%Y-%m')}  "
                  f"T_window={len(window)}  OK")
        except Exception as e:
            print(f"FAILED: {e}")

    if not series_dict:
        print("No data retrieved.")
        return

    # Save wide table
    wide = pd.DataFrame(series_dict)
    wide.index.name = "date"
    wide.to_csv(os.path.join(SENTIMENT_DIR, "oecd_cci_all.csv"))

    # Coverage report + grid bounds
    print("\n" + "=" * 95)
    print(f"{'Market':<14} {'Code':<5} {'Full start':<12} {'Full end':<10} "
          f"{'N(window)':>10} {'Missing%':>9} {'z_min':>7} {'z_max':>7} {'Usable'}")
    print("-" * 95)

    coverage_rows = []
    for market, fred_id in OECD_CCI_FRED.items():
        code = OECD_CCI_MARKETS[market]
        if code not in series_dict:
            print(f"{market:<14} {code:<5} {'FETCH FAILED'}")
            continue

        s      = series_dict[code]
        window = s.loc[WINDOW_START:WINDOW_END]

        expected = len(pd.date_range(WINDOW_START, WINDOW_END, freq="ME"))
        n_obs    = len(window)
        missing  = (expected - n_obs) / expected

        if len(window) >= 10:
            z_min = round(window.mean() - 2.5 * window.std(), 1)
            z_max = round(window.mean() + 2.5 * window.std(), 1)
        else:
            z_min = z_max = np.nan

        usable = (n_obs >= MIN_OBS) and (missing < MAX_MISSING)

        print(f"{market:<14} {code:<5} {s.index[0].strftime('%Y-%m'):<12} "
              f"{s.index[-1].strftime('%Y-%m'):<10} {n_obs:>10} "
              f"{missing*100:>8.1f}% {z_min:>7.1f} {z_max:>7.1f} "
              f"  {'YES' if usable else 'NO'}")

        coverage_rows.append({
            "market":      market,
            "oecd_code":   code,
            "fred_id":     fred_id,
            "country":     MARKETS.get(market, {}).get("country", market),
            "full_start":  s.index[0].strftime("%Y-%m"),
            "full_end":    s.index[-1].strftime("%Y-%m"),
            "n_window":    n_obs,
            "missing_pct": round(missing * 100, 1),
            "z_min":       z_min,
            "z_max":       z_max,
            "usable":      usable,
        })

    cov_df = pd.DataFrame(coverage_rows)
    cov_df.to_csv(os.path.join(SENTIMENT_DIR, "oecd_cci_coverage.csv"), index=False)

    usable_n = int(cov_df["usable"].sum()) if len(cov_df) else 0
    print(f"\n{usable_n} of {len(coverage_rows)} markets usable "
          f"(>={MIN_OBS} obs in {WINDOW_START}–{WINDOW_END}, <{MAX_MISSING*100:.0f}% missing)")
    print(f"\nFiles saved to {os.path.abspath(SENTIMENT_DIR)}/")
    print("  oecd_cci_{{CODE}}.csv  — per-country series")
    print("  oecd_cci_all.csv      — wide panel")
    print("  oecd_cci_coverage.csv — grid bounds for TAR estimation")


if __name__ == "__main__":
    collect_all_cci()
