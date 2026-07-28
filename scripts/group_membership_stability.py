"""
Test whether the paper's four heuristic groups (Section 4.2 prose, "the point
estimates can be organised into four heuristic groups rather than statistically
estimated clusters") survive re-estimation, even though the RW-share RANKING
does not (min_regime_summary.csv: Spearman vs base falls from 0.84 to 0.25 as
the minimum-regime-size constraint tightens).

The four groups, and their member markets, are read directly out of the
manuscript's Section 4.2 text (paper/Full_Paper_Draft_Tier2_Reworked_Referee_Revision.docx):

  G1  Global-stress-aligned (high RW share): Hong Kong, Singapore, Switzerland,
      Spain, Netherlands, Israel, Indonesia, Malaysia, Taiwan
  G2  Structural-mismatch cases: Japan, the Chinese exchanges (Shanghai, SZSE)
  G3  Mexico and Brazil: comparatively large low-sentiment (MR) shares
  G4  South Korea and the Philippines: low-sentiment classifications around
      stress episodes

Operationalisation (read the caveat in main() before citing this as a full
membership test): on the base panel (spec=1, full sample), G1 markets are
uniformly RW-dominant with MR% under ~15%; Japan is EXP-dominant; Shanghai,
SZSE, and the G3/G4 markets are RW-dominant but with a materially elevated
MR% (18-50%). That elevated-vs-low MR% split is the one thing regime shares
alone can test - it is NOT possible to test the finer G2-vs-G3-vs-G4
boundary from regime shares alone, since that boundary rests on episode-
timing/economic-history evidence (e.g. Shanghai's booms being domestic and
mistimed vs the global trigger), not on a different numeric profile. This
script tests two things per market: (a) does the base-run's dominant regime
survive, (b) does an elevated MR% (>=15pp, the rough gap separating G1 from
everyone else in the base run) survive - across the six min-regime rules
(outputs/rebuilt/min_regime_trimming.csv) and a fresh constant-drift (spec=2)
full-sample refit computed here.

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

GROUPS = {
    "G1_global_stress_aligned": ["hangseng", "sti", "smi", "ibex35", "aex",
                                  "ta125", "ta35", "jkse", "klci", "twse"],
    "G2_structural_mismatch": ["nikkei225", "shanghai", "szse"],
    "G3_mexico_brazil": ["ipc", "bovespa"],
    "G4_korea_philippines": ["kospi", "psei"],
}
ALL_MARKETS = [m for grp in GROUPS.values() for m in grp]
ELEVATED_MR_THRESHOLD = 15.0  # pp; roughly the gap between G1's MR% (<=10.1) and everyone else's (>=18.4)


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
    print("Computing constant-drift (spec=2) full-sample refit for 17 named markets...")
    spec2 = constant_drift_spec()

    alt_specs = {**min_regime, "constant_drift_spec2": spec2}

    rows = []
    for group, markets in GROUPS.items():
        for m in markets:
            mr0, rw0, exp0 = base[m]
            dom0 = dominant(mr0, rw0, exp0)
            elevated0 = mr0 >= ELEVATED_MR_THRESHOLD

            dom_agree, elevated_agree, n_specs = 0, 0, 0
            for spec_name, spec_data in alt_specs.items():
                if m not in spec_data:
                    continue
                mr, rw, exp = spec_data[m]
                n_specs += 1
                if dominant(mr, rw, exp) == dom0:
                    dom_agree += 1
                if (mr >= ELEVATED_MR_THRESHOLD) == elevated0:
                    elevated_agree += 1

            rows.append({
                "group": group, "market": m,
                "base_dominant": dom0, "base_MR_pct": round(mr0, 1),
                "base_elevated_MR": elevated0,
                "n_alt_specs": n_specs,
                "dominant_regime_agreement": f"{dom_agree}/{n_specs}",
                "elevated_MR_agreement": f"{elevated_agree}/{n_specs}",
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'Group':<28}{'Market':<12}{'Base dom.':<10}{'Base MR%':<10}"
          f"{'Dom. agree':<12}{'Elevated-MR agree'}")
    for r in rows:
        print(f"{r['group']:<28}{r['market']:<12}{r['base_dominant']:<10}"
              f"{r['base_MR_pct']:<10}{r['dominant_regime_agreement']:<12}"
              f"{r['elevated_MR_agreement']}")

    print(f"\nWrote: {OUT_CSV}")
    print("\nCAVEAT: this tests regime-dominance and elevated-MR-share stability only.")
    print("It does NOT test the finer G2-vs-G3-vs-G4 boundary (Shanghai/SZSE's mistimed")
    print("domestic booms vs Mexico/Brazil's general elevation vs Korea/Philippines'")
    print("episode-clustered MR months), which rests on episode-timing evidence this")
    print("script does not recompute.")


if __name__ == "__main__":
    main()
