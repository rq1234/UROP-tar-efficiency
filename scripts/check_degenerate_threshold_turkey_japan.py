"""
Check a claim made about Fig 5.2a (BIST100 matched-window, c2=99.61): that this
is the same "degenerate upper threshold" condition the paper documents for
Japan (c2=99.87, both below the Global OECD CCI's long-run average of 100),
and that it mechanically explains the high EXP share the same way.

Read-only diagnostic - confirms or corrects the claim before it goes into the
manuscript, since it was proposed as an inference from the figure title, not
something the pipeline itself reported.

Usage:
    python scripts/check_degenerate_threshold_turkey_japan.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import config                                                  # noqa: E402
from global_cci_study import load_global_cci_pair, load_global_cci_monthly  # noqa: E402


def main():
    cci = load_global_cci_monthly()
    print(f"Global OECD CCI, full series: mean={cci.mean():.3f}, "
          f"median={cci.median():.3f}, std={cci.std():.3f}")

    # Japan: full sample, spec=1 panel value
    y, z, dates = load_global_cci_pair("nikkei225", config.START, None)
    c2_japan = 99.87
    above_japan = 100.0 * float((z[1:] > c2_japan).sum()) / len(z[1:])
    print(f"\nJapan window ({dates[0]} to {dates[-1]}, T={len(z)}):")
    print(f"  global CCI mean over this window: {z.mean():.3f}")
    print(f"  c2={c2_japan}: {above_japan:.1f}% of months have global CCI > c2")
    print(f"  (panel's actual EXP% for nikkei225: 60.6%)")

    # Turkey: matched window only (2004-02 to 2024-01), c2 from the regenerated Fig 5.2a
    y2, z2, dates2 = load_global_cci_pair("bist100", config.START, None)
    import pandas as pd
    months = pd.to_datetime(dates2).to_period("M")
    cpath = os.path.join(config.DATA, "sentiment", "oecd_cci_TUR.csv")
    cs = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
    cs.index = pd.to_datetime(cs.index).to_period("M")
    keep = np.array([m in set(cs.index) for m in months])
    zm = z2[keep]
    c2_turkey = 99.61
    above_turkey = 100.0 * float((zm[1:] > c2_turkey).sum()) / len(zm[1:])
    print(f"\nTurkey matched window (T={len(zm)}):")
    print(f"  global CCI mean over this window: {zm.mean():.3f}")
    print(f"  c2={c2_turkey}: {above_turkey:.1f}% of months have global CCI > c2")
    print(f"  (regenerated Fig 5.2a's actual EXP%: 55.8%)")

    # Same check, but for Turkey's c2 applied to the FULL sample, and Japan's c2
    # applied to Turkey's matched window, to separate "which c2" from "which window"
    above_turkey_c2_on_japan_window = 100.0 * float((z[1:] > c2_turkey).sum()) / len(z[1:])
    above_japan_c2_on_turkey_window = 100.0 * float((zm[1:] > c2_japan).sum()) / len(zm[1:])
    print(f"\nCross-check (separating threshold level from window):")
    print(f"  Turkey's c2 ({c2_turkey}) applied to Japan's full-sample window: "
          f"{above_turkey_c2_on_japan_window:.1f}% above")
    print(f"  Japan's c2 ({c2_japan}) applied to Turkey's matched window: "
          f"{above_japan_c2_on_turkey_window:.1f}% above")


if __name__ == "__main__":
    main()
