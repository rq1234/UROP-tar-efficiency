"""
fastgrid.py - vectorised spec=1 TAR grid search.

WHY THIS EXISTS
---------------
src/estimate.py's find_optimal_thresholds evaluates ~4,800 threshold pairs per
market, calling gridsearch() for each. That costs roughly 1.4 s per fit, which
makes a B=1000 bootstrap that re-estimates the full grid on every draw
infeasible (23 markets x 1000 draws x 1.4 s is over 9 hours).

results/exports/README.md records that the original work used "a vectorized
spec=1 grid search that reproduces the repo's find_optimal_thresholds to 1e-9
on all 23 markets and is 347x faster (4.1 ms vs 1.4 s/fit)". That script was
lost. This is its replacement.

HOW IT WORKS
------------
For spec=1 / mode='returns', with dep = diff(y) and x = y[:-1]:

  MR  (z < c1)  intercept OLS of dep on x
  RW  (c1<=z<=c2)  beta forced to 0, alpha = mean(dep)
  EXP (z > c2)  intercept OLS of dep on x

Sort observations by the trigger z[1:]. Then for ANY threshold pair, MR is a
prefix of that sorted order and EXP is a suffix. So the six OLS sufficient
statistics (n, Sx, Sy, Sxx, Sxy, Syy) for all three regimes come from prefix
sums in O(1) per pair, and every pair is evaluated in one vectorised sweep.

RSS for an intercept OLS is  Syy - a*Sy - b*Sxy  (the cross terms cancel at
the optimum via the normal equations). For the RW band with beta forced to 0
and alpha = mean, it is  Syy - Sy^2/n.

EXACTNESS
---------
The regime guards are replicated exactly as src/estimate.py has them:
`if mr_mask.sum() > 2` and `if exp_mask.sum() > 2` - a regime with 2 or fewer
observations contributes alpha=beta=0, so its residual is dep itself and its
RSS contribution is Syy. Ties are broken the same way too: gridsearch keeps a
pair only on a strict `<`, so the FIRST minimum in iteration order wins, which
is what np.argmin returns.

Usage
-----
    python scripts/fastgrid.py            # validate against all 23 markets
    from fastgrid import fast_optimal_thresholds
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402


def _pair_indices(gridlength, min_gap):
    """The (i, j) pairs find_optimal_thresholds visits, in its exact order.

    for i in range(gridlength - 1):
        for j in range(i, gridlength - min_gap):
            c1 = grid[i]; c2 = grid[j + min_gap]
    """
    ii, jj = [], []
    for i in range(gridlength - 1):
        for j in range(i, gridlength - min_gap):
            ii.append(i)
            jj.append(j + min_gap)
    return np.asarray(ii, dtype=np.int64), np.asarray(jj, dtype=np.int64)


def fast_grid_rss(y, z, grid, min_gap):
    """RSS for every threshold pair on the grid, in find_optimal_thresholds order.

    Returns (rss, i_idx, j_idx) where rss[k] corresponds to c1=grid[i_idx[k]],
    c2=grid[j_idx[k]].
    """
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    return fast_grid_rss_parts(np.diff(y), y[:-1], z[1:], grid, min_gap)


def fast_grid_rss_parts(dep, x, zt, grid, min_gap, rw_free=False):
    """Same as fast_grid_rss but takes the regression parts directly.

    The bootstrap needs this: the wild scheme perturbs `dep` while holding `x`
    and `z` fixed, which does not correspond to any single log-price path, and
    the block schemes resample (dep, x, z) triples. Both break the assumption
    that dep == diff(y) and x == y[:-1], so they cannot go through fast_grid_rss.

    All three arrays must already be aligned and the same length (T-1).
    """
    dep = np.asarray(dep, dtype=float)
    x = np.asarray(x, dtype=float)
    zt = np.asarray(zt, dtype=float)

    order = np.argsort(zt, kind="stable")
    zs = zt[order]
    xs = x[order]
    ds = dep[order]

    # Prefix sums, with a leading zero so P[k] == sum of the first k elements.
    def pre(a):
        out = np.zeros(len(a) + 1, dtype=float)
        np.cumsum(a, out=out[1:])
        return out

    P_n = np.arange(len(zs) + 1, dtype=float)
    P_x = pre(xs)
    P_y = pre(ds)
    P_xx = pre(xs * xs)
    P_xy = pre(xs * ds)
    P_yy = pre(ds * ds)

    # Regime boundaries for each grid value.
    #   MR  = zt <  c1  -> sorted[:kL]      (searchsorted 'left')
    #   EXP = zt >  c2  -> sorted[kR:]      (searchsorted 'right')
    kL_all = np.searchsorted(zs, grid, side="left")
    kR_all = np.searchsorted(zs, grid, side="right")

    i_idx, j_idx = _pair_indices(len(grid), min_gap)
    kL = kL_all[i_idx]
    kR = kR_all[j_idx]
    # A pair with c2 < c1 cannot occur here: j >= i + min_gap, and grid ascends.

    def stats(lo, hi):
        return (P_n[hi] - P_n[lo], P_x[hi] - P_x[lo], P_y[hi] - P_y[lo],
                P_xx[hi] - P_xx[lo], P_xy[hi] - P_xy[lo], P_yy[hi] - P_yy[lo])

    n_end = len(zs)
    mr = stats(np.zeros_like(kL), kL)
    rw = stats(kL, kR)
    ex = stats(kR, np.full_like(kR, n_end))

    def rss_ols(n, Sx, Sy, Sxx, Sxy, Syy):
        """RSS of an intercept OLS, or Syy where estimate.py leaves alpha=beta=0."""
        out = Syy.copy()
        # estimate.py guard: `if mask.sum() > 2`
        ok = n > 2
        if not np.any(ok):
            return out
        nn, sx, sy = n[ok], Sx[ok], Sy[ok]
        sxx, sxy, syy = Sxx[ok], Sxy[ok], Syy[ok]
        den = nn * sxx - sx * sx
        # Degenerate design (all x identical): estimate.py's lstsq returns the
        # least-norm solution; with no x variation that is b=0, a=mean.
        safe = np.abs(den) > 1e-14
        b = np.zeros_like(nn)
        np.divide(nn * sxy - sx * sy, den, out=b, where=safe)
        a = (sy - b * sx) / nn
        out[ok] = syy - a * sy - b * sxy
        return out

    def rss_mean_only(n, Sy, Syy):
        """RW band: beta forced to 0, alpha = mean(dep)  ->  RSS = Syy - Sy^2/n."""
        out = Syy.copy()
        ok = n > 0
        out[ok] = Syy[ok] - (Sy[ok] * Sy[ok]) / n[ok]
        return out

    # rw_free=True gives the THREE-FREE-REGIMES model of Round 4 T5, where the
    # middle band also gets an intercept OLS instead of the imposed beta=0.
    # The optimal thresholds under that model are not generally the spec=1 ones.
    rw_rss = rss_ols(*rw) if rw_free else rss_mean_only(rw[0], rw[2], rw[5])
    rss = rss_ols(*mr) + rw_rss + rss_ols(*ex)
    return rss, i_idx, j_idx


def fast_optimal_thresholds(y, z, z_min, z_max, gridlength=None, min_gap=None,
                            spec=1, mode="returns"):
    """Drop-in replacement for find_optimal_thresholds for spec=1 / 'returns'.

    Returns a dict with 'c1' and 'c2'. Callers needing the full coefficient set
    should pass the thresholds to src.estimate.standard_errors, exactly as
    src/global_cci_study.py does.
    """
    if spec != 1 or mode != "returns":
        raise ValueError("fastgrid implements spec=1 / mode='returns' only; "
                         "use src.estimate.find_optimal_thresholds for others")
    gridlength = gridlength or config.GRID_LENGTH
    min_gap = min_gap if min_gap is not None else config.MIN_GAP_FLOOR

    grid = np.linspace(z_min, z_max, gridlength)
    rss, i_idx, j_idx = fast_grid_rss(y, z, grid, min_gap)
    k = int(np.argmin(rss))     # first minimum, matching the strict `<` in the original
    return {"c1": float(grid[i_idx[k]]), "c2": float(grid[j_idx[k]]), "RSS": float(rss[k])}


def optimal_from_parts(dep, x, zt, z_min, z_max, gridlength=None, min_gap=None):
    """Threshold pair minimising RSS, from regression parts (bootstrap path)."""
    gridlength = gridlength or config.GRID_LENGTH
    min_gap = min_gap if min_gap is not None else config.MIN_GAP_FLOOR
    grid = np.linspace(z_min, z_max, gridlength)
    rss, i_idx, j_idx = fast_grid_rss_parts(dep, x, zt, grid, min_gap)
    k = int(np.argmin(rss))
    return float(grid[i_idx[k]]), float(grid[j_idx[k]])


def fit_spec1(dep, x, zt, c1, c2):
    """Fit spec=1 at given thresholds; return coefficients, counts and residuals.

    Mirrors src/estimate.gridsearch's spec=1 / mode='returns' branch, including
    the `> 2` guards, so bootstrap draws are generated from exactly the model
    the paper estimates.
    """
    dep = np.asarray(dep, dtype=float)
    x = np.asarray(x, dtype=float)
    state = np.zeros(len(zt), dtype=int)
    state[np.asarray(zt) < c1] = 1
    state[np.asarray(zt) > c2] = 2

    a = np.zeros(3)
    b = np.zeros(3)
    for s, idx in ((1, state == 1), (2, state == 2)):
        if idx.sum() > 2:
            xs, ys = x[idx], dep[idx]
            n = xs.size
            den = n * (xs @ xs) - xs.sum() ** 2
            if abs(den) > 1e-14:
                b[s] = (n * (xs @ ys) - xs.sum() * ys.sum()) / den
            a[s] = (ys.sum() - b[s] * xs.sum()) / n
    rw = state == 0
    if rw.sum() > 0:
        a[0] = dep[rw].mean()

    fitted = a[state] + b[state] * x
    return {"alpha": a, "beta": b, "state": state,
            "fitted": fitted, "resid": dep - fitted,
            "n": np.array([(state == 1).sum(), rw.sum(), (state == 2).sum()])}


# ===========================================================================
#  Validation - the acceptance test this script must pass
# ===========================================================================
def validate(tol=1e-9, verbose=True):
    """Reproduce find_optimal_thresholds on all 23 panel markets.

    Returns (n_ok, n_total, rows). Exits non-zero from __main__ if any market
    fails, so this can gate the rest of the rebuild.
    """
    import csv

    from estimate import find_optimal_thresholds          # noqa: E402
    from global_cci_study import _grid_bounds, load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows, n_ok = [], 0
    t_slow = t_fast = 0.0
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        z_min, z_max, gl, mg = _grid_bounds(z)

        t0 = time.perf_counter()
        ref = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
        t_slow += time.perf_counter() - t0

        t0 = time.perf_counter()
        got = fast_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
        t_fast += time.perf_counter() - t0

        d1 = abs(ref["c1"] - got["c1"])
        d2 = abs(ref["c2"] - got["c2"])
        dr = abs(ref["RSS"] - got["RSS"])
        ok = d1 <= tol and d2 <= tol and dr <= max(tol, abs(ref["RSS"]) * 1e-12)
        n_ok += ok
        rows.append((mkt, ok, ref["c1"], got["c1"], ref["c2"], got["c2"], dr))
        if verbose:
            flag = "ok  " if ok else "FAIL"
            print(f"  {flag} {mkt:<11} c1 {ref['c1']:.6f}/{got['c1']:.6f}  "
                  f"c2 {ref['c2']:.6f}/{got['c2']:.6f}  dRSS {dr:.3e}")

    if verbose:
        speed = (t_slow / t_fast) if t_fast else float("nan")
        print(f"\n  {n_ok}/{len(panel)} markets reproduce find_optimal_thresholds "
              f"to {tol:g}")
        print(f"  reference {t_slow:.2f}s total, fastgrid {t_fast:.3f}s total "
              f"-> {speed:.0f}x faster")
    return n_ok, len(panel), rows


if __name__ == "__main__":
    print("Validating fastgrid against src/estimate.find_optimal_thresholds\n")
    ok, total, _ = validate()
    if ok != total:
        print("\nVALIDATION FAILED - do not build on this until it passes.")
        sys.exit(1)
    print("\nVALIDATION PASSED.")
