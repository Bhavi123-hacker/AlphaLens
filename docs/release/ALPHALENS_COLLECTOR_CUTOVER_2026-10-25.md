# Approved collector cutover — 25 October 2026

The operator explicitly approved only the action replacement on
`AlphaLens-Private-NSE-Market-Research`, including conditional restoration of the
reviewed original action after a critical failed check. The original
`AlphaLens-Private-EOD-Watchlist` is excluded. No manual collection, trigger,
quota, model or public-deployment change was authorized.

Approved immutable plan SHA-256:
`c91635db2a204ee4d47e08ccb44a0ae3026bffe0c76e563fb66da7d731c55a23`.
Protected plan directory:
`.local-data/operational-acceptance-20261025/cutover-approved-scope-final`.
Actual execution evidence is in
`.local-data/collector-cutover-20261025-1223`.

## Completed cutover

The action update completed at **12:30:49 UTC /18:00:49 IST**. Post-change checks
completed at **12:31:15 UTC**; the initial status was
**FIXED_AWAITING_LIVE_VERIFICATION**, without an immediate rollback.

**Final activation status: BLOCKED_SECURITY.** After the existing scheduled run,
a critical scheduler/worker lifecycle inconsistency triggered the explicitly
authorized rollback at **15:13:01 UTC /20:43:01 IST**. The exact original action
and its41 known dependency advisory records are restored. The patched candidate
is retained, with zero known advisories. Both the successful live data work and
the failed scheduler acceptance check are recorded below.

Fresh full read-only preflight matched the exact approved plan, original task
XML, all candidate/source bytes covered by the tested fingerprint, original
environment inventory, protected configuration and approved collection policy.
The original task was enabled, idle and `Ready`, well outside its next trigger.
Fresh candidate dependency audit: **zero known advisories**. The exact fixed
offline compatibility selection passed **47 cases in24.92 seconds**. A
candidate-interpreter PostgreSQL connection executed `SELECT 1` in an explicitly
read-only transaction; no database writes occurred.

One initial replay invocation named a nonexistent test file and exited before
running tests. Its log is preserved. The corrected invocation uses the reviewed
tool's `FOCUSED_TESTS` constant; no test, source or gate was altered.

Both actions retain native `C:\Windows\System32\cmd.exe` and working directory
`D:\al-research\p28-worktree`. Only the action arguments changed:

```text
BEFORE:
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-market.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json" auto --scheduled"

AFTER:
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-collector-isolated.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json""
```

The configured interpreter is now
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`.
The post-change exported definition is semantically identical to the reviewed
proposed XML; all non-action elements and attributes match the approved invariant
hash. Windows and the proposal tool serialize XML differently, so semantic
comparison and separately recorded raw hashes are distinguished.

The preserved watchlist definition is byte-identical before/after. Policy,
credentials, database targets, forecast rules, principal, enabled state,
20:30/21:30/22:30 IST triggers,30-minute execution limit, `IgnoreNew`, zero scheduler
retries,500-stock universe,250 stocks/run,600 reserved GETs/run,1,800/day and
60-minute conservative cooldown are unchanged.

Post-change package/source integrity again matched tested fingerprint
`ac15c85b392f795b447fee121c3768431a5b9ce67f6a3cc0eeccfd36532c35f6`.
The fresh clean dependency audit therefore still applies. Both runtimes remain
present. The separate watchlist/shared runtime retains **41 known advisory
records** and **BLOCKED_SECURITY**; this cutover does not clear that environment.

No approved wrapper, worker or task was manually launched. The only created
background process is a read-only observer. It captures existing task state,
worker executable/PID evidence, durable scheduled receipts, reservations,
accepted coverage and original forecast-body preservation. It neither requests
provider data nor controls the scheduler.

## Genuine existing scheduled run

The unchanged **25 October15:00 UTC /20:30 IST** trigger ran without a manual
launch. The read-only observer captured the candidate redirector PID26104 at
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`,
its base-Python child PID16888, the existing protected configuration argument,
and matching durable launcher/worker identities.

Run ID: `3227fd4510f3454b876e888249b9333a`.
Launch ID: `0604f0f8bc3547d1b0beb6b0fe220974`.

| Evidence | Actual result |
|---|---|
| Launcher start |15:00:02.675 UTC |
| Worker start / reservation |15:00:08.984 /15:00:11 UTC; **600 reserved requests** |
| Authorized provider calls |**3 actual GETs**, within600/run and1,800/day |
| Accepted new observation |**RRECL**,23 October |
| Configured-universe coverage |**498→499/500**; no evidence-qualified historical denominator substitution |
| Remaining missing security |**SHERVANI**, genuine empty/publication-incomplete response; no synthetic candle |
| Scoring |**312** genuine model outputs, regenerated15:09:11 UTC for observation23 October |
| Forecast records / unique decisions |**945 /914**, unchanged; **0 forecasts appended**,31 original overlaps preserved |
| Original forecast bodies |All **945** retained byte-for-byte by per-ledger/record hash |
| Qualified forward outcomes |**0**, `NOT_YET_MEASURABLE` |
| Durable worker terminal |15:09:58.692 UTC; `PARTIAL_OR_PUBLICATION_PENDING`; worker exit0 |
| Launcher exit receipt |15:10:17.713 UTC; exit0 |
| Windows scheduler result |**2147943467 /0x8007042B**, with premature `Ready` observed15:07:19 UTC |

The preserved shared provider ledger grew from4,510 to4,513 attempts, matching
the scheduled worker's three GETs. No manual provider call occurred. The600
reservation remains intact; it is not recycled because actual usage was lower.
Two original approved slots and1,200 reserved requests remain for the day.

The fair pending-selection repair was exercised by the real scheduled run:
previously unqueried RRECL was accepted before the already-attempted SHERVANI
retry. SHERVANI remains genuinely missing. Coverage is not500/500, and a missing
candle is not converted into an invented inactive-security exclusion.

## Critical check, power evidence and conditional rollback

Scheduler and worker completion disagree. Windows reported `Ready` with
`0x8007042B` before the worker's durable completion, and retained that result
after the worker and launcher reported exit0. The same scheduler result was
already present before cutover. The patched dependencies are **not established
as the cause**. Partial coverage alone did not trigger rollback.

Read-only System log evidence shows Kernel-Power105 records:

| UTC | IST | Record | `AcOnline` |
|---|---|---:|---|
|15:07:08.776 |20:37:08.776 |334171 |false |
|15:07:10.772 |20:37:10.772 |334172 |true |
|15:07:14.384 |20:37:14.384 |334173 |false |
|15:07:18.025 |20:37:18.025 |334174 |true |

The unchanged task has `StopIfGoingOnBatteries=true` and
`DisallowStartIfOnBatteries=true`. These power transitions immediately precede
the first observed scheduler failure. **Inference:** unstable AC and the existing
battery-stop policy are a likely external interruption mechanism. The precise
termination initiator is not proven: Task Scheduler's Operational log is disabled.
No log, power policy, battery setting, trigger or execution limit was changed.
There was also an observation gap13:40–14:32 UTC before the trigger; continuous
coverage of that interval is not claimed. The actual scheduled window has direct
process, receipt and event evidence.

The conservative conditional rollback was authorized up front and required no
second approval. It changed only the one task's action, after confirming the
worker had finished and the task was idle/Ready. Rollback was verified at
**15:13:01.649 UTC**. Data, forecasts and genuine collection receipts were retained.

| Task definition | Actual exported XML SHA-256 |
|---|---|
| Original before | `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820` |
| Installed candidate action | `12ad71c4bdafeaa84f5ea8fc3ad00d1b2791af2d14663883463d7c1747fd73ef` |
| Restored original after rollback | `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820` |
| Preserved watchlist throughout | `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419` |

All non-action invariants match throughout. Both tasks remain enabled as before;
the500-stock task is `Ready`. Its next unchanged trigger is **21:30 IST** and now
points at the original shared runtime. This restoration is explicitly recorded
as **BLOCKED_SECURITY**, never a silent fallback or security clearance.

The private dashboard remains on port8041. Its health evidence explicitly shows
the rollback, active41-advisory runtime, retained zero-advisory candidate, genuine
499/500 coverage and unmeasurable forward outcomes. No native app restart,
production migration, public exposure or cleanup was performed for this cutover.

## Final verification

After rollback, all13 authenticated saved-data HTTP checks returned200 and
unauthenticated monitoring returned401. The candidate's refreshed installed-
package security audit again reported zero known advisories. Read-only
preservation verified **2,485 protected files /8,505,278,241 bytes** and all
**47 original alerts** at15:20:28 UTC. All945 original forecast-body hashes match
the pre-run manifest. No forecast or outcome was deleted or rewritten.

No application code, dependency, frozen model or scheduler policy changed in this
delivery. The full application checks at implementation commit `ccd6293` remain
applicable; the fresh47-case candidate replay, genuine scheduled worker evidence,
database probe, security audit and post-rollback HTTP/preservation checks verify
the operational attempt separately. This report and the authorization/outcome
entry are the only tracked changes. Final delivery HEAD and evidence hashes are
pinned in the private `cutover-final-attestation.json` beside the execution logs.

## Remaining gates

1. **BLOCKED_SECURITY:** the restored shared runtime retains41 advisory records;
   the zero-advisory candidate is available but not active. The separate original
   watchlist was never switched.
2. **BLOCKED_EXTERNAL_DATA:** establish stable AC power and resolve the observed
   scheduler/worker lifecycle inconsistency before another acceptance attempt.
   A fresh preflight is required. Any change to battery policy, logging or other
   task settings requires scope beyond this action-only approval.
3. **BLOCKED_EXTERNAL_DATA:** obtain a genuine SHERVANI target candle or dated
   source/listing/tradability explanation. Its eligibility denominator remains
   unknown; no extra provider request is authorized by this report.
4. **BLOCKED_MODEL_EVIDENCE / BLOCKED_EXTERNAL_DATA:** independent model
   acceptance, genuine matured outcomes and public data rights remain separate.

No accuracy or profitability claim follows from this change. There was no manual
retry, quota increase, model fit, deletion of either runtime, live-policy change
or public deployment.
