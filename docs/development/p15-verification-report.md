# P15 development verification

Status: P15 DEVELOPMENT PASSED. Complete gate exited zero before the P15 commit.
Baseline was clean approved P14 5eaeb01, with P13 490de2e present and both passed
reports. Created p15-p16-portfolio-paper directly from P14. P15 was not previously
implemented. Main 9fa82284936f8b7a34f5409ba25cdce3538747b6 and original DOCX SHA256
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a are unchanged.

Implemented separate offline portfolio workspace: append-only provenance-preserving
ledger, exact FIFO fees/lot allocation, declared opening lots, no shorts/overdraft,
cutoff-aware canonical EOD valuation, current summaries, honest incomplete marks,
per-security/portfolio histories, P5 price views, optional P11-P14/prediction links,
benchmark alignment and immutable PostgreSQL metadata with account-row locking.
See [P15 contract](../portfolio/p15-portfolio-guardian.md) for all formulas/policies.
No external dependency was added; one local workspace package entered uv.lock.

Initial authored accounting tests exposed test-fixture mistakes: a P5 fixture with
unknown basis was correctly refused by valuation, and fixture helper signature
edits temporarily omitted the deposit day. Corrected tests use independently
authored raw-basis P6 history and separately assert unknown-basis rejection.
Intermediate 26 and 33 cases passed; final focused 36 P15 unit cases passed in
38.72s. These failures were not production-data failures or market observations.

Actual future-available canonical corrections, symbol revisions and economic
actions are replayed through P5. Earlier economic values are unchanged; new full
source input IDs remain different honest audit lineage. Future/unavailable
transactions do not change earlier snapshot identity. Splits/bonus/merger/delisting
evidence retains unresolved quantity/basis; missing marks block aggregate equity.
Classification mismatch blocks real user holdings from fixture/research marks.

Standalone CLI fixture replay twice matched exact valuation API JSON and identity,
including TEST_ONLY — NOT A REAL MARKET VALUATION. Durable PostgreSQL case checks
idempotent creates/appends, oversell/conflict rollback, database mutation triggers
and restart recovery. Initial complete run stopped at collection on a test helper
import from the unit directory. Moved helpers into scripts and restarted all tests.
A document encoding issue was corrected by restoring historical UTF-8 text from
approved git content before applying the new scope additions; prior reports intact.

20 authored session valuations and 19 post-entry owned-security observations
replayed twice through the standalone history CLI and matched exact API JSON.
The classified metadata report p15-portfolio-results.TEST_ONLY.json contains counts
and immutable snapshot references only, not fabricated market performance.

Current source gates passed: uv lock --check (97 resolved), uv sync --frozen
(96 checked), Ruff check/format (226 files), strict mypy (145 source files), Bandit
over nine package roots (14175 lines, zero findings/suppressions), dependency audit
--skip-editable (no known vulnerabilities), git diff --check. Credential/network
path review passed. Full Windows-safe short-root PostgreSQL 17 regression is being
recorded at ignored data/p15-full-final.log with explicit native exit capture.

Final coherent full suite: 460 passed and one production/live-provider skip (1128.68s);
PostgreSQL 17 integration, P2 ingestion CLI and P5 canonical replay twice passed.
Owned container/network/volume teardown completed; VERIFICATION_EXIT=0. All 37
P15 cases (36 unit plus one real PostgreSQL) passed. Source stayed unchanged during
the accepted full run; only verification/documentation evidence was completed.

Production clearance remains OPEN; production market-data use NOT_CLEARED.
Fundamentals UNAVAILABLE. TEST_ONLY — NOT A PERFORMANCE CLAIM. No NSE calibration,
real valuation, broker verification, optimization or performance result is claimed.
P16 implementation remains deferred until P15 passes and is committed separately.
