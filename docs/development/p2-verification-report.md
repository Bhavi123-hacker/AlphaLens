# P2 DEVELOPMENT verification - 2026-10-06

Branch: p2-raw-ingestion. Approved baseline: 3f8880c (P1 work reviewed and committed
with explicit user approval). No merge of main. DOCX unchanged.

P2_DEVELOPMENT_GATE = PASSED.
P1_PRODUCTION_DATA_CLEARANCE = OPEN.
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
P2 infrastructure development proceeds independently under D40-D42.
P3_READY_FOR_AUTHORIZATION = YES; P3_STARTED = NO.

## Executed quality gates

| Check | Actual result |
| --- | --- |
| uv lock --check | PASS: 66 resolved packages. |
| uv sync --frozen | PASS: 65 installed packages; free PyArrow 23.0.1 added; explicit data-package psycopg dependency reuses the existing locked driver. |
| pytest -W error -ra | PASS with real PostgreSQL: 96 passed, 1 skipped, zero warnings, 8.81 seconds. Full locked-environment suite; helper adds --tb=short for safe failure output. |
| PostgreSQL | PASS: real PostgreSQL 17 container; db-owned migration, immutable metadata, duplicate unique-row count, manifest/run retrieval, replay and durability across new connections tested. PostgreSQL connectivity test also passed. |
| Integration skip | Existing production/live-provider test skipped because clearance/adapter remain OPEN. This external gate was not passed with fixtures. |
| Existing research fixture tests | PASS against the actual ignored local CC BY P1 artifacts; no download, replacement or redistribution. |
| P2 tests | 32 new cases: 31 fixture unit cases and 1 real PostgreSQL integration case. Fixtures test implementation correctness, never performance. |
| Ruff check . | PASS. No rule suppression. |
| Ruff format --check . | PASS: 79 files formatted. |
| mypy | PASS: 43 source files. Narrow missing-import override for PyArrow's unavailable type stubs; existing strict checks remain enabled. |
| bandit -r apps/api/src ml/data/src | PASS: 1,659 lines scanned, zero findings, zero suppressions. |
| git diff --check | PASS; tracked/staged whitespace checked before commit. |
| Installed file CLI | PASS: fixture capture and automatic replay; second invocation duplicate, same manifest and canonical result. |
| PostgreSQL CLI | PASS: reconstructed landing reuses original PostgreSQL manifest, emits typed Parquet/JSON, verifies byte-identical replay. |
| Compose teardown | PASS: dedicated alphalens-p2-verification container/network/volume removed; no normal development database volume touched. |
| Source document | SHA256 remains 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a. |

## Implementation evidence

Raw artifacts have exclusive immutable publication, a read-only file attribute and
verified SHA256/size on every read. Identical capture reuses identity and first
manifest; changed bytes retain a separate revision with predecessor IDs. Tests
prove original bytes survive revision capture and conflicting writes fail.

Strict parsing/normalization validates actual calendar dates, required/optional
identifier representation, exact decimal bounds, all OHLC inequalities, integral
nonnegative int64 volume, malformed CSV/headers/UTF-8 and duplicate security/session
groups. A malformed duplicate cannot leave a supposedly valid sibling accepted.
Invalid data retains original row fields and explicit errors in quarantine; raw
artifact evidence survives undecodable artifact-level errors. All results retain
classification and production_claims_permitted=false.

Canonical IDs join persisted normalized IDs and versioned parser/normalizer/schema
lineage to raw artifact/hash/source. Tests independently recompute row/raw SHA256.
Replay checks normalized/canonical/quarantine bytes, report hashes/counts and typed
Parquet bytes. Deliberate raw and normalized-output corruption fail verification.
Source abstraction is verified using another acquisition format and parser version.

## Failures encountered and resolved

The initial baseline sandbox run could not access inherited Windows pytest
cache/temp permissions; rerunning with approved access passed. Docker's named pipe
also required approved access. The first uv path probe was incorrect; the existing
installation is .tools/bin/uv.exe. No baseline failure was hidden.

Initial P2 collection caught a Pydantic field named schema shadowing BaseModel;
renamed it schema_version and kept warnings-as-errors. Ruff found formatting and
long-line issues, all corrected. An initially unanchored data/ ignore rule also
ignored new ml/data source files; corrected to root-only /data/ before final gates.

The first real PostgreSQL full suite passed (89/1), but its subsequent CLI failed
because an independently captured identical artifact carried another acquisition
timestamp. Fixed by recovering the authoritative first manifest from the metadata
repository before publication, with conflict checks and a regression test. The
next suite/CLI passed (90/1); subsequent strict-identifier and malformed-duplicate
coverage produced the final 96/1 run. Earlier failed local smoke outputs remain
ignored evidence and are not promoted or overwritten.

## File inventory (33 files)

Created:

- ml/data/src/alphalens_data/ingestion/: __init__.py, acquisition.py, cli.py,
  contracts.py, normalizing.py, output.py, parsing.py, pipeline.py, repository.py,
  storage.py.
- db/migrations/001_p2_ingestion_metadata.sql; scripts/verify_p2_postgres.py.
- tests/fixtures/p2/TEST_ONLY.csv; tests/fixtures/p2/TEST_ONLY.spec.json;
  tests/unit/test_p2_ingestion.py; tests/integration/test_p2_postgres.py.
- docs/data/p2-raw-ingestion.md; docs/development/p2-verification-report.md.

Updated:

- .gitignore; AGENTS.md; DECISIONS.md; README.md; db/README.md.
- ml/data/pyproject.toml; pyproject.toml; uv.lock; tests/fixtures/README.md.
- docs/architecture/system-boundaries.md; docs/data/data-contract.md;
  docs/product/roadmap-and-acceptance.md.
- docs/development/local-setup.md; docs/development/command-log.md;
  docs/development/verification-report.md.

## Remaining limits

Production/live-data rights and access remain OPEN; fixture processing establishes
no production investment claims, PIT eligibility, historical universe or unbiased
performance. Only the fixture interchange adapter is implemented in P2; production
acquisition/vendor adapters are not implied by its neutral protocols.

Use a single shared landing root for revision capture. A stale process lock needs
operator inspection after a crash; cross-root distributed writers, retention,
backups/restores, broad retries and scheduling are deferred. Filesystem/PostgreSQL
are recoverable through idempotent retry, not a distributed atomic transaction.
Parquet replay is verified within the pinned environment; library-upgrade binary
equivalence and multi-version reprocessing are not claimed. Privileged filesystem
owners can bypass read-only permissions, but checksum mismatches fail closed.
Calendar/freshness/outlier/corporate-action policies and production identity
continuity remain later-phase work. No P3 implementation started.
