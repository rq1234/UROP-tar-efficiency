"""
granger_appendices.py - Round 4 T5 plus the Appendix A / B / C tables.

Rebuilds:
  unrestricted_b2.csv                 T5 - middle band freed, thresholds RE-ESTIMATED
  appendixA_granger_global_cci.csv    A6 - the reverse-Granger screen, all 57 candidates
  appendixB_episode_coverage.csv      H1 - episode coverage by market
  appendixC_dcci_correlations.csv     G5 - national vs global CCI first-difference corr

All deterministic.

T5 vs Round 10 P3 - the distinction the draft currently blurs
------------------------------------------------------------
  T5 (here)        three free regimes, thresholds RE-ESTIMATED on the freed model.
                   README: "8/23 markets show a RW slope != 0 at 5%
                   (median b2 = -0.0087)". Cited in Section 7.2.
  Round 10 P3      middle band freed at the BASELINE thresholds, which stay fixed.
                   "6/23 raw, 0/23 after BH, median -0.0063". Cited in Section 4.

Both are correct; they answer different questions, and the slopes are identical
in only 13 of 23 markets. See VERIFICATION_REPORT.md entry C20x.

Usage:  python scripts/granger_appendices.py
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config                                          # noqa: E402
from fastgrid import fast_grid_rss_parts                # noqa: E402
from threshold_bootstrap import grid_bounds              # noqa: E402


def t5_unrestricted_b2():
    """Free the middle-band slope AND re-estimate thresholds (three free regimes)."""
    from global_cci_study import load_global_cci_pair  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, _ = load_global_cci_pair(mkt, config.START, None)
        z_min, z_max, min_gap = grid_bounds(z)

        dep, x = np.diff(y), y[:-1]
        zt = z[1:]
        # THREE FREE REGIMES: the middle band gets its own intercept OLS, and the
        # thresholds are re-optimised under THAT model. This is what makes T5
        # different from Round 10 P3 - for most markets the optimum is unchanged,
        # but for ipc and bovespa it moves substantially.
        grid = np.linspace(z_min, z_max, config.GRID_LENGTH)
        rss, i_idx, j_idx = fast_grid_rss_parts(dep, x, zt, grid, min_gap, rw_free=True)
        k = int(np.argmin(rss))
        c1, c2 = float(grid[i_idx[k]]), float(grid[j_idx[k]])
        rw = (zt >= c1) & (zt <= c2)
        xs, ys = x[rw], dep[rw]
        n = len(xs)
        sx, sy = xs.sum(), ys.sum()
        sxx, sxy = float(xs @ xs), float(xs @ ys)
        D = n * sxx - sx * sx
        beta = (n * sxy - sx * sy) / D
        alpha = (sy - beta * sx) / n
        resid = ys - alpha - beta * xs
        s2 = float(resid @ resid) / (n - 2)
        se = float(np.sqrt(s2 * n / D))
        t = beta / se

        rows.append({"market": mkt, "c1_free": round(c1, 2), "c2_free": round(c2, 2),
                     "b2_rw": round(float(beta), 6), "se_b2": round(se, 6),
                     "t_b2": round(float(t), 3), "n_rw": n,
                     "sig5": abs(t) > 1.959963984540054})

    sig = sum(1 for r in rows if r["sig5"])
    med = float(np.median([r["b2_rw"] for r in rows]))
    print(f"  T5: {sig}/{len(rows)} markets with RW slope != 0 at 5%, median b2 {med:.5f}")
    return rows


def appendix_a(n_lags=None):
    """A6 - reverse-Granger screen over the full 57-market candidate universe.

    n_lags defaults to config.N_LAGS_SCREEN (4); pass n_lags=8 for the
    eight-lag re-run cited at C2 (see scripts/granger_eightlag.py)."""
    from exogeneity import granger_f_test              # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS                  # noqa: E402

    n_lags = config.N_LAGS_SCREEN if n_lags is None else n_lags
    rows = []
    for mkt in MARKETS:
        rec = {"market": mkt, "country": MARKETS[mkt]["country"],
               "T": "", "F": "", "p": "", "gate": "NO_DATA",
               "n_lags": n_lags, "direction": "return->d(globalCCI)"}
        try:
            y, z, _ = load_global_cci_pair(mkt, config.START, None)
            if len(y) >= 10:
                F, p = granger_f_test(np.diff(np.asarray(z, dtype=float)),
                                      np.diff(np.asarray(y, dtype=float)),
                                      n_lags)[:2]
                rec.update({"T": float(len(y)), "F": round(float(F), 4),
                            "p": round(float(p), 4),
                            "gate": "FAIL" if p <= config.ALPHA else "PASS"})
        except Exception:                              # noqa: BLE001
            pass                                       # stays NO_DATA
        rows.append(rec)

    tally = {}
    for r in rows:
        tally[r["gate"]] = tally.get(r["gate"], 0) + 1
    print(f"  Appendix A: {len(rows)} candidates -> {tally}")
    return rows


def appendix_b():
    """H1 - share of each pre-designated episode's months in the expected band."""
    import pandas as pd

    from estimate import _assign_states                # noqa: E402
    from global_cci_study import load_global_cci_pair  # noqa: E402
    from market_config import MARKETS                  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        y, z, dates = load_global_cci_pair(mkt, config.START, None)
        state = _assign_states(z[1:], float(p["c1"]), float(p["c2"]))
        months = pd.to_datetime(dates[1:]).to_period("M")
        rec = {"market": mkt, "country": MARKETS[mkt]["country"]}
        # COVERAGE windows, not the verdict windows - see config for why these
        # differ and what goes wrong if they are conflated.
        for col, key in (("dot_com_EXP_pct", "dot_com"),
                         ("GFC_MR_pct", "gfc"),
                         ("COVID_MR_pct", "covid")):
            a, b, want = config.EPISODES_COVERAGE[key]
            sel = (months >= pd.Period(a, "M")) & (months <= pd.Period(b, "M"))
            rec[col] = (round(100.0 * float((state[sel] == want).mean()), 1)
                        if sel.any() else "")
        rows.append(rec)
    print(f"  Appendix B: {len(rows)} markets x 3 episodes")
    return rows


def appendix_c():
    """G5 - corr(d global CCI, d country CCI) in first differences.

    Adds China (B7's 26th row) from the Round 4 T3 live FRED fetch
    (outputs/rebuilt/cci_CHN_fetched.csv) using the identical join/diff/
    correlate logic as the other 25 countries. That file is a standing
    dependency from scripts/country_cci_episodes.py - if it isn't present
    yet (fresh checkout, run_all.py hasn't reached that stage), China's row
    is skipped rather than re-fetched here."""
    import pandas as pd

    from market_config import MARKETS, OECD_CCI_MARKETS  # noqa: E402

    # The export labels each code with the country of the FIRST market carrying
    # that code, falling back to the market key when the key is not in MARKETS.
    # That fallback is why CZE reads "px" and POL reads "wig20" - both are
    # dangling OECD_CCI_MARKETS keys with no MARKETS entry. Reproduced verbatim.
    label = {}
    for mkt_key, code_ in OECD_CCI_MARKETS.items():
        if code_ not in label:
            label[code_] = MARKETS.get(mkt_key, {}).get("country", mkt_key)

    gpath = config.GLOBAL_CCI
    g = pd.read_csv(gpath, index_col=0, parse_dates=True).iloc[:, 0]
    g.index = pd.to_datetime(g.index).to_period("M")

    def correlate(s, min_n=24):
        s.index = pd.to_datetime(s.index).to_period("M")
        j = pd.concat([g.rename("g"), s.rename("c")], axis=1).dropna()
        if len(j) < min_n:
            return None
        d = j.diff().dropna()
        return {"n": len(d), "start": str(j.index[0]), "end": str(j.index[-1]),
                "corr_dCCI": round(float(d["g"].corr(d["c"])), 4)}

    sent = os.path.join(config.DATA, "sentiment")
    rows = []
    seen = set()
    for _, code in OECD_CCI_MARKETS.items():
        if code in seen:
            continue
        seen.add(code)
        f = os.path.join(sent, f"oecd_cci_{code}.csv")
        if not os.path.exists(f):
            continue
        s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
        res = correlate(s)
        if res is None:
            continue
        rows.append({"code": code, "country": label.get(code, code),
                     "source": "OECD_CCI_MARKETS", **res})

    chn_path = os.path.join(config.ROOT, "outputs", "rebuilt", "cci_CHN_fetched.csv")
    if os.path.exists(chn_path):
        chn = pd.read_csv(chn_path, index_col=0, parse_dates=True).iloc[:, 0]
        res = correlate(chn)
        if res is not None:
            rows.append({"code": "CHN", "country": "China", "source": "FRED_live_R4T3", **res})
    else:
        print("  Appendix C: cci_CHN_fetched.csv not found - China row skipped "
              "(run country_cci_episodes.py's T3 first)")

    rows.sort(key=lambda r: r["corr_dCCI"])
    print(f"  Appendix C: {len(rows)} countries, corr range "
          f"{rows[0]['corr_dCCI']:.3f} to {rows[-1]['corr_dCCI']:.3f}")
    return rows


def write(name, rows):
    path = os.path.join(config.ensure_rebuilt_dir(), name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"    -> {name} ({len(rows)} rows)")


def main():
    print("Round 4 T5 + Appendices A/B/C - deterministic\n")
    write("unrestricted_b2.csv", t5_unrestricted_b2())
    write("appendixA_granger_global_cci.csv", appendix_a())
    write("appendixB_episode_coverage.csv", appendix_b())
    write("appendixC_dcci_correlations.csv", appendix_c())


if __name__ == "__main__":
    main()
