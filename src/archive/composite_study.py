"""
Composite trigger: orthogonalised PCA of global CCI, VIX (monthly mean),
and BAA spread (monthly mean).

For each market separately:
  1. Resample VIX and BAA to monthly mean; align with global CCI monthly.
  2. Regress each component on 6 lags of that market's equity returns (OLS).
  3. Take residuals; z-score each set of three residuals.
  4. PCA across the three z-scored residuals -> PC1 is the composite trigger.

This removes each market's own equity feedback before combining, so markets
that fail the reverse Granger test with raw global CCI (e.g. S&P 500,
FTSE 100) should pass once the composite is orthogonalised.

Pipeline:
  1  components  - assemble & inspect monthly CCI, VIX, BAA
  2  individual  - baseline reverse Granger on each raw component (23 x 3)
  3  composite   - orthogonalise + PCA for every market, inspect loadings
  4  screen      - reverse Granger on composite (Step 6 in spec)
  5  rolling     - rolling 10-yr threshold stability (S&P 500)
  6  validate    - both-tails episode check for admissible markets
  7  estimate    - cross-market TAR estimation (Step 9)
  8  compare     - composite vs CCI-alone headline table (Step 10)

Usage:
    cd src && python composite_study.py              # full pipeline
    python composite_study.py components
    python composite_study.py individual
    python composite_study.py composite
    python composite_study.py screen
    python composite_study.py rolling
    python composite_study.py validate
    python composite_study.py estimate
    python composite_study.py compare
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from estimate           import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity         import granger_f_test
from market_config      import MARKETS
from replicate          import PANEL_PATH
from bubble_now         import FIGURES_DIR, TABLES_DIR, FULL_END, INSAMPLE_END
from rolling_thresholds import rolling_windows, WINDOW_MONTHS, STEP_MONTHS

SENTIMENT_DIR      = os.path.join(os.path.dirname(__file__), "..", "data", "sentiment")
GLOBAL_CCI_PATH    = os.path.join(SENTIMENT_DIR, "global_cci_monthly.csv")
VIX_DAILY_PATH     = os.path.join(SENTIMENT_DIR, "vix_daily.csv")
BAA_DAILY_PATH     = os.path.join(SENTIMENT_DIR, "baa_spread_daily.csv")
GLOBAL_CCI_RESULTS = os.path.join(os.path.dirname(__file__), "..", "results", "tables",
                                   "global_cci_all_markets.csv")
BCI_PATH           = os.path.join(SENTIMENT_DIR, "bci_monthly.csv")
ANFCI_PATH         = os.path.join(SENTIMENT_DIR, "anfci_monthly.csv")
YC_DAILY_PATH      = os.path.join(SENTIMENT_DIR, "yield_curve_monthly.csv")  # daily despite name
EPU_PATH           = os.path.join(SENTIMENT_DIR, "epu_monthly.csv")

START  = "1990-01"
N_ORTH = 6   # lags of equity returns used in orthogonalisation

EPISODES = [
    ("Dot-com",   "1997-01", "2001-12"),
    ("GFC",       "2007-07", "2009-12"),
    ("COVID",     "2020-03", "2020-06"),
    ("2022 hike", "2022-01", "2023-06"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_monthly_components(start=START, end=FULL_END):
    """
    Assemble six monthly indicators on common month-end dates:
        global_cci, vix_monthly, bci_monthly,
        anfci_monthly, yield_curve_monthly, epu_monthly
    VIX (Feb-1990) is the binding start constraint.
    EPU (~Apr-2026) is the binding end constraint.
    BAA spread excluded (0/23 exogeneity).
    Raw values stored; sign conventions applied at composite-construction time via PCA.
    """
    cci_raw = pd.read_csv(GLOBAL_CCI_PATH, index_col="date", parse_dates=True)
    cci = cci_raw["global_cci"].dropna()
    cci.index = cci.index + pd.offsets.MonthEnd(0)

    vix_raw = pd.read_csv(VIX_DAILY_PATH, index_col="date", parse_dates=True)
    vix_m = vix_raw["vix"].dropna().resample("ME").mean().dropna()

    bci_raw = pd.read_csv(BCI_PATH, index_col="date", parse_dates=True)
    bci = bci_raw["bci"].dropna()
    bci.index = bci.index + pd.offsets.MonthEnd(0)

    anfci_raw = pd.read_csv(ANFCI_PATH, index_col="date", parse_dates=True)
    anfci = anfci_raw["anfci"].dropna()
    anfci.index = anfci.index + pd.offsets.MonthEnd(0)

    yc_raw = pd.read_csv(YC_DAILY_PATH, index_col="date", parse_dates=True)
    yc_m = yc_raw["yield_curve"].dropna().resample("ME").mean().dropna()

    epu_raw = pd.read_csv(EPU_PATH, index_col="date", parse_dates=True)
    epu = epu_raw["epu"].dropna()
    epu.index = epu.index + pd.offsets.MonthEnd(0)

    df = pd.DataFrame({
        "global_cci": cci, "vix_monthly": vix_m, "bci_monthly": bci,
        "anfci_monthly": anfci, "yield_curve_monthly": yc_m, "epu_monthly": epu,
    })
    df = df.dropna().sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df.loc[start:end]


def _load_equity_monthly(market):
    """Load monthly log-prices for one market from monthly_panel.csv."""
    panel = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    col   = f"eq_{market}"
    if col not in panel.columns:
        raise KeyError(f"{col} not in monthly panel")
    prices = panel[col].dropna()
    prices.index = prices.index + pd.offsets.MonthEnd(0)
    return prices


# ---------------------------------------------------------------------------
# Composite construction (Steps 3-5)
# ---------------------------------------------------------------------------

def _pca_first_component(X):
    """
    First principal component via eigendecomposition of the 3x3 covariance matrix.
    X: (T, 3) matrix of z-scored residuals.
    Returns (scores, loadings, var_explained).
    No external dependencies -- uses numpy only.
    """
    Xc = X - X.mean(axis=0)
    cov = np.cov(Xc.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx          = np.argsort(eigenvalues)[::-1]
    eigenvalues  = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    loadings     = eigenvectors[:, 0]
    scores       = Xc @ loadings
    var_explained = float(eigenvalues[0] / eigenvalues.sum())
    return scores, loadings, var_explained


def make_composite(market, start=START, end=FULL_END, n_orth=N_ORTH):
    """
    Build the market-specific composite trigger.

    Steps:
      3. Align equity prices with (CCI, VIX_m, BAA_m); compute log-returns.
         For each component regress on n_orth lags of log-returns (OLS);
         take residuals.
      4. Z-score each set of residuals.
      5. PCA across the three z-scored columns -> PC1.

    Sign convention: if CCI loading on PC1 is negative, flip the sign of
    the composite so that high composite <-> high CCI <-> bubble risk (EXP).

    Returns
    -------
    composite_z   : np.ndarray (T - n_orth,) -- the composite trigger series
    log_prices    : np.ndarray (T - n_orth,) -- log equity prices, same dates
    dates         : np.ndarray[datetime64] (T - n_orth,)
    loadings      : np.ndarray (3,) -- [CCI, VIX, BAA] loadings (post sign-flip)
    var_explained : float -- variance fraction captured by PC1
    """
    comps  = load_monthly_components(start, end)
    prices = _load_equity_monthly(market)

    df = pd.DataFrame({"price": prices}).join(comps, how="inner").dropna().sort_index()
    T  = len(df)
    if T < n_orth + 30:
        raise ValueError(f"{market}: {T} aligned obs < minimum {n_orth + 30}")

    log_p = np.log(df["price"].values)
    ret   = np.diff(log_p)          # length T-1; ret[i] = log(p[i+1]/p[i])
    n_valid = T - n_orth

    # Lag matrix: row i corresponds to component at t = i + n_orth.
    # Column k (0-indexed) = lag k+1 = ret[i + n_orth - k - 1].
    L = np.column_stack([ret[n_orth - 1 - k : T - 1 - k] for k in range(n_orth)])
    X_design = np.hstack([np.ones((n_valid, 1)), L])   # (n_valid, 1 + n_orth)

    # CCI(+) VIX(-) BCI(+) -- BAA excluded (always endogenous: 0/23 pass)
    cols_order = ["global_cci", "vix_monthly", "bci_monthly"]
    z_residuals = []
    for col in cols_order:
        target = df[col].values[n_orth:]                   # length n_valid
        b, _, _, _ = np.linalg.lstsq(X_design, target, rcond=None)
        resid  = target - X_design @ b
        z_res  = (resid - resid.mean()) / resid.std(ddof=1)
        z_residuals.append(z_res)

    Z = np.column_stack(z_residuals)                       # (n_valid, 3)
    scores, loadings, var_exp = _pca_first_component(Z)

    # Ensure high composite <-> high CCI <-> EXP (bubble risk)
    if loadings[0] < 0:
        scores   = -scores
        loadings = -loadings

    dates      = np.array(df.index[n_orth:], dtype="datetime64[ns]")
    log_prices = log_p[n_orth:]

    return scores, log_prices, dates, loadings, var_exp


def _load_composite_pair(market, start=START, end=FULL_END, n_orth=N_ORTH):
    """Return (y, z, dates) ready for find_optimal_thresholds()."""
    z, y, dates, _, _ = make_composite(market, start, end, n_orth)
    return y, z, dates


def _grid_bounds(z):
    """
    Adaptive mu +/- 3sigma grid for the composite (PC1 scores ~= N(0, ~1)).
    Mirrors global_cci_study._grid_bounds().
    """
    mu, sigma = float(z.mean()), float(z.std())
    z_min = round(mu - 3.0 * sigma, 4)
    z_max = round(mu + 3.0 * sigma, 4)
    gridlen   = 100
    grid_step = (z_max - z_min) / (gridlen - 1)
    min_gap   = max(4, int(0.5 / grid_step))
    return z_min, z_max, gridlen, min_gap


# ---------------------------------------------------------------------------
# Stage 1 -- Inspect components
# ---------------------------------------------------------------------------

def inspect_components():
    """Step 1: print stats and coverage for the three monthly components."""
    comps = load_monthly_components()
    print(f"\n{'='*65}")
    print("STAGE 1 -- Component assembly & inspection")
    print(f"{'='*65}")
    print(f"  Date range : {comps.index[0].strftime('%Y-%m')} to "
          f"{comps.index[-1].strftime('%Y-%m')}   ({len(comps)} months)")
    for col in comps.columns:
        s = comps[col]
        print(f"  {col:<16}  mean={s.mean():8.3f}  std={s.std():7.3f}  "
              f"min={s.min():8.3f}  max={s.max():8.3f}")
    print()


# ---------------------------------------------------------------------------
# Stage 2 -- Individual component exogeneity (Step 2 baseline)
# ---------------------------------------------------------------------------

def individual_exogeneity(n_lags=4, alpha=0.05):
    """
    Step 2: reverse Granger test for each raw component against equity returns.

    Test direction: does equity_return Granger-cause D(component)?
    PASS (p > alpha): component is NOT predicted by returns -> exogenous (ok)
    FAIL (p <= alpha): returns predict component -> endogenous (x)

    Provides the baseline pass-rate for CCI, VIX_m, BAA_m individually.
    """
    print(f"\n{'='*72}")
    print("STAGE 2 -- Individual component exogeneity (reverse Granger, baseline)")
    print(f"  H0: equity_return does NOT Granger-cause D(component)")
    print(f"  PASS = fail to reject H0 = component exogenous")
    print(f"{'='*72}")

    comps  = load_monthly_components()
    cols   = ["global_cci", "vix_monthly", "bci_monthly"]
    labels = ["CCI", "VIX_m", "BCI_m"]

    header = f"{'Market':<14} {'Country':<16}" + "".join(f"  {l:<12}" for l in labels)
    print(header)
    print("-" * (14 + 18 + len(labels) * 14))

    counts = {l: 0 for l in labels}
    totals = {l: 0 for l in labels}
    rows   = []

    for market, info in MARKETS.items():
        row_data = {"market": market, "country": info["country"]}
        try:
            prices = _load_equity_monthly(market)
            df     = pd.DataFrame({"price": prices}).join(comps, how="inner").dropna()
            y_ret  = np.diff(np.log(df["price"].values))
            line   = f"{market:<14} {info['country']:<16}"
            for col, lbl in zip(cols, labels):
                z_diff = np.diff(df[col].values)
                n      = min(len(y_ret), len(z_diff))
                if n < n_lags + 5:
                    line += f"  {'SHORT':<12}"
                    row_data[lbl] = "SHORT"
                    continue
                F, p   = granger_f_test(z_diff[-n:], y_ret[-n:], n_lags)
                verdict = "PASS" if p > alpha else "FAIL"
                if verdict == "PASS":
                    counts[lbl] += 1
                totals[lbl] += 1
                row_data[lbl]          = verdict
                row_data[f"{lbl}_F"]   = round(float(F), 3)
                row_data[f"{lbl}_p"]   = round(float(p), 4)
                line += f"  {verdict:<12}"
            print(line)
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")
            row_data["error"] = str(e)
        rows.append(row_data)

    print()
    print(f"{'Component':<10}  {'Pass':>5}  {'Total':>6}  {'Rate':>7}")
    print("-" * 30)
    for lbl in labels:
        t = totals[lbl]
        c = counts[lbl]
        print(f"{lbl:<10}  {c:>5}  {t:>6}  {100*c/t:>6.0f}%" if t else f"{lbl:<10}  N/A")

    os.makedirs(TABLES_DIR, exist_ok=True)
    out = os.path.join(TABLES_DIR, "composite_individual_exogeneity.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved: {out}")
    return rows


# ---------------------------------------------------------------------------
# Stage 3 -- Build composites for all markets (Steps 3-5)
# ---------------------------------------------------------------------------

def build_all_composites(n_orth=N_ORTH):
    """
    Steps 3-5: orthogonalise + PCA for every market (CCI + VIX + BCI).
    Expected loadings: CCI (+), VIX (-), BCI (+).
    """
    print(f"\n{'='*72}")
    print(f"STAGES 3-5 -- Market-specific composite (CCI + VIX + BCI, n_orth={n_orth})")
    print(f"  Expected loadings: CCI(+) VIX(-) BCI(+)")
    print(f"{'='*72}")
    print(f"{'Market':<14} {'T':>5}  {'VarExp':>7}  {'L_CCI':>7}  {'L_VIX':>7}  {'L_BCI':>7}  Note")
    print("-" * 65)

    results = {}
    for market in MARKETS:
        try:
            z, _, dates, loadings, var_exp = make_composite(market, n_orth=n_orth)
            note = ""
            if loadings[1] > 0 or loadings[2] < 0:   # VIX- and BCI+ expected
                note = "?sign"
            results[market] = {
                "T": len(z), "var_exp": var_exp,
                "load_cci": loadings[0],
                "load_vix": loadings[1],
                "load_bci": loadings[2],
            }
            print(f"{market:<14} {len(z):>5}  {var_exp:>6.1%}  "
                  f"{loadings[0]:>+7.3f}  {loadings[1]:>+7.3f}  {loadings[2]:>+7.3f}  {note}")
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    print()
    return results


# ---------------------------------------------------------------------------
# Stage 4 -- Composite exogeneity gate (Step 6)
# ---------------------------------------------------------------------------

def composite_exogeneity(n_lags=4, alpha=0.05):
    """
    Step 6: reverse Granger test on composite PC1 for all 23 markets.
    The composite is market-specific (orthogonalised per-market above).

    Key check: S&P 500 and FTSE 100 should now PASS even though raw CCI fails.
    """
    print(f"\n{'='*65}")
    print("STAGE 4 (Step 6) -- Composite exogeneity gate (reverse Granger)")
    print(f"  H0: equity_return does NOT Granger-cause D(composite)")
    print(f"{'='*65}")
    print(f"{'Market':<14} {'Country':<18} {'F':>7}  {'p':>7}  Gate")
    print("-" * 55)

    admissible = []
    rows       = []

    for market, info in MARKETS.items():
        try:
            y, z, dates = _load_composite_pair(market)
            y_ret  = np.diff(y)
            z_diff = np.diff(z)
            n      = min(len(y_ret), len(z_diff))
            F, p   = granger_f_test(z_diff[-n:], y_ret[-n:], n_lags)
            verdict = "PASS" if p > alpha else "FAIL"
            if verdict == "PASS":
                admissible.append(market)
            print(f"{market:<14} {info['country']:<18} {F:>7.3f}  {p:>7.4f}  {verdict}")
            rows.append({"market": market, "country": info["country"],
                         "F": round(F, 3), "p": round(p, 4), "gate": verdict})
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")
            rows.append({"market": market, "gate": "ERROR", "error": str(e)})

    print(f"\n{len(admissible)} of {len(MARKETS)} markets admissible.")
    os.makedirs(TABLES_DIR, exist_ok=True)
    out = os.path.join(TABLES_DIR, "composite_exogeneity.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved: {out}")
    return admissible


# ---------------------------------------------------------------------------
# Stage 5 -- Rolling threshold stability (Step 7)
# ---------------------------------------------------------------------------

def rolling_composite_stability(market="sp500"):
    """
    Step 7: roll 10-year TAR windows over the composite trigger.
    Composite is fixed (full-sample orthogonalisation + PCA); only the
    TAR gridsearch rolls, matching the approach in global_cci_study.py.
    """
    print(f"\n{'='*65}")
    print(f"STAGE 5 (Step 7) -- Rolling stability: {market.upper()} + composite")
    print(f"{'='*65}")

    y, z, dates = _load_composite_pair(market)
    z_min, z_max, gl, mg = _grid_bounds(z)

    y_in, z_in, _ = _load_composite_pair(market, end=INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")
    print(f"  In-sample ref: c1={ref['c1']:.4f}  c2={ref['c2']:.4f}")
    print(f"  Rolling {WINDOW_MONTHS//12}-yr windows ...", end="", flush=True)

    rows_w = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1)
    print(f" {len(rows_w)} windows")

    df_roll = pd.DataFrame(rows_w, columns=["window_end", "c1", "c2"])
    df_roll["window_end"] = pd.DatetimeIndex(df_roll["window_end"]).strftime("%Y-%m")
    df_roll = df_roll.round({"c1": 4, "c2": 4})

    print(f"  c1 range: [{df_roll['c1'].min():.4f}, {df_roll['c1'].max():.4f}]  "
          f"mean={df_roll['c1'].mean():.4f}  ref={ref['c1']:.4f}")
    print(f"  c2 range: [{df_roll['c2'].min():.4f}, {df_roll['c2'].max():.4f}]  "
          f"mean={df_roll['c2'].mean():.4f}  ref={ref['c2']:.4f}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, f"rolling_thresholds_{market.upper()}_COMPOSITE.csv")
    df_roll.to_csv(csv_path, index=False)

    os.makedirs(FIGURES_DIR, exist_ok=True)
    dates_arr = np.array([r[0] for r in rows_w], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows_w])
    c2_arr    = np.array([r[2] for r in rows_w])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates_arr, c1_arr, color="cornflowerblue", linewidth=1.8, label="c1 (rolling)")
    ax.plot(dates_arr, c2_arr, color="tomato",         linewidth=1.8, label="c2 (rolling)")
    ax.axhline(ref["c1"], color="cornflowerblue", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c1 in-sample ({ref['c1']:.4f})")
    ax.axhline(ref["c2"], color="tomato", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c2 in-sample ({ref['c2']:.4f})")
    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7, label="2015-06 paper cutoff")
    ax.set_title(f"{market.upper()} + composite -- rolling {WINDOW_MONTHS//12}-yr TAR thresholds",
                 fontsize=9)
    ax.set_xlabel("Window end date", fontsize=8)
    ax.set_ylabel("Composite threshold", fontsize=8)
    ax.legend(fontsize=7, ncol=2)
    ax.tick_params(labelsize=7)
    ax.margins(x=0.01)
    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, f"rolling_thresholds_{market.upper()}_COMPOSITE.png")
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"  Saved: {csv_path}")
    print(f"  Saved: {fig_path}")


# ---------------------------------------------------------------------------
# Episode verdict helper (Step 8)
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """
    Check dot-com (EXP) and GFC (MR) episode coverage.
    Matches global_cci_study._episode_verdict().
    """
    regime_df = pd.DataFrame(
        {"regime": [["RW", "MR", "EXP"][s] for s in state]},
        index=pd.DatetimeIndex(dates),
    )

    def n_r(r, s, e):
        return (regime_df.loc[s:e]["regime"] == r).sum()

    dotcom_exp = n_r("EXP", "1997-01", "2001-12")
    gfc_mr     = n_r("MR",  "2007-07", "2009-12")
    covid_mr   = n_r("MR",  "2020-01", "2020-06")
    hike22_mr  = n_r("MR",  "2022-01", "2023-06")
    recent_exp = n_r("EXP", "2021-01", "2026-06")

    if verbose:
        print(f"    dot-com EXP:{dotcom_exp:2d}  GFC MR:{gfc_mr:2d}  "
              f"COVID MR:{covid_mr:2d}  2022 MR:{hike22_mr:2d}  "
              f"recent EXP:{recent_exp}", end="  ")

    has_exp = dotcom_exp >= min_months
    has_mr  = gfc_mr     >= min_months
    if has_exp and has_mr:      return "BOTH TAILS"
    if has_mr  and not has_exp: return "FEAR GAUGE"
    if has_exp and not has_mr:  return "EUPHORIA GAUGE"
    return "WEAK"


# ---------------------------------------------------------------------------
# Stage 6 -- Both-tails validation (Step 8)
# ---------------------------------------------------------------------------

def both_tails_validation(admissible=None):
    """
    Step 8: dot-com -> EXP and GFC -> MR for admissible markets.
    Economic validity check before reporting the full cross-market table.
    """
    print(f"\n{'='*65}")
    print("STAGE 6 (Step 8) -- Both-tails validation")
    print(f"{'='*65}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    for market in markets:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) ...", end="", flush=True)
        try:
            y, z, dates = _load_composite_pair(market)
            z_min, z_max, gl, mg = _grid_bounds(z)
            opt    = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns",
                                               min_pct=0.05)
            if opt is None:
                print("  -> NO SIGNAL")
                continue
            state  = _assign_states(z[1:], opt["c1"], opt["c2"])
            verdict = _episode_verdict(state, dates[1:])
            print(f"  -> {verdict}")
        except Exception as e:
            print(f" ERROR: {e}")


# ---------------------------------------------------------------------------
# Stage 7 -- Cross-market estimation (Step 9)
# ---------------------------------------------------------------------------

def _estimate_one(market, start=START, end=FULL_END, spec=1, verbose=True):
    """TAR estimation for one market with the composite trigger."""
    try:
        y, z, dates = _load_composite_pair(market, start, end)
    except Exception:
        return None
    if len(y) < 120:
        return None

    z_min, z_max, gl, mg = _grid_bounds(z)
    opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, spec, "returns",
                                  min_pct=0.05)
    if opt is None:
        return {
            "market":  market,
            "country": MARKETS[market]["country"],
            "T":       len(y) - 1,
            "c1": np.nan, "c2": np.nan,
            "beta_mr": np.nan, "beta_ex": np.nan,
            "n_mr": 0, "n_rw": 0, "n_ex": 0,
            "verdict": "NO SIGNAL",
        }
    c1, c2 = opt["c1"], opt["c2"]
    res    = standard_errors(y, z, c1, c2, spec, "returns")
    state  = _assign_states(z[1:], c1, c2)
    T      = len(state)
    verdict = _episode_verdict(state, dates[1:], verbose=verbose)

    return {
        "market":  market,
        "country": MARKETS[market]["country"],
        "T":       T,
        "c1": c1, "c2": c2,
        "beta_mr": res["beta1"],
        "beta_ex": res["beta3"],
        "n_mr":    res["n1"],
        "n_rw":    res["n2"],
        "n_ex":    res["n3"],
        "verdict": verdict,
    }


def run_all_markets(admissible=None):
    """Step 9: cross-market TAR estimation with the composite trigger, spec=1."""
    print(f"\n{'='*72}")
    print("STAGE 7 (Step 9) -- Cross-market TAR estimation (composite, spec=1)")
    print(f"{'='*72}")

    markets = admissible if admissible is not None else list(MARKETS.keys())
    rows    = []

    for market in markets:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) ...", end="", flush=True)
        r = _estimate_one(market)
        if r is None:
            print(" SKIP (< 120 obs or error)")
            continue
        rows.append(r)
        if r["verdict"] == "NO SIGNAL":
            print("  NO SIGNAL (5% min-occupancy constraint not satisfiable)")
            continue
        T = r["T"]
        print(f"  c1={r['c1']:.3f}  c2={r['c2']:.3f}  "
              f"MR={100*r['n_mr']/T:.0f}%  RW={100*r['n_rw']/T:.0f}%  "
              f"EXP={100*r['n_ex']/T:.0f}%  b3={r['beta_ex']:.4f}  {r['verdict']}")

    if not rows:
        print("  No results.")
        return []

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1':>7} {'c2':>7}  "
          f"{'MR%':>5} {'RW%':>5} {'EXP%':>5}  {'b3':>8}  Verdict")
    print("-" * 95)
    for r in rows:
        if r["verdict"] == "NO SIGNAL":
            print(f"{r['market']:<14} {r['country']:<16} {r['T']:>5}  "
                  f"{'--':>7} {'--':>7}  {'--':>4}  {'--':>4}  {'--':>4}  "
                  f"{'--':>8}  NO SIGNAL")
            continue
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>7.3f} {r['c2']:>7.3f}  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% {100*r['n_ex']/T:>4.0f}%  "
              f"{r['beta_ex']:>8.4f}  {r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, "composite_all_markets.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    return rows


# ---------------------------------------------------------------------------
# Stage 8 -- Comparison table (Step 10)
# ---------------------------------------------------------------------------

def compare_cci_vs_composite(admissible=None):
    """Step 10: headline comparison of composite trigger vs CCI-alone."""
    print(f"\n{'='*72}")
    print("STAGE 8 (Step 10) -- Composite vs CCI-alone comparison")
    print(f"{'='*72}")

    if os.path.exists(GLOBAL_CCI_RESULTS):
        cci_df = pd.read_csv(GLOBAL_CCI_RESULTS).set_index("market")
    else:
        print(f"  WARNING: {GLOBAL_CCI_RESULTS} not found. "
              "Run global_cci_study.py first.")
        cci_df = pd.DataFrame()

    markets = admissible if admissible is not None else list(MARKETS.keys())
    rows    = []

    print(f"\n{'Market':<14} {'Country':<16} "
          f"{'CCI ineff%':>11} {'Comp ineff%':>12} "
          f"{'b3 CCI':>9} {'b3 Comp':>9}  CCI-verdict  Comp-verdict")
    print("-" * 95)

    for market in markets:
        r_comp = _estimate_one(market, verbose=False)
        if r_comp is None:
            continue
        if r_comp["verdict"] == "NO SIGNAL":
            if market in cci_df.index:
                rc = cci_df.loc[market]
                v_cci  = str(rc.get("verdict", "--"))
                b3_cci = float(rc["beta_ex"])
            else:
                v_cci, b3_cci = "--", float("nan")
            print(f"{market:<14} {r_comp['country']:<16} "
                  f"{'--':>10}  {'NO SIGNAL':>11}  "
                  f"{b3_cci:>9.4f} {'--':>9}  {v_cci:<12}  NO SIGNAL")
            rows.append({
                "market": market, "country": r_comp["country"],
                "cci_inefficient": float("nan"), "comp_inefficient": float("nan"),
                "beta3_cci": b3_cci, "beta3_composite": float("nan"),
                "cci_verdict": v_cci, "comp_verdict": "NO SIGNAL",
            })
            continue

        T_comp     = r_comp["T"]
        ineff_comp = 100.0 * (r_comp["n_mr"] + r_comp["n_ex"]) / T_comp

        if market in cci_df.index:
            rc        = cci_df.loc[market]
            T_cci     = rc["T"]
            ineff_cci = 100.0 * (rc["n_mr"] + rc["n_ex"]) / T_cci
            b3_cci    = float(rc["beta_ex"])
            v_cci     = str(rc.get("verdict", "--"))
        else:
            ineff_cci = float("nan")
            b3_cci    = float("nan")
            v_cci     = "--"

        print(f"{market:<14} {r_comp['country']:<16} "
              f"{ineff_cci:>10.1f}% {ineff_comp:>11.1f}% "
              f"{b3_cci:>9.4f} {r_comp['beta_ex']:>9.4f}  "
              f"{v_cci:<12}  {r_comp['verdict']}")

        rows.append({
            "market":           market,
            "country":          r_comp["country"],
            "cci_inefficient":  round(ineff_cci, 1),
            "comp_inefficient": round(ineff_comp, 1),
            "beta3_cci":        round(b3_cci, 4),
            "beta3_composite":  round(r_comp["beta_ex"], 4),
            "cci_verdict":      v_cci,
            "comp_verdict":     r_comp["verdict"],
        })

    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, "composite_vs_cci_comparison.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    return rows


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all():
    inspect_components()
    individual_exogeneity()
    build_all_composites()
    admissible = composite_exogeneity()
    rolling_composite_stability("sp500")
    both_tails_validation(admissible)
    run_all_markets(admissible)
    compare_cci_vs_composite(admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    dispatch = {
        "components": inspect_components,
        "individual": individual_exogeneity,
        "composite":  build_all_composites,
        "screen":     composite_exogeneity,
        "rolling":    lambda: rolling_composite_stability("sp500"),
        "validate":   lambda: both_tails_validation(),
        "estimate":   lambda: run_all_markets(),
        "compare":    lambda: compare_cci_vs_composite(),
    }
    if cmd in dispatch:
        dispatch[cmd]()
    else:
        run_all()

