# P14 offline explainability

P13 passed and was committed separately as `490de2e` before this implementation.
D62-D64 are user-approved amendments to the unchanged DOCX, not new claims about
the original specification. TEST_ONLY — NOT A PERFORMANCE CLAIM. Thresholds and
P12 weights remain DEVELOPMENT_ASSUMPTION; no genuine NSE calibration exists.
Production clearance remains OPEN/use NOT_CLEARED. Stop before P15.

## Three layers and evidence boundary

`explain` first reproduces the supplied P13 signal from exact P12/P11 policy,
cutoff, risk, history and synthetic position evidence. Mismatched or incomplete
history rejects the explanation. P13's market/position boundary is retained.
No independent label join, training, model choice or future performance query
occurs. Optional P6 datasets must pass their full content identity and exact
decision-row/canonical snapshot/universe/classification checks. Complete source
dataset identity and cutoff snapshot identity remain distinct.

User summary supplies the current state's meaning, independent model horizon,
unmet entry requirements, confirmation, expected-return disclaimer and development
limitations. Ordered positive/negative factors trace to signal reason codes or
checked local attribution. Unknown codes remain recorded evidence flags rather
than invented narrative. Evidence details retain actual feature values, states,
all nine risk components with severity/metrics/reasons, source quality, model
uncertainty and P12 raw components/weighted contributions/individual penalties.
Technical lineage retains exact signal/rank/risk/model/prediction/evaluation,
feature/canonical/universe/revision identities, policy versions and cutoff.

Ranking explanation retains normalized probability/return/momentum, effective
weights after P12 missing-component normalization, raw/adjusted scores, each
penalty, prior rank and peer adjusted scores. Descending score and stable-ID
tie-break explain the ordinal rank; no global feature importance substitutes for
a local reason. P12's deliberate risk/uncertainty overlap and engineered weights
remain visible in the complete policy. Full risk decomposition prevents a HIGH
component from being hidden behind an average.

## Checked local model methods

Attribution is optional evidence, not invented when model/row data are absent.
An in-memory fitted pipeline must match the P9 model manifest SHA256, task,
horizon, training cutoff, feature order and decision-time prediction. Only fitted
training statistics are used. No reference set is fitted on later rows. Raw
missing values remain null; the estimator's training-median substitution is
separately disclosed as effective/transformed values. Attribution identity pins
the feature row, method, reference/statistics, contribution output and policy.

| Family | Local method | Units and limitations |
| --- | --- | --- |
| Logistic / Ridge | Coefficient × fitted train-standardized feature; intercept baseline | Logistic contributions sum in LOG_ODDS, then sigmoid reproduces positive-class probability. Ridge sums in RETURN. These are local linear contributions relative to scaler zero, not probability percentages. |
| LightGBM | Native `pred_contrib=True` | Training-tree SHAP with expected-value final column; binary classification sums in LOG_ODDS, regression in RETURN. |
| CatBoost | Native `ShapValues`, one thread | Local training-tree SHAP plus expected value; check against RawFormulaVal. Existing CatBoost adapter is unwrapped explicitly. |
| XGBoost | Native exact `pred_contribs`, strict shape, no approximation | SHAP sums to raw margin/return; check linked prediction and additivity. |
| Random Forest / HistGradientBoosting | ORDERED_TRAIN_MEDIAN_PATH fallback | Starting at fitted training medians, replace features in pinned P9 feature order; consecutive output differences telescope to the actual output. Classification uses PROBABILITY; regression RETURN. Order affects allocation of interactions. This is explicitly NOT SHAP, not causal intervention, and the median reference can be off-manifold. |

All twelve task/family combinations are tested with actual fitted TEST_ONLY
pipelines, reconstructed outputs and deterministic replay. Top positive/negative
features are ordered by absolute contribution within each prediction's own output
space, then name. Different units are never combined into an importance score.
Actual values (for example an authored RSI14=63.2) accompany contributions.
Global importance is explicitly unavailable/not used as local explanation.

SHAP compatibility was evaluated against [TreeExplainer documentation](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).
The existing boosted libraries already expose native local SHAP, so no additional
`shap`/Numba dependency or service is required. The two sklearn tree families use
the disclosed deterministic fallback, not a claim of verified SHAP support.
Native semantics: [LightGBM](https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html),
[CatBoost](https://catboost.ai/docs/en/concepts/shap-values),
[XGBoost](https://xgboost.readthedocs.io/en/stable/prediction.html).
Coefficient semantics: [sklearn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
Runtime support is tested against the repository's pinned versions, not inferred
from latest documentation alone. No SHAP package was installed or newly audited.

The bounded P9 artifact helper verifies the existing OOS schema/checksums/lineage,
requires the exact model blob checksum and retains P8's reviewed skops type
allowlist. It supports the four reviewed sklearn families only. Third-party
boosted serialized types are not automatically trusted; use trusted in-memory
pipelines for their native attribution. Predictions are projected without scoring
outcomes or future diagnostics. Checksums provide integrity, not authenticity.
The original model manifest is retained as canonical JSON text, preserving
XGBoost's NaN missing-value parameter without rewriting it to null. Financial
feature/contribution values themselves must be finite or explicitly unavailable.

## Honest language, missing inputs and transitions

Every sentence is a deterministic template over supplied structured evidence.
Prediction/contribution is association, not causation. No paid LLM/API, stochastic
text or unsupported investor/news/earnings/sector narrative exists.
Expected returns are fractional values in structured fields and percentages in
summary text: MODEL ESTIMATE — NOT GUARANTEED. Probability, categorical model
confidence, categorical signal evidence, opportunity score and risk remain
distinct. There is no promised target price, limit order, stop or loss probability.

Fundamental PIT analysis is explicitly unavailable. News/sentiment and live/
intraday data are unavailable; absent benchmark context and unestablished complete
corporate-action coverage are exposed. Missing local attribution/feature rows and
insufficient independent model-selection/calibration evidence remain explicit.
Model diagnostics are only those historically visible in P11/P12, prominently
classified; TEST_ONLY counts/metrics never become a real market track record.

Signal explanation retains current transition trigger, each entry/continuation
check, actual observations, full required policy and confirmation counts. It
explains why entry is incomplete and what conditions could permit it, without
promising transitions. Hysteresis retention is distinguished from fresh entry.
HOLD/review/exit require position evidence; EXITED requires an evidenced exit.
Review requests are synthetic contemporaneous context, not an inferred profit.
All invalidation conditions are copied from the verified signal, with thresholds.
Technical price invalidation remains unavailable. Each horizon is explained
independently; no preferred horizon is chosen.

## Immutable cards, annotations and developer CLI

ExplainabilitySnapshot exposes summary, factors, missing evidence, measured
features, local contributions, model evidence, ranking/risk decomposition,
transition/invalidation conditions, freshness and technical lineage. A versioned
ExplanationPolicy pins ordering/precision/tolerance/reference rules. SHA256
identity covers the complete explanation except its own ID. Same inputs/policy
produce identical text/order/identity. Future optional evidence is filtered before
identity calculation; changed source dataset lineage may change audit IDs without
changing earlier numerical evidence or text.

Immutable local JSON snapshot/manifests and checksum-verified annotation files
round-trip. `ChartAnnotation` contains session, canonical state, horizon, signal
ID, explanation ID and classification. It contains no invented chart price.
Future charts can overlay the record on separately evidenced prices. No chart,
API/frontend, portfolio or paper-trading product is implemented.

`alphalens-explain explain --signal SIGNAL_DIRECTORY --ranking RANK_DIRECTORY
--risk RISK_DIRECTORY --features FEATURES_JSON --history PRIOR_SIGNAL_DIRECTORY
--attribution LOCAL_ATTRIBUTION_JSON --output data/explanations` prints UTF-8
classified cards and annotations. Features/attribution/history are optional only
when the signal's evidence permits their absence. Missing required prior history
rejects replay. The CLI never loads arbitrary model binaries; optional local
attribution JSON passes schema/identity/PIT checks.

`python -m scripts.verify_p14_test_only` checks the approved signal/rank/risk/P6/P9
artifacts, produces local linear explanations of selected logistic/ridge models,
replays every structured explanation twice and checks immutable output. No
training or data download occurs. See the separate verification report.
