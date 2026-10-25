# Scheduler root cause and recovery — 25 October 2026

Branch: `alphalens-master-completion`. Starting commit:
`5f4d1fcf04e40c319bd4b4983e52205e21bbea90`.
Private application: **http://127.0.0.1:8041/nse-market**.

The original task action remains restored and unchanged. This investigation
starts no collector, provider request or second cutover. Its new process tests
run only explicitly constructed TEST_ONLY programs. The candidate containment
path is inactive until a new hash-bound plan receives explicit approval.

## Result and evidence limits

`0x8007042B` /2147943467 is HRESULT-wrapped Win32 error1067,
`ERROR_PROCESS_ABORTED`, meaning an unexpectedly terminated process. This generic
result identifies neither the process nor the termination initiator. See the
[Microsoft error table](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-)
and [HRESULT encoding](https://learn.microsoft.com/en-us/windows/win32/api/winerror/nf-winerror-hresult_from_win32).

The incident demonstrates disagreement between Scheduler completion and actual
Python lifecycle. The precise initiating cause remains **BLOCKED_EXTERNAL_DATA**.
The strongest supported external hypothesis is an AC-to-battery transition
interacting with the unchanged stop-on-battery policy. This is an inference,
not a proven termination event. No dependency crash, worker failure, timeout or
sleep event explains the retained evidence.

[The forensic report](scheduler-forensic-evidence.md) contains the full timeline,
native query methods, availability limits and protected artifact index. Raw
evidence remains in `.local-data/scheduler-investigation-20261025-forensics`.

| UTC on25 October | Actual evidence |
|---|---|
|15:00:02.675 | Launcher starts; base Python PID16888, parent venv redirector26104. |
|15:00:04.869 | Observer captures redirector26104 with parent30284 and base child16888. |
|15:00:08.984 | Worker starts in the same base-Python process. |
|15:06:14.883 | Last retained observation of Scheduler `Running`. |
|15:07:08.777 | Kernel-Power105: AC offline. |
|15:07:10.773 | AC online. |
|15:07:14.384 | AC offline again. |
|15:07:18.025 | AC online again. |
|15:07:19.345 | First observed `Ready` with0x8007042B. |
|15:07:38.803 | Genuine SHERVANI empty-response receipt, after prematureReady. |
|15:09:11.373 |312 experimental scores generated from23 October observations. |
|15:09:58.692 | Durable partial/publication-pending terminal;3 actual GETs,499/500. |
|15:09:58.713 | Worker-finished diagnostic records exit0. |
|15:10:17.713 | In-process launcher records exit0. |
|15:13:01.650 | Previously authorized exact-action rollback verified. |

The worker and launcher use `runpy` in one PID. Their diagnostic exit0 records
are not independently observed exit codes for CMD and the venv redirector.
The actual parent exit times/codes are unavailable. The lastRunning/firstReady
observations bound the transition to64.463seconds; they do not locate its exact
instant. Original stdout/stderr was not captured for the action, and cannot be
retroactively recovered from exit diagnostics.

Task Scheduler Operational logging was disabled; this investigation leaves it
disabled. Security process-audit access was denied; Sysmon was absent. The
explicit-UTC System query found30 events in14:45–15:20 UTC, all AC/DC transitions,
and no sleep/resume/reboot/service event. There was no matching Application
Error, Hang or Windows Error Reporting event. The30-minute execution limit does
not explain a transition roughly7minutes after launch.

Microsoft documents that
[StopIfGoingOnBatteries](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-stopifgoingonbatteries)
stops a task when the machine switches to battery. Both that setting and
`DisallowStartIfOnBatteries` remain true. Neither policy nor any power or logging
setting was altered. The timing supports the hypothesis without proving that
Scheduler invoked this policy during the incident.

## Candidate-only software repair

The active launcher already waits synchronously for its in-process worker.
Changing it to add an ordinary Python `wait()` would not repair the observed
ancestor-lifetime gap. The old path does not explicitly contain worker
descendants or monitor the Scheduler-hosted CMD ancestor.

The inactive isolated wrapper now selects `supervised_launcher`, which retains
the existing scheduled worker and all approval, clock, data, model, reservation,
cooldown and forecast logic. Its Windows-only supervisor:

1. Identifies the native Windows CMD ancestor, accounting for the venv redirector,
   and retains a synchronization handle rather than repeatedly trusting a PID.
2. Creates a private kill-on-close Job Object and supplies job membership during
   suspended worker creation using `STARTUPINFOEX` /`PROC_THREAD_ATTRIBUTE_JOB_LIST`,
   then resumes it. Failure to establish containment
   prevents collection; there is no uncontained fallback.
3. Waits for the actual contained worker and propagates its exit code. On observed
   ancestor loss it terminates contained work before recording interruption.
4. Uses non-inherited native handles so abrupt supervisor death closes its sole
   job handle and Windows terminates its contained descendants.
5. Preserves interrupted/missing-exit evidence. A killed process cannot promise
   to write a terminal receipt; absence remains incomplete evidence. Existing
   durable reservations are never cleared to authorize a retry.

These mechanisms follow Microsoft's
[Job Object process-containment semantics](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
Native process creation keeps suspension, membership and handle cleanup explicit.
No scanner exclusion or severity reduction is introduced.

The creation-time attribute closes the user-mode gap between creating a suspended
child and assigning it to a job. A deterministic test terminates the supervisor
immediately after the native creation call returns, before attribute cleanup or
resume, and verifies the suspended child dies without executing its body.
The attribute requires Windows10 /Server2016 or later; unsupported systems fail
closed. See Microsoft's
[process attribute reference](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
This is not a claim about every possible interruption inside the OS implementation
of a native API, or a substitute for actual Scheduler-hosted verification.

The original `launcher.py`, `run-nse-market.cmd` and `project-python.cmd` remain
unchanged. No existing live task selects the new candidate supervisor. The
read-only cutover tool now requires exactly `Ready` and zero matching collector
processes; `Running`, `Queued`, `Disabled`, unknown/empty states, surviving workers
and missing process-count evidence are rejected. Its bound offline selection
includes the new lifecycle tests.

## Verification and fresh readiness

The final atomic-creation source passed **72 bound offline cases in23.56seconds**
under the patched interpreter. Installed-package and source fingerprints matched
before and after those tests. All four frozen-lock, base-interpreter, package-
version and installed-RECORD checks passed. The measured candidate/source
fingerprint is:

`e4dd5159e7716ba61803d914c1cce9d2776ee832f6c5afc346fb6e68ef46d084`.

The protected source-bound proposal is
`.local-data/scheduler-recovery-20261025/candidate-review-atomic-final`.
It deliberately reports **BLOCKED_SECURITY** for applying a cutover while the
unchanged21:30 IST run is active: native getters report `Running` and two matching
Python processes. All candidate integrity and test gates passed. This is not a
claim of an idle cutover preflight. Any subsequent idle-state proposal/check is
recorded separately in the final private attestation; the immediate pre-apply
preflight must always be repeated under new explicit approval.

| Fresh verification | Actual result |
|---|---|
| Bound candidate collection/launcher/preflight replay |72 passed,23.56s; no provider requests |
| Native Windows lifecycle cases within that selection |17; actual TEST_ONLY process termination, descendants, restart and lock recovery |
| Full repository Ruff and formatting |Passed;766 Python files already formatted |
| Full strict Windows-target mypy |Passed;434 source files |
| Strict Linux-target typing of new modules/tests |Passed;3 source files |
| Full unchanged core Bandit gate and final launcher scan |Passed; no new suppression or scanner reduction |
| Candidate installed dependencies |102 packages; zero known advisories |
| Candidate PostgreSQL and private app |Read-only connection passed; six authenticated endpoints200, unauthenticated monitoring401 |

The native cases cover normal completion, exit17 failure propagation, delayed
descendants, supervisor/ancestor hard termination, interrupted worker restart,
real lock exclusion/recovery, unknown/dead ancestry, interrupt130, argument
preservation, failed creation attributes and blocked diagnostic writes. They also
reproduce the original uncontained worker surviving CMD termination. Tests never
load a real collector or contact a provider. They do not equate controlled process
lifecycles with an actual Task Scheduler execution; no task was created or
triggered for testing.

The initial Linux-target type check identified two Windows-only `ctypes` names;
explicit platform-API typing fixed this without ignore directives. Superseded
source-audit attempts and all their passing/failing gate results are retained;
only the final frozen source identity applies to the current candidate.

Existing fresh checks:23 cutover-tool cases passed,32 existing collection fault/
restart/publication/diagnostic cases passed. The installed candidate audit found
zero advisories across102 packages. Candidate PostgreSQL connectivity passed
inside an explicitly read-only transaction. Six authenticated saved-data HTTP
checks returned200; unauthenticated monitoring returned401. Protected preservation
again verified2,485 files /8,505,278,241 bytes and47 original alerts at15:44:14 UTC.

Private new verification receipts are retained under
`.local-data/scheduler-recovery-20261025`. Final delivery HEAD and CI artifacts
will be pinned in that directory's final attestation after commit and verification.

## Current task, rollback and data

The active market action still uses native `cmd.exe` and
`run-nse-market.cmd PRIVATE_CONFIG auto --scheduled`. It resolves to the
original shared runtime, with41 known dependency advisory records. The retained
patched candidate has zero. Active collector security therefore remains
**BLOCKED_SECURITY**, despite candidate dependency checks passing.

The original market XML hash remains
`a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`.
The separate untouched watchlist remains
`d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
Triggers, enabled state, retries, execution limit,500-stock cohort,250/run,
600 reserved/run,1,800/day, credentials and database/forecast targets are retained.
Both runtimes and the exact rollback action remain available.

The independent read-only15:58:25 UTC check confirmed exact original task XML,
zero matching collector processes at that time, all945 original forecast bodies
unchanged and945 total records. The already-authorized21:30 IST trigger later
started on the original runtime; this investigation neither started nor stopped
it. At16:03 UTC its actual state wasRunning, not an idle verification claim.

[SHERVANI's complete saved evidence](shervani-session-evidence.md) establishes
ISIN`INE011D01013`, provider key`NSE_EQ|INE011D01013`, token764890 and last accepted
candle19 October. Three23 October attempts have genuine empty arrays. No dated
session-tradability, suspension, delisting or exhaustive action evidence explains
the absence. Coverage remains499/500; the historical eligible denominator is
unknown.500/500 cannot be demonstrated from retained valid observations.

## Conditions for a second cutover

1. Review the new candidate source, passing native lifecycle tests and new
   protected plan/fingerprint. The previously approved plan
   `c91635db…c55a23` /fingerprint`ac15c85b…c35f6` cannot authorize changed bytes.
2. Establish stable AC for the collection window. Obtain separately authorized
   Scheduler/process logging if the operator needs the precise termination
   initiator; this investigation does not enable logging or weaken battery policy.
3. Require fresh candidate dependency, interpreter/RECORD, database, quota,
   protected-config and task-integrity checks immediately before any action.
   The original task must be enabled, idle and exactlyReady.
4. Obtain **new explicit operator approval** for the exact revised action-only
   plan and conditional exact-action rollback, acknowledging restored41-advisory
   runtime risk. Preserve the excluded watchlist.
5. Change no trigger or quota and do not run the collector manually. Observe the
   next existing authorized run: Scheduler completion must agree with contained
   worker lifecycle, and genuine receipts must establish accepted data and actual
   request use. A controlled stub test cannot establish live acceptance.

SHERVANI source evidence, independent model acceptance, zero qualified forward
outcomes and public market-data rights remain separate gates. No forecast,
accuracy, price or successful future run is fabricated by this recovery work.
