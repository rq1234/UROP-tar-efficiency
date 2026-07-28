"""
run_all.py - reproduce every rebuilt analysis, end to end.

Runs the validation gate first, then each round script, then the comparison
against the surviving exports and the paper-verification pass.

    python scripts/run_all.py              # everything
    python scripts/run_all.py --fast       # skip the B>=1000 resampling stages
    python scripts/run_all.py --list       # show the stages and exit

Nothing here writes to data/ or results/. Rebuilt outputs go to outputs/rebuilt/.

STAGE 0 IS A GATE. If fastgrid stops reproducing src/estimate.find_optimal_thresholds
to 1e-9 on all 23 markets, everything downstream is untrustworthy and the run
aborts rather than producing quietly wrong numbers.
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# (script, description, is_slow)
STAGES = [
    ("fastgrid.py", "GATE: fastgrid == find_optimal_thresholds to 1e-9", False),
    ("round01_horizon.py", "horizon table, per-market, EXP phase, F6, episodes, expn", False),
    ("round02_pool_optionAB.py", "R2/R3b pool exclusions, R4 Option A/B agreement", False),
    ("round03_episodes.py", "S1 country-CCI TAR (athex/bist100), S3 MR cluster count", False),
    ("round04_appendices.py", "T5 unrestricted band + Appendices A/B/C", False),
    ("round05_audit.py", "V1 reverse-Granger, V3 gCCI labels, V4 MCSI re-pull", False),
    ("round06_drift_fdr.py", "W1 drift table, W3/W4 Benjamini-Hochberg", False),
    ("round07_dependence.py", "X1/X4/X6/X7/X8 dependence corrections", False),
    ("round09_diagnostics.py", "P1/P2 regime-dynamics audit, two-metric efficiency", False),
    ("round10_rwband.py", "P3 RW-band validation at fixed thresholds", False),
    ("round10_remainder.py", "P2/P4.1/P4.3/P5/P8 min-regime, Wald, recursive, publag, scale", False),
    ("round08_permutation.py", "Y2 circular-shift permutation, B=5000", True),
    ("round10_placebo.py", "P9 placebo, B=1000, iid and block nulls", True),
    ("round10_bootstrap.py", "P1 threshold + pooled bootstrap, B=1000", True),
]

FINAL = [
    ("compare_rebuilt.py", "diff every rebuilt output against its export"),
    ("verify_paper.py", "verdict per paper number -> VERIFICATION_REPORT.md"),
]


def run(script, args=()):
    path = os.path.join(HERE, script)
    t0 = time.time()
    proc = subprocess.run([PY, path, *args], cwd=os.path.dirname(HERE))
    return proc.returncode, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="skip the B>=1000 resampling stages")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for s, d, slow in STAGES:
            print(f"  {'[slow] ' if slow else '       '}{s:<28}{d}")
        for s, d in FINAL:
            print(f"          {s:<28}{d}")
        return 0

    stages = [s for s in STAGES if not (args.fast and s[2])]
    print(f"Reproducing {len(stages)} stages"
          f"{' (fast mode: resampling stages skipped)' if args.fast else ''}\n")

    t0, failed = time.time(), []
    for i, (script, desc, _) in enumerate(stages, 1):
        print(f"{'=' * 78}\n[{i}/{len(stages)}] {script} - {desc}\n{'=' * 78}")
        code, dt = run(script)
        print(f"\n  ... {script} finished in {dt:.0f}s (exit {code})\n")
        if code != 0:
            failed.append(script)
            if script == "fastgrid.py":
                print("GATE FAILED: fastgrid no longer reproduces the reference "
                      "estimator. Aborting - everything downstream would be suspect.")
                return 1

    for script, desc in FINAL:
        print(f"{'=' * 78}\n{script} - {desc}\n{'=' * 78}")
        code, _ = run(script)
        if code != 0:
            failed.append(script)

    print(f"\n{'=' * 78}")
    print(f"total {time.time() - t0:.0f}s")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("all stages completed")
    print("\n  outputs/rebuilt/     regenerated analyses")
    print("  VERIFICATION_REPORT.md  verdict for every paper number")
    return 0


if __name__ == "__main__":
    sys.exit(main())
