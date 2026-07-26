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

## Note on OneDrive and where `.git` lives

The working tree is inside OneDrive, but **git's internals are not**:

```
.git                          <- a 41-byte pointer file, NOT a directory
    gitdir: C:/Users/rongq/gitrepos/UROP.git
```

The real repository is at **`C:\Users\rongq\gitrepos\UROP.git`**, outside OneDrive.

**Why.** Git rewrites hundreds of small files in `.git` on every commit; OneDrive tried to sync
each one. The two fought, OneDrive burned an hour of CPU, and it silently reverted an edited
`.gitignore` into a conflict copy (`-LAPTOP-K0CP9ISC.gitignore`) — so a commit captured the old
version of a file that had already been changed. Moving `.git` out ends that class of bug while
keeping the working tree backed up by OneDrive.

**Consequences to know:**
- `git` commands work normally from the repo directory. Nothing changes day to day.
- The path in the `.git` pointer is absolute. Opening this folder from OneDrive on a *different
  machine* will not find the repo — clone from GitHub instead (below).
- `gh` does not recognise a gitdir pointer file and reports "not a git repository". Use plain
  `git` for remote work, or run `gh` with `--repo rq1234/UROP-tar-efficiency`.
- If an edit seems to vanish, look for a `*-LAPTOP-*` conflict copy before redoing the work.
  Those are gitignored.

**Backup.** `C:\Users\rongq\gitrepos\` is outside OneDrive and not covered by it. The backup is
the private GitHub remote **`rq1234/UROP-tar-efficiency`**. Push after every session — that is
the only off-machine copy of the history.
