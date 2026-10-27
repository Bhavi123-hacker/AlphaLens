# Private Windows research release — 24 October 2026

The isolated application is at **http://127.0.0.1:8041/nse-market**. It uses the
patched candidate Python environment and compiled frontend, real retained private
research observations, a separate QA operator/personal store and disabled provider
access. It is not a public or production-data deployment. The original operator
configuration and live scheduler definitions are unchanged.

## 27 October verified continuation: current native configuration

The current compiled private application is still on port **8041**, using
`.local-data/completion-release/qa-config-market-workspace-20261027-v3.json`
and `.local-data/completion-release/web-build-market-workspace-20261027-v3`.
Only the frontend root differs from the prior operational configuration. The
same authentication, operations and database stores are preserved; older builds
and configurations remain available. Use the same
`.local-data/completion-runtime/venv/Scripts/python.exe` app interpreter and the
current config with the check/start/stop CLI commands below. These operations do
not start the separate market-data collector.

The final compiled entry is `index-CyuHA4qJ.js`. Genuine saved-data search,
chart preview, Top5/10/20, forecast history and pending outcome evaluation passed
the deployed browser workflow. See
[the 27 October execution and verification report](ALPHALENS_PRIVATE_MARKET_COMPLETION_2026-10-27.md).

The collector source activation separately deployed exactly its reviewed two
files under the operator's AC-wait amendment. Its installed fingerprint is
`98d635dc30737ac7c034fbcd6bd463ac4a4553878e4efac906ee4f4701c05eac`.
The active checkout remains pinned to `6a5b73af588624cadc1e464d8ca90b5944421893`
plus those two intended changes; do not reset, broadly update or merge it.
No scheduler action or power/clock policy changed. The existing 20:30 run passed
its initial clock gate, then reported ancestor interruption during a recorded
DC/AC interval; Scheduler returned `0x8007042B`. It made zero recorded provider
requests and delivered zero candles. The exact termination initiator is unknown.
Keep its 600-request reservation; never reset the budget or start a manual retry.
The next existing 21:30/22:30 triggers must establish actual delivery. The below older paths remain historical
rollback references, not the current configuration.

For cooperative restart, require a matching private owned instance and retain
the CLI result. An intermediate command returned exit2 although the same owned
instance reached STOPPED. Its exact exception was not retained. Verify matching
ownership, final STOPPED state, process absence and an unbound port before any
replacement start; do not kill arbitrary PIDs or adopt another listener. The
final restart returned `OWNED_INSTANCE_STOPPED` and preserved session/database
persistence. State files contain a private nonce: never print or publish the
whole instance/shutdown payload.

The excluded watchlist task remains on its original shared interpreter with
43 freshly observed dependency advisories. Its separate inactive action-only
proposal is under `.local-data/watchlist-runtime-readiness-20261027`. No approval
for that task is inferred from the collector source activation.

A separate inactive proposal changes only the NSE task's two battery flags:
`.local-data/nse-battery-policy-proposal-20261027/plan-INACTIVE.json`, SHA-256
`24698ecdfc693c333c904bc9a823e7865f7fdc6569eb2fdd8d3d1496cd19636b`.
It expires 27 October 21:15 IST and requires new explicit approval. Review
`BATTERY_SETTINGS_REVIEW.md` alongside it; do not apply it under the earlier
source-activation approval. No task modification has occurred.

## 25 October historical verified configuration

The updated compiled deployment now uses
`.local-data/completion-release/qa-config-production-readiness.json` and
`.local-data/completion-release/web-build-production-readiness-20261025`.
Use that config with the same patched app interpreter and local CLI start/check/
stop commands above. The previous `qa-config-blockers.json` and its build remain
available for rollback, alongside the earlier original QA configuration.
Authentication and the same PostgreSQL store survive cooperative restart.

The current prepared collector is a **separate dedicated** frozen-copy runtime,
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`.
Its wrapper and exact reversible approval-scoped task action are documented in
[the collector cutover procedure](production-collector-cutover.md). This supersedes
only the earlier proposed candidate path; no live action or RELIANCE task was
changed. Do not execute the prepared collection wrapper as an offline smoke test.

Validate private release wiring without provider calls:

```powershell
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.verify_private_release_manifest
```

Read forecast maturity without any writes:

```powershell
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.nse_forward_outcomes --root .local-data/nse-market-expansion
```

The existing daily stage runs the same qualified maturation after collection and
on replay. The standalone explicit `--append-qualified` mode is only an offline
idempotent retry using saved raw evidence and the existing kernel lock; it never
fetches missing prices. No new scheduler registration is needed or authorized.
Current readiness and the actual-date evidence are recorded in
[the final readiness report](ALPHALENS_PRODUCTION_READINESS_FINAL.md).

## Paths and prerequisites

Run from `D:\al-research\p28-worktree`. The candidate interpreter is
`.local-data\completion-runtime\venv\Scripts\python.exe`; do not substitute the
preserved shared `.venv`. The candidate frontend source/dependencies are in
`.local-data\completion-runtime\web-dependencies`; its compiled output is
`.local-data\completion-release\web-build-blockers-20261024`. Use the installed supported
`D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe`, not PATH's Node20.

The current config is `.local-data\completion-release\qa-config-blockers.json`.
The previous `qa-config.json` and `web-build` remain intact for rollback. QA credentials and
session state remain private owner-protected local files under that directory;
the original account/password is not reset. The existing owned PostgreSQL17
cluster and read-only database credential are reused. No schema migration occurs.

## Start, check and stop

```powershell
Set-Location -LiteralPath 'D:\al-research\p28-worktree'
$env:PYTHONPATH = (Get-Location).Path
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& .local-data/completion-runtime/venv/Scripts/python.exe -m scripts.p30_local_database start
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config-blockers.json check
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config-blockers.json start
```

`start` is a foreground owned loopback supervisor. When launching with PowerShell
`Start-Process`, use `-WindowStyle Hidden`, an explicit working directory and
private stdout/stderr paths. Do not expose the service on `0.0.0.0` or adopt another
listener. To stop this instance from another terminal:

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config-blockers.json stop
```

This requests a matching private supervisor nonce and waits for STOPPED. It does
not terminate arbitrary PIDs or stop the shared database. Preserve the candidate
build/config and previous builds for rollback; restarting the previous local
configuration does not clear its dependency advisories.

## Acceptance and evidence

Sign in through `/login`, then open `/nse-market`. Search **saved NSE prices** or
the full dated equity master. Staleness remains visible and blocks provider
identity actions without erasing saved search. Select gainers/losers/volume
and Top5/10/20. Five sessions is the trained classifier horizon. Risk ordering
subtracts daily-return SD with weight1, an unvalidated engineering assumption.
Ten/twenty-session screens remain descriptive, not trained forecasts.

Open a stock's saved daily chart and its experimental model/outcome evidence.
Its prospective history shows original immutable forecasts and pending outcomes.
Forward evaluation must show unavailable accuracy until qualified outcomes mature.
The provider button/refresh cannot acquire data in this QA configuration.

Actual HTTP checks include unauthorized401, login200, database readiness200,
saved-market/research/history/evaluation200 and blocked provider refresh503.
See the dated test report for final browser/restart results. Private logs and
receipts for the final blocker release live under
`.local-data\blocker-resolution-20261024`; the current native log is
`native-blockers-final.log`, plus the isolated operations store and supervisor
state. Earlier `.local-data\completion-20261024` evidence remains preserved.

To reproduce the numerical saved-data acceptance without new forecasts:

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m scripts.verify_saved_nse_workflow --root .local-data/nse-market-expansion --v2-root .local-data/experimental-nse-v2 --output .local-data/completion/saved-workflow-NEW-UNIQUE-NAME.json
```

The output must be a fresh private D: path. The verifier replays already-qualified
saved observations; it does not create new decisions, mature outcomes, fit models
or recertify present action/calendar/clock eligibility.

## Boundaries and operational recovery

Live collection remains the existing approved500 policy:250 securities/run,
600 reserved GETs/run,1800/day,20:30/21:30/22:30 IST,60-minute cooldown and31-day
catch-up. Do not change its interpreter, task, retry count or timing during release.
Read genuine worker receipts and source acceptance; scheduler exit0 alone is
insufficient. The latest retained session is partial, and recent starts failed
clock checks or were interrupted. Clock failures need diagnosis, not tolerance
widening or invented successful captures.

New provider calls, live-task modification, production migration/model replacement,
1000-stock activation, public display/deployment and paid resources require the
user approvals and evidence stated in the campaign. WebSocket entitlement and
public redistribution rights are unverified. Current exact-commit dependency,
container and full-history secret dispositions are in
[the final blocker report](ALPHALENS_FINAL_BLOCKER_RESOLUTION_2026-10-24.md).
The earlier 876dcee image result remains historical.

## Read-only collection diagnosis

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m scripts.nse_collection_status --root .local-data/nse-market-expansion --provider-root D:/al-research/p28-runtime/provider-state --observe-windows
```

This validates saved raw evidence and prints expected/retained sessions,
per-security missing reasons, actual versus reserved requests, unfinished runs,
next task trigger and forecast freshness. Cold reads can take minutes. It makes
no provider call, task change, forecast write or clock-network probe.

## Separate synthetic publication preparation

The existing `apps/web/vite.demo.config.ts` builds `apps/web/demo` separately from
the private dashboard, with no API proxy and CSP `connect-src 'none'`. Its source
and preview procedure are documented in `apps/web/demo/README.md` and
`docs/operations/p29-public-demo.md`. CI builds it and runs its four isolation
browser checks. Build artifacts remain local/CI evidence; actual public
publication still requires explicit final approval. Do not copy private configs,
session state, provider receipts, research data or model artifacts into it.

## Collector runtime migration proposal — approval required

The unchanged live task currently launches `scripts/windows/run-nse-market.cmd`,
which calls `project-python.cmd` and the shared `.venv`. A fresh read-only audit
of that environment still reports advisories in certifi2026.7.22, filelock4.0.10
and Pillow12.3.0. Its production collector path is BLOCKED_SECURITY. The private
8041 app instead uses the separate patched candidate and passed its own audit.

Proposed replacement action, **not registered or activated**:

```text
Executable: D:\al-research\p28-worktree\.local-data\completion-runtime\venv\Scripts\python.exe
Arguments: -m workers.nse_market.launcher --config D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json
Working directory: D:\al-research\p28-worktree
```

Retain the current run user/interactive security principal, 20:30/21:30/22:30 IST
triggers, original500 cohort, 250/run, 600-reserved/run, 1800/day, 60-minute
cooldown, protected credential targets and original RELIANCE task. Pin this
checkout's package paths as the existing wrapper does. Export and hash the
original XML before an approved replacement, then verify native imports,
independent clock, quota lock, actual terminal receipt and unchanged original
forecast/research records. Restore that exact original action/XML if the migration
fails; do not clear reservations, replace models or issue an extra provider probe.

User approval is required because this changes the live scheduled interpreter.
This proposal and the candidate dependency audit are preparation, not activation.
