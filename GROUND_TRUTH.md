# GROUND_TRUTH.md — TAR market-efficiency study (Global OECD CCI extension)

Reconstructed strictly from the code and saved outputs in this repo. No source files
were modified. Where a number is not in a saved output, it was reproduced by running a
**read-only** subcommand (screens only `print`; they write no files) or a scratchpad
script that only *reads* the panel/CSVs — these are flagged **[reproduced]** and the exact
command is given so the claim is checkable.

**One-line orientation.** The paper's headline panel is the **23-market Global-OECD-CCI
study**, produced by [src/global_cci_study.py](src/global_cci_study.py) and written to
[results/tables/global_cci_all_markets.csv](results/tables/global_cci_all_markets.csv)
(23 data rows). Several of the numbers in your notes ("48→27", "14 of 23", the
"96.8–98.2" band, the "14-market" horizon set) come from **earlier or adjacent studies**
(the Week-3/4 write-ups and the archived composite study), not from the current 23-market
run. Each is reconciled below.

---

## 1. SAMPLE CASCADE

### 1a. The definitive, code-backed cascade for the Global-CCI panel

The one pipeline that actually produces the final panel is
[src/global_cci_study.py](src/global_cci_study.py), `run_all()`
([global_cci_study.py:520-526](src/global_cci_study.py#L520-L526)):

```
inspect → exogeneity_screen_global_cci() → validate → rolling → run_all_markets(admissible) → bubble_call
```

Two gates thin the universe, in this order:

| Stage | Test | Where | Result (current run) |
|---|---|---|---|
| Candidate universe | markets defined in `MARKETS` | [market_config.py:19-99](src/market_config.py#L19-L99) | **57** entries |
| — with usable price data | non-empty equity CSV / panel column | `data/equity/`, `data/combined/monthly_panel.csv` | 56 (colcap has an empty CSV → `ERROR: 'eq_colcap'`) |
| **Gate 1 — exogeneity** | reverse Granger `return → Δ(global CCI)`, p > 0.05 | `exogeneity_screen_global_cci` [global_cci_study.py:168-202](src/global_cci_study.py#L168-L202) | **32 PASS / 24 FAIL** |
| **Gate 2 — length** | `len(y) ≥ 340` (drop shorter) | `_estimate_one` [global_cci_study.py:367-368](src/global_cci_study.py#L367-L368) | **23 kept** (9 PASS-but-short dropped) |
| Final panel | rows written to CSV | [results/tables/global_cci_all_markets.csv](results/tables/global_cci_all_markets.csv) | **23** |

**[reproduced]** `cd src && python global_cci_study.py screen` prints
`32 of 57 markets admissible`. Full per-market PASS/FAIL is in §3.

**The 23 final markets** (the CSV rows, in file order):
`ipc, bovespa, merval, ibex35, smi, aex, athex, ta125, ta35, bist100, nikkei225,
shanghai, szse, hangseng, hscei, kospi, sti, twse, jkse, lq45, klci, set, psei`.

**The 9 markets that PASS exogeneity but are dropped by the T≥340 gate** (i.e. the
difference between "32 admissible" and "23 estimated"):
`ipsa, psi20, omxcopenhagen, bux, topix, csi300, kosdaq, kse100, nzx50`.
(These are the markets shown `PASS` by `global_cci_study.py screen` but absent from the
23-row CSV; each has len(y) < 340 — e.g. csi300 has only 63 obs, omxcopenhagen 86.)

### 1b. Reconciling your "48 → 27 → 23"

That exact string is **your Week-4 write-up**, not the current code. Extracted verbatim
from `Week 4 Findings.docx`:

> "Sample cascade: 48 markets → 27 pass Granger exogeneity → 23 admissible after T ≥ 340
> obs (≈ 1998+, spanning dot-com, GFC, COVID). Large markets drop at the exogeneity stage
> (US indices, UK, DAX, CAC 40, ASX 200): their equity returns move the GDP-weighted
> aggregate."

- The **ordering is the same as the code**: exogeneity first (returns→trigger), then T≥340.
- The **48 and 27 are a stale, smaller snapshot** of the universe. The current
  `MARKETS` dict has 57 entries and the current screen passes **32**, not 27. The universe
  grew (extra US size indices, `aord`, `ftmc`, `mdax`, `csi300`, `kse100`, second Israel/
  Indonesia/HK/China lines, etc.) after that write-up. UROP is **not** under git here
  (git root is `C:\Users\rongq`, no commits — the staged files belong to the unrelated
  `Optimiser` project), so the exact 48/27 membership is **not reproducible** — it survives
  only in the docx. The terminal count **23 is stable** across both.
- So: **48→27** = old universe→old exogeneity-pass count; **current equivalent is 57→32**;
  both then → **23** via T≥340.

### 1c. Reconciling "14 of 23 pass"

This is **not** the global-CCI panel gate. It is the **composite-trigger** study (Week 3).
Verbatim from `Week 3 Findings.docx`:

> "Exogeneity matches CCI alone at 14 of 23 markets. The composite does not extend
> exogeneity beyond the single-trigger benchmark."

Meaning: within the **23-market CCI-admissible panel**, a raw PCA/blend composite
(CCI+VIX+BCI) reproduces CCI-alone exogeneity for only **14** of them (so 9 differ). The
implementation is archived at [src/archive/composite_study.py](src/archive/composite_study.py)
with the market-by-market gate in
[results/archive/tables/composite_individual_exogeneity.csv](results/archive/tables/composite_individual_exogeneity.csv)
(`CCI` column = the global-CCI reverse-Granger gate; `VIX_m`/`BCI_m` columns = the
component gates). **Which test/script does which:** the global-CCI panel gate is the
reverse-Granger in `global_cci_study.py` (§2.1); the "14 of 23" is a *comparison* of that
same CCI gate against composite-component gates in the archived composite study.

---

## 2. EXOGENEITY / GRANGER TEST SPEC

There are **two different Granger directions** in this codebase — do not conflate them.

### 2.1 Panel gate — reverse Granger (the one that builds the 23-market panel)
`exogeneity_screen_global_cci` [global_cci_study.py:168-202](src/global_cci_study.py#L168-L202),
core F-test `granger_f_test` [exogeneity.py:31-80](src/exogeneity.py#L31-L80).

| Property | Value |
|---|---|
| **Direction** | `equity return → Δ(global CCI)` (does the *return* predict the *trigger*?) |
| Rationale | If returns move the aggregate → endogenous → FAIL. A global aggregate should be unmovable by one market. |
| Variables | `y_ret = diff(log price)`, `z_diff = diff(CCI level)`; call is `granger_f_test(z_diff, y_ret, n_lags)` [L191](src/global_cci_study.py#L191) — note the trigger diff is the *dependent*, returns are the *regressors under test* |
| **Lag selection** | fixed **`n_lags = 4`** (not information-criterion selected) — arg default [L168](src/global_cci_study.py#L168) |
| **Threshold** | **α = 0.05**; PASS ⇔ p > 0.05 [L193](src/global_cci_study.py#L193) |
| **Library/function** | hand-rolled OLS F-test: `numpy.linalg.lstsq` for restricted/unrestricted RSS, `scipy.stats.f.cdf` for the p-value [exogeneity.py:63-80](src/exogeneity.py#L63-L80). No statsmodels. |
| Model | restricted `Δy ~ 1 + 4 own lags`; unrestricted adds 4 lags of the regressor; F on the 4 added coeffs |

The **mixed-trigger** study uses the *same* test/direction/lags/α
([mixed_trigger_study.py:82-136](src/mixed_trigger_study.py#L82-L136), `N_LAGS=4`,
`ALPHA=0.05`), but the trigger is the country CCI where a file exists, else global CCI.

The **country-CCI** study runs the identical reverse-Granger but **non-blocking /
informational only** — estimation proceeds regardless of the gate
([country_cci_study.py:145-161](src/country_cci_study.py#L145-L161), note the header
"country equity returns often predict own-country CCI — this is expected").

### 2.2 Original replication gate — forward Granger (VIX/MCSI/BAA validation)
`test_exogeneity` [exogeneity.py:83-117](src/exogeneity.py#L83-L117), study driver
`run_full_study` [exogeneity.py:195-250](src/exogeneity.py#L195-L250).

| Property | Value |
|---|---|
| **Direction** | `trigger → equity return` (does the *trigger* predict the *return*?) — opposite of §2.1 |
| **Lag selection** | fixed **5** for daily VIX/BAA, **4** for monthly MCSI [exogeneity.py:188-192](src/exogeneity.py#L188-L192) |
| Trigger lag | VIX/BAA lagged 1 (S&P) or 2 (FTSE, London TZ); MCSI lag 0 |
| **Threshold** | α = 0.05, three-way verdict: `ADMISSIBLE` (p>α), `PREDETERMINED` (p≤α but trigger_lag>0), `REJECTED` (p≤α, lag 0) [exogeneity.py:110-116](src/exogeneity.py#L110-L116) |
| Function | same `granger_f_test` (numpy + scipy.f) |

This is the script whose docstring calls it the **"27-market study"**
([exogeneity.py:15](src/exogeneity.py#L15), [L183](src/exogeneity.py#L183)) — that stale
"27" label is the likely origin of the "27" in your cascade note, but it is a *different
gate* (trigger→return) from the one that selects the 23-market panel.

---

## 3. THE 9 (actually 24) MARKETS FAILING THE GLOBAL-CCI GATE — which list is correct?

**Direct answer to your two candidate lists:**

- List A — **SMI, AEX, IPC, JKSE → these all PASS and are RETAINED in the final 23.**
  In [results/tables/global_cci_all_markets.csv](results/tables/global_cci_all_markets.csv):
  smi (p=0.2130), aex (0.2311), ipc (0.1250), jkse (0.7388) — all p>0.05. **This list is wrong** as a "failing" list.
- List B — **CAC40, ASX200, Nifty50, EuroStoxx50 → these all FAIL and are EXCLUDED.**
  From the screen: cac40 p=0.0032, asx200 p=0.0001, nifty50 p=0.0348, eurostoxx50 p=0.0034 — all p<0.05. **This list is correct** (they genuinely fail exogeneity).

So the correct characterization: **List B are true exogeneity failures; List A are passes.**

**Full FAIL list (current run, 24 markets)** — every market with Gate = FAIL in
`python global_cci_study.py screen` **[reproduced]**:
`sp500, nasdaq, djia, rut, rui, sp400, wilshire5000, tsx, eurostoxx50, ftse100, ftmc,
dax, mdax, cac40, ftsemib, iseq, bel20, atx, omxstockholm, omxhelsinki, oseax, nifty50,
asx200, aord` (24), plus `colcap` = ERROR (no equity data). These are overwhelmingly the
large developed markets whose returns move the GDP-weighted OECD aggregate — exactly the
mechanism your Week-4 note describes.

**Where does "9" come from?** Not this gate (which fails 24). "9" = **23 − 14** from the
*composite* comparison (§1c): of the 23 CCI-admissible markets, 9 have a composite gate
verdict that differs from CCI-alone. That is a property of the archived composite study
([results/archive/tables/composite_individual_exogeneity.csv](results/archive/tables/composite_individual_exogeneity.csv)),
**not** a list of markets excluded from the global-CCI panel. The two ideas were conflated
in your notes.

---

## 4. FINAL PANEL used by each figure/test

All three consumers read the **same** file,
[results/tables/global_cci_all_markets.csv](results/tables/global_cci_all_markets.csv)
(23 rows), so the count is **23** for all three. Japan (`nikkei225`) is present in all
three but has its EXP months excluded from the *pooled EXP* array only (see §5).

| Deliverable | Script | Panel | Count |
|---|---|---|---|
| (a) Threshold-consistency figure `chart_thresholds.png` | `gcci_figures.chart_thresholds` reads `efficiency_ranking.csv` [gcci_figures.py:337-369](src/gcci_figures.py#L337-L369) | 23-market ranking | **23** |
| (b) Efficiency ranking `efficiency_ranking.csv` / `chart_efficiency_ranking.png` | `gcci_figures.efficiency_ranking` [gcci_figures.py:62-99](src/gcci_figures.py#L62-L99) | sorted by RW% | **23** ([results/gcci/efficiency_ranking.csv](results/gcci/efficiency_ranking.csv) has 23 rows) |
| (c) Pooled horizon return test | `horizon_test._build_pooled_arrays` [horizon_test.py:105-169](src/horizon_test.py#L105-L169) | reads the 23-row CSV | **23** markets pooled |

**Watch out for stale hard-coded labels in the code** (they say 27, but the data is 23):
- [gcci_figures.py:261](src/gcci_figures.py#L261) chart title "27 admissible markets"
- [gcci_figures.py:338](src/gcci_figures.py#L338), [L359](src/gcci_figures.py#L359),
  [L377](src/gcci_figures.py#L377) "27 markets"
- [horizon_test.py:12](src/horizon_test.py#L12) docstring "currently 27 markets"

The **data-driven** labels are right: the saved horizon figure
[results/gcci/horizon_distributions_12m.png](results/gcci/horizon_distributions_12m.png)
reads "Pooled across **23** admissible markets", and `efficiency_ranking.csv` has 23 rows.
**No 14- or 13-market panel exists in the current outputs** — those counts belong to
earlier runs / the composite study.

---

## 5. HORIZON TEST NUMBERS (12-month, pooled)

**Caveat on saved outputs:** the horizon CSVs
(`horizon_test.csv`, `horizon_test_per_market.csv`, `horizon_test_exp_phase.csv`) that
[horizon_test.py:295-308](src/horizon_test.py#L295-L308) *would* write are **not present**
in `results/gcci/` — only the figure
[results/gcci/horizon_distributions_12m.png](results/gcci/horizon_distributions_12m.png)
(dated Jun 18, the latest) was saved. The numeric table therefore had to be **[reproduced]**
by calling `horizon_test._build_pooled_arrays()` read-only (no files written).

**Latest run = the 23-market panel.** Pooled mean forward log-returns (Japan EXP excluded,
per [horizon_test.py:141-145](src/horizon_test.py#L141-L145)):

| Horizon | MR mean (n) | RW mean (n) | EXP mean (n) |
|---|---|---|---|
| 1m | +0.688% (1183) | +0.775% (6855) | −0.442% (615) |
| 3m | +2.625% (1163) | +2.234% (6829) | −1.896% (615) |
| 6m | +7.181% (1145) | +4.079% (6778) | −3.338% (615) |
| **12m** | **+14.60% (1109)** | **+8.01% (6676)** | **−7.49% (615)** |

The saved figure's annotations (`MR +14.6%, n=1,109` / `RW +8.0%, n=6,676` /
`EXP −7.5%, n=615`, both p<0.001 vs RW) match these to rounding.

**Reconciling your two candidate sets:**
- **MR +14.6 / RW +8.0 / EXP −7.5 (your "23-market")** = the **current, latest** 23-market
  run. ✅ This is the one to cite.
- **MR +13.59 / RW +6.99 / EXP −3.48 (your "14-market")** = an **earlier run** on a smaller
  pool (the horizon script always reads whatever `global_cci_all_markets.csv` contained at
  the time — [horizon_test.py:115-116](src/horizon_test.py#L115-L116)). No current output
  reproduces those numbers, so they are **superseded**. There is no 14-market CSV left in
  the repo to regenerate them.

---

## 6. THRESHOLD RANGES (final 23-market panel)

From [results/tables/global_cci_all_markets.csv](results/tables/global_cci_all_markets.csv)
(`c1`, `c2` columns) **[reproduced via min/max over the 23 rows]**:

| | min (market) | max (market) |
|---|---|---|
| **c1** | **97.023** (twse) | **100.444** (bovespa) |
| **c2** | **99.872** (nikkei225) | **102.430** (bovespa) |

**Your notes ("c1 ~96.8–98.2, c2 ~100.8–102.5") describe the shaded CLUSTER BANDS, not the
min/max.** Those exact numbers are hard-coded as `ax.axhspan(96.8, 98.2, ...)` and
`ax.axhspan(100.8, 102.5, ...)` in
[gcci_figures.py:346-347](src/gcci_figures.py#L346-L347) — decorative bands showing where
*most* thresholds sit. The **true spread is wider**: the MR-dominated markets (bovespa,
shanghai, psei, ipc, szse) push c1 up to ~99.3–100.4, and Japan's degenerate c2=99.87
pulls the c2 minimum below 100. So: cluster ≈ notes; actual range = c1 [97.02, 100.44],
c2 [99.87, 102.43].

---

## 7. DATA SOURCES (exact, as implemented)

| Series | Source / API | Series ID / query | Sample (as stored) |
|---|---|---|---|
| **Equity indices** | **Yahoo Finance** via `yfinance.download(..., auto_adjust=True)` [collect_data.py:41-49](src/collect_data.py#L41-L49) | Yahoo tickers in `MARKETS` (e.g. `^GSPC`, `^N225`, `000001.SS`) [market_config.py:19-99](src/market_config.py#L19-L99) | daily from 1975-01-01 request; resampled to month-end for the monthly panel [collect_data.py:68-73](src/collect_data.py#L68-L73) |
| **Global OECD CCI** | **OECD.Stat SDMX** export, parsed locally by [collect_global_cci.py](src/collect_global_cci.py) from `data/sentiment/global_oecd_cci.csv` | Dataflow `OECD.SDD.STES:DSD_STES@DF_CLI`; `REF_AREA=OECD`, `MEASURE=CCICP` (composite consumer confidence), `ADJUSTMENT=AA` (amplitude-adjusted, 100 = long-run avg), `FREQ=M`, `METHODOLOGY=H` (verified in the CSV header row) | `global_cci_monthly.csv`: **1980-01 → 2026-05** (latest value 97.552, matching `current_cci` in the results CSV) |
| **Country CCIs** | **FRED** via `fredapi` [collect_oecd.py:1-8](src/collect_oecd.py#L1-L8), [collect_data.py:52-61](src/collect_data.py#L52-L61) | pattern **`CSCICP03{ISO2}M665S`** [collect_oecd.py:54-59](src/collect_oecd.py#L54-L59) (e.g. USA→`CSCICP03USM665S`, GBR→`CSCICP03GBM665S`) | per-country files `oecd_cci_{CODE}.csv`; USA runs 1975-01→…, GRC/TUR end 2024-01 (shorter) |

**⚠ Source discrepancy to flag in the write-up:** the *docstring* of
[global_cci_study.py:3-4](src/global_cci_study.py#L3-L4) (and the title text on figures)
says the global series is **"FRED series CSCICP03OECDm"**. The **actual** data ingested is
the **OECD.Stat SDMX** download (`DSD_STES@DF_CLI`, `REF_AREA=OECD`, `CCICP`, `AA`) — see
the real column structure in `data/sentiment/global_oecd_cci.csv` and the parser
[collect_global_cci.py:26-47](src/collect_global_cci.py#L26-L47). The two are economically
the same OECD amplitude-adjusted composite CCI, but the *implemented* source is OECD SDMX,
not FRED. Cite OECD SDMX.

**Per-market Global-CCI overlap windows** (23-market panel; end is 2026-05 for all because
that is the last global-CCI month) **[reproduced]** — all begin at each index's first
month with both price and CCI:

| Market | start | Market | start | Market | start |
|---|---|---|---|---|---|
| nikkei225 | 1990-01 | ta125/ta35 | 1992-10 | kospi | 1996-12 |
| hangseng | 1990-01 | aex | 1992-10 | set | 1996-12 |
| sti | 1990-01 | ibex35 | 1993-07 | lq45 | 1997-02 |
| psei | 1990-01 | hscei | 1993-07 | athex | 1997-07 |
| jkse | 1990-04 | bovespa | 1993-04 | bist100 | 1997-07 |
| smi | 1990-11 | klci | 1993-12 | shanghai | 1997-07 |
| ipc | 1991-11 | merval | 1996-10 | twse | 1997-07 |
| | | | | szse | 1997-08 |

---

## 8. T ≥ 340 ENFORCEMENT and per-market observation counts

**Where it is enforced** (the trigger is `len(y)`, i.e. the number of aligned price/CCI
months *before* differencing):

- Global-CCI estimation: `if len(y) < 340: return None`
  [global_cci_study.py:367-368](src/global_cci_study.py#L367-L368) (also in `bubble_call`
  [L475-476](src/global_cci_study.py#L475-L476)).
- Mixed-trigger study: `MIN_OBS_GLOBAL = 340`
  [mixed_trigger_study.py:43](src/mixed_trigger_study.py#L43), applied at
  [L108](src/mixed_trigger_study.py#L108) and [L168](src/mixed_trigger_study.py#L168) —
  but **only to global-trigger markets** (country-CCI markets have no minimum, [L44](src/mixed_trigger_study.py#L44)).
- The country-CCI study uses a different, looser floor: `MIN_OBS = 180`
  [country_cci_study.py:61](src/country_cci_study.py#L61).

**Note on the reported `T`.** The CSV `T` column = `len(state)` = `len(y) − 1` (state is
assigned to `z[1:]`, [global_cci_study.py:377](src/global_cci_study.py#L377)), so the gate
`len(y) ≥ 340` means CSV `T ≥ 339`. In practice the smallest kept markets have `len(y)=346`
(`T=345`).

**Per-market observation counts** (23-market panel; `T` from the results CSV, `len(y)=T+1`)
**[reproduced, matches the CSV `T` column and horizon per-market print]**:

| Market | len(y) | T | Market | len(y) | T | Market | len(y) | T |
|---|---|---|---|---|---|---|---|---|
| nikkei225 | 437 | 436 | ipc | 415 | 414 | kospi | 354 | 353 |
| hangseng | 437 | 436 | aex | 404 | 403 | set | 354 | 353 |
| sti | 437 | 436 | ta125 | 404 | 403 | lq45 | 352 | 351 |
| psei | 437 | 436 | ta35 | 404 | 403 | bist100 | 347 | 346 |
| jkse | 434 | 433 | bovespa | 398 | 397 | shanghai | 347 | 346 |
| smi | 427 | 426 | ibex35 | 395 | 394 | twse | 347 | 346 |
| | | | hscei | 395 | 394 | athex | 346 | 345 |
| | | | klci | 390 | 389 | szse | 346 | 345 |
| | | | merval | 356 | 355 | | | |

All 23 satisfy `len(y) ≥ 346 ≥ 340`. The nine PASS-but-excluded markets (§1a) fall below:
e.g. csi300 len(y)=63, omxcopenhagen 86, omxhelsinki/psi20 ~130, nifty50 225, kse100/bux
291, kosdaq 279, topix 193, ipsa 210, nzx50 249 (from `python global_cci_study.py screen`
/ `mixed_trigger_study.py screen` **[reproduced]**).

---

## Appendix — provenance of every "reproduced" figure
- `python global_cci_study.py screen` → 57 iterated, 32 PASS, 24 FAIL, colcap ERROR (§1a, §3, §8). Prints only; writes nothing.
- `python mixed_trigger_study.py screen` → "34 admissible from 57 markets (7 too short, 15 fail exogeneity); country 19, global 15" — used only to read the short-market T values (§8). Prints only.
- Scratchpad read-only script calling `horizon_test._build_pooled_arrays()` and
  `load_global_cci_pair()` → §5 horizon means, §6 c1/c2 min-max, §7 start dates, §8 T counts.
  Reads the committed CSV + panel; writes nothing to the repo.
- Docx extractions (`Week 3 Findings.docx`, `Week 4 Findings.docx`) → the "48→27→23" and
  "14 of 23" strings (§1b, §1c).
