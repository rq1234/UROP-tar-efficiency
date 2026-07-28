"""
round03_episodes.py - Round 3 (S1, S3). S2 (episodes_exp.csv) is already
rebuilt by round01_horizon.py, which produces it byte-for-byte from the same
MEMBERSHIP RULE this round's README section describes - not repeated here.

Rebuilds:
  localised_runs.csv (append)  S1 - standalone country-CCI TAR, Greece/Turkey

S3 (MR cluster count) has no CSV target in results/exports/ - it is a
narrative sentence in results/exports/README.md ("222 distinct MR
calendar-months collapse into 9 clusters"). Reproduced here as a printed
check against the README's own cluster-boundary list, not written to a file.

Key findings, from results/exports/README.md Round 3:

  S1  Standalone country-CCI TAR (independent of the rejected mixed-trigger
      file) matches manifest G2/G4 exactly - only the Table 5.1 source note
      changes.
  S3  222 distinct MR calendar-months (gap <=3 months) collapse into 9
      clusters. The MR premium is identified from ~9 global episodes, not
      222 independent observations - the corrected test is underpowered,
      not evidence of a zero premium.

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

    print("  NOTE: shanghai/szse China-CCI rows (Round 4 T3) are NOT included -"
          " they require a live FRED pull (CSCICP03CNM665S) with no API key"
          " configured in this environment. See ASSUMPTIONS.md.")
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


if __name__ == "__main__":
    main()
