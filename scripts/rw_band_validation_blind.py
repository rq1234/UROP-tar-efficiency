"""
The price-blind version of the middle-band drift test (A4/C20).

WHY: rw_band_validation.py's "unrestricted slope" check reuses the SAME
(c1, c2) the RSS-minimizing grid search already chose - and that search
forces beta=0 for the RW state at every candidate boundary it evaluates
(src/estimate.py:129,156), so the boundary is partly optimized to make the
middle band look flat before the "unrestricted" re-test ever runs on it.
That's a real test (it isn't rigged to pass - 6/23 raw-reject), but it's a
test on a sample selected in part by the assumption being tested.

This version defines the middle band a different way, with no reference to
price behaviour at all: for EACH market independently, the band is
"trigger between that market's OWN 10th and 90th percentile" - a pure
property of the trigger's distribution for that market, using the same
10th/90th convention as A12's fixed-tail cutoffs, but computed per-market
rather than pooled across all 23 (A12's pooled cutoff isn't reusable as-is
for this purpose - it applies one shared pair of numbers to every market,
which is fine for A12's own tail-spread comparison but wrong here, since a
price-blind per-market band has to reflect each market's own trigger
distribution). No RSS fit, no reference to the price series, decides
anywhere in this step.

Then, exactly as rw_band_validation.py does, a genuinely free (alpha, beta)
OLS is run on that band's returns, and Benjamini-Hochberg is applied across
the 23 markets - same math, same thresholds, directly comparable to A4/C20.

Output: outputs/rebuilt/rw_band_validation_blind.csv

Usage:
    python scripts/rw_band_validation_blind.py
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                    # noqa: E402
from drift_fdr import benjamini_hochberg          # noqa: E402

PCTILE_LO, PCTILE_HI = 10, 90


def main():
    from scipy import stats as sps                     # noqa: E402
    from global_cci_study import load_global_cci_pair    # noqa: E402
    from market_config import MARKETS                    # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        zt = z[1:]  # aligned with dep/x below, same convention as gridsearch()

        # Price-blind band: this market's OWN trigger percentiles only -
        # no c1/c2 from any RSS fit, no reference to y/dep anywhere above this line.
        lo_cut = float(np.percentile(zt, PCTILE_LO))
        hi_cut = float(np.percentile(zt, PCTILE_HI))
        mid = (zt >= lo_cut) & (zt <= hi_cut)

        dep = np.diff(y)
        x = y[:-1]
        xs, ys = x[mid], dep[mid]
        n = len(xs)
        if n < 10:
            continue

        sx, sy = xs.sum(), ys.sum()
        sxx, sxy = float(xs @ xs), float(xs @ ys)
        D = n * sxx - sx * sx
        beta = (n * sxy - sx * sy) / D
        alpha = (sy - beta * sx) / n
        resid = ys - alpha - beta * xs
        s2 = float(resid @ resid) / (n - 2)
        se = float(np.sqrt(s2 * n / D))
        t = beta / se
        pv = 2.0 * sps.norm.sf(abs(t))
        half = 1.959963984540054 * se

        rows.append({
            "market": mkt, "country": MARKETS[mkt]["country"],
            "lo_cut": round(lo_cut, 3), "hi_cut": round(hi_cut, 3),
            "n_mid": n, "mid_pct": round(100.0 * n / len(zt), 2),
            "b_mid": round(float(beta), 6), "se_mid": round(se, 6),
            "t_mid": round(float(t), 3), "p_mid": round(float(pv), 4),
            "ci_lo": round(float(beta - half), 6), "ci_hi": round(float(beta + half), 6),
        })

    p_bh, _ = benjamini_hochberg([r["p_mid"] for r in rows], config.BH_Q)
    for r, pb in zip(rows, p_bh):
        r["q_BH"] = round(float(pb), 4)
        r["reject_flat_blind"] = bool(pb <= config.BH_Q)

    neg = sum(1 for r in rows if r["b_mid"] < 0)
    pos = sum(1 for r in rows if r["b_mid"] > 0)
    raw = sum(1 for r in rows if r["p_mid"] < config.ALPHA)
    rej = sum(1 for r in rows if r["reject_flat_blind"])
    med = float(np.median([r["b_mid"] for r in rows]))
    med_pct = float(np.median([r["mid_pct"] for r in rows]))

    print(f"Price-blind middle-band drift test | {PCTILE_LO}th/{PCTILE_HI}th percentile "
          f"per market, n={len(rows)} markets\n")
    print(f"  median band width: {med_pct:.1f}% of each market's own months "
          f"(vs the RSS-fit RW band, typically ~80-90%)")
    print(f"  b_mid sign split      : {neg} negative / {pos} positive")
    print(f"  significant raw p<.05 : {raw}/{len(rows)}")
    print(f"  reject after BH       : {rej}/{len(rows)}")
    print(f"  median b_mid          : {med:.4f}")
    print(f"\n  Compare directly to A4/C20 (RSS-fit band, same BH convention): "
          f"6/23 raw, 0/23 after BH")

    out = os.path.join(config.ensure_rebuilt_dir(), "rw_band_validation_blind.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  -> {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
