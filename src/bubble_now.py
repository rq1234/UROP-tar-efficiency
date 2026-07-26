"""
Workstream 1 — current bubble call, extended to June 2026.

Two estimation approaches for four core (market, trigger) pairs (Tables 7 & 8):
  A) Full-sample refit   — c1/c2 minimising RSS on full history to 2026.
  B) Out-of-sample (OOS) — c1/c2 fixed from 1990–2015, applied to 1990–2026.

Deliverables:
  results/figures/bubble_now_{label}.png  — regime-shaded equity time-series
  results/tables/bubble_now_last12m.csv   — last-12-months regime table

Usage:
    cd src && python bubble_now.py          # full pipeline
    python bubble_now.py plot               # plots only
    python bubble_now.py table              # table only
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.dirname(__file__))
from estimate import find_optimal_thresholds, _assign_states
from replicate import PANEL_PATH, DAILY_PANEL_PATH

FIGURES_DIR   = os.path.join(os.path.dirname(__file__), "..", "results", "figures")
TABLES_DIR    = os.path.join(os.path.dirname(__file__), "..", "results", "tables")
SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
COVERAGE_PATH = os.path.join(SENTIMENT_DIR, "oecd_cci_coverage.csv")
FULL_END      = "2026-06"
INSAMPLE_END  = "2015-06"
CCI_START     = "1990-01"

# (freq, equity_col, trigger, insample_start, z_min, z_max, gridlen, mingap, spec, tlag, label)
#
# Grid bounds from the paper are used for both Options A and B.
# They are economically anchored (MCSI < 57 = extreme recession, VIX > 70 = crisis peak)
# and prevent degenerate solutions.  Data outside the grid range falls naturally into
# the appropriate tail regime regardless of where the optimal threshold lands.
PAIR_SPECS = [
    ("monthly", "eq_sp500",   "mcsi", "1978-01", 57, 110, 100, 4, 1, 0, "SP500_MCSI"),
    ("monthly", "eq_ftse100", "mcsi", "1984-01", 57, 110, 100, 4, 1, 0, "FTSE100_MCSI"),
    ("daily",   "eq_sp500",   "vix",  "1990-02", 10,  70, 200, 6, 1, 1, "SP500_VIX"),
    ("daily",   "eq_ftse100", "vix",  "1990-02", 10,  70, 200, 6, 1, 2, "FTSE100_VIX"),
]

_REGIME_NAMES  = {0: "RW", 1: "MR", 2: "EXP"}
_REGIME_COLORS = {
    0: ("#d0d0d0", 0.20),          # RW — light grey
    1: ("cornflowerblue", 0.30),   # MR — blue
    2: ("tomato", 0.35),           # EXP — red
}


def _panel_path(freq):
    return DAILY_PANEL_PATH if freq == "daily" else PANEL_PATH


def load_pair_with_dates(panel_path, equity_col, trigger_col, start, end, trigger_lag=0):
    """
    Load (y, z, dates) aligned for TAR estimation.

    Mirrors replicate.load_pair() but also returns the DatetimeIndex so callers
    can attach regimes to calendar dates without re-reading the panel.
    """
    panel = pd.read_csv(panel_path, index_col="date", parse_dates=True)
    pair  = panel[[equity_col, trigger_col]].dropna().loc[start:end]
    log_p = np.log(pair[equity_col].values).astype(float)
    trig  = pair[trigger_col].values.astype(float)
    dates = np.array(pair.index, dtype="datetime64[ns]")  # handles str or DatetimeIndex
    if trigger_lag > 0:
        log_p = log_p[trigger_lag:]
        trig  = trig[:-trigger_lag]
        dates = dates[trigger_lag:]
    return log_p, trig, dates


def _fit(y, z, z_min, z_max, gridlen, mingap, spec):
    return find_optimal_thresholds(y, z, z_min, z_max, gridlen, mingap, spec, "returns")


# ---------------------------------------------------------------------------
# Option A — full-sample refit
# ---------------------------------------------------------------------------

def run_option_a(spec):
    """Refit on full history (insample_start–2026) with the same grid bounds as the paper."""
    freq, eq, trig, start, z_min, z_max, gl, mg, sp, tlag, label = spec
    y, z, dates = load_pair_with_dates(_panel_path(freq), eq, trig, start, FULL_END, tlag)
    print(f"  [{label}] A  T={len(y)}  z=[{z.min():.1f}, {z.max():.1f}]  ...", end="", flush=True)
    opt   = _fit(y, z, z_min, z_max, gl, mg, sp)
    state = _assign_states(z[1:], opt["c1"], opt["c2"])
    T = len(state)
    print(f"  c1={opt['c1']:.1f}  c2={opt['c2']:.1f}  "
          f"MR={100*(state==1).sum()/T:.0f}%  "
          f"RW={100*(state==0).sum()/T:.0f}%  "
          f"EXP={100*(state==2).sum()/T:.0f}%")
    return {"c1": opt["c1"], "c2": opt["c2"], "state": state,
            "dates": dates[1:], "y": y, "label": label}


# ---------------------------------------------------------------------------
# Option B — out-of-sample classification with fixed thresholds
# ---------------------------------------------------------------------------

def run_option_b(spec):
    """Fix c1/c2 from in-sample (to 2015-06); classify the full 1990–2026 period."""
    freq, eq, trig, start, z_min, z_max, gl, mg, sp, tlag, label = spec
    path = _panel_path(freq)

    # Phase 1: in-sample fit (original paper window)
    y_in, z_in, _ = load_pair_with_dates(path, eq, trig, start, INSAMPLE_END, tlag)
    print(f"  [{label}] B  in-sample T={len(y_in)}  ...", end="", flush=True)
    opt = _fit(y_in, z_in, z_min, z_max, gl, mg, sp)
    print(f"  c1={opt['c1']:.1f}  c2={opt['c2']:.1f}")

    # Phase 2: apply fixed thresholds to the full extended period
    y, z, dates = load_pair_with_dates(path, eq, trig, start, FULL_END, tlag)
    state = _assign_states(z[1:], opt["c1"], opt["c2"])

    oos_mask = dates[1:] > np.datetime64("2015-06-30", "ns")
    if oos_mask.any():
        oos_s = state[oos_mask]
        n = len(oos_s)
        print(f"    OOS ({n} obs post-{INSAMPLE_END}):  "
              f"MR={100*(oos_s==1).sum()/n:.0f}%  "
              f"RW={100*(oos_s==0).sum()/n:.0f}%  "
              f"EXP={100*(oos_s==2).sum()/n:.0f}%")

    return {"c1": opt["c1"], "c2": opt["c2"], "state": state,
            "dates": dates[1:], "y": y, "label": label}


# ---------------------------------------------------------------------------
# CCI trigger — data loading and estimation
# ---------------------------------------------------------------------------

def _cci_specs():
    """
    Load CCI pair specs for all usable markets from oecd_cci_coverage.csv.
    Returns list of (market, oecd_code, country, z_min, z_max, label) tuples.
    """
    if not os.path.exists(COVERAGE_PATH):
        print("  WARNING: oecd_cci_coverage.csv not found — run collect_oecd.py first.")
        return []
    cov = pd.read_csv(COVERAGE_PATH)
    specs = []
    for _, row in cov.iterrows():
        if not row["usable"]:
            continue
        label = f"{row['market'].upper()}_CCI"
        specs.append((
            row["market"], row["oecd_code"], row["country"],
            float(row["z_min"]), float(row["z_max"]), label,
        ))
    return specs


def load_cci_with_dates(market, oecd_code, start, end):
    """
    Load (y, z, dates) for a (market, CCI) pair.

    Adapted from cci_study.load_cci_pair(): reads equity from the monthly panel
    and CCI levels from data/sentiment/oecd_cci_{code}.csv, aligning both to
    month-end dates before joining.
    """
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()

    cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{oecd_code}.csv")
    cci = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna()
    cci.index = cci.index + pd.offsets.MonthEnd(0)  # align to month-end

    df = pd.DataFrame({"price": prices, "cci": cci}).dropna().loc[start:end]

    y     = np.log(df["price"].values).astype(float)
    z     = df["cci"].values.astype(float)
    dates = np.array(df.index, dtype="datetime64[ns]")
    return y, z, dates


def _cci_min_gap(z_min, z_max, gridlen=100):
    """Minimum grid-index gap enforcing a 2-point absolute CCI band (cci_study.py line 278)."""
    grid_step = (z_max - z_min) / (gridlen - 1)
    return max(4, int(2.0 / grid_step))


def run_option_a_cci(spec):
    """Full-sample refit for a (market, CCI) pair using expanded history to 2026."""
    market, oecd_code, country, z_min, z_max, label = spec
    y, z, dates = load_cci_with_dates(market, oecd_code, CCI_START, FULL_END)
    gl, mg = 100, _cci_min_gap(z_min, z_max)
    print(f"  [{label}] A  T={len(y)}  z=[{z.min():.2f}, {z.max():.2f}]  ...", end="", flush=True)
    opt   = _fit(y, z, z_min, z_max, gl, mg, 1)
    state = _assign_states(z[1:], opt["c1"], opt["c2"])
    T = len(state)
    print(f"  c1={opt['c1']:.2f}  c2={opt['c2']:.2f}  "
          f"MR={100*(state==1).sum()/T:.0f}%  "
          f"RW={100*(state==0).sum()/T:.0f}%  "
          f"EXP={100*(state==2).sum()/T:.0f}%")
    return {"c1": opt["c1"], "c2": opt["c2"], "state": state,
            "dates": dates[1:], "y": y, "label": label}


def run_option_b_cci(spec):
    """OOS CCI: c1/c2 fixed from 1990–2015 in-sample fit, classify through 2026."""
    market, oecd_code, country, z_min, z_max, label = spec
    gl, mg = 100, _cci_min_gap(z_min, z_max)

    y_in, z_in, _ = load_cci_with_dates(market, oecd_code, CCI_START, INSAMPLE_END)
    print(f"  [{label}] B  in-sample T={len(y_in)}  ...", end="", flush=True)
    opt = _fit(y_in, z_in, z_min, z_max, gl, mg, 1)
    print(f"  c1={opt['c1']:.2f}  c2={opt['c2']:.2f}")

    y, z, dates = load_cci_with_dates(market, oecd_code, CCI_START, FULL_END)
    state = _assign_states(z[1:], opt["c1"], opt["c2"])

    oos_mask = dates[1:] > np.datetime64("2015-06-30", "ns")
    if oos_mask.any():
        oos_s = state[oos_mask]
        n = len(oos_s)
        print(f"    OOS ({n} obs post-{INSAMPLE_END}):  "
              f"MR={100*(oos_s==1).sum()/n:.0f}%  "
              f"RW={100*(oos_s==0).sum()/n:.0f}%  "
              f"EXP={100*(oos_s==2).sum()/n:.0f}%")

    return {"c1": opt["c1"], "c2": opt["c2"], "state": state,
            "dates": dates[1:], "y": y, "label": label}


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _shade_regimes(ax, dates, state):
    """Draw axvspan background shading, grouped into contiguous same-regime runs."""
    if len(state) == 0:
        return
    # Run-length encode: find every index where the regime changes
    chg  = np.flatnonzero(np.diff(state, prepend=state[0] - 1))
    ends = np.append(chg[1:], len(state))
    for si, ei in zip(chg, ends):
        color, alpha = _REGIME_COLORS[int(state[si])]
        ax.axvspan(dates[si], dates[ei - 1], color=color, alpha=alpha, lw=0)


def plot_pair(spec, result_a, result_b):
    """Save a two-panel (Option A / Option B) regime-shaded figure for one pair."""
    label = spec[-1]
    os.makedirs(FIGURES_DIR, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    panel_configs = [
        (result_a,
         f"Option A — full-sample refit  "
         f"(c₁={result_a['c1']:.1f}, c₂={result_a['c2']:.1f})"),
        (result_b,
         f"Option B — OOS  "
         f"(c₁={result_b['c1']:.1f}, c₂={result_b['c2']:.1f}  fixed at {INSAMPLE_END})"),
    ]
    for ax, (result, title) in zip(axes, panel_configs):
        _shade_regimes(ax, result["dates"], result["state"])
        # y[1:] aligns with dates (both length T-1 after lag + diff)
        ax.plot(result["dates"], result["y"][1:], color="black", linewidth=0.6, zorder=3)
        ax.set_title(f"{label}  —  {title}", fontsize=9)
        ax.set_ylabel("log price", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.margins(x=0)

    # Mark the OOS boundary on the bottom panel
    oos_ts = np.datetime64("2015-06-30", "ns")
    axes[1].axvline(oos_ts, color="navy", linewidth=1.1, linestyle="--", alpha=0.80, zorder=4)

    regime_patches = [
        mpatches.Patch(color="cornflowerblue", alpha=0.6, label="MR (mean-reverting)"),
        mpatches.Patch(color="#d0d0d0",        alpha=0.8, label="RW (efficient)"),
        mpatches.Patch(color="tomato",         alpha=0.6, label="EXP (explosive)"),
    ]
    oos_handle = Line2D([0], [0], color="navy", linewidth=1.1, linestyle="--",
                        label=f"OOS boundary ({INSAMPLE_END})")

    axes[0].legend(handles=regime_patches, fontsize=7, loc="upper left")
    axes[1].legend(handles=regime_patches + [oos_handle], fontsize=7, loc="upper left")
    axes[1].set_xlabel("Date", fontsize=8)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, f"bubble_now_{label}.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Regime table — last 12 months
# ---------------------------------------------------------------------------

def regime_table(results_a, results_b, n_months=12,
                 csv_name="bubble_now_last12m.csv"):
    """Print and save last-n-months regime classification for a set of pairs."""
    os.makedirs(TABLES_DIR, exist_ok=True)

    # Build a monthly regime series for each (pair, approach) combination.
    # For daily pairs, resample to month-end by taking the last state per month.
    monthly = {}
    for ra, rb in zip(results_a, results_b):
        lbl = ra["label"]
        for suf, r in [("A", ra), ("B", rb)]:
            s = pd.Series(r["state"], index=pd.DatetimeIndex(r["dates"]))
            monthly[f"{lbl}_{suf}"] = (
                s.resample("ME").last().dropna().map(_REGIME_NAMES)
            )

    df = pd.concat(monthly, axis=1).tail(n_months).fillna("N/A")
    df.index = df.index.strftime("%Y-%m")

    # Use labels from the results themselves (works for any set of pairs)
    labels = [r["label"] for r in results_a]
    width  = 8 + len(labels) * 14
    print(f"\n{'Last ' + str(n_months) + ' months -- bubble regime by market':^{width}}")
    print(f"{'MR=mean-reverting  RW=efficient  EXP=explosive  *=A/B disagree':^{width}}\n")

    header = f"{'Date':<8}"
    for lbl in labels:
        short = lbl.replace("100", "")
        header += f"  {short:^12}"
    print(header)
    sub = f"{'':8}"
    for _ in labels:
        sub += f"  {'A  / B':^12}"
    print(sub)
    print("-" * width)

    for date_str, row in df.iterrows():
        line = f"{date_str:<8}"
        for lbl in labels:
            va   = row.get(f"{lbl}_A", "N/A")
            vb   = row.get(f"{lbl}_B", "N/A")
            flag = "*" if va != vb else " "
            line += f"  {va:>3}/{vb:<3}{flag}    "
        print(line)

    csv_path = os.path.join(TABLES_DIR, csv_name)
    df.to_csv(csv_path)
    print(f"\nSaved: {csv_path}")
    print("  (* = Option A and B disagree on regime)")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def _run_panel():
    """Run Option A + B for the four MCSI/VIX panel pairs."""
    print("\n--- Panel pairs (MCSI + VIX) ---")
    print("Option A: full-sample refit")
    results_a = [run_option_a(s) for s in PAIR_SPECS]
    print("\nOption B: out-of-sample (fixed 2015 thresholds)")
    results_b = [run_option_b(s) for s in PAIR_SPECS]
    return results_a, results_b


def _run_cci():
    """Run Option A + B for all usable CCI pairs."""
    cci_specs = _cci_specs()
    if not cci_specs:
        return [], []
    print(f"\n--- CCI pairs ({len(cci_specs)} markets) ---")
    print("Option A: full-sample refit")
    cci_a = [run_option_a_cci(s) for s in cci_specs]
    print("\nOption B: out-of-sample (fixed 2015 thresholds)")
    cci_b = [run_option_b_cci(s) for s in cci_specs]
    return cci_specs, cci_a, cci_b


def run_all():
    print("=" * 60)
    print("Workstream 1: bubble detection extended to 2026")
    print("=" * 60)

    results_a, results_b = _run_panel()
    cci_specs, cci_a, cci_b = _run_cci()

    print("\n--- Plots ---")
    for spec, ra, rb in zip(PAIR_SPECS, results_a, results_b):
        plot_pair(spec, ra, rb)
    for spec, ra, rb in zip(cci_specs, cci_a, cci_b):
        plot_pair(spec, ra, rb)

    regime_table(results_a, results_b)
    if cci_a:
        regime_table(cci_a, cci_b, csv_name="bubble_now_cci_last12m.csv")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("plot", "table", "cci"):
        results_a, results_b = _run_panel()
        cci_specs, cci_a, cci_b = _run_cci()
        if cmd == "plot":
            for spec, ra, rb in zip(PAIR_SPECS, results_a, results_b):
                plot_pair(spec, ra, rb)
            for spec, ra, rb in zip(cci_specs, cci_a, cci_b):
                plot_pair(spec, ra, rb)
        elif cmd == "table":
            regime_table(results_a, results_b)
            if cci_a:
                regime_table(cci_a, cci_b, csv_name="bubble_now_cci_last12m.csv")
        else:  # cci only
            for spec, ra, rb in zip(cci_specs, cci_a, cci_b):
                plot_pair(spec, ra, rb)
            if cci_a:
                regime_table(cci_a, cci_b, csv_name="bubble_now_cci_last12m.csv")
    else:
        run_all()
