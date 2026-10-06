# P7 label-generation development verification

Date: 2026-10-06. Branch: p6-p7-features-labels.
Approved P5: 649340aeae012683718b882a0f31754ad2d8ed36.
P6 gate/commit: ac6973f3b9a85dfff1e6094e348065ab177b4535,
234 passed / one production-provider skip, all static/security/PostgreSQL gates PASS.
Clean tree and committed P6 verified before any P7 files were created.

P7 DEVELOPMENT PASSED. P6 AND P7 DEVELOPMENT PASSED. Stop before P8;
readiness is for user approval of development, not automatic implementation or
production data approval. No model training, accuracy, evaluation/backtest,
signal/ranking/portfolio/frontend or production infrastructure was implemented.

## Architecture and contracts

Separate local alphalens-labels package; p7.labels.v1 definition/plan/row/dataset
contracts, canonical future-outcome builder, deterministic storage/manifests,
descriptive distributions and developer CLI. p7.alignment.v1 declares separate
feature/target/metadata columns and training eligibility without fitting models.
P2-P5 data/domain code, database migrations and P6 implementation/tests are unchanged.
No external runtime dependency added; local package uses existing data/features.

Feature snapshots replay through P5 at their original cutoffs before outcome reads;
tampered features, incompatible source IDs/classifications and unknown columns fail.
Entry t+1 open -> t+h close for 1/5/10/20 verified future sessions, never t-close
execution. P5 lacks open-time evidence, so v1 conservatively requires cutoff before
the entry local date begins; late decisions receive NULL plus timing reason.
Raw Decimal return=(exit-entry)/entry, 38 significant digits / ROUND_HALF_EVEN;
exact rational/source-price evidence survives. Lossless text Parquet avoids silent
fixed-scale quantization. Positive direction=1, nonpositive=0; no success thresholds,
fees/slippage, adjustments or terminal-value guesses.

MATURE / NOT_YET_MATURE / UNAVAILABLE / TERMINAL_EVENT preserve every row and reason.
Availability is the latest consumed future-session/bar/quality/identity/membership/
action availability; later corrections advance it. Complete session evidence is
required; bad/missing intermediate and endpoint observations cannot be skipped.
Known unadjusted economic actions degrade raw outcomes and block training eligibility.
Unknown action coverage remains disclosed. Contracts: [P7 specification](../ml/p7-label-generation.md).

## Executed gates

| Check | Actual result |
| --- | --- |
| uv lock --check | PASS; 68 workspace packages, only local labels added; external dependency versions unchanged. |
| uv sync --frozen | PASS; CLI installed. |
| pytest -W error -ra --tb=short with real PostgreSQL | PASS: 259 passed, 1 production/live-provider gate skipped; 672.52 seconds; no warnings. Includes 34 P6 and 25 P7 cases. |
| Real PostgreSQL regression | PASS: PostgreSQL 17, P2/P5 persistence/migrations/constraints/revisions/lineage/PIT/replay, repeated P5 canonical CLI same JSON/Parquet identity, complete container/network/volume teardown; runner exit 0. |
| Ruff check / format --check | PASS; final review 134 files formatted. |
| Strict mypy | PASS; 82 source files. |
| Bandit API/data/features/labels | PASS; 6,499 lines, zero findings, skipped files or suppressions. |
| git diff --check | PASS. |
| DOCX / main | Unchanged; hashes below. |
| Secrets/data/dependencies | New code/docs/constructed tests and descriptive TEST_ONLY evidence only; no credentials, raw third-party data, paid service or external dependency added. |

Focused initial run: 19 passed, one expected-exception-regex mismatch; corrected
without changing the guard. Test type narrowing corrected for strict mypy.
Final full run includes added endpoint/quality-receipt/lineage tests and passes.
No skip was used to bypass a blocked development check. The only skip remains
production/live provider clearance, not passed by fixture software tests.

## Golden and leakage evidence

Four hand-verifiable horizons assert entry session, target session, exact prices,
independent rational numerator/denominator and expected directions/returns.
The 1-session case deliberately has next open=102, exit=101, prior close=100:
correct target is negative; a t-close assumption would falsely be positive.
Zero direction, Decimal context independence, end-of-scope maturity and availability
after target close are tested. Explicit NON_TRADING evidence shifts a 5-session
target; unknown calendar evidence blocks it.

All ten requested separation protections pass: future target price mutation changes
the target while earlier feature values and pinned bytes remain unchanged;
all feature bar keys have session <= t and availability <= cutoff; target bar keys
are future only; horizon20 unavailable before completion; later revisions hidden
from historical features and training targets until their availability; future
listing/departure knowledge stays outside earlier features; maturity respected in
eligibility; decision/session-only chronological split possible; target names cannot
be requested as feature columns; TEST_ONLY cannot become PRODUCTION.

Additional cases: terminal departures retained without zero return; rejected entry,
intermediate and exit prices; completely missing exit; strict versus allowed
degraded quality; delayed quality receipt moves label_available_at; known unadjusted
action blocks eligibility; late decision cannot claim next open; malformed plans;
float source/target rejection; tampered IDs/source/classification; no row dropping;
deterministic label/alignment JSON/Parquet/metadata and CLI replay.

## Descriptive TEST_ONLY report

Preserved [target-distribution.TEST_ONLY.json](p7-target-distribution.TEST_ONLY.json)
from the final successful CLI test: 26 artificial sessions; feature indices 0/20/25;
48 paired target rows, 24 MATURE and 24 NOT_YET_MATURE. Per-horizon mature counts
1/5/10/20 = 8/8/4/4 (12 rows per horizon). It includes mean, median, sample standard
deviation, positive and missing proportions, version and input/feature/label IDs.
These are constructed outcomes, not historical NSE returns, investment performance,
predictive accuracy or evidence for label optimization. No third-party raw data
is copied. Artifact receipt IDs belong to this capture; fresh captures get new IDs.

## Limits and persistent gates

Real historical exchange calendars, PIT NSE/index universe, production rights,
complete corporate-action coverage and PIT fundamentals remain unavailable.
UNADJUSTED outcomes are raw price targets, not total/net investment returns.
Conservative decision-before-entry-date bound excludes cases that would need actual
opening-clock evidence. Long-history 100/200-session features remain NULL in the
short fixture; all-feature alignment may therefore have no eligible rows. Selected
usable raw feature columns and degraded policy must be explicit and versioned.
No production-scale timing or model-performance claim. No migration required.

P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED;
FUNDAMENTAL_PIT_DATA = UNAVAILABLE. Original DOCX SHA256:
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a.
Main remains 9fa82284936f8b7a34f5409ba25cdce3538747b6, no merge.
Historical P1-P6 reports preserved. P8 requires separate user approval.
