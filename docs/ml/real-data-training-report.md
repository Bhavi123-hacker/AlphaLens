# Real-data training status after D69

Source use is authorized: REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY. Public
TejHQ originals were acquired at revision 14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98.
Source permission is no longer the blocking condition.

**NOT_RUN_HISTORICAL_EVIDENCE_GATE_BLOCKED**. The source has no historical
publication/availability/completion/vintage clocks; the observed calendar omits
known special sessions; dated asset-type evidence is incomplete. Unmodified
P4-P7 contracts cannot produce an eligible historical supervised matrix. No
historical clock, session, identity backfill, price or COMMON_EQUITY fact was
invented. A decoded EQ row is not automatically a common-equity training row.

P8 models trained: **0**. Planned classification families: Logistic Regression,
Random Forest, HistGradientBoosting, LightGBM, CatBoost, XGBoost. Planned regression:
Ridge and the same five tree families. Horizons: 1/5/10/20 sessions. Model IDs and
per-horizon sample counts are unavailable; there are no performance comparisons.
No research winner or production champion exists.

The [source identity](../data/dataset-identity.json) freezes revision, 35 raw
hashes, P2-P7 versions and feature definitions. It explicitly says the P7-aligned
training dataset is not ready; raw-source identity is not a supervised-matrix ID.
[Feature availability](feature-availability.json) retains each configured feature
with null unmeasured counts/percentages. SMA100/SMA200 were not computed and have
no measured availability percentage. Relative-strength/market-context benchmark
inputs and PIT fundamentals remain UNAVAILABLE.

[Locked pre-results plan](real-research-evaluation-plan.json): 2010-2014 early
history/warm-up; 2015-2021 development training; 2022-2024 sequential development
OOS; 2025 confirmation; 2026 final holdout through the source's latest session.
Observed first/last sessions are pinned by year, not weekday assumptions. P9 must
still supply exact knowledge/maturity/purge/embargo boundaries before execution.
No model performance was inspected, no configuration was selected, and the final
holdout was not evaluated. No scaling, imputation or tuning occurred.

P11-P14 weights/thresholds remain unchanged development assumptions. P17 unstarted.
Production clearance OPEN/use NOT_CLEARED. All result JSONs distinguish NOT_RUN
from zero empirical performance. Historical audit-only status is retained below.

---

# Real-data training status

Status: **NOT_RUN_SOURCE_GATE_BLOCKED**. No new real features, labels, aligned
supervised data, model artifacts or model IDs were generated. All sample counts,
SMA100/SMA200 percentages and year/feature availability remain UNAVAILABLE.

Requested arena, once the source/P2-P7 gates pass: classification LogisticRegression,
RandomForest, HistGradientBoosting, LightGBM, CatBoost and XGBoost; regression Ridge
and the same five tree families; independent 1/5/10/20-session labels. Use identical
eligible samples/features/time rules across families, existing versioned parameters
and fresh train-only preprocessing. P8/P9 software already supports the arena;
no source bypass or new training implementation is justified by an unapproved file.

The [feature availability status](feature-availability.json),
[label distribution status](label-distribution.json) and
[model comparison status](model-comparison.json) contain null observations/results,
not fixture metrics relabeled as real evidence. No model has a real research
candidate status, and none is a PRODUCTION_CHAMPION.

Before any final-period outcomes are inspected, pin source identities and exact
chronological split/fold boundaries after permitted date coverage is profiled.
Proposed boundary principle: earlier history for warm-up/training, development
walk-forward periods through 2024, 2025 candidate confirmation and an untouched
2026 final holdout when actual coverage permits. This is not an executed P9 fold
definition; no final-period targets/metrics have been inspected and no selection
or tuning has occurred. Missing clocks/universe evidence cannot be invented to
force training eligibility. Fundamentals remain UNAVAILABLE.

Production clearance remains OPEN/use NOT_CLEARED. Existing empirical outputs
remain TEST_ONLY — NOT A PERFORMANCE CLAIM. Any later approved real research
outputs must retain RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED classification.
