"""
Mixed-trigger TAR study.

For each market, uses the best available trigger:
  - Country-specific OECD CCI if data/sentiment/oecd_cci_{CODE}.csv exists
  - Global OECD CCI (CSCICP03OECDm) as fallback

Pipeline: exogeneity screen -> T>=340 filter -> TAR estimation -> efficiency table.
Outputs a comparison of % MR/RW/EXP vs the global-CCI-only results.

Usage:
    cd src && python mixed_trigger_study.py            # full pipeline
    cd src && python mixed_trigger_study.py screen     # screen only
    cd src && python mixed_trigger_study.py estimate   # screen + estimate
    cd src && python mixed_trigger_study.py compare    # comparison table only
    cd src && python mixed_trigger_study.py chart      # chart only
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
from estimate         import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity       import granger_f_test
from market_config    import MARKETS, OECD_CCI_MARKETS
from replicate        import PANEL_PATH
from bubble_now       import FULL_END
from global_cci_study import load_global_cci_pair, _grid_bounds, START

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
TABLES_DIR    = os.path.join(os.path.dirname(__file__), "..", "results", "tables")
GCCI_DIR      = os.path.join(os.path.dirname(__file__), "..", "results", "gcci")
RESULTS_CSV   = os.path.join(TABLES_DIR, "mixed_trigger_results.csv")
GLOBAL_CSV    = os.path.join(TABLES_DIR, "global_cci_all_markets.csv")

MIN_OBS_GLOBAL  = 340   # dot-com era coverage requirement for global CCI markets
# No minimum T for country CCI markets — use all available data
N_LAGS  = 4
ALPHA   = 0.05


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_mixed_pair(market, start=START, end=FULL_END):
    """
    Return (y, z, dates, trigger_type) for one market.
    trigger_type = "country" if a country-specific OECD CCI file exists,
                   "global"  otherwise.
    """
    if market in OECD_CCI_MARKETS:
        code = OECD_CCI_MARKETS[market]
        path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{code}.csv")
        if os.path.exists(path):
            panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
            prices = panel[f"eq_{market}"].dropna()
            cci    = pd.read_csv(path, index_col=0, parse_dates=True)["cci"].dropna()
            cci.index = cci.index + pd.offsets.MonthEnd(0)
            df = pd.DataFrame({"price": prices, "cci": cci}).dropna().loc[start:end]
            if len(df) == 0:
                raise ValueError(f"No overlapping data for {market} + country CCI")
            y     = np.log(df["price"].values).astype(float)
            z     = df["cci"].values.astype(float)
            dates = np.array(df.index, dtype="datetime64[ns]")
            return y, z, dates, "country"
    y, z, dates = load_global_cci_pair(market, start, end)
    return y, z, dates, "global"


# ---------------------------------------------------------------------------
# Stage 1 — Exogeneity screen + T filter
# ---------------------------------------------------------------------------

def screen(n_lags=N_LAGS, alpha=ALPHA):
    """
    Screen all markets: reverse Granger (do returns predict d(trigger)?) and T >= MIN_OBS.
    Returns list of (market, trigger_type) tuples that pass both gates.
    """
    print(f"\n{'='*80}")
    print("MIXED-TRIGGER STUDY  Stage 1: Exogeneity screen")
    print(f"Reverse Granger: equity return -> d(trigger)  n_lags={n_lags}  alpha={alpha}")
    print(f"{'='*80}")
    print(f"{'Market':<14} {'Country':<18} {'Trigger':<8} {'T':>5}  "
          f"{'F':>7}  {'p':>7}  Gate")
    print("-" * 70)

    admissible  = []
    n_short     = 0
    pass_counts = {"country": 0, "global": 0}
    fail_counts = {"country": 0, "global": 0}

    for market, info in MARKETS.items():
        try:
            y, z, _, ttype = load_mixed_pair(market)
        except Exception as e:
            print(f"{market:<14} {'':18} {'':8} {'':5}  ERROR: {e}")
            continue

        T_full = len(y)
        if ttype == "global" and T_full < MIN_OBS_GLOBAL:
            print(f"{market:<14} {info['country']:<18} {ttype:<8} {T_full:>5}  "
                  f"{'':>7}  {'':>7}  SHORT (<{MIN_OBS_GLOBAL})")
            n_short += 1
            continue

        y_ret  = np.diff(y)
        z_diff = np.diff(z)
        n      = min(len(y_ret), len(z_diff))
        rev_F, rev_p = granger_f_test(z_diff[-n:], y_ret[-n:], n_lags)

        verdict = "PASS" if rev_p > alpha else "FAIL"
        print(f"{market:<14} {info['country']:<18} {ttype:<8} {T_full:>5}  "
              f"{rev_F:>7.3f}  {rev_p:>7.4f}  {verdict}")

        if verdict == "PASS":
            admissible.append((market, ttype))
            pass_counts[ttype] += 1
        else:
            fail_counts[ttype] += 1

    n_fail = fail_counts["country"] + fail_counts["global"]
    print(f"\n{len(admissible)} admissible from {len(MARKETS)} markets  "
          f"({n_short} too short, {n_fail} fail exogeneity)")
    print(f"  With country CCI: {pass_counts['country']}  "
          f"(failed: {fail_counts['country']})")
    print(f"  With global  CCI: {pass_counts['global']}  "
          f"(failed: {fail_counts['global']})")
    return admissible


# ---------------------------------------------------------------------------
# Stage 2 — TAR estimation
# ---------------------------------------------------------------------------

def _sig_marker(tstat):
    if tstat is None or (isinstance(tstat, float) and np.isnan(tstat)):
        return ""
    a = abs(tstat)
    if a > 2.576: return "***"
    if a > 1.960: return "**"
    if a > 1.645: return "*"
    return ""


def estimate(admissible, spec=1):
    """
    TAR estimation for all admissible (market, trigger_type) pairs.
    Saves results/tables/mixed_trigger_results.csv and returns list of result dicts.
    """
    print(f"\n{'='*80}")
    print("MIXED-TRIGGER STUDY  Stage 2: TAR estimation  (spec=1, switching drift)")
    print(f"{'='*80}")

    rows = []
    for market, ttype in admissible:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) [{ttype:<7}] ...", end="", flush=True)
        try:
            y, z, _, _ = load_mixed_pair(market)
            if ttype == "global" and len(y) < MIN_OBS_GLOBAL:
                print(" SKIP (global CCI < 340 obs)")
                continue

            z_min, z_max, gl, mg = _grid_bounds(z)
            opt    = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, "returns")
            c1, c2 = opt["c1"], opt["c2"]
            res    = standard_errors(y, z, c1, c2, spec, "returns")
            state  = _assign_states(z[1:], c1, c2)
            T      = len(state)

            n_mr = int((state == 1).sum())
            n_rw = int((state == 0).sum())
            n_ex = int((state == 2).sum())

            print(f"  c1={c1:.3f}  c2={c2:.3f}  "
                  f"MR={100*n_mr/T:.0f}%  RW={100*n_rw/T:.0f}%  EXP={100*n_ex/T:.0f}%")

            rows.append({
                "market":       market,
                "country":      country,
                "trigger_type": ttype,
                "T":            T,
                "c1":           round(c1, 5),
                "c2":           round(c2, 5),
                "n_mr":         n_mr,
                "n_rw":         n_rw,
                "n_ex":         n_ex,
                "pct_MR":       round(100 * n_mr / T, 2),
                "pct_RW":       round(100 * n_rw / T, 2),
                "pct_EXP":      round(100 * n_ex / T, 2),
                "beta_mr":      round(res["beta1"], 6),
                "se_mr":        round(res["se_b1"], 6),
                "sig_mr":       _sig_marker(res.get("tstat1")),
                "beta_ex":      round(res["beta3"], 6),
                "se_ex":        round(res["se_b3"], 6),
                "sig_ex":       _sig_marker(res.get("tstat3")),
            })
        except Exception as e:
            print(f"  ERROR: {e}")

    if rows:
        os.makedirs(TABLES_DIR, exist_ok=True)
        pd.DataFrame(rows).to_csv(RESULTS_CSV, index=False)
        print(f"\nSaved: {RESULTS_CSV}")

    return rows


# ---------------------------------------------------------------------------
# Stage 3 — Comparison vs global CCI
# ---------------------------------------------------------------------------

def compare(rows=None):
    """
    Side-by-side efficiency comparison: mixed trigger vs pure global CCI.
    For markets in both admissible sets, prints delta_RW (pp).
    """
    if rows is None:
        if not os.path.exists(RESULTS_CSV):
            print("No results CSV found; run estimate first.")
            return
        df_mixed = pd.read_csv(RESULTS_CSV).set_index("market")
    else:
        df_mixed = pd.DataFrame(rows).set_index("market")

    if not os.path.exists(GLOBAL_CSV):
        print("No global CCI results found; run global_cci_study.py estimate first.")
        return
    df_global = pd.read_csv(GLOBAL_CSV).set_index("market")

    common      = df_mixed.index.intersection(df_global.index)
    only_mixed  = df_mixed.index.difference(df_global.index)
    only_global = df_global.index.difference(df_mixed.index)

    print(f"\n{'='*95}")
    print("COMPARISON: mixed trigger vs global CCI")
    print(f"{'='*95}")
    print(f"{'Market':<14} {'Country':<16} {'Trigger':<8}  "
          f"{'MR%':>4} {'RW%':>4} {'EXP%':>4}  |  "
          f"{'MR%_g':>5} {'RW%_g':>5} {'EXP%_g':>6}  |  {'dRW':>6}")
    print("-" * 80)

    d_rws_country = []
    for mkt in common:
        m   = df_mixed.loc[mkt]
        g   = df_global.loc[mkt]
        T_g = g["T"]
        mr_g  = round(100 * g["n_mr"] / T_g, 1)
        rw_g  = round(100 * g["n_rw"] / T_g, 1)
        ex_g  = round(100 * g["n_ex"] / T_g, 1)
        d_rw  = m["pct_RW"] - rw_g
        print(f"{mkt:<14} {m['country']:<16} {m['trigger_type']:<8}  "
              f"{m['pct_MR']:>3.0f}% {m['pct_RW']:>3.0f}% {m['pct_EXP']:>4.0f}%  |  "
              f"{mr_g:>4.0f}% {rw_g:>4.0f}% {ex_g:>5.0f}%  |  {d_rw:>+5.1f}pp")
        if m["trigger_type"] == "country":
            d_rws_country.append(d_rw)

    if len(only_mixed):
        print(f"\nNew admissible in mixed-trigger (not in global-CCI set):")
        for mkt in only_mixed:
            m = df_mixed.loc[mkt]
            print(f"  {mkt:<14} {m['country']:<16} [{m['trigger_type']}]  "
                  f"MR={m['pct_MR']:.0f}%  RW={m['pct_RW']:.0f}%  EXP={m['pct_EXP']:.0f}%")

    if len(only_global):
        print(f"\nDropped from mixed-trigger (were in global-CCI set):")
        for mkt in only_global:
            g   = df_global.loc[mkt]
            T_g = g["T"]
            print(f"  {mkt:<14} {g['country']:<16}  "
                  f"MR={100*g['n_mr']/T_g:.0f}%  RW={100*g['n_rw']/T_g:.0f}%  "
                  f"EXP={100*g['n_ex']/T_g:.0f}%")

    print(f"\nSummary:")
    print(f"  Mixed-trigger admissible: {len(df_mixed)}")
    print(f"  Global-CCI admissible:   {len(df_global)}")
    print(f"  In common:               {len(common)}")
    if d_rws_country:
        print(f"\n  For {len(d_rws_country)} markets switched to country CCI:")
        print(f"    Mean delta_RW = {np.mean(d_rws_country):+.1f} pp  "
              f"(positive = more RW/efficient with country CCI)")


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

def chart_mixed_trigger_efficiency(rows=None):
    """
    Horizontal bar chart of RW% for all admissible markets.
    Blue bars = country CCI trigger; grey bars = global CCI trigger.
    Sorted by RW% descending. Saves to results/gcci/chart_mixed_trigger_efficiency.png.
    """
    if rows is None:
        if not os.path.exists(RESULTS_CSV):
            print("No results CSV found; run estimate first.")
            return
        df = pd.read_csv(RESULTS_CSV)
    else:
        df = pd.DataFrame(rows)

    df = df.sort_values("pct_RW", ascending=True).reset_index(drop=True)

    labels  = df["country"].tolist()
    rw_vals = df["pct_RW"].values
    colours = ["#4472C4" if t == "country" else "#A0A0A0"
               for t in df["trigger_type"]]

    fig, ax = plt.subplots(figsize=(9, max(5, 0.35 * len(df))))
    y_pos   = np.arange(len(df))

    bars = ax.barh(y_pos, rw_vals, color=colours, height=0.7, edgecolor="none")
    for bar, val in zip(bars, rw_vals):
        ax.text(val + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}%", va="center", ha="left", fontsize=8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("RW regime — % of months classified as random walk", fontsize=10)
    n_country = (df["trigger_type"] == "country").sum()
    n_global  = (df["trigger_type"] == "global").sum()
    ax.set_title(
        f"Market efficiency — mixed-trigger study  ({len(df)} admissible markets)\n"
        f"Blue = country OECD CCI (n={n_country})  |  "
        f"Grey = global OECD CCI fallback (n={n_global})",
        fontsize=10, pad=10,
    )
    ax.set_xlim(0, 110)
    ax.axvline(80, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)

    patch_country = mpatches.Patch(color="#4472C4", label="Country OECD CCI")
    patch_global  = mpatches.Patch(color="#A0A0A0", label="Global OECD CCI (fallback)")
    ax.legend(handles=[patch_country, patch_global], fontsize=9, loc="lower right")

    plt.tight_layout()
    os.makedirs(GCCI_DIR, exist_ok=True)
    out = os.path.join(GCCI_DIR, "chart_mixed_trigger_efficiency.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all():
    admissible = screen()
    rows = estimate(admissible)
    compare(rows)
    chart_mixed_trigger_efficiency(rows)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "screen":
        screen()
    elif cmd == "estimate":
        rows = estimate(screen())
    elif cmd == "compare":
        compare()
    elif cmd == "chart":
        chart_mixed_trigger_efficiency()
    else:
        run_all()
