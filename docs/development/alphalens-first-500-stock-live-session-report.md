# First 500-stock live-session verification

## INTERIM live verification — 19 October 2026, 22:00 IST

**Verdict: `FINAL_SCHEDULED_RUN_PENDING`.** This supersedes the current-state
claims in the preserved 18 October preflight below. Baseline:
`e934d980e70be89a27231b9f906590a4c10a4487`, branch
`alphalens-visual-overhaul`. This inspection made **zero provider requests**,
started no collecting worker, and changed no task, quota, service or credential.

### 1. Current time and scheduled run status

Windows observations between 21:50 and 22:00 IST show:

| Slot | Result | Evidence |
|---|---|---|
| 20:30 | NOT RUN in retained worker evidence; Windows execution unconfirmed | No start/completion receipt or source reservation for this slot. Task Scheduler Operational history is disabled, and LastRunTime now refers to 21:30. Absence of a receipt cannot rule out termination before the receipt stage. |
| 21:30 | INTERRUPTED | Windows LastRunTime 21:30:00, LastTaskResult **3221225786 / 0xC000013A**. Run `eff65ccb9d964e9fa8090d5b8d92bff6` started at **21:30:26.938623 IST**, reserved at 21:30:29, and has no completion receipt. No collecting worker/descendant remains. Termination time and initiator are not established. |
| 22:30 | PENDING | Exact next trigger read from Windows: **19 October 22:30 IST**. It has not occurred at this verification. |

Both tasks are enabled, **Ready**, Dell/Interactive/Limited, `IgnoreNew`, and
`StartWhenAvailable`. Expanded action, working directory and all three triggers
match approval; only one expanded collecting task exists. RELIANCE remains
08:30 IST; its last start was **19 October 11:12:39**, result **0xC000013A**, next
**20 October 08:30**. The earlier RELIANCE interruption's initiator remains unknown.
Neither a Ready state nor a scheduled trigger demonstrates capture success.

Task XML SHA-256 values match the pre-inspection baseline:

- RELIANCE: `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
- Expanded: `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`.

Windows System evidence records a Modern Standby exit at 20:24:06, reason Lid;
it does not explain either slot's termination. At inspection the machine was on
AC, battery 100%. Both installed tasks disallow battery starts and stop on battery;
these existing settings were not changed. No related Application Error/WER event
was found in the inspected evening window. Lack of task history prevents assigning
a definitive termination cause.

### 2. New 19 October qualified data

| Measure | Actual count |
|---|---:|
| Target securities | **500** |
| Successfully updated / already verified for 19 October | **0 / 0** |
| Still pending, without an eligible 19 October observation | **500** |
| New qualified 19 October candles | **0** |
| Confirmed source-publication-pending responses | **0** |
| Quality-rejected / action-excluded new observations | **0 / 0** |
| Observed authentication / rate-limit failures | **0 / 0** |
| Securities stopped by request-budget exhaustion | **0** |
| Awaiting a future authorized attempt | **500** |

These are not 500 confirmed provider publication failures: **no candle GET was
reached**. There is no `daily/2026-10-19` capture directory, publication-attempt
receipt, accepted response, or per-security completion record. Missing observations
remain `NO_ELIGIBLE_OBSERVATION`, retry pending; HTTP success for metadata cannot
upgrade them. New-session candle storage growth is **0 bytes**.

Checksum-validated source reconstruction still yields **500 securities,
447,483 qualified candles**, 3 January 2022–16 October 2026. Six additional source
candles remain quarantined for 26 April 2025. There are **499** retained 16 October
rows. SHERVANI (`NSE_EQ|INE011D01013`) still ends on **15 October**, with 36
observations; neither its missing 16 October candle nor a 19 October candle exists.
The existing missing-first algorithm prioritizes it but accepts genuinely available
newer target-session observations without requiring an invented 16 October fill.
No recovery was run to test its actual publication tonight.

The one completed metadata request refreshed the identity snapshot at
**21:30:34.690458 IST**: **3,198** verified current common equities. All 500 configured
keys remain present, with zero ISIN/segment mismatches. This is identity discovery,
not candle delivery. Raw master hash:
`d6670c143b6e6e4b0260e9f6fec2decf0e2c979b3c4b9d2df3cc729cf265a38d`.

The saved official timing fact specifies 19 October **09:15–15:30 IST**; its raw
hash remains `eece364a6538548c2f02e788dc74877f97c1631ffbad055d2a5b3933f2988477`.
The run's independent receipt bounds were 21:30:29.610528–21:30:29.664385 IST,
state `INDEPENDENT_DATE_BOUNDS_AGREE`, with the unauthenticated NTP limitation
preserved. Neither calendar timing nor clock agreement proves EOD publication.

### 3. Provider usage

- **1 actual recorded GET today**, 21:30:30.087360 IST, `SUCCEEDED`: identity
  master refresh. **0 candle/action GETs**, **0 accepted new candles**.
- Shared ledger: **1,499 lifetime attempts**, all recorded `SUCCEEDED`; the prior
  1,498 attempts and interrupted 18 October run's five GETs remain preserved.
- **600** expanded-workflow reserved GET attempts today, one started run.
  **1,200** remain under the daily reservation ceiling; reservations are not GETs
  and the interrupted run's 600 are not refunded. Only the remaining **22:30 slot**
  may collect tonight, with its existing **600 GET / 250-security** limit.
- Fixed policy remains 500 securities, 250/run, 600/run, 1,800/day, three
  attempts/day, 60-minute cooldown, 31-calendar-day catch-up. Policy hash remains
  `4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778`.
- One request is below the existing shared 50/second, 500/minute and
  2,000/half-hour guards. No overlapping collecting worker or extra reservation
  was found. The audit sent no market request and reset nothing.
- The next run's independent **lower** bound must be at least
  **22:30:29.664385 IST** to satisfy the unchanged cooldown. Startup/NTP timing
  may make a nominal 22:30 trigger arrive too early at that guard. This is a risk
  to inspect in its actual result, not grounds to bypass the guard or move the task.

With zero completed securities and only one 250-security slot remaining, **full
500-security fresh-session coverage cannot be completed tonight under this policy**.
Later authorized runs can perform bounded catch-up; their success is unobserved.

### 4. ML workflow

| Measure | Actual result |
|---|---|
| Eligible new 19 October feature vectors | **0** |
| New-session V2 / LSTM inference results | **0 / 0** |
| Existing V2 scores | **300**, observation **16 October**, generated **18 October 16:35:57.246229 IST** |
| Existing compatible LSTM scores | **43**; original sequence evidence unchanged |
| Genuine new forecasts | **0** |
| Preserved forecasts | **31 original + 300 expanded = 331**, byte-exact bodies across 183 ledgers |
| Matured outcomes | **0**, checked across all original/expanded ledgers |
| Accepted models / accepted rankings | **0 / 0** |

Pinned model reload reproduced all 300 saved scores with maximum absolute
difference **0.0**; recomputed ordered feature vectors also differ by **0.0**.
This is reproducibility of 16 October inputs, not fresh-session inference. No
new input was eligible because acquisition did not reach candles. All 23 saved
sequence files remain byte-exact. Two global cohort declarations reference the
same 300 unique expanded forecasts; they are not 600 independent forecasts.
The first eligible opening being dated 19 October does not mature five-session
outcomes or establish that an opening price was actually captured.

### 5. Dashboard

**PARTIAL operational-monitoring correctness; saved research works.** At
21:58 IST the authenticated compiled browser on isolated **8029**, using the same
compiled index as native **8017**, verified:

- Current identity search, saved stock evidence, exact backend/saved-score
  alignment for **Top 5, Top 10 and Top 20**, 300 scored securities, and 447,483
  candles ending **16 October**. No 19 October success is shown.
- After the observer fix below, the task panel displays **21:30**, result
  **3,221,225,786**, **22:30 next trigger**, and **600 reserved** today.
- Zero provider acquisition requests, zero attempted refresh paths, zero page
  errors. Private screenshots: `.local-data/live-500-browser-20261019/`.
- Native 8017 login page returns 200 and anonymous private research returns
  401. An authenticated original-operator session was unavailable; this is **not**
  a claim of original-operator authenticated browser verification on 8017.

Two existing presentation limitations remain explicit: “GETs in last saved run”
is **0 from the 18 October recovered result**, not today's actual GET count of one;
the completed-result pointer does not incorporate the unfinished 21:30 run.
Also, latest-session coverage cards compute over the paginated shortlist
(**5/5** in Top 5), rather than the full retained cohort (**499/500** for 16 October).
Those cards must not be read as 500-stock completion or current-day usage.
No frontend/backend deployment was performed during the collecting window.

### 6. Problems, safe fix and verification

1. **Interrupted collection:** 21:30 stopped after metadata refresh, before EOD
   capture. `0xC000013A` establishes control interruption, not who caused it.
   No completion/exception receipt or task-history event establishes the initiator.
   Preserve evidence and let the next authorized slot run; do not manually retry.
2. **Unconfirmed 20:30 execution:** task history is disabled and no worker evidence
   survives for that slot. Do not invent its start, completion or failure cause.
3. **Reproduced observer defect, fixed safely:** `scripts/observe_nse_task.py`
   converted Windows `LastTaskResult` to signed PowerShell `[int]`, which overflows
   for **3221225786**. Its real read-only query failed before storing new task facts.
   Use **`[long]`**, preserving the exact unsigned 32-bit value as JSON/Python int.
   Extract the fixed query for testing; retain fixed task name, no shell input,
   no task mutation, no acquisition and original checksum/policy validation.
   Running the repaired observer appended one checksummed task observation with
   zero provider GETs; both actual task definitions remain byte-exact.
4. **Monitoring limitations:** old completed-run GET count and paginated coverage
   described above remain. Repair deployment is deferred; these are not collection
   success evidence. No source, quota, forecast or financial rule was changed.
5. **Remaining live prerequisites:** 22:30 must clear clock/cooldown, remain
   uninterrupted, and receive valid source-published candles. At most 250 securities
   can then complete; missing candles and model exclusions must remain explicit.

Verification: **75 focused tests passed**, warnings treated as errors (task observation,
operational engine, market evidence, cohort forecasts, stock history and EOD clock).
An earlier 65-case subset also passed; these counts are not added together.
The observer's four Windows
PowerShell cases exercise **0, 267014, 3221225786 and 4294967295**, with TEST_ONLY
functions shadowing both scheduler cmdlets. The real observer subsequently succeeded
against the unchanged installed task. Ruff/check/format and targeted mypy passed.
The first pytest invocation had an invalid short-temp-root environment, and a later
command named a nonexistent daily-test file; neither ran tests. Corrected explicit
test selection and `D:\al-tests` were used. No failing test was skipped.

Preservation: **2,485 frozen files / 8,505,278,241 bytes**, **47 original alerts**,
V1 model/evaluation, all original forecast bodies, 240 additionally protected files,
four Credential Manager fingerprints, original account/password hash, personal
records and protected configurations match their baselines. Source snapshot replay
found no changed files during inspection. Native app PID **29368**, PostgreSQL
PID **19512** stayed running; neither was stopped/restarted. Only this inspection's
failed QA-browser process tree was cleaned after a premature loading assertion;
the corrected browser waits for loaded saved evidence and then passed.

Security: no dependencies, authentication, model loading or scanner policy changed.
Baseline [foundation CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39211760114)
and [frontend CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39211760102)
passed. Their strict container result was **zero HIGH/CRITICAL**, not a new local
rescan today. An additional direct low-severity script scan reports the three
existing subprocess-import/fixed-executable/subprocess-call warnings; none was
suppressed. The three historical unverified secret findings remain disclosed;
no new full-history scan or history rewrite is claimed. Change CI is reported
separately when available; baseline CI is not a pass for untested changes.

Private audit: `.local-data/live-500-interim-audit-20261019.json` records checksums,
per-session counts, quota timestamps and forecast preservation. Market-data bodies,
credentials, private screenshots and financial records are not committed.

### 7. Final verdict

**`FINAL_SCHEDULED_RUN_PENDING`** — this is an interim report before 22:30, not a
successful first live session. Genuine progress was a refreshed identity master;
there was **no fresh-session candle, inference or forecast progress**.

### 8. Next action

Keep the operator logged in, the machine awake and on AC. **Wait for the existing
22:30 attempt.** Do not start another run, reset quota, interrupt a worker, restart
services or edit a scheduler definition. After Windows reports that attempt no
longer Running (no assumed completion minute), use these read-only commands:

```powershell
Set-Location D:\al-research\p28-worktree
Get-Date -Format o
Get-ScheduledTask -TaskName AlphaLens-Private-NSE-Market-Research | Get-ScheduledTaskInfo | Format-List LastRunTime,LastTaskResult,NextRunTime
.\scripts\windows\project-python.cmd -m scripts.observe_nse_task --config .local-data/full-nse-runtime/market-workflow-500.json
.\scripts\windows\project-python.cmd .local-data/live-500-interim-audit.py
```

The last command is the local read-only audit created for this inspection; it
verifies saved source/model/forecast evidence and records actual coverage without
network calls, locks, collection, reconciliation or forecast writes. Its printed
counts supersede this interim snapshot; recheck the new started/done receipt and
Windows exit status before choosing a final session verdict. If a run is still
active, leave it alone and inspect again after it finishes. If interrupted again,
preserve the new receipt/reservation and diagnose termination after collection.

## Preserved pre-session verification — 18 October 2026

Verified on Sunday **18 October 2026**, starting at 17:47 IST, from
`504c36df4ab4f78ddfd3e8e62a3fb5ea6abcddd4`, on
`alphalens-investment-evidence-completion`. This is a pre-session operational
verification. It is **not** evidence that Monday's market session or collection
has occurred. No collecting worker was started and no market-data GET was sent
during this verification.

## Observed outcomes

| Item | Result | Actual evidence and remaining condition |
|---|---|---|
| Task registration | PASS | Both exact tasks are enabled, Ready, Dell/Interactive/Limited. Only one expanded collecting task was found. Existing RELIANCE action and trigger were preserved. |
| Approved quota compliance | PASS | Fixed 500; 250 stocks/600 reserved GET attempts per run; 1,800/day; three attempts/day; 60-minute cooldown; 31-day catch-up. Installed config and immutable approval have the same policy hash below. |
| Ready for first new-session collection | PARTIAL | Current identity, protected credential, account, independent date, source checksums, model reload and quotas passed. An actual complete scheduled run and published new-session candles remain unobserved. |
| First 500-stock fresh-session collection | PENDING | Sunday is officially non-trading. Monday 19 October's cached official timing fact specifies 09:15–15:30 IST, but its session and publication have not happened. |
| Genuine new EOD securities | **0** | Zero retained candles for 19 October; no new capture attempted. Existing qualified coverage remains 500 securities/447,483 candles. |
| Provider GET attempts | **0 new** | Shared ledger has 1,498 historical successful HTTP attempts; no new attempt was added. The earlier interrupted attempt's five source GETs and 600-request reservation remain preserved. HTTP success is not candle acceptance. |
| Updated model inputs | **0 new** | Replayed the pinned model against 300 saved vectors; maximum score difference exactly zero. This is replay verification, not new-session inference. |
| Genuinely generated new forecasts | **0** | Existing 31 original plus 300 expanded forecast bodies remain byte-exact against the research backup. No prediction was backdated or republished. |
| Actual matured outcomes | **0** | All 183 checked original/expanded ledgers contain zero outcome records. Required future entry, five eligible sessions, qualified source retrieval and action checks remain outstanding. |
| Latest quote classification | PARTIAL | Last genuine six-stock browser batch: three strict VERIFIED, three indicative; all six delayed displays. A subsequent single RELIANCE diagnostic was indicative. No new quote request in this preflight; these are dated prior observations, not fresh Sunday quotes. |
| Frontend/browser correctness | PASS within stated scope | Six compiled authenticated real-saved-data browser cases passed on isolated port 8029. Native 8017 compiled pages and nine anonymous API rejection checks passed. Original operator authentication was not bypassed; a signed-in original-operator browser session was unavailable. |
| Data and personal-record preservation | PASS | 2,485 original frozen files (8,505,278,241 bytes), 47 alerts, 240 additional immutable files, original V1/V2 evidence, 331 V2 forecast bodies, 23 sequence files, four protected credential fingerprints, original account/password hash and personal records verified. |
| Security | PARTIAL | Current credential isolation/origin/read-only PostgreSQL check passed. Baseline foundation/container and frontend CI passed. Three historical unverified fixture detections remain disclosed; no history rewrite or scanner relaxation. New code CI results are recorded below. |

## Exact installed tasks

Read directly from Windows Task Scheduler; times are IST. Neither task was
re-registered, disabled, or run by this verification.

| Task | Action | Last run / result | Next run |
|---|---|---|---|
| `AlphaLens-Private-EOD-Watchlist` | `scripts\windows\p30-daily-update.cmd` with `.local-data\p34-runtime\daily-config.json` | 18 October 11:03:09 / **0** | **19 October 08:30** |
| `AlphaLens-Private-NSE-Market-Research` | `cmd.exe /d /c` → `scripts\windows\run-nse-market.cmd` with `.local-data\full-nse-runtime\market-workflow-500.json auto --scheduled` | 18 October 16:25:55 / **267014**, interrupted | **19 October 20:30**, then 21:30 and 22:30 |

Both working directories are `D:\al-research\p28-worktree`, both use
`IgnoreNew` and `StartWhenAvailable`; execution limits are 10 minutes for RELIANCE
and 30 minutes for expanded collection. The logged-in Dell operator and powered-on
machine are required. Next-trigger registration is not a successful capture.

The approved policy SHA-256 remains
`4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778`.
Its protected configuration, approval receipt and current task-registration
receipt are retained locally. No scope, quota, cadence or approval was expanded.

## Source, clock and coverage preflight

The fresh cached official master was retrieved on 18 October at
11:07:14.731992 UTC. It contains **3,198 verified current common equities**;
all 500 configured keys, ISINs, symbols and segments match. Current identities do
not prove historical membership or full-market candle coverage.

Independent date guard at 12:23:05 UTC returned
`INDEPENDENT_DATE_BOUNDS_AGREE`: receipt bounds
12:23:05.988778–12:23:06.052571 UTC, both on 18 October IST.
The NTP source is unauthenticated and is not production time attestation.
No Windows clock settings, receipt timestamps, strict quote thresholds or
intraday verification policy were changed. EOD readiness uses its independent
date/session/publication guard.

Existing checksummed official timing bodies confirm 17 and 18 October are
non-trading dates, 16 October completed, and 19 October is scheduled to open at
09:15 IST. The future timing body was retrieved on 18 October at
10:56:19.691533 UTC, SHA-256
`eece364a6538548c2f02e788dc74877f97c1631ffbad055d2a5b3933f2988477`.
It establishes a schedule, **not** future trading, publication or candle delivery.
The worker must recheck its own fresh clock and applicable session evidence.

Source bytes reconstructed **447,483 qualified candles** from 3 January 2022
through 16 October 2026, over 1,188 observed cohort dates. Six additional source
candles remain quarantined for the non-trading 26 April 2025 date. There are
146,517 absent slots against this observed cohort grid, including listing/history
limitations; this is not a claim of that many missing official trading sessions.
Official historical-calendar completeness remains unestablished.

**499/500** securities have a 16 October row. **SHERVANI,
`NSE_EQ|INE011D01013`**, has 36 observations from 17 August through 15 October
2026 and lacks the 16 October row. No fill or explanation such as suspension was
invented. It remains a missing-source-evidence case for bounded catch-up.
For 19 October, all 500 have **NO_ELIGIBLE_OBSERVATION**, not attempted, reason
`FUTURE_MARKET_SESSION`; none is marked updated. New-session data storage growth
is **0 bytes**; local verification receipts/backups are separate audit outputs.

The existing narrow [official private noncommercial research reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3)
and protected read-only analytics credential remain the source-use basis. This is
not public redistribution, commercial advice or unlimited acquisition permission.
The forum page could not be independently reopened by the web reader today;
previously captured source evidence and the exact operator approval were reused.
[Current official standard API limits](https://upstox.com/developer/api-documentation/rate-limiting/)
were checked: 50/second, 500/minute and 2,000/30 minutes. The shared local limiter
is conservatively aggregate across quote, master and EOD clients. Observed
historical aggregate window maxima were **8, 135 and 502**, respectively.
This does not establish unobserved calls from other applications or a remaining
provider daily allowance.

### Dated quote ordering evidence

The saved six-stock batch was actually retrieved on **18 October at 16:31 IST**.
All six last-trade dates were **16 October**, consistent with a closed Sunday
market. A newly generated provider snapshot is not a newly executed Sunday trade.
The existing compiled delayed/indicative presentation preserves that distinction.

| Securities | Provider generation (UTC) | Actual local network receipt (UTC) | Existing classification |
|---|---|---|---|
| BAJFINANCE, RELIANCE, TCS | 11:01:33.797000 | 11:01:33.725600 | Strict quote-time rejected; separately indicative within the conservative independent receipt interval |
| HDFCBANK, ICICIBANK, INFY | 11:01:36.611000 | 11:01:36.567936 | Strict validated snapshot using the independent lower receipt bound |

For the indicative group, generation is **71.4 milliseconds after the raw local
receipt**, while the independent interval remains inconclusive. An intentional
one-second display delay cannot prove the original ordering. This is retained
uncertainty, not a reason to rewrite timestamps or widen strict thresholds. The
fresh date guard still supports the separate EOD date check. Repeating closed-market
quote requests solely to seek six green badges was not justified.

## Recovery defect fixed and preservation of failed evidence

The existing worker sorted missing securities in descending last-observation
order. That spent the bounded batch on newer evidence before older gaps,
contrary to the approved oldest-missing policy. Commit **0554b65** removes that
reverse ordering. Ties remain deterministic by exact instrument key. Two
parameterized TEST_ONLY tests exercise actual first candle-request selection
with a one-stock budget and empty publication response. They do not represent
genuine provider captures.

The interrupted run `fff29e14ad9f45129818961feddf817b` retains its original
started/done records, five actual source GET attempts and **600** reserved GETs.
At preflight it was the sole collecting reservation for 18 October; the
conservative cooldown had elapsed by 5,222 seconds. Reservations were not
deleted, refunded or reset. The next IST day has its own approved ceiling.
No conflicting collector or dangling owned collecting descendant was observed.
No progressing real collection was deliberately interrupted for testing.

Existing fixture tests separately verify source-checksum replay, published
capture followed by zero-GET replay, publication-pending empty responses,
future-date rejection, crash reservations, cooldown/daily limits, shared atomic
request reservations, immutable forecasts and outcome maturity. Real historical
source validation and exact saved-model replay used **zero new source GETs**.
The current incomplete operational recovery status was preserved rather than
replaced with a dry-run success or another collecting attempt.

## Research lifecycle and application evidence

The pinned original price-only V2 model is unchanged:

- Model ID: `05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`.
- Artifact SHA-256: `f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3`.
- Exact ordered input contract: **16 features**.
- Recomputed all **300** eligible latest vectors from the genuine 61-slot source
  windows; maximum difference from saved ordered vectors was exactly zero.
- Saved expanded scores: **300**, observation date **16 October**; score snapshot
  matches the reconstructed source dataset. Saved generation time:
  **18 October 11:05:57.246229 UTC**. No model was retrained.
- Compatible saved LSTM scores: **43**, independently labelled experimental.
- Prospective bodies: **31 original + 300 expanded**, checked against the
  existing backup across 183 ledgers. Overlapping securities are not 331
  independent market decisions. No LSTM prospective records were invented.
- Outcome records: **0**. The first eligible entry is still future,
  **19 October 09:15 IST**. Five eligible observed sessions, corresponding opening
  and fifth close, required later retrieval, action/source compatibility and
  immutable outcome recording must occur before maturity can be claimed.

Known historical model and cost-adjusted failures remain unchanged:
`NO_DEMONSTRATED_EDGE`. Accepted model/ranking counts remain **zero**. The existing
126 matured decision dates, 1,000 outcomes, 30 securities, two quarters,
statistical/economic/calibration/stability criteria and independent human review
remain required. This verification is not independent model approval.

Six browser cases passed in **1.8 minutes**, without retries or provider capture:
FIFO and read-only research routes; indicative EOD exit scenario; exact compiled
Top 5/10/20 scores and identities versus backend; saved preference editor with
isolated-profile restoration; horizon/economic/adverse-scenario backend matching;
stock-level LSTM identity, historical comparison chart and explicit risk sizing.
No timeout occurred in this run. Historical intermittent timeouts remain recorded
in the previous report; this run does not prove they can never recur.

These authenticated tests used the same compiled build and genuine saved source
stores on **8029**, with a separate test account/personal store. Original native
**8017** served the expected compiled index and login page, rejected all nine
anonymous private API reads, and preserved the operator/password hash and personal
records. A signed-in browser test with the original operator account remains
unperformed; no password was reset, exposed or authentication bypassed.

The native online backup/isolated restore passed for auth, alerts, operations,
prospective and personal databases; restored sessions were revoked and original
stores were unchanged. Actual PostgreSQL reads confirmed connectivity,
read-only transactions and absence of write grants. Its four original financial
tables remain empty as recorded in the baseline; no transactions were invented.
The older fixed-name PostgreSQL restoration verifier correctly refused to reuse
its existing restore database (`EXISTING_RESTORE_DATABASE_PRESERVED`); this refusal
is not a new successful PostgreSQL restore. Existing PostgreSQL backup/restore
evidence was preserved.

## Test and security receipts

Private metadata, source receipts and test logs remain ignored under
`.local-data/first-500-*`; market bodies, credentials and financial records are
not committed.

| Check | Actual result |
|---|---|
| Market engine, operations, shared quota, forward cohort, stock history | **54 passed**, 15.07 seconds |
| Independent EOD date, strict/indicative quote clock, final forward, V2 maturity | **108 passed**, 26.55 seconds |
| Compiled authenticated browser | **6 passed**, 1.8 minutes; scope above |
| Focused Ruff lint and format | PASS |
| Full frontend suite | **108 passed**, 20 files, 114.12 seconds |
| Original frozen research and alerts | PASS: 2,485 files / 47 alerts |
| Protected credential/account/original V1/V2 preservation | PASS: 240 additional immutable files, four credential fingerprints |
| Online five-database backup and isolated restore | PASS; original unchanged; restored sessions revoked |
| Credential/build/API isolation, foreign origin, actual PostgreSQL read-only role | PASS; 1,039 source/build files scanned; no current credential values found |
| Local all-result TruffleHog changed range | PASS: `504c36d..0554b65`, verification enabled, three chunks/1,478 bytes, zero findings; earlier URI failure and zero-chunk attempt were not accepted as passing scans |
| New code container build and strict scan | PASS: **zero HIGH / zero CRITICAL**, downloaded Trivy artifact inspected |
| New code frontend CI | PASS: type/lint/tests/build/audit and isolated synthetic-demo workflow |
| New code full backend/PostgreSQL CI | **1,456 passed / eight skipped**, 320.74 seconds; full quality job PASS |

Baseline [foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39123123228)
and [frontend](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39123123239)
workflows completed successfully at `504c36d`. The unchanged strict container
gate rebuilt and scanned that baseline. A new code-commit build/scan is required
and was separately completed: [new foundation/container run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39127248924),
[new frontend run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39127249079).
At **`0554b65e89043a9aec2b726240ff1f9f8bb40379`**, both complete workflows passed:
Linux/PostgreSQL 17 tests **1,456 passed / eight skipped**, full Ruff/format/mypy,
Bandit, Python dependency audit, configured secret gate, container rebuild/imports
and strict Trivy; frontend **108 tests**, typecheck/lint/build, npm audit and
**four synthetic-demo browser tests**. Dependency audits found no known
vulnerabilities. The eight skips retain absent local-only research/archive and
production-live prerequisites; they are not passing provider acceptance tests.
The separate local provider-backed preservation/browser/replay evidence is
described above. The code-range secret stage scanned three chunks/1,478 bytes with
zero findings; it is not a new full-history diagnostic. Scanner policy was unchanged.

The report/runbook follow-up contains documentation only; the tested operational
software commit is the full hash above. The branch remains
`alphalens-investment-evidence-completion`; no merge into main was performed.

The [three historical unverified detections](../security/final-secret-history-audit.md)
remain part of the audit: reviewed fixture/configuration placeholders, no evidence
of a current exposed operator/provider secret. Their historical failed diagnostic
is not rewritten as passing. No detector suppression, history rewrite, credential
reset, container severity change or model acceptance relaxation was performed.

## Next real-world verification

Leave the two approved tasks intact. Keep the operator logged in, Windows awake,
PostgreSQL and protected credentials available on **19 October**. After actual
EOD publication, inspect the **20:30** run and the bounded **21:30/22:30** retries.
Do not manually start extra polling, delete reservations, or assume an official
guaranteed publication time. With a 250-stock run ceiling, full 500-stock coverage
requires at least two eligible batches and may remain partial if source evidence
is absent or rejected.

```powershell
Set-Location D:\al-research\p28-worktree
Get-ScheduledTask -TaskName 'AlphaLens-Private-EOD-Watchlist','AlphaLens-Private-NSE-Market-Research'
Get-ScheduledTaskInfo -TaskName 'AlphaLens-Private-NSE-Market-Research'
.\scripts\windows\project-python.cmd -m workers.nse_market status --root .local-data/nse-market-expansion --v2-root .local-data/experimental-nse-v2 > .local-data/first-500-after-session-workspace.json
```

That saved-only status does not acquire data. In the private workspace and
checksummed `operational/runs/*.done.json`, compare the intended session with
per-security `daily/<session>/<ISIN>/record.json`, immutable response/action
checksums, publication-attempt receipts, actual source GET accounting and daily
reservations. Classify each security as updated, already verified, pending,
rejected, excluded, rate-limited, authentication-failed or budget-limited based
on its actual evidence. Require real new-session vectors and future-entry-safe
forecasts before reporting downstream success. Then verify zero-request replay
and original forecast-body preservation. Windows result **0** alone is insufficient.

The application remains at <http://127.0.0.1:8017/nse-market>.

```powershell
.\scripts\windows\start-p33-alphalens.cmd
.\scripts\windows\check-alphalens.cmd .local-data/p33-runtime/operator-config.json
.\scripts\windows\stop-p33-alphalens.cmd
```

These are the existing owned app/PostgreSQL commands. They do not disable the
scheduled tasks; do not stop the machine/application for the planned verification.
The isolated 8029 test server was stopped after verification; native 8017 and
PostgreSQL remained running and both tasks remained Ready.

The generic `check-alphalens` command reports the older P19/P22 accepted-research
health contract. Its `automatic_acquisition=DISABLED`, accepted inference gate and
zero legacy prospective count do **not** describe the separately approved
experimental 500-stock Windows task or its 331 records. Use the actual task query
and `/nse-market` operations/experimental evidence for those. Native PostgreSQL
was reachable and the compiled process was responding in this check.
