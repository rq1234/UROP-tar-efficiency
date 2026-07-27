"""
round07_dependence.py - Round 7 (X1, X4, X6, X7, X8) and the episode dependence tests.

Rebuilds:
  episode_dep_corrected.csv        X1 - the episode test under three dependence corrections
  matched_window_localisation.csv  X4 - Greece and Turkey on MATCHED windows
  kappa_stability.csv              X6 - chance-corrected Option A vs B agreement
  drift_variance_ratio.csv         X7 - drift-to-volatility ratio by regime
  rho_confidence_intervals.csv     X8 - Fisher-z CIs on the national-global correlations

Why these matter, from results/exports/README.md Round 7:

  X1  The 30 episodes sit in only 5 calendar-year clusters (29 of them in
      1997-2000). Even the most conservative correction - collapsing to those 5
      years - keeps the discount significant: mean -18.31pp, t=-3.16, p=0.034.
      "This is the robust inference for the explosive discount."
  X4  On the SAME 240-month window as the country run, Turkey's global and
      country splits are nearly identical (6/38/56 vs 7/45/48), so the paper's
      Turkey localisation claim is mostly a WINDOW effect. Greece is different
      (7/83/10 vs 44/31/25) and its claim holds.
  X6  Chance-corrected, MCSI is MORE stable than the CCI (kappa 0.944 vs 0.740),
      which undercuts leaning on raw agreement percentages.
  X7  Reported WITH the caveat that alpha is log-price-level dependent, so these
      cross-market ratios are inflated and are not a clean statistic.
  X8  Turkey rho=0.376 [0.26,0.48] and Czechia 0.415 [0.32,0.50] OVERLAP, so the
      0.04 "gap" behind the 0.40 screening cutoff is within sampling error.

Usage:  python scripts/round07_dependence.py
"""

import csv
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                                          # noqa: E402
from round01_horizon import load_all, spells           # noqa: E402
from round10_bootstrap import grid_bounds              # noqa: E402


def x1_episode_dep_corrected():
    """Episode excess under year-cluster-robust, cluster-bootstrap and year-collapsed."""
    from scipy import stats as sps                     # noqa: E402

    data = load_all()
    eps = []
    for mkt, d in data.items():
        if mkt in config.EXCLUDED_EXP_MARKETS:
            continue
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        rw = ok & (d["state"] == 0)
        base = float(f[rw].mean())
        for s, L in spells(d["state"] == 2):
            seg, segok = f[s:s + L], ok[s:s + L]
            if segok.any():
                eps.append({"year": int(str(d["months"][s])[:4]),
                            "excess": float(seg[segok].mean()) - base})

    exc = np.array([e["excess"] for e in eps])
    years = np.array([e["year"] for e in eps])
    uy = sorted(set(years.tolist()))

    # (a) year-cluster-robust t: cluster-robust SE of the mean
    k = len(uy)
    means = np.array([exc[years == y].mean() for y in uy])
    counts = np.array([(years == y).sum() for y in uy], dtype=float)
    gbar = exc.mean()
    # CR1 variance of the overall mean with clusters as the unit of resampling
    num = float(np.sum(counts ** 2 * (means - gbar) ** 2))
    se_cr = math.sqrt(num * k / max(k - 1, 1)) / counts.sum()
    t_cr = gbar / se_cr
    p_cr = 2.0 * sps.t.sf(abs(t_cr), df=k - 1)

    # (b) year cluster bootstrap
    rng = np.random.default_rng(config.SEED_ROUND_8_10)
    boot = []
    for _ in range(config.B_CLUSTER_BOOT):
        pick = rng.integers(0, k, size=k)
        vals = np.concatenate([exc[years == uy[i]] for i in pick])
        boot.append(vals.mean())
    boot = np.asarray(boot)
    t_cb = gbar / boot.std(ddof=1)
    p_cb = 2.0 * float(np.mean(boot - boot.mean() >= abs(gbar)))

    # (c) year-collapsed: one observation per calendar year, the most conservative
    tt = sps.ttest_1samp(means, 0.0)

    rows = [
        {"method": "year_cluster_robust", "t": round(float(t_cr), 3),
         "p": round(float(p_cr), 4), "clusters": k},
        {"method": "year_cluster_bootstrap", "t": round(float(t_cb), 3),
         "p": round(float(p_cb), 4), "clusters": k},
        {"method": "year_collapsed", "t": round(float(tt.statistic), 3),
         "p": round(float(tt.pvalue), 4), "clusters": k},
    ]
    print(f"  X1: {len(eps)} episodes in {k} year clusters {uy}")
    print(f"      year-collapsed mean {means.mean():+.2f}pp  t={tt.statistic:.3f}  "
          f"p={tt.pvalue:.4f}   <- the conservative one, and it holds")
    return rows


def x4_matched_window():
    """Greece and Turkey: global vs country trigger on the SAME window."""
    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    import pandas as pd

    sent = os.path.join(config.DATA, "sentiment")
    rows = []
    for mkt, code in (("athex", "GRC"), ("bist100", "TUR")):
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates).to_period("M")
        cpath = os.path.join(sent, f"oecd_cci_{code}.csv")
        cs = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
        cs.index = pd.to_datetime(cs.index).to_period("M")

        keep = np.array([m in set(cs.index) for m in months])
        ym, zm, mm = y[keep], z[keep], months[keep]
        cm = cs.reindex(mm).to_numpy(dtype=float)

        rec = {"market": mkt, "window_start": str(mm[0]), "window_end": str(mm[-1]),
               "T_matched": len(ym) - 1}
        for tag, trig in (("global", zm), ("country", cm)):
            dep, x, zt = np.diff(ym), ym[:-1], trig[1:]
            zmin, zmax, mg = grid_bounds(trig)
            c1, c2 = optimal_from_parts(dep, x, zt, zmin, zmax, config.GRID_LENGTH, mg)
            st = _assign_states(zt, c1, c2)
            n = len(st)
            rec[f"{tag}_MR"] = round(100.0 * float((st == 1).sum()) / n, 1)
            rec[f"{tag}_RW"] = round(100.0 * float((st == 0).sum()) / n, 1)
            rec[f"{tag}_EXP"] = round(100.0 * float((st == 2).sum()) / n, 1)
        rows.append(rec)
        print(f"  X4 {mkt:<9} global {rec['global_MR']}/{rec['global_RW']}/{rec['global_EXP']}"
              f"   country {rec['country_MR']}/{rec['country_RW']}/{rec['country_EXP']}")
    return rows


def x6_kappa():
    """Cohen's kappa between Option A (full-sample) and Option B (frozen) labels."""
    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    import pandas as pd

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates).to_period("M")
        a = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))

        cut = pd.Period(config.INSAMPLE_END, "M")
        insample = np.array([m <= cut for m in months])
        yb, zb = y[insample], z[insample]
        zmin, zmax, mg = grid_bounds(zb)
        c1b, c2b = optimal_from_parts(np.diff(yb), yb[:-1], zb[1:], zmin, zmax,
                                      config.GRID_LENGTH, mg)
        b = _assign_states(z[1:], c1b, c2b)

        agree = float((a == b).mean())
        pe = sum(float((a == k).mean()) * float((b == k).mean()) for k in (0, 1, 2))
        kappa = (agree - pe) / (1 - pe) if pe < 1 else 1.0
        rows.append({"market": mkt, "kappa_AB": round(kappa, 4),
                     "agree_pct": round(100.0 * agree, 2)})
    ks = [r["kappa_AB"] for r in rows]
    print(f"  X6: mean kappa {np.mean(ks):.3f}, mean agreement "
          f"{np.mean([r['agree_pct'] for r in rows]):.1f}%")
    return rows


def x7_drift_variance():
    """Drift-to-volatility ratio per regime. Reported WITH its caveat."""
    from estimate import _assign_states, standard_errors  # noqa: E402
    from global_cci_study import load_global_cci_pair     # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        c1, c2 = float(p["c1"]), float(p["c2"])
        res = standard_errors(y, z, c1, c2, config.SPEC_SWITCHING_DRIFT, config.MODE)
        st = _assign_states(z[1:], c1, c2)
        dep = np.diff(y)

        def ratio(alpha, mask):
            sd = float(dep[mask].std(ddof=1)) if mask.sum() > 1 else np.nan
            return (alpha / sd) if sd and not np.isnan(sd) and sd > 0 else np.nan

        exp_sd = float(dep[st == 2].std(ddof=1)) if (st == 2).sum() > 1 else np.nan
        rows.append({
            "market": mkt,
            "exp_drift": round(res["alpha3"], 4),
            "exp_sd": round(exp_sd, 4) if not np.isnan(exp_sd) else "",
            "exp_drift_sd": round(ratio(res["alpha3"], st == 2), 3)
            if not np.isnan(ratio(res["alpha3"], st == 2)) else "",
            "mr_drift_sd": round(ratio(res["alpha1"], st == 1), 3)
            if not np.isnan(ratio(res["alpha1"], st == 1)) else "",
            "rw_drift_sd": round(ratio(res["alpha2"], st == 0), 3)
            if not np.isnan(ratio(res["alpha2"], st == 0)) else "",
        })
    print("  X7: reported with the caveat that alpha is log-price-level dependent, "
          "so these ratios are inflated")
    return rows


def x8_rho_cis():
    """Fisher-z confidence intervals on the Appendix C correlations."""
    src = os.path.join(config.EXPORTS, "appendixC_dcci_correlations.csv")
    reb = os.path.join(config.REBUILT, "appendixC_dcci_correlations.csv")
    with open(reb if os.path.exists(reb) else src, encoding="utf-8-sig", newline="") as fh:
        base = list(csv.DictReader(fh))

    rows = []
    for b in base:
        r, n = float(b["corr_dCCI"]), int(float(b["n"]))
        zf = math.atanh(r)
        se = 1.0 / math.sqrt(n - 3)
        lo, hi = math.tanh(zf - 1.959963984540054 * se), math.tanh(zf + 1.959963984540054 * se)
        rows.append({**b, "ci_lo": round(lo, 4), "ci_hi": round(hi, 4)})

    tur = next((r for r in rows if r["code"] == "TUR"), None)
    cze = next((r for r in rows if r["code"] == "CZE"), None)
    if tur and cze:
        overlap = float(tur["ci_hi"]) >= float(cze["ci_lo"])
        print(f"  X8: TUR {tur['corr_dCCI']} [{tur['ci_lo']}, {tur['ci_hi']}]  "
              f"CZE {cze['corr_dCCI']} [{cze['ci_lo']}, {cze['ci_hi']}]  "
              f"overlap={overlap}")
    return rows


def write(name, rows):
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    print("Round 7 dependence corrections\n")
    write("episode_dep_corrected.csv", x1_episode_dep_corrected())
    write("matched_window_localisation.csv", x4_matched_window())
    write("kappa_stability.csv", x6_kappa())
    write("drift_variance_ratio.csv", x7_drift_variance())
    write("rho_confidence_intervals.csv", x8_rho_cis())


if __name__ == "__main__":
    main()
