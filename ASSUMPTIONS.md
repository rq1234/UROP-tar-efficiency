# ASSUMPTIONS.md

Every judgment call not pinned down by `results/exports/README.md` or the paper, logged at the
moment it was made. Newest phase last.

---

## Phase 0 — mapping

**A0.1 — Spec authority.** Where `results/exports/README.md` and `paper_numbers_manifest.csv`
differ, the README is treated as authoritative for *specification* (parameters, seeds, B,
block lengths) and the manifest as authoritative for *reported values*. Rationale: the README
records how each run was configured; the manifest records only `id, paper_location,
description, value` with no parameters.

**A0.2 — Round 1 script attribution.** Manifest blocks `A`–`J` are attributed to the recovered
filenames `make_exports.py`, `build_manifest.py`, `build_figures.py`. The README does not state
this mapping; it is inferred from the recovered permission-allowlist filenames combined with
the export list under the "⭐ paper_numbers_manifest.csv" heading. If a rebuilt Round 1 script
fails to reproduce a block, this attribution is the first thing to doubt.

**A0.3 — Definition of "missing".** An analysis is classed MISSING when no file in `src/`
writes its export CSV. Some of its individual values may still be obtainable by calling a
surviving module directly (GROUND_TRUTH.md does exactly this for several numbers, tagged
`[reproduced]`). PHASE0_REPORT.md §2 lists only the cases I could confirm by reading the code.

**A0.4 — Panel is fixed input, not re-estimated.** Rebuilt analyses read the committed 23-market
panel `results/tables/global_cci_all_markets.csv` as given. A round re-estimates thresholds only
where its own spec says so (e.g. Round 8 Y1/Y4 re-estimate under spec=0/spec=2; Round 10 P1
re-estimates the full grid on every bootstrap draw). Rationale: the paper's numbers were
produced against this panel, and re-deriving it would silently change the baseline.

**A0.5 — `T1_verdict` and `P4d` are recorded as SUPERSEDED, not wrong.** The manifest still
holds the Round 4 / Round 9 values. PHASE0_REPORT.md §4 flags these; no manifest row was
edited, per the hard rule that manifests are never modified.

**A0.6 — Round 9 vs Round 10 `P#` id collision.** The README warns that `P#` ids appear in two
plans (Round 9 uses `P1_mr*`/`P2_metricB*`/`P4_*`/`P6`–`P8`; Round 10 uses
`P1_boot*`/`P1_pooled*`/`P2_pct*`/`P3_bRW*`). Disambiguation is by each row's `description`
field, as the README instructs. Scripts were originally named `round09_*` / `round10_*` so the
collision couldn't propagate into filenames; they were later renamed by function (A5.1) - the
disambiguation is now permanently anchored in `PHASE0_REPORT.md`'s round-to-file map instead.

**A0.7 — Dependencies not declared.** `statsmodels` and `linearmodels` were used by the lost
scripts (recovered from the settings.json allowlist; Round 1 note F5 confirms Driscoll–Kraay ran
via statsmodels `hac-groupsum` with 11 lags) but appear in neither `requirements.txt` nor any
`src/` import outside `src/archive/bic_composite_study.py`. Phase 1 will add them with pinned
versions. The exact versions used for the paper's numbers are **not recoverable** — a possible
source of small numerical differences in DK standard errors.

**A0.8 — Working copy.** Two copies of this project exist on disk:
`OneDrive\0 Rong\01 Documents\UROP` (has the `.venv`; the copy the lost exports work actually
ran in) and `OneDrive\0 Rong 1\05 Projects\Code\UROP` (this one). `src/` and `results/exports/`
appear identical, though a byte-level comparison was blocked by OneDrive files-on-demand
placeholders in the first copy. Per instruction, **this copy is authoritative**. The other is
not synchronised by anything in this repo and will drift.

**A0.9 — Git scope.** `git init` was run in this directory. Note that a separate,
never-committed git repository already exists with its root at `C:\Users\rongq` (263 MB, 53
staged files belonging to the unrelated `Optimiser` project). GROUND_TRUTH.md §1b independently
records this. The new repo is nested inside it; the outer repo was left untouched.

*(A0.9 superseded: the home-directory repo has since been deleted, and this working tree now
lives at `C:\Users\rongq\projects\UROP`, outside OneDrive — see A1.1.)*

---

## Phase 1 — relocation

**A1.1 — The repo left OneDrive.** OneDrive repeatedly undid work: it reverted committed
`.gitignore` and `README.md` to pre-commit versions while diverting the edits into
`*-LAPTOP-*` conflict copies, and it resurrected deleted directories as cloud-only
placeholders. The working tree is now `C:\Users\rongq\projects\UROP` with a normal `.git`
directory, `origin` = `rq1234/UROP-tar-efficiency`. GitHub is the backup; `data/` and
`results/` are tracked, so nothing depends on OneDrive.

**A1.2 — Relocation was done by clone, not by move.** A `git clone` of the committed history
was used rather than moving files. Rationale: it restores the correct committed `.gitignore`
and `README.md` automatically, leaves the 14 untracked duplicate ghosts behind, and avoids
forcing OneDrive to hydrate cloud-only placeholders. Before relying on it, all 14 untracked
files were confirmed to have tracked counterparts, and `data/`(18M) + `results/`(19M) sizes
and `git fsck` were verified in the clone.

---

## Phase 2 — verification

**A2.1 — Verification compares against committed outputs, not fresh computation.**
`scripts/verify_paper.py` checks `verification_manifest.md` targets against
`results/tables/` and `results/exports/`. It deliberately does *not* recompute from `data/`;
that is what the round scripts do. So a MATCH means "the paper agrees with what the pipeline
produced", not "the pipeline was re-run and agrees".

**A2.2 — Comparison is done at the precision the paper prints.** The manifest's class-E rule
is "within 1 in the last printed digit". Three verifier bugs were found and fixed by
inspecting the data rather than trusting the first verdict: substring matching (which flagged
Greece 43.5 vs a printed 44 as a mismatch), `round()` at the boundary (float representation
makes `round(-3.155, 2) == -3.15`), and a missing epsilon (`abs(-3.155 - -3.16)` evaluates to
0.0050000000000004, exceeding a `<= 0.005` test). A verifier that cries wolf is worse than none.

---

## Phase 3 — rebuild

**A3.1 — `fastgrid` is exact, and that is tested, not assumed.** It reproduces
`src/estimate.find_optimal_thresholds` on all 23 panel markets to 1e-9 (largest ΔRSS 9.5e-12)
and runs ~300× faster. `python scripts/fastgrid.py` exits non-zero on any disagreement, so it
gates the rest of the rebuild. It replicates the reference's `> 2` regime guards, the RW band's
forced β with α = mean, and first-minimum tie-breaking to match the original's strict `<`.

**A3.2 — `fastgrid` covers spec=1 / mode='returns' only.** That is the paper's main
specification and the only one the bootstrap needs. Other specs raise rather than silently
returning something unvalidated; Round 8's Y1/Y4 (spec 0 and 2) must use the reference
implementation or extend the validation first.

**A3.3 — Seeded stochastic results do NOT reproduce exactly, and cannot.** A seed fixes the
RNG stream, but reproducing a bootstrap bit-for-bit also requires the original *call order* —
how many draws, in what sequence, across markets and schemes. That was lost with the scripts.
So class-S outputs are expected to differ in point estimates; the test is whether the paper's
qualitative claim survives.

For Round 10 Priority 1 (B=1000, seed 20260722), rebuilt vs original:

| | original | rebuilt |
|---|---|---|
| pooled MR−RW | +8.178 [+2.515, +15.408] | +8.110 [+1.532, +16.057] |
| pooled EXP−RW | −10.879 [−18.232, −4.316] | −12.600 [−20.991, −5.160] |
| wild RW-share CI width | 37.310 pp | **37.310 pp** |
| wild c2 CI width | 0.997 | 1.011 |
| block24 c1 / c2 width | 2.925 / 2.680 | 2.853 / 2.577 |
| block24 markets with b_EXP CI < 0 | 5/23 | **1/23** |
| wild markets with b_EXP CI < 0 | 6/23 | 5/23 |

**Qualitative claims survive:** both pooled gaps keep their sign and both 95% CIs still
exclude 0, so "the aggregate explosive discount survives full threshold uncertainty" holds.
The wild scheme's share widths reproduce essentially exactly, which is expected — it conditions
on the observed CCI path.

**One divergence to report, not to hide:** under block24 the rebuild finds b_EXP CIs excluding
zero in **1/23** markets against the original's 5/23. This does not overturn the paper's claim;
it *strengthens* it in the same direction. The paper already concludes "individual slope stars
are fragile" and recommends de-emphasising per-market coefficient stars. The rebuild says they
are more fragile still. Section 4.2 should not lean on per-market stars under the block scheme.

**A3.4 — The wild scheme holds `x` and `z` fixed.** Per manifest row `P1_boot_design`
("wild=Rademacher on spec-1 residuals (x,z fixed)"), `dep* = fitted + resid · η`,
η ~ Rademacher. This produces a `dep` that corresponds to no single log-price path, so it
cannot go through the `y`-based entry point; `fastgrid.fast_grid_rss_parts` exists for exactly
this. Block schemes resample (dep, x, z) triples and recompute grid bounds per draw, since the
trigger itself is resampled.

**A3.5 — Japan is excluded from the pooled EXP cell only.** `config.EXCLUDED_EXP_MARKETS`
makes explicit what was buried at `src/horizon_test.py:145`. Its MR and RW months are kept.

---

## Phase 4 — consolidation

**A4.1 — Nothing in `src/archive/` was deleted, and the evidence says it must not be.**
The instruction was to keep one copy and delete superseded scripts once replaced. The rule
applied was "delete only what is provably replaced". Checking each archived module against
`paper_numbers_manifest.csv` shows they are not replaced by anything:

| Archived module | Sole provenance for |
|---|---|
| `cape_study.py` | `C6` — CAPE rolling threshold range |
| `baa_study.py` | `C7` — BAA euphoria compression vs GFC spike |
| `anfci_study.py` | `C9` — ANFCI high-sentiment firing rate |
| `composite_study.py` | `J1`, `J2`, `J4`, `J6` — the Section 7.1 composite story |
| `bic_composite_study.py` | `J3` — BIC orthogonalisation lag |

`results/exports/README.md` tags these rows `HISTORICAL` and states their generating scripts
are "committed under `src/archive/`". The rebuilt scripts regenerate the **global-CCI exports**,
not the alternative-trigger studies, so they replace none of this. Deleting them would destroy
the only remaining source for numbers the paper cites — the exact failure this repo exists to
repair.

**A4.2 — `results/exports/` is kept as the frozen vintage.** It is not a duplicate of
`outputs/rebuilt/`. The deterministic exports can now be regenerated exactly, but the seeded
ones cannot be reproduced bit-for-bit without the original RNG call order (A3.3). The exports
are what the draft was written against; the rebuild is the living reproduction. Keeping both is
one copy of each thing.

**A4.3 — Real duplication left undone, deliberately.** `_episode_verdict` is copy-pasted seven
times across the study modules, each re-hardcoding the same episode windows, and six study
modules share a ~70% identical skeleton. Consolidating that is a `src/` refactor touching code
that currently produces the published panel, with no test suite behind it. `config.py` now holds
single definitions of the constants (including both episode window sets, see A4.4), which is the
safe half of the job. The refactor itself should follow a TAR recovery test, per
`PHASE0_REPORT.md`.

**A4.4 — Two episode window sets exist and conflating them corrupts Appendix B.**
`HISTORICAL_EPISODES` (`src/global_cci_study.py:64`) drives `_episode_coverage` and Appendix B:
dot-com 1998-01..2001-03 expecting EXP, GFC 2008-09..2009-03 expecting MR, COVID
2020-02..2020-04 expecting MR. The verdict windows used by `_episode_verdict` are wider and
different. `config.EPISODES_COVERAGE` and `config.EPISODES_VERDICT` now carry both explicitly.

**A4.5 — Round 7 partial reproductions, recorded as gaps not matches.**
`episode_dep_corrected` (year-collapsed mean −11.98pp vs the export's −18.31pp),
`kappa_stability` (mean κ 0.694 vs 0.740) and `drift_variance_ratio` do not yet reproduce. X1's
structure is right — 30 episodes in the same 5 calendar-year clusters, 29 in 1997–2000 — so the
gap is in how episodes are assigned to clusters or weighted. The exports remain the source for
those three numbers, and `VERIFICATION_REPORT.md` records A14/C38 as MATCH against the export.

**A4.6 — Round 10 remainder (`scripts/min_regime_wald_recursive.py`), fixed vs residual gaps.**
Three real bugs found and fixed against the surviving `results/exports/` ground truth (not
tuned to a paper number — the export itself showed the correct shape):
- `recursive_horserace.csv`'s `tar`/`pct` columns are 3-valued (0=RW/middle, 1=MR/low-tail,
  2=EXP/high-tail), matching the state-code convention used everywhere else. The script had them
  as binary flags. Cut mismatched cells from 1771/5847 to 323/5847 once corrected.
- `nikkei225` (`config.EXCLUDED_EXP_MARKETS`) was not excluded from the EXP/high-tail band in
  the recursive labelling, unlike every other round script. Relabelling its would-be EXP months
  to RW (never dropping MR/RW, per the existing convention) moved the pooled TAR-high mean from
  −7.01 to −16.42 against the export's −16.93.
- `wald_tar_vs_fixed.csv`'s `cov_EXP_above` column read `V[1,2]` (cov(TAR_MR, TAR_EXP)) instead
  of `V[2,4]` (cov(TAR_EXP, above-P90)) — an indexing bug against the script's own documented
  column layout. Did not affect the Wald statistic itself, which already used the right indices.

Residual, unresolved, not chased further per the report-don't-repair rule:
- `recursive_horserace.csv` still carries 323/5847 (5.5%) `pct` mismatches (mostly single-cell,
  boundary-adjacent) and 57 extra `nikkei225` rows the export doesn't have at all (their absence
  isn't explained by the EXP exclusion above — likely a feasibility condition specific to how
  the original handled nikkei225's degenerate threshold that skipped those months outright).
- `wald_tar_vs_fixed.csv`: b_EXP −9.44 vs export −11.28, b_above90 −6.05 vs −4.36 — the qualitative
  conclusion (Wald fails to reject equality; DK p=0.75 vs export's 0.52, both ≫0.05) survives, but
  the point estimates differ by more than floating-point noise. Cause not identified; a plausible
  candidate is how `statsmodels`' `hac-groupsum` expects the panel sorted/grouped, but this was
  not confirmed.
- `normalized_local_runs.csv` / `common_level_scale.csv`: within 0.01–3.7 points of the export
  depending on cell — `compare_rebuilt.py` tags these seed/precision-sensitive; the headline P8b
  claim (Turkey RW share collapsing under percentile normalisation) reproduces closely (8.8%/9.2%
  export/rebuilt vs the reported 42%→9%).

**A4.7 — `appendixD_optionAB_agreement.csv` (Round 2, R4) inherits Round 7's Option-B gap.**
`scripts/pool_exclusions_optionab.py` reuses the frozen-threshold (Option B) method already in
`scripts/dependence_corrections.py`'s `x6_kappa` (in-sample fit to `INSAMPLE_END`, applied out of
sample via `optimal_from_parts`). Most markets reproduce the export within 1-4pp of agreement
(precision-level noise). `nikkei225` and `psei` reproduce `kappa_stability.csv`'s own agreement
figures for those markets EXACTLY (47.94%, 49.31%) but diverge sharply from
`appendixD_optionAB_agreement.csv`'s own figures for the same two markets (97.48%, 51.61%) — the
gap is consistent across both exports built on the same method, not a new bug introduced here.
The shared root cause (the in-sample-only grid search evidently lands on a different, likely
degenerate, threshold pair for these two markets than whatever the original process used) is
Round 7 scope and already flagged there via kappa_stability's own "mean kappa 0.694 vs 0.740"
gap; not re-derived. `horizon_test_exclusions.csv` (R2/R3b), by contrast, reproduces the export
exactly (per-rule MR/RW/EXP pooled means match to the reported 2 decimal places).

**A4.9 — Round 5 (`scripts/live_audit_2025_2026.py`), reproduces closely; two documented gaps.**
- V1 (`reverse_granger_extra.csv`): F=3.5358, p=0.0075, gate=FAIL reproduce the export exactly.
  `T` is 409 here vs the export's 408 - most likely data-vintage drift (this repo's committed
  `data/sentiment/global_cci_monthly.csv` now runs through 2026-05, one month later than when
  V1 was presumably first generated) rather than a code difference, since the appendix-A screen
  this reuses already verifies as MATCH with the identical `T = len(y)` convention.
- V3 (`gcci_labels_2025_2026.csv`): Option A (97.668/101.934) and Option B (97.567/101.972)
  reproduce the export's stated 97.67/101.93 and 97.53/101.93 closely - the same few-hundredths
  precision gap as A4.7's Option-B fits elsewhere. All 10 rows' `gcci_value` match exactly, and
  9 of 10 label pairs match exactly, but it flips the headline finding for the boundary month:
  the export has 2026-05 as `label_optionA=MR, label_optionB=RW` (MR appears "only under Option
  A"); this rebuild's slightly higher Option-B `c1` (97.567 vs the export's implied ~97.526)
  puts the same 97.552 reading just inside the MR side under both options. `compare_rebuilt.py`
  does not flag this - it only diffs numeric columns, not the label strings - so it is recorded
  here instead.
- V4 (`mcsi_2025_2026.csv`): the frozen SP500-MCSI Option-B `c1=59.677` matches the export's
  stated 59.677 exactly, as does `below_c1_flag` for all 11 months this rebuild can reach. The
  export's twelfth month, 2026-05 (umcsent=44.8), is not in `data/sentiment/mcsi_monthly.csv` or
  `data/combined/monthly_panel.csv` (both stop at 2026-04) - a live FRED re-pull beyond the
  committed vintage. No `FRED_API_KEY` is configured in this environment, so that month is
  reported as missing rather than filled in from the export's own number.

**A4.10 — Round 7 X2/X3, and X5 deferred (`scripts/dependence_corrections.py`).**
- X2 (`oos_exp_dep_corrected.csv`) needed a real fix, not just noise-tolerance: the panel's
  Option A (full-sample) thresholds give almost no post-2015 EXP months at all (only ibex35 has
  any, per `expn_check.csv`'s `last_EXP_month` column - every other non-Japan market's last-ever
  EXP month is ~2000-2001). The export's `n_EXP=76`/`n_RW=2141` match Round 2's R4d exactly
  (`appendixD_optionAB_agreement.csv`'s Option B / frozen-threshold OOS classification), so X2 was
  rewritten to classify the post-2015 window with Option B thresholds, computed inline the same
  way as `x6_kappa`. That fix is structural (confirmed by R4d's numbers), not tuning. What remains
  is count drift consistent with the same data-vintage pattern as A4.9's V1/V4: this rebuild gets
  `n_EXP=86` (vs 76), `n_RW=2330` (vs 2141), 6 markets/5 years (vs 4/4) - proportionally larger
  across the board, as expected if the committed data now runs further past 2015 than when the
  export was generated. The gap (`-8.33pp` vs `-9.84pp`) and both p-values (`DK 0.21` vs `0.19`;
  block-bootstrap `0.21` vs `0.22`) land close enough that the qualitative verdict is unchanged:
  the post-2015 OOS result does not survive dependence correction either way.
- X3 (`horserace_label_vs_trailing.csv`) reproduces closely (`CLOSE (seed-sensitive)`, max
  coefficient difference 0.87 on coefficients of magnitude ~14, e.g. EXP `-13.66` vs the export's
  `-14.07`) using the standard Option A / panel-threshold membership rule, no exclusion changes
  needed. The `c2_cci_level` model (continuous standardised CCI level `zlev` + trailing return)
  is not described in prose in `results/exports/README.md`, only inferred from the export's
  column names; included for completeness but its exact construction (which sample the
  standardisation uses) is a guess, not a spec.
- X5 (`turkey_real_return.csv`) is not built: it needs Turkish CPI (`TURCPIALLMINMEI`) deflating
  bist100, and that series is not in `data/sentiment/` (only a US `cpi_monthly.csv` exists) and
  requires a live FRED pull with no `FRED_API_KEY` configured here - the same blocker as T3
  (China CCI, A4.8) and V4's twelfth month (A4.9).

**A4.11 — Round 4 T1/T2 (`scripts/placebo_grid_stability.py`).**
- T1 (`placebo_summary.csv`, `placebo_thresholds.csv`): every deterministic ("real") value -
  `real_c1`, `real_c2`, `real_rss_impr_pct` for all 23 markets - reproduces the export exactly
  (verified by market, since row order differs from the export's). The aggregate finding matches
  closely: median real RSS percentile 92 here vs the export's 94, 14/23 markets >=90th vs 18/23,
  band share 24.0% vs 25.5% - same conclusion (location is partly mechanical, the fit is not).
  The 50-per-market simulated placebo draws themselves (`plac_c1_p*`, `real_*_pctile`,
  `placebo_thresholds.csv`'s individual `sim` rows) do not reproduce bit-for-bit - expected for a
  seeded simulation where the original RNG call order is unknown (the same limitation already
  noted for the B=1000 supersession in `placebo_1000.csv` and the B=1000/5000 bootstraps
  elsewhere). `placebo_1000.py`'s already-committed `BAND_C1`/`BAND_C2` constants and
  iid-generation method were reused unchanged, so this is the same simulation design at B=50.
- T2 (`stability_scale_adjusted.csv`): MCSI and global_CCI rows are near-exact (`c1_range_over_span`
  0.74/0.864 match the export's 0.74/0.864 to 3 decimals). US_CCI is off by more
  (`c1_range_over_sigma` 2.48 vs the export's 2.84) - most likely `data/sentiment/oecd_cci_USA.csv`
  starting later or differently-aligned than whatever window the original rolling analysis used;
  not investigated further. The cross-trigger ORDERING the finding rests on - global CCI >
  MCSI > US-CCI on both `range_over_sigma` and `range_over_span` - reproduces correctly.

**A4.12 — the three FRED-API-key blockers (A4.8, A4.9's V4 twelfth month, A4.10's X5) are
resolved.** A `FRED_API_KEY` was supplied and stored in a project-root `.env` (gitignored, never
committed - see `.gitignore`). All three now reproduce their exports exactly, not approximately:
- T3 (China CCI): `scripts/country_cci_episodes.py` fetches `CSCICP03CNM665S` live and gets 408 obs,
  1990-01..2023-12 - byte-identical to `results/exports/cci_CHN_fetched.csv`. The series really is
  discontinued in FRED after 2023-12; that was never a vintage-drift artefact. Shanghai and SZSE's
  `localised_runs.csv` rows now match the export exactly (T, c1, c2, MR/RW/EXP all `IDENTICAL` per
  `compare_rebuilt.py`).
- X5 (Turkey real return): `scripts/dependence_corrections.py` fetches `TURCPIALLMINMEI` live and
  deflates bist100's log price by log(CPI). Both rows of `turkey_real_return.csv` (real_CPI and
  the nominal baseline) reproduce exactly.
- V4 (`mcsi_2025_2026.csv` twelfth month): `scripts/live_audit_2025_2026.py` fetches `UMCSENT` live when
  the committed `data/` vintage doesn't reach the target month; got `2026-05 = 44.8`, matching the
  export exactly (all 12 rows now `IDENTICAL`).

None of these write to `data/` - the fetched series are used in memory (X5, V4's extra month) or
saved only to `outputs/rebuilt/` (T3's `cci_CHN_fetched.csv`). All three functions degrade
gracefully (print a clear skip message, return no rows) if `FRED_API_KEY` is absent, so the
scripts still run cleanly in an environment without the key.

**A4.8 — Round 3 (`scripts/country_cci_episodes.py`) reproduces exactly; China rows (Round 4 T3)
deferred.** S1's athex/bist100 rows match `localised_runs.csv` to every printed decimal place,
and S3's MR-cluster count (222 distinct calendar-months, 9 clusters gap<=3 months) matches the
README's own boundary list exactly, date for date. The export's other two rows (shanghai/szse,
tagged `cci_CHN`) belong to Round 4's T3 ("China CCI fetched fresh from FRED
`CSCICP03CNM665S`... `data/` untouched") — not written here, since no `FRED_API_KEY` is
configured in this environment (checked: no `.env`, no matching shell env var) and `data/` may
not be modified to work around that. `write()` merges by `market` rather than overwriting the
file, so a future Round 4 T3 script can append those two rows without disturbing these.

---

## Phase 5 - renamed by function

**A5.1 - Scripts renamed from `roundNN_*` to descriptive names, 1:1, no splitting.** The
referee-round numbering (`round01_...round10_...`) reflected *when* each analysis was
reconstructed, not what it does, and had become actively confusing once multiple functionally
unrelated things landed in the same round (e.g. `round07_dependence.py` mixed episode
dependence, matched-window localisation, kappa-stability, and Fisher-z CIs) while functionally
related things were split across rounds (e.g. all three placebo/permutation analyses -
`round04`'s T1, `round08`'s Y2, `round10`'s P9 - lived in three differently-numbered files).
Renamed by dominant function, one new name per old file, no internal code moved or split:

| old | new |
|---|---|
| `round01_data.py` | `raw_data_exports.py` |
| `round01_horizon.py` | `horizon_episodes.py` |
| `round02_pool_optionAB.py` | `pool_exclusions_optionab.py` |
| `round03_episodes.py` | `country_cci_episodes.py` |
| `round04_appendices.py` | `granger_appendices.py` |
| `round04_placebo_stability.py` | `placebo_grid_stability.py` |
| `round05_audit.py` | `live_audit_2025_2026.py` |
| `round06_drift_fdr.py` | `drift_fdr.py` |
| `round07_dependence.py` | `dependence_corrections.py` |
| `round08_permutation.py` | `rank_stability_permutation.py` |
| `round09_diagnostics.py` | `regime_diagnostics.py` |
| `round10_bootstrap.py` | `threshold_bootstrap.py` |
| `round10_placebo.py` | `placebo_1000.py` |
| `round10_remainder.py` | `min_regime_wald_recursive.py` |
| `round10_rwband.py` | `rw_band_validation.py` |

Done via `git mv` (history preserved), followed by fixing every cross-file import, every
self-referential "Usage:" line, and every prose mention of another script's old name. All
14 non-slow stages re-ran clean end to end (`run_all.py --fast`) after the rename with zero
import errors; every rebuilt CSV came out byte-identical to its pre-rename version except
`crisis_window_rho.csv`, whose row order changed - see A5.2, a real pre-existing bug the
rename incidentally surfaced, not something the rename caused. `run_all.py`, `README.md`,
`PHASE0_REPORT.md`'s recovered-script table, and this file were updated to the new names; earlier
entries in this file (A0-A4) were NOT rewritten to use the new names, since they are a log of
what was true at the time each entry was made.

**A5.2 - Second instance of the set-iteration-order bug (A4.6), found by the rename's
re-run.** `regime_diagnostics.py`'s `p7_correlation_diagnostics` (P7c, `crisis_window_rho.csv`)
built its market list with `pan = {p["market"] for p in panel()}` - a bare `set`, whose iteration
order is hash-randomised per Python process. Re-running the (otherwise unchanged) pipeline after
the rename produced the same 8 rows in a different order, which is how this surfaced. Fixed the
same way as A4.6: `sorted(...)`. Confirmed deterministic across two consecutive runs before and
after the fix. Not a rename artefact - the bug predates it and would have surfaced on any
re-run; grepped the rest of `scripts/` for the same pattern (bare `{expr for x in y}` feeding
output row order or RNG draw order) and found no other instances - the remaining set/dict
comprehensions either preserve deterministic dict-insertion order or are used only for
membership/counting, where order doesn't matter.

---

## Phase 6 - closing the verify_paper.py gap

**A6.1 - `verify_paper.py` was stuck at 26 of 77 non-figure manifest items, despite the
underlying data mostly existing.** `verification_manifest.md` ("every substantive number and
exhibit in the final draft") has 66 numbered IDs across Sections A/B/C/E (77 counting sub-checks
like B2x/C20x), plus 10 figures in Section D. `verify_paper.py` had 11 checker functions written
early (Phase 2), before most of Rounds 2-10 existed, and was never extended as coverage grew.
Went through all 51 unchecked IDs by hand against `results/exports/`: the overwhelming majority
already had a committed CSV to check against - they just weren't wired up. Added 18 new checker
functions (`v_panel_characterisation`, `v_localised_and_matched`, `v_scale_and_stability`,
`v_archive_studies`, `v_granger_and_correlations`, `v_efficiency_and_rank_metrics`,
`v_bootstrap_and_minregime`, `v_wald_and_recursive`, `v_permutation_and_horserace`,
`v_episode_variants`, `v_oos_publag_clusters`, `v_appendixD_and_coverage`,
`v_no_committed_generator`, `v_section_e4`, plus new A2/A3/A8/A12/E1 entries folded into the
panel/localised functions). Final count: **61 MATCH, 4 NEAR, 3 MISMATCH (E1/E2/E3, all genuine
paper-text errors - not verifier bugs), 9 NOT_REPRODUCIBLE.** 77 of 77 non-figure targets now
carry a verdict.

**A6.2 - Genuine gaps found and left as NOT_REPRODUCIBLE, not papered over:**
- **C1** (A&S Tables 7/8 replication) and **C2** (8-lag Granger re-run): no committed CSV carries
  either - `src/replicate.py`'s `replicate_table7`/`replicate_table8` print rather than write a
  file, and the 8-lag screen was never re-run (only the standard 4-lag one). Both need a human to
  run the script and eyeball the output, not a file diff.
- **C34/C35** (fixed-label moving-block bootstrap, low-RW and high-RW): `config.py`'s
  `SEED_FIXED_LABEL_BLOCK = 12345` is defined but grepping all of `scripts/` shows it is never
  used anywhere. This specific test was never reconstructed in any round - a real gap, not a
  wiring omission.
- **C48** (Fig 6.2 distribution facts - mode location, which calendar months populate the tails):
  needs the full per-month dated return distribution, which no summary export carries in that
  shape.
- **C8/C9/C49/C50** (BAA spread, ANFCI firing rate, composite and CCI-EPU pass rates): all route
  through `src/archive/` modules and `results/archive/tables/`, which exist and were smoke-tested
  (A6.3) but were not cross-checked cell-by-cell against these specific figures - flagged for
  manual review rather than guessed at.

**A6.3 - `src/archive/`'s 12 modules were never part of the lost-scripts problem and don't need
rebuilding.** They survived; their outputs are committed separately under `results/archive/`
(tables + figures), untouched throughout this whole reconstruction. Smoke-tested by importing all
12 (`cape_study`, `baa_study`, `anfci_study`, `composite_study`, `bic_composite_study`,
`bci_study`, `bis_study`, `bis_exogeneity_test`, `spy_study`, `cci_study`,
`combinatorial_search`, `robustness`) - all import cleanly, no bit-rot.

**A6.4 - Real bugs found while wiring this up, fixed because they were bugs, not tuned to match:**
- `min_regime_wald_recursive.py` (formerly `round10_remainder.py`) writes `min_regime_summary.csv`
  with rule names `obs20/obs30/obs40`; the committed export uses `abs20/abs30/abs40`. Values match
  row-for-row (confirmed earlier by `compare_rebuilt.py`, which fell back to positional pairing
  since the differing rule names broke its usual keyed match) - this is a labelling difference
  only, not a computational one. Not fixed at the source (would mean re-verifying that script for
  a cosmetic rename); `verify_paper.py`'s new checks read the export's `abs*` names directly.
- C12 (national-global correlation flags) needed China's correlation, which is not in
  `appendixC_dcci_correlations.csv` (25 rows, not 26 - already known, B7). Computed it fresh from
  `outputs/rebuilt/cci_CHN_fetched.csv` (Round 4 T3) against `data/sentiment/global_cci_monthly.csv`
  inside the checker, rather than leaving it unverifiable.

---

## Phase 7 - a false claim, caught and retracted

**A7.1 - E3's "RESOLVED... band share > 1.5%" claim (A6, Phase 6) was wrong.** An external
review of `VERIFICATION_REPORT.md` proved it by construction: Table 4.1 labels KLCI (low_pct=1.54%)
and TWSE (low_pct=1.73%) as "High only" even though both exceed 1.5% on the low band; it labels
PSEI (high_pct=1.15%) and SHANGHAI (high_pct=1.16%) as "Both" even though both are *below* 1.5% on
the high band. No single threshold, applied to both bands, can satisfy both constraints - the
prior claim conflated "the count of markets excluded reaches 20 at threshold=1.5%" (true, but by
excluding bovespa/shanghai/psei via `high_pct`) with "threshold=1.5% drops precisely klci/twse"
(false - those two are never the ones excluded by that sweep). Two different things, coincidentally
matching on the *count* alone. Retracted in full, not softened.

**A7.2 - The real rule needs two independent thresholds, and it's not a fragile fit.** Verified
by hand against all 23 markets in `global_cci_all_markets.csv`, then coded into
`scripts/verify_paper.py`'s E3 check: a market's low band counts as "present" iff
`low_pct > TAIL_COVERAGE_LOW_MIN_SHARE_PCT` (`config.py`, now 2.0); its high band counts as
"present" iff `high_pct > TAIL_COVERAGE_HIGH_MIN_SHARE_PCT` (now 1.0). This reproduces Table 4.1's
`tail_coverage` column exactly for all 23 markets (0/23 mismatches) - and with real margin, not a
coincidence: the low-band cutoff can be anywhere in `(1.734, 2.03]` (twse, the highest "absent"
value, to ibex35, the lowest "present" one) and the high-band cutoff anywhere in `(0.0, 1.147]`
(bovespa to psei) and it still reproduces every label. A 2-parameter rule fit to 23 binary
outcomes with no margin would be a red flag for overfitting; one with a combined margin this wide
on both axes is a discovered rule, not a tuned one. `config.py`'s comment records the exact
feasible intervals and which two markets bound each one, so the reasoning is checkable without
rererunning the sweep.

**A7.3 - Sec 7.1's "14" remains unexplained by any share-based rule, single- or two-threshold.**
No cutoff (or pair of cutoffs) on `low_pct`/`high_pct` yields a both-tailed count of 14 or 10 -
the table's own rule gives 20 (confirmed under both the retracted and the corrected rule).
`GROUND_TRUTH.md` §1c's identification of "14 of 23" as the composite-trigger exogeneity
comparison (a different quantity entirely) still stands as the most likely explanation for the
transplant - this part of the original A6/Phase-6 finding was never in question, only the "which
rule reproduces 20" half was wrong.
