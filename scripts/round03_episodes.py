"""
round03_episodes.py - Round 3 (S1, S3) plus Round 4 T3 (China CCI), which
shares S1's output file. S2 (episodes_exp.csv) is already rebuilt by
round01_horizon.py, which produces it byte-for-byte from the same
MEMBERSHIP RULE this round's README section describes - not repeated here.

Rebuilds:
  localised_runs.csv (append)  S1 - standalone country-CCI TAR, Greece/Turkey
                                T3 - China CCI, Shanghai/SZSE
  cci_CHN_fetched.csv          T3 - the fetched China CCI series itself

S3 (MR cluster count) has no CSV target in results/exports/ - it is a
narrative sentence in results/exports/README.md ("222 distinct MR
calendar-months collapse into 9 clusters"). Reproduced here as a printed
check against the README's own cluster-boundary list, not written to a file.

Key findings, from results/exports/README.md Round 3-4:

  S1  Standalone country-CCI TAR (independent of the rejected mixed-trigger
      file) matches manifest G2/G4 exactly - only the Table 5.1 source note
      changes.
  S3  222 distinct MR calendar-months (gap <=3 months) collapse into 9
      clusters. The MR premium is identified from ~9 global episodes, not
      222 independent observations - the corrected test is underpowered,
      not evidence of a zero premium.
  T3  China CCI fetched fresh from FRED (CSCICP03CNM665S, 408 obs,
      1990-01..2023-12 - the series appears discontinued in FRED after that,
      not a vintage artefact). Shanghai T=317 c1=100.77 c2=104.37
      MR/RW/EXP 71/27/1.6; SZSE T=316 similar. The 2006-08 and 2014-15 booms
      do NOT classify as explosive (0/35 and 0/23 EXP months) - China's CCI
      has such high amplitude that c2~104 is almost never breached.
      data/ is untouched: the fetch is saved only to outputs/rebuilt/.

Usage:  python scripts/round03_episodes.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                          # noqa: E402
from round01_horizon import load_all   # noqa: E402


def s1_localised_runs():
    """Standalone country-CCI TAR for Greece (athex/GRC) and Turkey (bist100/TUR),
    identical code path to global_cci_study.py but with the country's own CCI."""
    from country_cci_study import load_cci_pair         # noqa: E402
    from estimate import find_optimal_thresholds, standard_errors  # noqa: E402
    from global_cci_study import _grid_bounds, _sig_marker  # noqa: E402

    rows = []
    for mkt, code in (("athex", "GRC"), ("bist100", "TUR")):
        y, z, dates = load_cci_pair(mkt, code, start=config.START)
        z_min, z_max, gl, mg = _grid_bounds(z)
        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
        c1, c2 = opt["c1"], opt["c2"]
        res = standard_errors(y, z, c1, c2, 1, "returns")
        T = res["n1"] + res["n2"] + res["n3"]

        rows.append({"market": mkt, "trigger": f"cci_{code}", "T": T,
                     "c1": round(c1, 3), "c2": round(c2, 3),
                     "MR_pct": round(100.0 * res["n1"] / T, 2),
                     "RW_pct": round(100.0 * res["n2"] / T, 2),
                     "EXP_pct": round(100.0 * res["n3"] / T, 2),
                     "beta_mr": round(res["beta1"], 6), "se_mr": round(res["se_b1"], 6),
                     "sig_mr": _sig_marker(res.get("tstat1")),
                     "beta_ex": round(res["beta3"], 6), "se_ex": round(res["se_b3"], 6),
                     "sig_ex": _sig_marker(res.get("tstat3"))})
        print(f"  S1 {mkt:<9} T={T} c1={c1:.3f} c2={c2:.3f}  "
              f"{rows[-1]['MR_pct']}/{rows[-1]['RW_pct']}/{rows[-1]['EXP_pct']}")
    return rows


def t3_china_cci():
    """Fetch China's OECD CCI fresh from FRED and run the same standalone
    country-CCI TAR as S1, for Shanghai and SZSE. data/ is never touched -
    the fetched series is saved only to outputs/rebuilt/cci_CHN_fetched.csv.
    Requires FRED_API_KEY (via .env or the environment); skips with a clear
    message if it is not set, rather than failing the whole round."""
    import pandas as pd

    key = os.environ.get("FRED_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            key = os.environ.get("FRED_API_KEY")
        except ImportError:
            pass
    if not key:
        print("  T3: skipped - no FRED_API_KEY configured (checked .env and "
              "the environment). See ASSUMPTIONS.md.")
        return []

    from collect_data import fetch_fred                             # noqa: E402
    from estimate import find_optimal_thresholds, standard_errors   # noqa: E402
    from global_cci_study import _grid_bounds, _sig_marker          # noqa: E402

    cci = fetch_fred("cci", "CSCICP03CNM665S", key)["cci"]
    cci_path = os.path.join(config.ensure_rebuilt_dir(), "cci_CHN_fetched.csv")
    cci.to_frame(name="cci").rename_axis("date").to_csv(cci_path, date_format="%Y-%m-%d")
    print(f"  T3: fetched China CCI, {len(cci)} obs "
          f"{cci.index.min().date()} -> {cci.index.max().date()}  -> cci_CHN_fetched.csv")

    cci.index = cci.index + pd.offsets.MonthEnd(0)
    panel = pd.read_csv(config.MONTHLY_PANEL, index_col="date", parse_dates=True)

    rows = []
    for mkt in ("shanghai", "szse"):
        prices = panel[f"eq_{mkt}"].dropna()
        df = pd.DataFrame({"price": prices, "cci": cci}).dropna().loc[config.START:]
        y = np.log(df["price"].to_numpy(dtype=float))
        z = df["cci"].to_numpy(dtype=float)

        z_min, z_max, gl, mg = _grid_bounds(z)
        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
        c1, c2 = opt["c1"], opt["c2"]
        res = standard_errors(y, z, c1, c2, 1, "returns")
        T = res["n1"] + res["n2"] + res["n3"]

        rows.append({"market": mkt, "trigger": "cci_CHN", "T": T,
                     "c1": round(c1, 3), "c2": round(c2, 3),
                     "MR_pct": round(100.0 * res["n1"] / T, 2),
                     "RW_pct": round(100.0 * res["n2"] / T, 2),
                     "EXP_pct": round(100.0 * res["n3"] / T, 2),
                     "beta_mr": round(res["beta1"], 6), "se_mr": round(res["se_b1"], 6),
                     "sig_mr": _sig_marker(res.get("tstat1")),
                     "beta_ex": round(res["beta3"], 6), "se_ex": round(res["se_b3"], 6),
                     "sig_ex": _sig_marker(res.get("tstat3"))})
        print(f"  T3 {mkt:<9} T={T} c1={c1:.3f} c2={c2:.3f}  "
              f"{rows[-1]['MR_pct']}/{rows[-1]['RW_pct']}/{rows[-1]['EXP_pct']}")
    return rows


def s3_mr_clusters():
    """222 distinct MR calendar-months (any market), gap<=3 -> 9 clusters. No CSV target."""
    data = load_all()
    months = sorted({m for d in data.values() for m in d["months"][d["state"] == 1]})
    print(f"  S3: {len(months)} distinct MR calendar-months")

    clusters, start = [], months[0]
    prev = months[0]
    for m in months[1:]:
        if (m - prev).n > 3:
            clusters.append((start, prev))
            start = m
        prev = m
    clusters.append((start, prev))
    print(f"  S3: {len(clusters)} clusters (gap<=3 months):")
    for a, b in clusters:
        print(f"      {a}..{b}")
    return clusters


def write(name, rows):
    if not rows:
        return
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    existing = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            existing = list(csv.DictReader(fh))
    # Append/replace rows keyed on `market`, rather than clobbering any rows a
    # later round (Round 4 T3, China) may already have written to this file.
    by_market = {r["market"]: r for r in existing}
    for r in rows:
        by_market[r["market"]] = r
    all_rows = list(by_market.values())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"    -> {name} ({len(all_rows)} rows)")


def main():
    print("Round 3 - episode-level EXP test support (S1, S3)\n")
    write("localised_runs.csv", s1_localised_runs())
    s3_mr_clusters()
    print("\nRound 4 T3 - China CCI (fetched live)\n")
    write("localised_runs.csv", t3_china_cci())


if __name__ == "__main__":
    main()
