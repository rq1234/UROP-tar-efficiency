"""
anfci_export.py - C9: ANFCI all-markets export with firing rate and screen
pass/fail, for all reachable markets (not just the 14 that already cleared
run_all_markets()'s pre-filter in the committed results/archive/tables/
anfci_all_markets.csv).

Does NOT call anfci_study.run_all_markets() directly - that function writes
straight to the committed results/archive/tables/anfci_all_markets.csv and
must not be invoked as-is. Instead this loops _estimate_one() itself and
writes to outputs/rebuilt/ under a different filename.

src/archive/anfci_study.py is read-only here except for the small additive
patch already made to exogeneity_screen_anfci() (now returns
(admissible, records) instead of just admissible).

Usage:  python scripts/anfci_export.py
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
    from anfci_study import MARKETS, _estimate_one, exogeneity_screen_anfci  # noqa: E402

    print("C9 - ANFCI all-markets export (firing rate + screen)\n")
    _, screen_records = exogeneity_screen_anfci()
    screen_by_mkt = {r["market"]: r for r in screen_records}

    rows = []
    for market in MARKETS:
        try:
            r = _estimate_one(market, verbose=False)
        except (KeyError, ValueError):
            continue  # e.g. colcap has no equity column in the panel - no data
        if r is None:
            continue
        r["firing_rate_pct"] = round(100.0 * r["n_ex"] / r["T"], 1)
        s = screen_by_mkt.get(market, {})
        r["screen_F"] = round(s.get("F", float("nan")), 4) if "F" in s else ""
        r["screen_p"] = round(s.get("p", float("nan")), 4) if "p" in s else ""
        r["screen_gate"] = s.get("gate", "")
        rows.append(r)
        print(f"  {market:<12} T={r['T']:>4}  firing={r['firing_rate_pct']:>5.1f}%  "
             f"screen={r['screen_gate']}")

    path = os.path.join(config.ensure_rebuilt_dir(), "anfci_all_markets_full.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n    -> anfci_all_markets_full.csv ({len(rows)} rows)")

    n_fail = sum(1 for r in rows if r["screen_gate"] == "FAIL")
    print(f"  {len(rows)} markets estimated; {n_fail} fail the exogeneity screen")


if __name__ == "__main__":
    main()
