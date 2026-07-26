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
