"""
config.py - every seed, constant and path the rebuilt analyses use.

Single source of truth. The lost scripts kept these inline, which is why
results/exports/README.md is the only record of some of them. Never hard-code
a seed or a cutoff in a round script: import it from here.

Provenance for each value is given in the comment beside it. Where a value was
recovered from results/exports/README.md rather than from surviving code, that
is stated explicitly.
"""

import os

# ---------------------------------------------------------------------------
# Paths. Everything is resolved from this file so scripts work from any cwd.
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
EXPORTS = os.path.join(RESULTS, "exports")          # READ-ONLY ground truth
TABLES = os.path.join(RESULTS, "tables")            # READ-ONLY ground truth
REBUILT = os.path.join(ROOT, "outputs", "rebuilt")  # everything new goes here

PANEL_CSV = os.path.join(TABLES, "global_cci_all_markets.csv")
MONTHLY_PANEL = os.path.join(DATA, "combined", "monthly_panel.csv")
GLOBAL_CCI = os.path.join(DATA, "sentiment", "global_cci_monthly.csv")

# ---------------------------------------------------------------------------
# Seeds. All three are recorded in results/exports/README.md; none of them
# survived in code, which is precisely how the reproducibility gap arose.
# ---------------------------------------------------------------------------
SEED_PLACEBO_T1 = 20260721   # Round 4 T1 placebo grid search (50 draws/market)
SEED_ROUND_8_10 = 20260722   # Round 8 permutation B=5000; Round 10 bootstrap B=1000
SEED_FIXED_LABEL_BLOCK = 12345   # fixed-label moving-block bootstrap (Round 1 note F4)

# ---------------------------------------------------------------------------
# Replication counts
# ---------------------------------------------------------------------------
B_BOOTSTRAP = 1000    # Round 10 Priority 1, full grid re-estimated per draw
B_PERMUTATION = 5000  # Round 8 Y2 circular-shift permutation
B_PLACEBO = 1000      # Round 10 Priority 9 (supersedes Round 4 T1's B=50)
B_PLACEBO_T1 = 50     # Round 4 T1 original - kept so T1 can be reproduced as run
B_CLUSTER_BOOT = 2000 # Round 7 X1 year-cluster bootstrap

# ---------------------------------------------------------------------------
# Sample and estimation constants (these DO survive in src/, mirrored here so
# the round scripts have one import; values cross-checked against the source)
# ---------------------------------------------------------------------------
START = "1990-01"          # src/global_cci_study.py:54
INSAMPLE_END = "2015-06"   # Option-B freeze point; Round 2 R4 flags it is not 2015-12
MIN_OBS = 340              # src/global_cci_study.py:368 - the gate that gives 23 markets
MIN_OBS_COUNTRY = 180      # src/country_cci_study.py:61

GRID_LENGTH = 100          # src/global_cci_study.py:110
MIN_GAP_FLOOR = 4          # src/estimate.py find_optimal_thresholds default
MIN_BAND_POINTS = 2.0      # min_gap enforces a 2.0-point band (global_cci_study.py:112)
GRID_SIGMA = 3.0           # bounds are mean +- 3 sigma (global_cci_study.py:108)

SPEC_SWITCHING_DRIFT = 1   # the paper's main specification
SPEC_CONSTANT_DRIFT = 2    # Round 8 Y4 fair comparison
SPEC_NO_DRIFT = 0          # Round 8 Y1 (produces degenerate thresholds)
MODE = "returns"

# ---------------------------------------------------------------------------
# Inference settings
# ---------------------------------------------------------------------------
BH_Q = 0.05                # Benjamini-Hochberg level (Rounds 6 and 10)
ALPHA = 0.05               # exogeneity screen and coefficient tests
N_LAGS_SCREEN = 4          # reverse-Granger lags (global_cci_study.py:168)
DK_LAGS = 11               # Driscoll-Kraay, statsmodels hac-groupsum (Round 1 note F5)
BLOCK_LENGTHS = (12, 24, 36)   # moving-block bootstrap block sizes
MIN_REGIME_PCT = (0.05, 0.10, 0.15)   # Round 10 Priority 2 trimming rules
MIN_REGIME_OBS = (20, 30, 40)         # Round 10 Priority 2 trimming rules

HORIZONS = (1, 3, 6, 12)   # forward-return horizons in months

# ---------------------------------------------------------------------------
# Market-level exclusions that change reported numbers. These were buried in
# private helpers; naming them here makes them visible and toggleable.
# ---------------------------------------------------------------------------
EXCLUDED_EXP_MARKETS = ("nikkei225",)  # src/horizon_test.py:145 - Japan's c2=99.87 is
# degenerate (61% of months would be EXP), so its EXP months are dropped from the
# POOLED EXP cell only; its MR and RW months are kept. Round 6 W2 reports both ways.

# Episode windows, copy-pasted seven times across the study modules. One copy.
EPISODES = {
    "dot_com": ("1997-01", "2001-12"),
    "gfc":     ("2007-07", "2009-12"),
    "covid":   ("2020-01", "2020-06"),
    "post22":  ("2022-01", "2023-06"),
}

# Tail-coverage rule behind Table 4.1's tail_coverage column. Recovered in
# Phase 0 by sweeping candidate rules: >1.5% yields exactly 20 both-tailed and
# drops precisely twse (1.7%) and klci (1.5%). See VERIFICATION_REPORT.md E3.
TAIL_COVERAGE_MIN_SHARE_PCT = 1.5


def ensure_rebuilt_dir():
    os.makedirs(REBUILT, exist_ok=True)
    return REBUILT
