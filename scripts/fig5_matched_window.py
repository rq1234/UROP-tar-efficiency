"""
Regenerate Figure 5.1a (ATHEX/Greece) and 5.2a (BIST100/Turkey) on the matched
window, pairing with the already-correct 5.1b/5.2b (country-CCI plots, which
land on the matched window by construction since country CCI data simply
doesn't exist outside it).

The existing plot_global_cci() in src/country_cci_study.py always plots the
full 1990-2026 sample, so 5.1a/5.2a currently show a different window than
5.1b/5.2b and a referee cannot read the trigger contrast off the pair.

This does NOT just crop the full-sample plot to a shorter x-axis - it refits
thresholds on the matched window exactly the way
scripts/dependence_corrections.py's x4_matched_window() does (same
month-intersection logic, same fastgrid.optimal_from_parts call), so the
regenerated figure's RW/MR/EXP split matches the already-verified numbers in
results/exports/matched_window_localisation.csv (Greece 83.0% RW, Turkey
38.3% RW under the global trigger) rather than some other window-dependent
split.

Output: outputs/rebuilt/fig5_1a_athex_matched_GCCI.png
        outputs/rebuilt/fig5_2a_bist100_matched_GCCI.png

Usage:
    python scripts/fig5_matched_window.py
"""
import csv
import os
import sys

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                        # noqa: E402
from estimate import _assign_states                   # noqa: E402
from fastgrid import optimal_from_parts                # noqa: E402
from global_cci_study import load_global_cci_pair       # noqa: E402
from market_config import MARKETS                      # noqa: E402
from threshold_bootstrap import grid_bounds             # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs", "rebuilt")
CHECK_CSV = os.path.join(ROOT, "results", "exports", "matched_window_localisation.csv")

_REGIME_COLORS = {
    0: ("#d0d0d0", 0.20),           # RW  - light grey
    1: ("cornflowerblue", 0.30),    # MR  - blue
    2: ("tomato", 0.35),            # EXP - red
}

MARKET_SPECS = {
    "athex":   ("GRC", "fig5_1a_athex_matched_GCCI.png"),
    "bist100": ("TUR", "fig5_2a_bist100_matched_GCCI.png"),
}


def _shade_regimes(ax, dates, state):
    if len(state) == 0:
        return
    chg = np.flatnonzero(np.diff(state, prepend=state[0] - 1))
    ends = np.append(chg[1:], len(state))
    for si, ei in zip(chg, ends):
        color, alpha = _REGIME_COLORS[int(state[si])]
        ax.axvspan(dates[si], dates[ei - 1], color=color, alpha=alpha, lw=0)


def _matched_window_global(market, oecd_code):
    """Same month-intersection + refit logic as dependence_corrections.x4_matched_window(),
    kept here as arrays instead of a summary dict so the figure can be drawn."""
    y, z, dates = load_global_cci_pair(market, config.START, None)
    months = pd.to_datetime(dates).to_period("M")

    cpath = os.path.join(config.DATA, "sentiment", f"oecd_cci_{oecd_code}.csv")
    cs = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
    cs.index = pd.to_datetime(cs.index).to_period("M")

    keep = np.array([m in set(cs.index) for m in months])
    ym, zm, mm = y[keep], z[keep], months[keep]

    dep, x, zt = np.diff(ym), ym[:-1], zm[1:]
    zmin, zmax, mg = grid_bounds(zm)
    c1, c2 = optimal_from_parts(dep, x, zt, zmin, zmax, config.GRID_LENGTH, mg)
    state = _assign_states(zt, c1, c2)

    plot_dates = mm[1:].to_timestamp(how="end")
    return ym[1:], state, c1, c2, plot_dates


def _load_check_row(market):
    with open(CHECK_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["market"] == market:
                return row
    raise KeyError(f"{market} not found in {CHECK_CSV}")


def make_figure(market, oecd_code, filename):
    y, state, c1, c2, dates = _matched_window_global(market, oecd_code)
    T = len(state)
    mr_pct = 100 * (state == 1).sum() / T
    rw_pct = 100 * (state == 0).sum() / T
    exp_pct = 100 * (state == 2).sum() / T

    check = _load_check_row(market)
    target_rw = float(check["global_RW"])
    target_mr = float(check["global_MR"])
    target_exp = float(check["global_EXP"])
    diffs = (abs(rw_pct - target_rw), abs(mr_pct - target_mr), abs(exp_pct - target_exp))
    assert max(diffs) < 0.2, (
        f"{market}: regenerated split {mr_pct:.1f}/{rw_pct:.1f}/{exp_pct:.1f} does not match "
        f"matched_window_localisation.csv global {target_mr}/{target_rw}/{target_exp}"
    )

    country = MARKETS[market]["country"]
    fig, ax = plt.subplots(figsize=(13, 4))
    _shade_regimes(ax, dates, state)
    ax.plot(dates, y, color="black", linewidth=0.7, zorder=3)

    ax.set_title(
        f"{market.upper()} ({country}) - TAR regimes under Global OECD CCI, "
        f"matched window [c₁={c1:.2f}, c₂={c2:.2f}]   "
        f"MR={mr_pct:.0f}%  RW={rw_pct:.0f}%  EXP={exp_pct:.0f}%",
        fontsize=8,
    )
    ax.set_ylabel("Log equity price", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0)

    legend_patches = [
        mpatches.Patch(color="cornflowerblue", alpha=0.60, label="MR - mean-reverting"),
        mpatches.Patch(color="#d0d0d0", alpha=0.80, label="RW - efficient"),
        mpatches.Patch(color="tomato", alpha=0.70, label="EXP - explosive"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="upper left")

    plt.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, filename)
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"{market:<10} window {dates[0].strftime('%Y-%m')}..{dates[-1].strftime('%Y-%m')}  "
          f"T={T}  MR={mr_pct:.1f}%  RW={rw_pct:.1f}%  EXP={exp_pct:.1f}%  "
          f"(matches matched_window_localisation.csv within {max(diffs):.2f}pp)")
    print(f"  Saved: {out}")


def main():
    for market, (code, filename) in MARKET_SPECS.items():
        make_figure(market, code, filename)


if __name__ == "__main__":
    main()
