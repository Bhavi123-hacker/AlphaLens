# Forward maturity and model review, 25 October 2026

Starting reference: `491c93f7e34b65a5d44dc8978e8e62069948389d` on
`alphalens-master-completion`. This is a read-only software and saved-evidence
audit. It is not external independent model review, acceptance or promotion.

## Actual forward evidence

At **2026-10-25T07:08:41.153173+00:00**, the complete audit verified **945 original
and expanded V2 forecast records, 914 unique decisions and zero qualified matured
outcomes**. The 31 overlapping records are not additional independent decisions.
All 187 existing ledger file SHA-256 hashes were unchanged before and after the
read. No forecast, outcome, model, scheduler or provider state was written. The
read took **3.5244 seconds**, without rebuilding historical sources or inference.

The complete 914-decision audit is saved privately in:

`.local-data/operational-acceptance-20261025/forward-decisions-final-d742a0973df74a868b230c3292407c49.json`

| Unique decisions | Original observation | Proven future target dates | Exact maturity evidence | Current state |
| ---: | --- | --- | --- | --- |
| 300 | 16 October | 19, 21, 22, 23, 26 October | 26 October, 10:00 UTC / 15:30 IST | Target sessions not completed |
| 302 | 19 October | 21, 22, 23, 26 October | Unknown: fifth session not proven after 26 October | Calendar maturity unknown |
| 312 | 23 October | 26 October | Unknown: later target sessions not proven | Future entry not started |

Twenty October is explicitly closed in the original official evidence; it is not
a target session. No weekday approximation supplies 27 October or any other
missing date. Known schedule dates do not provide future prices. The first 300
decisions can only become candidates for reconciliation after the real fifth
session completes and qualified subsequent source observations arrive; their
scheduled maturity is not an eligible outcome or guaranteed collection time.

Every audited decision records original source/inference/forecast timestamps,
model/security/target identity, five-session horizon, frozen entry, proven date
prefix, exact maturity when known, the precise missing-calendar anchor,
per-session price-presence/completion evidence, action exclusions, current
identity versus historical continuity, and remaining qualification gaps.
Six target paths intersect a known action exclusion. Every decision currently
lacks at least one future target candle; this expected future absence is distinct
from failure to collect a past completed session.

Price-presence diagnostics use the checksum-verified saved market projection's
120-slot histories and small saved action references. Projected chart candles
do not carry full per-slot source-publication lineage. The audit explicitly
labels that limitation and never uses them to append a qualified outcome.
Current symbol/ISIN agreement does not prove historical identity continuity.
Observed action references remain non-exhaustive, even when no known target
hazard appears. The append-only outcome writer and read-side qualification keep
the existing raw-calendar, source, action, identity, price and chronology gates.

All forward metrics are **NOT_YET_MEASURABLE**. Accuracy, balanced accuracy,
precision, recall, F1, ROC-AUC, Brier, Top-5/10/20 hit rates and confidence
intervals remain null. A classifier score supplies no fabricated MAE/RMSE,
predicted price return or calibrated profit probability. Existing date-block
methods and independent acceptance criteria remain unchanged; correlated stocks,
shared dates and overlapping horizons do not become iid evidence.

## Implementation

`workers/nse_market/outcomes.py` adds efficient read-only diagnostic context and
per-decision maturity explanations. `nse_evaluation.read(..., row_limit=None)`
exports every unique decision for an audit. The existing API defaults to 100 rows
and now reports explicit truncation, complete maturity/gap counts and
`measurement_status=NOT_YET_MEASURABLE` when no outcome qualifies. Existing
classification arithmetic, result labels and original selections are preserved.
The dashboard shows original decision clocks, horizon, proven dates, unknown
maturity and remaining evidence alongside explicit unavailable metrics.

## Explicit model verdict registry

The registry is produced by
`workers.nse_market.model_review.registry(repository, private_root=...)`.
It pins original evaluation/report bytes, verifies existing sidecars, binds V2
and sequence evaluations to exact registered protocol hashes, records selected
artifact references and retains the native saved research verdict. It verifies
the complete candidate inventory rather than dropping missing candidates.

The complete per-candidate registry is saved privately in:

`.local-data/operational-acceptance-20261025/model-verdicts-final-d742a0973df74a868b230c3292407c49.json`

| User verdict | Candidate count |
| --- | ---: |
| ACCEPTED_FOR_PRIVATE_RESEARCH | 0 |
| EXPERIMENTAL_INSUFFICIENT_EVIDENCE | 63 |
| REJECTED | 0 |
| BLOCKED_DATA_QUALITY | 0 |

The last count means no saved evidence-integrity or protocol-hash mismatch was
found in this audit. It does not clear historical PIT, corporate-action,
membership, economic or current-input limitations. A missing or mismatched
registered evaluation is blocked, not silently accepted. No model receives an
acceptance verdict because its metrics look attractive or a local flag claims
acceptance. No registered final rejection criterion is invented retrospectively.

Every candidate has the following explicit verdict:

| Family / task | Candidate algorithms | Horizons | Verdict for every listed combination |
| --- | --- | --- | --- |
| Original classification | CatBoost, histogram gradient boosting, LightGBM, logistic, random forest, XGBoost | 1, 5, 10, 20 | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |
| Original return regression | CatBoost, histogram gradient boosting, LightGBM, random forest, ridge, XGBoost | 1, 5, 10, 20 | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |
| Experimental V1 daytime-chain classifier | Logistic | 5 separate daytime ratios | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |
| Experimental V2 20-feature contract | Histogram gradient boosting, logistic, random forest, ridge | 5 | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |
| Experimental V2 16-feature contract | Histogram gradient boosting, logistic, random forest, ridge | 5 | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |
| Matched sequence benchmark | LSTM, histogram gradient boosting, logistic, random forest, ridge, XGBoost | 5 | EXPERIMENTAL_INSUFFICIENT_EVIDENCE |

This enumerates 48 original candidates, one V1 candidate, eight V2 candidates
and six sequence candidates. Each registry row has an unambiguous candidate ID,
target/task/horizon or contract, native model ID where actually available, saved
evidence reference and SHA-256, acceptance-standard reference and concrete
limitations. A candidate specification spanning temporal fits is identified as
such; no estimator/model identity is invented for it.

Original frozen research requires the independent prospective registration in
`docs/ml/p33-prospective-acceptance-protocol.md`, including externally chosen
numeric power, success-margin, coverage and dependent-sample requirements.
Those original requirements are not replaced with a universal row threshold.
V1's different target remains exploratory and cannot substitute for V2 holding
returns or acquire a retrospectively invented acceptance rule.

V2 and sequence retain their predeclared **126 future decision dates, 1,000
qualified outcomes, 30 securities, two quarters**, frozen model/protocol,
simultaneous 95% twenty-date-block lower balanced-accuracy improvement above
0.02 versus registered baselines, mean date IC above 0.02 and the required
calibration, regime, benchmark, executable economic/cost/action evidence and
external pinned review. Current qualified sample and decision-date counts are
zero. The 474 economically unresolved original backtests remain unresolved.
The exact canonical V2 criteria/version object SHA-256 is
`729e45fc7015c79d0ae1937683d3354dacc11d7922ced4185e50235b15244bf6`;
the registry separately records every registered protocol document's SHA-256.
Historical development, once-read final-holdout and future prospective evidence
remain separate. This campaign ran zero fits, zero holdout reevaluations and
zero model promotions. Numerical inference remains experimental research.

## Validation and next evidence

Focused validation passed **44 backend tests in 10.52s**, Ruff and mypy for five
changed/new backend files, **four frontend tests in 56.99s**, candidate TypeScript
`tsc -b` and ESLint over the two changed frontend files. The isolated candidate
interpreter and supported Node22.23.3 were used; shared dependencies were not
replaced. The exact final release regression remains in the campaign's
consolidated results. Added TEST_ONLY cases cover complete and partial
calendar chains, unknown maturity without weekday guesses, future entry versus
missing prices, action/identity gaps, future-projection exclusion, all 63 model
verdicts, protocol mismatch, missing-candidate inventory and evidence corruption.
No fixture result is forward market performance.

The focused backend command was:

```powershell
$env:ALPHALENS_TEST_TEMP_ROOT = 'D:\al-tests\op25f'
.local-data/completion-runtime/venv/Scripts/python.exe -m pytest tests/unit/test_nse_decision_maturity_audit.py tests/unit/test_nse_model_verdict_registry.py tests/unit/test_nse_readonly_evaluation.py tests/unit/test_nse_forward_aggregate_metrics.py tests/unit/test_nse_forward_outcome_job.py -q --tb=short
```

Next steps are to retain genuinely authorized future calendar/source evidence,
allow existing guarded reconciliation only when full target paths qualify,
accumulate the unchanged prospective sample and obtain genuine independent
review. None requires rerunning frozen historical selection or manufacturing
an accuracy value. Expanded provider scope or scheduler changes remain separate
approval boundaries.
