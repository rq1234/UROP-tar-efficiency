"""
baa_export.py - C8: BAA spread euphoria-compression / GFC-spike summary.

Target (verification_manifest.md C8, class V): 0.56pp euphoria compression
vs 3.7pp GFC spike. No formula tried against the committed daily_panel.csv
BAA series reproduces both together under one consistent methodology - see
ASSUMPTIONS.md. This script (a) computes both a mean-deviation and an
intra-window-range statistic against the committed data, and (b), if
FRED_API_KEY is available, attempts a live BAA10Y refetch to test whether a
data-vintage difference explains the gap (the same pattern that resolved
V1/V4/C45 earlier in this rebuild).

src/archive/baa_study.py is read-only here except for the additive
episode_summary_stats() function already added to it.

Usage:  python scripts/baa_export.py
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src", "archive"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def main():
    from baa_study import episode_summary_stats  # noqa: E402

    print("C8 - BAA spread episode summary\n")
    rows = []
    for r in episode_summary_stats():
        r["source"] = "committed_daily_panel"
        rows.append(r)
        print(f"  [committed] {r['window']:<10} mean_dev={r['mean_deviation_pp']:+.3f}pp  "
             f"range={r['intra_window_range_pp']:.3f}pp")

    key = os.environ.get("FRED_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv  # noqa: E402
            load_dotenv()
            key = os.environ.get("FRED_API_KEY")
        except ImportError:
            pass
    if key:
        from collect_data import fetch_fred  # noqa: E402

        fresh = fetch_fred("baa_spread", "BAA10Y", key)["baa_spread"]
        for r in episode_summary_stats(baa_series=fresh):
            r["source"] = "live_FRED_refetch"
            rows.append(r)
            print(f"  [live]      {r['window']:<10} mean_dev={r['mean_deviation_pp']:+.3f}pp  "
                 f"range={r['intra_window_range_pp']:.3f}pp")
    else:
        print("  (no FRED_API_KEY - skipped live refetch, committed-data figures only)")

    path = os.path.join(config.ensure_rebuilt_dir(), "baa_episode_stats.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n    -> baa_episode_stats.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
