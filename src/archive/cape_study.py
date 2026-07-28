"""
Shiller CAPE as a global bubble trigger for the TAR model.

CAPE (Cyclically Adjusted P/E Ratio, P/E10) measures equity valuation relative
to 10-year average real earnings.  High CAPE = expensive / overvalued markets.

SIGN CONVENTION: No negation needed.  High CAPE â†’ EXP state (bubble risk).
                 Low  CAPE â†’ MR  state (cheapness / post-crash).
This is the opposite of ANFCI where negation was required.

Because the research question is "is there a bubble?", only the upper tail (EXP)
is diagnostically relevant.  "EUPHORIA GAUGE" verdicts (EXP in dot-com, no MR
in GFC) are treated as acceptable alongside "BOTH TAILS".

Six stages:
  1 â€” inspect    : plot CAPE with episode shading, sanity checks
  2 â€” screen     : Granger exogeneity screen for all 23 markets
  3 â€” validate   : S&P 500 sanity check (known-answer test)
  4 â€” rolling    : rolling-window threshold stability
  5 â€” estimate   : TAR estimation for all admissible markets
  6 â€” bubble     : Option A + B bubble call, regime table, headline chart

Usage:
    cd src && python cape_study.py              # full pipeline
    python cape_study.py inspect
    python cape_study.py screen
    python cape_study.py validate
    python cape_study.py rolling
    python cape_study.py estimate
    python cape_study.py bubble
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

CAPE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentiment",
                         "cape_monthly.csv")
START     = "1990-01"

EPISODES = [
    ("Dot-com",   "1997-01", "2001-12", "gold"),
    ("GFC",       "2007-07", "2009-12", "red"),
    ("COVID",     "2020-03", "2020-06", "purple"),
    ("2022 hike", "2022-01", "2023-06", "orange"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cape_monthly():
    """Return the raw monthly CAPE series (high = expensive = bubble risk)."""
    s = pd.read_csv(CAPE_PATH, index_col="date", parse_dates=True)["cape"].dropna()
    s.index = s.index + pd.offsets.MonthEnd(0)
    return s


def load_cape_pair(market, start, end):
    """
    Load (y, z, dates) for a (market, CAPE) pair.

    z = CAPE (no negation â€” high z = expensive = bubble risk = EXP state).
    Returns numpy arrays, same format as anfci_study.load_anfci_pair.
    """
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()

    cape = load_cape_monthly()
    df   = pd.DataFrame({"price": prices, "cape": cape}).dropna().loc[start:end]

    y     = np.log(df["price"].values).astype(float)
    z     = df["cape"].values.astype(float)
    dates = np.array(df.index, dtype="datetime64[ns]")
    return y, z, dates


def _grid_bounds(z):
    """
    Compute TAR grid bounds for the CAPE series.
    Uses Â±3 standard deviations, gridlen=150, min_gap enforces 0.15-unit band.
    """
    mu, sigma = float(z.mean()), float(z.std())
    z_min = round(mu - 3.0 * sigma, 2)
    z_max = round(mu + 3.0 * sigma, 2)
    gridlen   = 150
    grid_step = (z_max - z_min) / (gridlen - 1)
    min_gap   = max(4, int(0.15 / grid_step))
    return z_min, z_max, gridlen, min_gap


# ---------------------------------------------------------------------------
# Stage 1 â€” Inspection
# ---------------------------------------------------------------------------

def inspect_cape():
    """Plot CAPE 1990â€“2026 with episode shading and print summary stats."""
    cape = load_cape_monthly().loc[START:]

    print(f"\nCAPE stats (1990â€“present): "
          f"mean={cape.mean():.2f}  std={cape.std():.2f}  "
          f"min={cape.min():.2f}  max={cape.max():.2f}")
    print(f"  Current (latest): {cape.iloc[-1]:.2f}  "
          f"as of {cape.index[-1].strftime('%Y-%m')}")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 4))

    dates_np = np.array(cape.index, dtype="datetime64[ns]")
    ax.plot(dates_np, cape.values, color="black", linewidth=0.8)

    # Reference lines: historical mean, "elevated" zone, current reading
    ax.axhline(cape.mean(), color="gray",    linewidth=0.7, linestyle="--",
               alpha=0.7, label=f"1990â€“present mean ({cape.mean():.1f})")
    ax.axhline(30,          color="orange",  linewidth=0.7, linestyle="--",
               alpha=0.7, label="CAPE = 30 (historically elevated)")
    ax.axhline(38,          color="tomato",  linewidth=0.7, linestyle="--",
               alpha=0.7, label="CAPE = 38 (extreme)")

    for label, start, end, color in EPISODES:
        ep = cape.loc[start:end]
        if len(ep):
            ep_np = np.array(ep.index, dtype="datetime64[ns]")
            ax.axvspan(ep_np[0], ep_np[-1], alpha=0.15, color=color, label=label)

    patches = [mpatches.Patch(color=c, alpha=0.4, label=l)
               for l, _, _, c in EPISODES]
    ax.legend(handles=patches, fontsize=7, loc="upper left")
    ax.set_title("Shiller CAPE (P/E10)  â€”  high = expensive / bubble risk", fontsize=9)
    ax.set_ylabel("CAPE", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "cape_overview.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Stage 2 â€” Exogeneity screen
# ---------------------------------------------------------------------------

def exogeneity_screen_cape(n_lags=3, alpha=0.05):
    """
    Gate each of the 23 markets by testing CAPE exogeneity.

    Reverse test: does monthly equity return Granger-cause Î”CAPE?
    If yes, CAPE is endogenous (reflects equity prices, not an exogenous signal).
    Gate: p > alpha  â†’  ADMISSIBLE.

    Note: S&P 500 is expected to FAIL â€” its price is the numerator of CAPE,
    so US returns mechanically move CAPE contemporaneously.  Non-US market
    returns cannot materially move a 10-year US earnings average, so they
    should pass cleanly.  n_lags=3 (not 4) because the 10-year smoothing in
    CAPE's denominator makes 3 months of returns extremely unlikely to matter.
    """
    print(f"\n{'='*70}")
    print("STAGE 2 -- Exogeneity screen (reverse Granger: return -> dCAPE)")
    print(f"{'='*70}")
    print(f"{'Market':<14} {'Country':<18} {'F':>7}  {'p':>7}  Gate")
    print("-" * 55)

    admissible = []
    for market, info in MARKETS.items():
        try:
            y, z, _ = load_cape_pair(market, START, FULL_END)
            y_ret   = np.diff(y)
            z_diff  = np.diff(z)

            n = min(len(y_ret), len(z_diff))
            rev_F, rev_p = granger_f_test(z_diff[-n:], y_ret[-n:], n_lags)

            verdict = "PASS" if rev_p > alpha else "FAIL"
            if verdict == "PASS":
                admissible.append(market)
            flag = "  â† expected" if market == "sp500" and verdict == "FAIL" else ""
            print(f"{market:<14} {info['country']:<18} {rev_F:>7.3f}  {rev_p:>7.4f}  {verdict}{flag}")
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    print(f"\n{len(admissible)} of {len(MARKETS)} markets admissible.")
    return admissible


# ---------------------------------------------------------------------------
# Stage 3 â€” US validation (known-answer test)
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """
    Check whether key episodes fall in the expected regime.

    With z = CAPE (no negation):
      EXP state (z > c2): expensive markets, bubble risk period
      MR  state (z < c1): cheap markets, post-crash recovery
    For bubble detection, "EUPHORIA GAUGE" (EXP present, MR absent) is acceptable
    because CAPE is intentionally a one-tailed bubble indicator.
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

    # Also check 2017-present for current bubble call
    current_exp = n_regime("EXP", "2017-01", "2026-06")

    if verbose:
        print(f"    dot-com EXP: {dotcom_exp}  |  GFC MR: {gfc_mr}  |  "
              f"COVID MR: {covid_mr}  |  2022 MR: {hike22_mr}  |  "
              f"2017-present EXP: {current_exp}", end="  ")

    has_exp = dotcom_exp >= min_months
    has_mr  = gfc_mr     >= min_months

    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


def validate_us_cape():
    """S&P 500 + CAPE: full-sample estimation and episode overlap (known-answer test)."""
    print(f"\n{'='*70}")
    print("STAGE 3 â€” Validation: S&P 500 + CAPE (full sample 1990â€“2026)")
    print(f"{'='*70}")

    y, z, dates = load_cape_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)
    print(f"  T={len(y)}  CAPE=[{z.min():.1f}, {z.max():.1f}]  "
          f"grid=[{z_min:.1f}, {z_max:.1f}]  n={gl}  min_gap={mg}")

    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
    c1, c2 = opt["c1"], opt["c2"]
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)

    print(f"  c1={c1:.2f}  c2={c2:.2f}  "
          f"(CAPE: cheap<{c1:.1f}=MR  expensive>{c2:.1f}=EXP)")
    print(f"  MR={100*(state==1).sum()/T:.1f}%  "
          f"RW={100*(state==0).sum()/T:.1f}%  "
          f"EXP={100*(state==2).sum()/T:.1f}%")

    verdict = _episode_verdict(state, dates[1:])
    print(f"\n  Verdict: {verdict}")
    if verdict in ("BOTH TAILS", "EUPHORIA GAUGE"):
        print("  Validation PASSED â€” proceed to cross-market analysis.")
        print("  (EUPHORIA GAUGE is acceptable: CAPE is a one-tailed bubble signal.)")
    else:
        print("  WARNING: weak episode overlap. Check CAPE alignment.")

    return c1, c2, verdict


# ---------------------------------------------------------------------------
# Stage 4 â€” Rolling stability
# ---------------------------------------------------------------------------

def rolling_cape_stability():
    """10-year rolling-window thresholds for S&P 500 + CAPE."""
    print(f"\n{'='*70}")
    print("STAGE 4 â€” Rolling-window stability (S&P 500 + CAPE)")
    print(f"{'='*70}")

    y, z, dates = load_cape_pair("sp500", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)

    # In-sample reference
    y_in, z_in, _ = load_cape_pair("sp500", START, INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")

    print(f"  In-sample ref: c1={ref['c1']:.2f}  c2={ref['c2']:.2f}")
    print(f"  Rolling {WINDOW_MONTHS//12}-yr windows ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    print(f" {len(rows)} windows")

    # Save table
    os.makedirs(TABLES_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=["window_end", "c1", "c2"])
    df["window_end"] = pd.DatetimeIndex(df["window_end"]).strftime("%Y-%m")
    df = df.round({"c1": 2, "c2": 2})
    csv_path = os.path.join(TABLES_DIR, "rolling_thresholds_SP500_CAPE.csv")
    df.to_csv(csv_path, index=False)
    print(f"  c1: min={df['c1'].min():.2f}  max={df['c1'].max():.2f}  "
          f"mean={df['c1'].mean():.2f}  ref={ref['c1']:.2f}")
    print(f"  c2: min={df['c2'].min():.2f}  max={df['c2'].max():.2f}  "
          f"mean={df['c2'].mean():.2f}  ref={ref['c2']:.2f}")

    # Plot
    os.makedirs(FIGURES_DIR, exist_ok=True)
    dates_arr = np.array([r[0] for r in rows], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows])
    c2_arr    = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates_arr, c1_arr, color="cornflowerblue", linewidth=1.8, label="câ‚ (rolling)")
    ax.plot(dates_arr, c2_arr, color="tomato",         linewidth=1.8, label="câ‚‚ (rolling)")
    ax.axhline(ref["c1"], color="cornflowerblue", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"câ‚ in-sample ref ({ref['c1']:.2f})")
    ax.axhline(ref["c2"], color="tomato",         linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"câ‚‚ in-sample ref ({ref['c2']:.2f})")
    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7, label="2015-06 paper cutoff")
    ax.set_title("SP500+CAPE â€” rolling 10-year TAR thresholds (step=1yr)  "
                 "[high CAPE = expensive = EXP state]", fontsize=9)
    ax.set_xlabel("Window end date", fontsize=8)
    ax.set_ylabel("CAPE threshold", fontsize=8)
    ax.legend(fontsize=7, ncol=2)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "rolling_thresholds_SP500_CAPE.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")
    print(f"  Saved: {csv_path}")


# ---------------------------------------------------------------------------
# Stage 5 â€” Cross-market estimation
# ---------------------------------------------------------------------------

def _estimate_one(market, start=START, end=FULL_END, spec=1, verbose=True):
    """TAR estimation + episode verdict for one market with CAPE trigger."""
    y, z, dates = load_cape_pair(market, start, end)
    if len(y) < 120:
        return None

    z_min, z_max, gl, mg = _grid_bounds(z)
    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, "returns")
    c1, c2 = opt["c1"], opt["c2"]

    res    = standard_errors(y, z, c1, c2, spec, "returns")
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)
    verdict = _episode_verdict(state, dates[1:], verbose=verbose)

    return {
        "market":   market,
        "country":  MARKETS[market]["country"],
        "T":        T,
        "c1":       c1,  "c2":     c2,
        "beta_mr":  res["beta1"], "beta_ex": res["beta3"],
        "n_mr":     res["n1"],    "n_rw":    res["n2"], "n_ex": res["n3"],
        "verdict":  verdict,
    }


def run_all_markets(admissible=None):
    """Stage 5: TAR estimation for all (or admissible) markets with CAPE trigger."""
    print(f"\n{'='*70}")
    print("STAGE 5 â€” Cross-market estimation (CAPE trigger, spec=1)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
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
            print(f"  c1={r['c1']:.2f}  c2={r['c2']:.2f}  {r['verdict']}")
        except Exception as e:
            print(f" ERROR: {e}")

    if not rows:
        return

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1':>6} {'c2':>6}  "
          f"{'MR%':>5} {'RW%':>5} {'EXP%':>5}  Verdict")
    print("-" * 85)
    for r in rows:
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>6.2f} {r['c2']:>6.2f}  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% {100*r['n_ex']/T:>4.0f}%  "
              f"{r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(TABLES_DIR, "cape_all_markets.csv"), index=False
    )
    print(f"\nSaved: {os.path.join(TABLES_DIR, 'cape_all_markets.csv')}")
    return rows


# ---------------------------------------------------------------------------
# Stage 6 â€” Bubble call (Option A + B, all admissible markets)
# ---------------------------------------------------------------------------

def bubble_call(admissible=None):
    """
    Stage 6: Option A (full-sample refit) and Option B (OOS, 1990-2015 thresholds)
    for all admissible markets. Reuses bubble_now.plot_pair and regime_table.
    """
    print(f"\n{'='*70}")
    print("STAGE 6 â€” Bubble call (Option A + B, CAPE trigger)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    specs, results_a, results_b = [], [], []

    for market in markets:
        label = f"{market.upper()}_CAPE"
        try:
            y, z, dates = load_cape_pair(market, START, FULL_END)
            if len(y) < 120:
                continue
            z_min, z_max, gl, mg = _grid_bounds(z)

            # Option A: full-sample refit
            opt_a = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
            st_a  = _assign_states(z[1:], opt_a["c1"], opt_a["c2"])
            ra = {"c1": opt_a["c1"], "c2": opt_a["c2"], "state": st_a,
                  "dates": dates[1:], "y": y, "label": label}

            # Option B: in-sample fit (1990â€“2015), classify full period
            y_in, z_in, _ = load_cape_pair(market, START, INSAMPLE_END)
            opt_b = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
            st_b  = _assign_states(z[1:], opt_b["c1"], opt_b["c2"])
            rb = {"c1": opt_b["c1"], "c2": opt_b["c2"], "state": st_b,
                  "dates": dates[1:], "y": y, "label": label}

            oos = dates[1:] > np.datetime64("2015-06-30", "ns")
            print(f"  {label}: A(c1={opt_a['c1']:.2f},c2={opt_a['c2']:.2f})  "
                  f"B(c1={opt_b['c1']:.2f},c2={opt_b['c2']:.2f})  "
                  f"OOS n={oos.sum()}")

            specs.append(("cape", market, label))
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

    regime_table(results_a, results_b, n_months=24,
                 csv_name="cape_last24m.csv")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all():
    inspect_cape()
    admissible = exogeneity_screen_cape()
    validate_us_cape()
    rolling_cape_stability()
    run_all_markets(admissible)
    bubble_call(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "inspect":  inspect_cape,
        "screen":   exogeneity_screen_cape,
        "validate": validate_us_cape,
        "rolling":  rolling_cape_stability,
        "estimate": lambda: run_all_markets(),
        "bubble":   lambda: bubble_call(),
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()

