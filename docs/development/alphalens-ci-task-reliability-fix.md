# CI concurrency fix and read-only task diagnosis

19 October 2026; branch `alphalens-visual-overhaul`. Incident baseline:
`021c35c86a8a9a8304a70e49bc54b41c13000b74`. Software fix:
`5b2ea67e6feb707ce81a0b13cb16632a57c7586a`.

## CI root cause and exact fix

[Run 39207072908](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39207072908)
failed with **one failure, 1,461 passes and eight skips**. Its strict container
job passed. The failure was an application-side filesystem race, not a failed
SQLite transaction or evidence that the operations database was corrupt.

`OperationsStore.connection()` checked sidecar existence, then called the strict
permission verifier. Another connection could close and SQLite could remove the
WAL/SHM before that verifier finished. The POSIX verifier also called `stat()`
twice, so the file could disappear between its mode and owner reads. The trace
identifies the second `stat()` on `operations.sqlite3-wal`.
[SQLite documents last-connection WAL/SHM cleanup](https://sqlite.org/wal.html#the_wal_file).

The fix changes two production files:

- `auth/permissions.py`: use one `stat()` result for both POSIX mode and owner.
  Mode/owner requirements and Windows DACL validation are unchanged.
- `operations/store.py`: verify the directory and main database unconditionally.
  Handle `FileNotFoundError` or the Windows missing-ACL `ValueError` only around
  the two optional sidecar checks, and only continue if that sidecar is actually
  absent afterward. An existing failed sidecar still raises; permission errors
  and mandatory-path failures are never accepted.

No arbitrary sleep, retry loop, schema/journal-mode change, test skip or broad
exception suppression was introduced. Read/write SQLite URI modes, transactions,
outbox integrity and alert deduplication remain unchanged.

## Tests and CI

| Verification | Actual result |
|---|---|
| Deterministic regression against original code | Six failed / 13 passed: the four vanishing-sidecar cases and two double-stat cases exposed the defects before the fix. |
| Focused fixed checks | 64 passed: operations, auth concurrency, auth security and the 19 new regression cases. |
| Repeated original concurrency test | **100 passed**, ten independent pytest processes, ten parameterized runs/process, 62.79s. Every case retains the original eight probes / four concurrent publishers and exactly-one-alert assertions. |
| Full local Windows backend | **1,479 passed, 19 skipped**, no failures, 847.21s. Eleven PostgreSQL cases have no local test connection configured; CI runs those against isolated PostgreSQL 17. The other eight external research/live cases also skip in CI. Tests deliberately never point at the original financial database. |
| Linux/PostgreSQL 17 CI | [Foundation PASS](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39210322999): **1,490 passed, eight skipped**, 215.48s. Includes ten original concurrency repetitions plus all 19 new deterministic cases. |
| Frontend CI | [Dashboard PASS](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39210323071): **113 unit/component tests and four isolated synthetic-demo browser cases**; types, lint, both builds and npm audit pass. Frontend source is unchanged. |
| Static gates | Full Ruff/format passed; mypy passed, 385 source files. |
| Security CI | Bandit/dependency audit passed; downloaded Trivy evidence: zero HIGH/CRITICAL. Changed-range TruffleHog: zero verified/unverified findings, five scanned chunks. |

New deterministic cases cover WAL and SHM disappearance, both POSIX and Windows
exception forms, rejection of still-present failures, actual insecure POSIX mode /
Windows DACL rejection, mandatory root/database errors and single-snapshot owner
checks. The original concurrency test now repeats ten times in ordinary CI.
No market observations or production alerts are created by these TEST_ONLY cases.

Private detailed evidence: `.local-data/ci-task-race-before.log`,
`ci-task-race-focused.log`, `ci-task-race-repeat-01.log` through `-10.log`,
`ci-task-race-repeated.json`, `ci-task-backend-full.log` and
`ci-task-race-mypy.log`.

## RELIANCE interruption: what is and is not established

Actual task: `AlphaLens-Private-EOD-Watchlist`, enabled/Ready, unchanged 08:30 IST
trigger and original `.cmd` action. Last start: **19 October 11:12:39 IST**;
result **3221225786 / 0xC000013A**. Next actual trigger: **20 October 08:30 IST**.
Microsoft identifies this status as
[STATUS_CONTROL_C_EXIT](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55):
control-interrupt termination. It is not the worker's ordinary success/rejection
return code (0/1/2), and is not a successful capture.

Read-only supporting evidence:

- Kernel-Power event 507 records exit from Modern Standby at
  **11:12:38.5856459 IST**, immediately before the late task start. Event 566
  records the matching system-session transition. `StartWhenAvailable` is true;
  this is consistent with catch-up after standby, not proof of the trigger reason.
- The latest completed `daily-last-run.json` and independent clock receipt remain
  dated **18 October**. There is no new completed 19 October worker receipt.
- The shared provider ledger is unchanged at **1,498 attempts**, none since
  19 October IST midnight. No provider collection was launched to change status.
- No relevant Application Error/WER/hang event was found near that start.
  Task Scheduler Operational history is **disabled**. Consequently the initiating
  person/process and exact termination time cannot be reconstructed reliably.
  A console-control interruption is consistent with the status; attributing it to
  a particular user, task timeout, battery transition or Python exception would
  exceed the evidence.

No task edit or speculative worker change is justified by this evidence. Existing
battery restrictions remain: both tasks disallow battery starts and stop on a
switch to battery. AC power was observed online. Tonight requires the approved
logged-in operator, AC power, awake machine and network/source readiness. None
of these conditions is replaced by a green registration badge.

## Tonight's expanded task and preservation

`AlphaLens-Private-NSE-Market-Research` remains enabled/Ready, with actual next run
**19 October 20:30 IST** and unchanged 21:30/22:30 triggers. Its last result remains
267014 from the previously interrupted 18 October attempt, not a new success.
Fixed policy remains 500 stocks; 250/run; 600 reserved GET attempts/run;
1,800/day; three attempts/day; 60-minute cooldown; 31-day catch-up.

Before-inspection task-definition SHA-256:

- RELIANCE: `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`
- Expanded: `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`

Final exported task XML matches both hashes exactly
(`.local-data/ci-task-definitions-verified.json`). Prior
collection receipts and the interrupted reservation are preserved; none is reset.
No application or PostgreSQL restart, scheduler mutation, quota change, market
request, new model, forecast or frontend change was performed in this execution.
New worker processes use the verified checkout; the existing API process is not
hot-patched or restarted for this CI fix.

Preservation checks passed: 2,485 frozen files / 8,505,278,241 bytes, 47 original
alerts, original V1/V2 evidence, 23 sequence artifacts, 31 original plus 300 expanded
forecast bodies, account/password/personal records and four protected credential
fingerprints. Outcomes remain zero. Native app PID **29368** and PostgreSQL PID
**19512** remain running. Detailed private receipts are `ci-task-frozen-preservation.json`,
`ci-task-personal-preservation.json`, `ci-task-ledger-preservation.json`,
`ci-task-definitions-before.json`, `ci-task-interruption-events.json` and
`ci-task-power-evidence.json` under `.local-data/`.

The historical three unverified secret-scanner findings remain disclosed in the
existing history audit. No scanner policy, severity gate or Git history changed.
