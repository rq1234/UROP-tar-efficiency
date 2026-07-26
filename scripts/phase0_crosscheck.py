"""
Phase 0(c) — cross-check verification_manifest.md against paper_numbers_manifest.csv.

Scope is deliberately narrow. This script does NOT recompute anything from data: it
compares the PAPER-side target list (verification_manifest.md, what the draft prints)
against the AUTHOR-side manifest (results/exports/paper_numbers_manifest.csv, what the
pipeline computed), and where the two disagree it adjudicates ONLY by re-reading a
committed export CSV. Recomputation from data/ is Phase 1/2 work, not this.

Read-only. Writes one file: PHASE0_CROSSCHECK.md at the repo root.

Usage:  python scripts/phase0_crosscheck.py
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "results", "exports")
TABLES = os.path.join(ROOT, "results", "tables")
OUT = os.path.join(ROOT, "PHASE0_CROSSCHECK.md")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# The comparison table.
#
# vm_*  : transcribed from verification_manifest.md (the paper's target).
# pnm   : the id(s) in paper_numbers_manifest.csv that should carry the same fact.
#         None = the paper cites a number the author-side manifest has no row for.
# ---------------------------------------------------------------------------
CHECKS = [
    # --- Section A: headline / abstract, all P1 -----------------------------
    dict(vm="A1",  cls="E", pri="P1", target="57 / 32 / 23 (Colombia no data; 24 reject)",
         pnm=["A1", "A2", "A3"]),
    dict(vm="A3",  cls="E", pri="P1", target="Japan RW 33.7 (c2=99.87); Turkey RW 94.2",
         pnm=None),
    dict(vm="A4",  cls="E", pri="P1", target="6 raw 5% rejections; 0 survive BH q=0.05",
         pnm=["P3_bRW_signs", "P3_bRW_magnitude"], adjudicate="middle_band"),
    dict(vm="A5",  cls="S", pri="P1", target="block null 3/23; iid null 9/23; 1000 sims",
         pnm=["T1_verdict"], adjudicate="placebo"),
    dict(vm="A6",  cls="E", pri="P1", target="Greece matched window, global trigger: 83% RW",
         pnm=["X4_greece_matched"]),
    dict(vm="A7",  cls="E", pri="P1", target="Greece matched window, Greek CCI: 44/31/25",
         pnm=["X4_greece_matched"]),
    dict(vm="A8",  cls="E", pri="P1", target="Greece percentile-normalised: 43.8/31.5/24.6",
         pnm=None),
    dict(vm="A9",  cls="E", pri="P1", target="12m means +14.60 / +8.01 / -7.49",
         pnm=["D_12m_MR", "D_12m_RW", "D_12m_EXP"], adjudicate="horizon12"),
    dict(vm="A10", cls="E", pri="P1", target="12m n = 1109 / 6676 / 615",
         pnm=None, adjudicate="horizon12n"),
    dict(vm="A11", cls="S", pri="P1", target="calendar bootstrap high-RW -10.88 [-18.23,-4.32]",
         pnm=["P1_pooled_gaps_ci"]),
    dict(vm="A12", cls="E", pri="P1", target="fixed-tail spread 22.14 vs TAR 22.09",
         pnm=["F2"]),
    dict(vm="A13", cls="E", pri="P1", target="29 of 30 high spells in 1997-2000",
         pnm=["X1_n_year_clusters"]),
    dict(vm="A14", cls="E", pri="P1", target="five-cluster: mean -18.3, t=-3.16, p=0.034",
         pnm=["X1_episode_yearcollapsed"]),

    # --- Section B: table targets -------------------------------------------
    dict(vm="B1",  cls="E", pri="P1", target="Table 4.1, 23 rows",
         pnm=None, adjudicate="table41"),
    dict(vm="B2",  cls="E", pri="P1", target="Table 6.1, 4 horizons",
         pnm=["D0"], adjudicate="table61"),
    dict(vm="B3",  cls="E", pri="P1", target="Table 5.1 matched windows",
         pnm=["X4_greece_matched", "X4_turkey_matched"]),
    dict(vm="B5",  cls="E", pri="P2", target="Table A.1, all 57 candidates",
         pnm=["A6"], adjudicate="appendixA"),
    dict(vm="B7",  cls="V", pri="P2", target="Table C.1, 26 country correlations",
         pnm=["G5"], adjudicate="appendixC"),

    # --- Section C: in-text -------------------------------------------------
    dict(vm="C2",  cls="E", pri="P2", target="8-lag screen: 22/23 pass, Japan p=0.042",
         pnm=["A7"]),
    dict(vm="C11", cls="E", pri="P2", target="S&P vs US CCI screen F=3.54 p=0.008",
         pnm=["V1_uscci_granger"]),
    dict(vm="C13", cls="S", pri="P2", target="placebo iid null 9/23, 1000 sims",
         pnm=["T1_rss_percentile_median"], adjudicate="placebo"),
    dict(vm="C14", cls="S", pri="P2", target="placebo 12-mo block null 3/23",
         pnm=None, adjudicate="placebo"),
    dict(vm="C18", cls="E", pri="P2", target="RW share 76.9 -> 80.2; Spearman 0.878",
         pnm=["P2_metricB_shares", "P2_rank_corr"]),
    dict(vm="C19", cls="E", pri="P2", target="constant drift Spearman 0.42; shift 9pp",
         pnm=["Y4_rank_corr_constdrift", "Y4_share_shift"]),
    dict(vm="C20", cls="E", pri="P1", target="16 neg / 7 pos; 6 raw; 0 after BH; median -0.0063",
         pnm=["P3_bRW_signs", "P3_bRW_magnitude"], adjudicate="middle_band"),
    dict(vm="(none)", cls="E", pri="P2", target="Sec7.2 cites 8/23 median -0.0087 - DIFFERENT spec",
         pnm=["T5_count_sig", "T5_median_b2"], adjudicate="middle_band"),
    dict(vm="C21", cls="S", pri="P2", target="wild CI widths c1 2.14, c2 1.00, RW 37pp, high 13pp",
         pnm=["P1_boot_wild_conditional"]),
    dict(vm="C22", cls="S", pri="P2", target="block CI widths c1 2.93, c2 2.68, RW 67pp, high 62pp",
         pnm=["P1_boot_c1_width", "P1_boot_share_width"]),
    dict(vm="C23", cls="E", pri="P2", target="min-regime rank corr 0.836 -> 0.247; all 23 feasible",
         pnm=["P2_pct5", "P2_pct10", "P2_pct15"]),
    dict(vm="C36", cls="S", pri="P2", target="MR-RW +8.18 [+2.52,+15.41]; EXP-RW -10.88",
         pnm=["P1_pooled_gaps_ci"]),
    dict(vm="C29", cls="E", pri="P1", target="low>RW 19/23 p=0.0026; high<RW 20/21",
         pnm=["F6"]),
    dict(vm="C30", cls="E", pri="P1", target="pooled CCI 10th/90th = 98.4 / 101.4",
         pnm=["F2"]),
    dict(vm="C31", cls="E", pri="P2", target="TAR high -11.28 (p=0.019); fixed -4.36 (p=0.59)",
         pnm=["P4d_horserace_fixedbands"]),
    dict(vm="C32", cls="E", pri="P2", target="Wald DK p=0.516; block p=0.618",
         pnm=None),
    dict(vm="C35", cls="S", pri="P1", target="fixed-label MBB high-RW -15.5; DK p=0.040",
         pnm=["F4_L12", "F5"]),
    dict(vm="C37", cls="E", pri="P1", target="30 spells; length 20.5; excess -15.0; 26/30 neg",
         pnm=["S2_n_episodes", "S2_mean_excess", "S2_share_negative"]),
    dict(vm="C38", cls="E", pri="P1", target="5 clusters: -18.3, t=-3.16, p=0.034",
         pnm=["X1_episode_yearcollapsed"]),
    dict(vm="C51", cls="E", pri="P2", target="BH: 19/24 screen, 30/33 coefficient",
         pnm=["W3_exog_fdr", "W4_coef_fdr"]),
    dict(vm="C52", cls="E", pri="P2", target="agreement 88.2 / 84.6; kappa 0.74; 38.8% boundary",
         pnm=["R4b_overall_and_post2015", "R4c_boundary_share"]),

    # --- Section E: known issues -------------------------------------------
    dict(vm="E2",  cls="E", pri="P1", target="BOVESPA b_EXP=0.000, high band 0.0% - count months",
         pnm=None, adjudicate="bovespa"),
    dict(vm="E3",  cls="E", pri="P1", target="tail coverage: 20/23 both-tailed vs Sec7.1 '14'",
         pnm=None, adjudicate="tails"),
]


# ---------------------------------------------------------------------------
# Adjudicators — each re-reads a committed export and returns a finding string.
# These COUNT rows in existing outputs. They do not re-estimate anything.
# ---------------------------------------------------------------------------

def adj_middle_band():
    rw = read_csv(os.path.join(EXPORTS, "rw_band_validation.csv"))
    ub = read_csv(os.path.join(EXPORTS, "unrestricted_b2.csv"))
    rw_sig = sum(1 for r in rw if float(r["p_RW"]) < 0.05)
    rw_bh = sum(1 for r in rw if r["reject_RW_restriction"].strip().lower() == "true")
    rw_med = sorted(float(r["b_RW"]) for r in rw)[len(rw) // 2]
    ub_sig = sum(1 for r in ub if r["sig5"].strip().lower() == "true")
    ub_med = sorted(float(r["b2_rw"]) for r in ub)[len(ub) // 2]
    same = sum(1 for a, b in zip(rw, ub)
               if abs(float(a["b_RW"]) - float(b["b2_rw"])) < 1e-9)
    return (f"rw_band_validation.csv (Round 10 P3, thresholds FIXED at baseline): "
            f"{rw_sig}/23 raw p<0.05, {rw_bh}/23 reject after BH, median b_RW={rw_med:.4f}. "
            f"unrestricted_b2.csv (Round 4 T5, thresholds RE-ESTIMATED): "
            f"{ub_sig}/23 sig at 5%, median b2={ub_med:.5f}. "
            f"Identical b to 1e-9 in {same}/23 markets.")


def adj_placebo():
    p = read_csv(os.path.join(EXPORTS, "placebo_1000.csv"))
    out = []
    for dgp in sorted({r["dgp"] for r in p}):
        rows = [r for r in p if r["dgp"] == dgp]
        beat = sum(1 for r in rows if float(r["emp_p_rss"]) < 0.05)
        med = sorted(float(r["real_pctile"]) for r in rows)[len(rows) // 2]
        out.append(f"{dgp}: {beat}/{len(rows)} at p<0.05, median real pctile {med:g}")
    return "placebo_1000.csv -> " + "; ".join(out)


def adj_horizon12():
    h = read_csv(os.path.join(EXPORTS, "horizon_test.csv"))
    r = [x for x in h if x.get("horizon_m", "").strip() in ("12", "12m", "12.0")]
    if not r:
        return f"horizon_test.csv columns: {list(h[0].keys())} (no 12m row matched)"
    return f"horizon_test.csv 12m row -> {r[0]}"


def adj_horizon12n():
    return adj_horizon12()


def adj_table41():
    t = read_csv(os.path.join(TABLES, "global_cci_all_markets.csv"))
    return (f"results/tables/global_cci_all_markets.csv has {len(t)} rows, "
            f"columns {list(t[0].keys())}")


def adj_table61():
    h = read_csv(os.path.join(EXPORTS, "horizon_test.csv"))
    return f"horizon_test.csv has {len(h)} rows, columns {list(h[0].keys())}"


def adj_appendixA():
    a = read_csv(os.path.join(EXPORTS, "appendixA_granger_global_cci.csv"))
    key = "gate" if "gate" in a[0] else list(a[0].keys())[-1]
    counts = {}
    for r in a:
        counts[r[key].strip()] = counts.get(r[key].strip(), 0) + 1
    return f"appendixA_granger_global_cci.csv: {len(a)} rows, {key} -> {counts}"


def adj_appendixC():
    c = read_csv(os.path.join(EXPORTS, "appendixC_dcci_correlations.csv"))
    return f"appendixC_dcci_correlations.csv: {len(c)} rows, columns {list(c[0].keys())}"


def adj_bovespa():
    t = read_csv(os.path.join(TABLES, "global_cci_all_markets.csv"))
    row = next((r for r in t if r["market"] == "bovespa"), None)
    if not row:
        return "bovespa not found in global_cci_all_markets.csv"
    return (f"bovespa: n_ex={row.get('n_ex')}, beta_ex={row.get('beta_ex')}, "
            f"se_ex={row.get('se_ex')}, sig_ex={row.get('sig_ex')}, T={row.get('T')}")


def adj_tails():
    """E3 asks: under which explicit criterion does 'both tails covered' equal 20, 14 or 10?

    Sweeps a minimum-band-share rule and a significance rule over the committed panel.
    """
    t = read_csv(os.path.join(TABLES, "global_cci_all_markets.csv"))
    rows = []
    for r in t:
        T = float(r["T"])
        rows.append(dict(
            mkt=r["market"],
            low_pct=100.0 * float(r["n_mr"]) / T,
            high_pct=100.0 * float(r["n_ex"]) / T,
            low_sig=bool((r.get("sig_mr") or "").strip()),
            high_sig=bool((r.get("sig_ex") or "").strip()),
        ))

    out = []
    for thr in (0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0):
        both = sum(1 for x in rows if x["low_pct"] > thr and x["high_pct"] > thr)
        out.append(f"share>{thr:g}%: {both}")
    sig_both = sum(1 for x in rows if x["low_sig"] and x["high_sig"])
    nonempty = sum(1 for x in rows if x["low_pct"] > 0 and x["high_pct"] > 0)

    # which markets flip between the >1.5% and >2.0% rules
    flip = [x["mkt"] for x in rows
            if (x["low_pct"] > 1.5 and x["high_pct"] > 1.5)
            and not (x["low_pct"] > 2.0 and x["high_pct"] > 2.0)]

    return ("min-band-share sweep (both tails covered, of 23) -> " + "; ".join(out) +
            f". Both slopes starred: {sig_both}. Both bands non-empty: {nonempty}. "
            f"Markets lost going 1.5%->2.0%: {flip or 'none'}. "
            "NOTE: verification_manifest B1's tail_coverage column marks KLCI (low 1.5%) and "
            "TWSE (low 1.7%) as 'High only' while IBEX35 (2.0%) is 'Both' — i.e. that column "
            "is consistent with a ~2% minimum-share rule, NOT with non-emptiness.")


ADJUDICATORS = {
    "middle_band": adj_middle_band, "placebo": adj_placebo,
    "horizon12": adj_horizon12, "horizon12n": adj_horizon12n,
    "table41": adj_table41, "table61": adj_table61,
    "appendixA": adj_appendixA, "appendixC": adj_appendixC,
    "bovespa": adj_bovespa, "tails": adj_tails,
}


def main():
    pnm = {r["id"]: r for r in
           read_csv(os.path.join(EXPORTS, "paper_numbers_manifest.csv"))}

    lines = [
        "# PHASE 0(c) — verification_manifest.md vs paper_numbers_manifest.csv",
        "",
        "Generated by `scripts/phase0_crosscheck.py`. Read-only: compares the two manifests",
        "and adjudicates disagreements by re-reading committed exports. Nothing recomputed",
        "from `data/`; that is Phase 1/2.",
        "",
        f"Author-side manifest: **{len(pnm)} rows**. Paper-side entries checked here: "
        f"**{len(CHECKS)}**.",
        "",
        "| VM id | Cls | Pri | Paper target | Author manifest | Status |",
        "|---|---|---|---|---|---|",
    ]

    missing, adjudications = [], []
    for c in CHECKS:
        if c["pnm"] is None:
            author, status = "—", "**NO AUTHOR ROW**"
            missing.append(c["vm"])
        else:
            found = [i for i in c["pnm"] if i in pnm]
            gone = [i for i in c["pnm"] if i not in pnm]
            author = " / ".join(
                f"`{i}`: {pnm[i]['value'][:70]}" for i in found) or "—"
            if gone and not found:
                status, _ = f"**IDs ABSENT**: {', '.join(gone)}", missing.append(c["vm"])
            elif gone:
                status = f"partial (absent: {', '.join(gone)})"
            else:
                status = "paired"
        if c.get("adjudicate"):
            status += " · adjudicated"
        lines.append(
            f"| {c['vm']} | {c['cls']} | {c['pri']} | {c['target']} | "
            f"{author.replace('|', '\\|')} | {status} |")

    lines += ["", "## Adjudications from committed exports", ""]
    done = set()
    for c in CHECKS:
        a = c.get("adjudicate")
        if not a or a in done:
            continue
        done.add(a)
        try:
            lines.append(f"- **{a}** ({c['vm']}): {ADJUDICATORS[a]()}")
        except Exception as exc:                      # noqa: BLE001
            lines.append(f"- **{a}** ({c['vm']}): FAILED — {type(exc).__name__}: {exc}")

    lines += [
        "",
        "## Paper numbers with no author-side manifest row",
        "",
        "These are cited in the draft but have no row in `paper_numbers_manifest.csv`, so "
        "there is no author-side value to diff against. They need fresh implementation.",
        "",
        "".join(f"- `{m}`\n" for m in missing) or "- (none)",
    ]

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")
    print(f"{len(CHECKS)} checked, {len(missing)} with no author row")


if __name__ == "__main__":
    main()
