# Forecast performance — 24 October 2026

Status: **BLOCKED_EXTERNAL_EVIDENCE** for prospective usefulness.
The saved historical results show **NO_DEMONSTRATED_EDGE**. This audit read
existing evaluations and SQLite ledgers; it did not train, issue forecasts,
mature outcomes, retune thresholds or rerun the final holdout.

Read-only snapshot at 2026-10-24 05:55 UTC, refreshed within this campaign:
184 V2 ledgers contain **633 raw forecast records**, **602 unique
model/security/observation-session decisions**, **zero outcome records** and
therefore **zero matured outcomes**. The raw total includes the original
31-record V2 ledger and 183 expanded-ledger shards. Original V1 records are a
separate preserved family and are not included in 633. Counts were read using
SQLite `mode=ro` and `PRAGMA query_only`, without worker imports or initialization.
Private per-ledger body hashes and selected-model manifests are recorded in
`.local-data/completion/research-snapshot.json`.

No prospective accuracy, precision, recall, F1, ROC-AUC, Brier, calibration
error, MAE/RMSE, profit or drawdown can be reported from zero matured outcomes.
These quantities are unavailable, not zero percent. The 43 saved LSTM scores
remain dated research scores; they are not 43 independent matured forecasts.
Repeated forecasts and overlapping holding horizons cannot be treated as
independent Bernoulli trials.

Saved V2 bodies contain actual record/inference times, horizon, score,
model/data/feature/protocol IDs, complete vector/hash, original source clocks,
dated observation and next-session timing, cohort hashes/ranks and frozen
baseline scores. Maturation requires all five actual subsequent eligible
sessions, exact identities, source hashes, official timing links and conservative
later retrieval after the exit date. Later revisions append outcomes rather
than overwrite original evidence. Missing session or publication evidence keeps
the outcome pending. No weekday-derived maturity date or same-day provisional
close was substituted.

Existing evaluation software provides matured-only accuracy/balanced accuracy,
precision/recall/Brier, frozen baselines, period diagnostics, date-block
uncertainty and rank/reference-cost statistics. Classifier scores are explicitly
uncalibrated. A classification model need not fabricate a numeric expected
return; return-error metrics apply only where a compatible return regressor
and observed target exist. A genuine external NSE benchmark remains unavailable.

The following metrics were transcribed from previously saved evaluations,
without recomputing predictions. They are development/final-vintage research,
not prospective acceptance:

| Study / model | Sample basis | Balanced accuracy | ROC-AUC | Brier | Date-rank IC |
| --- | --- | ---: | ---: | ---: | ---: |
| V2 selected histogram booster | 39,847 rows, 934 dates, 2023-01-02–2026-10-08 | 50.1085% | 0.511012 | 0.252864 | 0.001997 |
| V2 majority | Same rows | 50.0000% | See saved evaluation | See saved evaluation | Constant score |
| V2 mean reversion | Same rows | 51.1131% | See saved evaluation | See saved evaluation | See saved evaluation |
| Sequence LSTM | 27,820 rows / 420 dates / 97 stocks, 2025-01-29–2026-10-09 | 51.1185% | 0.511518 | 0.250148 | 0.060122 |
| Sequence XGBoost | Same sequence samples | 52.1928% | 0.530803 | 0.251245 | 0.086416 |
| Sequence histogram booster | Same sequence samples | 52.1404% | 0.525413 | 0.254165 | 0.071724 |
| Sequence forest | Same sequence samples | 52.0173% | 0.527734 | 0.251296 | 0.084710 |
| Sequence reversal / majority / momentum | Same sequence samples | 50.6571% / 50.0000% / 49.3150% | Not independent evidence | Not calibrated | See saved report |

Sequence LSTM precision/recall are 47.8503%/55.9521%; XGBoost precision/recall
48.5815%/64.7939%. Ridge five-session price-return errors are MAE 0.0352835 and
RMSE 0.0497071, in fractional-return units. They are not currency-target errors.
Paired 20-date moving-block 500-draw 95% balanced-accuracy improvement intervals
versus reversal include zero: LSTM [−0.022673, +0.029785], XGBoost
[−0.003825, +0.031743]. These are exploratory multiple comparisons with known
development periods and current-cohort/vintage limitations.

The V2 selected companion's registered 20-date/1,000-draw Bonferroni intervals
also include zero: improvement against majority [−0.009336, +0.012414] and
against reversal [−0.033308, +0.010308]. V1 logistic's preserved separate final
evaluation was 48.0617% balanced accuracy versus majority 50.0000% and momentum
50.6259%, over 6,840 daytime-chain targets; that different target must not be
pooled with V2 holding-price outcomes.

For completeness, stored original frozen 2026 final metrics are:

| Horizon | Selected family | Saved rows | Accuracy | Balanced accuracy | Brier | Naive Brier |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Histogram boosting | 363,765 | 58.6838% | 50.0046% | 0.240702 | 0.242865 |
| 5 | Histogram boosting | 349,367 | 57.6234% | 50.6469% | 0.242588 | 0.244244 |
| 10 | XGBoost | 331,528 | 57.0775% | 50.9406% | 0.243334 | 0.245640 |
| 20 | Histogram boosting | 298,663 | 55.8211% | 52.3805% | 0.244651 | 0.248837 |

Those four candidates remain `REAL_RESEARCH_INSUFFICIENT_EVIDENCE`.
For example, one-session recall is only 0.0339%; its approximately 58.68%
accuracy largely reflects class imbalance, with naive accuracy also about
58.68%. Genuine raw-target ranking information does not establish investable
returns. The 474 unresolved economic backtests, historical publication/vintage
uncertainty, absent independent benchmark and unaccepted models remain material.

The shortest scientific next step is to retain genuinely future, frozen,
source-qualified decisions and collect their authorized outcome evidence under
the unchanged registered protocol. Future acceptance needs the prescribed
sample size, temporal coverage, baseline/date-block/economic evidence and an
external independent reviewer. More saved scores, throughput or fixture passes
cannot substitute for that evidence.

Sources: `docs/ml/real-model-comparison.json`,
`docs/development/ml-v2-observed-evidence.json`, the read-only private
`sequence-benchmark-v1/report-final.json`,
`docs/development/alphalens-investment-evidence-completion-report.md`,
`workers/experimental_nse_v2/forward.py` and `acceptance.py`. Software
regression and preservation results are centralized in
`14-end-to-end-verification.md`.
