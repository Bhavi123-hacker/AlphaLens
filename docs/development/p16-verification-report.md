# P16 development verification

Status: P16 DEVELOPMENT PASSED. STOP before P17.
P15 prerequisite passed and was committed as 2db5f157a00a682070cf2c1cf6cbb9f65d9827f3
before any P16 implementation. P13/P14 remain unchanged; main and original DOCX
retain their approved identities. Branch p15-p16-portfolio-paper.

Implemented offline immutable paper intents/events/fills/session reports, explicit
manual default and versioned fixed-horizon signal policy, whole-share sizing,
cash reservations, no shorts/pyramiding, P10 cost assumptions, P15 accounting/
valuation, fill-evidenced P13 position context, P14 explanation/marker lineage,
performance/chart contracts and atomic PostgreSQL event-stream persistence.
See [P16 contract](../portfolio/p16-paper-trading.md). No new external dependency,
paid service, broker client/credential, API/frontend or live pipeline.

Initial collection exposed an indentation error in the new module; corrected.
Initial focused run passed 22/23: the test expected an error when reprocessing a
previously processed earlier session, contrary to required idempotent locked
replay. Corrected the oracle to test an unprocessed retroactive session. All 23
then passed in 35.94s. Expanded 32 cases passed in 39.34s. Review identified that
entry risk limits must not block risk-triggered exit orders; corrected that policy
and added its regression. Final 34 unit cases passed in 49.61s, including actual
source-level symbol revision at simulated open with unchanged prior order intent.

One real PostgreSQL case persisted two simultaneous entry fills, unique intent/
event/fill/report records and P15 transactions, verified idempotent save, rejected
stale stream-prefix overwrite, database mutation guards and reconstruction from
persisted events. A focused helper initially passed the paper database case but
its following P2 ingestion smoke failed because that reduced harness did not
initialize the main P2 schema. Corrected the ignored harness to apply migrations;
database/ingestion/canonical replay/teardown then exited zero. Complete gate also
tests recovery through a separately reopened PostgreSQL connection.

Mandatory leakage/idempotency coverage includes no decision-close fill, evidenced
future entry/exit opens, locked old intents/model/policy references, invisible
future signals, repeated processing, no double fills/fees/orders/transactions,
cash reservation/overspend prevention, no pyramiding, missing/rejected next opens,
future cancellation cutoff guard, explicit TEST_ONLY identity/disclaimer and no
broker/network-client code path. Exit/HOLD/REVIEW/EXITED use actual simulated fill
context; no EXITED is manufactured from EXIT_SIGNAL. No performance tuning occurs.

Source gates passed: uv lock --check (97 resolved), uv sync --frozen (96 checked),
Ruff check/format (236 files), strict mypy (152 source files), Bandit over all nine
roots (15462 lines; zero findings/suppressions), git diff --check. The complete
Windows-safe PostgreSQL 17 suite is recorded in ignored data/p16-full-final.log:
495 passed, one production/live-provider skip in 1473.38s (24:33), including 34
P16 unit cases and one real PostgreSQL case. Explicit VERIFICATION_EXIT=0.
P2 ingestion smoke, twice-identical canonical replay, immutable paper event
recovery and owned container/network/volume teardown completed successfully.
The established short-root strategy used D:/al-tests. Source remained frozen
throughout this accepted run; subsequent changes only finalize documentation.
The sole skip is the unchanged production/live-provider clearance gate.

Standalone CLI replay: 20 forward fixture session calls, two intents, two fills
and one completely closed simulated cycle matched the domain API at every step.
Each session was processed twice without new orders/fees/transactions. Final
history/performance output and a second independent forward replay matched exact
checkpoint identity. Classified metadata p16-paper-results.TEST_ONLY.json records
only counts/IDs/disclaimers. The ignored driver first needed the repository root
on its import path; corrected before successful replay. Dependency audit found
no known vulnerabilities, explicit native exit 0.

Production clearance OPEN, market-data use NOT_CLEARED, fundamentals UNAVAILABLE.
TEST_ONLY PAPER SIMULATION — NOT REAL MARKET PERFORMANCE. TEST_ONLY — NOT A
PERFORMANCE CLAIM. Genuine NSE predictive calibration remains unavailable. Final
P16 commit and STOP precede any P17 API, frontend or live implementation.
