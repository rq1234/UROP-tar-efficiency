# Verification manifest: Full_Paper_Draft_Tier2_Reworked_Referee_Revision

**Purpose:** every substantive number and exhibit in the final draft, as a machine-checkable
target list for the reproduction pipeline. Each entry gets a computed value in
`outputs/numbers.json` (keyed by the IDs below) and a verdict in `VERIFICATION_REPORT.md`:
MATCH / NEAR (rounding only) / MISMATCH / NOT_REPRODUCIBLE.

## Tolerance classes

- **E (exact):** must match to stated precision. Counts, screen verdicts, thresholds (to grid
  resolution), band shares (within ~0.15 pp), coefficients (within 0.001), analytic F/t/p values
  (within 1 in the last printed digit).
- **S (seed-sensitive):** bootstrap, permutation and placebo outputs. Without the original seed,
  numeric drift is expected. The PAPER'S QUALITATIVE CLAIM must hold (sign, the significance
  category as the paper words it, counts such as "none survives BH correction"). Report the
  recomputed value AND whether the claim's category flips. A recorded seed from an earlier
  placebo run is **20260721** (source: `final_fix_plan.md`); try it, but do not assume it was
  used for every stochastic step.
- **V (vintage-sensitive):** recomputed from re-downloaded OECD/FRED data, so values may shift if
  the provider revised the series. Prefer cached raw data found on disk or in transcripts; record
  the download date either way.

## Priorities

- **P1:** must regenerate before submission (headline exhibits, abstract numbers).
- **P2:** should regenerate before submission (all inference and robustness).
- **P3:** verify if time permits (candidate-trigger detail, appendix diagnostics).

---

## Section A. Headline numbers (abstract and introduction). All P1.

| ID | Item | Value | Class |
|---|---|---|---|
| A1 | Panel: candidates / screen passes / retained (T >= 340) | 57 / 32 / 23 (1 candidate, Colombia, no data; 24 reject) | E |
| A2 | Threshold clusters, most indices | lower ~97.0 to 98.5; upper ~101.2 to 102.4 | E |
| A3 | RW-share endpoints | Japan 33.7 (degenerate c2 = 99.87); Turkey 94.2 (sample-window artefact) | E |
| A4 | Unrestricted middle-band slopes | 6 raw 5% rejections; 0 survive BH at q = 0.05 | E |
| A5 | Block placebo | fitted RSS improvement beats 12-month block null in 3 of 23 (i.i.d. null: 9 of 23), 1,000 sims per index | S |
| A6 | Greece matched window (global trigger) | 83% RW | E |
| A7 | Greece matched window (Greek CCI) | 44 low / 31 RW / 25 high | E |
| A8 | Greece percentile-normalised trigger | 43.8 / 31.5 / 24.6 | E |
| A9 | 12-month forward means by band | +14.60% low / +8.01% RW / -7.49% high | E |
| A10 | 12-month pooled n by band | 1,109 / 6,676 / 615 | E |
| A11 | Full-pipeline calendar bootstrap, high minus RW | -10.88, 95% CI [-18.23, -4.32] | S |
| A12 | Fixed-tail benchmark spread vs TAR spread | 22.14 vs 22.09 points | E |
| A13 | High-sentiment spells in 1997-2000 | 29 of 30 (ex-Japan) | E |
| A14 | Five-cluster episode test | mean -18.3, t = -3.16, p = 0.034 | E |

---

## Section B. Table targets (regenerate the full table, cell-diff against these)

### B1. Table 4.1 (P1). Stars: 1 = 10%, 2 = 5%, 3 = 1%.

```csv
index,country,T,c1,c2,rw_pct,low_pct,high_pct,b_MR,b_MR_stars,b_EXP,b_EXP_stars,tail_coverage
BIST100,Turkey,346,97.33,102.16,94.2,3.5,2.3,0.059,3,-0.904,3,Both
KLCI,Malaysia,389,97.06,101.50,90.2,1.5,8.2,-1.255,3,-0.274,3,High only
STI,Singapore,436,97.88,101.72,89.2,5.7,5.0,-0.004,0,-0.313,3,Both
ATHEX,Greece,345,97.55,101.54,88.4,4.1,7.5,-0.158,3,-0.270,3,Both
TA125,Israel,403,98.09,101.68,87.6,6.9,5.5,0.013,0,-0.192,2,Both
TA35,Israel (TA-35),403,98.09,101.68,87.6,6.9,5.5,0.016,0,-0.186,2,Both
HANGSENG,Hong Kong,436,98.45,102.01,87.4,10.1,2.5,-0.136,2,-0.865,3,Both
TWSE,Taiwan,346,97.02,101.32,86.7,1.7,11.6,-0.799,2,-0.152,1,High only
SMI,Switzerland,426,97.28,101.21,86.4,2.8,10.8,0.070,1,-0.179,3,Both
IBEX35,Spain,394,97.13,101.19,86.0,2.0,11.9,-0.760,3,-0.150,3,Both
JKSE,Indonesia,433,97.80,101.28,85.0,5.1,9.9,-0.004,0,-0.259,3,Both
AEX,Netherlands,403,97.80,101.38,84.6,5.5,9.9,0.031,0,-0.111,2,Both
MERVAL,Argentina,355,97.75,101.25,82.5,5.1,12.4,0.030,2,-0.180,2,Both
SET,Thailand,353,97.74,101.26,82.4,5.1,12.5,0.030,0,-0.186,2,Both
HSCEI,Hong Kong (H-shr),394,98.01,101.26,82.2,6.6,11.2,-0.247,2,-0.133,2,Both
LQ45,Indonesia (LQ45),351,97.88,101.33,80.9,7.1,12.0,-0.010,0,-0.341,3,Both
IPC,Mexico,414,99.27,102.01,70.3,27.1,2.7,-0.020,3,-0.827,3,Both
KOSPI,South Korea,353,98.73,101.26,69.1,18.4,12.5,0.058,2,-0.089,0,Both
SZSE,China (SZSE),345,99.47,101.77,57.4,37.4,5.2,-0.098,2,-0.474,3,Both
PSEI,Philippines,436,100.16,102.22,53.9,45.0,1.1,-0.020,3,-0.325,0,Both
SHANGHAI,China (SSE),346,100.17,102.24,52.0,46.8,1.2,-0.063,3,-0.361,3,Both
BOVESPA,Brazil,397,100.44,102.43,50.4,49.6,0.0,-0.051,3,0.000,0,Low only
NIKKEI225,Japan,436,97.88,99.87,33.7,5.7,60.6,0.049,1,-0.035,3,Both (mechanical)
```

### B2. Table 6.1 (P1). Means are pooled forward log returns; Welch p-values.

```csv
horizon_months,low_mean_pct,low_n,rw_mean_pct,rw_n,high_mean_pct,high_n,p_low_vs_rw,p_high_vs_rw
1,0.69,1183,0.78,6855,-0.44,615,0.741,0.010
3,2.63,1163,2.23,6829,-1.90,615,0.489,<0.001
6,7.18,1145,4.08,6778,-3.34,615,<0.001,<0.001
12,14.60,1109,8.01,6676,-7.49,615,<0.001,<0.001
```

**Cross-checks that must hold (all E, P1):** high-band n constant at 615 across horizons; last
included high month is July 2018 (Spain); 615 = 30 spells x 20.5 mean months; Japan's ~264
high-band months excluded throughout.

### B3. Table 5.1 matched windows (P1)

```csv
index,window,T,trigger,low_pct,rw_pct,high_pct
Greece,1997-07 to 2024-01,317,Global CCI,7,83,10
Greece,1997-07 to 2024-01,317,Greek CCI,44,31,25
Turkey,2004-01 to 2024-01,240,Global CCI,6,38,56
Turkey,2004-01 to 2024-01,240,Turkish CCI,7,45,48
```

### B4. Table 5.2 standalone estimates (P1)

```csv
index,trigger,T,c1,c2,low_pct,rw_pct,high_pct,low_slope,low_stars,high_slope,high_stars
ATHEX,Global CCI,345,97.55,101.54,4.1,88.4,7.5,-0.158,3,-0.270,3
ATHEX,Country CCI,317,99.08,101.59,43.53,31.23,25.24,-0.082,3,0.004,0
Shanghai,Country CCI,317,100.77,104.37,70.98,27.44,1.58,-0.036,3,-0.770,3
SZSE,Country CCI,316,100.77,104.38,70.89,27.85,1.27,-0.026,2,-0.594,3
BIST100,Global CCI,346,97.33,102.16,3.5,94.2,2.3,0.059,3,-0.904,3
BIST100,Country CCI,240,95.17,100.85,6.67,45.42,47.92,0.057,2,-0.034,3
```

### B5. Table A.1 reverse-Granger screen, all 57 candidates (P2)

```csv
index,country,T,F,p,screen
SP500,USA,437,5.60,0.0002,FAIL
NASDAQ,USA (NASDAQ),437,3.77,0.0050,FAIL
DJIA,USA (DJIA),413,4.80,0.0009,FAIL
RUT,USA (Small-Cap),437,3.98,0.0035,FAIL
RUI,USA (Large-Cap),402,5.32,0.0003,FAIL
SP400,USA (Mid-Cap),437,4.09,0.0029,FAIL
WILSHIRE5000,USA (Total Mkt),437,5.79,0.0002,FAIL
TSX,Canada,437,4.26,0.0022,FAIL
IPC,Mexico,415,1.82,0.1250,PASS
BOVESPA,Brazil,398,1.28,0.2755,PASS
IPSA,Chile,210,0.97,0.4226,PASS
COLCAP,Colombia,,,,no data
MERVAL,Argentina,356,0.48,0.7481,PASS
EUROSTOXX50,Eurozone,231,4.07,0.0034,FAIL
FTSE100,UK,437,2.49,0.0426,FAIL
FTMC,UK (Mid-Cap),437,4.82,0.0008,FAIL
DAX,Germany,437,3.58,0.0069,FAIL
MDAX,Germany (MDAX),364,3.82,0.0047,FAIL
CAC40,France,435,4.03,0.0032,FAIL
IBEX35,Spain,395,2.28,0.0600,PASS
SMI,Switzerland,427,1.46,0.2130,PASS
AEX,Netherlands,404,1.41,0.2311,PASS
FTSEMIB,Italy,342,3.47,0.0086,FAIL
ISEQ,Ireland,347,2.99,0.0190,FAIL
ATHEX,Greece,346,1.74,0.1416,PASS
BEL20,Belgium,422,4.81,0.0008,FAIL
ATX,Austria,403,3.87,0.0043,FAIL
PSI20,Portugal,158,2.19,0.0728,PASS
OMXSTOCKHOLM,Sweden,211,2.47,0.0459,FAIL
OMXHELSINKI,Finland,159,3.73,0.0064,FAIL
OMXCOPENHAGEN,Denmark,114,1.70,0.1552,PASS
OSEAX,Norway,159,2.62,0.0374,FAIL
BUX,Hungary,291,1.47,0.2102,PASS
TA125,Israel,404,1.21,0.3046,PASS
TA35,Israel (TA-35),404,1.43,0.2222,PASS
BIST100,Turkey,347,0.82,0.5108,PASS
NIKKEI225,Japan,437,1.08,0.3677,PASS
TOPIX,Japan (TOPIX),221,0.28,0.8923,PASS
SHANGHAI,China (SSE),347,0.16,0.9606,PASS
CSI300,China (CSI 300),63,0.21,0.9339,PASS
SZSE,China (SZSE),346,0.01,0.9996,PASS
HANGSENG,Hong Kong,437,1.26,0.2869,PASS
HSCEI,Hong Kong (H-shr),395,1.41,0.2308,PASS
KOSPI,South Korea,354,0.20,0.9377,PASS
KOSDAQ,South Korea (KQ),308,0.20,0.9369,PASS
NIFTY50,India,225,2.64,0.0348,FAIL
KSE100,Pakistan,291,1.77,0.1359,PASS
STI,Singapore,437,0.94,0.4390,PASS
TWSE,Taiwan,347,0.59,0.6720,PASS
JKSE,Indonesia,434,0.50,0.7388,PASS
LQ45,Indonesia (LQ45),352,0.60,0.6660,PASS
KLCI,Malaysia,390,0.33,0.8547,PASS
SET,Thailand,354,0.39,0.8175,PASS
PSEI,Philippines,437,0.72,0.5784,PASS
ASX200,Australia,403,6.32,0.0001,FAIL
AORD,Australia (All),437,6.75,0.0000,FAIL
NZX50,New Zealand,281,2.16,0.0736,PASS
```

### B6. Table B.1 episode coverage, percent of episode months in the pre-designated band (P2)

```csv
index,dotcom_high_pct,gfc_low_pct,covid_low_pct
BIST100,20.5,57.1,0.0
KLCI,74.4,0.0,0.0
STI,56.4,100.0,0.0
ATHEX,66.7,85.7,0.0
TA125,56.4,100.0,0.0
TA35,56.4,100.0,0.0
HANGSENG,28.2,100.0,33.3
TWSE,89.7,0.0,0.0
SMI,97.4,57.1,0.0
IBEX35,97.4,28.6,0.0
JKSE,92.3,100.0,0.0
AEX,87.2,100.0,0.0
MERVAL,94.9,85.7,0.0
SET,94.9,85.7,0.0
HSCEI,94.9,100.0,0.0
LQ45,89.7,100.0,0.0
IPC,28.2,100.0,66.7
KOSPI,94.9,100.0,33.3
SZSE,46.2,100.0,66.7
PSEI,12.8,100.0,66.7
SHANGHAI,10.3,100.0,66.7
BOVESPA,0.0,100.0,100.0
NIKKEI225,100.0,100.0,0.0
```

### B7. Table C.1 national-global first-difference correlations (P2, class V)

```csv
country,n,window,corr
China (FRED CSCICP03CNM665S),407,1990-01 to 2023-12,0.253
New Zealand,423,1988-06 to 2023-09,0.286
Greece,468,1985-01 to 2024-01,0.368
Turkey,240,2004-01 to 2024-01,0.376
Czechia (PX),348,1995-01 to 2024-01,0.415
Australia,528,1980-01 to 2024-01,0.435
Finland,434,1987-11 to 2024-01,0.482
Ireland,516,1980-01 to 2023-01,0.485
France,528,1980-01 to 2024-01,0.485
Italy,528,1980-01 to 2024-01,0.494
Austria,528,1980-01 to 2024-01,0.501
Mexico,272,2001-04 to 2023-12,0.507
Germany,528,1980-01 to 2024-01,0.523
Denmark,528,1980-01 to 2024-01,0.524
Belgium,528,1980-01 to 2024-01,0.534
Poland (WIG20),272,2001-05 to 2024-01,0.551
Netherlands,528,1980-01 to 2024-01,0.563
Portugal,451,1986-06 to 2024-01,0.570
Switzerland,526,1980-01 to 2023-11,0.577
Canada,455,1980-01 to 2017-12,0.590
South Korea,300,1998-12 to 2023-12,0.603
UK,528,1980-01 to 2024-01,0.617
Sweden,339,1995-10 to 2024-01,0.634
Japan,501,1982-04 to 2024-01,0.666
Spain,451,1986-06 to 2024-01,0.705
USA,528,1980-01 to 2024-01,0.808
```

---

## Section C. In-text numbers by section

### Methodology (Section 3)

| ID | Item | Value | Class | Pri |
|---|---|---|---|---|
| C1 | A&S replication vs published Tables 7/8 | match to grid resolution; FTSE no-drift c2 61.8 vs published 82.6, RSS surface flat within 0.018% | E | P2 |
| C2 | Eight-lag screen re-run | 22 of 23 pass; Japan p = 0.042 | E | P2 |
| C3 | Rolling 10-yr threshold ranges (S&P 500) | MCSI 46.0 units; US CCI 4.8 units | E/V | P3 |
| C4 | Frozen mid-2015 thresholds, later months | MCSI: S&P in low band from Aug 2025; CCI: middle band through Apr 2026, low band in May 2026 | V | P3 |
| C5 | Frozen vs full-sample label agreement | 88% of index-months (panel) | E | P2 |
| C6 | Chance-corrected self-agreement | kappa 0.94 (MCSI/S&P); 0.74 (CCI panel) | E | P2 |
| C7 | CAPE rolling threshold range | 21.4 units | E/V | P3 |
| C8 | BAA spread | 0.56 pp euphoria compression vs 3.7 pp GFC spike | E/V | P3 (archived study) |
| C9 | ANFCI | high-sentiment state fires 80 to 90% for European markets; partial screen, 9 fail | E/V | P3 (archived study) |
| C10 | Scale diagnostic, 8 national CCI series | 100 -> 38th to 51st pctile; 97.7 -> 4th to 28th; 101.4 -> 63rd to 87th | E | P2 |
| C11 | S&P 500 vs its own US CCI screen | F = 3.54, p = 0.008 | E | P2 |
| C12 | Correlation flag values | China 0.25, NZ 0.29, Greece 0.37, Turkey 0.38; next Czechia 0.415, Australia 0.435 | E/V | P2 |

### Cross-market classification (Section 4)

| ID | Item | Value | Class | Pri |
|---|---|---|---|---|
| C13 | Placebo, i.i.d. null | 9 of 23 beat at 5%; 1,000 sims | S | P2 |
| C14 | Placebo, 12-month block null | 3 of 23 | S | P2 |
| C15 | Low-band slope pattern | 11 significant negative, 5 significant positive, 7 indeterminate | E | P2 |
| C16 | High-band slopes | no positive point estimate; BOVESPA 0.000 with empty band (see E2) | E | P1 |
| C17 | High-band demeaned intercept | median +1.03%/mo, sd 2.96, range -7.4 to +7.4; contemporaneous return positive in 12 of 22 | E | P2 |
| C18 | Significant-slope convention | mean RW share 76.9 -> 80.2; Spearman 0.878 | E | P2 |
| C19 | Constant-drift alternative | Spearman 0.42 vs baseline; mean share shifts 9 pp | E | P2 |
| C20 | Unrestricted middle band | 16 negative, 7 positive; 6 raw rejections; 0 after BH q = 0.05; median slope -0.0063 | E | P1 |
| C21 | Wild bootstrap widths (median 95% CI) | c1 2.14, c2 1.00, RW share 37 pp, high share 13 pp | S | P2 |
| C22 | 24-mo block bootstrap widths | c1 2.93, c2 2.68, RW 67 pp, high 62 pp; high-slope CIs exclude zero: 6 wild, 5 block; Brazil high degenerate-draw rate | S | P2 |
| C23 | Minimum-regime rank correlations | 0.836 (20-obs rule) down to 0.247 (15% rule); all 23 feasible under all six rules | E | P2 |
| C24 | Case shares | HK 87.4/10.1/2.5; Japan 33.7/5.7/60.6 (c2 = 99.87); Shanghai 52.0/46.8/1.2 | E | P1 |

### Trigger domain (Section 5)

| ID | Item | Value | Class | Pri |
|---|---|---|---|---|
| C25 | Greece full-sample vs matched | 88.4% RW full sample; 83% matched window | E | P1 |
| C26 | Turkey global trigger on 2004-2024 window | 56 high / 38 RW (vs 94.2 RW on full window) | E | P1 |
| C27 | Turkey CPI-deflated check | domestic boom-bust survives deflation (no exhibit in paper; produce one) | E | P3 |
| C28 | Spain low-band share | 2.0% of IBEX 35 months | E | P2 |

### Horizon returns (Section 6)

| ID | Item | Value | Class | Pri |
|---|---|---|---|---|
| C29 | Sign consistency | low > RW in 19 of 23 (p = 0.0026); high < RW in 20 of 21 ex-Japan (p < 0.0001) | E | P1 |
| C30 | Fixed-tail percentile cuts | pooled CCI 10th/90th pctiles = 98.4 / 101.4 | E | P1 |
| C31 | Joint regression | TAR high -11.28 (p = 0.019); fixed above-90th -4.36 (p = 0.59) | E | P2 |
| C32 | Coefficient-equality Wald | Driscoll-Kraay p = 0.516; 24-mo calendar-block bootstrap p = 0.618 | E/S | P2 |
| C33 | Recursive expanding-window means | TAR high -16.93; fixed tail -21.92; both significant in encompassing regression; R^2 0.013 / 0.008; near-identical forecast errors | E | P2 |
| C34 | Fixed-label MBB, low minus RW | +6.6 pts; p = 0.21 / 0.31 / 0.35 (12/24/36-mo blocks); DK p = 0.18 | S | P2 |
| C35 | Fixed-label MBB, high minus RW | -15.5 pts; p = 0.083 / 0.049 / 0.026; DK p = 0.040 (11 lags); B = 1,000 | S | P1 (point), P2 (p) |
| C36 | Full-pipeline calendar bootstrap | MR-RW +8.18 [+2.52, +15.41]; EXP-RW -10.88 [-18.23, -4.32] | S | P2 |
| C37 | Episode block | 30 spells ex-Japan; mean length 20.5 mo; mean excess -15.0; 26 of 30 negative; 29 of 30 in 1997-2000 | E | P1 |
| C38 | Five calendar-year clusters | mean -18.3, t = -3.16, p = 0.034; 4 of 5 clusters in the same euphoria | E | P1 |
| C39 | Circular-shift permutation | 0 of 5,000 draws reproduce discount; p < 0.0002 | S | P2 |
| C40 | Trailing-return control | high coefficient -14.07 -> -14.06; trailing p = 0.55; DK p = 0.06 | E | P2 |
| C41 | Asian-crisis exclusion | mean -11.45; the 7 excluded spells average -26.8; unclustered p = 0.017 | E | P2 |
| C42 | One index per country | mean -14.9; unclustered p = 0.006 | E | P2 |
| C43 | Japan reinstated in pooled 12-mo mean | -7.5 -> -6.1 | E | P2 |
| C44 | Minimum-regime gaps | -13.2 / -7.7 / -5.1 (5/10/15%); -12.6 / -8.8 / -7.7 (20/30/40 obs); range quoted as -5.12 to -13.21 | E | P2 |
| C45 | Post-2015 frozen-threshold test | 76 high index-months, 4 calendar years, 4 indices; gap -9.8; bootstrap p = 0.22; DK p = 0.19 | E/S | P2 |
| C46 | Publication-lag re-estimation | lag 0: -16.17 (DK 0.020; blocks 0.046/0.017/0.008); lag 1: -15.90 (DK 0.025; blocks 0.055/0.044/0.025); lag 2: -12.26 (DK 0.049; blocks 0.103/0.093/0.077) | E/S | P2 |
| C47 | Low-sentiment calendar clusters | 9 clusters | E | P2 |
| C48 | Distribution facts (Fig 6.2) | low-band mode near +5% vs mean +14.6; tail months mostly 2008-09 and 2022; COVID months nearly absent | E | P2 |

### Discussion and appendices (Sections 7, D)

| ID | Item | Value | Class | Pri |
|---|---|---|---|---|
| C49 | Composite (CCI+VIX+BCI) | passed 23/23 mechanically; 3/23 under BIC orthogonalisation with longer test horizon | E | P3 |
| C50 | CCI-EPU composite | 18 of 23 pass at longer horizon; both-tails 10 vs "14 under the single CCI" (see E3) | E | P3 |
| C51 | BH on multiplicity | 19 of 24 screening rejections survive; 30 of 33 coefficient rejections survive | E | P2 |
| C52 | D.1 agreement detail | 88.2% full sample; 84.6% post-2015; kappa 0.74; outliers: Shanghai 22, Shenzhen 37, Philippines 52, Mexico 76; 38.8% of disagreements within 0.25 units of a threshold | E | P2 |

---

## Section D. Figures to regenerate

| Fig | Content | Pri |
|---|---|---|
| 3.1 | Rolling 10-yr thresholds, S&P 500: MCSI vs US CCI (two panels) | P3 |
| 4.1 | Threshold pairs, 23 indices, ordered by RW share | P2 |
| 4.2 | RW-band share by index | P2 |
| 4.3-4.5 | Band timelines: Hang Seng, Nikkei, Shanghai | P2 |
| 5.1a/b | ATHEX under global vs Greek CCI. RESOLVED: matched-window global-CCI version (83% RW, refit thresholds, same 1997-2024 window as 5.1b) regenerated by `scripts/fig5_matched_window.py`, output `outputs/rebuilt/fig5_1a_athex_matched_GCCI.png`. Verified against `results/exports/matched_window_localisation.csv` (within 0.04pp). Original full-sample version (88% RW) retained at `results/gcci/regimes_athex_GCCI.png`. | P1 |
| 5.2a/b | BIST 100 under global vs Turkish CCI. Same window mismatch existed; matched-window version (38% RW, 2004-2024) regenerated by `scripts/fig5_matched_window.py`, output `outputs/rebuilt/fig5_2a_bist100_matched_GCCI.png`. Verified within 0.03pp. | P2 |
| 6.1 | Pooled forward returns by band, 4 horizons | P1 |
| 6.2 | 12-mo forward-return distributions by band | P2 |
| 6.3 | Episode-level excess returns, 30 spells | P2 |
| B.1 | Episode coverage by index and episode | P3 |

---

## Section E. Known issues found in the pre-submission review (compute the truth, then fix the text)

**E1. Section 4.1 wording vs Table 4.1.** Text says "South Korea and Mexico place the upper
threshold above the cluster"; the table shows their UPPER thresholds inside the cluster (101.26,
102.01) and their LOWER thresholds above the lower cluster (98.73, 99.27). Compute both; the text
almost certainly needs "lower".

**E2. "Every estimated b_EXP is negative"** (Section 4.2) vs BOVESPA b_EXP = 0.000 with a 0.0%
high band. Report Brazil's high-band month count from code.

**E3. Both-tails count conflict.** Table 4.1's tail-coverage column implies 20 of 23 both-tailed;
Section 7.1 says "14 under the single CCI". An earlier draft used 14 as the count of lag-4
exogeneity passes in the composite study's interim universe, so the 14 may be a transplant error.
Compute tail coverage under an explicit, stated criterion and report which criterion (if any)
yields 10 and 14.

**E4. Wald test siting.** Abstract and conclusion attach the Wald test to the recursive
encompassing exercise; per Section 6.3 and D.4 it belongs to the full-sample joint regression.
Prose fix only; no computation.

---

## Data sources (pin exact series in ASSUMPTIONS.md)

- **Trigger:** OECD amplitude-adjusted CCI, SDMX dataflow `DSD_STES@DF_CLI`, `REF_AREA=OECD`,
  subject `CCICP`; country series via FRED `CSCICP03*665S`.
- **Equity:** month-end local-currency price-index closes (source NOT stated in the paper; recover
  from code/transcripts and record it).
- **Others referenced:** MCSI, VIX, ANFCI (FRED), Shiller CAPE, Moody's BAA, EPU
  (Baker-Bloom-Davis), Turkish CPI.
