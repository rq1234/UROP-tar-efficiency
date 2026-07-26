# results/exports/ — generated for the paper (current 23-market run)

## Round 10 (JEF referee priorities) — Priorities 1–3 + validated fast grid. (P4.1/P5/P8/P9 queued; P6/P7 fetches + LOO deferred.)
Support files: `threshold_bootstrap.csv`, `pooled_bootstrap_gaps.csv`, `min_regime_trimming.csv`,
`min_regime_summary.csv`, `rw_band_validation.csv`.

- **Validated fast grid (enabling the bootstrap):** a vectorized spec=1 grid search that **reproduces
  the repo's `find_optimal_thresholds` to 1e-9 on all 23 markets** and is **347× faster** (4.1 ms vs
  1.4 s/fit). This is what makes the ≥1000-rep full-pipeline bootstrap feasible; every draw re-runs the
  complete grid search (thresholds and labels re-estimated, not held fixed).
- **Priority 1 (full-pipeline threshold uncertainty) — DONE (B=1000, seed=20260722; full grid
  re-estimated every draw).** Two clear messages:
  - **Pooled gaps are ROBUST** (calendar-month cross-section resample, every market's thresholds
    re-estimated per draw, cross-market dependence preserved): **MR-RW +8.18 [+2.51, +15.41]** and
    **EXP-RW −10.88 [−18.23, −4.32]** — both 95% CIs exclude 0. The aggregate discount survives full
    threshold uncertainty. → `pooled_bootstrap_gaps.csv`.
  - **Per-market estimates are IMPRECISE, and share precision is scheme-dependent.** Threshold *levels*
    are moderately precise (c₂ 95% width ~1.0 under wild, ~2.7 under block). Regime *shares* are precise
    only under the **wild** bootstrap that conditions on the observed CCI path (**EXP share ±13pp**, RW
    ±37pp) and become very wide when the trigger itself is resampled (block: EXP ±60pp). Individual
    slope stars are fragile: b_EXP 95% CI excludes 0 in only **5–6/23** markets, b_MR in 0–3/23.
    Boundary/degenerate draws are rare (≤3% / ≤1%). **Recommendation: report the wild (conditional)
    intervals as primary and the block as the conservative bound; attach these CIs to Table 4.1 and
    de-emphasise per-market coefficient stars.** → `threshold_bootstrap.csv` (all four schemes).
- **Priority 3 (validate the imposed RW band) — the restriction holds.** Unrestricted middle-band slope
  b_RW at the baseline thresholds: 16 negative / 7 positive; **6/23 significant at raw p<0.05 but 0/23
  survive Benjamini-Hochberg (q=0.05)**. Median b_RW = **−0.0063** (95% CI half-width ~0.013, includes 0
  for all). Explicit definition recorded: the positional RW share counts as "validated efficient" only
  where b_RW fails to reject the imposed RW at BH q<0.05 — and since **no market rejects**, the positional
  and validated RW shares coincide (no market flagged). This empirically justifies the b_RW=0 main spec.
  → `rw_band_validation.csv`.
- **Priority 4.1 (formal Wald: TAR high-band == fixed-above-90) — NOT distinguishable.** b_EXP=−11.28
  vs b_above90=−4.36, difference −6.92, but Var(diff)=113 (DK) → **Wald does not reject equality (DK p≈0.5;
  calendar-block bootstrap p=0.62).** So the earlier "TAR beats the naive sort" (from each coefficient's
  own significance vs 0) does **not** survive the direct comparison the referee requested. → `wald_tar_vs_fixed.csv`.
- **Priority 4.3 (recursive/expanding-window horse race, final-vintage) — complementary, TAR not dominant.**
  Labelling with thresholds & 10/90 cutoffs estimated on *past data only*: recursive high-band forward
  means TAR −16.93 vs fixed −21.92; predictive R² TAR 0.013 vs fixed 0.008 (RMSE/MAE identical ~25/18).
  Encompassing (DK): **both tar_EXP (−18.46, p<0.001) and pct_hi (−14.00, p=0.001) are individually
  significant** — neither high-band definition encompasses the other; MR/low bands add nothing. Net:
  the TAR high band carries *some* independent signal recursively but is not superior to the naive
  percentile sort. → `recursive_horserace.csv`.
- **Priority 5 (publication lag + dependence corrections).** EXP-RW gap: lag-0 −16.2 (DK p=0.020, block
  0.05/0.02/0.008); lag-1 −15.9 (DK p=0.025, block 0.055/0.044/0.025) — robust; **lag-2 −12.3 loses
  significance under the block bootstrap (p 0.08–0.10)**. Threshold shifts under lagging are tiny. → `publag_corrected.csv`.
- **Priority 8 (scale/comparability).** (a) A fixed level of 100 sits at the 38th–51st national percentile
  (comparable), but the *thresholds* map to wildly different domestic percentiles — 97.7 → **4th–28th**,
  101.4 → **63rd–87th** — so centring at 100 gives a common numerical scale, not distributional
  comparability where the thresholds operate. (b) Normalized local re-estimation (Greece/Turkey): shares
  shift under z-score/percentile normalization (Turkey RW 42%→9% under percentile), partly because the
  repo's fixed 2.0-point minimum-band constraint is not scale-invariant. → `common_level_scale.csv`, `normalized_local_runs.csv`.
- **⚠ Priority 9 (placebo 50→1000 + vol-clustering DGP) — revises the T1 verdict.** At B=1000: against an
  **iid** null the real RSS improvement exceeds it (emp p<0.05) in 9/23 (median real pctile 91); against a
  **block-resampled (vol-clustering, heavy-tailed)** null, only **3/23** (median 80). So against a realistic
  null the TAR fit is **largely not distinguishable from chance** — the earlier T1 "distinguishable"
  claim (50 iid draws) does not hold and must be softened; do not claim a random walk "cannot" reproduce
  the fit. → `placebo_1000.csv`.
- **Priority 2 (minimum-regime trimming).** All 23 markets remain feasible under every rule
  (5/10/15% and 20/30/40 obs). The pooled **EXP-RW gap attenuates but stays negative** (baseline −15.5 →
  −13.2/−7.7/−5.1 at 5/10/15%; −12.6/−8.8/−7.7 at 20/30/40 obs). RW-share ranking Spearman vs baseline
  falls as the constraint tightens (0.84→0.25) — the fine ranking is threshold-rule-sensitive (consistent
  with Y1/Y4/P4d). The 1997–2000 EXP concentration is itself rule-dependent: near-total under loose rules
  (32/33) but diluted when a ≥15% EXP band is forced (20/118). → `min_regime_trimming.csv`, `min_regime_summary.csv`.

---

## Round 9 (referee response, PIPELINE tasks) — P1, P2 done; P3–P8 roadmap below.
Support files: `regime_dynamics_audit.csv`, `efficiency_ranking_two_metrics.csv`.

- **P1 (regime-dynamics audit, R1/R2) — the central-attack answer.** Re-expressed each state's
  intercept as its **state-conditional mean monthly return** (equivalent to demeaning the lagged log
  price; thresholds/shares unchanged, intercept now rebasing-invariant). Results: **explosive root
  present in 0/23** (no β_EXP>0; all reversal slopes) — the "explosive" name is not an AR-root claim;
  **correction dynamics (β_MR<0, one-sided 5%) present in 11/23** low states. The uninterpretable
  "α₃ median ≈1.6" is replaced by the EXP-band state-conditional mean return: **median +1.03%/mo,
  sd 2.96**, range −7.4 to +7.4. Drift/residual-sd ratios per state are in `regime_dynamics_audit.csv`.
  Prose consequence: keep A&S names but state plainly which dynamics are present (MR in ~half, explosive
  root in none); "explosive" = high-sentiment positional band with a modest, noisy positive drift.
- **P2 (two-metric efficiency, R2).** Metric A = positional RW share (76.9% mean). Metric B = efficient
  unless the outer-band slope is significant at 5% (A&S's stricter convention) → mean **80.2%**. The two
  rankings correlate **Spearman 0.878 (p=3.7e-8)** — the efficiency ordering *is* robust to the metric
  choice (contrast Y1/Y4: not robust to the drift spec). Biggest movers: twse 8→1, hangseng 7→13,
  athex 4→10. Reserve "weak-form efficient share" for Metric B. → `efficiency_ranking_two_metrics.csv`.
- **P4 (horizon-test rebuild, R5/R6/R9) — one big honest limit + several robustness confirms.**
  - **P4c leave-episode-out is the headline: dropping 1997–2000 leaves exactly ONE episode (Spain
    2018, −14pp).** The explosive discount is almost entirely a **1997–2000 (dot-com + Asian-crisis)**
    phenomenon; outside that window there is essentially no replication. Must be stated plainly — it
    bounds Contribution 3's generality and is consistent with X2's post-2015 null.
  - **P4a:** excluding the 7 AFC-*onset* spells still leaves episode mean **−11.45pp, t=−2.58, p=0.017**
    (n=23) — so it is the whole 1997–2000 window, not specifically the Asian crisis. The AFC-onset
    spells themselves average −26.84pp (t=−2.41, p=0.052, n=7).
  - **P4b one-index-per-country** (drop ta35/hscei/lq45 → 20 markets): robust — 12m EXP −6.85 (p<1e-21);
    episode −14.93, t=−2.99, p=0.006 (n=26).
  - **P4d fixed-band horse race:** with TAR dummies AND fixed 10th/90th CCI-band dummies jointly (DK),
    the **TAR EXP label is significant (−11.28, p=0.019) while the fixed >90th band is not (p=0.59)** —
    the estimated label adds beyond the naive sort (good for Contribution 3). But per-market RW share
    under fixed common bands vs estimated thresholds is rank-**uncorrelated (Spearman 0.016)** — another
    hit to fine-ranking robustness (levels similar, 76.9% vs 80.2%). → `horizon_test_rebuilt.csv`,
    `episodes_exp_ex_afc.csv`, `horse_race_sort.csv`.
- **P6 (comparability, R7).** (a) The global thresholds map to very different **domestic percentiles**
  across national CCI distributions (global c₂ at the 43rd–86th national percentile, c₁ at 8th–41st) —
  evidence *against* strict "same meaning everywhere." (b) Re-running the panel with the trigger
  transformed to its full-sample percentile rank gives RW-share rank corr **0.565** (mean |diff| 18pp) —
  comparability survives only *moderately* in practice, not fully (the grid discretisation, not just
  monotonicity, matters). → `cci_distribution_diagnostics.csv`, `percentile_trigger_run.csv`.
- **P7 (diagnostic hardening, R10).** (a) Fisher-z 90% CIs added for all 25 ρ (median half-width 0.054)
  → `appendixC_with_se.csv`. (b) The 0.40 cutoff separates {NZL, GRC, TUR} from the rest, but the
  boundary pair TUR(0.376)/CZE(0.415) has **overlapping 90% CIs → the cutoff is a practical screening
  value, not a sharp threshold** → `cutoff_loco.csv`. (c) National–global CCI co-move far more in crises
  (median ρ: full 0.57, **GFC 0.77, COVID 0.94**) — decoupling is a normal-times phenomenon → `crisis_window_rho.csv`.
- **P8 (timing/vintage, R4).** Publication-lag robustness: 12m EXP discount is stable under a 1- or
  2-month label lag (−7.49 → −7.27 → −6.57, all p≈0) → `horizon_test_publag.csv`. Vintage: the pipeline
  uses the **final-vintage** OECD series, so Option B = "frozen-threshold stability under the final
  vintage," not a real-time forecast; an ALFRED real-time pull was **not** done in this offline run
  (documented) → `vintage_availability_note.md`.
- **Deferred by decision:** P3 (full-pipeline bootstrap + regime-count — compute budget), P5 (LOO
  GDP-weighted CCI — needs official weights/method; only approximable here), and P4 return-basis
  variants (USD/CPI/total-return fetches). Flagged for the supervisor per Part 3.

---

## Round 8 (Y1–Y3) — hardening runs. One STRONG win (Y2), one result that goes AGAINST the intended defense (Y1). Reported as reproduced.
Support files: `rank_stability_drift.csv`, `permutation_exp.csv`.

- **⚠ Y1 (rank stability under no-drift) — DOES NOT support the intended defense. Verdict verbatim:**
  *"ranking NOT robust: Spearman 0.050; top-8 preserved 2/8; bottom-8 preserved 3/8."* Re-estimating all
  23 markets under the no-drift spec (spec=0, same trigger/grid/b₂=0) reorders the efficiency ranking
  almost completely (Spearman **0.050**, p=0.82; mean RW-share change **22.9pp**, max 76.4pp for ta125).
  So Section 4.2/7.2 **cannot** claim "the ranking is robust to the specification A&S flag as decisive" —
  it isn't. **Honest interpretive nuance (in `rank_stability_drift.csv`):** the no-drift optimiser places
  *degenerate* thresholds — c₂ falls **below 100** (the CCI mean) for several markets (ta125 c₂=98.46,
  ipc 98.54, hangseng 98.88), which is economically nonsensical for a euphoria upper bound. So the
  reshuffling reflects the *pathology of the no-drift model*, not a credible alternative ordering. The
  defensible line is therefore **not** "the ranking is spec-robust" but "the switching-drift spec is the
  economically appropriate one; the no-drift spec A&S invoke produces degenerate thresholds." Farid's call
  on framing — but the robustness claim as originally hoped is **not** available.
- **⚠ Y4 (fair spec-robustness: switching spec=1 vs constant-drift spec=2) — still not robust.** The
  constant-drift spec is *not* degenerate (c₂<100 for only **1** market vs 5 under no-drift), so this is
  the fair A&S comparison. Result: **Spearman = 0.417 (p=0.048)**, mean RW-share change 9.1pp; top-8
  preserved 4/8, bottom-8 5/8. So even between the two economically sensible specs the ranking is only
  **weakly-to-moderately** correlated — the "ranking is robust to drift specification" claim is **not**
  supported even in its fairest form. Honest positive that *is* available: **every market is highly
  efficient under both specs** (RW share 50–98% under switching, 32–98% under constant), so the broad
  qualitative finding — "these markets sit overwhelmingly in the efficient state, regardless of drift
  spec" — holds; only the fine ordinal ranking is specification-sensitive (the RW shares cluster in a
  narrow 80–95% band for most markets, so small level changes reshuffle ranks). Columns added to
  `rank_stability_drift.csv` (`rw_pct_constdrift`, `rank_constdrift`).
- **Y2 (circular-shift permutation test) — STRONG win. p-value verbatim:** episode-mean-excess
  **p = 0.0000** (i.e. **0 of 5000** circular-shift nulls were as negative as the observed −15.04pp;
  observed sits at the **0th percentile**, null mean +0.05pp, sd 3.99). Pooled EXP−RW gap −15.49pp:
  same, 0/5000, p=0.0000. Randomly re-timing each market's explosive spells (preserving spell count,
  length, and every return-autocorrelation feature) **destroys** the discount — so the result is carried
  by the *alignment of the labels with forward returns*, not by cross-market correlation or independence
  assumptions. This is the strongest evidence yet for the explosive discount and does not rely on the
  30-episodes-independent assumption. Seed=20260722, B=5000. → `permutation_exp.csv`.
- **Y3 (MR horse-race, symmetry with X3) — confirmed.** MR coef **+3.31 (p=0.42)** without trailing →
  **+2.66 (p=0.45)** with trailing; both insignificant under DK, and trailing does not absorb an MR
  effect (there is no significant pooled monthly MR effect to absorb). Consistent with X3: the
  mean-reversion premium, like the explosive discount, is not a pooled-monthly-significant regression
  effect — the robust MR evidence is the within-market sign test (F6, 19/23) and rank-level results.

**Net of Round 8:** Contribution 3 (explosive discount) is now very strongly defended (Y2 permutation +
X1 episode test); Contribution 1's *ranking-robustness-to-drift* defense is **not** available as hoped
(Y1) and should be reframed around the no-drift spec's degeneracy.

---

## Round 7 (X1–X8) — referee-response runs. Several are paper-changing; reported exactly as reproduced.
Support files: `horserace_label_vs_trailing.csv`, `episode_dep_corrected.csv`, `oos_exp_dep_corrected.csv`,
`matched_window_localisation.csv`, `turkey_real_return.csv`, `kappa_stability.csv`,
`drift_variance_ratio.csv`, `rho_confidence_intervals.csv`.

- **X3 (DECISIVE horse race) — verdict verbatim:** *"labels NOT subsumed by past return: EXP coef
  −14.07(a)→−14.06(c) when trailing added [ratio 1.00]; trailing insignificant (p=0.55). CAVEAT:
  under Driscoll-Kraay the pooled monthly EXP effect is marginal (p=0.057) with or without trailing,
  so contribution-3 significance rests on the episode-level test (X1), not this regression."* i.e. the
  regime label carries independent information (trailing 12m return neither predicts forward returns
  p=0.51 nor absorbs the EXP effect), **but** the pooled monthly EXP discount is only borderline once
  dependence-corrected. **Write contribution 3 around the episode-level result (X1), not the pooled
  monthly regression.** → `horserace_label_vs_trailing.csv`.
- **X1 (episode test, dependence-corrected) — SURVIVES.** The 30 episodes occupy **5 calendar-year
  clusters** (1997:2, 1998:6, 1999:15, 2000:6, 2018:1 — 29 in 1997–2000, exactly the concern). Excess
  vs 0: year-cluster-robust t=−4.68 p<0.001; year cluster-bootstrap (B=2000) p<0.001; **year-collapsed
  (most conservative, 5 obs) mean −18.31pp, t=−3.16, p=0.034.** Even the most conservative correction
  keeps it significant. This is the robust inference for the explosive discount. → `episode_dep_corrected.csv`.
- **X2 (OOS EXP, dependence-corrected) — DOES NOT survive.** The 76 post-2015 EXP months come from only
  **4 years and 4 markets.** Gap −9.84pp, but **moving-block bootstrap p=0.22, Driscoll-Kraay p=0.19.**
  The post-2015 out-of-sample explosive result is **not** statistically distinguishable once corrected;
  report it as suggestive only (consistent with R4d). → `oos_exp_dep_corrected.csv`.
- **X4 (matched-window localisation) — the Turkey story is mostly a WINDOW effect.** On the *same*
  240-month window as the country run: Turkey GLOBAL **6/38/56** vs COUNTRY 7/45/48 — nearly identical
  (the headline "94% RW under global" was the longer 1997–2026 window, not the trigger). Greece is
  different: GLOBAL **7/83/10** vs COUNTRY 44/31/25 on the matched window — the trigger change is real
  for Greece. **The paper's Turkey localisation claim needs revising; Greece's holds.** → `matched_window_localisation.csv`.
- **X5 (real-return Turkey).** Deflating bist100 by Turkish CPI (`TURCPIALLMINMEI`) and re-running the
  country-CCI TAR gives **6/11/82** (MR/RW/EXP), b_EXP=−0.099*** vs nominal-country 7/45/48, b_EXP=−0.034.
  Deflation does **not** remove the explosive classification (if anything more EXP), so the referee's
  "nominal inflation drives the explosive months" is not supported in the feared direction — **but** the
  real series is dominated by the post-2021 hyperinflation break, so read cautiously. → `turkey_real_return.csv`.
- **X6 (chance-corrected stability) — undercuts the CCI stability argument.** Global-CCI Option A-vs-B:
  mean Cohen κ **0.740** (range −0.147 to 1.0), mean agreement 87.7%. S&P 500 MCSI A-vs-B: κ **0.944**,
  agreement 99.3%. On a like-for-like, chance-corrected basis **MCSI is *more* stable than the CCI**
  (the raw 88% agreement flattered the CCI). Consistent with T2 — lean the selection argument on the
  OOS MCSI *misclassification* + amplitude mechanism, not on stability. → `kappa_stability.csv`.
- **X7 (drift/variance).** EXP drift/sd median 17.77 vs MR 0.23; EXP|ratio|>MR in 17/22. **Caveat: α is
  log-price-level dependent**, so these cross-market ratios are inflated and not a clean "drift vs
  variance" statistic — report with the caveat or drop. → `drift_variance_ratio.csv`.
- **X8 (sampling error on the diagnostic).** Fisher 95% CIs: Turkey ρ=0.376 **[0.26, 0.48]** and
  Czechia ρ=0.415 **[0.32, 0.50]** — **overlap**, so the 0.04 "gap" is within sampling error. → `rho_confidence_intervals.csv`.

---

## Round 6 (W1–W5) — three referee fixes. Support files: `table4_drift.csv`, `fdr_exogeneity.csv`, `fdr_coefficients.csv`.

- **W1 — the "explosive" label, justified by the drift α₃.** At the Table-4.1 thresholds, the
  explosive-state intercept **α₃ is positive for all 22 markets** with EXP months (median **1.585**,
  range 0.339–8.382, **20/22 significant at 5%**). So the expansionary force in the model does live in
  the drift, not the slope — `table4_drift.csv` tabulates α₃, its SE, t, and stars per market for
  Table 4.1. **Honesty caveat (also in the file):** the *net contemporaneous* return during EXP months
  is only positive for **12/22** markets (median +1.03%/mo), because the reversal slope β₃<0 offsets
  α₃. So α₃ backs "elevated drift," but the state's defining economic content remains the **negative
  12-month FORWARD return** (the reversal that follows). Recommend the paper present α₃ *and* frame
  "explosive" as the euphoria-triggered regime name (after Ahmed & Satchell), not a claim of an
  explosive AR root (β₃<0 rules that out).
- **W2 — EXP result reported BOTH ways (Japan in/out).** Excluding Japan (paper): EXP 12m **−7.49%**
  (n=615), p=4e-26. **Including Japan's 264 EXP months: −6.08%** (n=879), p=8.9e-36. Japan-EXP alone
  −2.78% (n=264); RW baseline +8.01%. Including Japan attenuates the discount by ~1.4pp but it stays
  large (−6.08 vs +8.01 → a −14pp gap) and *more* significant. Robustness line for Section 6.3 — the
  explosive discount is not an artefact of the one-directional Japan drop.
- **W3 — multiple testing, exogeneity screen.** 56 Granger tests: **24 FAIL at raw p<0.05 → 19 survive
  Benjamini-Hochberg (q=0.05).** The 5 that drop are borderline markets (p≈0.02–0.046), none of which
  are in the 23-market panel, so the panel is unaffected. → `fdr_exogeneity.csv`.
- **W4 — multiple testing, coefficient stars.** 45 coefficient t-tests (b_MR + b_EXP): **33 significant
  raw → 30 survive BH.** → `fdr_coefficients.csv`.
- **W5 — ready-to-paste limitations sentence** (in the manifest, uses the W3/W4 numbers): a BH
  correction leaves 19/24 exogeneity and 30/33 coefficient rejections intact, so the qualitative
  pattern is unchanged but individual stars should be read as descriptive.

---

## Round 5 (V1–V5) — 21-July audit verification. TWO tasks came back as CORRECTIONS, not confirmations.
Support files: `reverse_granger_extra.csv`, `gcci_labels_2025_2026.csv`, `mcsi_2025_2026.csv`,
`figures/figure6_3_episodes.png`.

- **⚠ V1 (audit A3) — the paper's claim is WRONG.** S&P 500 return → Δ(US CCI), q=4, identical to the
  Appendix-A screen: **F = 3.5358, p = 0.0075 → FAILS** exogeneity (p < 0.05: S&P returns *do*
  Granger-cause the US CCI). The report's assertion that "the S&P 500 passes the reverse-Granger
  screen under the US CCI" is **false** and must be rewritten to say it fails. (This is actually
  *consistent* with the paper's core thesis — large markets fail exogeneity — and matches the
  earlier mixed-trigger screen, sp500+US-CCI p=0.0075.) → `reverse_granger_extra.csv`.
- **⚠ V2 (audit B3) — "22 markets" is wrong; the true count is 21.** The 30 explosive episodes are
  contributed by **21 distinct markets** (Japan excluded, Bovespa 0% EXP → max 21, and all 21 appear):
  `aex, athex, bist100, hangseng, hscei, ibex35, ipc, jkse, klci, kospi, lq45, merval, psei, set,
  shanghai, smi, sti, szse, ta125, ta35, twse`. Episode count = 30 (matches S2). Section 6.3 must
  read "21 markets".
- **V3 (MCSI-cascade discriminator, A1) — CONFIRMED.** S&P 500 global-CCI labels (Option B frozen
  c1=97.53/c2=101.93; Option A c1=97.67/c2=101.93): **Aug 2025 → Apr 2026 = RW under both options**;
  MR appears only in **May 2026, and only under Option A** (gCCI 97.552 < 97.668; Option B keeps it RW
  at c1=97.526). So the global CCI read the 2025–26 rally as efficient/RW and gave at most a single,
  final-month MR signal — a much later, milder signal than MCSI's. The discriminating clause holds.
  → `gcci_labels_2025_2026.csv`.
- **V4 (MCSI re-pull, A1 [VERIFY]) — CONFIRMED + frozen c1 verified.** Frozen S&P 500 MCSI Option-B
  **c1 = 59.677** (confirms the assumed 59.7). FRED `UMCSENT` 2025-06…2026-05:
  60.7, 61.7, **58.2, 55.1, 53.6, 51.0, 52.9, 56.4, 56.6, 53.3, 49.8, 44.8**. **Cascade start =
  Aug 2025** (first month ≤ c1); MCSI stays below c1 every month Aug 2025 → May 2026; **minimum 44.8
  (May 2026)**. So MCSI flags the whole rally as MR while the global CCI (V3) reads it as RW — the
  two-trigger contrast is real. → `mcsi_2025_2026.csv`.
- **V5 (audit B4) — the referenced figure now exists.** `figures/figure6_3_episodes.png`: one bar per
  explosive episode (12m forward excess vs own-market RW baseline), sorted, zero line, caption N=30 /
  mean −15.04pp / t=−3.46, p=0.0017 / 26-of-30 negative. The old `figure6_3_early_late_exp.png` was
  **kept** (not deleted); the episode chart is added under the name Section 6.3 cites.

---

## Round 4 (T1–T5) — appended to the manifest (rows T1…T5). No expected values on T1/T2; reported as-is.
Support files: `placebo_thresholds.csv`, `placebo_summary.csv`, `stability_scale_adjusted.csv`,
`unrestricted_b2.csv`, `cci_CHN_fetched.csv`, updated `localised_runs.csv`.

- **T1 (placebo grid search) — VERDICT: threshold placement is DISTINGUISHABLE from trigger-driven.**
  50 placebo random-walks-with-drift per market (matched to each market's own T, mean, vol;
  seed=20260721), identical spec=1 grid search vs the REAL global CCI, 100-point grid (same as the
  real run). Two findings, and the second is the one that matters:
  - **Location is partly mechanical:** **25.5%** of the 1,150 placebo (c1,c2) pairs land inside the
    real cluster bands (97.02–98.45 & 101.19–102.43). So a referee is *right* that the *position* of
    the thresholds partly reflects the trigger's own percentiles — as F2 warned.
  - **But the fit is not:** the real markets' RSS improvement from splitting sits at a **median 94th
    percentile** of their placebo distributions (**18/23 markets ≥90th**; only shanghai 48, psei 58,
    kospi 58, nikkei 68 sit mid-pack — the degenerate/MR-saturated markets). The thresholds *earn*
    their placement from genuine price dynamics: a pure random walk against the same CCI almost never
    reduces RSS as much. This is the direct rebuttal to the "estimation is mechanical" objection.
  - → `placebo_summary.csv` (per-market percentiles, band share, real-vs-placebo RSS percentile),
    `placebo_thresholds.csv` (all 1,150 runs). Seed 20260721 recorded in the manifest.
- **T2 (scale-adjusted stability):** normalising the rolling-threshold ranges by each trigger's σ and
  span **removes the CCI's apparent advantage.** c1 range/σ: **global 4.12 > MCSI 3.32 > US-CCI 2.84**;
  c1 range/span: global **0.86** > MCSI 0.74 > US-CCI 0.65. i.e. the global CCI's thresholds span a
  *larger* fraction of their own scale than MCSI's — the raw "4.8 vs 46 units" comparison was a
  scale artefact. **Section 3.2 should lean on the OOS MCSI failure + amplitude-adjustment mechanism
  (scale-free), not the unit comparison.** CAPE skipped (archived rolling CSV has no trigger series).
  → `stability_scale_adjusted.csv`.
- **T3 (China):** China CCI fetched fresh from FRED `CSCICP03CNM665S` (408 obs, 1990-01…2023-12,
  saved to `cci_CHN_fetched.csv` — `data/` untouched). Shanghai T=317 c1=100.77 c2=**104.37** MR/RW/EXP
  71/27/**1.6**; SZSE T=316 similar. **The 2006–08 and 2014–15 booms do NOT classify as explosive
  (0/35 and 0/23 EXP months).** China's CCI has such high amplitude that c2≈104 is almost never
  breached, and corr(Δglobal, Δchina)=**0.25** (weak). **China is not a clean third localisation
  case — it is a finding about the diagnostic** (amplitude adjustment behaves differently in China).
  Appended to `localised_runs.csv`.
- **T4 (pre-1990 second era):** confirmed the session preview exactly — late-80s global CCI peak
  **101.84 (1988-09)**; HangSeng (c2=102.01) and PSEi (102.22) never reach threshold; Nikkei
  degenerate (82 EXP months); **STI alone: one episode 1988-08…1989-01, 12m forward +29.8pp,
  excess +25.9pp** (the 1990 crash sat beyond the 12-month window). "Second era unrecoverable;
  1 episode, positive excess." No paper change unless Farid wants the defensive sentence.
- **T5 (unrestricted middle band):** freeing b2 (3 free regimes, same grid): **8/23** markets show a
  RW slope ≠ 0 at 5% (median b2 = **−0.0087**, economically small; bovespa the degenerate outlier at
  b2=−0.050, t=−13.9). So the middle band is *mostly* but not perfectly efficient — one honest
  sentence for Section 7.2. → `unrestricted_b2.csv`.

---

## Round 3 (S1–S3) — appended to the manifest (rows S1…S3). All matched the session previews exactly.
Support files: `localised_runs.csv`, `episodes_exp.csv`.

- **S1 (Table 5.1 provenance):** standalone country-CCI TAR (identical code path, independent of
  the rejected mixed-trigger file) — **Greece** T=317, c1=99.08, c2=101.59, 43.5/31.2/25.2;
  **Turkey** T=240, c1=95.17, c2=100.85, 6.7/45.4/47.9. Matches manifest G2/G4 exactly → only the
  source note under Table 5.1 changes. → `localised_runs.csv`.
- **S2 (episode-level EXP test — referee-proof headline for Sec 6.3):** episode = unit of
  observation, own-market RW baseline, Japan excluded. **30 episodes**, mean length **20.5 months**,
  mean 12m excess **−15.04pp**, one-sample **t=−3.46, p=0.0017** (df=29), **26/30 negative**.
  Removes the overlapping-window and cross-market-correlation objections in one move.
  → `episodes_exp.csv` (per-episode detail). Reproduced the preview to the decimal.
- **S3 (MR power sentence):** **222** distinct MR calendar-months collapse into **9 clusters**
  (gap ≤3 months): 1990-09..1991-02; 1991-10..1994-03; 2001-10..2001-11; 2002-09..2003-09;
  2005-09..2005-10; 2007-10..2014-12; 2015-08..2015-09; 2016-03..2016-09; 2020-02..2026-05.
  The MR premium is identified from ~9 global episodes → the corrected test is underpowered,
  not evidence of a zero premium.

**Not added (per plan):** RW-share vs national-global-correlation scatter (only 8 markets have both;
Spearman −0.60, p=0.12; Japan a documented level-offset). Suggestive, not evidence — Section 5's
defence stays the selection-rule sentence + the Appendix C panel diagnostic.

---

## Robustness round 2 (R1–R4) — appended to the manifest (rows R1…R4d)
Fresh from the pipeline; original manifest rows unchanged. Support files:
`expn_check.csv`, `horizon_test_exclusions.csv`, `appendixD_optionAB_agreement.csv`.

- **R1 (constant EXP n):** **REAL.** Min gap between a market's last EXP month and its
  sample end (over pooled-EXP markets, excl. Japan) = **94 months** (ibex35, last EXP 2018-07);
  even Japan's last EXP (2021-09) is 56 months back. Every EXP month has a full 12-month
  forward window ⇒ n_EXP=615 is genuinely constant across horizons, not a join error (`expn_check.csv`).
- **R2 (pool exclusion):** means stay within ~1pp and MR>RW>EXP ordering + significance survive.
  21-mkt (−Greece,−Turkey): +13.77/+7.70/−6.55; 20-mkt (−Japan): +13.78/+7.68/−6.55;
  19-mkt (−Spain): +13.73/+7.85/−7.39. All pMR-RW<2e-5, pEXP-RW<2e-21. Stable.
- **R3a (return basis):** **local currency; price-return index close (yfinance `auto_adjust=True`
  — index tickers carry no dividend distributions, so dividends effectively NOT included);
  nominal.** Source `src/collect_data.py:44,47`. (Sentence for Section 3.3.)
- **R3b (drop Turkey+Argentina):** +12.45/+6.26/−5.94 (21 mkts). RW baseline falls ~1.75pp
  (as expected); MR-RW and EXP-RW orderings/significance survive (p<9e-7, p<4e-16).
- **R4 (Option A vs B agreement, Appendix D):** panel agreement **88.17% full / 84.63% post-2015**
  (in-sample cutoff = **2015-06**, the pipeline's `INSAMPLE_END`, not 2015-12 — flagged). Of the
  1,058 disagreeing months, **38.8%** sit within 0.25 CCI units of a threshold — the number to put
  behind Appendix D's "boundary months" sentence. Biggest disagreer = Mexico (ipc, c1 99.27→97.53).
  Per-market table in `appendixD_optionAB_agreement.csv`.
  - **R4d (Option-B OOS, Sec 7.2):** 12m horizon on post-2015 months, B labels — MR +10.03 (326) /
    RW +8.87 (2141) / EXP −0.97 (76). **MR-RW NOT significant OOS (p=0.48)**; EXP-RW stays
    significant (p=2.1e-5) but on only 76 EXP obs. Honest finding: the MR premium weakens sharply
    out of sample (few EXP months remain post-2015, per R1).

---

## ⭐ paper_numbers_manifest.csv — single source of truth
`paper_numbers_manifest.csv` (**216 rows** — Rounds 1–8 (A–Y) + Round 9 (P1–P8 referee) + Round 10
(JEF priorities 1–9: fast-grid bootstrap, min-regime, RW-band validation, Wald, publag, scale, placebo-1000, recursive); columns `id, paper_location, description, value`.
Note: "P#" ids appear in two plans — Round 9 uses P1_mr*/P2_metricB*/P4_*/P6–P8; Round 10 uses
P1_boot*/P1_pooled*/P2_pct*/P3_bRW*. Each row's `description` disambiguates.)
holds **every number the paper cites, recomputed fresh** from `data/combined/monthly_panel.csv`,
the CCI series, and the estimation code — nothing copied from old results/weekly reports
except rows explicitly tagged `HISTORICAL`. Diff the paper against this file and correct any
disagreement. Supporting fresh CSVs written alongside it:
`efficiency_ranking_fresh.csv` (Block B), `appendixA_granger_global_cci.csv` (A6),
`appendixB_episode_coverage.csv` (H1), `appendixC_dcci_correlations.csv` (G5),
`F6_within_market_means.csv` (F6), `item4_country_cci_T_screen.csv` (G6),
`horizon_test.csv` / `horizon_test_exp_phase.csv` (D/E). Regenerated figures are in
`figures/` (figure4_1_thresholds, figure6_1_horizon_bars, figure6_2_distributions_12m,
figure6_3_early_late_exp) — every printed annotation is drawn from the fresh CSVs.

### Reproduction notes — where the fresh value differs from an expected/session value
Per the ground rule *"output the reproduced value; never adjust code to hit the expectation."*
Everything reproduced as expected **except**:
- **A7** — q=12 exogeneity on the 23: **22/23 pass** (as expected), but **Japan p = 0.0420**,
  not the noted ~0.027. Japan still fails at q=12; only the exact p differs.
- **F1** — tercile bottom−top spread **+8.16pp** (session 8.2 ✓, effectively identical).
- **F2** — 10/90 spread **+22.14pp** (session had 21.1pp); cutoffs 98.39/101.40 match. Uses
  the fresh pooled CCI distribution — this **replaces** the session number.
- **F4** — block-bootstrap p's depend on the RNG seed (fixed at 12345): L=12 gives MR-RW
  p=0.211, EXP-RW p=0.083 (session ~0.16 / ~0.09 — same ballpark, non-significant / marginal).
  EXP-RW SE now nan-safe (997/1000 valid reps at L=12).
- **F6** — MR>RW is **19/23** (p=0.0026), not 20/23; MR exceptions = shanghai, szse, hangseng,
  klci. EXP<RW is **20/21** (p=2.1e-5) as expected; EXP exception = shanghai.
- **F5** — Driscoll–Kraay (statsmodels `hac-groupsum`, 11 lags) ran natively (no fallback):
  MR +6.59 p=0.179, EXP −15.50 p=0.040.
All Block A–E, G, H, I values matched expectations (incl. 12m MR +14.60/RW +8.01/EXP −7.49;
C4 global-CCI rolling c1 96.53–101.37 range 4.84; I2 FTSE no-drift RSS gap 0.018%).
`HISTORICAL` rows: C6, C7 (CAPE/BAA narrative — archived scripts, not re-run) and all of
Block J (Sec 7.1 composite story — generating scripts committed under `src/archive/`, values
cited from the Week 3 report, not regenerated this session).

---


All files below were generated **read-only** from the committed data
(`data/combined/monthly_panel.csv`, `data/sentiment/*`) and the committed results
CSV (`results/tables/global_cci_all_markets.csv`). No existing repo file was modified.
Global CCI latest month = **2026-05** (value 97.552); country CCIs end 2024-01 or earlier.

## Item 1 — raw data exports (for your own tests)
- **`prices_monthly.csv`** — long format `date, market, close`. Month-end closes for **all
  markets** with data in the monthly panel (20,910 rows). `market` is the short key
  (e.g. `sp500`, `nikkei225`).
- **`cci_series.csv`** — wide format `date, global_cci, cci_<CODE>…` (26 CCI columns,
  617 monthly rows). `global_cci` = OECD.Stat SDMX composite (`DSD_STES@DF_CLI`, REF_AREA=OECD,
  CCICP, amplitude-adjusted, 100 = long-run avg). `cci_<CODE>` = FRED `CSCICP03<ISO2>M665S`,
  snapped to month-end. Note `cci_POL`/`cci_CZE` correspond to markets (`wig20`,`px`) with no
  equity data in the panel.

## Item 2 — horizon tables (replaces old 14-market Tables 6.1/6.2)
Stated **membership rule** (one rule, applied uniformly):
> All 23 markets in `global_cci_all_markets.csv`. Each month is classified MR/RW/EXP by the
> **global** CCI against that market's own full-sample **Option-A** thresholds (c1,c2).
> Forward cumulative log-returns are pooled across the 23 markets. **Japan (nikkei225) EXP
> months are excluded from the pooled EXP cell only** (its c2=99.87 is degenerate — 61% of
> months would be "EXP"); Japan's MR and RW months are kept.

- **`horizon_test.csv`** — per horizon (1/3/6/12m): MR/RW/EXP mean forward log-return %, n
  each, Welch p (MR-vs-RW, EXP-vs-RW), one-way ANOVA p.
  **12m headline:** MR **+14.60%** (n=1109), RW **+8.01%** (n=6676), EXP **−7.49%** (n=615),
  both tails p<0.001 vs RW. Matches `results/gcci/horizon_distributions_12m.png`.
- **`horizon_test_exp_phase.csv`** — early vs late EXP split (early = first ⌈L/2⌉ months of
  each EXP run). 12m: early +0.60% vs late **−15.94%**, p<1e-6. Japan excluded.
- **`horizon_test_per_market.csv`** — the 23 markets with T and MR/RW/EXP month counts (the
  pool composition behind the tables).

⚠ These p-values are **raw** (not overlap-corrected). Forward windows overlap month-to-month,
so the effective N is smaller than the nominal n; treat p<0.001 as directional, not literal.
Overlap-corrected inference is on your test list (item 1 unlocks it).

## Item 4 — T≥340 screen applied to the country-CCI runs
- **`item4_country_cci_T_screen.csv`** — every country-CCI market from
  `mixed_trigger_results.csv` with its T and pass/fail at both 340 and 240.
- At **T≥340**, only **6** survive: `asx200, smi, cac40, nikkei225, rut, ftse100`.
- **Removed by T≥340 (13):** omxcopenhagen (85), psi20 (129), omxhelsinki (130),
  omxstockholm (182), topix (192), bist100 (240), nzx50 (248), ipc (272), kosdaq (278),
  kospi (300), ftsemib (313), athex (317), tsx (335).
- This confirms your point: **every degenerate ≥70%-EXP case sits on a short sample** —
  Sweden 85% EXP (T=182), Finland 83% (130), Portugal 70% (129), Mexico 79% (272),
  Korea 72% (300), Japan 71% (408 — the exception, degenerate for a different reason).
- A **T≥240** bar keeps Greece and Turkey-country (the two markets your country-CCI section
  actually discusses) while still dropping Denmark/Finland/Sweden/Portugal. Pick the bar
  deliberately; both columns are in the file.

## Item 5 — appendix exports
- **`appendixA_granger_global_cci.csv`** — per-market reverse-Granger F, p, gate for the
  exogeneity screen (direction `return → d(globalCCI)`, n_lags=4, PASS if p>0.05), **all 57
  markets** (colcap = NO_DATA). This is the raw Appendix-A table; 32 PASS / 24 FAIL / 1 no-data.
- **`appendixC_dcci_correlations.csv`** — corr(Δglobal CCI, Δcountry CCI) in first differences,
  per country, with n and overlap window, sorted ascending (most-distinct first). USA is the
  most global-aligned (0.808); NZ/Greece/Turkey the most idiosyncratic (0.29–0.38).

---

## Item 3 — the mixed-study assignment rule (documented, decision still yours + Farid)
The rule that generated `mixed_trigger_results.csv` is in
`src/mixed_trigger_study.py:53-75` (`load_mixed_pair`):

> A market uses its **country CCI iff** (`market in OECD_CCI_MARKETS`) **and** the file
> `oecd_cci_{CODE}.csv` exists; **otherwise global CCI fallback.**

This is **NOT** the paper's stated rule ("global by default, localise only where the global
diagnostic fails"). It is "country CCI wherever a country file exists, **regardless** of the
global gate." That is exactly why Switzerland, South Korea and Japan appear as country-triggered
(blue) even though they pass the global gate. **This file is not the paper's rule** and should
stay out until item 3 is settled. The four Table-4 conflicts you found (US index S&P→Russell,
Canada 92%→52%, FTSE tail swap, the blue/global mismatch) are all downstream of this rule plus
the fact that `mixed_trigger_results.csv` is an independent run — none of them touch the
23-market global panel, which remains internally consistent.

**To make the mixed study paper-ready** you need to decide (a) US index, (b) Canada trigger,
(c) whether "localise" means *file-exists* or *global-gate-fails*, then re-export one
definitive per-market file. I can regenerate it in minutes once (a)–(c) are fixed.
