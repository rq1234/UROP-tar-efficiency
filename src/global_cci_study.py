"""
OECD Global Composite CCI as a universal trigger for the TAR bubble model.

FRED series CSCICP03OECDm: composite Consumer Confidence across all OECD members,
normalised to 100 = long-run average.  Above 100 = optimistic; below 100 = pessimistic.

SIGN CONVENTION: No negation.  High CCI -> EXP (euphoria/bubble risk).
                              Low  CCI -> MR  (pessimism/crisis).

Unlike country-specific CCI (cci_study.py), this is a single global series
applied to all 23 markets, the same way ANFCI works.

Six stages:
  1 - inspect   : plot global CCI with episode shading, summary stats
  2 - screen    : Granger exogeneity gate for all 23 markets
  3 - validate  : S&P 500 known-answer test
  4 - rolling   : rolling-window threshold stability (S&P 500)
  5 - estimate  : TAR for all admissible markets
  6 - bubble    : Option A + B bubble call, last-24m regime table

Usage:
    cd src && python global_cci_study.py              # full pipeline
    python global_cci_study.py inspect
    python global_cci_study.py screen
    python global_cci_study.py validate
    python global_cci_study.py rolling
    python global_cci_study.py estimate
    python global_cci_study.py bubble
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
from estimate    import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity  import granger_f_test
from market_config import MARKETS
from replicate   import PANEL_PATH
from bubble_now  import (
    plot_pair, regime_table,
    FIGURES_DIR, TABLES_DIR, INSAMPLE_END, FULL_END,
)
from rolling_thresholds import rolling_windows, WINDOW_MONTHS, STEP_MONTHS

GLOBAL_CCI_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment",
                                "global_cci_monthly.csv")
START = "1990-01"

EPISODES = [
    ("Dot-com",   "1997-01", "2001-12", "gold"),
    ("GFC",       "2007-07", "2009-12", "red"),
    ("COVID",     "2020-03", "2020-06", "purple"),
    ("2022 hike", "2022-01", "2023-06", "orange"),
]

# Historical episodes: (start, end, expected_regime)
HISTORICAL_EPISODES = {
    "dot_com":   ("1998-01", "2001-03", "EXP"),
    "gfc":       ("2008-09", "2009-03", "MR"),
    "covid":     ("2020-02", "2020-04", "MR"),
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_global_cci_monthly():
    """Return the monthly global OECD CCI series (100 = long-run average)."""
    s = pd.read_csv(GLOBAL_CCI_PATH, index_col="date",
                    parse_dates=True)["global_cci"].dropna()
    s.index = s.index + pd.offsets.MonthEnd(0)
    return s


def load_global_cci_pair(market, start, end):
    """
    Load (y, z, dates) for a (market, global-CCI) pair.

    z = global OECD CCI level (no negation — high = optimistic = EXP).
    """
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()

    cci  = load_global_cci_monthly()
    df   = pd.DataFrame({"price": prices, "cci": cci}).dropna().loc[start:end]

    y     = np.log(df["price"].values).astype(float)
    z     = df["cci"].values.astype(float)
    dates = np.array(df.index, dtype="datetime64[ns]")
    return y, z, dates


def _grid_bounds(z):
    """
    Adaptive grid bounds for global CCI.
    Uses +/-3 sigma from mean.
    min_gap enforces a minimum band of 2.0 CCI points (same as country CCI).
    """
    mu, sigma = float(z.mean()), float(z.std())
    z_min = round(mu - 3.0 * sigma, 2)
    z_max = round(mu + 3.0 * sigma, 2)
    gridlen   = 100
    grid_step = (z_max - z_min) / (gridlen - 1)
    min_gap   = max(4, int(2.0 / grid_step))
    return z_min, z_max, gridlen, min_gap


# ---------------------------------------------------------------------------
# Stage 1 - Inspection
# ---------------------------------------------------------------------------

def inspect_global_cci():
    """Plot global OECD CCI 1990-2026 with episode shading."""
    cci = load_global_cci_monthly().loc[START:]

    print(f"\nGlobal OECD CCI stats (1990-present): "
          f"mean={cci.mean():.3f}  std={cci.std():.3f}  "
          f"min={cci.min():.3f}  max={cci.max():.3f}")
    print(f"  Current (latest): {cci.iloc[-1]:.3f}  "
          f"as of {cci.index[-1].strftime('%Y-%m')}")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 4))

    dates_np = np.array(cci.index, dtype="datetime64[ns]")
    ax.plot(dates_np, cci.values, color="black", linewidth=0.8)
    ax.axhline(100, color="gray", linewidth=0.7, linestyle="--",
               alpha=0.7, label="100 (long-run average)")
    ax.fill_between(dates_np, cci.values, 100,
                    where=(cci.values > 100), color="tomato",    alpha=0.20)
    ax.fill_between(dates_np, cci.values, 100,
                    where=(cci.values < 100), color="cornflowerblue", alpha=0.20)

    for label, start, end, color in EPISODES:
        ep = cci.loc[start:end]
        if len(ep):
            ep_np = np.array(ep.index, dtype="datetime64[ns]")
            ax.axvspan(ep_np[0], ep_np[-1], alpha=0.15, color=color, label=label)

    patches = [mpatches.Patch(color=c, alpha=0.4, label=l)
               for l, _, _, c in EPISODES]
    ax.legend(handles=patches, fontsize=7, loc="lower left")
    ax.set_title("OECD Global Composite CCI (CSCICP03OECDm)  "
                 "-- above 100 = optimistic / bubble risk", fontsize=9)
    ax.set_ylabel("CCI (100 = long-run avg)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "global_cci_overview.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Stage 2 - Exogeneity screen
# ---------------------------------------------------------------------------

def exogeneity_screen_global_cci(n_lags=4, alpha=0.05):
    """
    Reverse Granger test: does equity return Granger-cause delta(global CCI)?
    If yes, the global CCI reflects equity sentiment -> endogenous -> FAIL.
    Gate: p > alpha -> ADMISSIBLE.

    Global CCI aggregates 38 OECD members; no single market's returns can
    materially move the aggregate, so we expect clean passes.
    """
    print(f"\n{'='*70}")
    print("STAGE 2 -- Exogeneity screen (reverse Granger: return -> d(global CCI))")
    print(f"{'='*70}")
    print(f"{'Market':<14} {'Country':<18} {'F':>7}  {'p':>7}  Gate")
    print("-" * 55)

    admissible = []
    for market, info in MARKETS.items():
        try:
            y, z, _ = load_global_cci_pair(market, START, FULL_END)
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

    print(f"\n{len(admissible)} of {len(MARKETS)} markets admissible.")
    return admissible


# ---------------------------------------------------------------------------
# Stage 3 - US validation (known-answer test)
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """
    Check whether key episodes fall in the expected regime.

    EXP (z > c2): high global CCI -> optimism / bubble risk
    MR  (z < c1): low  global CCI -> pessimism / crisis
    """
    regime_df = pd.DataFrame({
        "regime": [["RW", "MR", "EXP"][s] for s in state],
    }, index=pd.DatetimeIndex(dates))

    def n_regime(r, start, end):
        return (regime_df.loc[start:end]["regime"] == r).sum()

    dotcom_exp = n_regime("EXP", "1997-01", "2001-12")
    gfc_mr     = n_regime("MR",  "2007-07", "2009-12")
    covid_mr   = n_regime("MR",  "2020-01", "2020-06")
    hike22_mr  = n_regime("MR",  "2022-01", "2023-06")
    recent_exp = n_regime("EXP", "2021-01", "2026-06")

    if verbose:
        print(f"    dot-com EXP: {dotcom_exp}  |  GFC MR: {gfc_mr}  |  "
              f"COVID MR: {covid_mr}  |  2022 MR: {hike22_mr}  |  "
              f"2021-present EXP: {recent_exp}", end="  ")

    has_exp = dotcom_exp >= min_months
    has_mr  = gfc_mr     >= min_months

    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


def validate_us_global_cci():
    """S&P 500 + global CCI: full-sample estimation and episode overlap."""
    print(f"\n{'='*70}")
    print("STAGE 3 -- Validation: S&P 500 + global CCI (full sample 1990-2026)")
    print(f"{'='*70}")

    y, z, dates = load_global_cci_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)
    print(f"  T={len(y)}  CCI=[{z.min():.3f}, {z.max():.3f}]  "
          f"grid=[{z_min:.2f}, {z_max:.2f}]  n={gl}  min_gap={mg}")

    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
    c1, c2 = opt["c1"], opt["c2"]
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)

    print(f"  c1={c1:.3f}  c2={c2:.3f}")
    print(f"  MR={100*(state==1).sum()/T:.1f}%  "
          f"RW={100*(state==0).sum()/T:.1f}%  "
          f"EXP={100*(state==2).sum()/T:.1f}%")

    verdict = _episode_verdict(state, dates[1:])
    print(f"\n  Verdict: {verdict}")
    if verdict in ("BOTH TAILS", "FEAR GAUGE", "EUPHORIA GAUGE"):
        print("  Validation PASSED -- proceed to cross-market analysis.")
    else:
        print("  WARNING: weak episode overlap.")

    return c1, c2, verdict


# ---------------------------------------------------------------------------
# Stage 4 - Rolling stability
# ---------------------------------------------------------------------------

def rolling_global_cci_stability():
    """10-year rolling-window thresholds for S&P 500 + global CCI."""
    print(f"\n{'='*70}")
    print("STAGE 4 -- Rolling-window stability (S&P 500 + global CCI)")
    print(f"{'='*70}")

    y, z, dates = load_global_cci_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)

    y_in, z_in, _ = load_global_cci_pair("sp500", START, INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")

    print(f"  In-sample ref: c1={ref['c1']:.3f}  c2={ref['c2']:.3f}")
    print(f"  Rolling {WINDOW_MONTHS//12}-yr windows ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    print(f" {len(rows)} windows")

    os.makedirs(TABLES_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=["window_end", "c1", "c2"])
    df["window_end"] = pd.DatetimeIndex(df["window_end"]).strftime("%Y-%m")
    df = df.round({"c1": 3, "c2": 3})
    csv_path = os.path.join(TABLES_DIR, "rolling_thresholds_SP500_GLOBAL_CCI.csv")
    df.to_csv(csv_path, index=False)
    print(f"  c1: min={df['c1'].min():.3f}  max={df['c1'].max():.3f}  "
          f"mean={df['c1'].mean():.3f}  ref={ref['c1']:.3f}")
    print(f"  c2: min={df['c2'].min():.3f}  max={df['c2'].max():.3f}  "
          f"mean={df['c2'].mean():.3f}  ref={ref['c2']:.3f}")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    dates_arr = np.array([r[0] for r in rows], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows])
    c2_arr    = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates_arr, c1_arr, color="cornflowerblue", linewidth=1.8, label="c1 (rolling)")
    ax.plot(dates_arr, c2_arr, color="tomato",         linewidth=1.8, label="c2 (rolling)")
    ax.axhline(ref["c1"], color="cornflowerblue", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c1 in-sample ref ({ref['c1']:.3f})")
    ax.axhline(ref["c2"], color="tomato",         linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c2 in-sample ref ({ref['c2']:.3f})")
    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7, label="2015-06 paper cutoff")
    ax.axhline(100, color="gray", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.set_title("SP500 + global CCI -- rolling 10-yr TAR thresholds  "
                 "[100 = long-run avg]", fontsize=9)
    ax.set_xlabel("Window end date", fontsize=8)
    ax.set_ylabel("CCI threshold", fontsize=8)
    ax.legend(fontsize=7, ncol=2)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "rolling_thresholds_SP500_GLOBAL_CCI.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")
    print(f"  Saved: {csv_path}")


# ---------------------------------------------------------------------------
# Stage 5 - Cross-market estimation
# ---------------------------------------------------------------------------

def _episode_coverage(state, dates):
    """
    For each historical episode, return % of months classified in the expected regime.
    Returns None for episodes with no data in the market's history.
    """
    regime_map = {0: "RW", 1: "MR", 2: "EXP"}
    s = pd.Series([regime_map[x] for x in state], index=pd.DatetimeIndex(dates))
    out = {}
    for name, (start, end, target) in HISTORICAL_EPISODES.items():
        w = s.loc[start:end]
        out[name] = round(100.0 * (w == target).sum() / len(w), 1) if len(w) else None
    return out


def _sig_marker(tstat):
    """Return significance indicator string based on large-sample critical values."""
    if tstat is None or (isinstance(tstat, float) and np.isnan(tstat)):
        return ""
    a = abs(tstat)
    if a > 2.576: return "***"
    if a > 1.960: return "**"
    if a > 1.645: return "*"
    return ""


def _estimate_one(market, start=START, end=FULL_END, spec=1, verbose=True):
    """TAR estimation + episode verdict for one market with global CCI trigger."""
    y, z, dates = load_global_cci_pair(market, start, end)
    if len(y) < 340:
        return None

    z_min, z_max, gl, mg = _grid_bounds(z)
    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, "returns")
    c1, c2 = opt["c1"], opt["c2"]

    res    = standard_errors(y, z, c1, c2, spec, "returns")
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)
    verdict = _episode_verdict(state, dates[1:], verbose=verbose)

    cov = _episode_coverage(state, dates[1:])
    latest_cci = load_global_cci_monthly().iloc[-1]
    if latest_cci < c1:    current = "MR"
    elif latest_cci > c2:  current = "EXP"
    else:                   current = "RW"

    return {
        "market":   market,
        "country":  MARKETS[market]["country"],
        "T":        T,
        "c1":       c1,  "c2": c2,
        "n_mr":     res["n1"],    "n_rw":  res["n2"],  "n_ex": res["n3"],
        "beta_mr":  res["beta1"], "se_mr": res["se_b1"],
        "sig_mr":   _sig_marker(res.get("tstat1")),
        "beta_ex":  res["beta3"], "se_ex": res["se_b3"],
        "sig_ex":   _sig_marker(res.get("tstat3")),
        "dc_exp":   cov["dot_com"],
        "gfc_mr":   cov["gfc"],
        "covid_mr": cov["covid"],
        "current_cci":    round(float(latest_cci), 3),
        "current_regime": current,
        "verdict":  verdict,
    }


def run_all_markets(admissible=None):
    """Stage 5: TAR for all (or admissible) markets with global CCI trigger."""
    print(f"\n{'='*70}")
    print("STAGE 5 -- Cross-market estimation (global CCI trigger, spec=1)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    rows = []

    for market in markets:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) ...", end="", flush=True)
        try:
            r = _estimate_one(market, verbose=True)
            if r is None:
                print(" SKIP (< 340 obs)")
                continue
            rows.append(r)
            print(f"  c1={r['c1']:.3f}  c2={r['c2']:.3f}  {r['verdict']}")
        except Exception as e:
            print(f" ERROR: {e}")

    if not rows:
        return

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1':>7} {'c2':>7}  "
          f"{'MR%':>5} {'RW%':>5} {'EXP%':>5}  "
          f"{'b_MR':>8} {'b_EX':>8}  "
          f"{'DC_EXP':>7} {'GFC_MR':>7} {'COVID':>6}  "
          f"{'Now':>4}  Verdict")
    print("-" * 111)
    for r in rows:
        T = r["T"]
        def _fmt_cov(v):
            return f"{v:>5.0f}%" if v is not None else "  n/a "
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>7.3f} {r['c2']:>7.3f}  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% {100*r['n_ex']/T:>4.0f}%  "
              f"{r['beta_mr']:>6.3f}{r['sig_mr']:<2} {r['beta_ex']:>6.3f}{r['sig_ex']:<2}  "
              f"{_fmt_cov(r['dc_exp'])} {_fmt_cov(r['gfc_mr'])} {_fmt_cov(r['covid_mr'])}  "
              f"{r['current_regime']:>4}  {r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(TABLES_DIR, "global_cci_all_markets.csv"), index=False
    )
    print(f"\nSaved: {os.path.join(TABLES_DIR, 'global_cci_all_markets.csv')}")
    return rows


# ---------------------------------------------------------------------------
# Stage 6 - Bubble call
# ---------------------------------------------------------------------------

def bubble_call(admissible=None):
    """
    Stage 6: Option A + B bubble call for all admissible markets.
    Reuses bubble_now.plot_pair and regime_table.
    """
    print(f"\n{'='*70}")
    print("STAGE 6 -- Bubble call (Option A + B, global CCI trigger)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    specs, results_a, results_b = [], [], []

    for market in markets:
        label = f"{market.upper()}_GCCI"
        try:
            y, z, dates = load_global_cci_pair(market, START, FULL_END)
            if len(y) < 340:
                continue
            z_min, z_max, gl, mg = _grid_bounds(z)

            # Option A: full-sample refit
            opt_a = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
            st_a  = _assign_states(z[1:], opt_a["c1"], opt_a["c2"])
            ra = {"c1": opt_a["c1"], "c2": opt_a["c2"], "state": st_a,
                  "dates": dates[1:], "y": y, "label": label}

            # Option B: in-sample fit (1990-2015), classify full period
            y_in, z_in, _ = load_global_cci_pair(market, START, INSAMPLE_END)
            opt_b = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
            st_b  = _assign_states(z[1:], opt_b["c1"], opt_b["c2"])
            rb = {"c1": opt_b["c1"], "c2": opt_b["c2"], "state": st_b,
                  "dates": dates[1:], "y": y, "label": label}

            oos = dates[1:] > np.datetime64("2015-06-30", "ns")
            print(f"  {label}: A(c1={opt_a['c1']:.3f},c2={opt_a['c2']:.3f})  "
                  f"B(c1={opt_b['c1']:.3f},c2={opt_b['c2']:.3f})  "
                  f"OOS n={oos.sum()}")

            specs.append(("global_cci", market, label))
            results_a.append(ra)
            results_b.append(rb)

        except Exception as e:
            print(f"  {market}: ERROR: {e}")

    if not results_a:
        print("  No results to plot.")
        return

    print("\n--- Plots ---")
    for spec, ra, rb in zip(specs, results_a, results_b):
        plot_pair(spec, ra, rb)

    regime_table(results_a, results_b, n_months=54,
                 csv_name="global_cci_2022_2026.csv")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all():
    inspect_global_cci()
    admissible = exogeneity_screen_global_cci()
    validate_us_global_cci()
    rolling_global_cci_stability()
    run_all_markets(admissible)
    bubble_call(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "inspect":  inspect_global_cci,
        "screen":   exogeneity_screen_global_cci,
        "validate": validate_us_global_cci,
        "rolling":  rolling_global_cci_stability,
        "estimate": lambda: run_all_markets(exogeneity_screen_global_cci()),
        "bubble":   lambda: bubble_call(),
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()
