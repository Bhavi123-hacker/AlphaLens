# P8 reproducible baseline machine learning

Authority: explicit user amendments D51-D54, approved P7
`9c2bad98996585bd465d1fdd6fdc360159fcaafa`. Original DOCX unchanged.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
FUNDAMENTAL_PIT_DATA = UNAVAILABLE. Stop before P9.

**TEST_ONLY — NOT A PERFORMANCE CLAIM.** Constructed records verify software
mechanics. Their accuracy, confusion counts, return prediction errors and naive
comparisons do not establish actual stock prediction, investment success or
production model quality. RESEARCH_FIXTURE outputs, if separately exercised,
state **RESEARCH_FIXTURE — NOT PRODUCTION-VALIDATED**. This milestone uses only
constructed data; no research-market training result or new acquisition is claimed.

## P6 prerequisite audit

The documented 50-session bound is per-decision trailing history for recursive
EMA12/26, MACD/signal, RSI14 and ATR14 with explicit reseeding. It does not constrain
SMA or return/volatility history. P6 retains up to 201 verified session observations.
An integrated P5 canonical fixture of 205 artificial sessions proves SMA100 at
100 observations, SMA200 at 200 observations, and correct trailing windows after
the 201-observation bound. The 70-session fixture stays INSUFFICIENT_HISTORY.
No P6 formulas, PIT policy or financial values were changed to improve ML metrics.
Historical P6/P7 reports remain unchanged; new evidence is in test_p6_features.py.

## Tasks and fixed suite

`alphalens_training` consumes only P7 `p7.alignment.v1` SupervisedDataset. It
checks the complete dataset hash, supported column namespaces, chronological
unique session/security keys, row classification, target consistency and P7
eligibility. It never independently joins features and labels or recomputes
historical universe/cross-sectional features.

Classification predicts the P7 direction (strictly positive raw return -> 1,
nonpositive -> 0). Regression predicts P7 raw t+1-open to t+h-close return.
Separate configurations/dataset IDs/runs support only 1/5/10/20-session horizons.
P7 Decimal targets remain unchanged; float64 conversion is explicit at the
estimator matrix boundary and rejects nonfinite conversions.

| Task | Family | Material configuration |
| --- | --- | --- |
| Classification | LogisticRegression | L2, C=1, lbfgs, max_iter=1000, tol=1e-8, intercept, no class weights |
| Classification | RandomForestClassifier | 32 trees, depth 4, leaf minimum 3, bootstrap, all features, Gini |
| Classification | HistGradientBoostingClassifier | 32 iterations, learning rate 0.1, depth 3, 7 leaves, leaf minimum 5, L2=1 |
| Regression | Ridge | alpha=1, intercept, SVD solver, tol=1e-8 |
| Regression | RandomForestRegressor | Same bounded forest, squared-error criterion |
| Regression | HistGradientBoostingRegressor | Same bounded histogram settings, squared-error loss |

Built-in histogram boosting completes the requested modest suite without another
model library. Histogram early_stopping=false avoids its internal random holdout.
No hyperparameter searches, neural networks or validation-driven selection exist.
Every estimator's complete resolved get_params is serialized, including library
defaults; meaningful changes therefore change identity. The dependency lock pins
scikit-learn 1.7.2, skops 0.14.0 and scientific dependencies.

Naive classification comparators are hard majority class (tie -> 0) and constant
training positive-rate probability. Naive regression comparators are zero return
and training target mean. All statistics use the final purged training fold.
Each run reports both comparators, every applicable metric and signed model-minus-
naive deltas with LOWER/HIGHER improvement direction. Weak performance is retained.
Primary descriptive comparison uses Brier versus positive rate, or MAE versus
training mean. BASELINE_BEATS_NAIVE / BASELINE_DOES_NOT_BEAT_NAIVE is fixture-scoped;
evidence_status remains INSUFFICIENT_EVIDENCE irrespective of apparent superiority.

## Chronology, availability and conservative purge

TrainingConfig explicitly supplies training_cutoff, validation_start and
validation_end; validation dates are Asia/Kolkata local sessions. Training cutoff
must strictly precede validation_start local midnight. All rows for a session
date belong to the same side. Rows are never randomly reordered or split.

Training candidates: session_date < validation_start, decision_time <= cutoff,
P7 TRAINING_ELIGIBLE, label_available_at <= cutoff and label_available_at strictly
before validation local midnight. Availability equal to cutoff is admitted.
Unknown availability fails closed. Validation candidates: session dates inside
the inclusive interval, decisions later than training cutoff, P7 eligibility,
and targets visible at the P7 dataset's explicitly pinned training_as_of, which
serves as validation evaluation knowledge cutoff. Targets after that knowledge
time were already masked by P7 and cannot enter fitting or metrics.

P7 alignment exports label_available_at but not target-end dates. P7/P5 guarantee
availability cannot precede consumed target session close, and include latest
consumed price/session/quality/membership/action/revision knowledge. Therefore
availability >= validation local midnight implies a conservative overlap purge.
This also purges earlier target periods whose evidence/revisions arrive late.
Any actual horizon crossing into the first validation session cannot meet the
training cutoff. No guessed target dates, fixed calendar-day horizon shortcuts
or weakened knowledge semantics are introduced. Boundary rows receive
TARGET_OVERLAP_PURGED and/or LABEL_AFTER_TRAINING_CUTOFF. A gap is an embargo
through unavailable target knowledge, not a walk-forward fold implementation.

All original ineligible rows remain excluded with exact P7 reasons; additional
P8 exclusions are counted separately. excluded_rows counts unique rows; reason
counts can sum above that count because one row can have several reasons. Nothing
is silently reclassified or imputed back into eligibility. Minimum train/validation
rows are explicit configuration (defaults 10/4); insufficient data rejects the run.
Classifier fitting requires both training classes. Validation single-class data
is supported with explicitly unavailable AUCs.

## Preprocessing and feature selection

Predefined P6 features are selected upstream through P7 alignment. The constructed
P8 example uses return_1, sma_5, volatility_5, volume_ratio_20 in this explicit
order, before any validation inspection. Missing/rejected/unknown slots remain
upstream unavailable, never replaced by neutral values. Current P7 eligibility
requires all selected values present; a declared eligible NULL is a contract
contradiction and rejected. Infinite values are rejected even in excluded rows.

Only constant features are optionally removed by the fixed train-only policy.
All-unavailable features already prevent upstream row eligibility; removing them
to revive rows would require a separately aligned P7 feature contract. There is
no target correlation, validation selection or deterministic-duplicate search.
All-constant training input rejects fitting. Selected order remains P7 order.

Pipelines contain SimpleImputer(strategy=median, add_indicator=false) as a
train-only defensive transform; it never rescues P7-ineligible rows. Logistic/Ridge
then use StandardScaler(with_mean=true, with_std=true). Tree pipelines omit scaling.
Pipelines fit once on purged X_train/y_train; validation only calls predict/transform.
Tests directly verify median behavior and train-only scaler statistics, and that
changing validation features/targets cannot change fitted preprocessing or model.
No full-data statistics, cross-section re-ranking or target-informed imputation.

## Metrics and diagnostics

Classification: sample count, positive rate, class distribution, accuracy,
balanced accuracy (mean recall over observed classes), precision, recall, F1,
ROC-AUC, average precision as the documented PR-AUC summary, log loss, Brier,
and tn/fp/fn/tp. Undefined precision/recall/F1 use explicit zero_division=0.
Both classes are required for ROC-AUC/average precision; otherwise NULL with
UNAVAILABLE_SINGLE_CLASS. Log loss uses explicit labels=[0,1]. Accuracy is never
the only diagnostic. Classification/confusion counts retain fixture labels.

Regression: MAE, RMSE, R2 and sample count. Constant or fewer-than-two targets
yield NULL R2 with explicit reason; no invented score. Spearman is omitted.
No metric is interpreted as investment performance.

Brier always supplies a probability calibration diagnostic. At least 20 validation
rows enables a deterministic five-bin summary on [0,1], left-closed/right-open
except the final bin includes 1. Empty bins retain count 0 and NULL averages.
Smaller validation data states UNAVAILABLE_TOO_FEW_ROWS. There is no validation-
fitted calibrator. Bins are descriptive small-fixture evidence only.

Top-k diagnostics are deliberately UNAVAILABLE_P8_DISABLED. No K optimization,
stock ranking, portfolio return, strategy or trading signal is created.
Linear/logistic coefficients and forest impurity importance preserve feature order;
importance is explicitly NOT_CAUSAL. Histogram importance is unavailable. There
is no SHAP UI or full P14 explanation.

## Identity, artifacts and local registry

SHA256(stable canonical JSON identity) defines model_run_id. Identity pins complete
P7 dataset, P6 feature set and P7 label set IDs, original column namespaces/order,
task/horizon, code contract p8.baseline.v1/model version 1, split/cutoffs, seed,
preprocessing and complete estimator parameters, classification and library/runtime
environment. A changed meaningful input/configuration produces a new ID.
Input dataset IDs transitively pin upstream P5/P4 revisions and knowledge snapshots.
Fresh fixture captures contain new receipt identities, so differ from replay of
the same captured bytes. No runtime created_at enters deterministic model identity.

Seed default 1729 is explicit in resolved config. Forests use n_jobs=1; all fit
and evaluation calls bound scientific thread pools to one thread. Same captured
data/configuration/versions/seed reproduce equivalent fitted behavior and metrics
in the pinned local environment. Tests require exact prediction equivalence here;
cross-platform BLAS behavior and byte-identical serialization are not promised.

Local layout: registry/<model_run_id>.json plus artifacts/<model_run_id>/{model.skops,
manifest.json,evaluation.json}, under ignored data/ or .local-data/ only. Files
publish exclusively, never overwrite different bytes. Registry publishes last;
partial writes do not create an accepted run. A conflicting partial run fails
closed and must be inspected locally. Replay reuses the original complete artifact
only after identical manifest/report checks. Checksums cover all three files.

Registry includes family/task/horizon/status, exact input identities, train cutoff,
validation interval, metrics, relative artifact path, checksums, created_at and
code/model version. TEST_ONLY inputs can only have TEST_ONLY status. Accepted
research may have VALIDATED_BASELINE meaning software validation only, never
PRODUCTION. No promotion method, hosted platform or PostgreSQL migration exists.

Skops is used without pickle/joblib loading. Only private locally created artifacts
are trusted. Checksum verification precedes deserialization; checksums detect
corruption and do not authenticate an attacker-controlled registry. A fixed reviewed
type list covers numpy.dtype and built-in sklearn histogram structures, never an
artifact-requested whitelist or automatic trust of get_untrusted_types. Exact
library/runtime environment, manifest identity, namespace/order and serialized
behavior must match before re-evaluation succeeds. No untrusted artifact endpoint
exists. See the [sklearn persistence guidance](https://scikit-learn.org/stable/model_persistence.html)
and [skops trusted-type guidance](https://skops.readthedocs.io/en/stable/persistence.html).

The developer commands and full fixture preparation are in
[local setup](../development/local-setup.md). `alphalens-train baseline` prints the
classification/disclaimer, intervals/rows, metrics, naive deltas, artifact ID and
checksums. `alphalens-model evaluate` verifies/re-evaluates the same pinned holdout
without refitting. Inputs are immutable P7 JSON with equivalent Parquet available
upstream; model outputs are files, not database financial facts.

## Development evidence and boundaries

Tests cover all 15 requested adversarial protections, a seeded TEST_ONLY target
shuffle negative control, six-model seeded replay and skops round trips, all
horizons, metric mathematics, single-class/constant outcomes, missingness,
checksum corruption, manifest identity, namespace laundering and no promotion.
The negative control never asserts exact chance accuracy on a tiny sample and
cannot claim meaningful signal regardless of its metric.

P8 DEVELOPMENT acceptance proves structured reproducible software. Real legally
usable PIT market history, exchange calendar/universe coverage, adjustment/actions
and fundamentals remain separate unavailable/open gates. This fixture does not
establish survivorship control or historical NSE investment performance. P9 owns
full sequential walk-forward/stability and untouched evaluation; P10 owns execution
economics/backtesting. There is no portfolio equity, CAGR, Sharpe, drawdown, trade
P&L, trading recommendation, product inference/UI or paid dependency in P8.
Full executed gate evidence: [verification report](../development/p8-verification-report.md).
