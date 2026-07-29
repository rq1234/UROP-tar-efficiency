"""
Ex-COVID sub-sample: does excluding 2020-01 through 2021-12 move the pooled
12-month forward means by band?

WHY: the Global OECD CCI fell sharply in early 2020, pushing those months
toward the low-sentiment (MR) band, while 12-month forward returns measured
from the March 2020 trough are very large and positive - exactly the pattern
that would inflate a pooled low-sentiment mean if enough of the 1,109 MR-band
observations are COVID months.

Reuses horizon_episodes.load_all() and its state/months/fwd arrays directly
(no re-derivation of states or forward returns) - only adds a calendar-month
exclusion mask before pooling, the same style of exclusion as the
Asian-crisis-onset check (C41 / regime_diagnostics.p4_episodes_and_variants),
applied here to the pooled month-level statistic (Table 6.1/A9/A10) rather
than the episode-level one.

Output: outputs/rebuilt/ex_covid_horizon_test.csv

Usage:
    python scripts/ex_covid_subsample.py
"""
import csv
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                          # noqa: E402
from horizon_episodes import load_all   # noqa: E402

EXCLUDE_START = "2020-01"
EXCLUDE_END = "2021-12"


def pooled_with_exclusion(data, h, exclude):
    """Same logic as horizon_episodes.pooled(), plus a calendar-month exclusion
    mask applied before bucketing by state. exclude=None keeps everything."""
    buckets = {0: [], 1: [], 2: []}
    excluded_low_count = 0
    for mkt, d in data.items():
        f = d["fwd"][h]
        ok = ~np.isnan(f)
        if exclude is None:
            keep = ok
        else:
            in_excl = np.array([exclude[0] <= m <= exclude[1] for m in d["months"]])
            excluded_low_count += int(np.sum(in_excl & (d["state"] == 1)))
            keep = ok & ~in_excl
        for lab in (0, 1, 2):
            if lab == 2 and mkt in config.EXCLUDED_EXP_MARKETS:
                continue
            sel = keep & (d["state"] == lab)
            if sel.any():
                buckets[lab].append(f[sel])
    return ({k: np.concatenate(v) if v else np.array([]) for k, v in buckets.items()},
            excluded_low_count)


def main():
    data = load_all()
    excl_window = (pd.Period(EXCLUDE_START, freq="M"), pd.Period(EXCLUDE_END, freq="M"))

    with_covid, _ = pooled_with_exclusion(data, 12, exclude=None)
    without_covid, excluded_low_n = pooled_with_exclusion(data, 12, exclude=excl_window)

    # How many index-months total (any band) fall in the excluded window, for context
    total_excluded = 0
    for mkt, d in data.items():
        in_excl = np.array([excl_window[0] <= m <= excl_window[1] for m in d["months"]])
        total_excluded += int(np.sum(in_excl))

    print(f"Excluded window: {EXCLUDE_START} to {EXCLUDE_END}")
    print(f"Total index-months in window (any band, any market): {total_excluded}")
    print(f"Of those, classified low-sentiment (MR): {excluded_low_n}\n")

    rows = []
    labels = {0: "RW", 1: "low (MR)", 2: "high (EXP)"}
    print(f"{'band':<12}{'with COVID mean':>18}{'n':>8}{'ex-COVID mean':>16}{'n':>8}")
    for lab in (1, 0, 2):
        m_with, n_with = float(with_covid[lab].mean()), len(with_covid[lab])
        m_without, n_without = float(without_covid[lab].mean()), len(without_covid[lab])
        print(f"{labels[lab]:<12}{m_with:>18.3f}{n_with:>8}{m_without:>16.3f}{n_without:>8}")
        rows.append({
            "band": labels[lab],
            "mean_with_covid_pct": round(m_with, 3), "n_with_covid": n_with,
            "mean_ex_covid_pct": round(m_without, 3), "n_ex_covid": n_without,
            "delta_pct": round(m_without - m_with, 3),
        })

    out = os.path.join(config.ensure_rebuilt_dir(), "ex_covid_horizon_test.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
