"""
Lagged S&P 500 monthly return as a global bubble trigger for the TAR model.

The trigger z[t] = log(SP500[t-1]/SP500[t-2]) â€” last month's S&P 500 return â€”
is used to classify the current month's equity return in each of the 23 markets.

SIGN CONVENTION: No negation.  High z (strong prior-month SP500 gain) â†’ EXP.
                              Low z  (sharp prior-month SP500 loss)  â†’ MR.

EXOGENEITY: Trivially satisfied by temporal ordering.  This month's FTSE return
cannot have caused last month's S&P 500 return.  The reverse Granger test will
pass for all markets by construction.

RELEVANCE: The forward Granger test (does lagged SP500 predict market returns?)
is reported as a diagnostic.  It should pass for integrated markets and fail for
segmented ones (Shanghai, etc.).

DATA: S&P 500 prices come from eq_sp500 in the existing monthly_panel.csv (^GSPC,
1975-01 onward).  No separate data collection step is needed.

Six stages:
  1 â€” inspect    : plot SP500 monthly return series with episode shading
  2 â€” screen     : reverse + forward Granger tests for all 23 markets
  3 â€” validate   : FTSE 100 sanity check (known-answer test)
  4 â€” rolling    : rolling-window threshold stability
  5 â€” estimate   : TAR estimation for all admissible markets
  6 â€” bubble     : Option A + B bubble call, regime table

Usage:
    cd src && python spy_study.py              # full pipeline
    python spy_study.py inspect
    python spy_study.py screen
    python spy_study.py validate
    python spy_study.py rolling
    python spy_study.py estimate
    python spy_study.py bubble
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

START = "1990-01"

EPISODES = [
    ("Dot-com",   "1997-01", "2001-12", "gold"),
    ("GFC",       "2007-07", "2009-12", "red"),
    ("COVID",     "2020-03", "2020-06", "purple"),
    ("2022 hike", "2022-01", "2023-06", "orange"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sp500_returns():
    """Return monthly S&P 500 log return series from the panel."""
    panel = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel["eq_sp500"].dropna()
    prices.index = prices.index + pd.offsets.MonthEnd(0)
    returns = np.log(prices / prices.shift(1)).dropna()
    return returns


def load_spy_pair(market, start, end):
    """
    Load (y, z, dates) for a (market, lagged-SPY) pair.

    z[t] = log(SP500[t-1]/SP500[t-2])  â€” S&P 500 return one month ago.
    shift(1) is applied at load time so trigger_lag=0 inside the model.

    Alignment: inside estimate.py, dep[i] = y[i+1]-y[i] (market return at t)
    is classified by z_states[i] = z[i+1] (SP500 return at t-1). âœ“
    """
    panel = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)

    if market == "sp500":
        cols = ["eq_sp500"]
    else:
        cols = [f"eq_{market}", "eq_sp500"]

    df = panel[cols].dropna().loc[start:end].copy()

    sp500_log = np.log(df["eq_sp500"])
    df["z"] = sp500_log.diff().shift(1)   # z[t] = SP500_return[t-1]
    df = df.dropna()

    y     = np.log(df[f"eq_{market}"].values).astype(float)
    z     = df["z"].values.astype(float)
    dates = np.array(df.index, dtype="datetime64[ns]")
    return y, z, dates


def _grid_bounds(z):
    """
    Grid bounds for the lagged SP500 return trigger.
    Monthly returns have much smaller scale than ANFCI z-scores, so use fixed
    min_gap=4 (not the adaptive 0.15-unit formula which breaks on return scale).
    """
    mu, sigma = float(z.mean()), float(z.std())
    z_min = round(mu - 3.0 * sigma, 4)
    z_max = round(mu + 3.0 * sigma, 4)
    return z_min, z_max, 100, 4   # gridlen=100, min_gap=4


# ---------------------------------------------------------------------------
# Stage 1 â€” Inspection
# ---------------------------------------------------------------------------

def inspect_spy():
    """Plot SP500 monthly returns 1990-2026 with episode shading."""
    ret = load_sp500_returns().loc[START:]

    print(f"\nSP500 monthly log-return stats (1990-present): "
          f"mean={ret.mean():.4f}  std={ret.std():.4f}  "
          f"min={ret.min():.4f}  max={ret.max():.4f}")
    worst = ret.nsmallest(3)
    best  = ret.nlargest(3)
    print(f"  3 worst months: {worst.index.strftime('%Y-%m').tolist()} = "
          f"{[f'{v:.3f}' for v in worst.values]}")
    print(f"  3 best  months: {best.index.strftime('%Y-%m').tolist()} = "
          f"{[f'{v:.3f}' for v in best.values]}")

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 4))

    dates_np = np.array(ret.index, dtype="datetime64[ns]")
    ax.bar(dates_np, ret.values,
           width=np.timedelta64(20, "D"),
           color=np.where(ret.values >= 0, "cornflowerblue", "tomato"),
           alpha=0.7)
    ax.axhline(0, color="black", linewidth=0.5)

    for label, start, end, color in EPISODES:
        ep = ret.loc[start:end]
        if len(ep):
            ep_np = np.array(ep.index, dtype="datetime64[ns]")
            ax.axvspan(ep_np[0], ep_np[-1], alpha=0.12, color=color, label=label)

    patches = [mpatches.Patch(color=c, alpha=0.4, label=l)
               for l, _, _, c in EPISODES]
    ax.legend(handles=patches, fontsize=7, loc="lower left")
    ax.set_title("S&P 500 (^GSPC) monthly log-returns  â€”  used as lagged trigger",
                 fontsize=9)
    ax.set_ylabel("Log return", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "spy_overview.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Stage 2 â€” Exogeneity screen
# ---------------------------------------------------------------------------

def exogeneity_screen_spy(n_lags=3, alpha=0.05):
    """
    Two Granger tests per market:

    Reverse (exogeneity gate): does market return predict z (lagged SP500 return)?
      Trivially PASS for all markets â€” z[t] happened before y_ret[t].

    Forward (relevance diagnostic): does z predict market returns?
      PASS for integrated markets, FAIL for segmented markets.
      Printed as a diagnostic but NOT used to exclude markets.
    """
    print(f"\n{'='*75}")
    print("STAGE 2 -- Exogeneity + relevance screen (lagged S&P 500 return)")
    print(f"{'='*75}")
    print(f"{'Market':<14} {'Country':<18} {'Rev-F':>7} {'Rev-p':>7} Gate  "
          f"{'Fwd-F':>7} {'Fwd-p':>7} Relevant")
    print("-" * 75)

    admissible = []
    for market, info in MARKETS.items():
        try:
            y, z, _ = load_spy_pair(market, START, FULL_END)
            y_ret  = np.diff(y)
            z_test = z[1:]           # align: both length T-1
            n      = min(len(y_ret), len(z_test))

            rev_F, rev_p = granger_f_test(z_test[-n:], y_ret[-n:], n_lags)
            fwd_F, fwd_p = granger_f_test(y_ret[-n:], z_test[-n:], n_lags)

            gate     = "PASS" if rev_p > alpha else "FAIL"
            relevant = "YES " if fwd_p < alpha else "no  "
            if gate == "PASS":
                admissible.append(market)
            print(f"{market:<14} {info['country']:<18} "
                  f"{rev_F:>7.3f} {rev_p:>7.4f} {gate}  "
                  f"{fwd_F:>7.3f} {fwd_p:>7.4f} {relevant}")
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    print(f"\n{len(admissible)} of {len(MARKETS)} markets pass exogeneity gate.")
    return admissible


# ---------------------------------------------------------------------------
# Stage 3 â€” FTSE validation (known-answer test)
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """
    Check whether key episodes fall in the expected regime.

    EXP state (z > c2): strong prior-month SP500 gain â†’ bubble/momentum period
    MR  state (z < c1): sharp prior-month SP500 loss  â†’ crash/crisis period
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
    recent_exp = n_regime("EXP", "2023-01", "2026-06")

    if verbose:
        print(f"    dot-com EXP: {dotcom_exp}  |  GFC MR: {gfc_mr}  |  "
              f"COVID MR: {covid_mr}  |  2022 MR: {hike22_mr}  |  "
              f"2023-present EXP: {recent_exp}", end="  ")

    has_exp = dotcom_exp >= min_months
    has_mr  = gfc_mr     >= min_months

    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


def validate_ftse_spy():
    """FTSE 100 + lagged SPY: full-sample estimation and episode overlap."""
    print(f"\n{'='*70}")
    print("STAGE 3 â€” Validation: FTSE 100 + lagged SPY (full sample 1990-2026)")
    print(f"{'='*70}")

    y, z, dates = load_spy_pair("ftse100", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)
    print(f"  T={len(y)}  z=[{z.min():.4f}, {z.max():.4f}]  "
          f"grid=[{z_min:.4f}, {z_max:.4f}]  n={gl}  min_gap={mg}")

    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
    c1, c2 = opt["c1"], opt["c2"]
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)

    print(f"  c1={c1:.4f} ({c1*100:.1f}%)  c2={c2:.4f} ({c2*100:.1f}%)")
    print(f"  MR={100*(state==1).sum()/T:.1f}%  "
          f"RW={100*(state==0).sum()/T:.1f}%  "
          f"EXP={100*(state==2).sum()/T:.1f}%")

    verdict = _episode_verdict(state, dates[1:])
    print(f"\n  Verdict: {verdict}")
    if verdict in ("BOTH TAILS", "FEAR GAUGE", "EUPHORIA GAUGE"):
        print("  Validation PASSED â€” proceed to cross-market analysis.")
    else:
        print("  WARNING: weak episode overlap.")

    return c1, c2, verdict


# ---------------------------------------------------------------------------
# Stage 4 â€” Rolling stability
# ---------------------------------------------------------------------------

def rolling_spy_stability():
    """10-year rolling-window thresholds for FTSE 100 + lagged SPY."""
    print(f"\n{'='*70}")
    print("STAGE 4 â€” Rolling-window stability (FTSE 100 + lagged SPY)")
    print(f"{'='*70}")

    y, z, dates = load_spy_pair("ftse100", START, FULL_END)
    z_min, z_max, gl, mg = _grid_bounds(z)

    # In-sample reference
    y_in, z_in, _ = load_spy_pair("ftse100", START, INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")

    print(f"  In-sample ref: c1={ref['c1']:.4f} ({ref['c1']*100:.1f}%)  "
          f"c2={ref['c2']:.4f} ({ref['c2']*100:.1f}%)")
    print(f"  Rolling {WINDOW_MONTHS//12}-yr windows ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    print(f" {len(rows)} windows")

    # Save table
    os.makedirs(TABLES_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=["window_end", "c1", "c2"])
    df["window_end"] = pd.DatetimeIndex(df["window_end"]).strftime("%Y-%m")
    df = df.round({"c1": 4, "c2": 4})
    csv_path = os.path.join(TABLES_DIR, "rolling_thresholds_FTSE100_SPY.csv")
    df.to_csv(csv_path, index=False)
    print(f"  c1: min={df['c1'].min():.4f}  max={df['c1'].max():.4f}  "
          f"mean={df['c1'].mean():.4f}  ref={ref['c1']:.4f}")
    print(f"  c2: min={df['c2'].min():.4f}  max={df['c2'].max():.4f}  "
          f"mean={df['c2'].mean():.4f}  ref={ref['c2']:.4f}")

    # Plot
    os.makedirs(FIGURES_DIR, exist_ok=True)
    dates_arr = np.array([r[0] for r in rows], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows])
    c2_arr    = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates_arr, c1_arr * 100, color="cornflowerblue", linewidth=1.8,
            label="câ‚ (rolling)")
    ax.plot(dates_arr, c2_arr * 100, color="tomato", linewidth=1.8,
            label="câ‚‚ (rolling)")
    ax.axhline(ref["c1"] * 100, color="cornflowerblue", linewidth=0.9,
               linestyle="--", alpha=0.65,
               label=f"câ‚ in-sample ref ({ref['c1']*100:.1f}%)")
    ax.axhline(ref["c2"] * 100, color="tomato", linewidth=0.9,
               linestyle="--", alpha=0.65,
               label=f"câ‚‚ in-sample ref ({ref['c2']*100:.1f}%)")
    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7, label="2015-06 paper cutoff")
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.set_title("FTSE100 + lagged SPY â€” rolling 10-yr TAR thresholds  "
                 "[z = lagged S&P 500 monthly return]", fontsize=9)
    ax.set_xlabel("Window end date", fontsize=8)
    ax.set_ylabel("Threshold (% monthly return)", fontsize=8)
    ax.legend(fontsize=7, ncol=2)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "rolling_thresholds_FTSE100_SPY.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out}")
    print(f"  Saved: {csv_path}")


# ---------------------------------------------------------------------------
# Stage 5 â€” Cross-market estimation
# ---------------------------------------------------------------------------

def _estimate_one(market, start=START, end=FULL_END, spec=1, verbose=True):
    """TAR estimation + episode verdict for one market with lagged SPY trigger."""
    y, z, dates = load_spy_pair(market, start, end)
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
        "c1_pct":   round(c1 * 100, 2),
        "c2_pct":   round(c2 * 100, 2),
        "beta_mr":  res["beta1"], "beta_ex": res["beta3"],
        "n_mr":     res["n1"],    "n_rw":    res["n2"], "n_ex": res["n3"],
        "verdict":  verdict,
    }


def run_all_markets(admissible=None):
    """Stage 5: TAR estimation for all (or admissible) markets with lagged SPY trigger."""
    print(f"\n{'='*70}")
    print("STAGE 5 â€” Cross-market estimation (lagged SPY trigger, spec=1)")
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
            print(f"  c1={r['c1_pct']:.1f}%  c2={r['c2_pct']:.1f}%  {r['verdict']}")
        except Exception as e:
            print(f" ERROR: {e}")

    if not rows:
        return

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1%':>6} {'c2%':>6}  "
          f"{'MR%':>5} {'RW%':>5} {'EXP%':>5}  Verdict")
    print("-" * 85)
    for r in rows:
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1_pct']:>5.1f}% {r['c2_pct']:>5.1f}%  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% {100*r['n_ex']/T:>4.0f}%  "
              f"{r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(TABLES_DIR, "spy_all_markets.csv"), index=False
    )
    print(f"\nSaved: {os.path.join(TABLES_DIR, 'spy_all_markets.csv')}")
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
    print("STAGE 6 â€” Bubble call (Option A + B, lagged SPY trigger)")
    print(f"{'='*70}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    specs, results_a, results_b = [], [], []

    for market in markets:
        label = f"{market.upper()}_SPY"
        try:
            y, z, dates = load_spy_pair(market, START, FULL_END)
            if len(y) < 120:
                continue
            z_min, z_max, gl, mg = _grid_bounds(z)

            # Option A: full-sample refit
            opt_a = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
            st_a  = _assign_states(z[1:], opt_a["c1"], opt_a["c2"])
            ra = {"c1": opt_a["c1"], "c2": opt_a["c2"], "state": st_a,
                  "dates": dates[1:], "y": y, "label": label}

            # Option B: in-sample fit (1990-2015), classify full period
            y_in, z_in, _ = load_spy_pair(market, START, INSAMPLE_END)
            opt_b = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
            st_b  = _assign_states(z[1:], opt_b["c1"], opt_b["c2"])
            rb = {"c1": opt_b["c1"], "c2": opt_b["c2"], "state": st_b,
                  "dates": dates[1:], "y": y, "label": label}

            oos = dates[1:] > np.datetime64("2015-06-30", "ns")
            print(f"  {label}: A(c1={opt_a['c1']*100:.1f}%,c2={opt_a['c2']*100:.1f}%)  "
                  f"B(c1={opt_b['c1']*100:.1f}%,c2={opt_b['c2']*100:.1f}%)  "
                  f"OOS n={oos.sum()}")

            specs.append(("spy", market, label))
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
                 csv_name="spy_last24m.csv")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all():
    inspect_spy()
    admissible = exogeneity_screen_spy()
    validate_ftse_spy()
    rolling_spy_stability()
    run_all_markets(admissible)
    bubble_call(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "inspect":  inspect_spy,
        "screen":   exogeneity_screen_spy,
        "validate": validate_ftse_spy,
        "rolling":  rolling_spy_stability,
        "estimate": lambda: run_all_markets(),
        "bubble":   lambda: bubble_call(),
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()

