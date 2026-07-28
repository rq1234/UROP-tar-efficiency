"""
fig62_distribution.py - C48: Figure 6.2's distribution facts.

Target (verification_manifest.md C48): "low-band mode near +5% vs mean
+14.6; tail months mostly 2008-09 and 2022; COVID months nearly absent."
"Low-band" = MR state (state==1). "+14.6" is the already-reproduced pooled
12m MR mean (horizon_test.csv).

Reads outputs/rebuilt/full_sample_raw.csv (horizon_episodes.py's raw
per-month export, full-sample Option-A classification - not the recursive
one) rather than recomputing from data/.

Usage:  python scripts/fig62_distribution.py
"""

import csv
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import config  # noqa: E402


def main():
    path = os.path.join(config.REBUILT, "full_sample_raw.csv")
    if not os.path.exists(path):
        print("  full_sample_raw.csv not found - run scripts/horizon_episodes.py first")
        return

    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    low = [r for r in rows if r["state"] == "1" and r["fwd12"] != ""]
    fwd = np.asarray([float(r["fwd12"]) for r in low])
    mean_pct = float(fwd.mean())

    # Mode: bin into 1pp-wide buckets centred on integers.
    buckets = np.round(fwd).astype(int)
    counts = Counter(buckets.tolist())
    mode_bucket, mode_n = counts.most_common(1)[0]

    # Which years dominate the tails (bottom/top 10% of the low-band distribution).
    lo_cut, hi_cut = np.percentile(fwd, 10), np.percentile(fwd, 90)
    years = [r["date"][:4] for r in low]
    tail_years = [y for y, f in zip(years, fwd) if f <= lo_cut or f >= hi_cut]
    year_counts = Counter(tail_years)
    top_years = year_counts.most_common(5)

    covid_months = sum(1 for r in low if r["date"].startswith("2020"))

    print(f"  low-band (MR) months: n={len(low)}, mean={mean_pct:.2f}%, "
         f"modal 1pp bucket={mode_bucket:+d}% (n={mode_n})")
    print(f"  tail-year counts (top 5, among the 10%/90% percentile tails): {top_years}")
    print(f"  2020 (COVID) low-band months: {covid_months} of {len(low)}")

    row = {
        "n_low_band_months": len(low), "mean_pct": round(mean_pct, 3),
        "modal_bucket_pct": mode_bucket, "modal_bucket_n": mode_n,
        "top_tail_years": str(top_years), "covid_2020_months": covid_months,
    }
    out = os.path.join(config.ensure_rebuilt_dir(), "fig62_distribution_facts.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
    print(f"\n    -> fig62_distribution_facts.csv (1 row)")


if __name__ == "__main__":
    main()
