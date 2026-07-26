"""
Country-specific OECD CCI study for Greece (athex/GRC) and Turkey (bist100/TUR).

Uses each country's own CCI as the sentiment trigger, mirroring global_cci_study.py
but with a per-country trigger instead of the global OECD aggregate.

Also generates regime-shaded equity plots using Global CCI thresholds for both markets.

Requires data/sentiment/oecd_cci_GRC.csv and oecd_cci_TUR.csv.
Run `python collect_oecd.py` first if those files are missing.

Usage:
    cd src && python country_cci_study.py
    python country_cci_study.py estimate
    python country_cci_study.py plots
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
from estimate          import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity        import granger_f_test
from market_config     import MARKETS
from replicate         import PANEL_PATH
from bubble_now        import FULL_END
from global_cci_study  import (
    _grid_bounds, _episode_verdict, _episode_coverage, _sig_marker, START,
    load_global_cci_pair, GLOBAL_CCI_PATH,
)
from market_config import OECD_CCI_MARKETS
from glob import glob as _glob

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
RESULTS_DIR   = os.path.join(os.path.dirname(__file__), "..", "results", "country_cci")
GLOBAL_RESULTS_CSV = os.path.join(os.path.dirname(__file__), "..", "results", "tables",
                                  "global_cci_all_markets.csv")

TARGET_MARKETS = {"athex": "GRC", "bist100": "TUR"}


def load_cci_pair(market, oecd_code, start=START, end=FULL_END):
    """Load (y, z, dates) aligned on overlapping monthly dates for country CCI analysis."""
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()
    cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{oecd_code}.csv")
    cci = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna()
    cci.index = cci.index + pd.offsets.MonthEnd(0)
    df = pd.DataFrame({"price": prices, "cci": cci}).dropna()
    df = df.loc[start:end]
    y = np.log(df["price"].values).astype(float)
    z = df["cci"].values.astype(float)
    return y, z, df.index
MIN_OBS        = 180   # country CCI data is shorter than global CCI; both markets ~T>200


# ---------------------------------------------------------------------------
# Core estimation
# ---------------------------------------------------------------------------

def _estimate_one(market, oecd_code, verbose=True):
    """TAR estimation + episode verdict using country-specific CCI trigger."""
    cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{oecd_code}.csv")
    if not os.path.exists(cci_path):
        print(f" MISSING: run collect_oecd.py to download {oecd_code} CCI")
        return None

    y, z, dates = load_cci_pair(market, oecd_code, start=START, end=FULL_END)
    if len(y) < MIN_OBS:
        return None

    z_min, z_max, gl, mg = _grid_bounds(z)
    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
    c1, c2 = opt["c1"], opt["c2"]

    res     = standard_errors(y, z, c1, c2, 1, "returns")
    state   = _assign_states(z[1:], c1, c2)
    T       = len(state)
    verdict = _episode_verdict(state, dates[1:], verbose=verbose)
    cov     = _episode_coverage(state, dates[1:])

    latest_cci = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna().iloc[-1]
    if latest_cci < c1:    current = "MR"
    elif latest_cci > c2:  current = "EXP"
    else:                  current = "RW"

    return {
        "market":         market,
        "country":        MARKETS[market]["country"],
        "oecd_code":      oecd_code,
        "T":              T,
        "c1":             round(c1, 3),
        "c2":             round(c2, 3),
        "n_mr":           res["n1"],
        "n_rw":           res["n2"],
        "n_ex":           res["n3"],
        "beta_mr":        res["beta1"],
        "se_mr":          res["se_b1"],
        "beta_ex":        res["beta3"],
        "se_ex":          res["se_b3"],
        "sig_mr":         _sig_marker(res.get("tstat1")),
        "sig_ex":         _sig_marker(res.get("tstat3")),
        "dc_exp":         cov.get("dot_com"),
        "gfc_mr":         cov.get("gfc"),
        "covid_mr":       cov.get("covid"),
        "current_cci":    round(float(latest_cci), 3),
        "current_regime": current,
        "verdict":        verdict,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def estimate():
    print(f"\n{'='*75}")
    print("COUNTRY-SPECIFIC CCI STUDY  —  Greece (GRC) and Turkey (TUR)")
    print(f"Trigger: each country's own OECD CCI  |  Full sample to {FULL_END}")
    print(f"{'='*75}")

    # Stage 1 — Inspect
    print("\nSTAGE 1 -- Data overlap")
    print(f"  {'Market':<10} {'Country':<20} {'Code':<5} {'T':>5}  Start")
    print("  " + "-" * 50)
    for market, code in TARGET_MARKETS.items():
        cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{code}.csv")
        if not os.path.exists(cci_path):
            print(f"  {market:<10} MISSING: run collect_oecd.py to get {code} CCI")
            continue
        y, z, dates = load_cci_pair(market, code, start=START, end=FULL_END)
        cci = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna()
        print(f"  {market:<10} {MARKETS[market]['country']:<20} {code:<5} {len(y):>5}  "
              f"{dates[0].strftime('%Y-%m')}  "
              f"CCI=[{cci.min():.2f}, {cci.max():.2f}]  "
              f"latest={cci.iloc[-1]:.3f} ({cci.index[-1].strftime('%Y-%m')})")

    # Stage 2 — Exogeneity screen (informational, non-blocking)
    print(f"\nSTAGE 2 -- Exogeneity screen (reverse Granger: return -> d(country CCI))")
    print(f"  NOTE: country equity returns often predict own-country CCI — this is expected.")
    print(f"  {'Market':<10} {'Country':<20} {'Code':<5}  {'F':>7}  {'p':>7}  Gate")
    print("  " + "-" * 60)
    for market, code in TARGET_MARKETS.items():
        cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{code}.csv")
        if not os.path.exists(cci_path):
            continue
        y, z, _ = load_cci_pair(market, code, start=START, end=FULL_END)
        y_ret  = np.diff(y)
        z_diff = np.diff(z)
        n = min(len(y_ret), len(z_diff))
        F, p = granger_f_test(z_diff[-n:], y_ret[-n:], 4)
        gate = "PASS" if p > 0.05 else "FAIL"
        print(f"  {market:<10} {MARKETS[market]['country']:<20} {code:<5}  "
              f"{F:>7.3f}  {p:>7.4f}  {gate}")

    # Stage 3 — Estimation (all markets, exogeneity non-blocking)
    print(f"\nSTAGE 3 -- TAR estimation")
    print("-" * 75)
    rows = []
    for market, code in TARGET_MARKETS.items():
        print(f"  {market:<12} ({MARKETS[market]['country']:<18}) ...", end="", flush=True)
        r = _estimate_one(market, code, verbose=True)
        if r is None:
            print(f" SKIP (< {MIN_OBS} obs or missing CCI data)")
            continue
        rows.append(r)

    if not rows:
        print("\nNo markets estimated.")
        return

    # Summary table
    print(f"\n\n{'='*100}")
    print("SUMMARY TABLE")
    print(f"  {'Market':<12} {'Country':<20} {'T':>5}  {'c1':>8} {'c2':>8}  "
          f"{'MR%':>4} {'RW%':>4} {'EXP%':>4}  {'b_MR':>10} {'b_EX':>10}  "
          f"{'DC_EXP':>7} {'GFC_MR':>7} {'Now':>5}  Verdict")
    print("  " + "-" * 95)
    for r in rows:
        mr_pct  = round(r["n_mr"] / r["T"] * 100)
        rw_pct  = round(r["n_rw"] / r["T"] * 100)
        exp_pct = round(r["n_ex"] / r["T"] * 100)
        b_mr = (f"{r['beta_mr']:>+7.4f}{r['sig_mr']}"
                if pd.notna(r.get("beta_mr")) else "        --")
        b_ex = (f"{r['beta_ex']:>+7.4f}{r['sig_ex']}"
                if pd.notna(r.get("beta_ex")) else "        --")
        dc  = f"{r['dc_exp']:>5.0f}%"  if r.get("dc_exp")  is not None else "   n/a"
        gfc = f"{r['gfc_mr']:>5.0f}%"  if r.get("gfc_mr")  is not None else "   n/a"
        print(f"  {r['market']:<12} {r['country']:<20} {r['T']:>5}  "
              f"{r['c1']:>8.3f} {r['c2']:>8.3f}  "
              f"{mr_pct:>4}% {rw_pct:>4}% {exp_pct:>4}%  "
              f"{b_mr} {b_ex}  {dc} {gfc} {r['current_regime']:>5}  {r['verdict']}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "country_cci_results.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved: {out}")


# ---------------------------------------------------------------------------
# Regime-shaded equity plots (Global CCI trigger)
# ---------------------------------------------------------------------------

_REGIME_COLORS = {
    0: ("#d0d0d0", 0.20),           # RW  — light grey
    1: ("cornflowerblue", 0.30),    # MR  — blue
    2: ("tomato", 0.35),            # EXP — red
}


def _shade_regimes(ax, dates, state):
    if len(state) == 0:
        return
    chg  = np.flatnonzero(np.diff(state, prepend=state[0] - 1))
    ends = np.append(chg[1:], len(state))
    for si, ei in zip(chg, ends):
        color, alpha = _REGIME_COLORS[int(state[si])]
        ax.axvspan(dates[si], dates[ei - 1], color=color, alpha=alpha, lw=0)


def plot_global_cci(markets=None):
    """
    Regime-shaded log-price plots for TARGET_MARKETS using Global CCI thresholds.
    Saved to results/country_cci/ so all outputs for these two markets are co-located.
    """
    if markets is None:
        markets = list(TARGET_MARKETS.keys())

    if not os.path.exists(GLOBAL_RESULTS_CSV):
        print(f"  ERROR: {GLOBAL_RESULTS_CSV} not found. Run global_cci_study.py estimate first.")
        return

    saved_df = pd.read_csv(GLOBAL_RESULTS_CSV).set_index("market")
    missing = [m for m in markets if m not in saved_df.index]
    if missing:
        print(f"  WARNING: {missing} not in global CCI results — skipping")
        markets = [m for m in markets if m in saved_df.index]

    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"\n{'='*55}")
    print("REGIME PLOTS — Global OECD CCI  (saved to country_cci/)")
    print(f"{'='*55}")
    for market in markets:
        print(f"  {market:<12} ...", end="", flush=True)
        try:
            y, z, dates = load_global_cci_pair(market, START, FULL_END)
            c1 = float(saved_df.loc[market, "c1"])
            c2 = float(saved_df.loc[market, "c2"])
            state = _assign_states(z[1:], c1, c2)

            country = MARKETS[market]["country"]
            T       = len(state)
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
            gcci_dir = os.path.join(os.path.dirname(__file__), "..", "results", "gcci")
            os.makedirs(gcci_dir, exist_ok=True)
            out = os.path.join(gcci_dir, f"regimes_{market}_GCCI.png")
            plt.savefig(out, dpi=150)
            plt.close()
            print(f"  Saved: {out}")
        except Exception as e:
            print(f"  ERROR: {e}")


# ---------------------------------------------------------------------------
# Country-CCI regime plots (2-panel: log-price + CCI series)
# ---------------------------------------------------------------------------

def plot_country_cci(markets=None):
    """
    Two-panel regime plot using each country's own CCI as trigger.
    Top: log equity price shaded by country-CCI regime.
    Bottom: country CCI series with c1/c2 threshold lines.
    Saved to results/gcci/ as regimes_{market}_country_CCI.png.
    """
    if markets is None:
        markets = list(TARGET_MARKETS.keys())

    gcci_dir = os.path.join(os.path.dirname(__file__), "..", "results", "gcci")
    os.makedirs(gcci_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print("COUNTRY-CCI REGIME PLOTS  (saved to gcci/)")
    print(f"{'='*60}")

    for market in markets:
        code = TARGET_MARKETS.get(market)
        if code is None:
            print(f"  {market}: not in TARGET_MARKETS — skipping")
            continue

        cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{code}.csv")
        if not os.path.exists(cci_path):
            print(f"  {market}: missing {code} CCI — run collect_oecd.py first")
            continue

        print(f"  {market:<12} ({MARKETS[market]['country']}) ...", end="", flush=True)
        try:
            y, z, dates = load_cci_pair(market, code, start=START, end=FULL_END)
            if len(y) < MIN_OBS:
                print(f" SKIP (T={len(y)} < {MIN_OBS})")
                continue

            z_min, z_max, gl, mg = _grid_bounds(z)
            opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
            c1, c2 = opt["c1"], opt["c2"]
            state   = _assign_states(z[1:], c1, c2)
            T       = len(state)
            mr_pct  = 100 * (state == 1).sum() / T
            rw_pct  = 100 * (state == 0).sum() / T
            exp_pct = 100 * (state == 2).sum() / T

            # Load country CCI for bottom panel
            cci_raw = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna()
            cci_raw.index = cci_raw.index + pd.offsets.MonthEnd(0)
            cci_plot = cci_raw.loc[dates[0]:dates[-1]]

            country = MARKETS[market]["country"]
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7),
                                           sharex=False, gridspec_kw={"height_ratios": [2, 1]})

            # Top: log-price with regime shading
            _shade_regimes(ax1, dates[1:], state)
            ax1.plot(dates[1:], y[1:], color="black", linewidth=0.7, zorder=3)
            ax1.set_title(
                f"{market.upper()} ({country}) — TAR regimes under {code} OECD CCI  "
                f"[c₁={c1:.2f}, c₂={c2:.2f}]   "
                f"MR={mr_pct:.0f}%  RW={rw_pct:.0f}%  EXP={exp_pct:.0f}%",
                fontsize=8,
            )
            ax1.set_ylabel("Log equity price", fontsize=8)
            ax1.tick_params(labelsize=7)
            ax1.margins(x=0)
            legend_patches = [
                mpatches.Patch(color="cornflowerblue", alpha=0.60, label="MR — mean-reverting"),
                mpatches.Patch(color="#d0d0d0",        alpha=0.80, label="RW — efficient"),
                mpatches.Patch(color="tomato",         alpha=0.70, label="EXP — explosive"),
            ]
            ax1.legend(handles=legend_patches, fontsize=7, loc="upper left")

            # Bottom: country CCI with threshold lines
            ax2.plot(cci_plot.index, cci_plot.values, color="navy", linewidth=0.8,
                     label=f"{code} OECD CCI")
            ax2.axhline(c1,  color="cornflowerblue", linewidth=1.2, linestyle="--",
                        label=f"c₁ = {c1:.2f}")
            ax2.axhline(c2,  color="tomato",         linewidth=1.2, linestyle="--",
                        label=f"c₂ = {c2:.2f}")
            ax2.axhline(100, color="black",           linewidth=0.7, linestyle=":",
                        alpha=0.5, label="100 (long-run avg)")
            ax2.fill_between(cci_plot.index, cci_plot.values, 100,
                             where=(cci_plot.values > 100), color="tomato", alpha=0.12)
            ax2.fill_between(cci_plot.index, cci_plot.values, 100,
                             where=(cci_plot.values < 100), color="cornflowerblue", alpha=0.12)
            ax2.set_ylabel(f"{code} OECD CCI", fontsize=8)
            ax2.set_xlabel("Date", fontsize=8)
            ax2.tick_params(labelsize=7)
            ax2.margins(x=0)
            ax2.legend(fontsize=7, loc="upper left", ncol=2)

            plt.tight_layout()
            out = os.path.join(gcci_dir, f"regimes_{market}_country_CCI.png")
            plt.savefig(out, dpi=150)
            plt.close()
            print(f"  Saved: {out}")
            print(f"            c1={c1:.3f}  c2={c2:.3f}  "
                  f"(global CCI was c1={MARKETS[market].get('country','?')})")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# Table A2 — Correlations between global CCI and country-specific CCIs
# ---------------------------------------------------------------------------

def correlation_table():
    """
    Pearson correlation between month-over-month first differences of global OECD CCI
    and each country-specific CCI over their full overlapping date range.
    Using differences removes shared long-run trends; measures genuine co-movement.
    Sorted ascending (lowest first = most distinct from global signal).
    """
    global_cci = pd.read_csv(GLOBAL_CCI_PATH, index_col="date",
                             parse_dates=True)["global_cci"]
    global_cci.index = global_cci.index + pd.offsets.MonthEnd(0)

    # code → display name (first market per code in OECD_CCI_MARKETS)
    code_to_name = {}
    for mkt, code in OECD_CCI_MARKETS.items():
        if code not in code_to_name:
            code_to_name[code] = MARKETS.get(mkt, {}).get("country", mkt)

    rows = []
    pattern = os.path.join(SENTIMENT_DIR, "oecd_cci_???.csv")
    for path in sorted(_glob(pattern)):
        code = os.path.basename(path)[9:12]   # "oecd_cci_USA.csv" → "USA"
        if not code.isupper():                # skip "oecd_cci_all.csv"
            continue
        country = code_to_name.get(code, code)
        cci = pd.read_csv(path, index_col=0, parse_dates=True)["cci"].dropna()
        cci.index = cci.index + pd.offsets.MonthEnd(0)
        merged = pd.concat([global_cci, cci], axis=1, join="inner").dropna()
        merged.columns = ["global", "country"]
        diff = merged.diff().dropna()
        r = diff["global"].corr(diff["country"])
        rows.append({
            "code":    code,
            "country": country,
            "n":       len(diff),
            "start":   merged.index[0].strftime("%Y-%m"),
            "end":     merged.index[-1].strftime("%Y-%m"),
            "corr":    round(r, 4),
        })

    df = pd.DataFrame(rows).sort_values("corr").reset_index(drop=True)

    print(f"\n{'='*65}")
    print("TABLE A2 -- Corr(d(Global CCI), d(Country CCI))  [sorted low->high]")
    print(f"{'='*65}")
    print(f"  {'Code':<5} {'Country':<22} {'n':>5}  {'Period':<18}  Corr[dCCI]")
    print("  " + "-" * 58)
    for _, r in df.iterrows():
        period = f"{r['start']} to {r['end']}"
        print(f"  {r['code']:<5} {r['country']:<22} {r['n']:>5}  {period:<18}  {r['corr']:>6.4f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "table_a2_cci_correlations.csv")
    df.to_csv(out, index=False)
    print(f"\nSaved: {out}")
    return df


if __name__ == "__main__":
    import sys as _sys
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else "all"
    if cmd == "estimate":
        estimate()
    elif cmd == "plots":
        plot_global_cci()
    elif cmd == "plot_country":
        plot_country_cci()
    elif cmd == "corr_table":
        correlation_table()
    else:
        estimate()
        plot_country_cci()
        correlation_table()
