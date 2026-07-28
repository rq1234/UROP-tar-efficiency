"""
raw_data_exports.py - the raw-data exports and the efficiency ranking.

Rebuilds:
  prices_monthly.csv            Item 1 - long-format month-end closes, all markets
  cci_series.csv                Item 1 - wide-format global + national CCI
  efficiency_ranking_fresh.csv  Block B - the 23-market panel sorted by RW share
  item4_country_cci_T_screen.csv Item 4 - T>=340 / T>=240 screen on country-CCI runs

All deterministic reshapes or sorts of committed data. No estimation.

Usage:  python scripts/raw_data_exports.py
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

import config  # noqa: E402


def prices_monthly():
    """Long format date,market,close from every eq_* column in the monthly panel."""
    import pandas as pd

    df = pd.read_csv(config.MONTHLY_PANEL, index_col=0, parse_dates=True)
    eq = [c for c in df.columns if c.startswith("eq_")]
    rows = []
    for c in sorted(eq, key=lambda x: x[3:]):        # export is ordered by market
        ser = df[c].dropna()
        mkt = c[3:]
        for d, v in ser.items():
            rows.append({"date": d.strftime("%Y-%m-%d"), "market": mkt,
                         "close": float(v)})
    print(f"  prices_monthly: {len(eq)} markets, {len(rows)} rows")
    return rows


def cci_series():
    """Wide format: global CCI plus every national series, snapped to month-end."""
    import pandas as pd

    from market_config import OECD_CCI_MARKETS  # noqa: E402

    g = pd.read_csv(config.GLOBAL_CCI, index_col=0, parse_dates=True).iloc[:, 0]
    g.index = pd.to_datetime(g.index).to_period("M")
    series = {"global_cci": g}

    sent = os.path.join(config.DATA, "sentiment")
    for code in dict.fromkeys(OECD_CCI_MARKETS.values()):
        f = os.path.join(sent, f"oecd_cci_{code}.csv")
        if not os.path.exists(f):
            continue
        ser = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]
        ser.index = pd.to_datetime(ser.index).to_period("M")
        series[f"cci_{code}"] = ser

    # UNION index over every series - the export runs 1975-01..2026-05, wider than
    # the global series alone, because several national series start earlier.
    out = pd.DataFrame(series).sort_index()
    cols = ["global_cci"] + sorted(c for c in out.columns if c != "global_cci")
    out = out[cols]
    rows = []
    for per, r in out.iterrows():
        rec = {"date": per.to_timestamp(how="end").strftime("%Y-%m-%d")}
        for c in cols:
            v = r[c]
            rec[c] = "" if pd.isna(v) else round(float(v), 4)
        rows.append(rec)
    print(f"  cci_series: {len(cols)} series, {len(rows)} months")
    return rows


def efficiency_ranking_fresh():
    """Block B - the panel sorted by RW share, with region and class attached."""
    from market_config import MARKETS  # noqa: E402

    with open(config.PANEL_CSV, encoding="utf-8-sig", newline="") as fh:
        panel = list(csv.DictReader(fh))

    rows = []
    for p in panel:
        mkt = p["market"]
        T = float(p["T"])
        m = MARKETS.get(mkt, {})
        rows.append({
            "market": mkt, "country": p["country"],
            "region": m.get("region", ""), "market_class": m.get("market_class", ""),
            "T": int(T),
            "c1": p["c1"], "c2": p["c2"],
            "rw_pct": round(100.0 * float(p["n_rw"]) / T, 2),
            "mr_pct": round(100.0 * float(p["n_mr"]) / T, 2),
            "exp_pct": round(100.0 * float(p["n_ex"]) / T, 2),
            "beta_mr": p["beta_mr"], "se_mr": p["se_mr"], "sig_mr": p["sig_mr"],
            "beta_ex": p["beta_ex"], "se_ex": p["se_ex"], "sig_ex": p["sig_ex"],
            "dc_exp": p["dc_exp"], "gfc_mr": p["gfc_mr"], "covid_mr": p["covid_mr"],
            "current_cci": p["current_cci"], "current_regime": p["current_regime"],
            "verdict": p["verdict"],
        })
    rows.sort(key=lambda r: -r["rw_pct"])
    print(f"  efficiency_ranking_fresh: {len(rows)} markets, top = {rows[0]['market']} "
          f"({rows[0]['rw_pct']}%)")
    return rows


def item4_screen():
    """Item 4 - apply the T gates to the country-CCI (mixed trigger) runs."""
    path = os.path.join(config.TABLES, "mixed_trigger_results.csv")
    if not os.path.exists(path):
        print("  item4: mixed_trigger_results.csv absent - skipped")
        return None
    with open(path, encoding="utf-8-sig", newline="") as fh:
        src = list(csv.DictReader(fh))

    rows = []
    for r in src:
        # the column is trigger_type, with value "country" for country-CCI runs
        if (r.get("trigger_type") or "").strip().lower() != "country":
            continue
        T = float(r.get("T") or 0)
        rows.append({
            "market": r["market"], "country": r.get("country", ""), "T": int(T),
            "pct_MR": r.get("pct_MR", ""), "pct_RW": r.get("pct_RW", ""),
            "pct_EXP": r.get("pct_EXP", ""),
            "passes_T340": T >= config.MIN_OBS, "passes_T240": T >= 240,
        })
    print(f"  item4: {len(rows)} country-CCI markets, "
          f"{sum(1 for r in rows if r['passes_T340'])} pass T>=340")
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
    print("Round 1 data exports + efficiency ranking\n")
    write("prices_monthly.csv", prices_monthly())
    write("cci_series.csv", cci_series())
    write("efficiency_ranking_fresh.csv", efficiency_ranking_fresh())
    write("item4_country_cci_T_screen.csv", item4_screen())


if __name__ == "__main__":
    main()
