# Third approved collector cutover — 26 October 2026

Branch: `alphalens-master-completion`. Reviewed source and starting Git checkpoint:
`d940e36036fd13bdd60a81cc3e498e1f86646aee`.
Private application: **http://127.0.0.1:8041/nse-market**.

**FIXED_AWAITING_LIVE_VERIFICATION:** the exact approved market-task action was
replaced at **04:51:49 UTC /10:21:49 IST**. Post-change verification completed
at04:52:15 UTC. No rollback was needed. This establishes configuration and
offline runtime readiness; it does not establish successful live collection.
The next existing authorized trigger is **26 October20:30 IST /15:00 UTC**.
No task was manually started and no provider or clock-source request was made
for this cutover. Live observation is pending that existing trigger.

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

## Pending scheduled acceptance and conditional rollback

Read-only observation will correlate the next existing trigger with actual
worker/launcher/contained-supervisor exit, Scheduler last-run result, zero
surviving workers, fresh independent clock/continuity evidence, immutable
reservation and actual request ledger, terminal receipts and genuine market
publication. Partial data coverage will remain distinct from successful process
lifecycle. No successful run is inferred solely from a Ready task or exit0.

If a critical check fails, preserve all evidence and restore only the exact
reviewed original action, after verifying enabled idle Ready state, zero matching
workers and an action equal to the approved proposal. The operator explicitly
acknowledged that rollback restores the41-advisory runtime. Do not initiate
another cutover, manual collection, extra requests or policy changes.
