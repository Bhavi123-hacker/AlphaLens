# P8 baseline machine-learning development verification

Date: 2026-10-06. Branch: p8-baseline-ml.
Approved P7 baseline: 9c2bad98996585bd465d1fdd6fdc360159fcaafa.
P8 DEVELOPMENT PASSED. Ready for user review/approval to start P9; P9 not started.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.

## Baseline verification

First commands ran before changes: git status, git branch --show-current,
git log --oneline -8. Working tree clean on p6-p7-features-labels, HEAD approved
P7. P6 ac6973f3b9a85dfff1e6094e348065ab177b4535 and approved P7 both exist;
P6/P7 DEVELOPMENT documented PASSED. Training/evaluation/registry had deferred
notes only, no P8 implementation. Inspected AGENTS/DECISIONS/README, requested
P3-P7 contracts/reports, feature/label interfaces and phase directories.
Created p8-baseline-ml directly from P7. Source DOCX P8 calls for logistic,
regularized/tree/boosted baselines and honest naive comparisons; D51-D54 explicitly
amend authorization, holdout/data/fixture gates. No contradiction was identified.

Main remains 9fa82284936f8b7a34f5409ba25cdce3538747b6; no merge or main change.
Original DOCX remains SHA256
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a.

## P6 long-history prerequisite

The 50-session statement applies to recursive EMA/MACD/RSI/ATR seeds/trailing
windows. Engine/registry retain up to 201 canonical sessions for longer definitions.
Integrated 205-session constructed canonical test confirms SMA100 at 100 samples,
SMA200 at 200, correct trailing means after 201 observations, and distance SMA200.
Short history remains INSUFFICIENT_HISTORY. Focused audit: 2 passed / 33 deselected,
401.09 seconds before any P8 fitting. No P6 implementation defect; no numerical,
PIT, P2-P7 library or DB schema change. Added regression evidence only.

## Implemented architecture and scientific controls

P7-only immutable supervised envelope -> contract/hash/namespace checks -> one
session-date chronological holdout -> label cutoff and conservative availability
purge -> train-only constant removal/imputer/scaler -> fixed seeded estimator ->
validation metrics/naive comparisons -> checksummed local skops registry.
Detailed policies/formulas/limitations: [P8 specification](../ml/p8-baseline-machine-learning.md).

Classification models: LogisticRegression, RandomForestClassifier,
HistGradientBoostingClassifier. Regression: Ridge, RandomForestRegressor,
HistGradientBoostingRegressor. Six modest fixed configurations; no tuning search
or neural networks. Built-in histogram boosting requires no separate model library.
Complete resolved hyperparameters, transforms, seed (1729 default), one-thread
policy and environment are explicit in deterministic model identity/manifests.
Feature families/order are declared; input/feature/label IDs are pinned exactly.

Majority/positive-rate classification and zero/train-mean regression comparators
use purged TRAIN only. All relevant validation metrics and signed deltas survive,
including weak comparisons. Targets explicitly convert P7 exact Decimal to float64
at estimator boundary. P7 eligibility/reasons remain authoritative; missing
ineligible rows are not rescued by the defensive TRAIN-only median imputer.
Scaling applies only to Logistic/Ridge; trees omit it. Constant removal never
examines validation or target correlation. Historical cross-sections are unchanged.

Cutoff strictly precedes validation local date midnight. Training decision and
label_available_at must be <= cutoff; label availability in the validation period
is purged. P7 availability cannot precede target close; absent target end dates
in alignment therefore do not require fabricated date arithmetic. Delayed knowledge
is conservatively excluded. All securities at a session use the same temporal side.
Validation uses targets matured at its pinned P7 evaluation knowledge cutoff.

Classification metrics include distribution/count/positive rate, accuracy, balanced
accuracy, precision/recall/F1, ROC-AUC, PR average precision, log loss/Brier/confusion
counts. Single-class validation AUCs explicitly unavailable. Regression includes
MAE/RMSE/R2; constant/short R2 unavailable. Five calibration bins require 20 rows;
smaller scope states unavailable, no calibrator fit. Top-k UNAVAILABLE_P8_DISABLED.
Linear coefficients and forest impurity diagnostics are engineering-only/noncausal.

Artifacts: model.skops + manifest.json + evaluation.json, all SHA256-pinned in
versioned local registry metadata. Created_at is runtime audit metadata, excluded
from model-run identity. Serialization bytes are not promised identical; replay
verifies identical behavior/metrics in the pinned environment. Hashes detect
corruption, not registry authenticity. Trusted locally created artifacts only;
fixed reviewed type list, no dynamic trust/pickle loading or production promotion.
No model blob/migration in PostgreSQL. P9/P10 and all product decisions stay deferred.

Final CI integration review found the existing API Dockerfile omitted P6/P7
workspace manifests/sources, and the new P8 member must also be present for the
root frozen workspace sync. Added those explicit COPY entries and excluded ignored
data/ (fixtures/models) from .dockerignore build context. No API endpoints or library
behavior changed. Local Docker build verification is recorded below.

## TEST_ONLY model-run evidence

**TEST_ONLY — NOT A PERFORMANCE CLAIM.**
[Machine-readable 24-run report](p8-baseline-results.TEST_ONLY.json) includes full
per-run metrics/naive values/deltas, samples/periods/exclusions, classifications,
identities, calibration/confusion data, feature diagnostics, limitations and checksums.
Report SHA256: 59b6673a21783923065b985128a929498f7d775d1bb7de0035377c975f17d6e8.
Model files and captured raw/normalized fixtures remain in ignored local storage.
No third-party data redistribution or real/research market training result.

All 24 runs (six families x four horizons) fitted, repeated with identical captured
inputs/config and passed skops re-evaluation round trips. Feature subset was fixed
before evaluation: return_1/sma_5/volatility_5/volume_ratio_20. No fixture metrics
were used to change P6 indicators, targets, models, hyperparameters or feature set.

| Horizon | Training / validation rows | Calibration assessment |
| --- | --- | --- |
| 1 | 27 / 20 | Descriptive five-bin summary; TEST_ONLY |
| 5 | 24 / 19 | UNAVAILABLE_TOO_FEW_ROWS; Brier present |
| 10 | 21 / 19 | UNAVAILABLE_TOO_FEW_ROWS; Brier present |
| 20 | 12 / 19 | UNAVAILABLE_TOO_FEW_ROWS; Brier present |

Weak primary comparisons retained: horizon1 forest/histogram classification do
not beat training positive-rate Brier; horizon5/horizon20 Ridge MAE does not beat
train-mean target. All other apparent improvements remain constructed-fixture
differences only. Every report keeps evidence_status=INSUFFICIENT_EVIDENCE and
production_claims_permitted=false. No investment success or stock recommendation.

## Leakage, negative control and reproducibility

All mandatory protections are implemented/tested: chronology/no random shuffle;
validation excluded from preprocessing fit; validation targets cannot affect
preprocessing; targets and metadata cannot enter X; labels after cutoff excluded;
overlap purged; actual future revisions/listings/members invisible; later
observations cannot change earlier training matrices; stable feature order;
TEST_ONLY cannot become PRODUCTION; manifests pin exact upstream identities.
Integrated future-evidence test passes through actual P5/P6/P7 before P8 split.
Namespace laundering and serialized unreviewed types are additional rejection tests.

| Required protection | Test evidence in test_p8_training.py |
| --- | --- |
| 1. No random temporal shuffling | chronology_maturity_overlap_and_upstream_exclusions; no_random_shuffle_and_target_metadata_feature_injection (reversed rows rejected) |
| 2. Validation excluded from preprocessing fit | validation_features_targets_never_fit_preprocessing checks exact TRAIN means/scales |
| 3. Validation targets excluded from preprocessing | same test mutates validation targets and compares fitted statistics |
| 4. Targets cannot enter X | no_random_shuffle_and_target_metadata_feature_injection |
| 5. Metadata cannot enter X | same test rejects explicit metadata and a forged feature namespace |
| 6. Labels after training cutoff excluded | availability_cutoff_equality_and_future_label_exclusion |
| 7. Future target overlap purged | same test plus per-horizon chronology_maturity_overlap_and_upstream_exclusions |
| 8. Future revisions invisible | actual_future_revisions_listings_members_and_observations_cannot_change_training; existing P6 price-revision regression |
| 9. Future listings invisible | same integrated test excludes TEST:NEW before its effective date |
| 10. Future universe members invisible | same test introduces future-known/effective-earlier TEST:FUTURE and compares matrices |
| 11. Changed validation targets cannot change preprocessing | validation_features_targets_never_fit_preprocessing also compares classifier coefficients |
| 12. Future observations cannot change earlier training matrix | integrated test removes all later canonical observations; validation mutation test also checks earlier X/y |
| 13. Stable feature ordering | constant_removal_and_feature_order_train_only; artifact round-trip assertions |
| 14. TEST_ONLY cannot become PRODUCTION | identity_all_meaningful_changes_and_classification_protection; artifact_corruption_no_promotion_and_exact_dataset_evaluation |
| 15. Exact feature/label/data manifest pins | all_models_naive_comparisons_roundtrip_and_determinism for every family |

Seeded negative control shuffles only TEST_ONLY targets. It cannot assert meaningful
predictive evidence or promote regardless of apparent metric; no exact tiny-sample
chance-accuracy requirement. Six-model repeated fitting requires identical local
predictions, manifests and metrics; all four horizons have independent training
tests. Artifact corruption, ID/config changes, single-class/insufficient samples,
missing/infinite values, median math, constant removal and CLI paths are covered.

## Executed quality gates

| Check | Actual result |
| --- | --- |
| uv lock --check / sync --frozen | PASS; 78 resolved workspace packages / 77 installed checked. Genuine lock, free local dependencies only. |
| Focused P8 suite | 31 passed / 1 TEST_ONLY helper enum failure, corrected; integrated follow-up 1 passed / 31 deselected. Final full suite includes all 33 P8 cases passing. |
| pytest -W error -ra --tb=short with real PostgreSQL | PASS: 293 passed, 1 production/live-provider gate skipped; 1020.45 seconds; no warnings. Includes 35 P6, 25 P7 and 33 P8 cases. |
| PostgreSQL 17 regression / P5 CLI replay / teardown | PASS: real P2/P5 migrations/constraints/revisions/lineage/PIT persistence; ingestion replay; two canonical CLI builds with identical fb3dd22e7826cd11d68e491123b8f7009405bb372059f2179708ede9549666ed snapshot; dedicated container/network/volume removed; runner exit 0. |
| Ruff check / format --check | PASS; 145 files formatted. |
| Strict mypy | PASS; 90 checked source files. Scientific untyped packages have scoped import overrides, project/tests remain strict. |
| Bandit API/data/features/labels/training | PASS; 7,296 lines, zero findings, skips or suppressions. |
| pip-audit --skip-editable | PASS; no known vulnerabilities. Local editable workspace packages skipped as expected. |
| Existing CI API image build | PASS after workspace COPY integration fix; alphalens-foundation:p8-local, local only. Build context 961.38 kB excludes ignored data/model storage. No registry push or deployment. |
| git diff --check | PASS; final code/documentation whitespace review. |
| DOCX/main | Unchanged, hashes above. |
| Credentials/dependencies | Reviewed new local code/config/docs/constructed evidence only; targeted AWS/private-key scan has no matches. No credentials, paid provider/service or third-party raw data added. |

Initial focused P8 run: 19 passed, 12 failed. Eight persistence/CLI tests rejected
an unreviewed built-in numpy.dtype emitted by this installed scientific stack;
reviewed fixed type was added, no automatic trust. Three horizon20 split cases
included the insufficient-row failure (nine training rows after P7/P8 exclusions)
and per-horizon tests; one extra authored decision at artificial index30 supplies
twelve mature samples without weakening cutoff/eligibility. Another failure was
a TEST_ONLY production-enum assertion helper under warnings-as-errors, corrected.
A subsequent --basetemp run had 29 setup errors because its parent directory was
missing; created the ignored parent and reran. Final integrated helper used a
string in an enum model_copy, corrected to the enum; guards were never relaxed.

Sandbox denied Git branch metadata, pytest artifact reads, uv execution in one
batched invocation, Docker config/context and pip-audit cache/network access. Required commands were
rerun with explicit tool approval and passed. No TLS/security bypass. Only the
existing real PostgreSQL verification subprocess timeout increased 1200->2400
seconds to accommodate integrated long-history/ML tests; regression scope unchanged.
An optional post-teardown docker ps probe was sandbox-denied; successful runner
exit 0 and explicit complete removal logs provide the teardown evidence.

## Documentation and remaining gates

Updated AGENTS.md, DECISIONS.md (original specification versus D51-D54 amendments),
README, architecture, roadmap/acceptance, local setup, command log/current
verification, and phase directory notes. Preserved P1-P7 reports and original DOCX.

Real legally usable PIT NSE calendars/universe, departed coverage, adjustment/action
completeness, production rights and fundamentals remain unavailable/open. Small
constructed training/holdout cannot establish real predictive quality or stability.
Latest pinned label evidence with delayed revisions may conservatively remove rows;
P8 does not reconstruct different label vintages independently of P7.
No P9 walk-forward, P10 economics/backtest or production-scale claim. Repository
is ready for separate user approval of P9 after the P8 commit. P9 remains unstarted.
