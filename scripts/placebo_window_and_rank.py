"""
Two follow-up checks requested against the placebo results:

1. Isolate the window-length effect from the trigger-choice effect for
   ATHEX/BIST100 by comparing each trigger's OWN full extent against the
   matched (shorter) window - reading placebo_1000.csv (full sample) and
   placebo_trigger_swap.csv (matched window) side by side. Note: "full sample
   under the country trigger" is not achievable - the Greek/Turkish CCI series
   genuinely do not exist before their own start dates (1997-07 / 2004-02),
   so the country side's "full extent" and "matched window" are the same
   thing by construction. Only the global side has a genuine full-vs-matched
   contrast.

2. Rank correlation between real_rss_impr and the placebo p-value (both
   dgp=block12) across all 23 panel markets in placebo_1000.csv, to state
   precisely how strongly "which markets clear the null" is explained by
   "which markets have the largest realized improvement."

Reads only already-committed exports; no new estimation.

Usage:
    python scripts/placebo_window_and_rank.py
"""
import csv
import os

from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORTS = os.path.join(ROOT, "results", "exports")
REBUILT = os.path.join(ROOT, "outputs", "rebuilt")


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def part1_window_effect():
    full = {r["market"]: r for r in read(os.path.join(EXPORTS, "placebo_1000.csv"))
             if r["dgp"] == "block12"}
    swap = {r["label"]: r for r in read(os.path.join(REBUILT, "placebo_trigger_swap.csv"))
            if r["dgp"] == "block12"}

    print("=" * 70)
    print("PART 1: window-length effect, isolated from trigger choice")
    print("=" * 70)
    panel = {r["market"]: r for r in read(os.path.join(ROOT, "results", "tables",
                                                          "global_cci_all_markets.csv"))}
    for market, code in [("athex", "GRC"), ("bist100", "TUR")]:
        f = full[market]
        g_full_p, g_full_T = f["emp_p_rss"], int(float(panel[market]["T"]))
        g_matched = swap[f"{market}_global"]
        c_matched = swap[f"{market}_country({code})"]
        print(f"\n{market.upper()}:")
        print(f"  global, full sample    (T={g_full_T}): emp_p={g_full_p}")
        print(f"  global, matched window (T={g_matched['T']}):        emp_p={g_matched['emp_p_rss']}")
        print(f"  country, matched window (=its own full extent, T={c_matched['T']}): "
              f"emp_p={c_matched['emp_p_rss']}")
        print(f"  -> window-length effect on global alone: "
              f"{g_full_p} (full) vs {g_matched['emp_p_rss']} (matched) - "
              f"same trigger, same market, only T changes")
        print(f"  -> trigger effect on the matched window: "
              f"{g_matched['emp_p_rss']} (global) vs {c_matched['emp_p_rss']} (country) - "
              f"same T, only trigger changes")


def part2_rank_correlation():
    block = {r["market"]: r for r in read(os.path.join(EXPORTS, "placebo_1000.csv"))
              if r["dgp"] == "block12"}
    panel = {r["market"]: r for r in read(os.path.join(ROOT, "results", "tables",
                                                          "global_cci_all_markets.csv"))}
    markets = list(block.keys())
    impr = [float(block[m]["real_rss_impr"]) for m in markets]
    emp_p = [float(block[m]["emp_p_rss"]) for m in markets]
    pctile = [float(block[m]["real_pctile"]) for m in markets]
    T = [float(panel[m]["T"]) for m in markets]

    rho_p, p_p = spearmanr(impr, emp_p)
    rho_pc, p_pc = spearmanr(impr, pctile)
    rho_T, p_T = spearmanr(T, emp_p)

    print("\n" + "=" * 70)
    print("PART 2: rank correlation, real RSS improvement AND T vs placebo p-value")
    print("=" * 70)
    print(f"n=23 markets, block12 null")
    print(f"Spearman(real_rss_impr, emp_p_rss)   = {rho_p:.3f}  (p={p_p:.2e})")
    print(f"Spearman(real_rss_impr, real_pctile) = {rho_pc:.3f}  (p={p_pc:.2e})")
    print(f"Spearman(T, emp_p_rss)               = {rho_T:.3f}  (p={p_T:.2e})")
    print(f"\nT range across panel: {min(T):.0f} to {max(T):.0f}")
    passers = sorted([m for m in markets if emp_p[markets.index(m)] < 0.05],
                      key=lambda m: emp_p[markets.index(m)])
    print(f"Passers (emp_p<0.05): " +
          ", ".join(f"{m} T={int(panel[m]['T'])}" for m in passers))
    print(f"\nSuggested Section 4.2 line: \"Across the panel, the block-null p-value "
          f"is strongly rank-correlated with the real RSS improvement itself "
          f"(Spearman rho={rho_p:.2f}, block12 null, n=23) - which markets clear the "
          f"placebo is explained substantially by which markets had the largest "
          f"in-sample regime-driven return difference, independent of any "
          f"trigger-specific or market-specific story.\"")


if __name__ == "__main__":
    part1_window_effect()
    part2_rank_correlation()
