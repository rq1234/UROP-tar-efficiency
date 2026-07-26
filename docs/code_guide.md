# Code Guide

Overview of every source file in `src/`, how they relate to each other,
and what each function does.

---

## Architecture

```
market_config.py        single source of truth — no imports from src
    |
    +-- collect_data.py     fetches equity + FRED data
    |       |
    |       +-- collect_oecd.py   fetches OECD CCI via FRED
    |
    +-- estimate.py         core TAR engine — no imports from src
    |       |
    |       +-- replicate.py      Tables 7 & 8 replication
    |       |       |
    |       |       +-- baa_study.py    BAA spread exploratory analysis
    |       |       |
    |       |       +-- cci_study.py    OECD CCI analysis pipeline
    |       |
    |       +-- robustness.py     Hurst + TAR efficiency comparison
    |
    +-- exogeneity.py       Granger exogeneity tests
            |
            +-- robustness.py
            +-- cci_study.py
```

---

## Data flow

```
collect_data.py  -->  data/equity/*.csv
                      data/sentiment/*_monthly.csv
                      data/sentiment/*_daily.csv
                      data/combined/monthly_panel.csv
                      data/combined/daily_panel.csv

collect_oecd.py  -->  data/sentiment/oecd_cci_{CODE}.csv
                      data/sentiment/oecd_cci_all.csv
                      data/sentiment/oecd_cci_coverage.csv

replicate.py     reads monthly_panel.csv + daily_panel.csv  -->  Table 7 / Table 8 output
cci_study.py     reads monthly_panel.csv + oecd_cci_*.csv   -->  CCI analysis output
robustness.py    reads daily_panel.csv                       -->  Hurst / TAR comparison
baa_study.py     reads daily_panel.csv                       -->  BAA episode analysis
exogeneity.py    reads monthly_panel.csv + daily_panel.csv  -->  Granger test output
```

---

## File reference

---

### `market_config.py` — Configuration

Single source of truth for all markets and triggers. Edit here, not in individual scripts.

**Run:** not run directly — imported by all other modules

**Contents:**

| Name | Type | Description |
|------|------|-------------|
| `SENTIMENT_MONTHLY` | dict | FRED series codes for monthly triggers (MCSI, CPI, etc.) |
| `SENTIMENT_DAILY` | dict | FRED series codes for daily triggers (VIX, BAA spread, etc.) |
| `OECD_CCI_MARKETS` | dict | Market key → OECD 3-letter country code mapping |
| `MARKETS` | dict | 23 equity indices: ticker, country, exchange |

---

### `estimate.py` — TAR Estimation Engine

Core statistical library. Translates Farid's MATLAB gridsearch2.m / gridsearchchk.m
into Python. All analytical modules import from here.

**Run:** library only — not run directly

**Functions:**

| Function | Description |
|----------|-------------|
| `gridsearch(y, z, c1, c2, spec, mode)` | Fit TAR model for a given threshold pair; returns betas, alphas, RSS |
| `find_optimal_thresholds(y, z, z_min, z_max, ...)` | Grid search over (c1, c2) pairs minimising RSS |
| `standard_errors(y, z, c1, c2, spec, mode)` | Compute betas, SEs, and t-statistics at given thresholds |
| `_ols_intercept(x, y)` | Analytical OLS with intercept; returns alpha, beta, SE |
| `_ols_no_intercept(x, y)` | Analytical OLS without intercept; returns beta, SE |
| `_assign_states(z, c1, c2)` | Assign regime state (0=RW, 1=MR, 2=EXP) to each observation |

**Imports:** `numpy`, `scipy` only

---

### `collect_data.py` — Data Collection

Fetches equity prices (Yahoo Finance) and sentiment triggers (FRED), builds
the combined monthly and daily panels used throughout the analysis.

**Run:** `python src/collect_data.py`

**Functions:**

| Function | Description |
|----------|-------------|
| `collect_all(fred_api_key=None)` | Main orchestrator: fetches all equity + triggers, builds panels |
| `fetch_equity(name, ticker)` | Download daily closes from Yahoo Finance |
| `fetch_fred(name, code, api_key)` | Download any FRED series at native frequency |
| `build_monthly_panel(equity_frames, sentiment_frames)` | Combine equity month-end + monthly triggers |
| `build_daily_panel(equity_frames, sentiment_frames)` | Combine equity daily + daily triggers |
| `to_month_end(daily_series)` | Resample daily prices to month-end closes |

**Imports:** `market_config.MARKETS`, `market_config.SENTIMENT_MONTHLY`, `market_config.SENTIMENT_DAILY`

---

### `collect_oecd.py` — OECD CCI Download

Downloads monthly OECD Consumer Confidence Indicators for all OECD markets
in the panel via FRED. Produces per-country CSVs and a coverage/grid-bounds summary.

**Run:** `python src/collect_oecd.py`

**Functions:**

| Function | Description |
|----------|-------------|
| `collect_all_cci()` | Fetch all country CCIs, save CSVs, print coverage report with recommended grid bounds |

**Outputs:**
- `data/sentiment/oecd_cci_{CODE}.csv` — per-country monthly CCI
- `data/sentiment/oecd_cci_all.csv` — wide panel
- `data/sentiment/oecd_cci_coverage.csv` — grid bounds (z_min, z_max) per market

**Imports:** `market_config.OECD_CCI_MARKETS`, `collect_data.fetch_fred`

---

### `replicate.py` — Table 7 & 8 Replication

Replicates Tables 7 and 8 from Ahmed & Satchell (2018) using collected data.
Also provides `load_pair()` — the standard data-loading utility used by all analysis scripts.

**Run:**
```
python src/replicate.py     # Table 7 (monthly, MCSI trigger)
python src/replicate.py 8   # Table 8 (daily, VIX trigger)
```

**Functions:**

| Function | Description |
|----------|-------------|
| `load_pair(panel_path, equity_col, trigger_col, start, end, skip, trigger_lag)` | Load aligned (y, z) arrays from a panel CSV with optional trigger lag |
| `replicate_table7(panel_path)` | Run all 6 rows of Table 7 and print results |
| `replicate_table8(panel_path)` | Run all 6 rows of Table 8 and print results |
| `_fmt_beta(beta, se, tstat, n, T)` | Format beta for tabular display (SE, significance star, obs%) |

**Imports:** `estimate.find_optimal_thresholds`, `estimate.standard_errors`

---

### `exogeneity.py` — Granger Exogeneity Tests

Tests whether each trigger variable is predetermined with respect to equity returns —
a prerequisite for valid regime classification. Runs validation on known pairs and
a full 27-market sweep.

**Run:**
```
python src/exogeneity.py           # full 27-market study
python src/exogeneity.py validate  # known-answer validation only
```

**Functions:**

| Function | Description |
|----------|-------------|
| `granger_f_test(y_ret, z, n_lags)` | F-test: does z Granger-cause y_ret? Returns (F, p_value) |
| `test_exogeneity(y_ret, z, n_lags, trigger_lag, alpha)` | Granger test with ADMISSIBLE / PREDETERMINED / REJECTED verdict |
| `run_validation()` | Test 6 known pairs (S&P500/FTSE100 × VIX/MCSI/BAA) |
| `run_full_study()` | Test all 27 markets × 3 triggers, print pass-rate summary |
| `_load_returns(panel_path, equity_col, start, end)` | Load log returns from panel CSV |
| `_load_trigger(panel_path, trigger_col, start, end)` | Load trigger series from panel CSV |

**Imports:** `market_config.MARKETS`

---

### `baa_study.py` — BAA Credit Spread Analysis

Exploratory analysis of S&P500 with Moody's BAA-10yr Treasury spread as trigger.
Tests whether the model identifies the 2005-07 credit euphoria and 2008-09 crisis
as distinct regimes.

**Run:** `python src/baa_study.py`

**Functions:**

| Function | Description |
|----------|-------------|
| `run_spec(spec, label)` | Grid search + episode overlap for one drift specification |
| `episode_overlap(regime_df, label, period_start, period_end)` | Print regime % breakdown for a named historical episode |
| `_regime_dates(y, z, c1, c2, panel_path, start, end)` | Reconstruct date-indexed regime classification |

**Imports:** `replicate.load_pair`, `replicate.DAILY_PANEL_PATH`, `estimate.*`

---

### `robustness.py` — Hurst Exponent vs TAR Comparison

Computes Hurst exponent (R/S analysis) and VIX-triggered TAR efficiency proportions
for all 27 markets in parallel. If both metrics agree on rankings, the TAR approach
is anchored to the established literature.

**Run:** `python src/robustness.py`

**Functions:**

| Function | Description |
|----------|-------------|
| `hurst_rs(returns, min_n)` | R/S Hurst exponent estimate (H≈0.5 = efficient, H>0.5 = persistent) |
| `tar_efficiency_fast(y, z)` | Vectorised TAR grid search using sort+prefix-sum trick; returns RW-state fraction |
| `run_comparison()` | Parallelised sweep over all 27 markets, prints ranked comparison table |
| `_analyse_market(args)` | Per-market worker function (runs in subprocess via ProcessPoolExecutor) |

**Imports:** `market_config.MARKETS`, `exogeneity._load_returns`

---

### `cci_study.py` — OECD CCI Analysis

Full analysis pipeline using each OECD market's own Consumer Confidence Indicator
as a country-specific sentiment trigger, validated against VIX-triggered results.

**Run:**
```
python src/cci_study.py            # full pipeline
python src/cci_study.py screen     # exogeneity gate
python src/cci_study.py validate   # US MCSI known-answer check
python src/cci_study.py estimate   # TAR estimation for admissible markets
python src/cci_study.py compare    # VIX vs CCI side-by-side table
python src/cci_study.py plot       # CCI time-series plots with episode shading
```

**Functions:**

| Function | Description |
|----------|-------------|
| `load_cci_pair(market, oecd_code, start, end)` | Load (y, z, dates) aligning equity prices and CCI on common monthly dates |
| `exogeneity_screen(markets, start, end, n_lags, alpha)` | Gate: does equity Granger-cause CCI? Drop markets where it does |
| `validate_us_mcsi()` | Run S&P500 + MCSI as a known-answer check (expected: BOTH TAILS) |
| `run_cci_estimation(market, oecd_code, z_min, z_max, ...)` | TAR estimation + episode overlap for one market |
| `run_estimation_all(admissible, spec)` | Estimation for all admissible markets, summary table |
| `compare_vix_cci(admissible)` | VIX (daily) vs CCI (monthly) side-by-side results table |
| `plot_cci_episodes(markets, start, end)` | Time-series plots with dot-com, GFC, euro-crisis shading |
| `_episode_verdict(y, z, c1, c2, dates, ...)` | Classify: BOTH TAILS / FEAR GAUGE / EUPHORIA GAUGE / WEAK |
| `_load_grid_bounds()` | Load per-country grid bounds from oecd_cci_coverage.csv |

**Imports:** `market_config.*`, `estimate.*`, `replicate.load_pair`, `exogeneity.granger_f_test`
