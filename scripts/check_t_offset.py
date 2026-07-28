"""
Check whether Table 4.1's per-market T (estimation sample size) matches
Appendix A's per-market T (reverse-Granger screening sample size).

Read-only diagnostic against committed ground truth in results/exports/ and
results/tables/. Written in response to an external audit claim that the two
tables report different T for the same market with no note explaining why.

Usage:
    python scripts/check_t_offset.py
"""
import csv
import os

EXPORTS = os.path.join(os.path.dirname(__file__), "..", "results", "exports")
TABLES = os.path.join(os.path.dirname(__file__), "..", "results", "tables")


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    screen = {r["market"]: float(r["T"]) for r in read(os.path.join(EXPORTS, "appendixA_granger_global_cci.csv")) if r["T"].strip()}
    est = {r["market"]: float(r["T"]) for r in read(os.path.join(TABLES, "global_cci_all_markets.csv"))}

    print(f"{'market':<12}{'screenT':>10}{'estT':>8}{'diff':>7}")
    diffs = []
    for m in sorted(est):
        s = screen.get(m)
        e = est[m]
        if s is None:
            print(f"{m:<12}{'MISSING':>10}{e:>8.0f}{'?':>7}")
            continue
        d = e - s
        diffs.append(d)
        print(f"{m:<12}{s:>10.0f}{e:>8.0f}{d:>7.0f}")

    print()
    print(f"n compared = {len(diffs)}")
    print(f"unique diffs = {sorted(set(round(d) for d in diffs))}")
    print(f"min diff = {min(diffs):.0f}, max diff = {max(diffs):.0f}")


if __name__ == "__main__":
    main()
