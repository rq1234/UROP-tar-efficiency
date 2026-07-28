# Data and Code Availability

This note describes how every quantitative claim in the paper can be checked against the
code and data in this repository, and reports the result of doing so.

## What is available

- **Data.** `data/` holds the raw and lightly processed series (equity indices, VIX, BIS
  credit gaps, ANFCI, BAA spread, CAPE, BCI, EPU, CCI) used to build the daily/monthly
  panels. `results/exports/`, `results/tables/`, and `results/archive/tables/` hold the
  committed outputs of the analysis pipeline as it stood when the paper's numbers were
  produced; these are treated as read-only ground truth and are never edited to match a
  claim.
- **Code.** `src/` and `scripts/` hold the full pipeline: data collection, the TAR grid
  search, exogeneity screens, bootstrap and Driscoll-Kraay inference, and the export
  scripts that produce the tables in `results/`.
- **Verification harness.** `verification_manifest.md` lists every non-figure numeric
  claim made in the manuscript (78 entries at the time of writing), each tagged with an
  ID, a tolerance class (exact / seed-sensitive / vintage-sensitive), and a priority.
  `scripts/verify_paper.py` reads this manifest, recomputes or looks up each target
  against the committed outputs in `results/`, and classifies every entry as MATCH, NEAR,
  MISMATCH, or NOT_REPRODUCIBLE. It writes `VERIFICATION_REPORT.md` (a human-readable
  table) and `outputs/rebuilt/numbers.json` (the same data, machine-readable). Nothing is
  recomputed from `data/` in this step, and no value is ever adjusted to force agreement
  — see the reproducibility rules in this repository's `CLAUDE.md`.

## Current result

As of this commit, all 78 non-figure manifest entries have a verdict:

| Verdict | Count |
|---|---|
| MATCH | 69 |
| NEAR | 5 |
| MISMATCH | 3 |
| NOT_REPRODUCIBLE | 1 |

Three findings from this pass are reported here specifically because they changed a
number in the manuscript rather than confirming one, and are offered as evidence that
the verification process finds real discrepancies rather than only confirming what was
already believed:

- **ANFCI firing rate (§3.2).** The manuscript's claim that the high-sentiment ANFCI
  state fires 80-90% of the time for European markets does not reproduce. The measured
  European firing rate (n=19 markets) has mean 47.1%, median 56.7%, and range
  1.3-83.0%. The manifest's separate claim that 9 of 19 European markets fail the
  exogeneity screen does reproduce exactly.
- **BAA spread figures (§3.2).** The manuscript's 0.56 percentage-point euphoria
  compression and 3.7 percentage-point GFC intra-window range are close to, but not
  exact matches for, the committed-data figures of 0.52pp and 3.62pp respectively. A
  live refetch of the underlying FRED series moves these by less than 0.02pp, so the
  gap is not a data-vintage effect.
- **CCI-EPU composite screen (§7.1).** The manuscript's claim of 18/23 indices passing
  a reverse-Granger screen with 10/23 covering both trigger tails is not reproducible
  from any committed archive table: the relevant export
  (`bic_cci_epu_tar_results.csv`) only overlaps 15 of the panel's 23 markets by name,
  with no alternate join key available, and none of those 15 rows show the tail
  pattern the manuscript describes.

Two further entries (RSS-flatness in §3.1, and the tail-coverage threshold rule
underlying Table 4.1) are classed NEAR/MATCH-with-refinement: the qualitative claim
holds but the precise stated figure needed adjustment, and the correct constants are
reported in the manuscript-correction record for this verification pass rather than
re-derived here.

## Reproducing the verification

```
python scripts/verify_paper.py
```

reads `verification_manifest.md`, checks every entry against `results/`, and rewrites
`VERIFICATION_REPORT.md` and `outputs/rebuilt/numbers.json`. `results/exports/CHECKSUMS.sha256`
records a sha256 hash for every file in `results/exports/`, so any future drift in that
directory relative to this commit is immediately detectable independent of git history.

## Known gaps

- One P3 entry (C50, the CCI-EPU screen above) is marked NOT_REPRODUCIBLE: the source
  table needed to check it does not contain enough overlapping markets to reconstruct
  the manuscript's claim, and no alternate source exists in this repository.
- Three P1-P2 entries are marked MISMATCH (E1, E2, C9); each is a specific, named
  disagreement between manuscript text and the committed table, documented in
  `VERIFICATION_REPORT.md` rather than silently resolved.
