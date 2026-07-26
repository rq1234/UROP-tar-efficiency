"""
TAR (Threshold Autoregression) estimation engine.

Translates existing MATLAB gridsearch2.m / gridsearchchk.m / optimalz.m
into a general-purpose Python library.

State assignment (same in both modes):
  z(t) < c1  →  State 1: mean-reverting
  c1 ≤ z(t) ≤ c2  →  State 0: efficient / random walk
  z(t) > c2  →  State 2: explosive

"""

import numpy as np


def _ols_intercept(x, y):
    """
    Analytical OLS with intercept: y ~ 1 + x.
    Returns (alpha, beta, se_alpha, se_beta).
    SE uses the standard with-intercept formula:
      SE(β) = sqrt( s² * n / (n*Σx² - (Σx)²) )
    where s² = SSR / (n-2).
    """
    n = len(x)
    if n < 3:
        return 0.0, 0.0, np.nan, np.nan
    sx  = x.sum();   sy  = y.sum()
    sxx = np.dot(x, x); sxy = np.dot(x, y)
    D = n * sxx - sx * sx
    if abs(D) < 1e-14:
        return float(sy / n), 0.0, np.nan, np.nan
    beta   = (n * sxy - sx * sy) / D
    alpha  = (sy - beta * sx) / n
    resid  = y - alpha - beta * x
    s2     = np.dot(resid, resid) / (n - 2)
    se_b   = float(np.sqrt(s2 * n / D))
    se_a   = float(np.sqrt(s2 * sxx / D))
    return float(alpha), float(beta), se_a, se_b


def _ols_no_intercept(x, y):
    """
    Analytical OLS without intercept: y ~ x.
    Returns (beta, se_beta).
    SE formula: SE(β) = sqrt( s² / Σx² )  where s² = SSR/(n-1).
    """
    n   = len(x)
    sxx = np.dot(x, x)
    if sxx < 1e-14 or n < 2:
        return 0.0, np.nan
    beta  = float(np.dot(x, y) / sxx)
    resid = y - beta * x
    s2    = np.dot(resid, resid) / (n - 1)
    se_b  = float(np.sqrt(s2 / sxx))
    return beta, se_b


def _assign_states(z, c1, c2):
    """
    Assign state to each observation based on trigger value.

    Returns int array: 0=RW (efficient), 1=MR (mean-reverting), 2=EXP (explosive).
    Input z should be z[1:] (i.e. z values at time t=1..T-1, matching MATLAB's i=2:length).
    """
    state = np.zeros(len(z), dtype=int)
    state[z < c1] = 1
    state[z > c2] = 2
    return state


def gridsearch(y, z, c1, c2, spec, mode='returns'):
    """
    Fit TAR model for a given threshold pair (c1, c2).

    Translates gridsearch2.m (mode='levels') and gridsearchchk.m (mode='returns').

    Parameters
    ----------
    y    : np.ndarray, shape (T,) — log prices
    z    : np.ndarray, shape (T,) — trigger series, same length as y
    c1   : float — lower z-threshold
    c2   : float — upper z-threshold
    spec : int
             1 = switching drift (each state gets own alpha)
             2 = constant drift  (single alpha, dummy regression on returns)
             0 = no drift        (alpha = 0 everywhere)
    mode : str — 'returns' or 'levels'

    Returns
    -------
    dict with keys:
      alpha1, alpha2, alpha3 — intercepts per state (0 if not estimated)
      beta1,  beta2,  beta3  — slope coefficients per state
      n1, n2, n3             — observation counts per state
      RSS                    — full-sample residual sum of squares
      sigmae                 — residual std dev (RSS / (T-7))
    """
    T = len(y)

    # State assignment: z[t] for t = 1..T-1 (MATLAB: i = 2:length)
    state = _assign_states(z[1:], c1, c2)   # length T-1

    # Dependent variable and lagged predictor
    dep = np.diff(y)    # Δy[t] = y[t] - y[t-1], length T-1
    x   = y[:-1]        # y[t-1], length T-1

    # LHS of regression depends on mode
    lhs = dep if mode == 'returns' else y[1:]

    rw_mask  = (state == 0)
    mr_mask  = (state == 1)
    exp_mask = (state == 2)

    alpha1 = alpha2 = alpha3 = 0.0
    beta1  = beta2  = beta3  = 0.0
    # Standard errors (nan until computed)
    se_a1 = se_a2 = se_a3 = np.nan
    se_b1 = se_b2 = se_b3 = np.nan

    # ----- spec = 1: switching drift ----------------------------------------
    if spec == 1:
        if mr_mask.sum() > 2:
            alpha2, beta2, se_a2, se_b2 = _ols_intercept(x[mr_mask], lhs[mr_mask])
        if exp_mask.sum() > 2:
            alpha3, beta3, se_a3, se_b3 = _ols_intercept(x[exp_mask], lhs[exp_mask])
        # RW state: alpha = mean of returns, beta forced — SE of mean
        n_rw   = rw_mask.sum()
        beta1  = 0.0 if mode == 'returns' else 1.0
        if n_rw > 0:
            rw_dep = dep[rw_mask]
            alpha1 = float(rw_dep.mean())
            se_a1  = float(rw_dep.std(ddof=1) / np.sqrt(n_rw)) if n_rw > 1 else np.nan
            se_b1  = np.nan   # forced, no SE meaningful

    # ----- spec = 2: constant drift (dummy regression on returns) -----------
    elif spec == 2:
        d_mr  = mr_mask.astype(float)
        d_exp = exp_mask.astype(float)
        X_dum = np.column_stack([np.ones(len(dep)), d_mr * x, d_exp * x])
        XtX   = X_dum.T @ X_dum
        Xty   = X_dum.T @ dep
        try:
            params  = np.linalg.solve(XtX, Xty)
            resid2  = dep - X_dum @ params
            n2      = len(dep)
            s2_2    = np.dot(resid2, resid2) / (n2 - 3)
            var_p   = s2_2 * np.linalg.inv(XtX)
            se_p    = np.sqrt(np.diag(var_p))
            se_a1   = float(se_p[0])
            se_b2   = float(se_p[1])
            se_b3   = float(se_p[2])
        except np.linalg.LinAlgError:
            params = np.zeros(3)
        alpha1 = float(params[0]);  alpha2 = 0.0;  alpha3 = 0.0
        beta1  = 0.0 if mode == 'returns' else 1.0
        beta2  = float(params[1]);  beta3  = float(params[2])
        se_b1  = np.nan   # forced

    # ----- spec = 0: no drift -----------------------------------------------
    else:
        if mr_mask.sum() > 1:
            beta2, se_b2 = _ols_no_intercept(x[mr_mask], lhs[mr_mask])
        if exp_mask.sum() > 1:
            beta3, se_b3 = _ols_no_intercept(x[exp_mask], lhs[exp_mask])
        beta1 = 0.0 if mode == 'returns' else 1.0
        se_b1 = np.nan   # forced

    # ----- Full-sample RSS --------------------------------------------------
    # Mirrors MATLAB's RSS loop (gridsearch2.m lines 119-146).
    # spec=2: single shared drift α applies to all states in the residual
    # (gridsearchchk.m L109-114 — constant-intercept dummy regression).
    # Vectorized RSS — replaces Python for-loop with numpy indexing (~50x faster)
    betas_arr = np.array([beta1, beta2, beta3])[state]
    if spec == 2:
        alphas_arr = np.full(T - 1, alpha1)
    else:
        alphas_arr = np.array([alpha1, alpha2, alpha3])[state]

    lhs_rss = dep if mode == 'returns' else y[1:]
    e       = lhs_rss - alphas_arr - betas_arr * x
    RSS     = float(np.dot(e, e))
    sigmae  = float(np.sqrt(RSS / (T - 7)))

    # Return keys follow the paper's state convention (Table 7):
    #   1 = mean-reverting (z < c1)
    #   2 = efficient / RW (c1 ≤ z ≤ c2)
    #   3 = explosive      (z > c2)
    # SE keys mirror the same convention (se_b1=MR, se_b2=RW, se_b3=EXP).
    return {
        'alpha1': alpha2, 'alpha2': alpha1, 'alpha3': alpha3,
        'beta1':  beta2,  'beta2':  beta1,  'beta3':  beta3,
        'se_b1': se_b2,  'se_b2': se_b1,  'se_b3': se_b3,
        'n1': int(mr_mask.sum()), 'n2': int(rw_mask.sum()), 'n3': int(exp_mask.sum()),
        'RSS': RSS, 'sigmae': sigmae,
    }


def find_optimal_thresholds(y, z, z_min, z_max, gridlength=100, min_gap=4,
                            spec=1, mode='returns', min_pct=0.0):
    """
    Grid search for optimal TAR thresholds minimising RSS.

    Translates optimalz.m / optimalzchk.m.

    Parameters
    ----------
    z_min, z_max  : float — bounds of the z-threshold grid (overridden when min_pct > 0)
    gridlength    : int   — number of grid points (100 in Farid's scripts)
    min_gap       : int   — minimum grid-index separation between c1 and c2 (4 in Farid)
    min_pct       : float — minimum fraction of observations required in each regime.
                    When > 0, restricts the grid to [q_min_pct, q_(1-min_pct)] quantiles
                    of z and skips pairs where any regime has fewer than min_pct * T obs.
                    Matches tsDyn default of 0.10. Default 0.0 = no constraint.

    Returns
    -------
    dict — gridsearch() output at the optimal (c1, c2), plus 'c1' and 'c2' keys
    """
    z_th = z[1:]

    if min_pct > 0:
        z_min = float(np.quantile(z_th, min_pct))
        z_max = float(np.quantile(z_th, 1.0 - min_pct))

    grid    = np.linspace(z_min, z_max, gridlength)
    min_obs = int(np.ceil(min_pct * len(z_th))) if min_pct > 0 else 0
    min_ssr = np.inf
    best    = None

    for i in range(gridlength - 1):
        for j in range(i, gridlength - min_gap):
            c1    = grid[i]
            c2    = grid[j + min_gap]
            stats = gridsearch(y, z, c1, c2, spec, mode)
            if min_obs > 0 and min(stats['n1'], stats['n2'], stats['n3']) < min_obs:
                continue
            if stats['RSS'] < min_ssr:
                min_ssr    = stats['RSS']
                best       = stats.copy()
                best['c1'] = float(c1)
                best['c2'] = float(c2)

    return best


def standard_errors(y, z, c1, c2, spec, mode='returns'):
    """
    Compute betas, SEs, and t-statistics at given thresholds.

    SEs come directly from the OLS fits inside gridsearch():
      - spec=1: standard with-intercept formula SE(β) = sqrt(s²·n / (n·Σx²−(Σx)²))
      - spec=2: SE from the joint dummy regression covariance matrix
      - spec=0: no-intercept formula SE(β) = sqrt(s² / Σx²)

    Parameters
    ----------
    c1, c2 : optimal thresholds from find_optimal_thresholds()

    Returns
    -------
    dict — gridsearch() output extended with se1-3, tstat1-3
    """
    stats = gridsearch(y, z, c1, c2, spec, mode)

    betas  = np.array([stats['beta1'], stats['beta2'], stats['beta3']])
    ses    = np.array([stats['se_b1'], stats['se_b2'], stats['se_b3']])
    with np.errstate(invalid='ignore'):
        tstats = betas / np.where(ses > 0, ses, np.nan)

    return {
        **stats,
        'se1': float(ses[0]),    'se2': float(ses[1]),    'se3': float(ses[2]),
        'tstat1': float(tstats[0]), 'tstat2': float(tstats[1]), 'tstat3': float(tstats[2]),
    }
