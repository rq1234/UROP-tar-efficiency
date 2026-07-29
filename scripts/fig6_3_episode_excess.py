"""
Rebuild Figure 6.3 - "Explosive episodes as the unit of observation" - from
episodes_exp.csv. This figure's original generating script does not exist in
this repo (its embedded image carries the filename fig6_3_episodes.png in the
docx's own picture metadata, and that filename appears nowhere in this
codebase) - confirmed independently as data-correct (klci 1997 (3m) = -91.9pp,
athex 1998 (2m) = +41.6pp, matching episodes_exp.csv exactly, and the title's
t=-3.46/p=0.0017 matching paper_numbers_manifest.csv's S2_t_p), but with no
committed code path to regenerate it - a gap for any replication package.

One horizontal bar per episode (30 spells, Japan already excluded from
episodes_exp.csv), sorted by excess_pp descending (largest positive at top),
coloured by sign, with a dashed vertical line at the pooled mean.

Output: outputs/rebuilt/fig6_3_episode_excess.png

Usage:
    python scripts/fig6_3_episode_excess.py
"""
import csv
import os
import sys

import numpy as np
from scipy import stats as sps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORTS = os.path.join(ROOT, "results", "exports")
OUT_DIR = os.path.join(ROOT, "outputs", "rebuilt")


def main():
    with open(os.path.join(EXPORTS, "episodes_exp.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        r["excess_pp"] = float(r["excess_pp"])
        r["start_year"] = r["start"][:4]
        r["length_months"] = int(float(r["length_months"]))
        r["label"] = f"{r['market']} {r['start_year']} ({r['length_months']}m)"

    rows.sort(key=lambda r: r["excess_pp"], reverse=True)
    excess = np.array([r["excess_pp"] for r in rows])
    n_neg = int(np.sum(excess < 0))
    mean_excess = float(excess.mean())

    tt = sps.ttest_1samp(excess, 0.0)
    t_stat, p_val = float(tt.statistic), float(tt.pvalue)
    assert abs(t_stat - -3.46) < 0.01 and abs(p_val - 0.0017) < 0.0005, (
        f"t/p do not match the manuscript's stated t=-3.46, p=0.0017: got t={t_stat}, p={p_val}"
    )

    labels = [r["label"] for r in rows]
    colors = ["cornflowerblue" if v >= 0 else "firebrick" for v in excess]

    fig, ax = plt.subplots(figsize=(10, 9))
    y = np.arange(len(rows))[::-1]  # top of chart = first (largest) row
    ax.barh(y, excess, color=colors, zorder=3)
    ax.axvline(0, color="black", linewidth=1.0, zorder=4)
    ax.axvline(mean_excess, color="darkred", linestyle="--", linewidth=1.3,
               label=f"mean = {mean_excess:.1f}pp", zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Episode 12-month forward return minus own-market RW baseline (pp)")
    ax.set_title(
        f"Figure 6.3  Explosive episodes as the unit of observation "
        f"({len(rows)} episodes, Japan excluded)\n"
        f"{n_neg} of {len(rows)} episodes underperform their own market baseline; "
        f"t = {t_stat:.2f}, p = {p_val:.4f}",
        fontsize=12,
    )
    ax.grid(axis="x", linewidth=0.4, alpha=0.5, zorder=0)
    ax.legend(loc="lower right", framealpha=0.9)
    ax.margins(y=0.01)

    plt.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "fig6_3_episode_excess.png")
    plt.savefig(out, dpi=150)
    plt.close()

    print(f"{len(rows)} episodes, {n_neg} negative, mean={mean_excess:.3f}pp, "
          f"t={t_stat:.3f}, p={p_val:.4f}")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
