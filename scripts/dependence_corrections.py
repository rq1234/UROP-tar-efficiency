"""
dependence_corrections.py - Round 7 (X1-X4, X6-X8) and the episode dependence tests.
X5 is deferred - see the note by main().

Rebuilds:
  episode_dep_corrected.csv        X1 - the episode test under three dependence corrections
  oos_exp_dep_corrected.csv        X2 - post-2015 OOS EXP-RW gap, dependence-corrected
  horserace_label_vs_trailing.csv  X3 - does the label add info beyond trailing 12m return?
  matched_window_localisation.csv  X4 - Greece and Turkey on MATCHED windows
  kappa_stability.csv              X6 - chance-corrected Option A vs B agreement
  drift_variance_ratio.csv         X7 - drift-to-volatility ratio by regime
  rho_confidence_intervals.csv     X8 - Fisher-z CIs on the national-global correlations

Why these matter, from results/exports/README.md Round 7:

  X1  The 30 episodes sit in only 5 calendar-year clusters (29 of them in
      1997-2000). Even the most conservative correction - collapsing to those 5
      years - keeps the discount significant: mean -18.31pp, t=-3.16, p=0.034.
      "This is the robust inference for the explosive discount."
  X2  The 76 post-2015 EXP months come from only 4 years and 4 markets. Gap
      -9.84pp, but moving-block bootstrap p=0.22, DK p=0.19 - the post-2015
      OOS result does NOT survive dependence correction; report as suggestive.
  X3  DECISIVE horse race: EXP coef -14.07(a) -> -14.06(c) when trailing 12m
      return is added [ratio 1.00]; trailing itself is insignificant (p=0.55).
      CAVEAT: under DK the pooled monthly EXP effect is only marginal (p=0.057)
      with or without trailing - contribution 3 should rest on X1, not this.
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

Usage:  python scripts/dependence_corrections.py
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
from horizon_episodes import load_all, spells           # noqa: E402
from threshold_bootstrap import grid_bounds              # noqa: E402


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


def _pooled_with_trailing():
    """Per-market state, 12m forward return, 12m trailing (past) return, global
    CCI trigger level and month ordinal, aligned - the common input to X2/X3."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    data = {}
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        state = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))
        logp = y[1:]
        zt = z[1:]
        months = pd.to_datetime(dates[1:]).to_period("M")
        h = 12
        fwd = np.full(len(state), np.nan)
        fwd[:-h] = 100.0 * (logp[h:] - logp[:-h])
        trail = np.full(len(state), np.nan)
        trail[h:] = 100.0 * (logp[h:] - logp[:-h])
        data[mkt] = {"state": state, "fwd12": fwd, "trail12": trail, "z": zt,
                     "months": months, "t": np.asarray([m.ordinal for m in months])}
    return data


def _pooled_optionB():
    """Per-market Option B (frozen at INSAMPLE_END) state, 12m forward return
    and month, for the whole sample - X2/R4d both classify the post-2015 OOS
    window this way, not with the panel's Option A (full-sample) thresholds."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts             # noqa: E402
    from global_cci_study import load_global_cci_pair   # noqa: E402
    from threshold_bootstrap import grid_bounds            # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    cut = pd.Period(config.INSAMPLE_END, "M")
    data = {}
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates).to_period("M")
        insample = np.asarray(months <= cut)
        yb, zb = y[insample], z[insample]
        zmin, zmax, mg = grid_bounds(zb)
        c1b, c2b = optimal_from_parts(np.diff(yb), yb[:-1], zb[1:], zmin, zmax,
                                      config.GRID_LENGTH, mg)
        state = _assign_states(z[1:], c1b, c2b)
        logp = y[1:]
        mm = months[1:]
        h = 12
        fwd = np.full(len(state), np.nan)
        fwd[:-h] = 100.0 * (logp[h:] - logp[:-h])
        data[mkt] = {"state": state, "fwd12": fwd, "months": mm,
                     "t": np.asarray([m.ordinal for m in mm])}
    return data, cut


def x2_oos_exp_dep_corrected():
    """OOS (post-INSAMPLE_END) EXP-RW gap under Option B, dependence-corrected.

    Uses frozen (Option B) thresholds, matching R4d's OOS classification
    (pool_exclusions_optionab.py), not the panel's Option A full-sample c1/c2 -
    the full-sample thresholds give almost no post-2015 EXP months at all,
    since most markets' last-ever EXP month is ~2000-2001 (expn_check.csv).
    No EXCLUDED_EXP_MARKETS zeroing here: nikkei225's Option B thresholds are
    not degenerate the way its Option A ones are, and get 0 post-2015 EXP
    months on their own.
    """
    from threshold_bootstrap import moving_block_indices  # noqa: E402
    from min_regime_wald_recursive import dk_ols                # noqa: E402
    from scipy import stats as sps                      # noqa: E402

    data, cut = _pooled_optionB()

    ys, Xs, ts, years, mkts_exp = [], [], [], set(), set()
    n_exp = n_rw = 0
    for mkt, d in data.items():
        post = d["months"] > cut
        st, f, ok_t = d["state"][post], d["fwd12"][post], d["t"][post]
        mm = d["months"][post]
        ok = ~np.isnan(f)
        exp = (st == 2).astype(float)
        n_exp += int(exp[ok].sum())
        n_rw += int((ok & (st == 0)).sum())
        years |= {int(str(m)[:4]) for m, e in zip(mm[ok], exp[ok]) if e}
        if exp[ok].sum():
            mkts_exp.add(mkt)
        keep = ok & ((st == 0) | (st == 2))
        ys.append(f[keep])
        Xs.append(np.column_stack([np.ones(keep.sum()), exp[keep]]))
        ts.append(ok_t[keep])

    y, X, t = np.concatenate(ys), np.vstack(Xs), np.concatenate(ts)
    gap = float(y[X[:, 1] == 1].mean() - y[X[:, 1] == 0].mean())
    m = dk_ols(y, X, t)
    dk_coef, dk_p = float(m.params[1]), float(m.pvalues[1])

    rng = np.random.default_rng(config.SEED_ROUND_8_10)
    months = np.unique(t)
    ests = []
    for _ in range(500):
        idx = moving_block_indices(len(months), 24, rng)
        keep = np.isin(t, months[idx])
        if keep.sum() < 30 or X[keep, 1].std() == 0:
            continue
        ests.append(float(np.linalg.lstsq(X[keep], y[keep], rcond=None)[0][1]))
    a = np.asarray(ests)
    block_se = float(a.std(ddof=1)) if a.size > 2 else float("nan")
    block_p = float(2 * sps.norm.sf(abs(gap) / block_se)) if block_se and np.isfinite(block_se) else ""

    print(f"  X2: OOS gap {gap:+.3f}pp  DK p={dk_p:.4f}  block SE={block_se:.3f} "
          f"p={block_p if block_p == '' else round(block_p, 4)}  "
          f"({n_exp} EXP obs, {len(years)} years, {len(mkts_exp)} markets)")
    return [
        {"stat": "gap_pp", "value": round(gap, 3)},
        {"stat": "DK_EXP_coef", "value": round(dk_coef, 3)},
        {"stat": "DK_p", "value": round(dk_p, 4)},
        {"stat": "block_boot_SE", "value": round(block_se, 3) if np.isfinite(block_se) else ""},
        {"stat": "block_boot_p", "value": round(block_p, 4) if block_p != "" else ""},
        {"stat": "n_EXP", "value": float(n_exp)},
        {"stat": "n_RW", "value": float(n_rw)},
        {"stat": "years", "value": float(len(years))},
        {"stat": "markets", "value": float(len(mkts_exp))},
    ]


def x3_horserace_label_vs_trailing():
    """Does the regime label carry information beyond the trailing 12m return?
    Four DK regressions of pooled fwd12: (a) regime dummies only, (b) trailing
    only, (c) both, (c2) continuous CCI level (standardised) + trailing."""
    from min_regime_wald_recursive import dk_ols  # noqa: E402

    data = _pooled_with_trailing()
    ys, mrs, exps, trails, zs, ts = [], [], [], [], [], []
    for mkt, d in data.items():
        f, tr, st, z, t = d["fwd12"], d["trail12"], d["state"], d["z"], d["t"]
        ok = ~np.isnan(f) & ~np.isnan(tr)
        exp = (st[ok] == 2).astype(float)
        if mkt in config.EXCLUDED_EXP_MARKETS:
            exp[:] = 0.0
        ys.append(f[ok]); mrs.append((st[ok] == 1).astype(float)); exps.append(exp)
        trails.append(tr[ok]); zs.append(z[ok]); ts.append(t[ok])

    y = np.concatenate(ys); mr = np.concatenate(mrs); ex = np.concatenate(exps)
    trail = np.concatenate(trails); z = np.concatenate(zs); t = np.concatenate(ts)
    zlev = (z - z.mean()) / z.std(ddof=1)
    ones = np.ones(len(y))

    def r2(m, yv):
        rss = float((m.resid ** 2).sum())
        tss = float(((yv - yv.mean()) ** 2).sum())
        return 1.0 - rss / tss if tss else float("nan")

    rows = []
    Xa = np.column_stack([ones, mr, ex])
    ma = dk_ols(y, Xa, t)
    ra = round(r2(ma, y), 4)
    for term, i in (("MR", 1), ("EXP", 2)):
        rows.append({"model": "a_regime_only", "term": term,
                     "coef": round(float(ma.params[i]), 4),
                     "dk_p": round(float(ma.pvalues[i]), 4), "R2": ra})

    Xb = np.column_stack([ones, trail])
    mb = dk_ols(y, Xb, t)
    rows.append({"model": "b_trailing_only", "term": "trail12",
                 "coef": round(float(mb.params[1]), 4),
                 "dk_p": round(float(mb.pvalues[1]), 4), "R2": round(r2(mb, y), 4)})

    Xc = np.column_stack([ones, mr, ex, trail])
    mc = dk_ols(y, Xc, t)
    rc = round(r2(mc, y), 4)
    for term, i in (("MR", 1), ("EXP", 2), ("trail12", 3)):
        rows.append({"model": "c_both", "term": term,
                     "coef": round(float(mc.params[i]), 4),
                     "dk_p": round(float(mc.pvalues[i]), 4), "R2": rc})

    Xc2 = np.column_stack([ones, zlev, trail])
    mc2 = dk_ols(y, Xc2, t)
    rc2 = round(r2(mc2, y), 4)
    for term, i in (("zlev", 1), ("trail12", 2)):
        rows.append({"model": "c2_cci_level", "term": term,
                     "coef": round(float(mc2.params[i]), 4),
                     "dk_p": round(float(mc2.pvalues[i]), 4), "R2": rc2})

    a_exp = next(r for r in rows if r["model"] == "a_regime_only" and r["term"] == "EXP")
    c_exp = next(r for r in rows if r["model"] == "c_both" and r["term"] == "EXP")
    print(f"  X3: EXP coef {a_exp['coef']:+.2f} (a) -> {c_exp['coef']:+.2f} (c) "
          f"when trailing added [ratio {c_exp['coef'] / a_exp['coef']:.2f}]; "
          f"trailing p={next(r for r in rows if r['model']=='b_trailing_only')['dk_p']}")
    return rows


def x5_turkey_real_return():
    """Deflate bist100 by Turkish CPI (FRED TURCPIALLMINMEI) and re-run the
    same standalone country-CCI TAR as S1 (country_cci_episodes.py), on the real
    series. data/ is untouched - the fetched CPI is used in memory only."""
    import pandas as pd

    key = os.environ.get("FRED_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv  # noqa: E402
            load_dotenv()
            key = os.environ.get("FRED_API_KEY")
        except ImportError:
            pass
    if not key:
        print("  X5: skipped - no FRED_API_KEY configured (checked .env and "
              "the environment). See ASSUMPTIONS.md.")
        return []

    from collect_data import fetch_fred                             # noqa: E402
    from country_cci_study import load_cci_pair                     # noqa: E402
    from estimate import find_optimal_thresholds, standard_errors   # noqa: E402
    from global_cci_study import _grid_bounds, _sig_marker          # noqa: E402

    def fit(y, z, tag):
        z_min, z_max, gl, mg = _grid_bounds(z)
        opt = find_optimal_thresholds(y, z, z_min, z_max, gl, mg, 1, "returns")
        res = standard_errors(y, z, opt["c1"], opt["c2"], 1, "returns")
        T = res["n1"] + res["n2"] + res["n3"]
        row = {"basis": tag, "cpi_series": "TURCPIALLMINMEI" if tag == "real_CPI" else "-",
               "trigger": "cci_TUR", "T": T,
               "c1": round(opt["c1"], 3), "c2": round(opt["c2"], 3),
               "MR_pct": round(100.0 * res["n1"] / T, 1),
               "RW_pct": round(100.0 * res["n2"] / T, 1),
               "EXP_pct": round(100.0 * res["n3"] / T, 1),
               "beta_ex": round(res["beta3"], 5), "sig_ex": _sig_marker(res.get("tstat3"))}
        print(f"  X5 {tag:<22} c1={row['c1']} c2={row['c2']}  "
              f"{row['MR_pct']}/{row['RW_pct']}/{row['EXP_pct']}  b_EXP={row['beta_ex']}")
        return row

    y_nom, z, dates = load_cci_pair("bist100", "TUR", start=config.START)
    nominal_row = fit(y_nom, z, "nominal_country(paper)")

    cpi = fetch_fred("cpi", "TURCPIALLMINMEI", key)["cpi"]
    cpi.index = cpi.index + pd.offsets.MonthEnd(0)
    dates_idx = pd.DatetimeIndex(dates)
    cpi_aligned = cpi.reindex(dates_idx)
    keep = ~cpi_aligned.isna().to_numpy()
    y_real = y_nom[keep] - np.log(cpi_aligned.to_numpy(dtype=float)[keep])
    real_row = fit(y_real, z[keep], "real_CPI")

    return [real_row, nominal_row]


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
    write("oos_exp_dep_corrected.csv", x2_oos_exp_dep_corrected())
    write("horserace_label_vs_trailing.csv", x3_horserace_label_vs_trailing())
    write("matched_window_localisation.csv", x4_matched_window())
    write("turkey_real_return.csv", x5_turkey_real_return())
    write("kappa_stability.csv", x6_kappa())
    write("drift_variance_ratio.csv", x7_drift_variance())
    write("rho_confidence_intervals.csv", x8_rho_cis())


if __name__ == "__main__":
    main()
