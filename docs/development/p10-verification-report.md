# P10 development verification

Date: 2026-10-06. Branch: p9-p10-evaluation-backtesting.
P10 DEVELOPMENT PASSED. P9 prerequisite commit:
4e29b49eea97bf1b439db2886aa4d2dc62ee5ec4, passed and committed before P10 edits.
Approved starting P8: 58159b7aa321ee3207d50d232b8ccca97a757176.
Commit P10 separately, then stop before P11.

See [P10 contract](../backtesting/p10-backtesting.md) and the separate
[real-data readiness report](real-data-readiness.md). All fixture metrics:
**TEST_ONLY — NOT A PERFORMANCE CLAIM**. No real stock-model winner, predictive
edge, profitable strategy or expected investment return is established.

## Architecture and accepted evidence

The new local backtesting workspace consumes only verified P9 FOLD_TEST output;
it never loads fitted models or generates predictions. Exact rational cash,
inventory, quantities, fees and P&L reconcile without monetary float rounding.
Fixed decision-time allocations, next verified session open entries, horizon
close exits and maximum concurrent positions prevent retroactive decisions and
over-allocation. TOP_K, TOP_PERCENTILE and PREDICTION_THRESHOLD use predefined
configuration; sizing is EQUAL_WEIGHT across available slots.

A separately pinned, availability-aware calendar supplements P5's absent opening
clock without redesigning P2–P8. Schedule knowledge must precede each decision.
Missing/rejected opens never fill or incur costs; no close substitution. Calendar
conflicts while held, known unadjusted economic actions and unknown planned-exit
recoveries retain unresolved holdings. No invented adjustment, zero terminal
value or later substitute exit. Whole-period economic metrics are withheld when
valuation is incomplete. Later drawdown stays unavailable after any unknown mark
gap even if current valuation recovers. Benchmarks require explicit evidence;
constructed names are TEST_ONLY_BENCHMARK, not NIFTY 50.

Three fixed, versioned cost/slippage assumptions are ZERO_COST_DIAGNOSTIC,
LOW_COST_ASSUMPTION and HIGHER_COST_STRESS. They are not verified broker or tax
schedules. Session equity/drawdown/positions/P&L and complete trade/selection
ledgers retain deterministic IDs, ordering, schemas and SHA256 checksums. Audit
chains pin P9 predictions/folds, P8 model identities, P7 labels/aligned datasets,
P6 features, P5 canonical vintages, P4 universe, P3 quality and P2 source artifacts.

The fixed matrix completed **192 runs, each replayed twice**: eight task/horizon
evaluations × (six learned families × three costs + two naive policies × three
costs). All 192 output sets passed current schema/identity/checksum verification.
Each comparison preserves P9 predictive/ranking context, economic diagnostics,
trade-origin-fold diagnostics and cost sensitivity. Cohort/random baselines do
not become validated market winners. Standalone UTF-8 CLI replay matched the
corresponding arena economics with its own null comparison-context identity.
Full arena saves require both pinned comparison reports. Machine-readable
[fixture evidence](p10-backtest-results.TEST_ONLY.json) preserves unresolved
outcomes and fixed comparisons, with no real winner asserted.

TEST_ONLY annualization/Sharpe/Sortino/Calmar remain INSUFFICIENT_EVIDENCE. For
non-TEST data the documented minimum is 252 observed sessions and 365 days with
positive complete equity; undefined ratios stay null. Closed-only trade statistics
are separately scoped. EOD exposure is not intraday time-weighted exposure; gross
return adds back costs for the same executed quantities, not a reinvested portfolio.

## Tests and final gates

All **337 distinct tests passed**, with **one production/live-provider gate skip**,
across the final full regression and a targeted short-path retry. This is not
claimed as a single all-passing 337-test invocation:

- The prior full PostgreSQL 17 runner passed 336 tests/one skip (1267.92 seconds),
  ingestion CLI, two canonical CLI replays and dedicated teardown, exit 0.
- After the final holding-calendar guard/test, the full current suite collected
  338 cases: 335 passed, two artifact failures and one skip (1134.06 seconds).
  All 26 P10 cases, actual future-knowledge replay, and real PostgreSQL integration
  tests passed in this run. The long D: temporary root exceeded Windows immutable
  hard-link path limits in the P7 CLI and P9 artifact test.
- Reran only those two failed cases under `pytest -W error -ra --tb=short`, with
  fresh short `D:/alpt10r` basetemp and the same disposable PostgreSQL runner:
  **two passed** (269.43 seconds). That targeted runner subsequently exited 1
  because its ingestion smoke expected schemas normally initialized by the
  now-unselected integration tests. Teardown still passed. A CLI-only continuation
  applied existing migrations to a fresh disposable PostgreSQL 17 instance:
  ingestion and two identical canonical replays passed, teardown passed, exit 0.
  No completed pytest case was rerun in this continuation. No domain source,
  eligibility, checksum or immutable-publication guard changed to obtain the pass.
  Passing cases were not repeated after the user's continuation instruction.

The 26 P10 cases cover both tasks/four horizons, exact capital/costs/quantities,
fixed policies, normalized capital, overlapping positions, unavailable open/exit,
future targets/predictions/prices, calendar availability/conflicts, known actions,
departed outcomes, OOS-only/classification protections, complete lineage,
immutable schemas/checksums, naive/random controls, undefined/annual arithmetic,
and large exact-rational serialization without disabling interpreter safety limits.
The existing future-knowledge test now proves unchanged prior P9 preprocessing
and P10 economics under later price revisions, listings, membership and action
evidence. Shared session fixtures avoid redundant P2–P7 capture construction.

| Gate | Final evidence |
| --- | --- |
| uv lock --check / uv sync --frozen | PASS: 95 resolved / 94 checked packages. |
| Ruff check / format | PASS: 175 files. |
| Strict mypy | PASS: 110 source files. |
| Bandit all seven package roots | PASS: 9640 lines, zero findings, no suppressions. |
| Dependency audit | No known vulnerabilities; local editable workspaces excluded by existing audit policy and covered by static/security checks. |
| Real PostgreSQL 17 | Full integration regression passed; ingestion and repeated canonical CLI replay plus dedicated teardown passed. |
| Artifact/CLI replay | 192 configurations replayed twice; current schemas/checksums and standalone UTF-8 CLI equality passed. |
| git diff --check / staged review | PASS; no credentials, raw third-party data or paid dependency introduced. Narrow secret-pattern check is not a comprehensive security certification. |
| Source DOCX / main | Unchanged SHA256 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a; main 9fa82284936f8b7a34f5409ba25cdce3538747b6. |
| Linux image/imports | Original full frozen P10 build passed; current package incremental image/reinstall and CPU imports under -W error passed. Cold final full rebuild hit local disk capacity; not claimed passed. Hosted CI/Trivy not run. |

## Failures, limitations and production boundary

Intermediate failures are not passing evidence. Focused tests exposed fixture
injection excluding a tradable fixture benchmark, a wrong departure date,
disallowed artifact output root and an unjustified zero-loss expectation.
Corrected tests to actual fixture contracts, kept storage restrictions, and
verified profit factor against observed closed P&L. The temporary-mark case moved
to an interval without a confounding fixture departure; terminal guards remained.

A cold image rebuild exhausted C: capacity and stopped Docker; the concurrent
regression encountered filesystem errors and was stopped, not claimed passed.
Archived only obsolete task outputs/temp runs reversibly to D:, restarted Docker
and explicitly removed dedicated failed test resources. Accepted P9/P10 inputs
remained in place. The later two Windows path failures were resolved solely with
a shorter fresh temporary root, as documented in local setup. No general pruning,
unrelated database removal or destructive data workaround was used.

Historical phase reports and database/domain contracts remain unchanged.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
No genuine production-quality historical NSE universe is demonstrated. Research
results remain separately NOT PRODUCTION VALIDATED. Calendar/action/terminal,
rights/benchmark/cost and sufficient sample evidence are required before actual
stock-selection conclusions; see the dedicated real-data report. No new market
dataset was acquired. Zero paid dependencies. No production promotion or P11
implementation. Software is ready for user review and separate P11 authorization.
