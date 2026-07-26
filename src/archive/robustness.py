"""
Robustness layer: Hurst exponent vs TAR efficiency proportions across 27 markets.

For each market:
  1. Hurst exponent (R/S method) â€” established efficiency measure from the literature.
  2. TAR efficiency proportion â€” fraction of time in the random-walk state, using
     VIX as the trigger (grid search per market, spec=0 no-drift formulation).

If both metrics agree on rankings, the TAR-based approach is anchored to the
accepted standard. Divergences for segmented or emerging markets are findings.

Usage:
    python robustness.py
"""

import os
import sys
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from market_config import MARKETS
from exogeneity import _load_returns

DAILY_PANEL = os.path.join(os.path.dirname(__file__), "..", "data", "combined", "daily_panel.csv")

# Analysis window â€” matches Table 8 / VIX coverage
START = "1990-02"
END   = "2015-06"

# VIX grid params â€” from optimalvix.m
Z_MIN     = 10
Z_MAX     = 70
GRIDLEN   = 200
MIN_GAP   = 6
TLAG      = 1      # 1-day VIX lag for all markets (trigger determined before return)
MIN_OBS   = 500    # skip markets with fewer observations


# ---------------------------------------------------------------------------
# Hurst exponent â€” R/S (rescaled range) method
# ---------------------------------------------------------------------------

def hurst_rs(returns, min_n=8):
    """
    Estimate the Hurst exponent via R/S analysis.

    H â‰ˆ 0.5  â†’ random walk (efficient)
    H > 0.5  â†’ persistent (trending)
    H < 0.5  â†’ mean-reverting

    Vectorised over blocks â€” no Python inner loop.
    """
    T = len(returns)
    max_n = T // 4
    if max_n < min_n:
        return np.nan

    ns = np.unique(np.logspace(np.log10(min_n), np.log10(max_n), 25).astype(int))

    log_ns, log_rs = [], []

    for n in ns:
        n_blocks = T // n
        if n_blocks < 4:
            continue
        mat   = returns[: n_blocks * n].reshape(n_blocks, n)
        means = mat.mean(axis=1, keepdims=True)
        cs    = np.cumsum(mat - means, axis=1)
        R     = cs.max(axis=1) - cs.min(axis=1)
        S     = mat.std(axis=1, ddof=1)
        valid = S > 0
        if valid.sum() < 2:
            continue
        log_ns.append(np.log(n))
        log_rs.append(np.log((R[valid] / S[valid]).mean()))

    if len(log_ns) < 4:
        return np.nan

    H = float(np.polyfit(log_ns, log_rs, 1)[0])
    return H


# ---------------------------------------------------------------------------
# Fast TAR efficiency proportion â€” sort + prefix-sum trick, fully vectorised
# ---------------------------------------------------------------------------

def tar_efficiency_fast(y, z):
    """
    Find the TAR (c1, c2) pair that minimises RSS (spec=0, no-drift formulation)
    and return the fraction of time in the efficient/RW state.

    Speed: O(T log T + gridÂ²) via sort-and-prefix-sum â€” no Python inner loops.
    spec=0 chosen for vectorisability; qualitative market rankings are
    invariant to drift specification.
    """
    dep = np.diff(y)       # log returns, length T-1
    x   = y[:-1]           # lagged log levels, length T-1
    z_  = z[1:]            # z values aligned with dep
    n   = len(dep)

    # Sort observations by z
    idx  = np.argsort(z_)
    z_s  = z_[idx]
    x_s  = x[idx]
    y_s  = dep[idx]

    # Prefix sums (length n+1, index 0 is 0)
    pXY = np.concatenate([[0.0], np.cumsum(x_s * y_s)])
    pXX = np.concatenate([[0.0], np.cumsum(x_s ** 2)])
    pYY = np.concatenate([[0.0], np.cumsum(y_s ** 2)])

    sXY = pXY[n]; sXX = pXX[n]; sYY = pYY[n]

    # Grid and corresponding sorted-index boundaries
    grid  = np.linspace(Z_MIN, Z_MAX, GRIDLEN)
    k_all = np.searchsorted(z_s, grid, side='left')   # k_all[i] obs have z < grid[i]

    # All valid (i, j) pairs with min_gap separation
    i_vec = np.repeat(np.arange(GRIDLEN - 1), GRIDLEN - 1)
    j_vec = np.tile  (np.arange(GRIDLEN - 1), GRIDLEN - 1)
    keep  = (j_vec >= i_vec) & (j_vec < GRIDLEN - MIN_GAP)
    i_vec = i_vec[keep]; j_vec = j_vec[keep]

    k1 = k_all[i_vec]
    k2 = k_all[j_vec + MIN_GAP]

    # Require at least 2 obs per state
    valid = (k1 >= 2) & ((k2 - k1) >= 2) & ((n - k2) >= 2)
    k1 = k1[valid]; k2 = k2[valid]

    if len(k1) == 0:
        return np.nan

    # MR state (0..k1): no-intercept OLS, RSS = Î£yÂ² - (Î£xy)Â²/Î£xÂ²
    xy_mr = pXY[k1]; xx_mr = pXX[k1]; yy_mr = pYY[k1]
    with np.errstate(divide='ignore', invalid='ignore'):
        rss_mr = np.where(xx_mr > 1e-12, yy_mr - xy_mr**2 / xx_mr, yy_mr)

    # RW state (k1..k2): Î²=0, RSS = Î£yÂ²
    rss_rw = pYY[k2] - pYY[k1]

    # EXP state (k2..n): no-intercept OLS
    xy_ex = sXY - pXY[k2]; xx_ex = sXX - pXX[k2]; yy_ex = sYY - pYY[k2]
    with np.errstate(divide='ignore', invalid='ignore'):
        rss_ex = np.where(xx_ex > 1e-12, yy_ex - xy_ex**2 / xx_ex, yy_ex)

    rss = rss_mr + rss_rw + rss_ex
    best = np.argmin(rss)

    eff = float((k2[best] - k1[best]) / n)
    c1  = float(grid[i_vec[valid][best]])
    c2  = float(grid[j_vec[valid][best] + MIN_GAP])
    return eff, c1, c2


# ---------------------------------------------------------------------------
# Per-market worker (runs in its own process)
# ---------------------------------------------------------------------------

def _analyse_market(args):
    name, meta, panel_path, start, end, tlag = args

    eq_col = f"eq_{name}"
    try:
        panel  = pd.read_csv(panel_path, index_col="date", parse_dates=True)
        prices = panel[eq_col].dropna()
        vix    = panel["vix"].dropna()

        # Align equity and VIX, apply trigger lag via array slicing
        df = pd.DataFrame({"price": prices, "vix": vix}).dropna().loc[start:end]
        if len(df) < MIN_OBS:
            return name, None, f"insufficient data ({len(df)} obs)"

        log_p = np.log(df["price"].values).astype(float)
        trig  = df["vix"].values.astype(float)

        # Trigger lag: same approach as load_pair()
        y = log_p[tlag:]
        z = trig[:-tlag] if tlag > 0 else trig

        if len(y) < MIN_OBS:
            return name, None, "insufficient data after lag"

        returns = np.diff(log_p)      # for Hurst (no lag needed)
        H       = hurst_rs(returns)
        result  = tar_efficiency_fast(y, z)

        if result is None or np.isnan(result[0]):
            return name, None, "TAR failed (degenerate grid)"

        eff, c1, c2 = result
        return name, {
            "country": meta["country"],
            "T":       len(y),
            "H":       H,
            "eff":     eff,
            "c1":      c1,
            "c2":      c2,
        }, None

    except Exception as e:
        return name, None, str(e)


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def run_comparison():
    args_list = [
        (name, meta, DAILY_PANEL, START, END, TLAG)
        for name, meta in MARKETS.items()
    ]

    results = {}
    errors  = {}

    print(f"Running Hurst + TAR analysis for {len(args_list)} markets...")
    print(f"Window: {START} â†’ {END},  VIX lag: {TLAG} day\n")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(_analyse_market, a): a[0] for a in args_list}
        for fut in as_completed(futures):
            name, res, err = fut.result()
            if res:
                results[name] = res
                print(f"  âœ“ {name:<14} T={res['T']:>5}  H={res['H']:.3f}  eff={res['eff']*100:5.1f}%")
            else:
                errors[name] = err
                print(f"  âœ— {name:<14} skipped: {err}")

    if not results:
        print("No results â€” check data.")
        return

    # Build DataFrame
    rows = []
    for name, r in results.items():
        H   = r["H"]
        eff = r["eff"]
        h_class = ("Efficient"      if 0.45 <= H <= 0.55 else
                   "Persistent"     if H > 0.55          else
                   "Mean-reverting")
        t_class = ("Efficient"      if eff >= 0.80 else
                   "Mixed"          if eff >= 0.50 else
                   "Non-efficient")
        rows.append({
            "market":   name,
            "country":  r["country"],
            "T":        r["T"],
            "H":        round(H, 3),
            "eff%":     round(eff * 100, 1),
            "c1":       round(r["c1"], 1),
            "c2":       round(r["c2"], 1),
            "H_class":  h_class,
            "TAR_class": t_class,
        })

    df = pd.DataFrame(rows).sort_values("eff%", ascending=False).reset_index(drop=True)

    print("\n" + "=" * 90)
    print(f"{'#':<3} {'Market':<14} {'Country':<16} {'T':>5}  {'H':>6}  {'TAR eff%':>9}  "
          f"{'c1':>5} {'c2':>6}  {'Hurst class':<16} {'TAR class'}")
    print("-" * 90)
    for i, row in df.iterrows():
        agree = "âœ“" if row["H_class"] == row["TAR_class"] else " "
        print(f"{i+1:<3} {row['market']:<14} {row['country']:<16} {row['T']:>5}  "
              f"{row['H']:>6.3f}  {row['eff%']:>8.1f}%  "
              f"{row['c1']:>5.1f} {row['c2']:>6.1f}  "
              f"{row['H_class']:<16} {row['TAR_class']}  {agree}")

    # Correlation
    valid = df.dropna(subset=["H", "eff%"])
    if len(valid) >= 5:
        r = np.corrcoef(valid["H"], valid["eff%"])[0, 1]
        print(f"\nCorrelation (H vs TAR efficiency%): r = {r:.3f}  (n={len(valid)})")
        if abs(r) >= 0.6:
            print("â†’ Strong agreement â€” TAR method validated against Hurst benchmark.")
        elif abs(r) >= 0.3:
            print("â†’ Moderate agreement â€” methods broadly consistent.")
        else:
            print("â†’ Weak agreement â€” divergences may reflect regime-sensitivity of TAR.")

    if errors:
        print(f"\nSkipped {len(errors)} markets: {', '.join(errors)}")


if __name__ == "__main__":
    run_comparison()

