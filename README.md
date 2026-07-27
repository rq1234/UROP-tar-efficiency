# Cross-Market Efficiency via Threshold Autoregressions

Extends Ahmed & Satchell (2018) from 2 markets to a global cross-section by replacing the
US-specific sentiment trigger (Michigan CSI, VIX) with the **OECD global composite Consumer
Confidence Index** — a trigger plausibly exogenous to any single national market.

Market efficiency is modelled as **state-dependent**: the trigger `z(t)` partitions time into
three regimes, and the "proportion of time efficient" is the share of months in the middle one.

| Regime | Condition | Behaviour |
|---|---|---|
| Low / MR | `z < c1` | mean-reverting |
| **RW** | `c1 ≤ z ≤ c2` | random walk — **efficient** |
| High / EXP | `z > c2` | explosive |

**Sample cascade:** 57 candidate markets → 32 pass the reverse-Granger exogeneity screen
(`return → Δ global CCI`, α = 0.05, 4 lags) → **23 retained** after the `T ≥ 340` gate.

---

## Where things are

```
├── README.md                  you are here — the map
├── CLAUDE.md                  reproducibility rules (READ BEFORE RUNNING ANALYSIS)
├── GROUND_TRUTH.md            every headline number reconciled to a code path
├── verification_manifest.md   paper-side target list (what the draft prints)
├── PHASE0_REPORT.md           what is reproducible today, and what is not
├── ASSUMPTIONS.md             judgment calls made during the rebuild
│
├── src/                       CORE PIPELINE — do not move (paths are __file__-relative)
├── scripts/                   rebuilt revision-round analyses  [Phase 1, in progress]
├── outputs/rebuilt/           their outputs, for diffing against results/exports/
│
├── data/                      READ-ONLY. Raw inputs at the paper's vintage. Do not re-download.
│   ├── equity/                74 index CSVs
│   ├── sentiment/             60 trigger CSVs (global + national CCI, MCSI, VIX, CAPE, ...)
│   └── combined/              monthly_panel.csv, daily_panel.csv
│
├── results/                   READ-ONLY GROUND TRUTH
│   ├── tables/                global_cci_all_markets.csv  ← the 23-market panel
│   ├── gcci/                  efficiency ranking, regime plots
│   ├── figures/               bubble-call charts
│   ├── exports/               ★ the paper-support layer (61 CSVs + README + manifest)
│   └── archive/               superseded-trigger outputs
│
├── docs/
│   ├── code_guide.md          per-module function tables
│   ├── data_layer.md          why monthly and daily panels both exist
│   └── writeups/              Week 1-4 Findings, code_guide, tar_results_tables (.docx)
├── paper/                     drafts + the A&S source paper
└── reference/farid/           supervisor's original MATLAB (estimate.py was ported from it)
```

**Three documents carry the project's memory** — read them before changing anything:

1. `results/exports/README.md` — a forensic log of revision Rounds 2–10, with each analysis's
   spec, parameters and seeds.
2. `results/exports/paper_numbers_manifest.csv` — 216 rows, the author-side single source of
   truth the draft was diffed against.
3. `GROUND_TRUTH.md` — maps numbers to code paths with line references.

---

## Running the pipeline

Most modules are `python <file>.py [subcommand]` scripts, run **from inside `src/`**.

```bash
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -r requirements.txt

# 1. Collect  (needs FRED_API_KEY in .env) — NOT needed to reproduce the paper;
#    data/ already holds the paper's vintage. Re-running changes every number.
python src/collect_data.py

# 2. Main study — writes results/tables/global_cci_all_markets.csv
cd src && python global_cci_study.py        # inspect|screen|validate|rolling|estimate|bubble

# 3. Downstream (all read that CSV)
cd src && python gcci_figures.py            # ranking|plots|charts|chart_*
cd src && python horizon_test.py            # all|dist
cd src && python bubble_now.py              # all|plot|table|cci

# 4. Replication of A&S Tables 7 & 8
python src/replicate.py                     # arg "8" for Table 8
```

`global_cci_study.py screen` and `mixed_trigger_study.py screen` are **read-only** (print only).

---

## Reproducing the analysis

```bash
python scripts/run_all.py            # everything (~15 min; the B>=1000 stages dominate)
python scripts/run_all.py --fast     # skip resampling stages (~2 min)
python scripts/run_all.py --list     # show stages
```

Stage 0 is a **gate**: if `fastgrid.py` stops reproducing `src/estimate.find_optimal_thresholds`
to 1e-9 on all 23 markets, the run aborts rather than producing quietly wrong numbers.

| Script | Rebuilds |
|---|---|
| `config.py` | every seed and constant, with provenance |
| `fastgrid.py` | vectorised spec=1 grid search, ~300× faster, self-validating |
| `round01_horizon.py` | horizon table, per-market pool, EXP phase, F6, episodes, expn check |
| `round04_appendices.py` | T5 unrestricted band, Appendices A / B / C |
| `round06_drift_fdr.py` | W1 drift table, W3 / W4 Benjamini-Hochberg |
| `round07_dependence.py` | X1 / X4 / X6 / X7 / X8 dependence corrections |
| `round08_permutation.py` | Y2 circular-shift permutation, B=5000 |
| `round10_bootstrap.py` | P1 threshold + pooled bootstrap, B=1000 |
| `round10_placebo.py` | P9 placebo, B=1000, iid and block nulls |
| `round10_rwband.py` | P3 RW-band validation |
| `compare_rebuilt.py` | diffs every rebuilt output against its export |
| `verify_paper.py` | verdict per paper number → `VERIFICATION_REPORT.md` |

**Status:** 23 outputs rebuilt — 14 reproduce their export exactly or to floating-point noise,
5 are close, 4 differ (the B≥1000 resampling stages, plus `kappa_stability`). Deterministic
analyses match; seeded ones cannot match bit-for-bit because reproducing a bootstrap needs the
original RNG *call order*, not just the seed. For those the test is whether the paper's claim
survives — and it does. See `ASSUMPTIONS.md` §A3.3.

## Why `results/exports/` and `src/archive/` are not deleted

Both look like duplication. Neither is.

**`results/exports/`** is the frozen vintage your draft was written against. The deterministic
files can now be regenerated exactly, but the seeded ones cannot. Delete it and the numbers in
the submitted paper lose their source. `outputs/rebuilt/` is the living reproduction; keeping
both is one copy of each *thing*, not two copies of one thing.

**`src/archive/`** is the **sole provenance** for paper numbers the rebuild does not cover —
`C6` (CAPE), `C7` (BAA), `C9` (ANFCI) and all of block `J` (composite, BIC-composite, CCI+EPU),
which `results/exports/README.md` tags `HISTORICAL`. The rebuilt scripts regenerate the
global-CCI exports, not the alternative-trigger studies. Deleting these would recreate exactly
the problem this repo exists to fix.

Genuine duplication that *could* still be consolidated: `_episode_verdict` is copy-pasted seven
times across the study modules with the episode windows re-hardcoded in each. That is a `src/`
refactor and needs tests first, so it is deliberately left undone.
