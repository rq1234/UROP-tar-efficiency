"""
Direct OECD SDMX API fetcher for CCI data.

FRED mirrors OECD data with a lag.  For countries where OECD publishes
CCICP (Consumer Confidence Index, Composite, Amplitude-Adjusted) at monthly
frequency, the OECD SDMX endpoint is often 12-24 months ahead of FRED.

This script patches oecd_cci_{CODE}.csv files in-place: it appends any
observations that are newer than what the file already contains.

Countries with active CCICP+AA series confirmed via API (as of 2026-06):
  USA  → through 2025-11 (FRED: 2024-01, gain ~22 months)
  GBR  → through 2025-11 (FRED: 2024-01, gain ~22 months)
  ESP  → through 2026-02 (FRED: 2024-01, gain ~26 months)
  JPN  → through 2025-10 (FRED: 2024-01, gain ~21 months)

Usage:
    cd src && python collect_oecd_direct.py
"""

import os
import sys
import time
import urllib.request
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from market_config import OECD_CCI_MARKETS

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")

# ISO-2 to ISO-3 mapping (OECD API uses 3-letter codes)
_ISO2_TO_OECD3 = {
    "US": "USA", "GB": "GBR", "DE": "DEU", "FR": "FRA",
    "JP": "JPN", "KR": "KOR", "CA": "CAN", "AU": "AUS",
    "ES": "ESP", "CH": "CHE", "NL": "NLD", "MX": "MEX",
    "IL": "ISR",
}
_OECD_TO_ISO2 = {v: k for k, v in _ISO2_TO_OECD3.items()}

# OECD API endpoint (the stats.oecd.org URL redirects here with proper content)
_BASE_URL = "https://stats.oecd.org/SDMX-JSON/data/MEI_CLI/CSCICP03.{country}.M/all"
_HEADERS  = {
    "Accept": "application/vnd.sdmx.data+json;version=1.0.0",
    "User-Agent": "Mozilla/5.0",
}


def fetch_cci_oecd(oecd3_code, timeout=30):
    """
    Fetch the full amplitude-adjusted CCI monthly series for one country.

    Returns pd.Series indexed by month-end Timestamps, or None if unavailable.
    """
    url = _BASE_URL.format(country=oecd3_code)
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"    FETCH FAILED ({type(e).__name__}): {e}")
        return None

    try:
        struct   = data["data"]["structures"][0]
        ser_dims = struct["dimensions"]["series"]
        dim_vals = {d["id"]: [v["id"] for v in d["values"]] for d in ser_dims}
        time_vals = [v["id"] for v in struct["dimensions"]["observation"][0]["values"]]
    except (KeyError, IndexError) as e:
        print(f"    PARSE FAILED (structure): {e}")
        return None

    ds = data["data"]["dataSets"][0]
    obs_out = {}

    for ser_key, ser_data in ds["series"].items():
        obs = ser_data.get("observations", {})
        if not obs:
            continue
        indices = list(map(int, ser_key.split(":")))
        try:
            freq    = dim_vals["FREQ"][indices[1]]
            measure = dim_vals["MEASURE"][indices[2]]
            adj     = dim_vals["ADJUSTMENT"][indices[5]]
        except IndexError:
            continue

        try:
            country = dim_vals["REF_AREA"][indices[0]]
        except IndexError:
            continue
        if country != oecd3_code:
            continue
        if freq != "M" or measure != "CCICP" or adj != "AA":
            continue

        for k, v in obs.items():
            idx = int(k)
            if idx < len(time_vals) and v[0] is not None:
                period = time_vals[idx]
                # Only keep monthly periods (YYYY-MM format)
                if len(period) == 7 and period[4] == "-":
                    obs_out[period] = v[0]

    if not obs_out:
        return None

    # Convert YYYY-MM to month-end Timestamps
    s = pd.Series(obs_out, name="cci")
    s.index = pd.to_datetime([p + "-01" for p in s.index]) + pd.offsets.MonthEnd(0)
    s = s.sort_index()
    return s


def patch_csv(market, oecd3_code, verbose=True):
    """
    Update data/sentiment/oecd_cci_{oecd3}.csv with any newer OECD-direct data.
    Appends only observations with dates strictly after the existing file's last date.
    Skips if OECD data does not extend the existing file.
    Returns (old_end, new_end, n_added) or None.
    """
    # Files are named with 3-letter codes (matching collect_oecd.py convention)
    csv_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{oecd3_code}.csv")

    if verbose:
        print(f"  {market:<14} ({oecd3_code})  fetching from OECD ...  ", end="", flush=True)

    fresh = fetch_cci_oecd(oecd3_code)
    if fresh is None or fresh.empty:
        if verbose:
            print("no CCICP+AA data available")
        return None

    fresh_end = fresh.index.max()

    # Load existing file
    if os.path.exists(csv_path):
        existing = pd.read_csv(csv_path, index_col=0, parse_dates=True)["cci"]
        existing.index = pd.to_datetime(existing.index) + pd.offsets.MonthEnd(0)
        old_end = existing.index.max()
    else:
        existing = pd.Series(dtype=float, name="cci")
        old_end  = pd.Timestamp("1900-01-01")

    if fresh_end <= old_end:
        if verbose:
            print(f"OECD ends {fresh_end.strftime('%Y-%m')} <= file {old_end.strftime('%Y-%m')}, skip")
        return (old_end, old_end, 0)

    new_obs = fresh[fresh.index > old_end]
    n_added = len(new_obs)

    if n_added == 0:
        if verbose:
            print(f"no new obs (file already at {old_end.strftime('%Y-%m')})")
        return (old_end, old_end, 0)

    combined = pd.concat([existing, new_obs]).sort_index()
    combined.name = "cci"
    combined.to_frame().to_csv(csv_path)

    new_end = combined.index.max()
    if verbose:
        print(f"added {n_added} obs  ({old_end.strftime('%Y-%m')} -> {new_end.strftime('%Y-%m')})")
    return (old_end, new_end, n_added)


def patch_all(markets=None):
    """Patch all markets (or a subset) with direct OECD data."""
    if markets is None:
        markets = OECD_CCI_MARKETS

    _OECD_TO_ISO2_local = {
        "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR",
        "JPN": "JP", "KOR": "KR", "CAN": "CA", "AUS": "AU",
        "ESP": "ES", "CHE": "CH", "NLD": "NL", "MEX": "MX", "ISR": "IL",
    }

    print(f"\nPatching {len(markets)} CCI files from OECD direct API...\n")
    summary = []
    for market, oecd3 in markets.items():
        result = patch_csv(market, oecd3)
        if result is not None:
            summary.append((market, oecd3, *result))
        time.sleep(1.0)  # be polite to the API

    print(f"\nSummary — {sum(r[4] for r in summary)} total obs added:")
    for market, oecd3, old, new, n in summary:
        if n > 0:
            print(f"  {market:<14} ({oecd3})  {old.strftime('%Y-%m')} -> {new.strftime('%Y-%m')}  (+{n})")


if __name__ == "__main__":
    os.makedirs(SENTIMENT_DIR, exist_ok=True)
    patch_all()
