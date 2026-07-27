"""
round09_diagnostics.py - Round 9 (P1, P2, P4, P6, P7, P8).

Rebuilds:
  regime_dynamics_audit.csv          P1 - state-conditional dynamics, rebasing-invariant
  efficiency_ranking_two_metrics.csv P2 - positional vs dynamics-validated efficiency
  episodes_exp_ex_afc.csv            P4a - the 7 Asian-crisis-onset spells
  horizon_test_rebuilt.csv           P4a/b/c - exclusion variants of the episode test
  horse_race_sort.csv                P4d - estimated thresholds vs fixed 10/90 bands
  cci_distribution_diagnostics.csv   P6a - national CCI shape and threshold percentiles
  percentile_trigger_run.csv         P6b - trigger transformed to percentile rank
  appendixC_with_se.csv              P7a - Fisher-z 90% CIs on the correlations
  cutoff_loco.csv                    P7b - is the 0.40 cutoff sharp?
  crisis_window_rho.csv              P7c - national-global co-movement in crises
  horizon_test_publag.csv            P8 - publication-lag robustness

Key findings these support, from results/exports/README.md Round 9:
  P1  explosive ROOT present in 0/23 (all beta_EXP < 0); MR correction in 11/23.
      The "explosive" label is a regime name, not an AR-root claim.
  P4c leave-episode-out: dropping 1997-2000 leaves exactly ONE episode. The
      discount is almost entirely a dot-com / Asian-crisis phenomenon.
  P7b the 0.40 cutoff is a practical screening value, not a sharp threshold -
      TUR and CZE have overlapping 90% CIs.

Usage:  python scripts/round09_diagnostics.py
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
from round01_horizon import load_all, spells, pooled    # noqa: E402
from round10_bootstrap import grid_bounds              # noqa: E402

Z90 = 1.6448536269514722
Z95 = 1.959963984540054
# AFC onset = spells starting in 1997 in an ASIAN market. Both conditions are
# needed: a bare 1997 filter also catches ibex35, smi, aex and merval, which are
# European/Latin American and have nothing to do with the Asian crisis. The seven
# that qualify are klci twse jkse set hscei lq45 kospi, mean excess -26.84pp.
AFC_YEARS = (1997,)
AFC_REGIONS = ("SE Asia", "Asia Pacific")


def panel():
    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def p1_regime_dynamics():
    """State-conditional mean return and drift/sd per regime, plus the two pass flags."""
    from estimate import _assign_states, standard_errors  # noqa: E402
    from global_cci_study import load_global_cci_pair     # noqa: E402

    rows = []
    for p in panel():
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        c1, c2 = float(p["c1"]), float(p["c2"])
        res = standard_errors(y, z, c1, c2, config.SPEC_SWITCHING_DRIFT, config.MODE)
        st = _assign_states(z[1:], c1, c2)
        dep, x = np.diff(y), y[:-1]

        rec = {"market": mkt, "country": p["country"]}
        for lab, name, akey, bkey, tkey in ((1, "MR", "alpha1", "beta1", "tstat1"),
                                            (0, "RW", "alpha2", "beta2", "tstat2"),
                                            (2, "EXP", "alpha3", "beta3", "tstat3")):
            m = st == lab
            n = int(m.sum())
            mean_ret = 100.0 * float(dep[m].mean()) if n else np.nan
            resid = dep[m] - (res[akey] + res[bkey] * x[m]) if n else np.array([])
            sd = 100.0 * float(resid.std(ddof=1)) if n > 1 else np.nan
            rec[f"{name}_mean_ret_pct"] = round(mean_ret, 4) if n else ""
            rec[f"{name}_resid_sd_pct"] = round(sd, 4) if n > 1 else ""
            rec[f"{name}_drift_sd"] = (round(res[akey] / (sd / 100.0), 3)
                                       if n > 1 and sd else "")
            if name in ("MR", "EXP"):
                t = res[tkey]
                rec[f"{name}_beta"] = round(res[bkey], 5)
                rec[f"{name}_t"] = round(float(t), 3) if np.isfinite(t) else ""
                if name == "MR":
                    # one-sided 5%: a genuine correction means beta significantly < 0
                    rec["MR_correction_pass"] = bool(np.isfinite(t) and t < -Z90)
                else:
                    # an explosive ROOT would need beta > 0; none is expected
                    rec["EXP_root_pass"] = bool(np.isfinite(t) and res[bkey] > 0
                                                and t > Z90)
        rec["n_EXP"] = int((st == 2).sum())
        rows.append(rec)

    mr_pass = sum(1 for r in rows if r["MR_correction_pass"])
    ex_pass = sum(1 for r in rows if r["EXP_root_pass"])
    med = float(np.median([r["EXP_mean_ret_pct"] for r in rows
                           if r["EXP_mean_ret_pct"] != ""]))
    print(f"  P1: MR correction in {mr_pass}/{len(rows)}; explosive ROOT in "
          f"{ex_pass}/{len(rows)}; median EXP state return {med:+.2f}%/mo")
    return rows


def p2_two_metrics():
    """Metric A = positional RW share; Metric B adds bands whose slope is insignificant."""
    from scipy import stats as sps                     # noqa: E402

    rows = []
    for p in panel():
        T = float(p["T"])
        a = 100.0 * float(p["n_rw"]) / T
        mr_sig = bool((p["sig_mr"] or "").strip() in ("**", "***"))
        ex_sig = bool((p["sig_ex"] or "").strip() in ("**", "***"))
        b = a
        if not mr_sig:
            b += 100.0 * float(p["n_mr"]) / T
        if not ex_sig:
            b += 100.0 * float(p["n_ex"]) / T
        rows.append({"market": p["market"], "country": p["country"],
                     "effA_rw_pct": round(a, 2),
                     "MR_slope_sig5": mr_sig, "EXP_slope_sig5": ex_sig,
                     "effB_dynvalid_pct": round(b, 2)})

    for key, rk in (("effA_rw_pct", "rankA"), ("effB_dynvalid_pct", "rankB")):
        order = sorted(rows, key=lambda r: -r[key])
        for i, r in enumerate(order, 1):
            r[rk] = i
    for r in rows:
        r["rank_move"] = r["rankB"] - r["rankA"]

    rho = sps.spearmanr([r["effA_rw_pct"] for r in rows],
                        [r["effB_dynvalid_pct"] for r in rows])
    print(f"  P2: mean A {np.mean([r['effA_rw_pct'] for r in rows]):.1f}% -> "
          f"mean B {np.mean([r['effB_dynvalid_pct'] for r in rows]):.1f}%, "
          f"Spearman {rho.statistic:.3f}")
    return rows


def p4_episodes_and_variants():
    """P4a/b/c - Asian-crisis onset spells and the exclusion variants."""
    from scipy import stats as sps                     # noqa: E402

    from market_config import MARKETS               # noqa: E402

    data = load_all()
    eps = []
    for mkt, d in data.items():
        if mkt in config.EXCLUDED_EXP_MARKETS:
            continue
        region = MARKETS.get(mkt, {}).get("region", "")
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        base = float(f[ok & (d["state"] == 0)].mean())
        for s, L in spells(d["state"] == 2):
            seg, so = f[s:s + L], ok[s:s + L]
            if so.any():
                yr = int(str(d["months"][s])[:4])
                eps.append({"market": mkt, "start": str(d["months"][s]),
                            "end": str(d["months"][s + L - 1]), "start_year": yr,
                            "length": L,
                            "excess_pp": round(float(seg[so].mean()) - base, 3),
                            "_region": region})

    def is_afc(e):
        return e["start_year"] in AFC_YEARS and e["_region"] in AFC_REGIONS

    afc = [{k: v for k, v in e.items() if k != "_region"} for e in eps if is_afc(e)]
    ex_afc = [e for e in eps if not is_afc(e)]

    def tt(rows_):
        a = np.array([r["excess_pp"] for r in rows_], dtype=float)
        r = sps.ttest_1samp(a, 0.0) if len(a) > 1 else None
        return (round(float(a.mean()), 3),
                round(float(r.pvalue), 4) if r is not None else "", len(a))

    variants = []
    m, pv, n = tt(eps)
    variants.append({"variant": "all_episodes", "mr": "", "episode_mean": m,
                     "episode_p": pv, "n_ep": n})
    m, pv, n = tt(ex_afc)
    variants.append({"variant": "ex_AFC_onset", "mr": "", "episode_mean": m,
                     "episode_p": pv, "n_ep": n})
    one = [e for e in eps if e["market"] not in ("ta35", "hscei", "lq45")]
    m, pv, n = tt(one)
    variants.append({"variant": "one_index_per_country", "mr": "", "episode_mean": m,
                     "episode_p": pv, "n_ep": n})
    era = [e for e in eps if not (1997 <= e["start_year"] <= 2000)]
    m, pv, n = tt(era) if len(era) > 1 else (
        round(float(np.mean([e["excess_pp"] for e in era])), 3) if era else "", "", len(era))
    variants.append({"variant": "leave_1997_2000_out", "mr": "", "episode_mean": m,
                     "episode_p": pv, "n_ep": n})

    print(f"  P4a: {len(afc)} AFC-onset spells (mean {np.mean([e['excess_pp'] for e in afc]):+.2f}pp); "
          f"excluding them leaves {len(ex_afc)} at {variants[1]['episode_mean']:+.2f}pp "
          f"p={variants[1]['episode_p']}")
    print(f"  P4c: dropping 1997-2000 leaves {len(era)} episode(s) "
          f"-> the discount is almost entirely that window")
    return afc, variants


def p4d_horse_race_sort():
    """P4d - RW share under estimated thresholds vs fixed 10th/90th CCI bands."""
    from scipy import stats as sps                     # noqa: E402

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    allz = []
    per = {}
    for p in panel():
        y, z, _ = load_global_cci_pair(p["market"], config.START, None)
        per[p["market"]] = (y, z, float(p["c1"]), float(p["c2"]),
                            100.0 * float(p["n_rw"]) / float(p["T"]))
        allz.append(np.asarray(z[1:], dtype=float))
    pool = np.concatenate(allz)
    lo, hi = float(np.percentile(pool, 10)), float(np.percentile(pool, 90))

    rows = []
    for mkt, (y, z, c1, c2, rw_est) in per.items():
        st = _assign_states(z[1:], lo, hi)
        rows.append({"market": mkt, "rw_pct_estimated": round(rw_est, 2),
                     "rw_pct_fixedbands": round(100.0 * float((st == 0).mean()), 2)})
    rho = sps.spearmanr([r["rw_pct_estimated"] for r in rows],
                        [r["rw_pct_fixedbands"] for r in rows])
    print(f"  P4d: pooled 10th/90th = {lo:.2f}/{hi:.2f}; RW-share rank corr "
          f"estimated vs fixed = {rho.statistic:.3f}")
    return rows


def p6_distribution_and_percentile():
    """P6a national CCI shape; P6b the trigger as a percentile rank."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS, OECD_CCI_MARKETS  # noqa: E402

    sent = os.path.join(config.DATA, "sentiment")
    pan = {p["market"]: p for p in panel()}

    diag = []
    for mkt in pan:
        code = OECD_CCI_MARKETS.get(mkt)
        f = os.path.join(sent, f"oecd_cci_{code}.csv") if code else None
        if not f or not os.path.exists(f):
            continue
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0].dropna()
        v = s.to_numpy(dtype=float)
        c1, c2 = float(pan[mkt]["c1"]), float(pan[mkt]["c2"])
        diag.append({
            "market": mkt, "code": code, "n": len(v),
            "sd": round(float(v.std(ddof=1)), 3),
            "skew": round(float(pd.Series(v).skew()), 3),
            "excess_kurt": round(float(pd.Series(v).kurt()), 3),
            "pctile_97.7": round(100.0 * float((v < 97.7).mean()), 1),
            "pctile_c1": round(100.0 * float((v < c1).mean()), 1),
            "pctile_c2": round(100.0 * float((v < c2).mean()), 1),
        })

    pct_rows = []
    for p in panel():
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        rank = pd.Series(z).rank(pct=True).to_numpy() * 100.0
        dep, x, zt = np.diff(y), y[:-1], rank[1:]
        zmin, zmax, mg = grid_bounds(rank)
        c1, c2 = optimal_from_parts(dep, x, zt, zmin, zmax, config.GRID_LENGTH, mg)
        st = _assign_states(zt, c1, c2)
        pct_rows.append({"market": mkt,
                         "rw_pct_level": round(100.0 * float(p["n_rw"]) / float(p["T"]), 2),
                         "rw_pct_percentile": round(100.0 * float((st == 0).mean()), 2)})
    from scipy import stats as sps                     # noqa: E402
    rho = sps.spearmanr([r["rw_pct_level"] for r in pct_rows],
                        [r["rw_pct_percentile"] for r in pct_rows])
    print(f"  P6: {len(diag)} national CCI series; percentile-trigger RW rank corr "
          f"{rho.statistic:.3f}")
    return diag, pct_rows


def p7_correlation_diagnostics():
    """P7a Fisher-z 90% CIs, P7b the 0.40 cutoff, P7c crisis-window co-movement."""
    import pandas as pd

    src = os.path.join(config.REBUILT, "appendixC_dcci_correlations.csv")
    if not os.path.exists(src):
        src = os.path.join(config.EXPORTS, "appendixC_dcci_correlations.csv")
    with open(src, encoding="utf-8-sig", newline="") as fh:
        base = list(csv.DictReader(fh))

    with_se, loco = [], []
    for b in base:
        r, n = float(b["corr_dCCI"]), int(float(b["n"]))
        se = 1.0 / math.sqrt(n - 3)
        zf = math.atanh(r)
        lo, hi = math.tanh(zf - Z90 * se), math.tanh(zf + Z90 * se)
        with_se.append({"code": b["code"], "country": b["country"], "n": n,
                        "start": b["start"], "end": b["end"],
                        "corr_dCCI": b["corr_dCCI"], "se_z": round(se, 4),
                        "ci90_lo": round(lo, 4), "ci90_hi": round(hi, 4)})
        loco.append({"code": b["code"], "country": b["country"], "n": n,
                     "corr_dCCI": b["corr_dCCI"], "ci90_lo": round(lo, 4),
                     "ci90_hi": round(hi, 4), "below_040": r < 0.40})

    g = pd.read_csv(config.GLOBAL_CCI, index_col=0, parse_dates=True).iloc[:, 0]
    g.index = pd.to_datetime(g.index).to_period("M")
    sent = os.path.join(config.DATA, "sentiment")
    from market_config import OECD_CCI_MARKETS         # noqa: E402
    windows = {"GFC_2008_09": ("2008-01", "2009-12"),
               "COVID_2020": ("2020-01", "2020-12"),
               "dotcom_2000_02": ("2000-01", "2002-12")}
    crisis = []
    pan = {p["market"] for p in panel()}
    for mkt in pan:
        code = OECD_CCI_MARKETS.get(mkt)
        f = os.path.join(sent, f"oecd_cci_{code}.csv") if code else None
        if not f or not os.path.exists(f):
            continue
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
        s.index = pd.to_datetime(s.index).to_period("M")
        j = pd.concat([g.rename("g"), s.rename("c")], axis=1).dropna().diff().dropna()
        rec = {"market": mkt, "code": code,
               "full": round(float(j["g"].corr(j["c"])), 3)}
        for name, (a, b2) in windows.items():
            w = j.loc[(j.index >= pd.Period(a, "M")) & (j.index <= pd.Period(b2, "M"))]
            rec[name] = round(float(w["g"].corr(w["c"])), 3) if len(w) > 5 else ""
        crisis.append(rec)

    med_full = float(np.median([c["full"] for c in crisis]))
    print(f"  P7: {len(with_se)} CIs; {sum(1 for r in loco if r['below_040'])} below 0.40; "
          f"crisis median full-sample rho {med_full:.2f}")
    return with_se, loco, crisis


def p8_publag():
    """P8 - lag the LABELS by 0/1/2 months and recompute the 12m band means."""
    from scipy import stats as sps                     # noqa: E402

    data = load_all()
    rows = []
    for lag in (0, 1, 2):
        buckets = {0: [], 1: [], 2: []}
        for mkt, d in data.items():
            st = d["state"]
            f = d["fwd"][12]
            ok = ~np.isnan(f)
            if lag:
                # the label for month t is only known at t+lag, so shift forward and
                # drop the first `lag` months rather than padding them
                st = st[:-lag]
                f, ok = f[lag:], ok[lag:]
            for lab in (0, 1, 2):
                if lab == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                    continue
                sel = ok & (st == lab)
                if sel.any():
                    buckets[lab].append(f[sel])
        mr = np.concatenate(buckets[1])
        rw = np.concatenate(buckets[0])
        ex = np.concatenate(buckets[2])
        rows.append({"pub_lag_months": lag,
                     "MR_mean_pct": round(float(mr.mean()), 4),
                     "RW_mean_pct": round(float(rw.mean()), 4),
                     "EXP_mean_pct": round(float(ex.mean()), 4),
                     "n_MR": len(mr), "n_RW": len(rw), "n_EXP": len(ex),
                     "EXP_vs_RW_p": round(float(
                         sps.ttest_ind(ex, rw, equal_var=False).pvalue), 8)})
    print("  P8: 12m EXP mean by publication lag -> " +
          ", ".join(f"lag{r['pub_lag_months']} {r['EXP_mean_pct']:+.2f}" for r in rows))
    return rows


def write(name, rows):
    if not rows:
        return
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    print("Round 9 diagnostics\n")
    write("regime_dynamics_audit.csv", p1_regime_dynamics())
    write("efficiency_ranking_two_metrics.csv", p2_two_metrics())
    afc, variants = p4_episodes_and_variants()
    write("episodes_exp_ex_afc.csv", afc)
    write("horizon_test_rebuilt.csv", variants)
    write("horse_race_sort.csv", p4d_horse_race_sort())
    diag, pct = p6_distribution_and_percentile()
    write("cci_distribution_diagnostics.csv", diag)
    write("percentile_trigger_run.csv", pct)
    wse, loco, crisis = p7_correlation_diagnostics()
    write("appendixC_with_se.csv", wse)
    write("cutoff_loco.csv", loco)
    write("crisis_window_rho.csv", crisis)
    write("horizon_test_publag.csv", p8_publag())


if __name__ == "__main__":
    main()
