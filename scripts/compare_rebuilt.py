"""
compare_rebuilt.py - diff outputs/rebuilt/* against the surviving results/exports/*.

Every rebuilt round writes a CSV whose name matches the export it replaces. This
compares them cell by cell and reports, per file:

  - shape agreement (rows, columns, keys)
  - for numeric columns: max and median absolute difference, and how many cells
    agree at the precision the export prints
  - a verdict

Deterministic analyses should agree to floating-point noise. Seeded stochastic
ones (class S in verification_manifest.md) will NOT, because reproducing a
bootstrap exactly requires the original RNG call order, not just the seed. For
those the question is whether the paper's QUALITATIVE claim survives, which is
reported separately by each round script and recorded in ASSUMPTIONS.md.

Nothing is written to results/. Nothing is ever adjusted to force agreement.

Usage:
    python scripts/compare_rebuilt.py                 # all rebuilt files
    python scripts/compare_rebuilt.py threshold_bootstrap.csv
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config  # noqa: E402


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def numeric(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


# Candidate row-identity columns, most specific first. A combo is only used if it
# is actually UNIQUE across the file - keying fdr_coefficients on "market" alone
# silently collapses its two rows per market and reports spurious differences.
KEY_COMBOS = (
    ("market", "scheme"), ("market", "coef"), ("market", "dgp"),
    ("market", "method"), ("market", "rule"), ("market", "trigger"),
    ("market",), ("stat",), ("statistic",), ("rule",), ("method",), ("id",),
    ("country",), ("horizon_m",), ("scheme",), ("dgp",),
)


def choose_key(rows):
    """First candidate combo present in the rows AND unique across them."""
    for combo in KEY_COMBOS:
        if not all(c in rows[0] for c in combo):
            continue
        keys = [tuple(r[c] for c in combo) for r in rows]
        if len(set(keys)) == len(keys):
            return combo
    return None


def compare_file(name):
    old_p = os.path.join(config.EXPORTS, name)
    new_p = os.path.join(config.REBUILT, name)
    if not os.path.exists(old_p):
        return name, "NO ORIGINAL", ["no counterpart in results/exports - new output"]
    if not os.path.exists(new_p):
        return name, "NOT REBUILT", ["no file in outputs/rebuilt yet"]

    old, new = read(old_p), read(new_p)
    notes = [f"rows {len(old)} -> {len(new)}"]

    combo = choose_key(old)
    if combo is None:
        pairs = list(zip(old, new))
        notes.append("paired positionally (no unique key column found)")
    else:
        kf = lambda r: tuple(r[c] for c in combo)          # noqa: E731
        idx = {kf(r): r for r in new if all(c in r for c in combo)}
        pairs = [(o, idx[kf(o)]) for o in old if kf(o) in idx]
        missing = [kf(o) for o in old if kf(o) not in idx]
        notes.append(f"keyed on {'+'.join(combo)}")
        if missing:
            notes.append(f"{len(missing)} rows absent from rebuild, e.g. {missing[:3]}")

    cols = [c for c in old[0] if numeric(old[0][c]) is not None]
    stats = []
    for c in cols:
        diffs = []
        for o, n in pairs:
            a, b = numeric(o.get(c)), numeric(n.get(c))
            if a is not None and b is not None:
                diffs.append(abs(a - b))
        if diffs:
            d = np.asarray(diffs)
            stats.append((c, float(d.max()), float(np.median(d))))

    if not stats:
        return name, "NO NUMERIC COLS", notes

    worst = max(stats, key=lambda s: s[1])
    med_of_max = float(np.median([s[1] for s in stats]))
    if worst[1] < 1e-9:
        verdict = "IDENTICAL"
    elif worst[1] < 1e-4:
        verdict = "NUMERICALLY EQUAL"
    elif med_of_max < 0.5:
        verdict = "CLOSE (seed-sensitive)"
    else:
        verdict = "DIFFERS"
    notes.append(f"largest disagreement: {worst[0]} max {worst[1]:.4g} "
                 f"median {worst[2]:.4g}")
    notes.append("per-column max |diff|: " +
                 ", ".join(f"{c}={m:.3g}" for c, m, _ in sorted(
                     stats, key=lambda s: -s[1])[:6]))
    return name, verdict, notes


def main():
    targets = sys.argv[1:]
    if not targets:
        targets = sorted(f for f in os.listdir(config.REBUILT) if f.endswith(".csv"))
    if not targets:
        print("nothing in outputs/rebuilt yet")
        return

    print(f"{'file':<34}{'verdict':<26}detail")
    print("-" * 100)
    for name in targets:
        n, v, notes = compare_file(name)
        print(f"{n:<34}{v:<26}{notes[0] if notes else ''}")
        for extra in notes[1:]:
            print(f"{'':<60}{extra}")


if __name__ == "__main__":
    main()
