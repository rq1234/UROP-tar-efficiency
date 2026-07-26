# OECD CCI vintage availability (P8, R4)

- The pipeline uses the FINAL-vintage OECD.Stat amplitude-adjusted composite CCI (DSD_STES@DF_CLI, REF_AREA=OECD, CCICP, AA). Option B ('frozen-threshold stability') therefore conditions on final-vintage data, not a real-time information set.
- Publication lag: OECD CCI is released ~the following month; `horizon_test_publag.csv` re-runs the 12-month test labelling month t with the CCI known by end of t (lag 1) and lag 2, alongside lag 0.
- Real-time vintages: FRED/ALFRED archives real-time vintages for some CSCICP03 country series; an ALFRED vintage pull for the OECD-aggregate series was NOT performed in this offline run and should be checked before any real-time claim. If no vintage exists, the prose reframes Option B as final-vintage stability rather than an out-of-sample forecast.
