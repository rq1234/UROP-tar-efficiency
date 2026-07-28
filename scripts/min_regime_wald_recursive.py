"""
min_regime_wald_recursive.py - Round 10 Priorities 2, 4.1, 4.3, 5, 8.

Rebuilds:
  min_regime_trimming.csv   P2  - thresholds under six minimum-regime rules
  min_regime_summary.csv    P2  - and the pooled gaps / rank correlation per rule
  wald_tar_vs_fixed.csv     P4.1 - formal Wald: TAR high band == fixed above-90?
  recursive_horserace.csv   P4.3 - expanding-window labels, past data only
  publag_corrected.csv      P5  - publication lag with dependence corrections
  common_level_scale.csv    P8a - what a fixed CCI level means nationally
  normalized_local_runs.csv P8b - Greece/Turkey under normalised triggers

Key findings, from results/exports/README.md Round 10:

  P4.1 "b_EXP=-11.28 vs b_above90=-4.36, difference -6.92, but Var(diff)=113 (DK)
        -> Wald does NOT reject equality (DK p~0.5). So the earlier 'TAR beats the
        naive sort' does not survive the direct comparison the referee asked for."
  P2   All 23 markets stay feasible under every rule; the pooled EXP-RW gap
        attenuates but stays negative; the RW-share ranking correlation falls from
        0.84 to 0.25 as the constraint tightens.
  P8b  Turkey's RW share moves 42% -> 9% under percentile normalisation, partly
        because the fixed 2.0-point minimum band is not scale-invariant.

Driscoll-Kraay standard errors use statsmodels' `hac-groupsum` with 11 lags,
per Round 1 note F5.

Usage:  python scripts/min_regime_wald_recursive.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                                          # noqa: E402
from fastgrid import fast_grid_rss_parts               # noqa: E402
from horizon_episodes import load_all                   # noqa: E402
from threshold_bootstrap import grid_bounds, moving_block_indices  # noqa: E402


def panel():
    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def optimal_min_regime(dep, x, zt, z_min, z_max, min_gap, min_obs):
    """Grid optimum subject to every regime holding at least `min_obs` observations."""
    grid = np.linspace(z_min, z_max, config.GRID_LENGTH)
    rss, i_idx, j_idx = fast_grid_rss_parts(dep, x, zt, grid, min_gap)
    order = np.argsort(zt, kind="stable")
    zs = zt[order]
    kL = np.searchsorted(zs, grid, side="left")[i_idx]
    kR = np.searchsorted(zs, grid, side="right")[j_idx]
    n = len(zt)
    ok = (kL >= min_obs) & ((kR - kL) >= min_obs) & ((n - kR) >= min_obs)
    if not ok.any():
        return None
    idx = np.flatnonzero(ok)
    k = idx[int(np.argmin(rss[idx]))]
    return float(grid[i_idx[k]]), float(grid[j_idx[k]])


def p2_min_regime():
    from scipy import stats as sps                     # noqa: E402

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    data = load_all()
    base_rw = {m: 100.0 * float((d["state"] == 0).mean()) for m, d in data.items()}

    rules = [(f"pct{int(p * 100)}", p, None) for p in config.MIN_REGIME_PCT] + \
            [(f"obs{o}", None, o) for o in config.MIN_REGIME_OBS]

    trim, summary = [], []
    for name, pct, obs in rules:
        rw_now, feas, infeas = {}, 0, 0
        gaps = {"MR": [], "RW": [], "EXP": []}
        ep_hits = ep_tot = 0
        for p in panel():
            mkt = p["market"]
            y, z, _ = load_global_cci_pair(mkt, config.START, None)
            dep, x, zt = np.diff(y), y[:-1], z[1:]
            zmin, zmax, mg = grid_bounds(z)
            need = int(np.ceil(pct * len(zt))) if pct else obs
            got = optimal_min_regime(dep, x, zt, zmin, zmax, mg, need)
            if got is None:
                infeas += 1
                continue
            feas += 1
            c1, c2 = got
            st = _assign_states(zt, c1, c2)
            n = len(st)
            trim.append({"rule": name, "market": mkt,
                         "c1": round(c1, 3), "c2": round(c2, 3),
                         "MR_pct": round(100.0 * float((st == 1).mean()), 1),
                         "RW_pct": round(100.0 * float((st == 0).mean()), 1),
                         "EXP_pct": round(100.0 * float((st == 2).mean()), 1)})
            rw_now[mkt] = 100.0 * float((st == 0).mean())

            f = data[mkt]["fwd"][12]
            ok = ~np.isnan(f)
            for lab, key in ((1, "MR"), (0, "RW"), (2, "EXP")):
                if lab == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                    continue
                sel = ok & (st == lab)
                if sel.any():
                    gaps[key].append(f[sel])
            months = data[mkt]["months"]
            for i in np.flatnonzero(st == 2):
                ep_tot += 1
                if 1997 <= int(str(months[i])[:4]) <= 2000:
                    ep_hits += 1

        common = [m for m in rw_now if m in base_rw]
        rho = sps.spearmanr([base_rw[m] for m in common],
                            [rw_now[m] for m in common]).statistic if len(common) > 2 else ""
        rw_m = np.concatenate(gaps["RW"]).mean()
        summary.append({
            "rule": name, "n_feasible": feas, "n_infeasible": infeas,
            "spearman_vs_base": round(float(rho), 3) if rho != "" else "",
            "MR_RW_gap": round(float(np.concatenate(gaps["MR"]).mean() - rw_m), 2),
            "EXP_RW_gap": round(float(np.concatenate(gaps["EXP"]).mean() - rw_m), 2),
            "exp_ep_1997_2000": f"{ep_hits}/{ep_tot}",
        })
        print(f"  P2 {name:<7} feasible {feas}/23  rho {summary[-1]['spearman_vs_base']}  "
              f"EXP-RW {summary[-1]['EXP_RW_gap']}")
    return trim, summary


def dk_ols(y, X, groups, lags=None):
    """OLS with Driscoll-Kraay SEs (statsmodels hac-groupsum)."""
    import statsmodels.api as sm                       # noqa: E402

    lags = config.DK_LAGS if lags is None else lags
    m = sm.OLS(y, X).fit(cov_type="hac-groupsum",
                         cov_kwds={"time": np.asarray(groups), "maxlags": lags})
    return m


def p41_wald():
    """Formal Wald test that the TAR high band and the fixed above-90 band coincide.

    Manifest row P4d_horserace_fixedbands gives the exact regression:
        fwd12 ~ TAR(MR,EXP) + fixed CCI bands(<98.4, >101.4), DK
    i.e. FOUR dummies jointly - TAR_MR, TAR_EXP, belowP10, aboveP90 - not just the
    two high-band dummies. Fitting only tar_hi and pct_hi (the first attempt here)
    absorbs some of the TAR_EXP effect into the intercept and gives the wrong
    b_EXP. The fixed cutoffs are the POOLED 10th/90th percentile of the trigger
    across all markets, ~98.4 / 101.4 (see C30).
    """
    data = load_all()
    zpool = {}
    for p in panel():
        from global_cci_study import load_global_cci_pair  # noqa: E402
        _, z, _ = load_global_cci_pair(p["market"], config.START, None)
        zpool[p["market"]] = np.asarray(z[1:], dtype=float)
    lo_cut = float(np.percentile(np.concatenate(list(zpool.values())), 10))
    hi_cut = float(np.percentile(np.concatenate(list(zpool.values())), 90))

    rows_y, rows_X, times = [], [], []
    for mkt, d in data.items():
        z = zpool[mkt]
        f = d["fwd"][12]
        ok = ~np.isnan(f)
        tar_mr = (d["state"] == 1).astype(float)
        if mkt in config.EXCLUDED_EXP_MARKETS:
            tar_ex = np.zeros(len(f), dtype=float)
        else:
            tar_ex = (d["state"] == 2).astype(float)
        below_p10 = (z < lo_cut).astype(float)
        above_p90 = (z > hi_cut).astype(float)
        rows_y.append(f[ok])
        rows_X.append(np.column_stack([np.ones(ok.sum()), tar_mr[ok], tar_ex[ok],
                                       below_p10[ok], above_p90[ok]]))
        times.append(np.asarray([m.ordinal for m in d["months"]])[ok])

    y = np.concatenate(rows_y)
    X = np.vstack(rows_X)
    t = np.concatenate(times)
    m = dk_ols(y, X, t)
    # columns: 0=const, 1=TAR_MR, 2=TAR_EXP, 3=belowP10, 4=aboveP90
    b_tar, b_pct = float(m.params[2]), float(m.params[4])
    V = np.asarray(m.cov_params())
    var_diff = float(V[2, 2] + V[4, 4] - 2 * V[2, 4])
    wald = (b_tar - b_pct) ** 2 / var_diff
    from scipy import stats as sps                     # noqa: E402
    p_dk = float(sps.chi2.sf(wald, 1))
    print(f"      joint fit: TAR_MR {m.params[1]:+.3f} (p={m.pvalues[1]:.3f})  "
          f"belowP10 {m.params[3]:+.3f} (p={m.pvalues[3]:.3f})")

    # calendar-block bootstrap on the difference
    rng = np.random.default_rng(config.SEED_ROUND_8_10)
    months = np.unique(t)
    diffs = []
    for _ in range(500):
        idx = moving_block_indices(len(months), 24, rng)
        keep = np.isin(t, months[idx])
        if keep.sum() < 500:
            continue
        try:
            mb = dk_ols(y[keep], X[keep], t[keep])
            diffs.append(float(mb.params[2] - mb.params[4]))
        except Exception:                              # noqa: BLE001
            continue
    d_arr = np.asarray(diffs)
    block_se = float(d_arr.std(ddof=1)) if d_arr.size > 2 else float("nan")
    block_p = (float(2 * sps.norm.sf(abs(b_tar - b_pct) / block_se))
               if block_se and np.isfinite(block_se) else "")

    print(f"  P4.1 Wald: b_EXP {b_tar:.2f} vs above-90 {b_pct:.2f}, diff "
          f"{b_tar - b_pct:.2f}, Var {var_diff:.1f}, DK p={p_dk:.4f}")
    return [{"b_EXP": round(b_tar, 3), "b_above90": round(b_pct, 3),
             "diff": round(b_tar - b_pct, 3), "var_diff_DK": round(var_diff, 4),
             "cov_EXP_above": round(float(V[2, 4]), 4),
             "wald_chi2": round(float(wald), 3), "wald_p_DK": round(p_dk, 4),
             "block_SE": round(block_se, 3) if np.isfinite(block_se) else "",
             "block_p": round(block_p, 4) if block_p != "" else ""}]


def p43_recursive():
    """Expanding-window labels: thresholds and 10/90 cutoffs from PAST data only."""
    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    import pandas as pd

    # Labelling uses PAST DATA ONLY, but the evaluation window is COMMON across
    # markets (the export runs 2000-2025) and the 10/90 cutoffs come from the
    # POOLED cross-market trigger history up to that date, not from one market's
    # own past. A per-market expanding percentile never fires here, because the
    # global CCI peaks early in the sample and no later value exceeds it.
    RECURSIVE_START = pd.Period("2000-01", "M")

    series = {}
    for p in panel():
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates[1:]).to_period("M")
        logp = y[1:]
        h = 12
        fwd = np.full(len(months), np.nan)
        fwd[:-h] = 100.0 * (logp[h:] - logp[:-h])
        series[mkt] = {"dep": np.diff(y), "x": y[:-1], "zt": z[1:], "z": z,
                       "months": months, "fwd": fwd}

    all_months = sorted({m for s in series.values() for m in s["months"]
                         if m >= RECURSIVE_START})

    index = {mkt: {m: i for i, m in enumerate(s["months"])} for mkt, s in series.items()}

    # Pooled 10th/90th percentile of every market's trigger history up to each
    # month, computed ONCE per month rather than once per market-month. `pct`
    # uses the SAME 3-value coding as `tar` (0=middle, 1=low tail, 2=high
    # tail) - confirmed against the export: every (tar,pct) pair present is
    # one of the 7 combinations reachable from two independent 3-way splits
    # with no (1,2)/(2,1) crossover, and they sum to the full row count.
    cuts_lo, cuts_hi = {}, {}
    for m in all_months:
        past = [series[k]["zt"][:index[k][m]] for k in series
                if m in index[k] and index[k][m] > 0]
        if past:
            pooled = np.concatenate(past)
            cuts_lo[m] = float(np.percentile(pooled, 10))
            cuts_hi[m] = float(np.percentile(pooled, 90))
        else:
            cuts_lo[m] = cuts_hi[m] = np.nan

    rows = []
    for mkt, s in series.items():
        idx_of = index[mkt]
        for m in all_months:
            i = idx_of.get(m)
            # burn-in: need 120 months (10y) of the market's OWN history before the
            # first recursive label. Confirmed against the export: athex/bist100
            # (start 1997-08) both lose exactly 90 months versus the raw window,
            # and 30 (pre-window history) + 90 = 120; hangseng (start 1990-02, so
            # already has 120 months by the window start) loses none.
            if i is None or i < 120 or np.isnan(cuts_hi[m]):
                continue
            zmin, zmax, mg = grid_bounds(s["z"][:i + 1])
            try:
                c1, c2 = optimal_from_parts(s["dep"][:i], s["x"][:i], s["zt"][:i],
                                            zmin, zmax, config.GRID_LENGTH, mg)
            except Exception:                          # noqa: BLE001
                continue
            if np.isnan(s["fwd"][i]):
                continue          # export drops months with no 12m-forward data, not pad them
            zi = s["zt"][i]
            st = 1 if zi < c1 else (2 if zi > c2 else 0)
            if st == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                st = 0     # nikkei225's c2 is degenerate; EXP dropped, RW/MR kept (config.py)
            pc = 1 if zi < cuts_lo[m] else (2 if zi > cuts_hi[m] else 0)
            rows.append({"market": mkt,
                         "date": m.to_timestamp(how="end").strftime("%Y-%m-%d"),
                         "tar": st, "pct": pc,
                         "fwd12": round(float(s["fwd"][i]), 4)})
    tar = [r for r in rows if r["tar"] == 2 and r["fwd12"] != ""]
    pct = [r for r in rows if r["pct"] == 2 and r["fwd12"] != ""]
    print(f"  P4.3 recursive: {len(rows)} market-months; TAR high mean "
          f"{np.mean([r['fwd12'] for r in tar]):.2f}, fixed tail "
          f"{np.mean([r['fwd12'] for r in pct]):.2f}")
    return rows


def p5_publag():
    """Publication lag with DK and block-bootstrap p-values on the EXP-RW gap."""
    from scipy import stats as sps                     # noqa: E402

    data = load_all()
    rng = np.random.default_rng(config.SEED_ROUND_8_10)
    rows = []
    for lag in (0, 1, 2):
        ys, Xs, ts, thr_shift = [], [], [], []
        n_exp = 0
        for mkt, d in data.items():
            st, f = d["state"], d["fwd"][12]
            ok = ~np.isnan(f)
            if lag:
                st = st[:-lag]
                f, ok = f[lag:], ok[lag:]
                mn = d["months"][lag:]
            else:
                mn = d["months"]
            exp = (st == 2).astype(float)
            if mkt in config.EXCLUDED_EXP_MARKETS:
                exp[:] = 0.0
            n_exp += int(exp[ok].sum())
            ys.append(f[ok])
            Xs.append(np.column_stack([np.ones(ok.sum()), exp[ok]]))
            ts.append(np.asarray([m.ordinal for m in mn])[ok])
        y, X, t = np.concatenate(ys), np.vstack(Xs), np.concatenate(ts)
        m = dk_ols(y, X, t)
        gap, dk_p = float(m.params[1]), float(m.pvalues[1])

        bl = {}
        months = np.unique(t)
        for L in config.BLOCK_LENGTHS:
            est = []
            for _ in range(300):
                idx = moving_block_indices(len(months), L, rng)
                keep = np.isin(t, months[idx])
                if keep.sum() < 500:
                    continue
                Xk = X[keep]
                if Xk[:, 1].std() == 0:
                    continue
                est.append(float(np.linalg.lstsq(Xk, y[keep], rcond=None)[0][1]))
            a = np.asarray(est)
            bl[L] = (round(float(2 * sps.norm.sf(abs(gap) / a.std(ddof=1))), 4)
                     if a.size > 2 and a.std(ddof=1) > 0 else "")
        rows.append({"lag": lag, "EXP_RW_gap": round(gap, 3), "n_EXP": n_exp,
                     "DK_p": round(dk_p, 4),
                     "block12_p": bl.get(12, ""), "block24_p": bl.get(24, ""),
                     "block36_p": bl.get(36, ""),
                     "mean_thr_shift_vs_lag0": 0.0 if lag == 0 else ""})
        print(f"  P5 lag{lag}: gap {gap:+.2f}  DK p={dk_p:.4f}  blocks "
              f"{bl.get(12)}/{bl.get(24)}/{bl.get(36)}")
    return rows


def p8_scale():
    """P8a - where fixed CCI levels sit in each national distribution."""
    import pandas as pd

    from market_config import OECD_CCI_MARKETS         # noqa: E402

    sent = os.path.join(config.DATA, "sentiment")
    pan = sorted({p["market"] for p in panel()})
    rows = []
    for mkt in pan:
        code = OECD_CCI_MARKETS.get(mkt)
        f = os.path.join(sent, f"oecd_cci_{code}.csv") if code else None
        if not f or not os.path.exists(f):
            continue
        v = pd.read_csv(f, index_col=0).iloc[:, 0].dropna().to_numpy(dtype=float)
        mu, sd = float(v.mean()), float(v.std(ddof=1))
        rec = {"code": code, "mean": round(mu, 3), "sd": round(sd, 3),
               "skew": round(float(pd.Series(v).skew()), 3),
               "p10": round(float(np.percentile(v, 10)), 2),
               "p90": round(float(np.percentile(v, 90)), 2)}
        for lvl in (97.7, 98.4, 100.0, 101.4):
            rec[f"pct_{lvl}"] = round(100.0 * float((v < lvl).mean()), 1)
            rec[f"z_{lvl}"] = round((lvl - mu) / sd, 2)
        rows.append(rec)
    if rows:
        p100 = [r["pct_100.0"] for r in rows]
        print(f"  P8a: a fixed level of 100 sits at the "
              f"{min(p100):.0f}th-{max(p100):.0f}th national percentile")
    return rows


def p8_normalized():
    """P8b - Greece and Turkey re-estimated under z-score and percentile triggers."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from fastgrid import optimal_from_parts            # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402

    sent = os.path.join(config.DATA, "sentiment")
    rows = []
    for mkt, code in (("athex", "GRC"), ("bist100", "TUR")):
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        months = pd.to_datetime(dates).to_period("M")
        cs = pd.read_csv(os.path.join(sent, f"oecd_cci_{code}.csv"),
                         index_col=0, parse_dates=True).iloc[:, 0]
        cs.index = pd.to_datetime(cs.index).to_period("M")
        keep = np.array([m in set(cs.index) for m in months])
        ym = y[keep]
        cm = cs.reindex(months[keep]).to_numpy(dtype=float)

        for norm in ("amplitude_raw", "zscore", "percentile"):
            if norm == "amplitude_raw":
                trig = cm
            elif norm == "zscore":
                trig = (cm - cm.mean()) / cm.std(ddof=1)
            else:
                trig = pd.Series(cm).rank(pct=True).to_numpy() * 100.0
            dep, x, zt = np.diff(ym), ym[:-1], trig[1:]
            zmin, zmax, mg = grid_bounds(trig)
            c1, c2 = optimal_from_parts(dep, x, zt, zmin, zmax, config.GRID_LENGTH, mg)
            st = _assign_states(zt, c1, c2)
            rows.append({"market": mkt, "norm": norm,
                         "c1": round(c1, 3), "c2": round(c2, 3),
                         "MR_pct": round(100.0 * float((st == 1).mean()), 1),
                         "RW_pct": round(100.0 * float((st == 0).mean()), 1),
                         "EXP_pct": round(100.0 * float((st == 2).mean()), 1)})
    for r in rows:
        if r["market"] == "bist100":
            print(f"  P8b bist100 {r['norm']:<11} RW {r['RW_pct']}%")
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
    print("Round 10 remainder (P2, P4.1, P4.3, P5, P8)\n")
    trim, summary = p2_min_regime()
    write("min_regime_trimming.csv", trim)
    write("min_regime_summary.csv", summary)
    write("wald_tar_vs_fixed.csv", p41_wald())
    write("publag_corrected.csv", p5_publag())
    write("common_level_scale.csv", p8_scale())
    write("normalized_local_runs.csv", p8_normalized())
    write("recursive_horserace.csv", p43_recursive())


if __name__ == "__main__":
    main()
