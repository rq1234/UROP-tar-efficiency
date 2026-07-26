"""
Horizon return test for Global CCI regime classifications.

For each regime (MR, RW, EXP), computes mean forward cumulative equity return
over 1, 3, 6, and 12-month horizons, pooled across all admissible markets.
Runs Welch t-tests (MR vs RW, EXP vs RW) and one-way ANOVA at each horizon.

Data source: global CCI thresholds from global_cci_all_markets.csv (Option A,
full-sample); equity prices from monthly_panel.csv.

Admissible markets are read dynamically from global_cci_all_markets.csv so this
script always uses whatever set passed the exogeneity gate (currently 27 markets).

Usage:
    cd src && python horizon_test.py           # run test + save distribution chart
    cd src && python horizon_test.py dist      # distribution chart only
"""

import math
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind, f_oneway, gaussian_kde

sys.path.insert(0, os.path.dirname(__file__))
from estimate         import _assign_states
from market_config    import MARKETS
from replicate        import PANEL_PATH
from bubble_now       import TABLES_DIR, FULL_END
from global_cci_study import load_global_cci_pair, START

RESULTS_CSV = os.path.join(os.path.dirname(__file__), "..", "results", "tables",
                           "global_cci_all_markets.csv")
GCCI_DIR    = os.path.join(os.path.dirname(__file__), "..", "results", "gcci")

HORIZONS = [1, 3, 6, 12]

_STATE_NAMES = {0: "RW", 1: "MR", 2: "EXP"}
_COLOURS     = {1: "#4472C4", 0: "#808080", 2: "#C00000"}
_LABELS      = {1: "MR (mean-reverting)", 0: "RW (efficient)", 2: "EXP (explosive)"}


# ---------------------------------------------------------------------------
# Core computation helpers
# ---------------------------------------------------------------------------

def forward_returns(y_ret, h):
    """
    fwd[i] = sum of y_ret[i+1 : i+1+h]  (next h monthly log-returns after period i).
    NaN for the last h observations (no complete forward window).
    """
    T = len(y_ret)
    fwd = np.full(T, np.nan)
    for i in range(T - h):
        fwd[i] = y_ret[i + 1: i + 1 + h].sum()
    return fwd


def label_exp_spells(state):
    """
    For each EXP month, assign it to the early or late phase of its consecutive
    EXP run: early = first ceil(L/2) months of the run, late = remaining months.

    Returns int array same length as state:
      -1 = not EXP
       0 = early EXP (bubble inflation phase)
       1 = late  EXP (extended bubble, approaching peak)
    """
    T = len(state)
    labels = np.full(T, -1, dtype=int)
    i = 0
    while i < T:
        if state[i] == 2:
            j = i
            while j < T and state[j] == 2:
                j += 1
            run_len = j - i
            split = math.ceil(run_len / 2)
            for k in range(run_len):
                labels[i + k] = 0 if k < split else 1
            i = j
        else:
            i += 1
    return labels


def load_market_data(market, saved_thresholds):
    """
    Return (state, y_ret, dates_ret) for one market using saved c1/c2.
    state and y_ret are aligned: state[i] classifies return y_ret[i].
    """
    y, z, dates = load_global_cci_pair(market, START, FULL_END)
    c1 = saved_thresholds.loc[market, "c1"]
    c2 = saved_thresholds.loc[market, "c2"]
    state     = _assign_states(z[1:], c1, c2)
    y_ret     = np.diff(y)
    dates_ret = dates[1:]
    return state, y_ret, dates_ret


def _build_pooled_arrays():
    """
    Load all admissible markets and compute pooled forward returns by regime.

    Returns
    -------
    pooled_arrays : {h: {0: np.array(RW), 1: np.array(MR), 2: np.array(EXP)}}
    pooled_exp_phase : {h: {"early": np.array, "late": np.array}}
    per_market_rows : list of dicts with market-level observation counts
    """
    saved      = pd.read_csv(RESULTS_CSV).set_index("market")
    admissible = list(saved.index)

    per_market_rows  = []
    pooled           = {h: {0: [], 1: [], 2: []} for h in HORIZONS}
    pooled_exp_phase = {h: {"early": [], "late": []} for h in HORIZONS}

    print(f"\nLoading {len(admissible)} markets and computing forward returns...")
    for market in admissible:
        try:
            state, y_ret, dates_ret = load_market_data(market, saved)
        except Exception as e:
            print(f"  {market}: ERROR {e}")
            continue

        country = MARKETS[market]["country"]
        n_mr  = int((state == 1).sum())
        n_rw  = int((state == 0).sum())
        n_exp = int((state == 2).sum())
        print(f"  {market:<14} ({country:<16}) T={len(state):>4}  "
              f"MR={n_mr:>3}  RW={n_rw:>4}  EXP={n_exp:>3}")
        per_market_rows.append({
            "market": market, "country": country,
            "T": len(state), "n_MR": n_mr, "n_RW": n_rw, "n_EXP": n_exp,
        })

        # Japan's c2=99.87 sits in the middle of the global CCI distribution,
        # classifying 61% of months as EXP — not genuine euphoria, just the
        # structural gap between Japan's low baseline and the global average.
        # Exclude Japan's EXP observations from the pooled EXP array.
        exclude_exp = (market == "nikkei225")
        exp_phase   = label_exp_spells(state)

        for h in HORIZONS:
            fwd = forward_returns(y_ret, h)
            for s in [0, 1, 2]:
                if s == 2 and exclude_exp:
                    continue
                mask = (state == s) & ~np.isnan(fwd)
                pooled[h][s].extend(fwd[mask].tolist())

            if not exclude_exp:
                for phase_code, phase_name in [(0, "early"), (1, "late")]:
                    mask = (exp_phase == phase_code) & ~np.isnan(fwd)
                    pooled_exp_phase[h][phase_name].extend(fwd[mask].tolist())

    pooled_arrays = {
        h: {s: np.array(v) for s, v in pooled[h].items()}
        for h in HORIZONS
    }
    pooled_exp_phase = {
        h: {k: np.array(v) for k, v in pooled_exp_phase[h].items()}
        for h in HORIZONS
    }
    return pooled_arrays, pooled_exp_phase, per_market_rows


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def run_horizon_test():
    pooled_arrays, pooled_exp_phase, per_market_rows = _build_pooled_arrays()

    # ---------------------------------------------------------------------------
    # Results table
    # ---------------------------------------------------------------------------
    print(f"\n{'='*75}")
    print("HORIZON RETURN TEST — pooled across admissible markets (global CCI)")
    print("Forward cumulative log-returns (%) after regime classification")
    print(f"{'='*75}")

    header = (f"{'Horizon':>8}  {'MR mean%':>9} {'n':>5}  "
              f"{'RW mean%':>9} {'n':>5}  "
              f"{'EXP mean%':>9} {'n':>5}  "
              f"{'MR-RW p':>8}  {'EXP-RW p':>8}  {'ANOVA p':>8}")
    print(header)
    print("-" * 75)

    result_rows   = []
    mr_by_horizon = {}

    for h in HORIZONS:
        mr  = pooled_arrays[h][1]
        rw  = pooled_arrays[h][0]
        exp = pooled_arrays[h][2]

        mr_mean  = np.mean(mr)  * 100
        rw_mean  = np.mean(rw)  * 100
        exp_mean = (np.mean(exp) * 100) if len(exp) > 0 else np.nan

        mr_rw_p  = ttest_ind(mr, rw,  equal_var=False).pvalue if len(mr)  > 1 and len(rw)  > 1 else np.nan
        exp_rw_p = ttest_ind(exp, rw, equal_var=False).pvalue if len(exp) > 1 and len(rw)  > 1 else np.nan

        groups  = [g for g in [mr, rw, exp] if len(g) > 1]
        anova_p = f_oneway(*groups).pvalue if len(groups) >= 2 else np.nan

        mr_by_horizon[h] = mr

        print(f"{h:>7}m  "
              f"{mr_mean:>+8.2f}% {len(mr):>5}  "
              f"{rw_mean:>+8.2f}% {len(rw):>5}  "
              f"{exp_mean:>+8.2f}% {len(exp):>5}  "
              f"{mr_rw_p:>8.4f}  {exp_rw_p:>8.4f}  {anova_p:>8.4f}")

        result_rows.append({
            "horizon":      h,
            "MR_mean_pct":  round(mr_mean,  4),
            "RW_mean_pct":  round(rw_mean,  4),
            "EXP_mean_pct": round(exp_mean, 4),
            "n_MR":  len(mr),
            "n_RW":  len(rw),
            "n_EXP": len(exp),
            "MR_vs_RW_p":  round(mr_rw_p,  4),
            "EXP_vs_RW_p": round(exp_rw_p, 4),
            "ANOVA_p":     round(anova_p,  4),
        })

    # ---------------------------------------------------------------------------
    # Current signal quantification
    # ---------------------------------------------------------------------------
    print(f"\n{'='*75}")
    print("CURRENT SIGNAL QUANTIFICATION (May 2026 = MR for most markets)")
    print(f"{'='*75}")
    for h in HORIZONS:
        mr = mr_by_horizon[h]
        if len(mr) < 2:
            continue
        mean_h = np.mean(mr) * 100
        se_h   = np.std(mr, ddof=1) / np.sqrt(len(mr)) * 100
        ci_lo  = mean_h - 1.96 * se_h
        ci_hi  = mean_h + 1.96 * se_h
        print(f"  {h:>2}m: {mean_h:>+6.2f}%  "
              f"95% CI [{ci_lo:>+6.2f}%, {ci_hi:>+6.2f}%]  "
              f"(n={len(mr)})")

    # ---------------------------------------------------------------------------
    # Early vs late EXP breakdown
    # ---------------------------------------------------------------------------
    print(f"\n{'='*75}")
    print("EARLY vs LATE EXP BREAKDOWN")
    print("early = first ceil(L/2) months of each EXP run  |  late = remainder")
    print("Japan excluded from EXP pool (degenerate threshold)")
    print(f"{'='*75}")

    header2 = (f"{'Horizon':>8}  {'early mean%':>11} {'n':>5}  "
               f"{'late mean%':>10} {'n':>5}  "
               f"{'early-late p':>12}")
    print(header2)
    print("-" * 60)

    exp_phase_rows = []
    for h in HORIZONS:
        early = pooled_exp_phase[h]["early"]
        late  = pooled_exp_phase[h]["late"]

        early_mean = np.mean(early) * 100 if len(early) > 0 else np.nan
        late_mean  = np.mean(late)  * 100 if len(late)  > 0 else np.nan

        p = ttest_ind(early, late, equal_var=False).pvalue if len(early) > 1 and len(late) > 1 else np.nan

        print(f"{h:>7}m  "
              f"{early_mean:>+10.2f}% {len(early):>5}  "
              f"{late_mean:>+9.2f}% {len(late):>5}  "
              f"{p:>12.4f}")

        exp_phase_rows.append({
            "horizon":            h,
            "early_EXP_mean_pct": round(early_mean, 4),
            "late_EXP_mean_pct":  round(late_mean,  4),
            "n_early":            len(early),
            "n_late":             len(late),
            "early_vs_late_p":    round(p, 4),
        })

    # ---------------------------------------------------------------------------
    # Save outputs
    # ---------------------------------------------------------------------------
    os.makedirs(GCCI_DIR, exist_ok=True)

    results_df = pd.DataFrame(result_rows)
    main_path  = os.path.join(GCCI_DIR, "horizon_test.csv")
    results_df.to_csv(main_path, index=False)
    print(f"\nSaved: {main_path}")

    per_market_df = pd.DataFrame(per_market_rows)
    pm_path       = os.path.join(GCCI_DIR, "horizon_test_per_market.csv")
    per_market_df.to_csv(pm_path, index=False)
    print(f"Saved: {pm_path}")

    phase_df   = pd.DataFrame(exp_phase_rows)
    phase_path = os.path.join(GCCI_DIR, "horizon_test_exp_phase.csv")
    phase_df.to_csv(phase_path, index=False)
    print(f"Saved: {phase_path}")

    # ---------------------------------------------------------------------------
    # Per-market audit table
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("PER-MARKET OBSERVATION COUNTS")
    print(f"{'='*60}")
    print(f"{'Market':<14} {'Country':<18} {'T':>5}  {'MR':>4} {'RW':>5} {'EXP':>4}")
    print("-" * 55)
    total_mr = total_rw = total_exp = 0
    for r in per_market_rows:
        print(f"{r['market']:<14} {r['country']:<18} {r['T']:>5}  "
              f"{r['n_MR']:>4} {r['n_RW']:>5} {r['n_EXP']:>4}")
        total_mr  += r["n_MR"]
        total_rw  += r["n_RW"]
        total_exp += r["n_EXP"]
    print("-" * 55)
    print(f"{'TOTAL':<14} {'':<18} {'':>5}  "
          f"{total_mr:>4} {total_rw:>5} {total_exp:>4}")


# ---------------------------------------------------------------------------
# Distribution chart
# ---------------------------------------------------------------------------

def chart_horizon_distributions(h=12):
    """
    3-subplot distribution chart for h-month forward returns by TAR regime.
    Each subplot: histogram + KDE + mean dashed line + annotation (n, mean, p-value).
    Saves to results/gcci/horizon_distributions_{h}m.png.
    """
    pooled_arrays, _, _ = _build_pooled_arrays()
    arrays = pooled_arrays[h]

    rw_raw  = arrays[0]
    mr_raw  = arrays[1]
    exp_raw = arrays[2]

    p_mr  = ttest_ind(mr_raw,  rw_raw, equal_var=False).pvalue if len(mr_raw)  > 1 else np.nan
    p_exp = ttest_ind(exp_raw, rw_raw, equal_var=False).pvalue if len(exp_raw) > 1 else np.nan

    def _fmt_p(p):
        if np.isnan(p):    return "n/a"
        if p < 0.001:      return "p < 0.001 vs RW"
        if p < 0.01:       return f"p = {p:.3f} vs RW"
        return             f"p = {p:.2f} vs RW"

    # Convert to % for display
    specs = [
        (mr_raw  * 100, 1, _fmt_p(p_mr)),
        (rw_raw  * 100, 0, "baseline"),
        (exp_raw * 100, 2, _fmt_p(p_exp)),
    ]

    # Shared x range: 1st–99th percentile of all data combined
    all_vals = np.concatenate([mr_raw, rw_raw, exp_raw]) * 100
    x_lo = np.percentile(all_vals, 1)
    x_hi = np.percentile(all_vals, 99)
    xs   = np.linspace(x_lo, x_hi, 400)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
    fig.suptitle(
        f"Distribution of {h}-month forward log-returns by TAR regime\n"
        f"Pooled across 23 admissible markets  |  Global OECD CCI trigger",
        fontsize=12, y=1.02,
    )

    for ax, (data, state_code, p_label) in zip(axes, specs):
        col   = _COLOURS[state_code]
        label = _LABELS[state_code]
        mean  = np.mean(data)
        n     = len(data)

        ax.hist(data, bins=40, density=True, range=(x_lo, x_hi),
                color=col, alpha=0.30, linewidth=0)

        kde_fn = gaussian_kde(data, bw_method="scott")
        ax.plot(xs, kde_fn(xs), color=col, lw=2.2)

        ax.axvline(mean, color=col, lw=1.8, linestyle="--", label=f"mean = {mean:+.1f}%")
        ax.axvline(0,    color="black", lw=0.8, alpha=0.35)

        sign = "+" if mean >= 0 else ""
        ax.text(
            0.97, 0.97,
            f"n = {n:,}\nmean = {sign}{mean:.1f}%\n{p_label}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            family="monospace",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=col, alpha=0.85, lw=0.8),
        )

        ax.set_title(label, fontsize=11, fontweight="bold", color=col, pad=8)
        ax.set_xlabel(f"{h}-month forward log-return (%)", fontsize=10)
        if ax is axes[0]:
            ax.set_ylabel("Density", fontsize=10)
        ax.set_xlim(x_lo, x_hi)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)

    plt.tight_layout()
    os.makedirs(GCCI_DIR, exist_ok=True)
    out = os.path.join(GCCI_DIR, f"horizon_distributions_{h}m.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "dist":
        chart_horizon_distributions()
    else:
        run_horizon_test()
        chart_horizon_distributions()
