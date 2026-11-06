# Final native Windows operating commands

Use the retained D-drive-backed Python environment. No daily model training,
CSV upload or public server is part of this workflow. The automatic research MVP
is blocked; these commands do not override provider/model/scheduler gates.

## Configure and create the operator account only if needed

Use an existing initialized account root where available. The example's
operator-auth is an uninitialized operator location, not a default account.
Review the private configuration's paths; retain an existing account and financial
DSN. No populated store/environment is recreated. No package is installed here.

```cmd
cd /d C:\Users\Dell\AlphaLens
if not exist D:\al-research\final-completion-runtime\local-config.json copy docs\operations\final-local-config.example.json D:\al-research\final-completion-runtime\local-config.json
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root D:\al-research\p21-runtime\operator-auth diagnostics
```

If diagnostics confirms no account at the selected root, choose your own username
and password through the existing hidden interactive prompt:

```cmd
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root D:\al-research\p21-runtime\operator-auth bootstrap --username operator
```

No password in argv or Git; bootstrap refuses existing accounts. If an existing
root differs, change auth_root in the private JSON and use that same root for CLI
operations. PostgreSQL is optional for historical browsing and required for
actual financial records; missing configuration remains503, not fictitious data.
Do not put a DSN/SMTP secret in shared JSON; preserve private existing environment.

## Start, log in, inspect and stop

The new compiled build is already at final-completion-runtime/web-final. The
existing P24 scripts serve compiled React and protected API in one foreground
process on127.0.0.1:8017. Setup initializes only additive operations state.

```cmd
scripts\windows\setup-local.cmd D:\al-research\final-completion-runtime\local-config.json
scripts\windows\start-alphalens.cmd D:\al-research\final-completion-runtime\local-config.json
```

After LOCAL_PROCESS_READY, open http://127.0.0.1:8017/login and sign in using your
own initialized credentials. Settings supports password changes/logout/session
revocation; Notifications supports authorized read/acknowledgment/preferences.
In a second CMD at the project root:

```cmd
scripts\windows\check-alphalens.cmd D:\al-research\final-completion-runtime\local-config.json
scripts\windows\stop-alphalens.cmd D:\al-research\final-completion-runtime\local-config.json
```

These exact script interfaces were exercised against the new compiled application
using an isolated TEST_ONLY account/config; real research and the original47 alerts
were read without modification. Cooperative stop affects only the owned instance.
No scheduler, source price download, outbound message, tunnel or public listener.
Normal operator initialization still requires your own password; test credentials
are never a supported application login or production fallback.

## Source, model, run and prospective evidence

```cmd
.venv\Scripts\python.exe -m workers.daily.cli check-source --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli check-source --root D:\al-research\p19-runtime\pipeline --network-publication-status
.venv\Scripts\python.exe -m workers.daily.cli check-models --root D:\al-research\p19-runtime\pipeline --model-root D:\al-research\tejhq-research-evaluation-v2-fit-parallel
.venv\Scripts\python.exe -m workers.daily.cli status --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli verify --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli init-prospective --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli forecasts --root D:\al-research\p19-runtime\pipeline --limit 20 --offset 0
.venv\Scripts\python.exe -m workers.daily.cli prospective-status --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli process-prospective-alerts --root D:\al-research\p19-runtime\pipeline --alerts-root D:\al-research\p20-runtime\alerts
```

Network publication status is one explicit keyless metadata request, not a price
acquisition or scheduling approval. A publisher-advertised date is not an accepted
market session. check-models reads checksum-pinned local metadata/skops types,
never deserializes, trains or reevaluates. Initialization is explicit/idempotent,
keeps existing forecasts and rejects unknown schema versions. Current forecast
and outcome totals0, all metrics null, prospective alerts scanned0/published0.
Processing is bounded100 outcome events; repeat when continuation=1. Failed P20
publication leaves the cursor unacknowledged; repeated events deduplicate safely.

Open /data-health, /opportunities and /system-health through authenticated dashboard
navigation. Current predictions/top5/10/20 shortlists remain explicitly unavailable.
There is no claimed functioning shortlist command or normal fake forecast API.
Existing version-compatible worker resume and run-once interfaces are documented
and tested in [P19 commands](../pipeline/p19-windows-commands.md). Select the actual
failed checkpoint/run ID shown by status; never generate a competing request or
launch another worker while its lock is held. Rights/adapter failure returns a
blocked receipt (exit2), not a successful live update. No new enabled schedule is
registered or prepared as a falsely active daily service.

## Notification and operational history

Existing P20 command interfaces are verified by preserved tests. Listing is read-only;
process/retry are explicit local in-app operations and do not enable external channels.

```cmd
.venv\Scripts\python.exe -m workers.alerts.cli --root D:\al-research\p20-runtime\alerts list --limit 20
.venv\Scripts\python.exe -m workers.alerts.cli --root D:\al-research\p20-runtime\alerts process --daily-root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.alerts.cli --root D:\al-research\p20-runtime\alerts list --delivery FAILED
.venv\Scripts\python.exe -m workers.alerts.cli --root D:\al-research\p20-runtime\alerts retry
```

No original alert lifecycle/preference was mutated during this resumed work. Detailed
health and request measurements require authentication in System Health. Persisting
an operational probe/history or processing its outbox uses existing explicit
operations.cli check/history/process-alerts commands with configured private
ALPHALENS_* roots; the dashboard performs read-only probes. Email/desktop and stock
signal notifications remain disabled and cannot be activated via preferences.

## Backup and disposable restore

Choose a NEW directory for each backup; pause mutations if cross-store consistency
is required. Online SQLite backup handles open WAL databases. Source stores and
immutable market/model archives are never overwritten or copied into the backup.

```cmd
scripts\windows\backup-alphalens.cmd D:\al-research\final-completion-runtime\local-config.json D:\al-research\final-completion-runtime\backup-NEW
.venv\Scripts\python.exe -m alphalens_api.operations.cli restore --source D:\al-research\final-completion-runtime\backup-NEW --destination D:\al-research\final-completion-runtime\restore-NEW
```

Actual four-store backup/isolated restore passed. The optional prospective database
is included only if explicitly initialized. Restore validates manifest/file hashes
and schema, requires a new destination and revokes restored authentication sessions.
It does not replace a real account root or source archive. PostgreSQL backup remains
a separate native pg_dump procedure under the existing database configuration.

## Targeted tests and build

These checks are finite software tests, not historical research reruns:

```cmd
set ALPHALENS_TEST_TEMP_ROOT=D:\al-tests
.venv\Scripts\python.exe -m pytest tests\unit\test_final_provider.py tests\unit\test_final_compatibility.py tests\unit\test_final_forward.py tests\unit\test_p19_daily.py tests\unit\test_p20_alerts.py tests\unit\test_p22_operations.py tests\integration\test_p19_api.py -W error -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\final-completion-runtime\web-final
cd apps\web
npm test
npm run typecheck
npm run lint
npm run build
cd ..\..
```

Actual browser evidence used private TEST_ONLY credentials/state outside Git and
PLAYWRIGHT_BROWSERS_PATH=D:\al-research\p18-runtime\browsers. Do not run session
expiry injection against a real operator store. Complete executed test totals,
retries, skips and CI outcomes are in the final report. The existing compiled build
and environments are reused; no install/cache deletion is required for daily use.
