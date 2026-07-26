# Cross-Market Efficiency via Threshold Autoregressions

Python implementation extending Ahmed & Satchell (2018), testing the
"proportion-of-time-efficient" hypothesis across many world equity markets.

## Quick start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export FRED_API_KEY=your_key_here
python src/collect_data.py        # fetch all data, fresh
```

## Layout

```
data/equity/      equity index CSVs        (the assets)
data/sentiment/   trigger series CSVs       (the regime switches)
data/combined/    combined_panel.csv        (all aligned, month-end)
src/              code
docs/             methodology + guides
tests/            verification
results/          generated tables & figures
```

See `docs/data_layer.md` for how data collection works.

## Pipeline

1. **Collect** — `src/collect_data.py` pulls fresh data to month-end.
2. **Estimate** — (next module) run the threshold model per (asset, trigger).
3. **Compare** — tabulate efficiency proportions across markets.

## Verification

- Simulate data with known parameters; confirm the estimator recovers them.
- Replicate the paper's S&P 500 / FTSE 100 results as a sanity check.
