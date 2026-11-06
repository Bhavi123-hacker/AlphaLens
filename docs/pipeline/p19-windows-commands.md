# P19 local Windows CMD operations

Run from Windows CMD, with the existing D-drive junctions and frozen archive intact.
No model training, final-holdout evaluation, broker or automatic price download is
invoked by these commands. They were exercised locally. Python dependencies and
frontend node_modules already exist; do not reinstall through an existing junction.

## Backend and dashboard

First CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_RESEARCH_DATA_ROOT=D:\al-research\tejhq-final-vintage-v1-r3
set ALPHALENS_RESEARCH_RUN_ROOT=D:\al-research\tejhq-research-evaluation-v2-fit-parallel
set ALPHALENS_RESEARCH_REPORT_ROOT=C:\Users\Dell\AlphaLens\docs
set ALPHALENS_CATALOG_PATH=D:\al-research\p17-api\discovery.sqlite
set ALPHALENS_DAILY_ROOT=D:\al-research\p19-runtime\pipeline
set ALPHALENS_PORT=8017
.venv\Scripts\python.exe -m alphalens_api serve
```

Use the existing instance if 8017 is already listening; do not duplicate it.
Database configuration is optional for historical/daily reads. Private portfolio
records remain unavailable without the privately configured P17 database.

Second CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens\apps\web
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set ALPHALENS_API_PROXY_TARGET=http://127.0.0.1:8017
set ALPHALENS_WEB_CACHE_DIR=D:\al-research\p19-runtime\web-cache
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p19-runtime\web-build
npm run dev
```

Open `http://127.0.0.1:5173/data-health`; OpenAPI is at
`http://127.0.0.1:8017/openapi.json`. Verify reads:

```cmd
curl.exe http://127.0.0.1:8017/api/v1/daily/status
curl.exe http://127.0.0.1:8017/api/v1/daily/runs?limit=20
curl.exe http://127.0.0.1:8017/api/v1/daily/checkpoints
curl.exe -i http://127.0.0.1:8017/api/v1/daily/latest
```

Latest is intentionally 503: a historical replay is not a successful new-session
run. No current candles, predictions or signals are manufactured.

## Worker inspection and recovery

```cmd
cd /d C:\Users\Dell\AlphaLens
.venv\Scripts\python.exe -m workers.daily.cli status --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli check-source --root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.daily.cli verify --root D:\al-research\p19-runtime\pipeline --run-id 39053e9cf4c8b1509046fc3ab6bd29c046b59a85a0d9d3c12ae05edd7b05ccbf
.venv\Scripts\python.exe -m workers.daily.cli dry-run --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\final-replay-request\request.json
.venv\Scripts\python.exe -m workers.daily.cli resume --root D:\al-research\p19-runtime\pipeline --run-id 39053e9cf4c8b1509046fc3ab6bd29c046b59a85a0d9d3c12ae05edd7b05ccbf
```

The last command returns the already completed receipt; it does not repeat the
completed replay. For an incomplete current-version run, supply the same local
payload and approved manifest as the original replay. A changed execution schema
is rejected on resume; older completed receipts remain readable/verifiable.
Optional `check-source --network-metadata` checks only fixed public HF metadata
with bounded retries. It never downloads market prices or changes permission.

CLI exit codes: 0 read/dry-run/completed-with-warnings, 2 evidence/source blocked,
1 failed or recovery required, 130 Ctrl+C. JSON is structured operational output;
immutable request/retry/receipt files provide the audit trail. Ctrl+C safely stops
an active worker, retains checkpoints and releases its OS lock. There is no
always-running ingestion daemon to stop, and no training worker is restarted.

Prepare a separately stored **blocked** DAILY request (no price acquisition):

```cmd
.venv\Scripts\python.exe -m scripts.prepare_p19_request --archive-root D:\al-research\tejhq-final-vintage-v1-r3 --output D:\al-research\p19-runtime\blocked-daily-request --session 2026-10-08
.venv\Scripts\python.exe -m workers.daily.cli dry-run --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\blocked-daily-request\request.json
.venv\Scripts\python.exe -m workers.daily.cli run-once --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\blocked-daily-request\request.json
```

Expected: unknown calendar session/source gate, `BLOCKED_SOURCE`, exit 2. Repeating
the unchanged request returns the same receipt. A corrected input requires a
new revision directory; do not overwrite originals. Request preparation reuses
matching files and preserves the first cutoff. No missing weekday is invented.

## Explicit pinned historical replay

The existing source file is reused, with no network download. This only replays
P2-P6 into independent P19 storage. On this machine the final replay is already
complete and returns its receipt:

```cmd
.venv\Scripts\python.exe -m workers.daily.cli replay --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\final-replay-request\request.json --context D:\al-research\p19-runtime\final-replay-request\context.json --payload C:\Users\Dell\AlphaLens\data\tejhq-research\p2\raw\tejhq\indian-markets-nse\2026\10\07\2b23245b897f861bd8302a4fec2b69da6945de7982a75c40dda45b6b87bc7856\payload --approved-manifest docs\data\tejhq-acquisition-manifest.json
```

The approved manifest is hash-pinned in the CLI. Caller-written permission flags
cannot approve another provider/revision. Raw data/models are never committed.

## Scheduling and verification

Preparation writes `disabled-task.xml`: both task and trigger disabled; its action
is dry-run, not ingestion. **No task has been registered or enabled.** Its example
22:30 IST time is not evidence of provider release time. A genuine recurring
run-once schedule is not ready until source/calendar/inference gates pass and
the user explicitly authorizes installation. Task Scheduler must run on a powered-on
computer; StartWhenAvailable controls missed-run recovery, not data availability.
No Codex session or paid scheduler is required. After a separately authorized task
exists, Windows inspection/disable commands are:

```cmd
schtasks /Query /TN AlphaLens-P19-Research /V /FO LIST
schtasks /Change /TN AlphaLens-P19-Research /DISABLE
```

These administrative examples were not executed because no task exists. No enabled
registration command is supplied while activation is blocked.

Frontend checks from `apps\web`, using the Node PATH above:

```cmd
npm run typecheck
npm run lint
npm test
npm run build
set PLAYWRIGHT_BROWSERS_PATH=D:\al-research\p18-runtime\browsers
set ALPHALENS_BROWSER_OUTPUT_DIR=D:\al-research\p19-runtime\browser-results-final
set ALPHALENS_BROWSER_REPORT=D:\al-research\p19-runtime\browser-final-report.json
npm run test:browser
```

Targeted Python verification from repository root:

```cmd
set ALPHALENS_TEST_TEMP_ROOT=D:/al-tests
.venv\Scripts\python.exe -m pytest tests\unit\test_p19_daily.py tests\integration\test_p19_api.py -W error -ra
```

Tests do not grant provider permission. See the separate verification/security
reports for the real PostgreSQL regression, strict CI and production blockers.
