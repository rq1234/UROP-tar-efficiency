"""
Rolling-window threshold stability analysis.

Runs find_optimal_thresholds() on successive 10-year windows (1-year step)
to produce a time series of (c1, c2) pairs showing whether the thresholds
are stable over time or exhibit a structural break.

Flat lines = stable model parameters.
Drift or kink = structural break — you can see when and how large.

Usage:
    cd src && python rolling_thresholds.py          # MCSI + CCI (SP500 & FTSE)
    python rolling_thresholds.py mcsi               # MCSI pairs only
    python rolling_thresholds.py cci                # CCI (SP500 & FTSE) only
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from estimate import find_optimal_thresholds
from bubble_now import (
    load_pair_with_dates, load_cci_with_dates,
    _panel_path, _cci_specs, _cci_min_gap,
    FIGURES_DIR, TABLES_DIR, FULL_END, INSAMPLE_END, CCI_START,
)

# Panel pairs — same spec format as bubble_now.PAIR_SPECS
ROLL_SPECS = [
    ("monthly", "eq_sp500",   "mcsi", "1978-01", 57, 110, 100, 4, 1, 0, "SP500_MCSI"),
    ("monthly", "eq_ftse100", "mcsi", "1984-01", 57, 110, 100, 4, 1, 0, "FTSE100_MCSI"),
]

WINDOW_MONTHS = 120  # 10-year rolling window
STEP_MONTHS   = 12   # step forward 1 year at a time


# ---------------------------------------------------------------------------
# Core rolling estimation
# ---------------------------------------------------------------------------

def rolling_windows(y, z, dates, z_min, z_max, gl, mg, sp,
                    window=WINDOW_MONTHS, step=STEP_MONTHS):
    """
    Slide a fixed-length window over (y, z) and estimate TAR thresholds
    at each position.

    Returns list of (end_date, c1, c2) — one entry per window.
    end_date is the last date in that window (the "as-of" date).
    """
    rows = []
    n = len(y)
    i = 0
    while i + window <= n:
        y_w = y[i : i + window]
        z_w = z[i : i + window]
        end_date = dates[i + window - 1]
        try:
            opt = find_optimal_thresholds(y_w, z_w, z_min, z_max, gl, mg, sp, "returns")
            rows.append((end_date, opt["c1"], opt["c2"]))
        except Exception as e:
            print(f"    skip window ending {end_date}: {e}")
        i += step
    return rows


# ---------------------------------------------------------------------------
# Panel pairs (MCSI)
# ---------------------------------------------------------------------------

def run_rolling_panel(spec, window=WINDOW_MONTHS, step=STEP_MONTHS):
    """Rolling estimation for one MCSI/VIX panel pair."""
    freq, eq, trig, start, z_min, z_max, gl, mg, sp, tlag, label = spec
    path = _panel_path(freq)

    y, z, dates = load_pair_with_dates(path, eq, trig, start, FULL_END, tlag)

    # In-sample reference thresholds (paper's 1990–2015 window)
    y_in, z_in, _ = load_pair_with_dates(path, eq, trig, start, INSAMPLE_END, tlag)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, sp, "returns")

    print(f"  [{label}] T={len(y)}, rolling {window//12}-yr windows "
          f"(ref: c1={ref['c1']:.1f} c2={ref['c2']:.1f}) ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, sp, window, step)
    print(f" {len(rows)} windows")

    return label, rows, ref["c1"], ref["c2"]


# ---------------------------------------------------------------------------
# CCI pairs
# ---------------------------------------------------------------------------

def run_rolling_cci(cci_spec, window=WINDOW_MONTHS, step=STEP_MONTHS):
    """Rolling estimation for one (market, CCI) pair."""
    market, oecd_code, country, z_min, z_max, label = cci_spec
    gl = 100
    mg = _cci_min_gap(z_min, z_max)

    y, z, dates = load_cci_with_dates(market, oecd_code, CCI_START, FULL_END)

    y_in, z_in, _ = load_cci_with_dates(market, oecd_code, CCI_START, INSAMPLE_END)
    ref = find_optimal_thresholds(y_in, z_in, z_min, z_max, gl, mg, 1, "returns")

    print(f"  [{label}] T={len(y)}, rolling {window//12}-yr windows "
          f"(ref: c1={ref['c1']:.2f} c2={ref['c2']:.2f}) ...", end="", flush=True)
    rows = rolling_windows(y, z, dates, z_min, z_max, gl, mg, 1, window, step)
    print(f" {len(rows)} windows")

    return label, rows, ref["c1"], ref["c2"]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def plot_rolling(label, rows, ref_c1, ref_c2):
    """Save a time-series plot of c1 and c2 across rolling windows."""
    os.makedirs(FIGURES_DIR, exist_ok=True)

    dates_arr = np.array([r[0] for r in rows], dtype="datetime64[ns]")
    c1_arr    = np.array([r[1] for r in rows])
    c2_arr    = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(dates_arr, c1_arr, color="cornflowerblue", linewidth=1.8,
            label=f"c₁ (rolling)")
    ax.plot(dates_arr, c2_arr, color="tomato", linewidth=1.8,
            label=f"c₂ (rolling)")

    ax.axhline(ref_c1, color="cornflowerblue", linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c₁ in-sample ref  ({ref_c1:.2f})")
    ax.axhline(ref_c2, color="tomato",         linewidth=0.9, linestyle="--",
               alpha=0.65, label=f"c₂ in-sample ref  ({ref_c2:.2f})")

    ax.axvline(np.datetime64("2015-06-30", "ns"), color="navy",
               linewidth=1.0, linestyle=":", alpha=0.7,
               label="2015-06  (paper cutoff)")

    ax.set_title(
        f"{label}  —  rolling {WINDOW_MONTHS//12}-year TAR thresholds  "
        f"(step = 1 year,  window = {WINDOW_MONTHS} obs)",
        fontsize=9,
    )
    ax.set_xlabel("Window end date", fontsize=8)
    ax.set_ylabel("Trigger threshold", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.margins(x=0.01)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, f"rolling_thresholds_{label}.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"    -> {out}")


def save_table(label, rows, ref_c1, ref_c2):
    """Save rolling threshold values to CSV."""
    os.makedirs(TABLES_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=["window_end", "c1", "c2"])
    df["window_end"] = pd.DatetimeIndex(df["window_end"]).strftime("%Y-%m")
    df = df.round({"c1": 3, "c2": 3})
    path = os.path.join(TABLES_DIR, f"rolling_thresholds_{label}.csv")
    df.to_csv(path, index=False)
    print(f"    -> {path}")

    # Brief console summary
    print(f"    c1: min={df['c1'].min():.2f}  max={df['c1'].max():.2f}  "
          f"mean={df['c1'].mean():.2f}  ref={ref_c1:.2f}")
    print(f"    c2: min={df['c2'].min():.2f}  max={df['c2'].max():.2f}  "
          f"mean={df['c2'].mean():.2f}  ref={ref_c2:.2f}")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run_mcsi():
    print("\n=== MCSI rolling thresholds ===")
    for spec in ROLL_SPECS:
        label, rows, ref_c1, ref_c2 = run_rolling_panel(spec)
        plot_rolling(label, rows, ref_c1, ref_c2)
        save_table(label, rows, ref_c1, ref_c2)


def run_cci():
    print("\n=== CCI rolling thresholds (SP500 + FTSE100) ===")
    cci_specs = _cci_specs()
    for cci_spec in cci_specs:
        if cci_spec[0] not in ("sp500", "ftse100"):
            continue
        label, rows, ref_c1, ref_c2 = run_rolling_cci(cci_spec)
        plot_rolling(label, rows, ref_c1, ref_c2)
        save_table(label, rows, ref_c1, ref_c2)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "mcsi":
        run_mcsi()
    elif cmd == "cci":
        run_cci()
    else:
        run_mcsi()
        run_cci()
