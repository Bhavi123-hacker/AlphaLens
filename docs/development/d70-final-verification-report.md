# D70 final research verification — 2026-10-09

D70 real research replay COMPLETE: 152 model fits, 504 hypothetical backtests
and 46,072,188 OOS prediction records verified. Frozen dataset,
statistical configurations, folds and final-holdout boundaries are unchanged.
Completed accepted-run fits were reused after interruption; none was repeated.
The four development-locked candidates were evaluated once in 2026, without
retuning. All selected candidates remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE.
Thirty backtests have available full-path raw-price diagnostics; 474 retain
unresolved economic outcomes. All twelve Logistic fits reached their fixed
iteration limit; convergence is not established. No profitability claim follows.

Required offline research software gates: 548 passed / one expected live skip,
1912.67s, Windows-safe suite and PostgreSQL 17 replay/teardown exit 0; frozen
lock/sync, Ruff, mypy, Bandit and Python dependency audit passed. These already
completed gates were reused under unchanged statistical code and lock.
The repaired TruffleHog scan passed on GitHub. The separate foundation-container
scan FAILED on reported OS/Rust findings; it is not waived and full CI success
is not claimed. See docs/development/ci-container-scan-status.json.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.
NOT PRODUCTION PIT. Production remains OPEN/NOT_CLEARED; fundamentals and
benchmark remain UNAVAILABLE. P11-P14 are unchanged. STOP before P17.
The following earlier running/pending checkpoints are historical and superseded.

Frozen supervised identity:
`f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2`.

Frozen execution-plan SHA256:
`ff421096b839224927e3ee4d96c8faa8593895837648fbb79f87ab6d4e92675c`.

Read-only final verification checked all canonical/supervised partitions,
model and OOS checksums, immutable run identities, research classification,
shared training/test masks and features across families/tasks, chronological
fold membership, assumed availability, outcome maturity, OOS-only P10 inputs,
nonnegative cash, position limits, next-slot execution, missing benchmark,
unresolved-return nullability and chart-export hashes/counts. It verified
144 development fits plus four confirmation and four final-holdout fits,
with exactly four final-holdout attempt markers. No new fit or prediction
was made by this verifier. The receipt contains the actual verified counts.

Exact development OOS periods: 2022-01-03–2022-12-30,
2023-01-02–2023-12-29 and 2024-01-01–2024-12-31. Confirmation:
2025-01-01–2025-12-31. Locked final fold: 2026-01-01–2026-10-06.
The latest source session is retained, but a decision requiring an unknown
next-calendar boundary remains unavailable; no future session was invented.

Candidate lock:
`3ac78dd722e03301f3177b3a212a4d2fa0331e0b7e4d05bdec9929f614ccf1eb`.
Selection used only 2022–2024 OOS and fixed P10 diagnostics: HistGradientBoosting
classification at 1/5/20 sessions, XGBoost classification at 10 sessions.
Positive daily rank IC and probability-loss improvements do not establish
a profitable strategy. The 2025 10/20-session candidates failed to beat
their Brier naive baseline. The 2026 candidates beat the Brier baseline,
but balanced accuracy remains about 50.00–52.38%, with low positive recall.

The complete model-by-horizon tables are in ../ml/real-model-metrics-tables.md,
with all fold details in real-model-comparison.json/walk-forward-results.json.
The full P10 report retains every rule/cost/period, including losses and
unavailable outcomes; no policy was selected from confirmation/holdout gains.

The original DOCX SHA256 and main reference match the protected baseline.
Large raw/processed/Parquet/model files remain local, out of normal Git history.
No paid service, broker integration, real trade, frontend or P17 work was added.
