"""
Assemble the Section 6.3 robustness checks into one Appendix D exhibit table.

All nine numbers already have an individual verdict in outputs/rebuilt/numbers.json
(written by scripts/verify_paper.py) - the gap this closes is that they live
scattered across prose with no single table a referee can check against. This
script does not recompute anything; it pulls each item's already-verified
target/observed strings into one place.

C45 (frozen-threshold) is NEAR, not MATCH - the table must show the actual
reproduced values, not the paper's original claim, and flags the row so it
doesn't read as an exact match it isn't.

Output: outputs/rebuilt/appendix_d_robustness.csv
        outputs/rebuilt/appendix_d_robustness.md   (paste-ready for the manuscript)

Usage:
    python scripts/build_appendix_d_table.py
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NUMBERS_JSON = os.path.join(ROOT, "outputs", "rebuilt", "numbers.json")
OUT_CSV = os.path.join(ROOT, "outputs", "rebuilt", "appendix_d_robustness.csv")
OUT_MD = os.path.join(ROOT, "outputs", "rebuilt", "appendix_d_robustness.md")

# (manifest id, plain-English label for the Appendix D row)
ITEMS = [
    ("A12", "Fixed-tail percentile cuts vs TAR spread (22.14 / 22.09pp)"),
    ("A14", "Five calendar-year clusters (year-collapsed test)"),
    ("C37", "Episode spells (30 ex-Japan): count, mean length, mean excess, negative count"),
    ("C39", "Circular-shift permutation (5,000 draws)"),
    ("C40", "Trailing-return control (label vs trailing 12m return horse race)"),
    ("C41", "Asian-crisis (AFC) exclusion"),
    ("C42", "One index per country"),
    ("C43", "Japan reinstated in pooled 12m mean"),
    ("C45", "Frozen-threshold (post-2015 out-of-sample) test"),
]


def main():
    with open(NUMBERS_JSON, encoding="utf-8") as f:
        numbers = json.load(f)

    rows = []
    for vid, label in ITEMS:
        entry = numbers[vid]
        rows.append({
            "id": vid,
            "item": label,
            "verdict": entry["verdict"],
            "target": entry["target"],
            "reproduced": entry["observed"],
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "item", "verdict", "target", "reproduced"])
        w.writeheader()
        w.writerows(rows)

    lines = [
        "# Appendix D - Section 6.3 robustness table",
        "",
        "Every row is pulled directly from `outputs/rebuilt/numbers.json`, itself written by "
        "`scripts/verify_paper.py` against committed pipeline output - nothing here is "
        "recomputed or hand-typed.",
        "",
        "| ID | Check | Verdict | Reproduced value |",
        "|---|---|---|---|",
    ]
    for r in rows:
        flag = " †" if r["verdict"] != "MATCH" else ""
        lines.append(f"| {r['id']} | {r['item']} | {r['verdict']}{flag} | {r['reproduced']} |")
    lines.append("")
    lines.append("† NEAR: reproduces the paper's qualitative claim but not to exact "
                 "precision - see the reproduced value, not the original figure, for the true "
                 "number.")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    n_match = sum(1 for r in rows if r["verdict"] == "MATCH")
    print(f"{len(rows)} rows, {n_match} MATCH, {len(rows) - n_match} other")
    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()
