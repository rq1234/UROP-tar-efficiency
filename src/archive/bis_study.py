"""
BIS Credit-to-GDP Gap as a TAR bubble trigger.

The credit gap = (credit/GDP) minus HP-trend. Positive = credit boom = EXP.
Negative = deleveraging = MR. No sign negation needed.

IMPORTANT TIMING: The credit gap lags the equity cycle by 1-2 years because
it measures cumulative credit buildups. During the acute GFC (2008-09) the US
gap was still +9 to +11pp (bubble hadn't deflated yet). The MR signal appears
during the post-GFC deleveraging (2010-2014) when the gap went to -17pp.
Episode windows are adjusted accordingly:
  EXP check: dot-com (1998-2001) and housing bubble (2004-2007)
  MR check:  post-GFC deleveraging (2010-2014) and 2022-2023 rate hike shock

Data: data/sentiment/bis_monthly_{market}.csv
  Quarterly BIS gaps linearly interpolated to monthly (collect_bis.py).

Admissible markets (17 of 21 pass Step 1 quarterly Granger gate):
  sp500, ftse100, dax, nikkei225, shanghai, hangseng, nifty50, tsx,
  asx200, bovespa, ibex35, sti, jse, aex, ipc, ta125, klci

Excluded (equity returns Granger-cause their credit gap):
  cac40, kospi, smi, jkse

Six stages:
  1 - inspect  : plot US credit gap with episode shading
  2 - screen   : monthly exogeneity re-confirmation (n_lags=3)
  3 - validate : S&P 500 known-answer test
  4 - rolling  : 10-yr rolling threshold stability
  5 - estimate : cross-market TAR estimation with sanity check
  6 - bubble   : Option A + B bubble call, last-24m regime table

Usage:
    cd src && python bis_study.py              # full pipeline
    python bis_study.py inspect
    python bis_study.py screen
    python bis_study.py validate
    python bis_study.py rolling
    python bis_study.py estimate
    python bis_study.py bubble
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from estimate    import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity  import granger_f_test
from market_config import MARKETS
from replicate   import PANEL_PATH
from bubble_now  import (
    plot_pair, regime_table,
    FIGURES_DIR, TABLES_DIR, INSAMPLE_END, FULL_END,
)
from rolling_thresholds import rolling_windows, WINDOW_MONTHS, STEP_MONTHS

SENTIMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentiment")
START = "1990-01"

ADMISSIBLE = [
    "sp500", "ftse100", "dax", "nikkei225", "shanghai", "hangseng",
    "nifty50", "tsx", "asx200", "bovespa", "ibex35", "sti",
    "jse", "aex", "ipc", "ta125", "klci",
]

# Episode windows adjusted for credit gap's lagged nature:
#   - EXP periods: when gap is elevated (credit boom) - BEFORE the equity crash
#   - MR periods: when gap is deeply negative (deleveraging) - AFTER the crash
EPISODES = [
    ("Dot-com boom",  "1998-01", "2001-12", "gold"),
    ("Housing bubble","2004-01", "2007-12", "orange"),
    ("Deleveraging",  "2010-01", "2014-12", "red"),
    ("2022 shock",    "2022-01", "2023-12", "purple"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_bis_monthly(market):
    """Return monthly credit gap series for one market (pp, positive = boom)."""
    path = os.path.join(SENTIMENT_DIR, f"bis_monthly_{market}.csv")
    s = pd.read_csv(path, index_col="date", parse_dates=True)["gap"].dropna()
    s.index = s.index + pd.offsets.MonthEnd(0)
    return s


def load_bis_pair(market, start, end):
    """Return (y, z, dates) for (market, BIS credit gap) pair."""
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()
    gap    = load_bis_monthly(market)

    df = pd.DataFrame({"price": prices, "gap": gap}).dropna().loc[start:end]
    y     = np.log(df["price"].values).astype(float)
    z     = df["gap"].values.astype(float)
    dates = np.array(df.index, dtype="datetime64[ns]")
    return y, z, dates


def _grid_bounds(z):
    """Adaptive Â±3Ïƒ grid bounds for credit gap (scale varies widely by country)."""
    mu, sigma = float(z.mean()), float(z.std())
    z_min = round(mu - 3.0 * sigma, 2)
    z_max = round(mu + 3.0 * sigma, 2)
    gridlen   = 150
    grid_step = (z_max - z_min) / (gridlen - 1)
    min_gap   = max(4, int(0.15 / grid_step))
    return z_min, z_max, gridlen, min_gap


# ---------------------------------------------------------------------------
# Stage 1 - Inspection
# ---------------------------------------------------------------------------

def inspect_bis():
    """Plot US credit gap 1990-2025 with episode shading."""
    gap = load_bis_monthly("sp500").loc[START:]

    print(f"\nUS credit gap (1990-present): "
          f"mean={gap.mean():.2f}pp  std={gap.std():.2f}pp  "
          f"min={gap.min():.1f}pp  max={gap.max():.1f}pp")
    print(f"  Housing bubble peak (2004-07): {gap.loc['2004':'2007'].max():+.1f}pp")
    print(f"  GFC trough in gap (2010-14):   {gap.loc['2010':'2014'].min():+.1f}pp")
    print(f"  Current (latest):              {gap.iloc[-1]:+.1f}pp "
          f"as of {gap.index[-1].strftime('%Y-%m')}")
    print(f"  Note: gap was still +{gap.loc['2008':'2009'].mean():.1f}pp during acute GFC "
          f"(2008-09) â€” MR signal lags equity crash by ~1-2 years")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 4))
    dates_np = np.array(gap.index, dtype="datetime64[ns]")
    ax.plot(dates_np, gap.values, color="black", linewidth=0.8)
    ax.axhline(0, color="gray", linewidth=0.7, linestyle="--", alpha=0.6)
    ax.fill_between(dates_np, gap.values, 0,
                    where=(gap.values > 0), color="tomato",         alpha=0.20)
    ax.fill_between(dates_np, gap.values, 0,
                    where=(gap.values < 0), color="cornflowerblue", alpha=0.20)

    for label, start, end, color in EPISODES:
        ep = gap.loc[start:end]
        if len(ep):
            ep_np = np.array(ep.index, dtype="datetime64[ns]")
            ax.axvspan(ep_np[0], ep_np[-1], alpha=0.15, color=color, label=label)

    patches = [mpatches.Patch(color=c, alpha=0.4, label=l)
               for l, _, _, c in EPISODES]
    ax.legend(handles=patches, fontsize=7, loc="lower left")
    ax.set_title("US Credit-to-GDP Gap (BIS)  --  positive = credit boom, "
                 "negative = deleveraging", fontsize=9)
    ax.set_ylabel("Credit gap (pp)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "bis_overview.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Stage 2 - Exogeneity screen (monthly)
# ---------------------------------------------------------------------------

def exogeneity_screen_bis(n_lags=3, alpha=0.05):
    """
    Re-confirm quarterly Granger gate on the monthly interpolated series.
    Reverse test: does equity return predict delta(gap)?
    """
    print(f"\n{'='*70}")
    print("STAGE 2 -- Monthly exogeneity re-confirmation (n_lags=3)")
    print(f"{'='*70}")
    print(f"{'Market':<14} {'Country':<18} {'F':>7}  {'p':>7}  Gate")
    print("-" * 55)

    admissible = []
    for market in ADMISSIBLE:
        info = MARKETS[market]
        try:
            y, z, _ = load_bis_pair(market, START, FULL_END)
            y_ret  = np.diff(y)
            z_diff = np.diff(z)
            n = min(len(y_ret), len(z_diff))
            rev_F, rev_p = granger_f_test(z_diff[-n:], y_ret[-n:], n_lags)
            verdict = "PASS" if rev_p > alpha else "FAIL"
            if verdict == "PASS":
                admissible.append(market)
            print(f"{market:<14} {info['country']:<18} "
                  f"{rev_F:>7.3f}  {rev_p:>7.4f}  {verdict}")
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    print(f"\n{len(admissible)}/{len(ADMISSIBLE)} markets pass monthly gate.")
    return admissible


# ---------------------------------------------------------------------------
# Stage 3 - US validation
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """
    Episode overlap for BIS credit gap.
    EXP expected during credit booms (dot-com 1998-2001, housing 2004-2007).
    MR expected during prolonged deleveraging (2010-2014) and 2022 shock.
    NOTE: gap was still positive during acute GFC 2008-09 â€” NOT a valid MR check.
    """
    regime_df = pd.DataFrame({
        "regime": [["RW", "MR", "EXP"][s] for s in state],
    }, index=pd.DatetimeIndex(dates))

    def n_regime(r, s, e):
        return (regime_df.loc[s:e]["regime"] == r).sum()

    dotcom_exp   = n_regime("EXP", "1998-01", "2001-12")
    housing_exp  = n_regime("EXP", "2004-01", "2007-12")
    delever_mr   = n_regime("MR",  "2010-01", "2014-12")
    shock22_mr   = n_regime("MR",  "2022-01", "2023-12")
    recent_exp   = n_regime("EXP", "2021-01", "2026-06")

    if verbose:
        print(f"    dot-com EXP: {dotcom_exp}  |  housing EXP: {housing_exp}  |  "
              f"delever MR: {delever_mr}  |  2022 MR: {shock22_mr}  |  "
              f"2021-present EXP: {recent_exp}", end="  ")

    has_exp = (dotcom_exp >= min_months) or (housing_exp >= min_months)
    has_mr  = delever_mr >= min_months

    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


def validate_us_bis():
    """S&P 500 + US credit gap: full-sample estimation and episode overlap."""
    print(f"\n{'='*70}")
    print("STAGE 3 -- Validation: S&P 500 + US credit gap (1990-2025)")
    print(f"{'='*70}")

    y, z, dates = load_bis_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)
    print(f"  T={len(y)}  gap=[{z.min():.1f}, {z.max():.1f}]pp  "
          f"grid=[{z_min:.1f}, {z_max:.1f}]  n={gl}  min_gap={mg}")

    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
    c1, c2 = opt["c1"], opt["c2"]
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)

    print(f"  c1={c1:.2f}pp (below = deleveraging/MR)  "
          f"c2={c2:.2f}pp (above = credit boom/EXP)")
    print(f"  MR={100*(state==1).sum()/T:.1f}%  "
          f"RW={100*(state==0).sum()/T:.1f}%  "
          f"EXP={100*(state==2).sum()/T:.1f}%")

    verdict = _episode_verdict(state, dates[1:])
    print(f"\n  Verdict: {verdict}")
    if verdict in ("BOTH TAILS", "EUPHORIA GAUGE"):
        print("  Validation PASSED.")
    else:
        print("  WARNING: check episode overlap.")

    return c1, c2, verdict


# ---------------------------------------------------------------------------
# Stage 4 - Rolling stability
# ---------------------------------------------------------------------------

def rolling_bis_stability():
    """10-year rolling-window thresholds for S&P 500 + US credit gap."""
    print(f"\n{'='*70}")
    print("STAGE 4 -- Rolling-window stability (S&P 500 + US credit gap)")
    print(f"{'='*70}")

    y, z, dates = load_bis_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)

    y_in, z_in, _ = load_bis_pair("sp500", START, INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
    print(f"  In-sample ref: c1={ref['c1']:.2f}pp  c2={ref['c2']:.2f}pp")
    print(f"  Rolling {WINDOW_MONTHS//12}-yr windows ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    print(f" {len(rows)} windows")

    os.makedirs(TABLES_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=["window_end", "c1", "c2"])
    df["window_end"] = pd.DatetimeIndex(df["window_end"]).strftime("%Y-%m")
    df = df.round({"c1": 2, "c2": 2})
    csv_path = os.path.join(TABLES_DIR, "rolling_thresholds_SP500_BIS.csv")
    df.to_csv(csv_path, index=False)
    print(f"  c1: min={df['c1'].min():.2f}  max={df['c1'].max():.2f}  "
          f"range={df['c1'].max()-df['c1'].min():.2f}  ref={ref['c1']:.2f}")
    print(f"  c2: min={df['c2'].min():.2f}  max={df['c2'].max():.2f}  "
          f"range={df['c2'].max()-df['c2'].min():.2f}  ref={ref['c2']:.2f}")
    print(f"  (Compare: MCSI c1 range was 46 units; BIS should be narrower)")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    dates_arr = np.array([r[0] for r in rows], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows])
    c2_arr    = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates_arr, c1_arr, color="cornflowerblue", linewidth=1.8, label="c1 (rolling)")
    ax.plot(dates_arr, c2_arr, color="tomato",         linewidth=1.8, label="c2 (rolling)")
    ax.axhline(ref["c1"], color="cornflowerblue", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c1 in-sample ref ({ref['c1']:.2f}pp)")
    ax.axhline(ref["c2"], color="tomato",         linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c2 in-sample ref ({ref['c2']:.2f}pp)")
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7, label="2015-06 cutoff")
    ax.set_title("SP500 + BIS credit gap -- rolling 10-yr TAR thresholds", fontsize=9)
    ax.set_xlabel("Window end", fontsize=8)
    ax.set_ylabel("Threshold (pp)", fontsize=8)
    ax.legend(fontsize=7, ncol=2)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "rolling_thresholds_SP500_BIS.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")
    print(f"  Saved: {csv_path}")


# ---------------------------------------------------------------------------
# Stage 5 - Cross-market estimation
# ---------------------------------------------------------------------------

def _estimate_one(market, start=START, end=FULL_END, spec=1, verbose=True):
    """TAR estimation + episode verdict for one market with BIS credit gap."""
    y, z, dates = load_bis_pair(market, start, end)
    if len(y) < 120:
        return None

    z_min, z_max, gl, mg = _grid_bounds(z)
    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, "returns")
    c1, c2 = opt["c1"], opt["c2"]

    res    = standard_errors(y, z, c1, c2, spec, "returns")
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)
    verdict = _episode_verdict(state, dates[1:], verbose=verbose)

    # Sanity check: flag degenerate proportions
    exp_pct = res["n3"] / T
    mr_pct  = res["n1"] / T
    if exp_pct > 0.50 or mr_pct > 0.50:
        verdict = verdict + " DEGENERATE"

    return {
        "market":    market,
        "country":   MARKETS[market]["country"],
        "T":         T,
        "c1":        c1,      "c2":       c2,
        "beta_mr":   res["beta1"], "beta_ex":  res["beta3"],
        "se_mr":     res["se1"],   "se_ex":    res["se3"],
        "tstat_mr":  res["tstat1"],"tstat_ex": res["tstat3"],
        "n_mr":      res["n1"],    "n_rw":     res["n2"], "n_ex": res["n3"],
        "verdict":   verdict,
    }


def run_all_markets(admissible=None):
    """Stage 5: TAR estimation for all admissible markets with BIS credit gap."""
    print(f"\n{'='*70}")
    print("STAGE 5 -- Cross-market estimation (BIS credit gap, spec=1)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else ADMISSIBLE
    rows = []

    for market in markets:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) ...", end="", flush=True)
        try:
            r = _estimate_one(market, verbose=True)
            if r is None:
                print(" SKIP (< 120 obs)")
                continue
            rows.append(r)
            T = r["T"]
            print(f"  c1={r['c1']:.1f}pp  c2={r['c2']:.1f}pp  "
                  f"MR={100*r['n_mr']/T:.0f}%  RW={100*r['n_rw']/T:.0f}%  "
                  f"EXP={100*r['n_ex']/T:.0f}%  {r['verdict']}")
        except Exception as e:
            print(f" ERROR: {e}")

    if not rows:
        return

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  "
          f"{'c1':>6} {'c2':>6}  {'MR%':>5} {'RW%':>5} {'EXP%':>5}  Verdict")
    print("-" * 85)
    for r in rows:
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>5.1f} {r['c2']:>5.1f}  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% "
              f"{100*r['n_ex']/T:>4.0f}%  {r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(TABLES_DIR, "bis_all_markets.csv"), index=False
    )
    print(f"\nSaved: {os.path.join(TABLES_DIR, 'bis_all_markets.csv')}")
    return rows


# ---------------------------------------------------------------------------
# Stage 6 - Bubble call
# ---------------------------------------------------------------------------

def bubble_call(admissible=None):
    """Stage 6: Option A + B bubble call for all admissible markets."""
    print(f"\n{'='*70}")
    print("STAGE 6 -- Bubble call (Option A + B, BIS credit gap)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else ADMISSIBLE
    specs, results_a, results_b = [], [], []

    for market in markets:
        label = f"{market.upper()}_BIS"
        try:
            y, z, dates = load_bis_pair(market, START, FULL_END)
            if len(y) < 120:
                continue
            z_min, z_max, gl, mg = _grid_bounds(z)

            opt_a = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
            st_a  = _assign_states(z[1:], opt_a["c1"], opt_a["c2"])
            ra = {"c1": opt_a["c1"], "c2": opt_a["c2"], "state": st_a,
                  "dates": dates[1:], "y": y, "label": label}

            y_in, z_in, _ = load_bis_pair(market, START, INSAMPLE_END)
            opt_b = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
            st_b  = _assign_states(z[1:], opt_b["c1"], opt_b["c2"])
            rb = {"c1": opt_b["c1"], "c2": opt_b["c2"], "state": st_b,
                  "dates": dates[1:], "y": y, "label": label}

            oos = dates[1:] > np.datetime64("2015-06-30", "ns")
            print(f"  {label}: A(c1={opt_a['c1']:.1f},c2={opt_a['c2']:.1f})  "
                  f"B(c1={opt_b['c1']:.1f},c2={opt_b['c2']:.1f})  "
                  f"OOS n={oos.sum()}")

            specs.append(("bis", market, label))
            results_a.append(ra)
            results_b.append(rb)

        except Exception as e:
            print(f"  {market}: ERROR: {e}")

    if not results_a:
        print("  No results.")
        return

    print("\n--- Plots ---")
    for spec, ra, rb in zip(specs, results_a, results_b):
        plot_pair(spec, ra, rb)

    regime_table(results_a, results_b, n_months=54,
                 csv_name="bis_2022_2026.csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all():
    inspect_bis()
    admissible = exogeneity_screen_bis()
    validate_us_bis()
    rolling_bis_stability()
    run_all_markets(admissible)
    bubble_call(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "inspect":  inspect_bis,
        "screen":   exogeneity_screen_bis,
        "validate": validate_us_bis,
        "rolling":  rolling_bis_stability,
        "estimate": lambda: run_all_markets(ADMISSIBLE),
        "bubble":   lambda: bubble_call(ADMISSIBLE),
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()

