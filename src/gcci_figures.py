"""
Global OECD CCI cross-market analysis — efficiency ranking and regime plots.

Reads results from results/tables/global_cci_all_markets.csv (produced by
`python global_cci_study.py estimate`) and generates paper-ready outputs in
a dedicated results/gcci/ folder:

  results/gcci/efficiency_ranking.csv   — markets sorted by RW% with region labels
  results/gcci/regimes_*_GCCI.png       — regime-shaded equity price plots

Usage:
    cd src && python gcci_figures.py            # ranking + plots
    python gcci_figures.py ranking              # Task 5 only
    python gcci_figures.py plots                # Task 6 only
    python gcci_figures.py plots nikkei225 aex  # custom market list
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(__file__))
from estimate         import _assign_states
from market_config    import MARKETS
from bubble_now       import FULL_END
from global_cci_study import load_global_cci_pair, START

RESULTS_CSV = os.path.join(os.path.dirname(__file__), "..", "results", "tables",
                           "global_cci_all_markets.csv")
GCCI_DIR    = os.path.join(os.path.dirname(__file__), "..", "results", "gcci")

REPRESENTATIVE = ["nikkei225", "hangseng", "bovespa", "ibex35", "shanghai"]

_REGIME_COLORS = {
    0: ("#d0d0d0", 0.20),           # RW  — light grey
    1: ("cornflowerblue", 0.30),    # MR  — blue
    2: ("tomato", 0.35),            # EXP — red
}


def _shade_regimes(ax, dates, state):
    """Shaded background by regime (same colour convention as bubble_now.py)."""
    if len(state) == 0:
        return
    chg  = np.flatnonzero(np.diff(state, prepend=state[0] - 1))
    ends = np.append(chg[1:], len(state))
    for si, ei in zip(chg, ends):
        color, alpha = _REGIME_COLORS[int(state[si])]
        ax.axvspan(dates[si], dates[ei - 1], color=color, alpha=alpha, lw=0)


# ---------------------------------------------------------------------------
# Task 5 — Cross-market efficiency ranking
# ---------------------------------------------------------------------------

def efficiency_ranking():
    """Sort admissible markets by RW% and save with regional labels."""
    df = pd.read_csv(RESULTS_CSV)
    df["mr_pct"]  = df["n_mr"] / df["T"] * 100
    df["rw_pct"]  = df["n_rw"] / df["T"] * 100
    df["exp_pct"] = df["n_ex"] / df["T"] * 100
    df["region"]       = df["market"].apply(lambda m: MARKETS[m]["region"]       if m in MARKETS else "Other")
    df["market_class"] = df["market"].apply(lambda m: MARKETS[m]["market_class"] if m in MARKETS else "Other")

    df_sorted = df.sort_values("rw_pct", ascending=False).reset_index(drop=True)

    print(f"\n{'='*72}")
    print("CROSS-MARKET EFFICIENCY RANKING (Global OECD CCI, sorted by RW%)")
    print(f"{'='*72}")
    print(f"{'#':>3}  {'Market':<14} {'Country':<18} {'Class':<9} {'Region':<16}  "
          f"{'RW%':>5} {'MR%':>5} {'EXP%':>5}  {'b_MR':>7} {'b_EX':>7}  Now")
    print("-" * 92)
    for i, r in df_sorted.iterrows():
        b_mr = f"{r['beta_mr']:>+7.4f}" if pd.notna(r.get("beta_mr")) else "     --"
        b_ex = f"{r['beta_ex']:>+7.4f}" if pd.notna(r.get("beta_ex")) else "     --"
        print(f"{i+1:>3}  {r['market']:<14} {r['country']:<18} {r['market_class']:<9} {r['region']:<16}  "
              f"{r['rw_pct']:>4.0f}% {r['mr_pct']:>4.0f}% {r['exp_pct']:>4.0f}%  "
              f"{b_mr} {b_ex}  {r.get('current_regime', '--')}")

    os.makedirs(GCCI_DIR, exist_ok=True)
    keep_cols = [
        "market", "country", "region", "market_class", "T",
        "rw_pct", "mr_pct", "exp_pct",
        "c1", "c2",
        "beta_mr", "se_mr", "sig_mr",
        "beta_ex", "se_ex", "sig_ex",
        "dc_exp", "gfc_mr", "covid_mr",
        "current_cci", "current_regime", "verdict",
    ]
    out = os.path.join(GCCI_DIR, "efficiency_ranking.csv")
    df_sorted[[c for c in keep_cols if c in df_sorted.columns]].to_csv(out, index=False)
    print(f"\nSaved: {out}")
    return df_sorted


# ---------------------------------------------------------------------------
# Task 6 — Regime-shaded equity plots
# ---------------------------------------------------------------------------

def plot_market(market, saved_df):
    """Single-panel regime-shaded log-price plot for one market."""
    y, z, dates = load_global_cci_pair(market, START, FULL_END)
    c1 = float(saved_df.loc[market, "c1"])
    c2 = float(saved_df.loc[market, "c2"])
    state = _assign_states(z[1:], c1, c2)

    country = MARKETS[market]["country"]
    T = len(state)
    mr_pct  = 100 * (state == 1).sum() / T
    rw_pct  = 100 * (state == 0).sum() / T
    exp_pct = 100 * (state == 2).sum() / T

    fig, ax = plt.subplots(figsize=(13, 4))
    _shade_regimes(ax, dates[1:], state)
    ax.plot(dates[1:], y[1:], color="black", linewidth=0.7, zorder=3)

    ax.set_title(
        f"{market.upper()} ({country}) — TAR regimes under Global OECD CCI  "
        f"[c₁={c1:.2f}, c₂={c2:.2f}]   "
        f"MR={mr_pct:.0f}%  RW={rw_pct:.0f}%  EXP={exp_pct:.0f}%",
        fontsize=8,
    )
    ax.set_ylabel("Log equity price", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0)

    legend_patches = [
        mpatches.Patch(color="cornflowerblue", alpha=0.60, label="MR — mean-reverting"),
        mpatches.Patch(color="#d0d0d0",        alpha=0.80, label="RW — efficient"),
        mpatches.Patch(color="tomato",         alpha=0.70, label="EXP — explosive"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="upper left")

    plt.tight_layout()
    os.makedirs(GCCI_DIR, exist_ok=True)
    out = os.path.join(GCCI_DIR, f"regimes_{market}_GCCI.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


def regime_plots(markets=None):
    """Generate regime-shaded plots for a list of markets (default: REPRESENTATIVE)."""
    if markets is None:
        markets = REPRESENTATIVE
    saved_df = pd.read_csv(RESULTS_CSV).set_index("market")
    missing = [m for m in markets if m not in saved_df.index]
    if missing:
        print(f"  WARNING: {missing} not in results CSV — skipping")
        markets = [m for m in markets if m in saved_df.index]

    print(f"\n{'='*55}")
    print(f"REGIME PLOTS — {len(markets)} markets (Global OECD CCI)")
    print(f"{'='*55}")
    for market in markets:
        print(f"  {market:<14} ...", end="", flush=True)
        try:
            plot_market(market, saved_df)
        except Exception as e:
            print(f"  ERROR: {e}")


# ---------------------------------------------------------------------------
# Shared paths for chart data
# ---------------------------------------------------------------------------

RANKING_CSV    = os.path.join(GCCI_DIR, "efficiency_ranking.csv")
HORIZON_CSV    = os.path.join(GCCI_DIR, "horizon_test.csv")
EXP_PHASE_CSV  = os.path.join(GCCI_DIR, "horizon_test_exp_phase.csv")

CLASS_COLORS = {
    "DM":       "#4878CF",   # blue
    "EM":       "#D65F5F",   # red
    "Frontier": "#C4AD66",   # khaki/gold
}


def _sig_star(p):
    if pd.isna(p):     return ""
    if p < 0.001:      return "***"
    if p < 0.01:       return "**"
    if p < 0.05:       return "*"
    return ""


# ---------------------------------------------------------------------------
# Chart 1 — Cross-market efficiency ranking (horizontal bar)
# ---------------------------------------------------------------------------

def chart_efficiency_ranking():
    """Horizontal bar chart: RW% sorted high→low, labelled by country name."""
    df = pd.read_csv(RANKING_CSV)   # already sorted by rw_pct desc

    colors = ["#5B8DB8"] * len(df)
    labels = df["country"].tolist()

    fig, ax = plt.subplots(figsize=(9, 10))
    bars = ax.barh(range(len(df)), df["rw_pct"], color=colors, edgecolor="white",
                   linewidth=0.4, height=0.75)

    for i, (val, bar) in enumerate(zip(df["rw_pct"], bars)):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}%", va="center", ha="left", fontsize=7)

    ax.axvline(50, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("Random Walk % (RW regime share)", fontsize=9)
    ax.set_title(f"Cross-market efficiency ranking under Global OECD CCI\n"
                 f"{len(df)} admissible markets, full sample", fontsize=9)
    ax.set_xlim(0, 108)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    os.makedirs(GCCI_DIR, exist_ok=True)
    out = os.path.join(GCCI_DIR, "chart_efficiency_ranking.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Chart 2 — Horizon test grouped bar chart
# ---------------------------------------------------------------------------

def chart_horizon_test():
    """Grouped bar: MR / RW / EXP mean forward returns at 1, 3, 6, 12-month horizons."""
    df = pd.read_csv(HORIZON_CSV)

    horizons   = df["horizon"].tolist()
    mr_vals    = df["MR_mean_pct"].tolist()
    rw_vals    = df["RW_mean_pct"].tolist()
    exp_vals   = df["EXP_mean_pct"].tolist()
    mr_rw_p    = df["MR_vs_RW_p"].tolist()
    exp_rw_p   = df["EXP_vs_RW_p"].tolist()

    x     = np.arange(len(horizons))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 5))
    b_mr  = ax.bar(x - width, mr_vals,  width, color="cornflowerblue", label="MR (mean-reverting)", zorder=3)
    b_rw  = ax.bar(x,          rw_vals,  width, color="lightgrey",     label="RW (efficient)",      zorder=3, edgecolor="grey", linewidth=0.5)
    b_exp = ax.bar(x + width,  exp_vals, width, color="tomato",        label="EXP (explosive)",     zorder=3)

    ax.axhline(0, color="black", linewidth=0.8, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}m" for h in horizons], fontsize=9)
    ax.set_ylabel("Mean forward log-return (%)", fontsize=9)
    ax.set_xlabel("Horizon", fontsize=9)
    ax.set_title("Pooled forward returns by TAR regime — Global OECD CCI\n"
                 "27 admissible markets; significance vs RW baseline", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5, zorder=0)

    # Significance stars above bars (MR vs RW and EXP vs RW)
    for i, (mv, ev, mp, ep) in enumerate(zip(mr_vals, exp_vals, mr_rw_p, exp_rw_p)):
        star_mr  = _sig_star(mp)
        star_exp = _sig_star(ep)
        offset   = 0.15
        if star_mr:
            ax.text(i - width, mv + offset, star_mr,  ha="center", va="bottom", fontsize=8, fontweight="bold")
        if star_exp:
            ax.text(i + width, ev - offset, star_exp, ha="center", va="top",    fontsize=8, fontweight="bold",
                    color="firebrick")

    ax.legend(fontsize=8, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(GCCI_DIR, "chart_horizon_test.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Chart 3 — Early vs late EXP bar chart
# ---------------------------------------------------------------------------

def chart_early_late_exp():
    """Grouped bar: early-EXP vs late-EXP forward returns at each horizon."""
    df = pd.read_csv(EXP_PHASE_CSV)

    horizons    = df["horizon"].tolist()
    early_vals  = df["early_EXP_mean_pct"].tolist()
    late_vals   = df["late_EXP_mean_pct"].tolist()
    phase_p     = df["early_vs_late_p"].tolist()

    x     = np.arange(len(horizons))
    width = 0.3

    fig, ax = plt.subplots(figsize=(8, 5))
    b_early = ax.bar(x - width / 2, early_vals, width, color="coral",     label="Early EXP (bubble inflation)", zorder=3)
    b_late  = ax.bar(x + width / 2, late_vals,  width, color="firebrick", label="Late EXP (extended/peak)",     zorder=3)

    ax.axhline(0, color="black", linewidth=0.8, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}m" for h in horizons], fontsize=9)
    ax.set_ylabel("Mean forward log-return (%)", fontsize=9)
    ax.set_xlabel("Horizon", fontsize=9)
    ax.set_title("Early vs late EXP phase — pooled forward returns\n"
                 "Japan excluded (degenerate threshold); *** p<0.001 for all horizons", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5, zorder=0)

    # Significance stars between bars
    for i, (ev, lv, p) in enumerate(zip(early_vals, late_vals, phase_p)):
        star = _sig_star(p)
        if star:
            top = max(ev, 0) + 0.3
            ax.text(i, top, star, ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.legend(fontsize=8, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(GCCI_DIR, "chart_early_late_exp.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Chart 4 — Threshold consistency strip chart
# ---------------------------------------------------------------------------

def chart_thresholds():
    """Scatter of c1 and c2 across all 27 markets sorted by RW% (high→low)."""
    df = pd.read_csv(RANKING_CSV)
    n  = len(df)
    x  = np.arange(n)

    fig, ax = plt.subplots(figsize=(13, 5))

    # Shaded cluster bands
    ax.axhspan(96.8, 98.2, color="cornflowerblue", alpha=0.08, zorder=0)
    ax.axhspan(100.8, 102.5, color="tomato",       alpha=0.08, zorder=0)

    ax.scatter(x, df["c2"], marker="D", s=45, color="tomato",
               label="c₂ (upper — EXP threshold)", zorder=3)
    ax.scatter(x, df["c1"], marker="o", s=45, color="cornflowerblue",
               label="c₁ (lower — MR threshold)", zorder=3)
    ax.axhline(100, color="black", linewidth=0.9, linestyle="--",
               alpha=0.7, label="CCI = 100 (long-run mean)", zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(df["market"], rotation=45, ha="right", fontsize=7.5)
    ax.set_ylabel("Global OECD CCI level", fontsize=9)
    ax.set_title(f"Optimal TAR thresholds across {n} admissible markets (sorted by RW%)\n"
                 "Shaded bands: c₁ cluster 96.8–98.2, c₂ cluster 100.8–102.5", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(GCCI_DIR, "chart_thresholds.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Chart 5 — Episode coverage heatmap
# ---------------------------------------------------------------------------

def chart_episode_heatmap():
    """Heatmap: episode coverage % for dot-com / GFC / COVID across 27 markets."""
    df  = pd.read_csv(RANKING_CSV)
    ep_cols  = ["dc_exp", "gfc_mr", "covid_mr"]
    ep_labels = ["Dot-com\n(EXP%)", "GFC\n(MR%)", "COVID\n(MR%)"]

    data   = df[ep_cols].values.astype(float)   # (27, 3), may contain NaN
    masked = np.ma.masked_invalid(data)

    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad("lightgrey")

    fig, ax = plt.subplots(figsize=(5, 11))
    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=0, vmax=100)

    # Cell annotations
    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            val = data[r, c]
            txt = f"{val:.0f}%" if not np.isnan(val) else "–"
            color = "black" if (np.isnan(val) or val < 70) else "white"
            ax.text(c, r, txt, ha="center", va="center", fontsize=7.5,
                    color=color, fontweight="bold" if not np.isnan(val) else "normal")

    ax.set_xticks(range(len(ep_labels)))
    ax.set_xticklabels(ep_labels, fontsize=8.5)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(
        [f"{m} ({c})" for m, c in zip(df["market"], df["country"])],
        fontsize=7.5,
    )
    ax.set_title("Historical episode coverage\n(% of episode months in expected regime)",
                 fontsize=9, pad=10)
    ax.tick_params(length=0)

    cb = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Coverage %", fontsize=8)
    cb.ax.tick_params(labelsize=7)

    plt.tight_layout()
    out = os.path.join(GCCI_DIR, "chart_episode_heatmap.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_charts():
    print(f"\n{'='*55}")
    print("GENERATING PAPER CHARTS (5 total)")
    print(f"{'='*55}")
    chart_efficiency_ranking()
    chart_horizon_test()
    chart_early_late_exp()
    chart_thresholds()
    chart_episode_heatmap()
    print(f"\nAll charts saved to: {os.path.abspath(GCCI_DIR)}")


def run_all():
    efficiency_ranking()
    regime_plots()
    run_all_charts()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "ranking":          efficiency_ranking,
        "plots":            lambda: regime_plots(sys.argv[2:] if len(sys.argv) > 2 else None),
        "charts":           run_all_charts,
        "chart_efficiency": chart_efficiency_ranking,
        "chart_horizon":    chart_horizon_test,
        "chart_exp_phase":  chart_early_late_exp,
        "chart_thresholds": chart_thresholds,
        "chart_heatmap":    chart_episode_heatmap,
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()
