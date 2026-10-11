# P20 Windows CMD operations

Run from `C:\Users\Dell\AlphaLens`. Existing environments and D-drive junctions
are reused. These commands never train models, reevaluate the holdout, run
historical backtests, send external messages or install scheduled tasks.
Global P20 `--root` precedes its subcommand.

## One-shot alert processing and recovery

```cmd
cd /d C:\Users\Dell\AlphaLens
set P20_ROOT=D:\al-research\p20-runtime\alerts
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% init
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% check-source
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% check-source --network
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% process --daily-root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% inspect-lock --daily-root D:\al-research\p19-runtime\pipeline
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% inspect-models --run-root D:\al-research\tejhq-research-evaluation-v2-fit-parallel
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% list --limit 20
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% list --delivery FAILED --limit 20
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% preferences
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% retry
.venv\Scripts\python.exe -m workers.daily.cli status --root D:\al-research\p19-runtime\pipeline
```

`init` is idempotent. `process` validates saved receipts/checkpoints, atomically
stores unseen alerts and processes the due in-app outbox. Repeating it after a
restart creates zero duplicate events. `retry` does not reset failed attempt caps
or resend suppressed events. `inspect-lock` probes without stopping its owner;
AVAILABLE describes only the instant of that probe. Metadata checks do not acquire
prices or grant rights. Model checks read hashes/metadata only, without deserialization.

The saved one-time P19 blocked attempt remains inspectable; its unchanged request
returns its existing receipt and does not acquire prices:

```cmd
.venv\Scripts\python.exe -m workers.daily.cli dry-run --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\blocked-daily-request\request.json
.venv\Scripts\python.exe -m workers.daily.cli run-once --root D:\al-research\p19-runtime\pipeline --request D:\al-research\p19-runtime\blocked-daily-request\request.json
```

Expected P19 exit 2 / BLOCKED_SOURCE. This is not live activation. Existing
[P19 operations](../pipeline/p19-windows-commands.md) cover saved historical receipt
verification/resume; do not repeat the completed replay. No recurring collection
or notification processing task is registered. An operator can run this finite
processor manually even while market acquisition remains blocked.

## Start the read-only dashboard

Use an already running instance if the ports are occupied; never duplicate it.
First CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_RESEARCH_DATA_ROOT=D:\al-research\tejhq-final-vintage-v1-r3
set ALPHALENS_RESEARCH_RUN_ROOT=D:\al-research\tejhq-research-evaluation-v2-fit-parallel
set ALPHALENS_RESEARCH_REPORT_ROOT=C:\Users\Dell\AlphaLens\docs
set ALPHALENS_CATALOG_PATH=D:\al-research\p17-api\discovery.sqlite
set ALPHALENS_DAILY_ROOT=D:\al-research\p19-runtime\pipeline
set ALPHALENS_ALERTS_ROOT=D:\al-research\p20-runtime\alerts
set ALPHALENS_ALERT_MUTATIONS=false
set ALPHALENS_PORT=8017
.venv\Scripts\python.exe -m alphalens_api serve
```

Second CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens\apps\web
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set ALPHALENS_API_PROXY_TARGET=http://127.0.0.1:8017
set ALPHALENS_WEB_CACHE_DIR=D:\al-research\p20-runtime\web-cache
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p20-runtime\web-build
npm run dev
```

Open `http://127.0.0.1:5173/notifications`, `/data-health` and `/settings`.
API reads (verified with actual local HTTP during browser checks):

```cmd
curl.exe http://127.0.0.1:8017/api/v1/alerts?limit=20
curl.exe http://127.0.0.1:8017/api/v1/alerts/unread-count
curl.exe http://127.0.0.1:8017/api/v1/alerts/preferences
```

Read/acknowledgment and settings controls show explicitly unavailable until the
operator opts in. The default server does not register POST alert routes. Guarded
writes were verified in isolated ASGI tests; the actual browser run used this
read-only startup. No enabled local write server was left running.

For an operator who deliberately wants local interactive alert controls, the
implementation accepts `ALPHALENS_ALERT_MUTATIONS=true` at startup. This is an
opt-in alternative, not the default verified browser startup above. It affects
only alert lifecycle/preferences; P17 financial routes remain GET-only. No remote
access, scheduling or outbound delivery is enabled by this flag. Same-origin
Vite requests must supply the required Origin, JSON type and P20 context header.

## CLI acknowledgment and preferences

Use a real ID returned by `list`; placeholders below are parameter shapes, not
claims that a corresponding ID/file already exists. These dispatches were tested
against isolated persisted operational evidence:

```cmd
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% get ALERT_ID
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% state ALERT_ID READ
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% state ALERT_ID ACKNOWLEDGED
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% state ALERT_ID RESOLVED
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% preferences --file D:\al-research\p20-runtime\my-preferences.json
.venv\Scripts\python.exe -m workers.alerts.cli --root %P20_ROOT% prune
```

Obtain the complete preferences object with `preferences`, edit a separately
named local JSON file, then load it with `--file`. Categories `[]` disable in-app
delivery while retaining evidence. `include_info=false` avoids success-message
spam. Quiet hours retain pending INFO/WARNING; ERROR/CRITICAL bypass them.
`email` and `desktop` must remain `false`; both external channels are unavailable.
Changing preferences does not retroactively resend previously suppressed alerts.
Pruning is deliberate and removes only old resolved INFO/WARNING; high severity
and dedup tombstones survive. Archive operational storage separately if capacity
is reached. Never delete frozen research files, junctions or project environments.

Explicit `import-paper`, `import-valuation` and `freshness` dispatches exist for
trusted, hash-named persisted evidence. Their readers are exercised by tests;
no real new paper trade or missing-session document was invented for this run.
`--test-only` imports are strictly isolated and cannot be served by app mode.
CLI operational failures return exit 2 with a redacted message; successful finite
commands return 0. P19 retains its separate existing exit-code contract.
