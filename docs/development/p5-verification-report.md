# P5 canonical development verification

Date: 2026-10-06. Branch: `p5-canonical-data-model`.
Approved baseline: `59da9a82d5c0f6f5a39fd36b4f645cc10035261b` (P4).
Baseline checks ran before changes: git status clean; current branch
`p3-p4-validation-universe`; P4/P3 commits present; both DEVELOPMENT PASSED;
P1_PRODUCTION_DATA_CLEARANCE OPEN; P5 had not started. Inspected AGENTS, DECISIONS,
README, P2/P3/P4 data contracts/reports, product/roadmap/boundaries, db/ migrations
and the existing data package. Created the P5 branch directly from approved P4.

P5 DEVELOPMENT PASSED. P6 remains unauthorized and requires user approval.

## Scope and acceptance evidence

`alphalens_data.canonical` supplies versioned registry/session/price/action/
fundamental/revision contracts, explicit availability reads, evidence assembly,
PIT services, storage interfaces, PostgreSQL repositories and deterministic Parquet.
Existing P2/P3/P4 implementations remain unchanged. P4 facts are wrapped exactly;
their resolver owns effective intervals, classifications, listings, departures,
aliases and symbols. P3 report hashes and row/session gates remain authoritative.
Invalid prices survive as values-null evidence with original quarantine lineage.

Migration 002 belongs solely to db/ and supplies immutable normalized canonical
storage, revision/domain/lineage constraints and justified query indexes. No
fundamental facts or tables are populated. Fundamental reads remain UNAVAILABLE
and writes rejected. No adjustment engine or manufactured real actions/calendar.
Details: [P5 model and relationships](../data/p5-canonical-data-model.md).

TEST_ONLY fixture: eight securities, five historical observation dates, 78 canonical
revision/evidence records, a known Jan 15 correction to Jan 10 observations, and
36 selected EOD observations at Jan 20 cutoff (including one values-null rejected
session). Price family is DEGRADED; fundamentals UNAVAILABLE. Counts describe
constructed software evidence, not real NSE coverage or investment performance.

## Verification results

| Gate | Result |
| --- | --- |
| uv lock --check | PASS; existing 66-package lock valid; no dependency change. |
| uv sync --frozen | PASS; editable data package rebuilt for CLI registration. |
| pytest -W error -ra --tb=short with real PostgreSQL | PASS: 200 passed, 1 production/live gate skipped, no warnings, 84.50 seconds. Includes 30 P5 unit cases and 1 P5 PostgreSQL integration case. |
| Real PostgreSQL | PASS on PostgreSQL 17, including final reordered replay/manifest checks, repeated canonical CLI persistence and complete teardown. |
| Ruff lint | PASS, all checks. |
| Ruff format --check | PASS, 113 files. |
| mypy | PASS, 67 source files. |
| Bandit apps/api/src + ml/data/src | PASS, 4,843 lines, zero findings/skips/suppressions. |
| git diff --check | PASS, including final staged whitespace review before commit. |
| Original DOCX | SHA256 unchanged: 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a. |
| main | Unchanged at 9fa82284936f8b7a34f5409ba25cdce3538747b6. No merge. |
| Paid dependencies/secrets | No new runtime dependencies or paid service; generated disposable credentials stay in process environments, never committed/logged. Staged changes reviewed before commit. |

## Critical correctness tests

Anti-lookahead tests cover all ten requested protections: future availability is
invisible; later revisions are invisible earlier; future symbols and listings do
not apply backward; delisted securities retain history; bad prices do not erase
existence; fundamentals stay unavailable; fixtures cannot become production;
current metadata cannot rewrite a pinned snapshot; identical rebuilds retain IDs.
P4's CURRENT_SNAPSHOT_ONLY guard remains active. Timely and late identity changes
are queried at both effective date and knowledge cutoff. Historical/live receipt
gating and unknown availability are tested independently.

Financial checks cover OHLC/positive/finite/exact precision, strict int64 volume,
float rejection, evidenced completed-bar close, and explicit adjustment evidence.
Quality integration rejects an unrelated corrected-source P3 report attached to
an older bar. Local reads replay P2 normalization and quarantine, reference
normalization, raw checksums and immutable capture manifests. Deterministic input
ordering, JSON/ID/Parquet byte equality, idempotent/new/conflicting revisions,
invalid/branching chains, freshness policy and separate availability/quality are tested.

Real PostgreSQL integration uses a separately created disposable test database:
migration creation/replay, all typed projections, indexes, same/new revision replay,
reordered equivalent input replay, parent-chain failures, direct SQL OHLC/volume/
nonfinite failures, forbidden production classification, lineage foreign keys,
source/checksum lineage failures, mutation rejection, cutoff selection, stable
snapshots and persistence in a new connection. The test database is dropped in
finally. The dedicated runner also repeats the P5 PostgreSQL CLI build; identical
dataset IDs and immutable JSON/Parquet publication prove replay. Container/network/
volume teardown is in finally and does not touch the regular local database.

Initial verification found error-expectation/refactoring mistakes in tests and a
fresh-connection test reading connection information after closure; corrected.
Lint/type findings were corrected without suppressions. Contract review added
canonical ordering before PostgreSQL input persistence, exact captured-manifest
comparison, and price-to-report record lineage checks; their final regression run
passed on the final run. No test was weakened or warning ignored.

Final CLI replay example, over one immutable TEST_ONLY capture:
input ID `820a47f28bd8a71ee460aab164a298092376b8368c0ba8cce6aa433a258d0614`;
both builds produced dataset ID
`77d918dfb604831624614ee9f8bdf0d8d5845811119b9018a91812c55ff18535`.
The runner exited 0 after removing its container/network/volume. Fresh captures
have their own receipt evidence and therefore legitimately different input IDs.

## Limitations and stop boundary

P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
FUNDAMENTAL_PIT_DATA = UNAVAILABLE. Real NSE calendars, verified historical universe/
index membership, real PIT actions/adjustments and production rights remain
unresolved. No dataset is silently upgraded. The bounded developer loader supports
FixtureCSV/reference replay; new adapters require documented source evidence.
Reproducibility pins actual captures including receipt metadata; separate fresh
captures do not falsely share byte-identical receipt evidence. No production-scale
benchmark, coverage, performance or vulnerability-audit claim is made.

P5 supplies development prerequisites for user review before P6. No features,
labels, ML, walk-forward evaluation, backtesting, signals, ranking, portfolio,
frontend or model registry work is authorized or implemented in this change.
Historical P1/P2/P3/P4 reports and the DOCX are preserved.
