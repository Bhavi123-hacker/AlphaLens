# P6 feature-engineering development verification

Date: 2026-10-06. Branch: p6-p7-features-labels.
Approved P5 baseline: 649340aeae012683718b882a0f31754ad2d8ed36.
P6 DEVELOPMENT PASSED. P7 implementation has not started at this gate; P6 must
be committed first. Production clearance OPEN and use NOT_CLEARED.

## Baseline and implementation

Initial git status clean; branch p5-canonical-data-model; HEAD equals approved
P5; commit exists; P5 gate documented PASSED; P6/P7 directories had deferred
notes only. Inspected all requested contracts/reports and P2-P5 source interfaces.
Created combined branch directly from approved P5. Main remains
9fa82284936f8b7a34f5409ba25cdce3538747b6. DOCX checksum remains
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a.

Versioned FeatureDefinition/FeatureSet/decision/row/dataset contracts; P5 cutoff
reader pipeline; 41 raw derived features with optional benchmark (38 without);
P3 quality and P4 historical membership gates; explicit null reasons; declared
unadjusted/adjusted basis; known-action degradation; deterministic SHA256 identity,
JSON, typed Parquet, manifests and developer CLI. No fitted scaling, models,
fundamentals, production data, migration or online feature store.
Exact formulas and limits: [P6 contract](../ml/p6-feature-engineering.md).

## Executed gates

| Check | Actual result |
| --- | --- |
| uv lock --check | PASS; 67 workspace packages, only local alphalens-features added; external dependencies unchanged. |
| uv sync --frozen | PASS; CLI installed. |
| pytest -W error -ra --tb=short on real PostgreSQL | PASS: 234 passed, 1 production/live-provider gate skipped; 312.89 seconds; no warnings. Includes 34 P6 tests. |
| PostgreSQL regression | PASS: real PostgreSQL 17; P2 and P5 integration, migration/projection/revision/lineage/persistence checks; repeated P5 CLI dataset ID unchanged; dedicated container/network/volume teardown complete. |
| Ruff check / format --check | PASS; 123 files formatted. |
| mypy | PASS; 75 source files, strict configuration. |
| Bandit API/data/features | PASS; 5,636 lines, no findings, skipped files or suppressions. |
| git diff --check | PASS. |
| Source DOCX / main | Unchanged, hashes above. |
| Dependencies and credentials | No external runtime dependency or paid service added; only code/docs/constructed fixture builder/tests committed; no raw third-party data or credentials. |

Focused and full failed runs are preserved in command-log.md: invalid fixture
slug; missing reference links; duplicate normalized evidence; long Windows paths;
sandbox cache access; one string-versus-enum fixture warning. All were corrected
without weakening P5 checks, suppressing warnings or changing P2-P5 domain code.
The first full run had 233 passed, 1 failed, 1 skipped. Final full rerun above passed.
The existing regression runner's test timeout increased to 1200 seconds because
the expanded suite exceeded 300; container management behavior is unchanged.
Fixture assembly now uses bounded declaration landings via existing P2/P5 APIs.

## Numerical and leakage evidence

Golden checks independently verify returns/log return, SMA/distance, seeded EMA,
MACD/signal/histogram, Wilder RSI including flat/zero-loss/zero-gain behavior and
smoothing, ATR including a gap, unannualized sample return volatility, volume
mean/ratio/z-score, drawdown/high relationship and zero-denominator nulls.
Arithmetic ramp and single-shock expectations are algebraically derived;
indicators are not validated by calling the implementation twice.

Integrated P5/P4/P3/P2 tests cover every requested leakage protection: changed
t+1 and later prices leave earlier values unchanged; late price revisions hidden;
future listing excluded from earlier rows/ranks; later symbol/current-membership
corrections hidden by cutoff; CURRENT_SNAPSHOT_ONLY rejected; trailing-only volume
normalization; late corporate-action evidence cannot rewrite earlier values or a
pinned artifact. New input evidence produces a new ID, even when earlier numerical
values are unchanged; full input hashes are metadata, never model features.

Additional checks: rejected day remains in its window; rolling windows recover
only after it leaves; DEGRADED propagation/strict policy; missing calendar and late
availability fail closed; unknown basis cannot be upgraded; PRODUCTION rejected;
departed securities retain historical rows; benchmark and deterministic midrank;
100/200-session indicators explicitly insufficient; deterministic JSON/Parquet;
manifest/schema metadata; successful CLI replay with identical output summaries.

## Limits

TEST_ONLY artificial 70-session calendar/securities/benchmark, not real NSE/index
history. Real research-fixture unknown calendar, availability or price basis still
cannot generate eligible numerical features. Corporate-action completeness is
NOT_ESTABLISHED; known unadjusted economic actions degrade windows, no repair.
Recursive indicators use finite trailing 50-session seeding, not all-history EMA.
Missing prelisting slots fail closed for longer windows; no shortened bad windows.
100/200-session features remain unavailable in the short fixture. No production
scale, predictive accuracy, performance, or legal production coverage claim.
FUNDAMENTAL_PIT_DATA = UNAVAILABLE. Stop before P8; P7 only after this gate/commit.
