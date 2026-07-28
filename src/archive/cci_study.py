"""
OECD CCI analysis: exogeneity screening, TAR estimation, and episode overlap tests
for each OECD market using its country-specific Consumer Confidence Indicator as
the sentiment trigger. Includes a side-by-side comparison against VIX-triggered results.

Usage:
    python cci_study.py            # full pipeline
    python cci_study.py screen     # exogeneity gate only
    python cci_study.py plot       # CCI time-series plots with episode shading
    python cci_study.py validate   # US MCSI validation (known-answer check)
    python cci_study.py estimate   # estimation for admissible markets
    python cci_study.py compare    # VIX vs CCI side-by-side comparison table
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from market_config import OECD_CCI_MARKETS, MARKETS
from exogeneity import granger_f_test
from replicate import PANEL_PATH, DAILY_PANEL_PATH, load_pair
from estimate import find_optimal_thresholds, standard_errors, _assign_states

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SENTIMENT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentiment")
FIGURES_DIR    = os.path.join(os.path.dirname(__file__), "..", "..", "results", "figures")
COVERAGE_PATH  = os.path.join(SENTIMENT_DIR, "oecd_cci_coverage.csv")

# Analysis window
START = "1990-01"
END   = "2015-06"

# Markets with >= 240 obs in window (kospi and ipc excluded)
USABLE_MARKETS = {k: v for k, v in OECD_CCI_MARKETS.items()
                  if k not in ("kospi", "ipc")}

# Historical episodes for overlap test
EPISODES = [
    ("Dot-com bubble", "1997-01", "2001-12", "gold"),
    ("GFC",           "2007-07", "2009-12", "red"),
    ("Euro crisis",   "2010-06", "2012-12", "orange"),
]


# ---------------------------------------------------------------------------
# Step 1 â€” Data loading
# ---------------------------------------------------------------------------

def load_cci_pair(market, oecd_code, start=START, end=END):
    """
    Load (y, z, dates) for CCI analysis.
    y = log monthly equity prices (from monthly_panel.csv)
    z = CCI levels (from oecd_cci_{CODE}.csv)
    Aligned on overlapping monthly dates.
    """
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()

    cci_path = os.path.join(SENTIMENT_DIR, f"oecd_cci_{oecd_code}.csv")
    cci = pd.read_csv(cci_path, index_col=0, parse_dates=True)["cci"].dropna()
    cci.index = cci.index + pd.offsets.MonthEnd(0)   # align to month-end like the equity panel

    df = pd.DataFrame({"price": prices, "cci": cci}).dropna()
    df = df.loc[start:end]

    y = np.log(df["price"].values).astype(float)
    z = df["cci"].values.astype(float)
    return y, z, df.index


def _load_grid_bounds():
    """Load per-country TAR grid bounds from coverage CSV."""
    cov = pd.read_csv(COVERAGE_PATH).set_index("market")
    return cov[["z_min", "z_max", "oecd_code"]].to_dict("index")


# ---------------------------------------------------------------------------
# Step 2 â€” Exogeneity screen
# ---------------------------------------------------------------------------

def exogeneity_screen(markets=None, start=START, end=END, n_lags=4, alpha=0.05):
    """
    Gate markets by testing CCI exogeneity in both directions.

    Standard (CCI -> returns): CCI should not predict equity returns.
    Reverse  (returns -> CCI): equity returns should not predict CCI.
                               If they do, CCI is a market reflection, not a signal.

    Returns list of admissible market keys.
    """
    if markets is None:
        markets = USABLE_MARKETS

    print(f"\n{'='*70}")
    print("STEP 2 â€” Exogeneity screen")
    print(f"{'='*70}")
    print(f"{'Market':<14} {'Country':<16} {'Reverse (ret->CCI)':<22} {'F':>7}  {'p':>7}  {'Gate'}")
    print("-" * 75)

    admissible = []
    for market, code in markets.items():
        try:
            y, z, _ = load_cci_pair(market, code, start, end)
            y_ret  = np.diff(y)
            z_diff = np.diff(z)

            min_len  = min(len(y_ret), len(z_diff))
            y_ret_a  = y_ret[-min_len:]
            z_diff_a = z_diff[-min_len:]

            # Gate: do equity returns Granger-cause CCI changes?
            # If yes, CCI is a market reflection not an exogenous signal.
            rev_F, rev_p = granger_f_test(z_diff_a, y_ret_a, n_lags)
            verdict = "ADMISSIBLE" if rev_p > alpha else "REJECTED"
            gate    = "PASS" if verdict == "ADMISSIBLE" else "FAIL"
            if gate == "PASS":
                admissible.append(market)

            country = MARKETS[market]["country"]
            print(f"{market:<14} {country:<16} {verdict:<22} {rev_F:>7.3f}  {rev_p:>7.4f}  {gate}")
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    print(f"\n{len(admissible)} of {len(markets)} markets passed: {admissible}")
    return admissible


# ---------------------------------------------------------------------------
# Step 3 â€” Plot CCI with episode shading
# ---------------------------------------------------------------------------

def plot_cci_episodes(markets=None, start=START, end=END):
    """Plot each market's CCI over time with key episodes shaded."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    if markets is None:
        markets = USABLE_MARKETS

    os.makedirs(FIGURES_DIR, exist_ok=True)

    n = len(markets)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4 * nrows))
    axes = axes.flatten()

    for ax, (market, code) in zip(axes, markets.items()):
        try:
            _, z, dates = load_cci_pair(market, code, start, end)
            ax.plot(dates, z, linewidth=0.8, color="steelblue")
            ax.axhline(100, color="black", linewidth=0.5, linestyle="--", alpha=0.4)

            for label, ep_start, ep_end, color in EPISODES:
                mask = (dates >= ep_start) & (dates <= ep_end)
                if mask.any():
                    ax.axvspan(dates[mask][0], dates[mask][-1],
                               alpha=0.25, color=color, label=label)

            ax.set_title(f"{MARKETS[market]['country']} CCI", fontsize=9)
            ax.set_ylabel("CCI", fontsize=7)
            ax.tick_params(labelsize=7)
        except Exception as e:
            ax.set_title(f"{market} â€” error")

    # Hide unused subplots
    for ax in axes[n:]:
        ax.set_visible(False)

    # Legend on first axis
    patches = [mpatches.Patch(color=c, alpha=0.4, label=l)
               for l, _, _, c in EPISODES]
    axes[0].legend(handles=patches, fontsize=7, loc="lower left")

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, "cci_overview.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"\nStep 3: plot saved -> {path}")


# ---------------------------------------------------------------------------
# Step 4 â€” Validation: US MCSI
# ---------------------------------------------------------------------------

def validate_us_mcsi():
    """
    Run S&P500 + MCSI estimation and episode overlap.
    Known answer: BOTH TAILS (dot-com explosive, 2008 mean-reverting).
    Confirms the battery is working before deploying to new markets.
    """
    print(f"\n{'='*70}")
    print("STEP 4 â€” Validation: S&P500 + MCSI (known answer)")
    print(f"{'='*70}")

    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel["eq_sp500"].dropna()
    mcsi   = panel["mcsi"].dropna()

    df = pd.DataFrame({"price": prices, "mcsi": mcsi}).dropna()
    df = df.loc[START:END]

    y = np.log(df["price"].values).astype(float)
    z = df["mcsi"].values.astype(float)

    opt = find_optimal_thresholds(y, z, z_min=57, z_max=110,
                                  gridlength=100, min_gap=4, spec=1, mode="returns")
    res = standard_errors(y, z, opt["c1"], opt["c2"], spec=1, mode="returns")

    print(f"  c1={opt['c1']:.1f}  c2={opt['c2']:.1f}  "
          f"n_mr={res['n1']} ({100*res['n1']/len(y):.0f}%)  "
          f"n_rw={res['n2']} ({100*res['n2']/len(y):.0f}%)  "
          f"n_exp={res['n3']} ({100*res['n3']/len(y):.0f}%)")

    print("  ", end="")
    verdict = _episode_verdict(y, z, opt["c1"], opt["c2"], df.index)
    print(f"\n  Verdict: {verdict}")
    if verdict == "BOTH TAILS":
        print("  Validation PASSED - proceed to Step 5.")
    else:
        print("  WARNING: expected BOTH TAILS. Check data or estimation.")


# ---------------------------------------------------------------------------
# Step 5 â€” CCI estimation for admissible markets
# ---------------------------------------------------------------------------

def _episode_verdict(y, z, c1, c2, dates, min_months=2, verbose=True):
    """
    Classify regime presence during key episodes.

    Checks whether each tail state has meaningful presence (>= min_months)
    during the relevant episode â€” not whether it dominated.
    With thresholds as extreme as c2~107, EXP will never dominate monthly data;
    what matters is whether it clustered in the euphoria window.
    """
    state = _assign_states(z[1:], c1, c2)   # 0=RW, 1=MR, 2=EXP
    regime_df = pd.DataFrame({
        "state": state,
        "regime": [["RW", "MR", "EXP"][s] for s in state],
    }, index=dates[1:])

    def count_regime(regime, start, end):
        ep = regime_df.loc[start:end]
        return (ep["regime"] == regime).sum()

    has_exp = count_regime("EXP", "1997-01", "2001-12") >= min_months
    has_mr  = count_regime("MR",  "2007-07", "2009-12") >= min_months

    exp_n = count_regime("EXP", "1997-01", "2001-12")
    mr_n  = count_regime("MR",  "2007-07", "2009-12")
    if verbose:
        print(f"    dot-com EXP months: {exp_n}  |  GFC MR months: {mr_n}", end="  ")

    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


def run_cci_estimation(market, oecd_code, z_min, z_max,
                       start=START, end=END, spec=1):
    """TAR estimation + episode overlap for one (market, CCI) pair."""
    y, z, dates = load_cci_pair(market, oecd_code, start, end)
    T = len(y)

    # min_gap enforces a minimum absolute band of 2 CCI points.
    # CCI range is ~6 points wide; without this, the search collapses to a
    # near-zero efficient band (degenerate result, same as FTSE no-drift issue).
    gridlength = 100
    grid_step  = (z_max - z_min) / (gridlength - 1)
    min_gap    = max(4, int(2.0 / grid_step))

    opt = find_optimal_thresholds(y, z, z_min=z_min, z_max=z_max,
                                  gridlength=gridlength, min_gap=min_gap,
                                  spec=spec, mode="returns")
    res = standard_errors(y, z, opt["c1"], opt["c2"], spec=spec, mode="returns")
    verdict = _episode_verdict(y, z, opt["c1"], opt["c2"], dates)

    return {
        "market":  market,
        "country": MARKETS[market]["country"],
        "T":       T,
        "c1":      opt["c1"], "c2": opt["c2"],
        "beta_mr": res["beta1"], "se_mr": res["se1"],
        "beta_rw": res["beta2"],
        "beta_ex": res["beta3"], "se_ex": res["se3"],
        "n_mr":    res["n1"], "n_rw": res["n2"], "n_ex": res["n3"],
        "verdict": verdict,
    }


def run_estimation_all(admissible, spec=1):
    """Run estimation for all admissible markets and print summary table."""
    print(f"\n{'='*70}")
    print("STEP 5 â€” CCI estimation for admissible markets")
    print(f"{'='*70}")

    bounds = _load_grid_bounds()
    rows   = []

    for market in admissible:
        code = OECD_CCI_MARKETS[market]
        if market not in bounds:
            print(f"  {market}: no grid bounds in coverage CSV â€” skipping")
            continue
        z_min = bounds[market]["z_min"]
        z_max = bounds[market]["z_max"]
        print(f"  {market:<14} grid=[{z_min:.1f},{z_max:.1f}]  ", end="", flush=True)
        try:
            r = run_cci_estimation(market, code, z_min, z_max)
            rows.append(r)
            print(f"c1={r['c1']:.1f} c2={r['c2']:.1f}  {r['verdict']}")
        except Exception as e:
            print(f"ERROR: {e}")

    if not rows:
        return

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1':>6} {'c2':>6}  "
          f"{'beta_mr':>8} {'beta_ex':>8}  {'n_mr%':>6} {'n_rw%':>6} {'n_ex%':>6}  Verdict")
    print("-" * 100)
    for r in rows:
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>6.1f} {r['c2']:>6.1f}  "
              f"{r['beta_mr']:>8.4f} {r['beta_ex']:>8.4f}  "
              f"{100*r['n_mr']/T:>5.1f}% {100*r['n_rw']/T:>5.1f}% {100*r['n_ex']/T:>5.1f}%  "
              f"{r['verdict']}")


# ---------------------------------------------------------------------------
# VIX vs CCI comparison table
# ---------------------------------------------------------------------------

def compare_vix_cci(admissible):
    """
    Run VIX (daily) and CCI (monthly) estimation for each admissible market
    and print results side by side.
    """
    bounds = _load_grid_bounds()

    print(f"\n{'='*108}")
    print("VIX vs CCI COMPARISON TABLE")
    print(f"{'='*108}")
    print(f"{'Market':<14} {'Country':<14} | "
          f"{'--- VIX (daily, spec=1) ---':^36} | "
          f"{'--- CCI (monthly, spec=1) ---':^36} | Agreement")
    print(f"{'':14} {'':14} | "
          f"{'c1':>5} {'c2':>5} {'eff%':>6} {'verdict':<17}| "
          f"{'c1':>5} {'c2':>5} {'eff%':>6} {'verdict':<17}|")
    print("-" * 108)

    for market in admissible:
        country = MARKETS[market]["country"]
        eq_col  = f"eq_{market}"

        # VIX estimation (daily, trigger_lag=1)
        vix_str  = f"{'ERROR':^36}"
        verdict_v = "ERR"
        opt_v     = {'c1': 0, 'c2': 0}
        eff_v     = None
        try:
            y_v, z_v = load_pair(DAILY_PANEL_PATH, eq_col, "vix",
                                  START, END, trigger_lag=1)
            opt_v = find_optimal_thresholds(y_v, z_v, 10, 70, 200, 6,
                                             spec=1, mode='returns')
            res_v = standard_errors(y_v, z_v, opt_v['c1'], opt_v['c2'],
                                     spec=1, mode='returns')
            eff_v = 100 * res_v['n2'] / len(y_v)

            # Reconstruct dates for episode verdict
            panel_d = pd.read_csv(DAILY_PANEL_PATH, index_col="date", parse_dates=True)
            dates_v = panel_d[[eq_col, "vix"]].dropna().loc[START:END].index[1:]
            verdict_v = _episode_verdict(y_v, z_v, opt_v['c1'], opt_v['c2'],
                                         dates_v[:len(y_v)], verbose=False)
            vix_str = (f"{opt_v['c1']:>5.1f} {opt_v['c2']:>5.1f} "
                       f"{eff_v:>5.1f}% {verdict_v:<17}")
        except Exception as e:
            vix_str = f"{'ERROR: ' + str(e)[:28]:<36}"

        # CCI estimation (monthly, trigger_lag=0)
        cci_str   = f"{'ERROR':^36}"
        verdict_c = "ERR"
        eff_c     = None
        if market in bounds:
            try:
                code  = OECD_CCI_MARKETS[market]
                r_cci = run_cci_estimation(market, code,
                                           bounds[market]['z_min'],
                                           bounds[market]['z_max'])
                eff_c     = 100 * r_cci['n_rw'] / r_cci['T']
                verdict_c = r_cci['verdict']
                cci_str   = (f"{r_cci['c1']:>5.1f} {r_cci['c2']:>5.1f} "
                             f"{eff_c:>5.1f}% {verdict_c:<17}")
            except Exception as e:
                cci_str = f"{'ERROR: ' + str(e)[:28]:<36}"

        agree = ""
        if eff_v is not None and eff_c is not None:
            agree = "AGREE" if verdict_v == verdict_c else "DIFFER"

        print(f"{market:<14} {country:<14} | {vix_str}| {cci_str}| {agree}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all():
    admissible = exogeneity_screen()
    plot_cci_episodes()
    validate_us_mcsi()
    run_estimation_all(admissible)
    compare_vix_cci(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "screen":
        exogeneity_screen()
    elif cmd == "plot":
        plot_cci_episodes()
    elif cmd == "validate":
        validate_us_mcsi()
    elif cmd == "estimate":
        admissible = exogeneity_screen()
        run_estimation_all(admissible)
    elif cmd == "compare":
        admissible = exogeneity_screen()
        compare_vix_cci(admissible)
    else:
        run_all()

