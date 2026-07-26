"""
BIC-driven composite trigger: data-selected orthogonalisation and Granger test lags.

Solves the circularity in the fixed-lag orthogonalised composite (N_ORTH=6):

  Fixed lag problem: N_ORTH=6 > n_lags=4 guarantees the Granger test passes
  by construction. The 23/23 result is tautological.

  Solution:
    1. BIC selects the orthogonalisation lag per (market, component) pair.
       Typically 1-4 for monthly data; VIX likely 1 (immediate response).
    2. BIC selects the Granger test lag per market via VAR order selection.
    3. Buffer rule: test_lag = max(granger_bic, max_orth + buffer).
       This ensures the test always examines lags the orthogonalisation did NOT remove.
    4. Robustness check across buffer values [2, 4, 6, 8].

Expected outcome: genuine exogeneity pass rate of 15-18/23, between the
tautological 23/23 (fixed lags) and the raw composite's 14/23.

Usage:
    cd src && python bic_composite_study.py          # full pipeline
    python bic_composite_study.py lags               # BIC lag selection table only
    python bic_composite_study.py screen             # exogeneity screen
    python bic_composite_study.py estimate           # TAR for admissible markets
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd

import statsmodels.api as sm
from statsmodels.tsa.vector_ar.var_model import VAR

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from composite_study  import (
    load_monthly_components, _pca_first_component, _grid_bounds, GLOBAL_CCI_RESULTS
)
from estimate         import find_optimal_thresholds, _assign_states, standard_errors
from exogeneity       import granger_f_test
from market_config    import MARKETS
from replicate        import PANEL_PATH
from bubble_now       import TABLES_DIR, FULL_END, INSAMPLE_END

START = "1990-01"
COMP_COLS = ["global_cci", "vix_monthly", "bci_monthly"]


# ---------------------------------------------------------------------------
# Step 1 -- BIC lag selection for orthogonalisation
# ---------------------------------------------------------------------------

def select_orth_lag(component, returns, max_lag=12):
    """
    Select the number of return lags to remove from a component via BIC.

    Fits OLS: component(t) = alpha + sum_{i=1}^{k} beta_i * return(t-i) + e
    for k = 1 .. max_lag.  Returns the k minimising BIC.

    Typically 1-3 for monthly data.  VIX usually k=1 (immediate equity response).
    """
    best_k, best_bic = 1, np.inf
    for k in range(1, max_lag + 1):
        lags = pd.concat(
            [returns.shift(i).rename(f"lag{i}") for i in range(1, k + 1)],
            axis=1,
        )
        data = pd.concat([component, lags], axis=1).dropna()
        if len(data) < max(30, k + 5):
            continue
        try:
            model = sm.OLS(data.iloc[:, 0],
                           sm.add_constant(data.iloc[:, 1:])).fit(disp=0)
            if model.bic < best_bic:
                best_bic = model.bic
                best_k   = k
        except Exception:
            continue
    return best_k


# ---------------------------------------------------------------------------
# Step 2 -- Orthogonalise one component
# ---------------------------------------------------------------------------

def orthogonalise(component, returns, n_lags):
    """
    Return OLS residuals of component regressed on n_lags of returns.
    Residuals are a pd.Series on the aligned date index.
    """
    lags = pd.concat(
        [returns.shift(i).rename(f"lag{i}") for i in range(1, n_lags + 1)],
        axis=1,
    )
    data = pd.concat([component, lags], axis=1).dropna()
    y = data.iloc[:, 0]
    X = sm.add_constant(data.iloc[:, 1:])
    try:
        model = sm.OLS(y, X).fit(disp=0)
        return pd.Series(model.resid, index=data.index, name=component.name)
    except Exception:
        # Fallback: return demeaned component if OLS fails
        return (component - component.mean()).rename(component.name)


# ---------------------------------------------------------------------------
# Step 3 -- Build BIC-orthogonalised composite for one market
# ---------------------------------------------------------------------------

_SIGN_WEIGHTS = {
    "global_cci": 1, "bci_monthly": 1, "yield_curve_monthly": 1,
    "vix_monthly": -1, "anfci_monthly": -1, "epu_monthly": -1,
}


def _apply_sign_convention(scores, loadings, comp_cols):
    """
    Flip PC1 sign so that high composite = high positive sentiment = EXP risk.

    Find the first component in comp_cols; if its canonical sign weight is +1,
    ensure its loading is positive; if -1 (fear indicator), ensure negative.
    This gives a consistent 'high composite = euphoria' interpretation regardless
    of which components are included.
    """
    col = comp_cols[0]
    w   = _SIGN_WEIGHTS.get(col, 1)
    if loadings[0] * w < 0:
        scores   = -scores
        loadings = -loadings
    return scores, loadings


def build_composite_for_market(market, comps_df, comp_cols=None, max_orth_lag=12):
    """
    Construct the market-specific BIC composite.

    For each component in comp_cols (default: CCI, VIX, BCI):
      - Select BIC orthogonalisation lag k_i against this market's equity returns.
      - Orthogonalise component against k_i return lags.
      - Z-score residuals.
    Stack and apply PCA (first principal component).

    Returns dict:
      composite_z  : pd.Series on aligned monthly dates
      log_prices   : pd.Series of log equity prices (same index, for TAR)
      orth_lags    : {col: k}  per-component selected lags
      max_orth     : max of orth_lags.values()
      loadings     : np.ndarray (n_comp,) post sign-flip
      var_exp      : float
    """
    cols   = comp_cols if comp_cols is not None else COMP_COLS
    panel  = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)
    prices = panel[f"eq_{market}"].dropna()
    prices.index = prices.index + pd.offsets.MonthEnd(0)

    # Align equity prices with components
    df = pd.DataFrame({"price": prices}).join(comps_df[cols], how="inner").dropna().sort_index()
    if len(df) < 60:
        raise ValueError(f"{market}: only {len(df)} aligned obs")

    log_p   = np.log(df["price"])
    returns = log_p.diff().dropna()  # log returns, pd.Series

    # BIC lag selection and orthogonalisation per component
    orth_lags = {}
    residuals = {}
    for col in cols:
        comp = df[col]
        k = select_orth_lag(comp, returns, max_lag=max_orth_lag)
        orth_lags[col] = k
        resid = orthogonalise(comp, returns, k)
        residuals[col] = resid

    # Align residuals on common dates and z-score
    resid_df = pd.DataFrame(residuals).dropna()
    scaled   = (resid_df - resid_df.mean()) / resid_df.std(ddof=1)

    # PCA
    scores, loadings, var_exp = _pca_first_component(scaled.values)
    scores, loadings = _apply_sign_convention(scores, loadings, cols)

    composite_z = pd.Series(scores, index=resid_df.index, name="composite")

    # Trim log_prices to match composite dates
    log_prices_aligned = log_p.reindex(resid_df.index)

    return {
        "composite_z":  composite_z,
        "log_prices":   log_prices_aligned,
        "orth_lags":    orth_lags,
        "max_orth":     max(orth_lags.values()),
        "loadings":     loadings,
        "var_exp":      float(var_exp),
    }


# ---------------------------------------------------------------------------
# Step 4 -- BIC Granger test lag via VAR
# ---------------------------------------------------------------------------

def select_granger_lag(composite_z, returns, max_lag=15):
    """
    Select the Granger test lag using VAR BIC order selection.

    Uses first differences of composite for stationarity.
    Returns an integer (minimum 1).  Fallback to 6 on failure.
    """
    comp_diff = composite_z.diff().dropna()
    data      = pd.concat([comp_diff, returns], axis=1).dropna()
    data.columns = ["comp_diff", "returns"]

    if len(data) < 50:
        return 6

    try:
        effective_max = min(max_lag, len(data) // 5)
        if effective_max < 1:
            return 6
        model = VAR(data)
        order = model.select_order(maxlags=effective_max)
        lag   = int(order.bic)
        return max(1, lag)   # at least 1
    except Exception:
        return 6


# ---------------------------------------------------------------------------
# Step 5 -- Buffer rule
# ---------------------------------------------------------------------------

def get_test_lag(max_orth, granger_bic, buffer=4):
    """
    test_lag = max(granger_bic, max_orth + buffer).

    The buffer ensures the Granger test checks lags beyond what was
    orthogonalised, preventing tautological passing.
    """
    return max(granger_bic, max_orth + buffer)


# ---------------------------------------------------------------------------
# Step 6 -- Granger test at test_lag
# ---------------------------------------------------------------------------

def test_exogeneity_bic(composite_z, returns, test_lag, alpha=0.05):
    """
    Reverse Granger test at test_lag: does equity_return predict D(composite)?
    Uses the existing granger_f_test from exogeneity.py.
    Returns (F, p_value, verdict).
    """
    z_diff = np.diff(composite_z.values)
    y_ret  = np.diff(returns.values)
    n      = min(len(z_diff), len(y_ret))
    if n < test_lag + 10:
        return np.nan, np.nan, "SKIP"
    F, p   = granger_f_test(z_diff[-n:], y_ret[-n:], test_lag)
    verdict = "PASS" if (not np.isnan(p) and p > alpha) else "FAIL"
    return float(F), float(p), verdict


# ---------------------------------------------------------------------------
# Step 7 -- Robustness check across buffers
# ---------------------------------------------------------------------------

def robustness_check(composite_z, returns, max_orth, granger_bic,
                     buffers=(2, 4, 6, 8), alpha=0.05):
    """
    Run the Granger test at test_lag = max(granger_bic, max_orth + buf)
    for each buffer in buffers.  Returns dict of results and a 'robust' flag.
    """
    results  = {}
    verdicts = []
    for buf in buffers:
        tl = get_test_lag(max_orth, granger_bic, buffer=buf)
        _, p, v = test_exogeneity_bic(composite_z, returns, tl, alpha)
        results[f"buf{buf}"] = {"test_lag": tl, "p": p, "verdict": v}
        verdicts.append(v)

    unique = set(v for v in verdicts if v in ("PASS", "FAIL"))
    robust = len(unique) == 1
    return results, robust


# ---------------------------------------------------------------------------
# CLI: lags -- print BIC lag selection table only
# ---------------------------------------------------------------------------

def show_bic_lags(max_orth_lag=12):
    """Print BIC-selected orthogonalisation lags for all markets (fast)."""
    print(f"\n{'='*70}")
    print(f"BIC orthogonalisation lags (max_lag={max_orth_lag})")
    print(f"{'='*70}")
    print(f"{'Market':<14} {'Country':<16}  {'CCI':>4}  {'VIX':>4}  {'BCI':>4}  "
          f"{'max':>4}  {'VarExp':>7}")
    print("-" * 60)

    comps = load_monthly_components()
    rows  = []
    for market, info in MARKETS.items():
        try:
            res = build_composite_for_market(market, comps, max_orth_lag)
            ol  = res["orth_lags"]
            print(f"{market:<14} {info['country']:<16}  "
                  f"{ol['global_cci']:>4}  {ol['vix_monthly']:>4}  "
                  f"{ol['bci_monthly']:>4}  {res['max_orth']:>4}  "
                  f"{res['var_exp']:>6.1%}")
            rows.append({"market": market, "country": info["country"],
                         "orth_cci": ol["global_cci"],
                         "orth_vix": ol["vix_monthly"],
                         "orth_bci": ol["bci_monthly"],
                         "max_orth": res["max_orth"],
                         "var_exp":  round(res["var_exp"], 4)})
        except Exception as e:
            print(f"{market:<14} ERROR: {e}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(TABLES_DIR, "bic_composite_lags.csv"), index=False
    )
    print(f"\nSaved: bic_composite_lags.csv")
    return rows


# ---------------------------------------------------------------------------
# Main: exogeneity screen + robustness
# ---------------------------------------------------------------------------

def run_bic_composite(markets=None, buffer=4, max_orth_lag=12, alpha=0.05):
    """
    Full BIC composite pipeline: lag selection, orthogonalisation, exogeneity.

    buffer      : default 4 â€” test_lag >= max_orth + buffer
    max_orth_lag: max lags tried in BIC orth selection
    """
    print(f"\n{'='*80}")
    print(f"BIC COMPOSITE -- exogeneity screen (buffer={buffer}, max_orth={max_orth_lag})")
    print(f"{'='*80}")
    print(f"{'Market':<14} {'C':>3} {'V':>3} {'B':>3} {'mo':>3} "
          f"{'gBIC':>5} {'tLag':>5}  {'p':>7}  Gate  Robust")
    print("-" * 65)

    comps    = load_monthly_components()
    markets  = list(MARKETS.keys()) if markets is None else markets
    rows     = []
    composites = {}  # store for TAR step

    panel = pd.read_csv(PANEL_PATH, index_col="date", parse_dates=True)

    for market in markets:
        country = MARKETS[market]["country"]
        try:
            # Build BIC composite
            res = build_composite_for_market(market, comps, max_orth_lag)
            composites[market] = res

            comp_z  = res["composite_z"]
            log_p   = res["log_prices"]
            ol      = res["orth_lags"]
            max_orth = res["max_orth"]

            # Equity returns for this market
            prices = panel[f"eq_{market}"].dropna()
            prices.index = prices.index + pd.offsets.MonthEnd(0)
            returns = np.log(prices).diff().dropna()
            returns = returns.reindex(comp_z.index).dropna()

            # BIC Granger test lag
            g_bic = select_granger_lag(comp_z, returns)

            # Apply buffer rule
            t_lag = get_test_lag(max_orth, g_bic, buffer=buffer)

            # Primary test
            F, p, verdict = test_exogeneity_bic(comp_z, returns, t_lag, alpha)

            # Robustness check
            rob_results, robust = robustness_check(
                comp_z, returns, max_orth, g_bic,
                buffers=(2, 4, 6, 8), alpha=alpha
            )

            flag = "*" if not robust else " "
            print(f"{market:<14} {ol['global_cci']:>3} {ol['vix_monthly']:>3} "
                  f"{ol['bci_monthly']:>3} {max_orth:>3} "
                  f"{g_bic:>5} {t_lag:>5}  {p:>7.4f}  {verdict}  "
                  f"{'YES' if robust else 'NO':>3}{flag}")

            row = {
                "market":       market,
                "country":      country,
                "orth_cci":     ol["global_cci"],
                "orth_vix":     ol["vix_monthly"],
                "orth_bci":     ol["bci_monthly"],
                "max_orth":     max_orth,
                "granger_bic":  g_bic,
                "test_lag":     t_lag,
                "F":            round(F, 3) if not np.isnan(F) else np.nan,
                "p_value":      round(p, 4) if not np.isnan(p) else np.nan,
                "verdict":      verdict,
                "robust":       robust,
                "var_exp":      round(res["var_exp"], 4),
            }
            for buf in (2, 4, 6, 8):
                r = rob_results[f"buf{buf}"]
                row[f"p_buf{buf}"] = round(r["p"], 4) if r["p"] and not np.isnan(r["p"]) else np.nan
                row[f"v_buf{buf}"] = r["verdict"]
            rows.append(row)

        except Exception as e:
            print(f"{market:<14} ERROR: {e}")
            rows.append({"market": market, "country": country, "verdict": "ERROR"})

    admissible = [r["market"] for r in rows if r.get("verdict") == "PASS"]
    print(f"\n{len(admissible)} of {len(markets)} markets admissible (buffer={buffer}).")
    robust_pass = sum(1 for r in rows if r.get("verdict") == "PASS" and r.get("robust"))
    print(f"Robustly exogenous (all buffers): {robust_pass}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, "bic_composite_results.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")

    return rows, composites, admissible


# ---------------------------------------------------------------------------
# TAR estimation for admissible markets
# ---------------------------------------------------------------------------

def _episode_verdict(state, dates, min_months=2, verbose=True):
    """Episode check (same as composite_study.py)."""
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


def run_tar_for_admissible(composites, admissible, spec=1):
    """
    TAR estimation for markets that passed the BIC exogeneity gate.
    Uses each market's BIC composite (already built in composites dict).
    """
    print(f"\n{'='*72}")
    print(f"TAR estimation for {len(admissible)} admissible markets (BIC composite)")
    print(f"{'='*72}")

    rows = []
    for market in admissible:
        country = MARKETS[market]["country"]
        print(f"  {market:<14} ({country:<16}) ...", end="", flush=True)

        try:
            res     = composites[market]
            comp_z  = res["composite_z"].values
            log_p   = res["log_prices"].values
            dates   = np.array(res["composite_z"].index, dtype="datetime64[ns]")

            if len(comp_z) < 120:
                print(" SKIP (< 120 obs)")
                continue

            z_min, z_max, gl, mg = _grid_bounds(comp_z)
            opt    = find_optimal_thresholds(log_p, comp_z, z_min, z_max,
                                             gl, mg, spec, "returns")
            c1, c2 = opt["c1"], opt["c2"]
            se_res = standard_errors(log_p, comp_z, c1, c2, spec, "returns")
            state  = _assign_states(comp_z[1:], c1, c2)
            T      = len(state)
            verdict = _episode_verdict(state, dates[1:])

            rows.append({
                "market":  market,
                "country": country,
                "T":       T,
                "c1": c1, "c2": c2,
                "beta_mr": se_res["beta1"],
                "beta_ex": se_res["beta3"],
                "n_mr":    se_res["n1"],
                "n_rw":    se_res["n2"],
                "n_ex":    se_res["n3"],
                "verdict": verdict,
            })
            print(f"  c1={c1:.3f}  c2={c2:.3f}  "
                  f"MR={100*se_res['n1']/T:.0f}%  RW={100*se_res['n2']/T:.0f}%  "
                  f"EXP={100*se_res['n3']/T:.0f}%  b3={se_res['beta3']:.4f}  {verdict}")
        except Exception as e:
            print(f" ERROR: {e}")

    if not rows:
        return []

    print(f"\n{'Market':<14} {'Country':<16} {'T':>5}  {'c1':>7} {'c2':>7}  "
          f"{'MR%':>5} {'RW%':>5} {'EXP%':>5}  {'b3':>8}  Verdict")
    print("-" * 95)
    for r in rows:
        T = r["T"]
        print(f"{r['market']:<14} {r['country']:<16} {T:>5}  "
              f"{r['c1']:>7.3f} {r['c2']:>7.3f}  "
              f"{100*r['n_mr']/T:>4.0f}% {100*r['n_rw']/T:>4.0f}% "
              f"{100*r['n_ex']/T:>4.0f}%  {r['beta_ex']:>8.4f}  {r['verdict']}")

    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, "bic_composite_tar.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    return rows


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_all(buffer=4, max_orth_lag=12):
    show_bic_lags(max_orth_lag)
    rows, composites, admissible = run_bic_composite(
        buffer=buffer, max_orth_lag=max_orth_lag
    )
    run_tar_for_admissible(composites, admissible)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "lags":
        show_bic_lags()
    elif cmd == "screen":
        run_bic_composite()
    elif cmd == "estimate":
        rows, composites, admissible = run_bic_composite()
        run_tar_for_admissible(composites, admissible)
    else:
        run_all()

