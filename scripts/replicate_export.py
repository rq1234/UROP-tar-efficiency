"""
replicate_export.py - C1: export src/replicate.py's Table 7/8 replication to
CSV, plus the RSS-flatness diagnostic for FTSE100's no-drift row.

src/replicate.py's replicate_table7()/replicate_table8() only print - there
was never a committed CSV to diff Tables 7/8 against. This script imports
(read-only) from src/replicate.py and src/estimate.py and re-runs the same
six-row spec loops, capturing what standard_errors() already returns into
row dicts instead of printing them.

It also answers the "RSS surface flat within 0.018%" claim (results/exports/
README.md's I2 item) for the FTSE100 no-drift row: no existing function
exposes the full RSS grid (find_optimal_thresholds keeps only the best), so
this instruments the same double loop over gridsearch() to record every RSS
value, then reports the range as a percentage of both the min and the mean -
whichever is closest to 0.018% is reported, not forced.

src/replicate.py and src/estimate.py are read-only here - all output goes to
outputs/rebuilt/.

Usage:  python scripts/replicate_export.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def export_table(specs, load_pair, panel_path, trigger, name):
    from estimate import find_optimal_thresholds, standard_errors  # noqa: E402

    rows = []
    for equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, tlag in specs:
        y, z = load_pair(panel_path, equity_col, trigger, start, end, skip=skip, trigger_lag=tlag)
        T = len(y)
        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, mode)
        res = standard_errors(y, z, opt["c1"], opt["c2"], spec, mode)
        rows.append({
            "label": label, "spec": spec, "T": T,
            "c1": round(opt["c1"], 4), "c2": round(opt["c2"], 4),
            "alpha1": round(res["alpha1"], 6), "beta1": round(res["beta1"], 6),
            "se1": round(res["se1"], 6), "tstat1": round(res["tstat1"], 4), "n1": res["n1"],
            "alpha2": round(res["alpha2"], 6), "beta2": round(res["beta2"], 6),
            "se2": round(res["se2"], 6), "tstat2": round(res["tstat2"], 4), "n2": res["n2"],
            "alpha3": round(res["alpha3"], 6), "beta3": round(res["beta3"], 6),
            "se3": round(res["se3"], 6), "tstat3": round(res["tstat3"], 4), "n3": res["n3"],
        })
        print(f"  {label:<25} spec={spec} c1={opt['c1']:.2f} c2={opt['c2']:.2f} T={T}")

    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")
    return rows


def rss_flatness_ftse_nodrift():
    """C1 / README I2: 'FTSE no-drift RSS surface flat within 0.018%'.

    Instruments the same double loop find_optimal_thresholds() runs
    internally, but keeps every RSS value instead of only the minimum -
    no existing function exposes the full grid."""
    from estimate import gridsearch                     # noqa: E402
    from replicate import TABLE7_SPECS, load_pair, PANEL_PATH  # noqa: E402

    spec_row = next(s for s in TABLE7_SPECS if s[9] == "FTSE100 w/out drift")
    equity_col, start, end, z_min, z_max, gl, mg, spec, mode, label, skip, tlag = spec_row
    y, z = load_pair(PANEL_PATH, equity_col, "mcsi", start, end, skip=skip, trigger_lag=tlag)

    z_th = z[1:]
    grid = np.linspace(z_min, z_max, gl)
    i_idx, j_idx, rss_values = [], [], []
    for i in range(gl - 1):
        for j in range(i, gl - mg):
            stats = gridsearch(y, z, grid[i], grid[j + mg], spec, mode)
            i_idx.append(i)
            j_idx.append(j + mg)
            rss_values.append(stats["RSS"])
    rss = np.asarray(rss_values, dtype=float)
    i_idx, j_idx = np.asarray(i_idx), np.asarray(j_idx)
    k_opt = int(np.argmin(rss))
    i_opt, j_opt = i_idx[k_opt], j_idx[k_opt]

    # Whole-grid range - includes far-off-optimum pairs, expected to be large.
    flat_pct_whole = 100.0 * (rss.max() - rss.min()) / rss.min()

    # Narrower, more literal reading of "the RSS surface is flat": how much RSS
    # varies AMONG NEAR-OPTIMAL pairs only. Two slices through the optimum:
    #   fixed c1 at its optimal grid index, c2 varies (the "column")
    #   fixed c2 at its optimal grid index, c1 varies (the "row")
    col = rss[i_idx == i_opt]     # c1 fixed, c2 varies
    row_slice = rss[j_idx == j_opt]  # c2 fixed, c1 varies
    flat_pct_col = 100.0 * (col.max() - col.min()) / col.min() if len(col) > 1 else float("nan")
    flat_pct_row = 100.0 * (row_slice.max() - row_slice.min()) / row_slice.min() \
        if len(row_slice) > 1 else float("nan")

    # Top-K near-optimal pairs by RSS (smallest K), regardless of grid position.
    order = np.argsort(rss)
    top10 = rss[order[:10]]
    flat_pct_top10 = 100.0 * (top10.max() - top10.min()) / top10.min()

    candidates = {"whole_grid": flat_pct_whole, "fixed_c1_col": flat_pct_col,
                 "fixed_c2_row": flat_pct_row, "top10_by_rss": flat_pct_top10}
    closest_name = min(candidates, key=lambda k: abs(candidates[k] - 0.018))

    row = {"market": "FTSE100", "spec": "no_drift", "n_grid_pairs": len(rss),
          "rss_min": round(float(rss.min()), 6), "rss_max": round(float(rss.max()), 6),
          "flat_pct_whole_grid": round(flat_pct_whole, 4),
          "flat_pct_fixed_c1_col": round(flat_pct_col, 4),
          "flat_pct_fixed_c2_row": round(flat_pct_row, 4),
          "flat_pct_top10_by_rss": round(flat_pct_top10, 4),
          "closest_to_target_0.018pct": closest_name}
    print(f"  RSS flatness (FTSE100, no-drift): {len(rss)} pairs, target 0.018% -> "
         f"whole_grid={flat_pct_whole:.3f}%  fixed_c1_col={flat_pct_col:.4f}%  "
         f"fixed_c2_row={flat_pct_row:.4f}%  top10={flat_pct_top10:.4f}%  "
         f"(closest: {closest_name})")

    path = os.path.join(config.ensure_rebuilt_dir(), "rss_flatness_ftse_nodrift.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
    print("    -> rss_flatness_ftse_nodrift.csv (1 row)")
    return row


def main():
    from replicate import TABLE7_SPECS, TABLE8_SPECS, load_pair, PANEL_PATH, DAILY_PANEL_PATH  # noqa: E402

    print("C1 - A&S Table 7/8 replication export\n")
    export_table(TABLE7_SPECS, load_pair, PANEL_PATH, "mcsi", "replicate_table7.csv")
    export_table(TABLE8_SPECS, load_pair, DAILY_PANEL_PATH, "vix", "replicate_table8.csv")
    print()
    rss_flatness_ftse_nodrift()


if __name__ == "__main__":
    main()
