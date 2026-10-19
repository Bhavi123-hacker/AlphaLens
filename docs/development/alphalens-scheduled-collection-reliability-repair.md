# Scheduled collection reliability repair

Verification date: 19 October 2026, IST. Branch: `alphalens-visual-overhaul`.
Starting commit: `7b1bf94f580424bda7bd7f9136a3e678dd870474`.
Software repair: `b6be9107bde64f8a5969408ddb7af452f857049e`.

## Defect and correction

The 19 October 22:30 attempt correctly refused acquisition under the old immediate
cooldown check. Its independent lower receipt bound was 22:30:08.142331 IST;
the preceding reservation's upper bound was 21:30:29.664385 IST. Only
**3,578.477946 conservative seconds** had elapsed: **21.522054 seconds short** of
the required 3,600. Hourly wall-clock triggers do not guarantee hourly elapsed
receipt bounds. The refusal occurred before a new reservation or provider GET.
This was an operational startup defect, not evidence that the cooldown was wrong.

`workers/nse_market/operational.py` now allows only the explicitly approved
scheduled path a maximum **60-second monotonic preflight wait**. It computes each
wait from the remaining conservative interval, obtains fresh independent clock
evidence afterward, and recalculates eligibility. It rechecks rollback, future
dates, exact approval/cohort policy, operator/credential readiness, IST-day attempt
count and reserved capacity. Crossing midnight uses the newly verified IST day.
Clock disagreement, excessive shortfall, exhausted wait budget or revoked readiness
fails closed. Waiting never creates a collecting reservation, constructs a provider
meter or calls the provider. No cooldown tolerance or trigger was changed.

The existing kernel lock encloses the complete preflight, wait and reservation.
A second worker cannot pass the check while the first waits. Existing immutable
`*.started.json` capacity reservations remain consumed after crashes. Manual
collection retains immediate cooldown refusal; dry runs make no acquisition and
do not wait. A separate `*.attempt.json` records process/preflight evidence without
being counted as a collecting attempt.

## Interruption investigation and diagnostics

The 19 October 21:30 expanded run and the RELIANCE task reported
`3221225786 / 0xC000013A`, a control-interruption exit. The expanded run has a
start/reservation receipt and one successful master GET, but no terminal worker
receipt. The 22:30 run instead completed with exit **1** and the cooldown error.
Neither result proves who interrupted the earlier process.

Inspection did not establish a reproducible application-side process termination
defect. The existing CMD launcher is synchronous and propagates the Python exit
code; the inspected worker contains no scheduled timeout that explains these
interruptions. Available system evidence does not establish sleep, logoff, console
closure or a termination initiator at 21:30. Task Scheduler Operational history
remains **disabled**. No system audit setting or task definition was changed.

The scheduled CMD branches now invoke a small **in-process** diagnostic launcher,
`workers/nse_market/launcher.py`, before importing the heavier worker. It does not
introduce a subprocess, alter console groups or claim to cure an unknown external
termination. Private checksummed facts record UTC time, launch/run correlation,
PID/parent PID, safe stage/error identifiers and observed exit status. Normal exit,
Python control interruption and unexpected exceptions are distinct. The worker
also records preflight, identity, session-selection and collection/research stages.
Metadata is allowlisted; credentials, command arguments, provider bodies and free
exception text are excluded. Private-directory ACL checks remain enforced.

A hard-killed process cannot be relied upon to write its own final fact. A start
without a terminal receipt is displayed as **incomplete evidence**, with unknown
per-run actual GET count, rather than success or proof of a currently running PID.
These diagnostics improve the next incident's evidence; the prior initiator is
still **unknown**.

## Monitoring corrections

The saved research API computes full configured-cohort session coverage **before**
shortlist pagination. Top 5, 10 and 20 now report the same underlying session
coverage. The currently retained end date is **16 October**, with **499/500**
securities having that session; SHERVANI's latest saved observation remains
15 October. This is not 19 October coverage.

The panel separates today's read-only **shared-provider ledger** across clients
and retries from workflow capacity reservations, the last terminal workflow
receipt, and unfinished attempts. It preserves exact underlying timestamps as
well as human-readable IST times. Unresolved provider intents do not prove HTTP
completion; successful HTTP responses do not prove accepted candles. Reading this
API/panel performs **zero provider GETs**.

Observed before midnight on 19 October: **1** shared completed GET, **600** reserved
workflow requests, and **0** GETs in the failed 22:30 terminal run. The older
unfinished 21:30 run retains its reservation; its per-run actual count is unknown
from its missing terminal receipt. The shared ledger and earlier source receipt
provide the separate one-GET evidence. All prior reservation evidence is retained.

## Verification

| Check | Actual result |
|---|---|
| Worker/monitoring focused suite | **35 passed**, warnings treated as errors; isolated TEST_ONLY clocks/stores, no Upstox requests |
| Incident shortfall and kernel concurrency recheck | **2 passed**, 3.67 seconds |
| Strict typing | **390 source files**, no issues |
| Ruff check/format and diff whitespace | Passed; **660** files formatted as required |
| Bandit | Zero issues, 45,338 lines scanned; zero suppressed lines |
| Python dependency audit | No known vulnerabilities |
| Full local Windows backend regression | **1,507 passed / 19 skipped**, 1,318.93 seconds, warnings treated as errors; exit 0 |
| Full local frontend | **114 passed / 22 files**, 73.30 seconds with one Windows worker and unchanged timeouts |
| Frontend typecheck/lint/production build | Passed; separate private build directory; existing large chart-chunk warning retained |
| Authenticated compiled browser | **10 grouped checks passed** on isolated QA port 8029, saved real research, desktop/mobile screenshots; zero page errors/provider requests |
| Frontend GitHub CI | **PASS**: 114 tests, four isolated synthetic-demo browser tests, typecheck/lint/build, unchanged OpenAPI client/notices, npm audit zero vulnerabilities |
| Backend/PostgreSQL GitHub CI | **PASS: 1,514 passed / 12 skipped**, 324.34 seconds, real disposable PostgreSQL 17; frozen lock, Ruff, typing, Bandit and dependency audit passed |
| Container CI | Rebuilt/import/auth/non-root checks and strict scan passed; downloaded report has **zero HIGH/CRITICAL findings**, three targets |

The first local frontend run had **111 passes and three existing 5-second
interaction-test timeouts** while other checks ran. The subsequent complete run
used one worker, preserved the same deadlines and passed all 114. The Linux CI
run also passed all 114. The initial failures are retained rather than represented
as a clean first run. The private browser harness initially inspected loading
content too early and compared CSS-uppercased labels case-sensitively; it was
corrected to wait for actual coverage and compare visible label case appropriately.
No product timeout was increased.

Deterministic worker tests cover exact 3,600-second eligibility; the actual
21.522054-second deficit; fresh-clock rechecking; shortfall over 60 seconds;
rollback; clock disagreement; monotonic timeout/stalled clock; midnight accounting;
daily attempt and reservation ceilings; crash reservations; simultaneous workers;
revoked credentials/approval; and unchanged dry/manual behavior. Additional tests
cover launcher exits, interrupted stages, sensitive-metadata rejection, missing
completion evidence, full-cohort pagination and shared-ledger IST-day accounting.

The 22:58 IST read-only independent clock check returned
`INDEPENDENT_DATE_BOUNDS_AGREE`, approximately 52.473 ms receipt-bound width,
with the existing explicit **unauthenticated NTP, not production attestation**
qualification. It required no quote-classification change or Upstox request.

CI evidence for the software commit:

- [Foundation/backend/PostgreSQL/container](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39294448433)
- [Frontend and synthetic demo](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39294448286)

The unchanged configured secret gate scanned 26 chunks / 42,215 bytes in this
code range with **zero verified and zero unverified findings**. This is not a new
full-history clean claim. The three historical unverified secret detections remain disclosed in
[the existing audit](../security/final-secret-history-audit.md). No detector,
severity policy, credential or Git history was altered or suppressed.

The Windows skips are **11** isolated-PostgreSQL prerequisites plus the **eight**
external archive/research/production-live prerequisites. CI exercised real
PostgreSQL 17: its 12 skips are those eight external prerequisites plus **four**
Windows-only PowerShell cases. Skips are not counted as passes or real-provider
acceptance. No failing backend test was hidden behind a rerun.

## Preservation, tasks and deployment

Before edits, a recoverable private backup captured the previous source entrypoints,
compiled assets, three configurations, online SQLite backups and immutable evidence
manifest under `.local-data/scheduled-repair-backup-20261019T171117Z/`.
No active collector was found. The prior build remains available.

Preservation checks passed: **2,485 frozen files / 8,505,278,241 bytes**, original
**47 alerts**, V1 models/evaluation, **4,544** protected current market/research files,
all **331** V2 forecast bodies across 183 stores, existing account/password/personal
records and **four** protected credential fingerprints. The shared provider attempt
ledger matches its online backup. All existing capacity receipts are byte-exact.
No provider acquisition, real forecast publication, outcome reconciliation or
research-model retraining was run. Constructed regression fixtures remain TEST_ONLY.

Actual task definitions, exported again after repair, retain their original hashes:

| Task | Principal and behavior | Next actual Windows trigger | XML SHA-256 |
|---|---|---|---|
| `AlphaLens-Private-EOD-Watchlist` | Dell, Interactive, Limited, enabled/Ready; 08:30 IST | **20 October 08:30 IST** | `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419` |
| `AlphaLens-Private-NSE-Market-Research` | Dell, Interactive, Limited, enabled/Ready; 20:30/21:30/22:30 IST | **20 October 20:30 IST** | `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820` |

Both retain `IgnoreNew`, `StartWhenAvailable` and their existing battery conditions.
Both disallow starting on battery and stop on a battery transition. Execution
limits remain **10 minutes for RELIANCE / 30 minutes for the expanded task**;
the available incident evidence does not establish either limit as the initiator.
The working directory is `D:\al-research\p28-worktree` for both. RELIANCE's action
remains `scripts\windows\p30-daily-update.cmd` with the protected
`.local-data\p34-runtime\daily-config.json` argument. The expanded action remains:

```text
C:\WINDOWS\System32\cmd.exe /d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-market.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json" auto --scheduled"
```

Expanded approval-policy SHA-256 remains
`4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778`:
fixed **500** stocks, **250/run**, **600 reserved GET/run**, **1,800/day**,
**three collecting attempts/day**, minimum **60 minutes**, **31-day catch-up**.
No task XML, recurring scope, credential, quota or RELIANCE launcher was edited.

Deployment: **PASS**, idle-window promotion before 20 October. Both tasks were
Ready and process inspection found no collector. The previous compiled build and
configuration remain recoverable. Only the owned native web process was stopped
gracefully and restarted with the new frontend path; all other configuration
fields were checked unchanged. Native app PID is **28760**; PostgreSQL retained
PID **19512** throughout. The running login HTML matches the tested build and
anonymous private access returns **401**. The original native operator session
was not impersonated or reset. Account/password, personal data and credential
fingerprint checks passed again after restart.

Authenticated real saved-data browser verification used isolated QA port **8029**
with separate QA authentication and the identical compiled build. That owned QA
server was stopped gracefully afterward. Desktop/mobile screenshots and aggregate
assertions remain private under `.local-data/scheduled-repair-browser/`. No model
or portfolio body was committed. The native app remains at
<http://127.0.0.1:8017/nse-market>.

## Next real-world acceptance

**First successful fresh-session collection remains PENDING.** The repair itself
adds **zero** 19 October candles, new scores, forecasts or matured outcomes. Existing
qualified history remains 447,483 candles, saved V2 scores 300 and compatible LSTM
scores 43. No independent predictive/economic acceptance is implied.

Leave the approved tasks unchanged. Keep the Dell operator logged in and Windows
awake, connected to AC under the existing battery conditions, with protected
credentials and PostgreSQL available. The next authorized
expanded slot is **20 October at 20:30 IST**, then its approved 21:30/22:30 retries.
Inspect immutable source, quality and terminal receipts after completion; require
qualified dated candles before calling it successful. Do not manually collect to
make a task result green or refund the interrupted reservation. If an external
interruption recurs, retain new process facts and report the missing evidence;
system audit activation remains a separate operator decision.

Saved-only task inspection:

```powershell
Set-Location D:\al-research\p28-worktree
Get-ScheduledTaskInfo -TaskName AlphaLens-Private-NSE-Market-Research
.\scripts\windows\project-python.cmd -m scripts.observe_nse_task --config .local-data/full-nse-runtime/market-workflow-500.json
```

Use the [operator runbook](../operator/alphalens-runbook.md) for ordinary start/stop
and recovery. Never stop a progressing collector or PostgreSQL during collection.
