"""
drift_fdr.py - Round 6 (W1, W3, W4).

Rebuilds:
  table4_drift.csv       W1 - the explosive-state drift that justifies the label
  fdr_exogeneity.csv     W3 - Benjamini-Hochberg over the 56 screening tests
  fdr_coefficients.csv   W4 - Benjamini-Hochberg over the 45 coefficient t-tests

All three are DETERMINISTIC: no seed, no resampling. They should reproduce the
surviving exports exactly, and `python scripts/compare_rebuilt.py` is the check.

Spec, from results/exports/README.md Round 6:

  W1  "At the Table-4.1 thresholds, the explosive-state intercept alpha3 is
       positive for all 22 markets with EXP months (median 1.585, range
       0.339-8.382, 20/22 significant at 5%)." Also reports the NET contemporaneous
       EXP return, which is positive for only 12/22 because the reversal slope
       beta3 < 0 offsets alpha3.
  W3  "56 Granger tests: 24 FAIL at raw p<0.05 -> 19 survive BH (q=0.05)."
  W4  "45 coefficient t-tests (b_MR + b_EXP): 33 significant raw -> 30 survive BH."

Everything reuses the surviving engine: src/estimate.standard_errors and
src/exogeneity.granger_f_test.

Usage:  python scripts/drift_fdr.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def benjamini_hochberg(pvals, q):
    """Return (adjusted p, reject flags) under Benjamini-Hochberg at level q.

    Adjusted p is the standard step-up monotone transform:
        p_bh[(i)] = min over k>=i of  min(1, p[(k)] * m / k)
    """
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p, kind="stable")
    ranked = p[order]
    adj = ranked * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]      # enforce monotonicity
    adj = np.minimum(adj, 1.0)
    out = np.empty(m, dtype=float)
    out[order] = adj
    return out, out <= q


def w1_table4_drift():
    """W1 - explosive-state drift per market at the Table 4.1 thresholds."""
    from estimate import _assign_states, standard_errors          # noqa: E402
    from global_cci_study import load_global_cci_pair             # noqa: E402
    from market_config import MARKETS                             # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        c1, c2 = float(p["c1"]), float(p["c2"])
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        res = standard_errors(y, z, c1, c2, config.SPEC_SWITCHING_DRIFT, config.MODE)

        state = _assign_states(z[1:], c1, c2)
        dep = np.diff(y)
        exp_mask = state == 2
        n_exp = int(exp_mask.sum())
        # net contemporaneous return in the EXP state, in percent per month
        contemp = 100.0 * float(dep[exp_mask].mean()) if n_exp else float("nan")

        # NOTE: standard_errors() returns only the BETA standard errors - gridsearch
        # computes se_a1..se_a3 but does not put them in its return dict. W1 needs the
        # SE of the INTERCEPT, so recompute it here with estimate.py's own formula
        # (_ols_intercept: se_a = sqrt(s2 * Sxx / D), s2 = SSR/(n-2)).
        se_alpha, t_exp = float("nan"), float("nan")
        if n_exp > 2:
            xs = y[:-1][exp_mask]
            ys = dep[exp_mask]
            n = len(xs)
            sx, sy = xs.sum(), ys.sum()
            sxx, sxy = float(xs @ xs), float(xs @ ys)
            D = n * sxx - sx * sx
            if abs(D) > 1e-14:
                beta = (n * sxy - sx * sy) / D
                alpha = (sy - beta * sx) / n
                resid = ys - alpha - beta * xs
                s2 = float(resid @ resid) / (n - 2)
                se_alpha = float(np.sqrt(s2 * sxx / D))
                t_exp = alpha / se_alpha if se_alpha > 0 else float("nan")

        a = abs(t_exp) if not np.isnan(t_exp) else 0.0
        sig = "***" if a > 2.576 else "**" if a > 1.960 else "*" if a > 1.645 else ""

        rows.append({
            "market": mkt, "country": MARKETS[mkt]["country"],
            "alpha_MR": round(res["alpha1"], 5),
            "alpha_RW_drift": round(res["alpha2"], 5),
            "alpha_EXP": round(res["alpha3"], 5),
            "se_alpha_EXP": round(se_alpha, 5) if not np.isnan(se_alpha) else "",
            "t_alpha_EXP": round(t_exp, 3) if not np.isnan(t_exp) else "",
            "sig_alpha_EXP": sig,
            "beta_EXP": round(res["beta3"], 5),
            "mean_contemp_EXP_ret_pct": round(contemp, 4) if n_exp else "",
            "n_EXP": n_exp,
        })

    pos = [r for r in rows if r["n_EXP"] > 0 and r["alpha_EXP"] > 0]
    with_exp = [r for r in rows if r["n_EXP"] > 0]
    med = float(np.median([r["alpha_EXP"] for r in with_exp]))
    contemp_pos = sum(1 for r in with_exp if r["mean_contemp_EXP_ret_pct"] != ""
                      and r["mean_contemp_EXP_ret_pct"] > 0)
    print(f"  W1: alpha_EXP > 0 in {len(pos)}/{len(with_exp)} markets with EXP months, "
          f"median {med:.3f}")
    print(f"      net contemporaneous EXP return positive in only "
          f"{contemp_pos}/{len(with_exp)} - the reversal slope offsets the drift")
    return rows


def w3_fdr_exogeneity():
    """W3 - BH over the reverse-Granger screen."""
    from exogeneity import granger_f_test                          # noqa: E402
    from global_cci_study import load_global_cci_pair              # noqa: E402
    from market_config import MARKETS                              # noqa: E402

    rows = []
    for mkt in MARKETS:
        try:
            y, z, _ = load_global_cci_pair(mkt, config.START, None)
        except Exception:                                          # noqa: BLE001
            continue     # no equity data - excluded from the 56, as in the original
        if len(y) < 10:
            continue
        y_ret = np.diff(np.asarray(y, dtype=float))
        z_diff = np.diff(np.asarray(z, dtype=float))
        try:
            F, p = granger_f_test(z_diff, y_ret, config.N_LAGS_SCREEN)[:2]
        except Exception:                                          # noqa: BLE001
            continue
        rows.append({"market": mkt, "country": MARKETS[mkt]["country"],
                     "T": float(len(y)), "F": round(float(F), 4), "p": round(float(p), 4),
                     "gate": "FAIL" if p <= config.ALPHA else "PASS",
                     "n_lags": config.N_LAGS_SCREEN,
                     "direction": "return->d(globalCCI)"})

    p_bh, _ = benjamini_hochberg([r["p"] for r in rows], config.BH_Q)
    for r, pb in zip(rows, p_bh):
        r["p_bh"] = round(float(pb), 4)
        r["fail_raw"] = r["p"] <= config.ALPHA
        r["fail_bh"] = bool(pb <= config.BH_Q)

    raw = sum(1 for r in rows if r["fail_raw"])
    bh = sum(1 for r in rows if r["fail_bh"])
    print(f"  W3: {len(rows)} tests, {raw} FAIL raw -> {bh} FAIL after BH(q={config.BH_Q})")
    return rows


def w4_fdr_coefficients():
    """W4 - BH over the b_MR and b_EXP t-tests.

    t-statistics come from the ESTIMATOR (standard_errors), not from ratios of
    the panel CSV's rounded columns - the two are not the same to 3dp.
    """
    from scipy import stats as sps                                 # noqa: E402

    from estimate import standard_errors                           # noqa: E402
    from global_cci_study import load_global_cci_pair              # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        res = standard_errors(y, z, float(p["c1"]), float(p["c2"]),
                              config.SPEC_SWITCHING_DRIFT, config.MODE)
        # estimate.py's return convention: 1 = MR, 3 = EXP
        for label, tkey in (("b_MR", "tstat1"), ("b_EXP", "tstat3")):
            t = res.get(tkey)
            if t is None or not np.isfinite(t):
                continue               # e.g. Brazil: empty EXP band, no estimate
            # LARGE-SAMPLE normal p-value, not the t-distribution. This matches
            # src/global_cci_study._sig_marker, which stars on 2.576/1.960/1.645
            # (normal critical values); using a t df here shifts p by ~1e-3.
            pv = 2.0 * sps.norm.sf(abs(float(t)))
            rows.append({"market": mkt, "coef": label,
                         "t": round(float(t), 3), "p": round(float(pv), 5)})

    p_bh, _ = benjamini_hochberg([r["p"] for r in rows], config.BH_Q)
    for r, pb in zip(rows, p_bh):
        r["p_bh"] = round(float(pb), 5)
        r["sig_raw"] = r["p"] < config.ALPHA
        r["sig_bh"] = bool(pb <= config.BH_Q)

    raw = sum(1 for r in rows if r["sig_raw"])
    bh = sum(1 for r in rows if r["sig_bh"])
    print(f"  W4: {len(rows)} coefficient tests, {raw} significant raw -> {bh} after BH")
    return rows


def write(name, rows):
    out = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    print("Round 6 (W1, W3, W4) - deterministic, should reproduce exactly\n")
    write("table4_drift.csv", w1_table4_drift())
    write("fdr_exogeneity.csv", w3_fdr_exogeneity())
    write("fdr_coefficients.csv", w4_fdr_coefficients())


if __name__ == "__main__":
    main()
