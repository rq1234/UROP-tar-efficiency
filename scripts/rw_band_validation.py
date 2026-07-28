"""
rw_band_validation.py - Round 10 Priority 3: validate the imposed RW band.

Rebuilds `rw_band_validation.csv`.

Deterministic - no seed, no resampling. Should reproduce the export exactly.

Spec, from results/exports/README.md Round 10 Priority 3:

  "Unrestricted middle-band slope b_RW AT THE BASELINE THRESHOLDS: 16 negative /
   7 positive; 6/23 significant at raw p<0.05 but 0/23 survive Benjamini-Hochberg
   (q=0.05). Median b_RW = -0.0063 (95% CI half-width ~0.013, includes 0 for all).
   ... the positional RW share counts as 'validated efficient' only where b_RW
   fails to reject the imposed RW at BH q<0.05 - and since no market rejects, the
   positional and validated RW shares coincide."

The main specification forces b_RW = 0. This frees it - but holds the thresholds
FIXED at their Table 4.1 values. That is what distinguishes it from Round 4 T5
(`unrestricted_b2.csv`), which RE-ESTIMATES the thresholds with three free
regimes and reports 8/23. The two are different questions and the draft must not
present them as the same check; see VERIFICATION_REPORT.md entry C20x.

Usage:  python scripts/rw_band_validation.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                                          # noqa: E402
from drift_fdr import benjamini_hochberg       # noqa: E402


def main():
    from scipy import stats as sps                     # noqa: E402

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS                  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        c1, c2 = float(p["c1"]), float(p["c2"])
        y, z, _ = load_global_cci_pair(mkt, config.START, None)

        state = _assign_states(z[1:], c1, c2)
        dep = np.diff(y)
        x = y[:-1]
        rw = state == 0

        xs, ys = x[rw], dep[rw]
        n = len(xs)
        # intercept OLS on the middle band only - estimate.py's _ols_intercept
        sx, sy = xs.sum(), ys.sum()
        sxx, sxy = float(xs @ xs), float(xs @ ys)
        D = n * sxx - sx * sx
        beta = (n * sxy - sx * sy) / D
        alpha = (sy - beta * sx) / n
        resid = ys - alpha - beta * xs
        s2 = float(resid @ resid) / (n - 2)
        se = float(np.sqrt(s2 * n / D))
        t = beta / se
        # large-sample normal, consistent with _sig_marker (see drift_fdr.py notes)
        pv = 2.0 * sps.norm.sf(abs(t))
        half = 1.959963984540054 * se

        rows.append({
            "market": mkt, "country": MARKETS[mkt]["country"],
            "b_RW": round(float(beta), 6), "se_RW": round(se, 6),
            "t_RW": round(float(t), 3), "p_RW": round(float(pv), 4),
            "ci_lo": round(float(beta - half), 6),
            "ci_hi": round(float(beta + half), 6),
            "rw_pct": round(100.0 * rw.sum() / len(state), 2),
        })

    p_bh, _ = benjamini_hochberg([r["p_RW"] for r in rows], config.BH_Q)
    for r, pb in zip(rows, p_bh):
        r["q_BH"] = round(float(pb), 4)
        r["reject_RW_restriction"] = bool(pb <= config.BH_Q)

    neg = sum(1 for r in rows if r["b_RW"] < 0)
    pos = sum(1 for r in rows if r["b_RW"] > 0)
    raw = sum(1 for r in rows if r["p_RW"] < config.ALPHA)
    rej = sum(1 for r in rows if r["reject_RW_restriction"])
    med = float(np.median([r["b_RW"] for r in rows]))
    half_med = float(np.median([(r["ci_hi"] - r["ci_lo"]) / 2 for r in rows]))

    print("Round 10 Priority 3 - unrestricted middle band at FIXED thresholds\n")
    print(f"  b_RW sign split      : {neg} negative / {pos} positive")
    print(f"  significant raw p<.05: {raw}/{len(rows)}")
    print(f"  reject after BH      : {rej}/{len(rows)}")
    print(f"  median b_RW          : {med:.4f}")
    print(f"  median 95% half-width: {half_med:.4f}")
    if rej == 0:
        print("\n  No market rejects the imposed RW restriction, so the positional and")
        print("  validated RW shares coincide - this empirically justifies b_RW=0.")

    out = os.path.join(config.ensure_rebuilt_dir(), "rw_band_validation.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  -> rw_band_validation.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
