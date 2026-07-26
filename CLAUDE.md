# Reproducibility rules for this repo
- Never run analysis via heredoc or inline python -c. Every analysis is a
  script under scripts/, committed before its output is used.
- data/ and results/exports/ are read-only ground truth; new outputs go to
  outputs/rebuilt/.
- Every stochastic step takes its seed from config.py.
- After any code change, re-run scripts/check_manifest.py and commit the
  updated VERIFICATION_REPORT.md.
- Never adjust code, parameters or data to force agreement with the paper
  or the manifests. Mismatches are reported, not repaired.
- Commit after every working session. This repo lost its analysis scripts
  once because they only existed inside a session transcript.

---

## Note on scratchpads (the specific way the scripts were lost)

The lost Round 3-10 scripts were **not** heredocs. They were real `.py` files written to a
Claude Code session **scratchpad** (a temp directory), which is deleted automatically. A script
in a scratchpad is as lost as one never written. If it writes anything under `results/` or
`outputs/`, it lives in `scripts/` and is committed.

## Note on OneDrive

This repo is inside OneDrive. OneDrive creates sync-conflict copies named
`<name>-LAPTOP-XXXX.<ext>` and can revert a file you just edited. If an edit seems to vanish,
check for a `*-LAPTOP-*` copy before redoing the work. Those copies are gitignored.
