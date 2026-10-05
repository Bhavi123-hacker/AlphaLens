# P4 DEVELOPMENT verification - 2026-10-06

P4_DEVELOPMENT_GATE = PASSED. P3_DEVELOPMENT_GATE = PASSED.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
P5_STARTED = NO. P5_READY_FOR_USER_APPROVAL = YES (development prerequisites only).

Branch: p3-p4-validation-universe. P2 baseline verified clean before edits:
d3eee20ed9318435639a83b8afea3fe7c8c002d1. P3 gate passed with 125 tests/one skip
and was committed as 304ab3ddc22619c3248da446c785dbf48b2f567b before P4 began.
Main remains 9fa82284936f8b7a34f5409ba25cdce3538747b6; no merge/push.
DOCX unchanged: SHA256
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a.

## Executed final gates

| Check | Actual result |
| --- | --- |
| uv lock --check | PASS: 66 packages, no dependency or lockfile change |
| uv sync --frozen | PASS: 65 packages checked; data CLI installed from local editable package |
| pytest -W error -ra | PASS with real PostgreSQL: 169 passed, 1 skipped, zero warnings; 170 collected |
| P3 cases | 31 passed (29 initial + 2 scoped-quarantine integration cases) |
| P4 cases | 42 passed, including all seven required anti-leakage cases and survivorship/series/identity/quality/replay guards |
| PostgreSQL | PASS via unchanged scripts/verify_p2_postgres.py: real PostgreSQL 17, connectivity, db-owned migration, immutable ingestion metadata, cross-connection retrieval/replay, PostgreSQL CLI and dedicated container/network/volume teardown |
| Existing real research artifacts | PASS: local ignored P1 research fixtures still verified; no reacquisition, modification or redistribution |
| Skip | Existing production/live-provider test: clearance and adapter OPEN; not passed using fixtures |
| Ruff check . | PASS, no suppressions |
| Ruff format --check . | PASS: 95 files formatted |
| mypy | PASS: 54 source files; strict checks including imported fixture orchestration |
| bandit -r apps/api/src ml/data/src | PASS: 3,158 lines scanned, zero findings, skips or suppressions |
| git diff --check | PASS |
| Installed universe CLI | PASS: two Jan 10 runs produced identical bytes/hash; Jan 20 CLI audit replayed four earlier snapshots and produced the identical audit |
| Fixture acquisition/replay | PASS: per-session P2 ingestion + replay, P3 reports, repeated fixture-builder run preserved identical input/report bytes; actual first-capture receipt is retained rather than invented |
| P3 v2 installed CLI | PASS: identical repeated report hash; v1 report remains unchanged alongside versioned v2 output |

No P3/P4 migrations were added: deterministic file storage suffices. Existing P2
PostgreSQL metadata is regression-tested; db/ remains sole migration owner. No
SQLite, paid dependencies, remote execution or new network acquisitions.

## Acceptance evidence

Temporal identity supports stable internal/source IDs, dated symbol/series/ISIN,
aliases, listing/departure/type facts and preserved revision chains. Half-open
intervals, availability/publication/receipt separation, aware decision timestamps,
indexed known-revision selection and exclusive-interval conflict checks pass.
UNKNOWN types/availability remain excluded. All non-common-equity categories are
ineligible, regardless of EQ series. CURRENT_SNAPSHOT_ONLY fails explicitly.

Tests prove future listing/symbol/classification/delisting knowledge cannot leak;
late availability is respected; current lists cannot become history; bad prices do
not erase membership; later corrections cannot silently replace earlier knowledge.
Historical mode permits later captured evidenced history; live mode requires receipt.
Snapshots pin versions, full input hash, known-evidence hash and quality evidence.
Reordering equivalent facts produces the same snapshot; replay is byte-identical;
changed input/output hashes and conflicting immutable writes fail.

P4 integration required a narrowly versioned P3 extension, p3.quality.v2:
explicit stable source-ID/date quarantine scope, indexed session issue lookup and
session-based valid counts. This locates G's invalid session while retaining A's
valid analytical data. Unknown/malformed scope remains globally blocked. P2 code
and financial rules are unchanged; P3 v1 report reading/history is preserved.

## TEST_ONLY audit and reproducibility

Machine-readable measured evidence:
[p4-survivorship-audit.json](p4-survivorship-audit.json). All results below describe
constructed TEST_ONLY snapshots, not actual NSE data or investment performance.

| Metric across Jan 1/5/10/12/20 | Result |
| --- | --- |
| Unique historically included common equities | 6: A/B/C/D/G/H |
| Membership entries (including initial set) / exits | 6 / 1 |
| Observed symbol changes | 2: D and H |
| Historically included but absent at end | TEST:C, retained in earlier snapshots |
| Unknown classifications | 5 security/snapshot exclusions: F |
| Unavailable membership evidence | 1 security/snapshot exclusion: B before its evidence became available |
| Data-quality analytical exclusions | 2: G's temporary missing price and invalid OHLC session, both preserving membership |
| Other exclusions | ETF E: 5; delisted C: 2 |

Jan 10 universe snapshot ID:
7c897b96b30bacbb4c24a946f36b0b15ac864f4297f384d9ecd3e000557bc200.
It contains six universe members, G excluded only from analysis, D_NEW and
H_OLD because H_NEW is not yet available. Jan 20 has five members and C excluded
as delisted; H_NEW is available. Both the audit and each snapshot replay byte-for-byte
against retained ignored data/p4-test-only-v2/universe-input.json.

Repeated P3 v2 report SHA256:
5a962f289b04447d5a59e15d32b6b36c54884d396fb0ecf9faac635004c7cab0.
v1 report SHA256 remains:
5e382ca9c547143084bd9e5604d81e94813eab4445990bef733613b568a05f1e.
Fresh P2 captures have new actual receipt evidence; they are new full inputs, not
byte-identical reproductions of a previous capture. Replay uses the pinned input.

## Failures resolved and boundaries

Initial P4 collection could not import the scripts namespace; added repository
root to pytest pythonpath so the tested orchestration is importable. A hash test
caught pre-model +00:00 versus canonical Z timestamp serialization; hashes now use
canonical model JSON. A test initially supplied an unchecked string instead of a
QualityStatus enum and triggered warnings-as-errors; corrected the fixture without
suppressions. Lint/format fixes and failed atomic documentation patches were
resolved. Early ignored smoke outputs remain separate evidence; nothing was
overwritten to hide a different result. Earlier P3 permission/encoding failures
remain documented in p3-verification-report.md.

No claim of verified real NSE historical membership, classification/identity/
departed coverage, survivorship control, calendar, corporate-action adjustment,
live freshness, NIFTY 500 history or fundamental PIT data. Production permissions
and live adapter remain OPEN; fundamentals remain UNAVAILABLE. One quality report
per session/source is supported; ambiguous alternative reports fail rather than
silently resolving revisions. Full P5 entities, sector/index history without real
evidence, features, labels, ML, backtesting, signals, frontend and AWS remain deferred.

P3 AND P4 DEVELOPMENT PASSED — READY FOR USER APPROVAL TO START P5.
