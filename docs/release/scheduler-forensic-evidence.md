# Collector scheduler forensic evidence — 25 October 2026

This is a read-only investigation of the 20:30 IST scheduled run and the
subsequent authorized rollback. It does not prove which component initiated
termination. No task, logging, power, quota, model or provider configuration was
changed, and no collector or provider request was started for this investigation.

Fresh private evidence is owner-restricted under
`.local-data/scheduler-investigation-20261025-forensics`. The reference cutover
evidence remains unchanged under `.local-data/collector-cutover-20261025-1223`.
The system/event collection used native getters and explicit UTC XPath predicates
for **25 October 14:45:00–15:20:00 UTC**. Earlier diagnostic filter queries are
retained separately; the `*-utc.json` files are authoritative for this interval.

## Meaning of the result

`2147943467` is `0x8007042B`: the HRESULT encoding of Win32 error1067,
`ERROR_PROCESS_ABORTED`. Windows' own message lookup returns
“The process terminated unexpectedly.” This is a generic termination result;
it does not identify an AC transition, a failed Python import, the component
terminated, or its initiator. Microsoft's definitions are the
[system error-code table](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-)
and [HRESULT conversion](https://learn.microsoft.com/en-us/windows/win32/api/winerror/nf-winerror-hresult_from_win32).

## Correlated timeline

All times below are UTC; add05:30 for IST. Scheduler state times are observation
times, not a claimed exact OS termination time.

| UTC | Evidence |
|---|---|
|15:00:02.675464 | Durable `LAUNCHER_STARTED`, launch `0604f0f8bc3547d1b0beb6b0fe220974`; actual Python PID16888, parent redirector26104. |
|15:00:04.869084 | Observer sees candidate `venv/Scripts/python.exe` PID26104, parent30284, and base-Python PID16888, parent26104; both match the existing protected configuration. |
|15:00:08.984109 | `WORKER_STARTED`, run `3227fd4510f3454b876e888249b9333a`. |
|15:00:12.849882 | `EOD_CAPTURE_AND_RESEARCH` stage begins. |
|15:06:14.882714 | Latest retained observation of Scheduler `Running`. |
|15:07:08.7769163 | Kernel-Power105 record334171, `AcOnline=false`. |
|15:07:10.7729574 | Kernel-Power105 record334172, `AcOnline=true`. |
|15:07:14.3840735 | Kernel-Power105 record334173, `AcOnline=false`. |
|15:07:18.0253574 | Kernel-Power105 record334174, `AcOnline=true`. |
|15:07:19.345377 | First retained observation of Scheduler `Ready`, result `0x8007042B`. |
|15:09:11.372907 | Genuine retained model-scoring timestamp;312 experimental scores for23 October observations. |
|15:09:58.692172 | Durable terminal `PARTIAL_OR_PUBLICATION_PENDING`; three actual GETs,499/500 updated, zero forecast appends. |
|15:09:58.712531 | `WORKER_FINISHED`, PID16888, worker exit0. |
|15:10:17.713175 | `LAUNCHER_EXIT`, same PID16888, exit0. |
|15:13:01.649917 | Previously authorized exact-action rollback verified. |
|15:38:09.1607879 | Fresh read-only task snapshot: original action, `Ready`, last result unchanged, next trigger16:00 UTC /21:30 IST. |

The worker and launcher execute in the same base-Python process through `runpy`;
these are separate lifecycle facts for one PID, not evidence of two independent
OS child exit statuses. The venv redirector creates the base-Python child. The
retained process snapshot establishes that hierarchy at15:00:04; it does not
establish the exit time or exit code of CMD PID30284 or redirector PID26104.
No parent-exit audit or full stdout/stderr capture for that scheduled action is
available. Durable zero exit records therefore prove the Python path returned
success later, while leaving the Scheduler-hosted parent outcome unresolved.

## Available and missing Windows evidence

| Source | Actual observation | Limitation |
|---|---|---|
| Task Scheduler Operational | Channel exists but is disabled; no matching events. | No action-start/action-finish/termination event establishes the initiator. The investigation did not enable the channel. |
| Windows Security process audit | Read denied (`UnauthorizedAccessException`). | No4688/4689 creation/termination evidence can be claimed. Command lines were not exported. |
| Sysmon | Operational channel absent. | No Sysmon process-lifetime history. |
| System log | Exactly30 events in the interval, all Kernel-Power105 AC/DC changes. | None is a Scheduler termination event. |
| Sleep/resume/reboot/service events | No matching System events in the bounded interval. | Absence in this retained interval is not proof that sleep is impossible or never occurred elsewhere. |
| Application Error / Windows Error Reporting / Application Hang / TaskScheduler / Python | No matching Application events in the interval. | No crash dump or faulting-module evidence establishes a parent/Python crash. |
| Durable collector receipts | Complete worker terminal and launcher exit0, written after first `Ready` observation. | Do not override the nonzero Scheduler result. |

There are **15 AC-to-DC and15 DC-to-AC events**, spanning15:07:08–15:16:25.
The first DC transition precedes the first observed failure by10.568seconds;
the failure time itself is bounded only by15:06:14.883–15:07:19.345.

The task retains `StopIfGoingOnBatteries=true` and
`DisallowStartIfOnBatteries=true`. Microsoft's
[documented stop-on-battery behavior](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-stopifgoingonbatteries-settingstype-element)
makes this a plausible stop mechanism. The timing is strong supporting evidence,
but no retained Scheduler/process-termination event proves that this mechanism
caused the result. A parent failure, external termination or supervisory status
failure remains possible. The patched dependency environment is not established
as the cause; the same result existed before its installation.

## Power and timeout checks

Read-only `powercfg /getactivescheme`, `/query`, `/a` and `/lastwake` report:

- Balanced power plan; automatic sleep timeout0 on both AC and DC.
- AC hibernate timeout0; DC `0x7fffffff` seconds.
- S0 Low Power Idle connected standby and hibernation are supported; S3 is not.
- Last-wake history contains one entry without an identified wake source. It
  does not date or identify a wake during the failed run.
- Task execution limit remains `PT30M`, `IgnoreNew`, restart count0,
  `StartWhenAvailable=true`, `WakeToRun=false`, and native
  `AllowHardTerminate=true` at query time.

The observed loss of Scheduler `Running` happened about7minutes after launch,
well short of the30-minute task limit. No retained event supports execution-timeout
termination. No power setting was changed.

## Preserved task definitions

The market task still executes `C:\WINDOWS\System32\cmd.exe` with the original
`run-nse-market.cmd` arguments and protected500-stock configuration. The current
market XML SHA-256 is
`a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`.
The excluded watchlist XML remains
`d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
Both exactly match the reviewed original hashes. At capture the market task was
enabled/Ready, with zero missed runs and its original next21:30 IST trigger.

## Hypothesis assessment

| Hypothesis | Assessment |
|---|---|
| Worker failed before completion | Contradicted by complete later terminal, three genuine requests, accepted RRECL candle, successful scoring and worker exit0. |
| Launcher returned without waiting for its in-process worker | Not observed: same-PID launcher exit is19seconds after worker completion. Its code directly invokes `runpy`, without detached worker creation. |
| Scheduler-hosted CMD/redirector terminated while descendant continued | Consistent with observed prematureReady and later Python completion; parent exit code/time unavailable. |
| Existing battery-stop policy responded to AC/DC transition | Strongly consistent with policy and timing, but exact initiator is unproven. |
| Task30-minute execution limit | Inconsistent with observed approximately7-minute transition; no supporting event. |
| Sleep/hibernate/reboot | No supporting event in the bounded interval; automatic sleep currently disabled. |
| Misreported status without actual parent termination | Cannot be excluded without missing Scheduler/parent process events. |
| Patched dependencies caused a crash | No supporting WER/Python event; Python actually completed0. |

The demonstrated fault is **Scheduler completion and retained Python lifecycle
disagreeing**, including genuine delayed worker completion. Offline supervision
tests can establish deterministic future parent/child behavior; they cannot
retroactively supply the missing OS termination initiator. A second cutover
requires new explicit approval, a fresh reviewed proposal/fingerprint, stable
power evidence, tested process-lifetime handling and read-only observation of an
existing authorized run. No additional task or logging modification is approved
by this report.

## Private artifact index

Within `.local-data/scheduler-investigation-20261025-forensics`:

- `System-utc.json`, `system-summary.json`:30 timestamped power records and counts.
- `Application-utc.json`: filtered application-crash query result.
- `Microsoft-Windows-TaskScheduler-Operational-utc.json`,
  `Security-process-utc.json`, `Sysmon-process-utc.json`: availability limitations.
- `log-availability.json`, `tasks.json`, both task XML exports, and
  `current-processes.json`: bounded native state; no process command lines retained.
- `power-*.txt`, `error-code-meaning.json`: power getters and local error lookup.
- `collection-metadata.json`, `collect.ps1`, `collect-events-utc.ps1`: collection
  window/method and exact read-only commands; no provider or task mutation.
- `evidence-manifest.json`: hashes of the private artifacts and referenced
  original observation/terminal/launcher evidence.

Raw private evidence remains outside Git. This document contains no credentials,
session material, provider request URLs or database connection strings.
