# Data Layer

## Folder structure

```
data/
├── equity/           DAILY closes, one CSV per index        (date, price)
├── sentiment/        native-frequency per trigger
│   ├── mcsi_monthly.csv    monthly
│   ├── cpi_monthly.csv     monthly
│   ├── hy_spread_monthly.csv
│   ├── yield_curve_monthly.csv
│   ├── epu_monthly.csv
│   ├── vix_daily.csv       daily
│   └── ted_spread_daily.csv
└── combined/
    ├── monthly_panel.csv   equity (month-end) + monthly triggers
    └── daily_panel.csv     equity (daily)     + daily triggers
```

## Why two frequencies? — this matches the paper exactly

The paper runs TWO separate analyses:

| Paper table | Equity freq | Trigger | Why |
|-------------|-------------|---------|-----|
| Table 7     | Monthly     | MCSI    | MCSI only published monthly |
| Table 8     | Daily       | VIX     | VIX available daily, more obs |

MCSI is monthly — you literally cannot run a daily regression with it
because it doesn't exist between survey dates. VIX is daily — using it
at monthly frequency throws away >95% of the available information.

So equity data is stored at its native DAILY frequency, and the two
panels are derived from it:

- `monthly_panel.csv`:  equity resampled to MONTH-END + monthly triggers
- `daily_panel.csv`:    equity at daily close + daily triggers

## How everything aligns

Monthly: `.resample("ME").last()` snaps all equity and monthly trigger
series to the same month-end dates (Jan-31, Feb-28/29, etc.).

Daily: equity closes and VIX are both trading-day frequency and align
naturally on business dates.

## Running the collector

```bash
pip install pandas pandas-datareader yfinance fredapi
export FRED_API_KEY=your_key_here
python src/collect_data.py
```

Re-run any time to refresh to the latest available data.

## A note on overlapping windows

Different series have different start dates:
  - MCSI: 1978
  - VIX:  1990
  - Shanghai, Hang Seng, etc.: early 1990s

Do NOT force one global window. When estimating, restrict each
(asset, trigger) pair to its own overlapping date range.
