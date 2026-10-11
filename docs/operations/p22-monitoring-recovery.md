# P22 local monitoring and recovery

Scope: one authenticated local operator, research-only; no acquisition, scheduling,
outbound delivery, public deployment or financial mutation. P21 security remains
mandatory. P19 live activation and model/signal gates remain blocked.

Protected GET `/api/v1/operations/status`, `/metrics`, `/history` are additive;
the old health contracts remain. Status probes actual auth/session/audit storage,
checksum-pinned catalog, configured PostgreSQL, research directories, immutable
P19 receipts/checkpoints, P20 deliveries and operation-store/disk capacity. Missing
configuration is distinct from failure and policy blocks. PostgreSQL is optional
for historical reads; its absence still makes portfolio/paper reads unavailable.
Storage warns below two GiB OR ten percent free. Receipt corruption withholds
worker health. No permission, production or profitability upgrade follows from
a running process. Diagnostics exclude credential values and filesystem paths.

Data Health displays genuine component statuses and observed process metrics.
API request counts/errors/denials and p50/p95 retain at most 1,000 samples per
fixed component family; no usernames, security IDs or caller-supplied labels.
Metrics reset on process restart and are explicitly labeled as such. Persisted
probe history is separate: no invented uptime series or page-triggered alerts.
Database probe duration, actual storage bytes and saved worker/delivery totals
are reported when evidence/configuration exists.

The separate `db/operations/schema.sql` owns version 1 of `operations.sqlite3`.
Explicit CLI initialization, private owner/SYSTEM Windows DACL or POSIX 0700/0600,
WAL, synchronous FULL and BEGIN IMMEDIATE protect state. No startup migration.
At 5,000 probes recording refuses further growth rather than silently losing
evidence; archive operational backups and review capacity before continuing.

An explicit `check` persists its actual probe and detector timestamp. Two repeated
UNAVAILABLE/DEGRADED checks create one outbox event per component/status/reason
episode. Recovery or a material reason change starts a new episode. `process-alerts`
validates the referenced probe SHA256 before publishing through P20. Its cursor
advances only after P20 publication; a crash between commits replays the same
stable identity without duplication. Existing cooldown/quiet-hours/delivery
preferences remain. No new engine, stock alert or outbound channel is created.
TEST_ONLY observations are labeled and refused by real application history.

Safe JSON logs contain generated correlation IDs, fixed component/event/operation,
optional checksum-shaped research run ID, duration and status. Bodies, passwords,
cookies, CSRF, URLs/DSNs, paths and exception text are omitted. API/P19/P20/operation
commands share this boundary; saved receipts and P20 retain detailed domain reasons.
`api.jsonl` rotates at two MiB with three backups in the private operations root.
No arbitrary logging label or unbounded stack trace is emitted.

## Finite Windows CMD operations

Use the P21 research/auth/alert configuration, then:

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_OPERATIONS_ROOT=D:\al-research\p22-p25-runtime\operations
.venv\Scripts\python.exe -m alphalens_api.operations.cli init
.venv\Scripts\python.exe -m alphalens_api.operations.cli check
.venv\Scripts\python.exe -m alphalens_api.operations.cli history
.venv\Scripts\python.exe -m alphalens_api.operations.cli process-alerts
.venv\Scripts\python.exe -m alphalens_api.operations.cli backup --destination D:\al-research\p22-p25-runtime\backup-CHOOSE-NEW-NAME
.venv\Scripts\python.exe -m alphalens_api.operations.cli restore --source D:\al-research\p22-p25-runtime\backup-CHOOSE-NEW-NAME --destination D:\al-research\p22-p25-runtime\restore-CHOOSE-NEW-NAME
```

Backup uses SQLite's online backup API against read-only sources (128-page batches,
30-second time budget), not an open-file copy. Each completed database is schema/
quick-check verified and SHA256-pinned in a complete manifest published last.
Destinations must be new and owner restricted. A failed backup lacks a complete
manifest. Databases are separate snapshots, not a cross-database transaction.
For an application-coherent snapshot pause operator writes/finite workers first.

Restore validates every hash/name/size before creating a NEW disposable target;
it never overwrites original auth/alerts/operations. Restored auth sessions are
revoked to avoid resurrecting old credentials. Original credentials/alerts stay
untouched. Select a validated restored root only deliberately after shutdown.
Keep backups private: they include password hashes, CSRF and private alert state.
Research artifacts are excluded; PostgreSQL uses its established independent
backup convention and is not falsely covered by these SQLite commands.

API restart: stop its own foreground terminal with Ctrl+C, check free configured
port, restart with the same roots, then verify liveness/login/protected status.
P19 interruption: inspect existing receipt/checkpoint/lock, preserve original
request/payload/context, use the existing `resume` command only after the worker
is no longer active; never remove a live lock. P20 interruption: replay explicit
`process` then `retry`; immutable evidence/dedup survive. No scheduler is enabled.

Focused verification: 20 new backend monitoring/API/recovery/CLI cases passed; 97
P22/P19/P20 regression cases passed, earlier 42 P22/P21 cases passed; two frontend
component cases passed. Ruff/mypy/Bandit and TypeScript/ESLint passed. Browser/
deployed-system verification is repeated as part of P24/P25, not claimed here.
