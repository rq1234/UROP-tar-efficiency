"""
Dominant-band stability test, run across the FULL 23-market panel rather than
only the 17 markets Section 4.2's prose names across its four heuristic
groups. Simpler question than the group-membership version this replaces:
for every panel market, does the base run's dominant regime (whichever of
MR/RW/EXP has the largest share) survive under the same six minimum-regime
rules (outputs/rebuilt/min_regime_trimming.csv) plus a fresh constant-drift
(spec=2) full-sample refit computed here - seven alternative specifications
in total, same design as the original 17-market check (C53).

Panel-wide rather than group-restricted specifically so the result doesn't
depend on which markets Section 4.2 chose to name - one number, one panel,
no explanation needed about which markets were in scope and why.

Output: outputs/rebuilt/group_membership_stability.csv

Usage:
    python scripts/group_membership_stability.py
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                                    # noqa: E402
from estimate import find_optimal_thresholds                      # noqa: E402
from global_cci_study import load_global_cci_pair, _grid_bounds    # noqa: E402

BASE_PANEL = os.path.join(ROOT, "results", "tables", "global_cci_all_markets.csv")
MIN_REGIME_CSV = os.path.join(ROOT, "outputs", "rebuilt", "min_regime_trimming.csv")
OUT_CSV = os.path.join(ROOT, "outputs", "rebuilt", "group_membership_stability.csv")


def _all_markets():
    with open(BASE_PANEL, newline="", encoding="utf-8") as f:
        return [r["market"] for r in csv.DictReader(f)]


ALL_MARKETS = _all_markets()


def dominant(mr, rw, exp):
    return max((("MR", mr), ("RW", rw), ("EXP", exp)), key=lambda t: t[1])[0]


def base_panel():
    with open(BASE_PANEL, newline="", encoding="utf-8") as f:
        rows = {r["market"]: r for r in csv.DictReader(f)}
    out = {}
    for m in ALL_MARKETS:
        r = rows[m]
        T = float(r["T"])
        out[m] = (100 * float(r["n_mr"]) / T, 100 * float(r["n_rw"]) / T, 100 * float(r["n_ex"]) / T)
    return out


def min_regime_specs():
    with open(MIN_REGIME_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    specs = {}
    for r in rows:
        if r["market"] not in ALL_MARKETS:
            continue
        specs.setdefault(r["rule"], {})[r["market"]] = (
            float(r["MR_pct"]), float(r["RW_pct"]), float(r["EXP_pct"]))
    return specs


def constant_drift_spec():
    """Fresh spec=2 (constant-drift) full-sample refit, same grid construction
    as the paper's base (spec=1) panel - only the drift specification differs."""
    out = {}
    for m in ALL_MARKETS:
        y, z, dates = load_global_cci_pair(m, config.START, None)
        z_min, z_max, gl, mg = _grid_bounds(z)
        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 2, "returns")
        n1, n2, n3 = opt["n1"], opt["n2"], opt["n3"]
        T = n1 + n2 + n3
        out[m] = (100 * n1 / T, 100 * n2 / T, 100 * n3 / T)
        print(f"  spec=2  {m:<10} c1={opt['c1']:.2f} c2={opt['c2']:.2f}  "
              f"MR={out[m][0]:.1f}% RW={out[m][1]:.1f}% EXP={out[m][2]:.1f}%")
    return out


def main():
    base = base_panel()
    min_regime = min_regime_specs()
    print(f"Computing constant-drift (spec=2) full-sample refit for all {len(ALL_MARKETS)} "
          f"panel markets...")
    spec2 = constant_drift_spec()

    alt_specs = {**min_regime, "constant_drift_spec2": spec2}

    rows = []
    for m in ALL_MARKETS:
        mr0, rw0, exp0 = base[m]
        dom0 = dominant(mr0, rw0, exp0)

        dom_agree, n_specs = 0, 0
        for spec_name, spec_data in alt_specs.items():
            if m not in spec_data:
                continue
            mr, rw, exp = spec_data[m]
            n_specs += 1
            if dominant(mr, rw, exp) == dom0:
                dom_agree += 1

        rows.append({
            "market": m, "base_dominant": dom0,
            "base_MR_pct": round(mr0, 1), "base_RW_pct": round(rw0, 1),
            "base_EXP_pct": round(exp0, 1),
            "n_alt_specs": n_specs,
            "dominant_regime_agreement": f"{dom_agree}/{n_specs}",
            "is_exception": dom_agree < n_specs,
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'Market':<12}{'Base dom.':<10}{'MR%':<7}{'RW%':<7}{'EXP%':<7}"
          f"{'Dom. agree'}")
    for r in rows:
        print(f"{r['market']:<12}{r['base_dominant']:<10}{r['base_MR_pct']:<7}"
              f"{r['base_RW_pct']:<7}{r['base_EXP_pct']:<7}"
              f"{r['dominant_regime_agreement']}")

    n_stable = sum(1 for r in rows if not r["is_exception"])
    exceptions = [r["market"] for r in rows if r["is_exception"]]
    print(f"\n{n_stable} of {len(rows)} panel markets keep the same dominant regime "
          f"across all 7 alternative specifications.")
    if exceptions:
        print(f"Exceptions: {', '.join(exceptions)}")
    else:
        print("No exceptions.")

    print(f"\nWrote: {OUT_CSV}")
    print("\nCAVEAT: tests regime-dominance stability only (whichever of MR/RW/EXP has the")
    print("largest share) - not a test of the four heuristic groups' finer boundaries,")
    print("which rest partly on episode-timing evidence this script does not recompute.")


if __name__ == "__main__":
    main()
