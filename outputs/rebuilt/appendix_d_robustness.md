# Appendix D - Section 6.3 robustness table

Every row is pulled directly from `outputs/rebuilt/numbers.json`, itself written by `scripts/verify_paper.py` against committed pipeline output - nothing here is recomputed or hand-typed.

| ID | Check | Verdict | Reproduced value |
|---|---|---|---|
| A12 | Fixed-tail percentile cuts vs TAR spread (22.14 / 22.09pp) | MATCH | cut 98.33/101.39; below 17.84 above -4.57; fixed spread 22.40pp; TAR spread 22.09pp |
| A14 | Five calendar-year clusters (year-collapsed test) | MATCH | year_collapsed t=-3.155, p=0.0343, clusters=5 |
| C37 | Episode spells (30 ex-Japan): count, mean length, mean excess, negative count | MATCH | 30 episodes, mean length 20.5, mean excess -15.04, 26 negative (col 'excess_pp') |
| C39 | Circular-shift permutation (5,000 draws) | MATCH | perm_p_le_obs=0.0, B=5000 |
| C40 | Trailing-return control (label vs trailing 12m return horse race) | MATCH | a=-14.0682 -> c=-14.0647; trailing_p=0.5052; c_exp_dk_p=0.057 |
| C41 | Asian-crisis (AFC) exclusion | MATCH | -11.45, p=0.017; excluded-spells mean=-26.843 (n=7) |
| C42 | One index per country | MATCH | -14.93, p=0.0062 |
| C43 | Japan reinstated in pooled 12m mean | MATCH | -7.49 (n=615) -> -6.08 (n=879) |
| C45 | Frozen-threshold (post-2015 out-of-sample) test | NEAR † | n_EXP=76.0, years=4.0, markets=4.0, gap=-9.839, DK_p=0.1876, block_p=0.2176 |

† NEAR: reproduces the paper's qualitative claim but not to exact precision - see the reproduced value, not the original figure, for the true number.
