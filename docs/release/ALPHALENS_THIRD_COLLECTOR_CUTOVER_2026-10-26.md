# Third approved collector cutover — 26 October 2026

Branch: `alphalens-master-completion`. Reviewed source and starting Git checkpoint:
`d940e36036fd13bdd60a81cc3e498e1f86646aee`.
Action-installation report checkpoint: `630d6345837f72d7df4e9fb68cac57662a79b1e9`.
The final report commit, CI artifacts and private evidence checksums are recorded
in the separate private final attestation, avoiding a self-referential Git hash.
Private application: **http://127.0.0.1:8041/nse-market**.

**VERIFIED_COMPLETE for the approved action and scheduled runtime lifecycle;
BLOCKED_EXTERNAL_DATA for fresh observations and publication.** The exact approved market-task action was
replaced at **04:51:49 UTC /10:21:49 IST**. Post-change verification completed
at04:52:15 UTC. No rollback was needed. The existing **26 October20:30 IST**
trigger subsequently ran the patched collector and exited normally. It made
251 genuine authorized API attempts but accepted zero new observations because
all250 candle responses contained empty arrays. Fresh-data collection and the
complete data-to-new-forecast workflow therefore remain unverified. No task was
manually started; the preflight and action replacement made no provider or
clock-source calls. Only the existing scheduled worker performed its normal
bounded collection and independent clock observations.

## Authority and preserved scope

The operator explicitly approved the protected plan
`.local-data/clock-gate-recovery-20261025/candidate-review-final` with SHA-256
`698a329ea7d51a4ac96acd739bf469cde937a63088c61564216e0f473236b402`
and candidate/source fingerprint
`a19e1024fd39105320358c7365dc81ed04d6672c770bc2ef16d50e213d685b7d`.
Both matched during fresh read-only verification and after the action update.
No backend/runtime/model source was changed during this operation.

Only the action of `AlphaLens-Private-NSE-Market-Research` changed. The native
`System32\cmd.exe` command and worktree working directory remain unchanged.
Arguments changed from:

```text
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-market.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json" auto --scheduled"
```

to the reviewed proposal:

```text
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-collector-isolated.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json""
```

The new wrapper pins the tested isolated Python3.12.4 runtime at
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`.
The original shared runtime remains available; there is no automatic fallback.
`AlphaLens-Private-EOD-Watchlist` is excluded and byte-for-byte unchanged.
Task principal, enabled state, triggers20:30/21:30/22:30 IST, retries, execution
limit, IgnoreNew, start-when-available and all non-action settings are preserved.
The cohort remains500,250 securities/run,600 reserved GETs/run,1800/day,
three collecting reservations/day and60-minute conservative cooldown.
Credentials, database targets, clock validation, models and forecast rules
remain unchanged.

## Read-only preflight and power rejection

The first precondition check did **not** change the action. Windows System
Kernel-Power105 recorded DC at04:40:02.4982965 UTC, record334349, and AC restored
at04:40:03.7509793 UTC, record334350. The native guard rejected
`RECENT_AC_INTERRUPTION_OBSERVED` before `Set-ScheduledTask`. A separate proof
confirmed zero action transitions, unchanged original XML and watchlist, Ready
state and zero workers. No rollback was required for that rejection.

After a new stable-power window, all read-only checks were repeated in a fresh
evidence directory. The60-second native power sample contained31 AC samples.
The mutation guard additionally required current AC and no recorded DC event
in the preceding10 minutes. No power setting or event logging was changed.

Fresh `verify-plan` completed04:48:06 UTC with `preflight=VERIFIED_COMPLETE`,
exact approved fingerprint and no provider calls. The tool's generic
`status=BLOCKED_APPROVAL` is the preparation utility's fixed non-mutating output;
the separate explicit operator grant is retained in the operation's authority
receipt. The guarded action helper independently rehashed the approved plan,
required a preflight no older than300 seconds, exact original task XML, Ready
enabled state, zero matching workers and a safe distance from the next trigger.
All post-change package integrity checks and the full fingerprint matched.

No26 October reservation existed before the update. Both25 October collecting
reservations had genuine terminal receipts and retained1200 reserved requests.
The latest22:30 run had already failed clock preflight with zero GETs and no
reservation. The unchanged19 October orphan reservation
`eff65ccb9d964e9fa8090d5b8d92bff6` still lacks a historical terminal receipt;
it is not represented as recovered. Its original checksum is preserved. Native
Ready/zero-worker evidence and the absence of current reservations establish
that no current collection was interrupted. Historical completeness is not claimed.

## Security, tests and saved-data baseline

| Check | Evidence-backed result |
| --- | --- |
| Installed candidate dependency audit | Zero advisories; fresh audit |
| Candidate integrity |15387 RECORD-verified files;15404 fingerprinted files; all checks pass |
| Targeted collector/clock/launcher replay |210 passed, warnings treated as errors |
| Candidate PostgreSQL connectivity | Read-only SELECT1 passed; zero database writes |
| Existing authenticated private application |13 saved-data endpoints returned200; unauthenticated collection-health access returned401; Top5/10/20 lengths verified |
| Old shared runtime |41 known advisories, preserved; no longer the selected market action |
| Research/alerts preservation baseline |2485 protected files and47 original alerts verified |
| Original forecasts |945 immutable bodies across187 ledgers preserved |
| Searchable identities / saved histories |3207 /500 |
| Latest retained session coverage |499/500 for23 October; SHERVANI remains missing |
| Genuine saved experimental scores |312; observation23 October, inference25 October15:09:11 UTC |
| Forecasts / unique decisions / qualified outcomes |945 /914 /0 |

The unchanged source at `d940e36036fd13bdd60a81cc3e498e1f86646aee` also
has successful foundation CI40268221179 and frontend CI40268221372, including
1822 Linux backend passes/30 skips,130 frontend passes and a strict container
scan with zero reported HIGH/CRITICAL findings. The historical secret gate
retains its raw failure183 and exact disposition of three reviewed fixtures,
zero verified secrets and zero unexpected findings; no scanner was weakened.
Those are source-checkpoint results, not a claim that a subsequent documentation
commit or an upcoming live run has already been verified.

The action-installation checkpoint `630d6345837f72d7df4e9fb68cac57662a79b1e9`
subsequently passed exact-commit foundation CI40271491848 and frontend
CI40271491853:1822 backend passes/30 skips in310.97 seconds,130 frontend passes,
dependency/static/type gates and the full historical secret disposition passed,
and the strict container scan reported zero HIGH/CRITICAL findings. That checkpoint
contains documentation changes only; the reviewed source fingerprint remains
unchanged.

These are dated saved observations, not new26 October prices or predictions.
There are zero independently accepted models; forward accuracy remains
`NOT_YET_MEASURABLE`. No collection-universe expansion or public display was
authorized. Public redistribution rights remain unresolved.

Private evidence is retained under
`.local-data/collector-third-cutover-20261026-1020`; the rejected precondition
evidence remains separately under
`.local-data/collector-third-cutover-20261026-1002`. Original XML, action intent,
operator authorization, checksummed plan, preflight, security audit, power
samples, database probe,210-test log, post-change fingerprint and reservation
accounting are retained without overwriting prior evidence.

## Actual scheduled acceptance

Run `eafeaaa1f6f44b83a82ac63fb1bf36fd` was started by the existing trigger,
not by an operator command. Its durable terminal state is
`PARTIAL_OR_PUBLICATION_PENDING`, with no error code. Times below are UTC.

| Time | Retained event |
| --- | --- |
|15:00:04 | Scheduler LastRunTime for the existing trigger |
|15:00:04.894830 | Native cmd.exe action process created |
|15:00:12.203509 /15:00:13.496276 | Isolated Python redirector and contained supervisor created |
|15:00:17.014748 | Actual child Python worker PID7152 created |
|15:00:55.201078 | Durable operational run start |
|15:01:00.473451 | Accepted independent date/clock evidence |
|15:10:06.029775 | Durable completed operational receipt |
|15:10:45–15:10:46 | Observer retained supervisor and launcher exits, both0 |
|15:10:51.304154 | Observer sealed complete lifecycle/clock/accounting verification |

The worker, launcher and contained supervisor all exited0. Scheduler subsequently
reported Ready, result0 and zero matching collector processes. Actual executable
paths and parent/child identities were observed independently of receipts.
The original watchlist remained identical and all original945 forecast bodies
remained unchanged. Scheduler Operational logging is disabled; no event-history
claim is made for that unavailable log, and logging was not enabled. Native task
status, process observations and durable lifecycle receipts provide the retained
evidence.

Clock acceptance used six samples from `time.windows.com` and `time.google.com`.
Receipt bounds were15:01:00.738268 through15:01:00.807829 UTC, width69.561 ms;
evidence age was0.000311600 seconds. The original100 ms/30-second limits, IST
date agreement, actual-worker PID7152 and process/boot continuity binding passed.
The recorded unauthenticated-NTP assumptions remain explicit. No cooldown was
required, so the refreshed-evidence-after-cooldown branch remains verified by
deterministic tests only; this run does not establish live renewal verification.

The immutable reservation is600 requests. The terminal reports251 attempts,
exactly matching the shared ledger delta4515→4766, all marked SUCCEEDED, with
no pending attempts in the after-image. Reserved capacity remaining is1200,
not1549; unused capacity inside this reservation was not recycled. No quota,
retry or collection-cadence change was made.

### Fresh-data result and precise limitation

All250 checksummed publication-attempt bodies report provider `success` with
`data.candles=[]`:250 empty responses, zero nonempty responses missing the target.
The collector correctly retained them as
`PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE`. The saved official calendar
establishes26 October as the expected completed session. Coverage is therefore
**0/500 for26 October**, with250 queried/empty and250 not queried in this bounded
batch. Current identity eligibility is500, not proof of historical tradability
for every security. The older retained session remains **499/500 for23 October**.

Zero new candles, zero new forecasts and zero outcomes were inserted. Market
publication reports `UNCHANGED_VERIFIED_DATASET`; it was not a failed write or
a new26 October price snapshot. The312 saved experimental predictions retain
their23 October observation date and25 October inference timestamp; none is
claimed as a fresh26 October prediction.945 forecast records/914 unique decisions
and zero qualified outcomes remain unchanged; forward accuracy is
`NOT_YET_MEASURABLE`.

This proves the patched runtime can execute the actual authorized scheduled
workflow, validate its clock, account for requests and terminate consistently.
It does **not** prove successful fresh-market-data delivery or500/500 coverage.
Empty responses do not establish provider publication timing, delisting or a
specific upstream cause. No new probe was made to speculate about that cause.
The next existing triggers and bounded policy remain untouched.

### Power observations and rollback decision

System Kernel-Power105 records show brief DC/AC transitions during the run,
including15:00:16.255332→15:00:18.276414 and several between15:01:41 and15:02:41.
These are retained as an unresolved power-stability risk, not proof of process
termination or a clock jump. Actual process and Scheduler exits were0. The prior
10-minute stable-power action precondition had passed when the action changed
in the morning. No power policy was altered.

**No rollback was performed:** all critical runtime identity, lifecycle, clock,
security, request accounting and preservation checks passed. Empty provider
arrays are a handled external-data condition; reverting to a41-advisory runtime
would not supply the missing observations. The patched runtime remains selected,
with zero advisories in a fresh post-run audit. The original runtime is preserved.

## Post-run integrity and remaining release gates

The read-only after-run audit completed at15:17:15 UTC. It rechecked every
original protected research file and alert, all original forecast bodies,
PostgreSQL read-only connectivity, exact task/watchlist configuration and the
complete approved candidate/source fingerprint. All checks passed:2485 research
files,47 original alerts and945 original forecast bodies are preserved. No
original runtime, model, reservation or evidence was deleted or overwritten.
The original19 October missing-terminal reservation remains explicitly unresolved.

| Gate | Verdict |
| --- | --- |
| Exact approved action, invariant settings and excluded watchlist | VERIFIED_COMPLETE |
| Actual scheduled runtime lifecycle, clock and request accounting | VERIFIED_COMPLETE |
| Patched dependency security, pre- and post-run audits | VERIFIED_COMPLETE; zero advisories |
| Original research, alerts, forecasts and local database preservation | VERIFIED_COMPLETE |
| New26 October observations and new dashboard price publication | BLOCKED_EXTERNAL_DATA;250 empty replies/250 unqueried |
| Refresh-after-cooldown branch in an actual scheduled run | FIXED_AWAITING_LIVE_VERIFICATION; offline cases pass |
| Independent model acceptance | BLOCKED_MODEL_EVIDENCE; zero accepted models |
| Qualified forward outcomes and accuracy | BLOCKED_EXTERNAL_DATA; zero qualified outcomes |
| Public market-data deployment | BLOCKED_EXTERNAL_DATA and BLOCKED_APPROVAL; rights and operator release absent |

No new cutover approval is requested: the reviewed patched action is already
active and its first scheduled lifecycle passed. The smallest next operational
step is to inspect receipts from the remaining already-authorized triggers for
genuine published candles, without manual requests or policy changes. If empty
arrays persist, obtain provider clarification using the retained response hashes,
identities, session and receipt timestamps. Any extra live probe or revised
scheduler/collection policy requires its own exact approval. Stable power remains
an external operational concern; no unsupported clock or AC-failure cause is claimed.

## Conditional rollback boundary

If a subsequent critical check fails, preserve all evidence and restore only the exact
reviewed original action, after verifying enabled idle Ready state, zero matching
workers and an action equal to the approved proposal. The operator explicitly
acknowledged that rollback restores the41-advisory runtime. Do not initiate
another cutover, manual collection, extra requests or policy changes.
