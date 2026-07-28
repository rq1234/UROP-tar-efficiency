"""
granger_eightlag.py - C2: re-run the reverse-Granger screen at 8 lags.

The standard screen (granger_appendices.py's appendix_a) uses
config.N_LAGS_SCREEN=4. C2 in verification_manifest.md cites a separate
eight-lag re-run: 22/23 pass, Japan p=0.042. This calls the same function
parametrized to n_lags=8, in its own script rather than growing
granger_appendices.py's default behavior (that script's exports must stay
byte-identical run to run).

Usage:  python scripts/granger_eightlag.py
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                          # noqa: E402
from granger_appendices import appendix_a  # noqa: E402


def main():
    print("Eight-lag reverse-Granger re-run (C2)\n")
    rows = appendix_a(n_lags=8)
    path = os.path.join(config.ensure_rebuilt_dir(), "appendixA_eightlag.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> appendixA_eightlag.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
