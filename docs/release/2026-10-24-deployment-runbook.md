# Private Windows research release — 24 October 2026

The isolated application is at **http://127.0.0.1:8041/nse-market**. It uses the
patched candidate Python environment and compiled frontend, real retained private
research observations, a separate QA operator/personal store and disabled provider
access. It is not a public or production-data deployment. The original operator
configuration and live scheduler definitions are unchanged.

## Paths and prerequisites

Run from `D:\al-research\p28-worktree`. The candidate interpreter is
`.local-data\completion-runtime\venv\Scripts\python.exe`; do not substitute the
preserved shared `.venv`. The candidate frontend source/dependencies are in
`.local-data\completion-runtime\web-dependencies`; its compiled output is
`.local-data\completion-release\web-build`. Use the installed supported
`D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe`, not PATH's Node20.

The config is `.local-data\completion-release\qa-config.json`. QA credentials and
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
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config.json check
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config.json start
```

`start` is a foreground owned loopback supervisor. When launching with PowerShell
`Start-Process`, use `-WindowStyle Hidden`, an explicit working directory and
private stdout/stderr paths. Do not expose the service on `0.0.0.0` or adopt another
listener. To stop this instance from another terminal:

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m alphalens_api.local.cli --config .local-data/completion-release/qa-config.json stop
```

This requests a matching private supervisor nonce and waits for STOPPED. It does
not terminate arbitrary PIDs or stop the shared database. Preserve the candidate
build/config and previous builds for rollback; restarting the previous local
configuration does not clear its dependency advisories.

## Acceptance and evidence

Sign in through `/login`, then open `/nse-market`. Search **saved NSE prices**;
the current-master search can be stale independently. Select gainers/losers/volume
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
receipts live under `.local-data\completion-20261024`; the native log is
`native-qa.log`, plus the isolated operations store and supervisor state.

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
public redistribution rights are unverified. Fresh final-image container scanning
and the strict full-history secret gate remain separate release blockers.
