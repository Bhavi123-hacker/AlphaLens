# Forward evaluation and independent model acceptance, 24 October 2026

## Registered descriptive aggregate policy

Registered before the new aggregate implementation is run on saved forecasts.
This additive read-only policy does not change any original forecast, outcome,
selection, acceptance threshold, protocol or historical result.

Classification summaries use only unique, qualified matured decisions, fixed
threshold 0.5 and original saved continuous scores. Undefined precision, recall,
F1, balanced accuracy and ROC-AUC are null with explicit denominators. AUC gives
equal scores half credit. Brier and ten fixed-width score bins are descriptive
diagnostics of uncalibrated scores, never proof of calibrated probabilities.
Model/target groups stay separate. Baseline differences use identical complete
candidate/baseline pairs, not unmatched samples. No regression error is inferred
from a classifier score. No iid confidence interval is added: stocks share dates
and overlapping targets. Existing registered date-block independent acceptance
requirements remain unchanged.

Top-5/10/20 hit rates use original immutable global declarations and their
frozen selection keys only. Validate original protocol, forecast IDs, model,
source/feature hashes, original score and future-entry chronology. Require every
declared member to have a qualified matured outcome before calculating any
selection statistic. The denominator is the actual frozen selected count capped
by original cohort size. Never rerank surviving outcomes, average shard rankings,
create a retrospective global cohort or treat declarations as independent dates.
Report each original declaration independently, including missing denominators;
do not pool overlapping declarations into an accuracy estimate. Equal-cohort and
frozen baseline comparisons are descriptive price-component research, not an
external NSE index, executed return or economic acceptance.

## Read-only forward evidence

Forward result status: **BLOCKED_EXTERNAL_DATA**. Aggregate software status:
**VERIFIED_COMPLETE** for the tests and read-only evidence below. Neither status
asserts that the complete live outcome collection workflow has run successfully.

At **2026-10-24T12:02:31.568374+00:00**, the authenticated evaluation reader inspected
184 existing V2 SQLite ledgers with `mode=ro`, `PRAGMA query_only=ON` and stable
read transactions. All 184 database file SHA-256 hashes were unchanged before
and after the read. The new private receipt is
`.local-data/blocker-resolution-20261024/forward-evaluation-first.json`; it also
pins the initial registered-policy document before this evidence appendix.

| Evidence | Observed count |
| --- | ---: |
| Raw original and expanded V2 forecast records | 633 |
| Unique model/security/observation decisions | 602 |
| Overlapping original/expanded records | 31 |
| Stored outcome revisions | 0 |
| Qualified matured outcomes | 0 |
| Decisions awaiting qualified five-session outcomes | 602 |
| Original global declarations | 4 |
| Complete matured global declarations | 0 |

All 633 records use model
`05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`.
331 raw records observe 16 October with entry 19 October; 302 observe 19 October
with entry 21 October. Deduplication yields 300 and 302 decisions respectively.
The only retained consecutive session links are **16 to 19, 19 to 21, and 21 to
22 October**. The 19-to-21 link explicitly records 20 October as closed; counting
weekdays would falsely add a target session. No 22-to-later link is saved. The
latest retained market observations are 21 October. Neither group has five
qualified future session prices and complete official-calendar links. A passed
calendar date or a scheduler exit cannot substitute for this missing evidence.

The four original global declarations contain 302, 300, 300 and 156 members.
All remain incomplete. Their overlapping membership is not an independent
sample, and the second 300-member declaration is not a second decision date.
Top-5/10/20 hit rates, accuracy, balanced accuracy, precision, recall, F1,
ROC-AUC and Brier remain **null**, not zero. No outcome was created, revised or
backdated; no provider call, fit, forecast append or scheduler change occurred.
V1's separate ledger/target and 43 saved sequence scores are not pooled into
these V2 counts.

Outcome qualification continues to require original actual chronology, future
entry, five sorted consecutive official sessions, exact entry timing, completed
exit before retrieval, matching target version, verified input hashes, no known
action exclusions and exact rational price-return arithmetic. This is a
split/bonus-adjusted **price-component reference**, not dividend-inclusive
return, independently verified identity/action completeness or executed profit.
Missing exhaustive action and identity-continuity evidence still prevents
economic acceptance even if a future reference outcome becomes scoreable.

## Software changes and validation

`apps/api/src/alphalens_api/nse_evaluation.py` now supplies matured-only confusion
counts, explicit sample/exclusion denominators, precision, recall, F1, tied-score
ROC-AUC, Brier and ten fixed score bins. Undefined metrics stay null. The score
classification explicitly says uncalibrated. Matched baseline comparisons use
identical candidate/baseline rows and include the frozen low-risk baseline.
Different model/target groups cannot be pooled. No classifier regression metric
or iid uncertainty interval is manufactured.

The same read-only endpoint now reports original global-declaration Top-N hit
rates and equal-cohort hit rates. It verifies protocol and forecast/model/source/
feature/entry lineage and validates saved selections against their original
scores. It calculates no selection statistic until every original member has a
qualified outcome, including members outside Top5. Missing declarations are not
reconstructed. No overlapping declaration hit-rate pooling is performed.

The overlap-conflict check now includes frozen baseline scores and target
versions, preventing apparent duplicates with different target/baseline evidence
from contributing a result. Outcome checks bind the exact original forecast ID
and recheck its complete forecast chronology. If only an overlapping expanded
record has a qualified outcome, the unique decision remains evaluable once,
using that record's own ID and evidence rather than rebinding its outcome to a
different original record.

Candidate interpreter:
`.local-data/completion-runtime/venv/Scripts/python.exe`.
Test scratch root: `ALPHALENS_TEST_TEMP_ROOT=D:\al-tests\fa24`.

```powershell
python -m pytest tests/unit/test_nse_readonly_evaluation.py tests/unit/test_nse_forward_aggregate_metrics.py tests/unit/test_nse_market_forward_cohort.py tests/unit/test_experimental_nse_v2_forward.py tests/unit/test_nse_market_stock_history.py -q
python -m ruff check apps/api/src/alphalens_api/nse_evaluation.py tests/unit/test_nse_forward_aggregate_metrics.py
python -m ruff format --check apps/api/src/alphalens_api/nse_evaluation.py tests/unit/test_nse_forward_aggregate_metrics.py
python -m mypy apps/api/src/alphalens_api/nse_evaluation.py tests/unit/test_nse_forward_aggregate_metrics.py
```

Results after the additional outcome-binding guards: **73 passed in 8.51s**;
Ruff passed; both files formatted; mypy passed
for both files. Tests use explicit TEST_ONLY inputs. They cover empty/single-class
samples, undefined denominators, invalid scores/targets, tie AUC, matched
baseline denominators, capped Top-N counts, complete-cohort blocking, rejected
selection/source lineage changes, cutoff visibility and zero-write behavior.
These checks are not empirical evidence of model accuracy or live maturity.

The existing `ProspectiveEvaluation.tsx` view now displays precision, recall,
F1 and ROC-AUC alongside original metrics; matched baseline sample counts and
differences; original declaration maturity and capped Top-5/10/20 hit-rate
denominators; and explicit insufficient-forward-evidence/null states. Complete
selection requirements and uncalibrated diagnostics are visible. Baseline/score
bins and original declaration details remain inspectable in the exact evidence.
Its isolated candidate Vitest suite passed **3 tests in 52.71s**, including
zero-outcome null handling, incomplete-cohort blocking even with five selected
outcomes and complete TEST_ONLY metric/selection rendering. No numerical fixture
is described as actual market performance. Supported Node22.23.3 candidate
`tsc -b --pretty false` and ESLint over the two changed frontend files both exited
0. Only those two files were copied into the isolated candidate for these
checks; shared frontend dependencies and the running deployment were untouched.

## Independent model acceptance

All model acceptance verdicts below are **BLOCKED_MODEL_EVIDENCE**. This review
reads saved evaluations and registered protocols; it performs no estimator fit,
prediction regeneration, holdout selection/evaluation or acceptance-threshold
change. Historical OOS separation is distinct from genuinely future independent
confirmation. The AI author of this report cannot supply the required external
review.

| Model or candidate | Horizon/target | Verdict | Concrete reason |
| --- | --- | --- | --- |
| Frozen selected histogram booster `fef6c043...` | 1 session | BLOCKED_MODEL_EVIDENCE | Original once-read final-vintage research; production PIT, economic and independent gates absent |
| Frozen selected histogram booster `fc0ff27e...` | 5 sessions | BLOCKED_MODEL_EVIDENCE | Same original research limitations; no forward acceptance |
| Frozen selected XGBoost `204d3205...` | 10 sessions | BLOCKED_MODEL_EVIDENCE | Same original research limitations; no forward acceptance |
| Frozen selected histogram booster `00c58086...` | 20 sessions | BLOCKED_MODEL_EVIDENCE | Same original research limitations; no forward acceptance |
| Experimental V1 logistic | Five separate future daytime close/open ratios | BLOCKED_MODEL_EVIDENCE | Different target; final BA 48.0617% below both frozen baselines; no independent calibration/PIT/action completeness |
| V2 20-feature histogram booster `d539dae5...` | Next open to fifth subsequent close | BLOCKED_MODEL_EVIDENCE | Known historical development dates; no qualified future evidence or external acceptance |
| V2 20-feature logistic | Same V2 target | BLOCKED_MODEL_EVIDENCE | Historical candidate only; same protocol gates absent |
| V2 20-feature forest | Same V2 target | BLOCKED_MODEL_EVIDENCE | Historical candidate only; same protocol gates absent |
| V2 20-feature ridge | Same V2 return target | BLOCKED_MODEL_EVIDENCE | Historical regressor only; transformed ranking score is not a probability |
| V2 16-feature histogram booster `05f80156...` | Same V2 target | BLOCKED_MODEL_EVIDENCE | 602 decisions but zero qualified outcomes; historical BA 50.1085%, IC 0.001997; saved baseline-improvement intervals include zero |
| V2 16-feature logistic | Same V2 target | BLOCKED_MODEL_EVIDENCE | Historical candidate only; same protocol gates absent |
| V2 16-feature forest | Same V2 target | BLOCKED_MODEL_EVIDENCE | Historical candidate only; same protocol gates absent |
| V2 16-feature ridge | Same V2 return target | BLOCKED_MODEL_EVIDENCE | Historical regressor only; no calibrated probability or acceptance |
| Sequence LSTM | Same five-session price-component target | BLOCKED_MODEL_EVIDENCE | 27,820 saved historical rows, zero prospective forecasts/outcomes; known-period report; improvement interval includes zero |
| Sequence logistic | Same target/matched sequence samples | BLOCKED_MODEL_EVIDENCE | Known-period development candidate, no independent future study |
| Sequence forest | Same target/matched sequence samples | BLOCKED_MODEL_EVIDENCE | Same limitation |
| Sequence histogram booster | Same target/matched sequence samples | BLOCKED_MODEL_EVIDENCE | Same limitation |
| Sequence XGBoost | Same target/matched sequence samples | BLOCKED_MODEL_EVIDENCE | Known-period improvement interval includes zero; no independent future study |
| Sequence ridge | Same return target/matched sequence samples | BLOCKED_MODEL_EVIDENCE | Return-regression metrics only; probability diagnostics inapplicable; no independent future study |

The complete original `docs/ml/real-model-comparison.json` contains 48
task/family/horizon candidates. Each remains explicitly blocked, not only the four
selected models. The following rows each cover all four original horizons
**1, 5, 10 and 20 sessions**, with no exceptions:

| Original task | Candidate family | Verdict at every listed horizon |
| --- | --- | --- |
| Classification | CatBoost | BLOCKED_MODEL_EVIDENCE |
| Classification | Histogram gradient boosting | BLOCKED_MODEL_EVIDENCE |
| Classification | LightGBM | BLOCKED_MODEL_EVIDENCE |
| Classification | Logistic regression | BLOCKED_MODEL_EVIDENCE |
| Classification | Random forest | BLOCKED_MODEL_EVIDENCE |
| Classification | XGBoost | BLOCKED_MODEL_EVIDENCE |
| Return regression | CatBoost | BLOCKED_MODEL_EVIDENCE |
| Return regression | Histogram gradient boosting | BLOCKED_MODEL_EVIDENCE |
| Return regression | LightGBM | BLOCKED_MODEL_EVIDENCE |
| Return regression | Random forest | BLOCKED_MODEL_EVIDENCE |
| Return regression | Ridge | BLOCKED_MODEL_EVIDENCE |
| Return regression | XGBoost | BLOCKED_MODEL_EVIDENCE |

All 48 stored original verdicts agree that research evidence is insufficient.
The original logistic fits also exhausted their fixed iteration limit.
Original 2026 holdout results remain frozen. The original source has absent
historical availability/vintage/action evidence; original membership and
assumed availability cannot establish production PIT. The 474 economically
unresolved backtests prevent independent net-economic acceptance. No positive
historical headline overrules these missing facts.

V1 has shared-date chronological splits with five-slot purge/embargo and
train-only scaling; its target is not V2's holding-price target. V2 uses shared
annual date folds, twenty-slot purge/embargo, train-only transforms and
2023–2025 selection; known 2026 observations remain diagnostic. Sequence
training is 2022–2023, validation 2024 with twenty-date embargo, and known
2025–2026 development reporting with train-only scaling. These registered
software controls reduce algorithmic leakage; they do not reconstruct unknown
publication/revision clocks, eliminate current-cohort survivorship bias or
make later known-period studies independent. Scores and Brier/score-bin
diagnostics do not demonstrate calibration. The equal-cohort baseline is not
an external NSE index. Original transaction-cost scenarios remain assumptions.

V2 and sequence independent acceptance still require **126 future decision
dates, 1,000 qualified matured outcomes, 30 securities, two quarters**, a single
frozen model/protocol, simultaneous 95% twenty-date-block lower BA improvement
above 0.02 versus the registered baselines, mean date IC above 0.02, required
regime/calibration/economic evidence and actual externally pinned human review.
Current matured sample/date counts are zero. `acceptance.py` additionally keeps
the accepted publication adapter separate. Risk-adjusted display ordering is
an unvalidated registered engineering assumption and supplies no independent
investment acceptance. All ranking output remains experimental research.

Read saved evidence without modifying it:

| Saved evidence | SHA-256 |
| --- | --- |
| V1 evaluation | `83ee458f29f0bb90c136ca7fbbe45cdb2f6fd4cd37e5f17df4b3b59b9ae8407e` |
| V2 context evaluation | `78a2facc1509cea6007615dc235c36d3013adbd9dd479144b477291fefcd61cc` |
| V2 price-only evaluation | `e75701e6aa883fa0a90a4543b6e8b30a7aa62a38d216e819ecb526b839fab552` |
| Sequence final report | `632d002e6c9fd1eb12d4e1b5d8240d288feb4b2d88412af75ebefbdd53c07eb8` |

Registered sources: `experimental-nse-v1-predeclared-study.md`,
`ml-v2-registered-protocol.md`, `ml-v2-price-only-registered-protocol.md`,
`ml-sequence-v1-registered-protocol.md` and
`nse-expanded-forward-protocol-v1.md` under `docs/development`; original frozen
comparison in `docs/ml/real-model-comparison.json`. Full selected model IDs and
artifact checksums remain in `docs/completion/model-readiness-manifest.json`.

## Exact remaining actions

- **BLOCKED_EXTERNAL_DATA:** obtain permitted genuine subsequent prices, dated
  official session links and applicable source/action/identity evidence for all
  five target slots. Keep missing slots explicit. Existing idempotent append-only
  reconciliation can then write qualified reference outcomes; this audit has no
  qualified path to reconcile.
- **BLOCKED_MODEL_EVIDENCE:** accumulate the unchanged prospective sample and
  statistical/economic evidence; arrange external independent review of the exact
  frozen bundle. Do not rerun final-holdout selection or promote historical scores.
- **BLOCKED_APPROVAL:** new provider requests, live scheduler modification or
  expansion beyond the approved cohort require the exact separate user approval.
  Software test passes do not grant these permissions.
