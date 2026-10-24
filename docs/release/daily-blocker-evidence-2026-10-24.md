# Daily collection blocker evidence, 24 October 2026

| Scope | Status | Evidence |
|---|---|---|
| Read-only diagnosis command and offline reliability regression | VERIFIED_COMPLETE | `scripts.nse_collection_status` and 42 targeted passing tests |
| Derived dashboard publication recovery | FIXED_AWAITING_LIVE_VERIFICATION | Completed-source replay retries a failed/missing/stale publication with zero provider GETs; successful matching publication remains unchanged |
| Native Windows task display timezone | VERIFIED_COMPLETE | Corrected local COM wall times; native read-only query now agrees with independent PowerShell task getters |
| Reliable current 500-security session coverage | BLOCKED_EXTERNAL_DATA | Last retained session is 21 October, 248/500; no complete newer collection evidence |
| Additional requests or live task changes | BLOCKED_APPROVAL | None performed; existing exact cohort, cadence, cooldown and request ceilings retained |

The original authenticated port 8041 deployment was not stopped, restarted or
reconfigured by this task. No provider calls, clock-network requests, scheduler
changes, model fits, source-record edits, forecast edits or cleanup occurred.

## Observed failure chain

Saved immutable terminal receipts show two evening attempts on 21 October:
`e71cb300c51841b5a1fde1df098ae04e` made 251 GET attempts including timing;
`a6f8d0cd575c49528440e964765702b6` made 250. Their successful candle replies were
empty. Both selected the oldest missing batch; 500 candle attempts do not prove
that all 500 distinct securities were queried. The source policy deliberately
keeps empty responses retryable, rather than freezing them as accepted absence.

The 22 October catch-up run `69d81cf9042348269f5d838fee01b4a2` made 499 GET
attempts and retained 248 of its 250 requested securities for 21 October. Its two
remaining replies were classified
`PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE`. The other 250 cohort members
also lack that session. A provider success response is distinct from a validated
accepted candle.

Official saved timing bodies establish that 21 October was an NSE session. The
next morning's nonempty replies support delayed publication or endpoint
availability for those 248 observations. They do not establish the exact release
time, explain all 252 missing slots, prove suspension/no-trade status, or qualify a
different endpoint. The historical daily endpoint remains unchanged. Any
intraday-daily endpoint qualification needs separate bounded acquisition approval.

The latest worker terminal, `42b4d2a204384900bbea63a78b82a259`, failed at
`PREFLIGHT` on 22 October 23:42:26 IST with
`DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`, zero provider attempts and no collecting
reservation. No timestamp or independent-clock condition was relaxed.

Read-only Windows inspection during this task finds the expanded task Ready,
last start 23 October 22:50:33 IST, result **3221225786 / 0xC000013A**, next start
24 October 20:30 IST. That control-interruption result and the missing newer
terminal evidence do not identify a termination initiator. Earlier launcher
diagnostics and strict worker guards remain in place. A task state, planned next
start or successful HTTP response cannot certify source acceptance.

Only official timing files through 22 October are retained. Current expected
session determination is therefore explicitly unavailable: official facts for
23 and 24 October are missing. The command reports the latest saved completed
calendar fact separately from the latest retained price session; it does not
infer exchange trading days from weekdays or prices.

The full source replay printed **248 accepted / 252 missing** for the latest
retained session: **250 not queried for that session**, **two publication
pending**. Shared quota storage contains **3,505 SUCCEEDED attempt records**:
**501 on 21 October**, **501 on 22 October**, and none on 23/24 October at this
read. The expanded worker's available terminal receipts report **2,007** lifetime
attempts; its immutable lifetime reservations total **4,200**. Those totals have
different scopes and are not interchangeable. Pending intents, if present, would
not prove HTTP completion. The saved forecast snapshot remains **302 candidates
observed 19 October**, mismatched to the current retained dataset/session.

## Concrete software defect repaired

`workers/nse_market/daily.py` previously returned immediately on a fully observed
session. If its final accepted batch survived but the derived
`saved_market.publish` stage failed, every following replay skipped publication.
The dashboard could remain stale indefinitely despite accepted source records.
This is a demonstrable recovery defect; it is not asserted to be the cause of the
21 October provider empties or the later Windows interruptions.

The fully observed replay now calls a bounded publication helper after source
verification and reconciliation. An existing matching dataset is a no-op. A
missing or older derived dataset is published from the already verified frame.
A partial accepted batch also recovers publication when its next collection
attempt retains zero new rows; recovery adds no provider requests.
A corrupt pointer/checksum remains a reported failure. Failure recovery never
calls the provider, recreates source records, manufactures a new forecast, changes
an original record, or bypasses official session/clock checks. The operational
wrapper retains its normal terminal receipt, including the recovery result.

The change is software verified. Actual collection reliability remains subject to
genuine future receipts; no new collecting run was triggered for this campaign.

An independent display defect was found by comparing the new native task read
with PowerShell's existing task getters: COM Automation timestamps attach a UTC
wrapper to local wall-clock fields in this environment. Treating that wrapper as
the event zone displayed a 20:30 IST trigger as 20:30 UTC. The monitoring reader
now interprets those fields using the Windows local timezone before UTC
serialization. A fresh native read returned **last start
2026-10-23T17:20:33+00:00**, **next trigger
2026-10-24T15:00:00+00:00**, matching **22:50:33 IST / 20:30 IST** from PowerShell.
Deterministic tests cover misleading attached UTC/local/no timezone wrappers and
both summer and winter daylight-saving rules. This repair affects task display
metadata only; raw market timestamps, source acceptance and independent clock
gates are untouched.

## Read-only operator command

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m scripts.nse_collection_status --root .local-data/nse-market-expansion --provider-root D:/al-research/p28-runtime/provider-state --observe-windows
```

This command performs full saved source-lineage replay, which can take several
minutes on a cold Windows disk. It is an explicit diagnostic, not a page-load
operation. It writes nothing itself and imports no acquisition credentials. Its
optional Windows query uses getters only and preserves an explicitly stale saved
fallback if the native query is unavailable.

It prints expected qualified session or missing calendar dates, latest retained
session, full-cohort accepted/missing counts, per-security missing reasons,
shared-account actual attempt counts, per-run terminal counts, reserved capacity,
unfinished reservations, last run with at least one accepted observation, next
scheduled start with observation freshness, and forecast freshness. Shared
attempts include other clients; workflow reservations are never equated with
actual GETs. An accepted-observation run is explicitly not a claim of full-cohort
success. Complete daily success rates remain unavailable without a complete
qualified expected-session/run series.

## Exact offline verification

```powershell
& .local-data/completion-runtime/venv/Scripts/python.exe -m pytest tests/unit/test_nse_market_operational.py tests/unit/test_nse_monitoring.py tests/unit/test_nse_process_diagnostics.py tests/unit/test_nse_daily_market_publication.py tests/unit/test_nse_collection_status.py -q --basetemp D:/al-tests/daily-blockers-final42-20261024
```

Result: **42 passed in 14.36 seconds**. Fixtures are explicitly TEST_ONLY and make
no provider requests. Cases cover existing independent-clock/cooldown/quota and
launcher protections, missing terminal reporting, source/calendar strictness,
attempt versus reservation accounting, filesystem-preserving status reads,
stale forecasts, and both missing-view and stale-view publication recovery.
Recovery retains zero GETs and zero additional model score invocations; a second
replay keeps the matching publication unchanged.

The first added partial-batch regression had 41 passes and one failure because
its 2025 fixture used the real 2026 clock when reloading a cached future calendar.
The test now freezes its own display clock at the declared TEST_ONLY fixture time;
the production seven-day calendar refresh guard was preserved. The final complete
42-case run above passed.

Focused Ruff lint and format checks passed for all seven changed Python files.
Strict mypy passed on those seven source/test files. The broader release's
exact-commit CI/security and deployment
verification are recorded separately in the final release report.

## Remaining concrete actions

1. Preserve exact 500-stock/250-per-run/600-reserved-per-run/1,800-per-day policy.
   Do not clear interrupted capacity reservations.
2. Obtain genuine independent clock evidence for any future approved run; diagnose
   failures without widening acceptance conditions.
3. Preserve launcher and Windows event facts for the next interruption. Current
   evidence cannot identify its initiator; enabling new audit settings or changing
   the live task is outside this task's authorization.
4. Qualify any alternative current-day publication endpoint only after exact
   bounded provider-call approval. The repaired offline presentation stage does
   not establish provider publication behavior.
5. Evaluate subsequent unchanged scheduled runs against accepted per-security
   source records and genuine terminal receipts. Keep missing dates/securities
   explicit until new qualified evidence exists; do not backdate forecasts after
   their entry time has passed.

## Final parent integration check

The parent review also covers unchanged candles with a newly advanced verified
score pointer: replay compares the embedded score snapshot as well as dataset ID
before declaring the view unchanged. This prevents a failed score publication
from staying stale without acquiring data or invoking inference again.

The final combined focused command ran the five reliability modules above and
`tests/unit/test_secret_history_review.py`: **63 passed in 9.00 seconds**,
comprising **44 reliability/publication/monitoring cases and 19 secret-gate cases**.
Full strict mypy passed **410 source files** after this change. The earlier
42-case evidence remains valid for its explicitly stated scope.
