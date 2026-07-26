"""
Combinatorial component search for BIC-composite trigger.

Tests all 57 subsets of size 2-6 from the 6 available monthly components
(CCI, VIX, BCI, ANFCI, YC, EPU) using the full BIC-selected pipeline:
  - Per-component BIC orthogonalisation lag
  - BIC Granger test lag with buffer rule
  - TAR estimation for admissible markets

Output: results/tables/bic_combinatorial_search.csv -- 57 rows ranked by score.
Score = exog_pass * 2 + both_tails (exogeneity weighted 2x).

Usage:
    python combinatorial_search.py              # buffer=4, max_orth_lag=12
    python combinatorial_search.py --quick      # max_orth_lag=6, ~3x faster
    python combinatorial_search.py --buffer 2   # alternative buffer
"""

import argparse
import itertools
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bic_composite_study import (
    build_composite_for_market,
    select_granger_lag,
    get_test_lag,
    test_exogeneity_bic,
    _episode_verdict,
)
from composite_study import load_monthly_components, _grid_bounds
from estimate        import find_optimal_thresholds, _assign_states, standard_errors
from market_config   import MARKETS
from bubble_now      import TABLES_DIR

ALL_COMPS = [
    "global_cci", "vix_monthly", "bci_monthly",
    "anfci_monthly", "yield_curve_monthly", "epu_monthly",
]
COMP_LABELS = {
    "global_cci":         "CCI",
    "vix_monthly":        "VIX",
    "bci_monthly":        "BCI",
    "anfci_monthly":      "ANFCI",
    "yield_curve_monthly": "YC",
    "epu_monthly":        "EPU",
}


# ---------------------------------------------------------------------------
# Silent TAR estimation (no prints, no file I/O)
# ---------------------------------------------------------------------------

def _tar_one_market(composite_z, log_prices, spec=1):
    """Run TAR for one market silently.  Returns result dict or None."""
    comp_z = composite_z.values
    log_p  = log_prices.values
    dates  = np.array(composite_z.index, dtype="datetime64[ns]")

    if len(comp_z) < 120:
        return None

    try:
        z_min, z_max, gl, mg = _grid_bounds(comp_z)
        opt    = find_optimal_thresholds(log_p, comp_z, z_min, z_max, gl, mg, spec, "returns")
        c1, c2 = opt["c1"], opt["c2"]
        se_res = standard_errors(log_p, comp_z, c1, c2, spec, "returns")
        state  = _assign_states(comp_z[1:], c1, c2)
        verdict = _episode_verdict(state, dates[1:], verbose=False)
        T = len(state)
        return {
            "c1": c1, "c2": c2,
            "beta_mr": se_res["beta1"],
            "beta_ex": se_res["beta3"],
            "n_mr": se_res["n1"], "n_rw": se_res["n2"], "n_ex": se_res["n3"],
            "T": T, "verdict": verdict,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Single combination: run all markets, aggregate stats
# ---------------------------------------------------------------------------

def run_combination(comp_cols, comps_df, markets, buffer=4, max_orth_lag=12, alpha=0.05):
    """
    Run full BIC pipeline for one component subset across all 23 markets.
    Returns a summary stats dict with one row worth of data.
    """
    exog_pass  = 0
    both_tails = 0
    beta3_neg  = 0
    var_exps   = []
    tar_mr, tar_rw, tar_ex = [], [], []

    for market in markets:
        try:
            res = build_composite_for_market(market, comps_df, comp_cols, max_orth_lag)
        except Exception:
            continue

        comp_z   = res["composite_z"]
        log_p    = res["log_prices"]
        max_orth = res["max_orth"]
        var_exps.append(res["var_exp"])

        returns = log_p.diff().dropna().reindex(comp_z.index).dropna()
        g_bic   = select_granger_lag(comp_z, returns)
        t_lag   = get_test_lag(max_orth, g_bic, buffer=buffer)
        _, _, verdict = test_exogeneity_bic(comp_z, returns, t_lag, alpha)

        if verdict != "PASS":
            continue

        exog_pass += 1
        tar = _tar_one_market(comp_z, log_p)
        if tar is None:
            continue

        T = tar["T"]
        tar_mr.append(tar["n_mr"] / T)
        tar_rw.append(tar["n_rw"] / T)
        tar_ex.append(tar["n_ex"] / T)
        if tar["verdict"] == "BOTH TAILS":
            both_tails += 1
        if tar["beta_ex"] < 0:
            beta3_neg += 1

    def _avg(lst):
        return round(float(np.mean(lst)), 4) if lst else np.nan

    label = "+".join(COMP_LABELS[c] for c in comp_cols)
    return {
        "components":  label,
        "n_comp":      len(comp_cols),
        "exog_pass":   exog_pass,
        "both_tails":  both_tails,
        "avg_var_exp": _avg(var_exps),
        "avg_mr_pct":  _avg(tar_mr),
        "avg_rw_pct":  _avg(tar_rw),
        "avg_exp_pct": _avg(tar_ex),
        "beta3_neg":   beta3_neg,
        "score":       exog_pass * 2 + both_tails,
    }


# ---------------------------------------------------------------------------
# Main: iterate all 57 combinations
# ---------------------------------------------------------------------------

def run_all_combinations(buffer=4, max_orth_lag=12, alpha=0.05):
    combs = [
        list(c)
        for r in range(2, len(ALL_COMPS) + 1)
        for c in itertools.combinations(ALL_COMPS, r)
    ]
    assert len(combs) == 57, f"Expected 57 subsets, got {len(combs)}"

    comps_df = load_monthly_components()
    markets  = list(MARKETS.keys())

    print(f"\n{'='*72}")
    print(f"Combinatorial BIC search  (57 subsets, buffer={buffer}, max_orth={max_orth_lag})")
    print(f"{'='*72}")

    rows = []
    for i, comp_cols in enumerate(combs, 1):
        label = "+".join(COMP_LABELS[c] for c in comp_cols)
        print(f"[{i:>2}/57] {label:<40} ...", end="", flush=True)
        row = run_combination(comp_cols, comps_df, markets, buffer, max_orth_lag, alpha)
        rows.append(row)
        print(f"  exog={row['exog_pass']:>2}  bt={row['both_tails']}  score={row['score']}")

    df = (pd.DataFrame(rows)
            .sort_values(["score", "avg_var_exp"], ascending=[False, False])
            .reset_index(drop=True))

    os.makedirs(TABLES_DIR, exist_ok=True)
    out_path = os.path.join(TABLES_DIR, "bic_combinatorial_search.csv")
    df.to_csv(out_path, index=False)

    print(f"\n{'='*72}")
    print("Top 10 by score  (exog_pass*2 + both_tails)")
    print(f"{'='*72}")
    print(f"{'#':<4} {'Components':<40} {'n':>2}  {'Exog':>4}  "
          f"{'BT':>3}  {'VarExp':>7}  Score")
    print("-" * 72)
    for rank, (_, r) in enumerate(df.head(10).iterrows(), 1):
        ve = f"{r['avg_var_exp']:.1%}" if not np.isnan(r["avg_var_exp"]) else "  n/a"
        print(f"{rank:<4} {r['components']:<40} {r['n_comp']:>2}  "
              f"{r['exog_pass']:>4}  {r['both_tails']:>3}  {ve:>7}  {r['score']}")

    print(f"\nSaved -> {out_path}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick",  action="store_true",
                        help="Use max_orth_lag=6 for a ~3x faster run")
    parser.add_argument("--buffer", type=int, default=4,
                        help="Buffer added to max_orth for test_lag (default 4)")
    args = parser.parse_args()

    max_orth = 6 if args.quick else 12
    run_all_combinations(buffer=args.buffer, max_orth_lag=max_orth)

