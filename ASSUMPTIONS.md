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
field, as the README instructs. Rebuilt scripts are named `round09_*` / `round10_*` so the
collision cannot propagate into filenames.

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

**A4.6 — Round 10 remainder (`scripts/round10_remainder.py`), fixed vs residual gaps.**
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
`scripts/round02_pool_optionAB.py` reuses the frozen-threshold (Option B) method already in
`scripts/round07_dependence.py`'s `x6_kappa` (in-sample fit to `INSAMPLE_END`, applied out of
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

**A4.8 — Round 3 (`scripts/round03_episodes.py`) reproduces exactly; China rows (Round 4 T3)
deferred.** S1's athex/bist100 rows match `localised_runs.csv` to every printed decimal place,
and S3's MR-cluster count (222 distinct calendar-months, 9 clusters gap<=3 months) matches the
README's own boundary list exactly, date for date. The export's other two rows (shanghai/szse,
tagged `cci_CHN`) belong to Round 4's T3 ("China CCI fetched fresh from FRED
`CSCICP03CNM665S`... `data/` untouched") — not written here, since no `FRED_API_KEY` is
configured in this environment (checked: no `.env`, no matching shell env var) and `data/` may
not be modified to work around that. `write()` merges by `market` rather than overwriting the
file, so a future Round 4 T3 script can append those two rows without disturbing these.
