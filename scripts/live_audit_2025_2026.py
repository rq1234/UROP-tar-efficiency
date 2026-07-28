"""
live_audit_2025_2026.py - Round 5 (21-July audit verification), V1/V3/V4.

Rebuilds:
  reverse_granger_extra.csv   V1 - S&P 500 return -> d(US CCI), the audit A3 check
  gcci_labels_2025_2026.csv   V3 - S&P 500 under the global CCI, Option A vs B
  mcsi_2025_2026.csv          V4 - MCSI re-pull vs the frozen Option-B c1

V2 (the "22 markets" -> "21 markets" correction) and V5 (the episode figure)
have no CSV target: V2 is a sentence for Section 6.3, already consistent with
config.EXCLUDED_EXP_MARKETS and episodes_exp.csv (21 distinct contributing
markets - confirmed below); V5 is a figure, out of scope here.

Key findings, from results/exports/README.md Round 5:

  V1  S&P 500 return -> Delta(US CCI), q=4, identical setup to the Appendix-A
      screen: F=3.5358, p=0.0075 -> FAILS exogeneity. The paper's claim that
      the S&P 500 PASSES this screen is wrong and must be rewritten.
  V3  S&P 500 global-CCI labels (Option B frozen c1=97.53/c2=101.93; Option A
      c1=97.67/c2=101.93): Aug 2025 - Apr 2026 = RW under both options; MR
      appears only in May 2026, and only under Option A.
  V4  Frozen S&P 500 MCSI Option-B c1=59.677 (confirms the assumed 59.7).
      MCSI stays below c1 every month Aug 2025 - May 2026; minimum 44.8
      (May 2026).

Usage:  python scripts/live_audit_2025_2026.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                          # noqa: E402
from horizon_episodes import load_all   # noqa: E402


def v1_reverse_granger():
    """S&P 500 return -> d(US CCI): identical setup to appendix_a, one market."""
    from country_cci_study import load_cci_pair         # noqa: E402
    from exogeneity import granger_f_test               # noqa: E402

    y, z, _ = load_cci_pair("sp500", "USA", start=config.START)
    F, p = granger_f_test(np.diff(z), np.diff(y), config.N_LAGS_SCREEN)[:2]
    gate = "FAIL" if p <= config.ALPHA else "PASS"
    row = {"market": "sp500", "trigger": "US_CCI", "q": config.N_LAGS_SCREEN,
           "F": round(float(F), 4), "p": round(float(p), 4), "gate": gate, "T": len(y)}
    print(f"  V1: F={row['F']} p={row['p']} -> {gate} (T={row['T']})")
    return [row]


def v2_market_count():
    """No CSV target - confirm the 21-market episode count against episodes_exp.csv."""
    data = load_all()
    mkts = sorted({m for m, d in data.items() if m not in config.EXCLUDED_EXP_MARKETS
                   and (d["state"] == 2).any()})
    print(f"  V2: {len(mkts)} distinct markets contribute EXP episodes "
          f"(Japan excluded): {mkts}")


def v3_gcci_labels():
    """S&P 500 under the global CCI: Option A (full-sample) vs Option B (frozen)."""
    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts             # noqa: E402
    from global_cci_study import load_global_cci_pair   # noqa: E402
    from threshold_bootstrap import grid_bounds            # noqa: E402
    import pandas as pd

    y, z, dates = load_global_cci_pair("sp500", config.START, None)
    months = pd.to_datetime(dates).to_period("M")

    zmin_a, zmax_a, mg_a = grid_bounds(z)
    c1_a, c2_a = optimal_from_parts(np.diff(y), y[:-1], z[1:], zmin_a, zmax_a,
                                    config.GRID_LENGTH, mg_a)

    cut = pd.Period(config.INSAMPLE_END, "M")
    insample = np.asarray(months <= cut)
    yb, zb = y[insample], z[insample]
    zmin_b, zmax_b, mg_b = grid_bounds(zb)
    c1_b, c2_b = optimal_from_parts(np.diff(yb), yb[:-1], zb[1:], zmin_b, zmax_b,
                                    config.GRID_LENGTH, mg_b)
    print(f"  V3: Option A c1={c1_a:.3f} c2={c2_a:.3f}   "
          f"Option B c1={c1_b:.3f} c2={c2_b:.3f}")

    a_state = _assign_states(z[1:], c1_a, c2_a)
    b_state = _assign_states(z[1:], c1_b, c2_b)
    names = {0: "RW", 1: "MR", 2: "EXP"}
    mm = months[1:]

    win = (mm >= pd.Period("2025-08", "M")) & (mm <= pd.Period("2026-05", "M"))
    rows = []
    for m, zv, sa, sb in zip(mm[win], z[1:][win], a_state[win], b_state[win]):
        rows.append({"month": str(m), "gcci_value": round(float(zv), 3),
                     "label_optionA": names[int(sa)], "label_optionB": names[int(sb)]})
    for r in rows:
        print(f"    {r['month']}  {r['gcci_value']:.3f}  A={r['label_optionA']}  "
              f"B={r['label_optionB']}")
    return rows


def v4_mcsi_repull():
    """MCSI Aug 2025 - May 2026 vs the frozen S&P 500 MCSI Option-B c1.

    2026-05 (44.8) is in the export but not in data/sentiment/mcsi_monthly.csv
    or data/combined/monthly_panel.csv (both stop at 2026-04) - a live re-pull
    beyond the committed vintage. If FRED_API_KEY is configured (.env or the
    environment), the missing month is fetched fresh (data/ still untouched -
    the extra month is merged in memory only); otherwise it is reported as a
    documented gap rather than fabricated. See ASSUMPTIONS.md.
    """
    import pandas as pd

    from bubble_now import PAIR_SPECS, run_option_b     # noqa: E402

    spec = next(s for s in PAIR_SPECS if s[-1] == "SP500_MCSI")
    b = run_option_b(spec)
    c1 = b["c1"]
    print(f"  V4: frozen SP500-MCSI Option-B c1={c1:.3f}")

    mcsi = pd.read_csv(config.MONTHLY_PANEL, index_col="date", parse_dates=True)["mcsi"].dropna()
    mcsi.index = mcsi.index.to_period("M")
    window = mcsi.loc[(mcsi.index >= pd.Period("2025-06", "M"))
                       & (mcsi.index <= pd.Period("2026-05", "M"))]

    target = pd.Period("2026-05", "M")
    if target not in window.index:
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
            fresh = fetch_fred("mcsi", "UMCSENT", key)["mcsi"]
            fresh.index = fresh.index.to_period("M")
            if target in fresh.index:
                window = pd.concat([window, fresh.loc[[target]]]).sort_index()
                print(f"  V4: fetched the missing {target} month live "
                      f"({float(fresh.loc[target]):.1f}) - not written to data/")

    rows = []
    for m, v in window.items():
        rows.append({"month": str(m), "umcsent": float(v), "below_c1_flag": bool(v < c1)})
    if target not in window.index:
        print(f"  V4: {target} is missing from data/ and no FRED_API_KEY is configured - "
              "not fabricated, see ASSUMPTIONS.md A4.9")
    for r in rows:
        print(f"    {r['month']}  {r['umcsent']}  below_c1={r['below_c1_flag']}")
    return rows


def write(name, rows):
    if not rows:
        return
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    print("Round 5 - 21-July audit verification (V1, V2 check, V3, V4)\n")
    write("reverse_granger_extra.csv", v1_reverse_granger())
    v2_market_count()
    write("gcci_labels_2025_2026.csv", v3_gcci_labels())
    write("mcsi_2025_2026.csv", v4_mcsi_repull())


if __name__ == "__main__":
    main()
