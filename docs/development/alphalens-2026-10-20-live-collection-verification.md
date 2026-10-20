# 20 October 2026 production collection verification

**Verdict: `PARTIAL_COLLECTION_VERIFIED`.** Read-only audit performed on 20 October, approximately 22:50–23:10 IST, against branch `alphalens-visual-overhaul`, software commit `56e42455909bd1eda2b3d3daa25565c44ac4966b`.

AlphaLens genuinely collected and persisted **499 qualified candles for 499 of its 500 securities**, recomputed **302 complete V2 feature vectors**, applied the pinned model, and appended **302 eligible prospective forecasts**. This is supported by source bodies, hashes, normalized rows and forecast records, not just Windows exit status. One security, RRECL, remains incomplete. The 21:30 launcher was interrupted before worker initialization. Monitoring defects remain.

**These are 19 October observations acquired on 20 October.** The saved dated market-timing response for **20 October contains no open NSE session**. Therefore zero 20 October candles is appropriate; 19 October is the latest validated trading session. No holiday name or unobserved session is inferred. Evidence: E1–E5 below.

## Evidence and audit boundaries

All paths below are relative to the repository. Private evidence stays ignored and local; this report contains no prices, financial records, credentials or provider response bodies. Audit scripts only read production stores. Their JSON outputs are new verification artifacts, not replacement production receipts.

| Reference | Actual evidence |
| --- | --- |
| E1 | `.local-data/verification-20261020/initial-audit.json` and `audit.py`: checksummed run receipts, process diagnostics, calendar facts, coverage and all 499 individual source-record references/hashes. Each accepted candle was reparsed from its retained raw body and compared with normalization and the saved research frame. |
| E2 | `.local-data/verification-20261020/windows-task-state.private.json`: actual `Get-ScheduledTask` / `Get-ScheduledTaskInfo` results and exported task XML hashes, observed around 23:06 IST. |
| E3 | `.local-data/nse-market-expansion/operational/runs/65b9bcacca15405597cc793b75e50c43.done.json` and `6e4392cb9a244c8ab7e92cac05bba460.done.json`, corresponding `.attempt.json` / `.started.json`, and `operational/diagnostics/*.json`. |
| E4 | `.local-data/verification-20261020/ledger-preservation.private.json`, `ledger_preservation.py` and `final-checks.private.json`: read-only shared SQLite attempt ledger, immutable run reservations, rolling request peaks and unchanged ledger digest during final audit checks. |
| E5 | `.local-data/nse-market-expansion/calendar/2026-10-19.json`, `2026-10-20.json`, `2026-10-21.json`, and `session-links/2026-10-19.json`: retained dated provider timing bodies, hashes and receipt times. |
| E6 | `.local-data/verification-20261020/forecast-audit.private.json` and `forecasts.py`: original-body preservation, all forecast stores, append-only triggers, chronology, pinned-model reload and exact feature/score replay. |
| E7 | `.local-data/verification-20261020/power-events.private.json`: Windows System events, event records and timestamps. No matching Application Error/WER/Python fault was found in the queried window. Task Scheduler Operational history is disabled. |
| E8 | `.local-data/verification-20261020/api-diagnosis.private.json`, `api_diagnosis.py`, and `characterization-tests.txt`: isolated authenticated ASGI checks against native saved market data, stale-master reproduction and two isolated characterization tests. |
| E9 | `.local-data/verification-20261020/account-preservation.json`, `frozen-preservation.json`, `ledger-preservation.private.json`, `final-checks.private.json` and `supplement.private.json`: protected-file/account/credential comparisons, original alerts and research, native HTTP status, PostgreSQL `SELECT 1`, pending raw-response count. |

No provider acquisition, collection replay, outcome reconciliation, forecast publication, model fitting, deployment, service restart, task modification, quota reset, power-setting change or audit-policy change was performed. Provider GETs caused by this audit: **0**. The native operator account was not reset or impersonated. Authenticated API diagnosis used cloned existing QA authentication with the native saved-data configuration and QA ownership context, in an isolated process; it is **not** a fresh authenticated browser test of the native operator session.

## 1. Scheduled executions

All times in this report are **IST**; source receipts retain their original UTC timestamps. E1–E3 preserve the exact underlying values.

| Expanded slot | Actual evidence | Result |
| --- | --- | --- |
| 20:30 | Launcher 20:30:03.689873; worker 20:30:35.227562–20:37:06.501098; launcher exit 0 at 20:37:06.555197. Worker duration 391.273536 seconds. | **PARTIAL toward 500:** 250 selected and accepted; 502 actual GETs; 156 new forecasts. Terminal batch state `CAPTURED` does not mean all 500 were complete. |
| 21:30 | Launcher start 21:30:02.142614, PID 29324, launch ID `17cafcafa0384d878edd34b76059d86a`. No worker-start fact, collection attempt, reservation or terminal receipt. | **INTERRUPTED / incomplete launch evidence.** Earlier Windows result `3221225786 / 0xC000013A` is the operator's recorded observation; current TaskInfo has been superseded by 22:30. Exact termination time and duration cannot be recovered. No GETs at 21:00–21:59. |
| 22:30 | Windows last start 22:30:01; launcher 22:30:02.186378; worker 22:30:07.595562–22:33:18.924253; launcher exit 0 at 22:33:18.945525. Worker duration 191.328691 seconds. | **PARTIAL:** skipped 250 already verified, selected remaining 250, accepted 249, one pending; 500 GETs; 146 new forecasts. Terminal state `PARTIAL_OR_PUBLICATION_PENDING`. |

The final receipt hashes are respectively `dab5da939927b2630ff88e13696796fa9ea4e8f9a3a3b1abc5bc69e17e82337e` and `025e8ab69de2c04ed2b3dbf8d868e628ea57c2a61d17febc15627d37b0e9a6c6`.

At the final Windows query, both tasks were **Enabled / Ready**:

| Task | Last actual Windows start / result | Next actual trigger | Unchanged definition |
| --- | --- | --- | --- |
| `AlphaLens-Private-EOD-Watchlist` | 20 October 14:05:27 / 0 | **21 October 08:30 IST** | Interactive operator, Limited, 10-minute execution limit; XML SHA-256 `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`. |
| `AlphaLens-Private-NSE-Market-Research` | 20 October 22:30:01 / 0 | **21 October 20:30 IST** | Interactive operator, Limited, 30-minute execution limit; XML SHA-256 `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`. |

Expanded triggers remain 20:30/21:30/22:30. Both tasks disallow starting on battery and stop on battery. `IgnoreNew` and `StartWhenAvailable` remain unchanged. No collecting worker or collecting descendant was active at inspection. No overlapping completed collector intervals were found. Ready and exit 0 are reported separately from data acceptance.

The RELIANCE wrapper's `.local-data/p34-runtime/daily-last-run.json` recorded a bounded run at **14:05:32.962167**, two API calls, existing 14/15/16 October receipts, and 19 October `IDENTITY_REFRESH_DEFERRED_BY_BUDGET`. Its separate legacy store remains at three sessions, latest 16 October. These are not three newly proven captures today. The expanded pipeline independently retained RELIANCE's 19 October candle. Disabled task history prevents proving why the 08:30 task last started at 14:05; a delayed start is consistent with its settings but not established as the cause. E2, E6.

## 2. Power and interruption investigation

| Windows System time | Event / record | Confirmed observation |
| --- | --- | --- |
| 21:28:50.654454 | Kernel-Power 105 / 332838 | AC online false. |
| 21:28:53.981030 | Kernel-Power 105 / 332839 | AC restored before the 21:30 launcher. |
| 21:41:45.280764 | Kernel-Power 506 / 332844 | Modern Standby entered, reason Lid, 11 minutes 43 seconds after launcher start. |
| 21:54:58.648660 | Kernel-Power 105 / 332865 | AC online false. |
| 21:54:58.662045–21:55:10.084089 | 507/506 transitions, including records 332866, 332868, 332871, 332873, 332876 | Standby exits/reentries; AC restored at 21:55:08.476359; final listed exit reason Lid. |

These events demonstrate an unsuitable unattended operating environment and a possible interaction with the tasks' battery conditions. They **do not prove** the termination initiator or exact causal chain: there is no historical task-stop record or worker completion time for 21:30. The `0xC000013A` observation indicates control termination, not a unique cause. Sleep, a battery-condition stop, console control, task timeout or external termination cannot be conclusively selected from current evidence.

The process trace localizes the missing progress to **after launcher start and before operational worker entry**. The launcher records its start before importing/running the worker module. No worker reservation or provider request was reached. A reproducible application-side import/launcher defect was not established. An abruptly terminated process cannot be assumed to write its own final diagnostic. No new power/audit settings were enabled. E1, E7; implementation: `workers/nse_market/operational.py`, `workers/nse_market/daily.py`, `scripts/windows/run-nse-market.cmd` and existing diagnostic entrypoints.

## 3. Actual source-qualified collection

| Measurement | Actual result |
| --- | --- |
| Configured / distinct attempted securities | **500 / 500** across two disjoint batches. |
| Newly accepted securities / candles | **499 / 499**, all session **19 October 2026**. |
| Still incomplete | **1**, RRECL, `NSE_EQ\|INE0AK901016`. |
| Malformed/OHLCV quality rejections / identity exclusions in these batches | **0 / 0**. |
| HTTP authentication failures / rate-limit failures / budget-exhausted securities | **0 / 0 / 0**. |
| Previously completed securities skipped at 22:30 | **250**, already source-verified at 20:30; no repeat capture GET for those securities. |
| Accepted source receipt interval | **20 October 20:33:08.721715–22:31:59.539514 IST**. |
| Qualified retained candles now / before | **447,982 / 447,483**, increase **499**. |
| Retained securities / latest validated trading session | **500 / 19 October**. |
| New 20 October candles | **0**, correct for the retained dated non-trading-session evidence. |
| Current master eligible common equities | **3,185** in the 22:30 refresh; previous 3,198 was a different dated snapshot. This difference alone does not establish 13 delistings. |

For every accepted `daily/2026-10-19/<ISIN>/record.json`, the audit checked instrument key/ISIN/symbol/segment/type against the configured identity, response and action checksums, raw candle hash, parser OHLCV/schema validation, exactly one requested-session row, receipt after official close, normalized/raw parity and membership in the resulting saved dataset. No duplicate 19 October slots were found. E1 contains every per-security receipt and digest.

The frame contains 447,988 provider-reported observations before six **pre-existing 26 April 2025 non-trading anomalies** are excluded, producing 447,982 qualified rows. Those six are not new 20 October collection failures. Current quote access, historical coverage, action compatibility and accepted ML eligibility remain separate measurements.

RRECL's retained `daily/2026-10-19/INE0AK901016/publication-attempts/f11fd00fd77b4896a308d875f919c83e.json` records receipt **22:31:04.312716**, provider status success and **zero candles**, state `PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE`. Raw SHA-256: `83d511d64ffda7e4c950b5f2c8f95130e5fa0c872af9b85a70e1a6bf3616428f`. There is no completed record for that security/session. HTTP 200 was correctly not upgraded to capture success. Publication delay versus no trading/suspension cannot be distinguished from this empty response. It remains eligible for existing bounded catch-up, without a fabricated fill. E1, E9.

SHERVANI, `NSE_EQ|INE011D01013`, has an accepted **19 October** record. Its older 16 October gap was not filled or allowed to block valid newer source evidence. E1.

The saved 19 October timing fact is 09:15–15:30 IST. The 20 October timing response, retrieved at **20:30:39.759911**, has no open NSE session; raw SHA-256 `deb7283f6b6f082c293251bd10802e3fe12f671f7cd11984bb6593838c70579c`. The next retained opening is **21 October 09:15 IST**, published timing evidence retrieved at 20 October 20:33:08.532251. The audit verified these retained bodies without another calendar request. E5.

## 4. Actual GETs, reserved capacity and guards

| Usage on 20 October IST | Actual GET attempts | Immutable reserved capacity |
| --- | --- | --- |
| RELIANCE task | **2** | Separate legacy workflow; included in shared actual GET count. |
| Expanded 20:30 | **502** | **600** |
| Expanded 21:30 | **0** | **0**; no worker reservation reached. |
| Expanded 22:30 | **500** | **600** |
| Total | **1,004 shared**, of which **1,002 expanded** | **1,200 expanded** of **1,800/day** |

The expanded 1,002 GETs comprise **500 candle requests, 499 action requests, two dated timing requests and one master refresh**. All 1,004 shared attempts completed with success/HTTP 200; **zero unresolved shared-ledger attempts** remain. The empty RRECL response remains a data-level pending result despite its completed HTTP request. The earlier interrupted/crash reservations remain intact. E3–E4.

Unused reservation capacity is **600**, not a refund of the difference between 1,200 reserved and 1,002 actual expanded GETs. All three scheduled slots have elapsed; unused capacity does **not** authorize a fourth/manual attempt. There were two reserved collecting attempts and one pre-worker interrupted launcher. Limits remain 500 configured, 250 selected/run, 600 reserved/run, 1,800/day, three authorized slots, 60-minute cooldown and 31-calendar-day catch-up.

The first reservation upper bound to the second reservation lower bound is **7,171.117359 seconds**, satisfying the conservative 3,600-second cooldown. Today's completed runs did not require the new bounded wait; 21:30 never reached that guard. Therefore this audit does not claim a live exercise of the wait path or live competing-worker test. Existing locking/reservation code was unchanged.

Observed shared rolling peaks were **8/second, 326/minute, 502/30 minutes**, below configured 50/500/2,000 limits. An Upstox universal daily allowance is not established by this calculation: 1,800 is the approved workflow reservation ceiling. Ledger lifetime count was 2,503, of which 1,004 occurred today. The final audit found its digest unchanged: `8767702190458003c39052eeeb92d69b81a7480348f00de7efd7c53222db7f70`. No reservations were cleared, reused or rewritten. E4.

## 5. Model application and prospective forecasts

| Measurement | Verified result |
| --- | --- |
| Latest complete V2 feature vectors / model scores | **302 / 302**, observation session 19 October. Previous saved score snapshot had 300 for 16 October. |
| Feature and pinned-model numerical replay | Maximum absolute error **0.0 / 0.0**. No training performed. |
| Excluded securities from V2 scoring | **198:** 162 known-action lookback exclusions, 35 missing-lookback slots, one missing observed session. |
| New eligible forecasts | **302:** 156 at first completed batch, 146 at second. |
| Original forecasts preserved | **331 of 331 byte-exact**. |
| Total V2 forecast records | **633:** original service 31, expanded stores 602 (old 300 + new 302). These are records, not 633 distinct stocks or independent outcomes. |
| New forecast recording interval | **20 October 20:36:48.764331–22:33:14.382799 IST**. |
| New forecast entry reference | **21 October 09:15 IST**, supported by retained next-session timing. |
| Matured / recorded outcomes | **0 / 0**. |
| LSTM | **43 unchanged saved 16 October scores**. No new 19 October LSTM inference was performed by this daily workflow. Two saved report files describe the same 43, not 86. |
| Independently accepted models / rankings | **0 / 0**; `NO_DEMONSTRATED_EDGE` remains unchanged. |

Pinned model: `05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`. Latest dataset: `fd9a4701494d0a3bc78e864f69a78057a25691a4f73e859896ff9705bd4280e7`. Latest score generation **20 October 22:33:12.327501 IST**. Source-compatible split/bonus-adjusted price-component research remains distinct from dividend-inclusive total return and exhaustive corporate-action coverage.

For all 302 new forecasts, the audit verified `source_observed_at <= inference_at <= recorded_at < next_session_timing.open_at`, complete ordered vectors, stored version/hash lineage and prospective eligibility. Expanded stores contain 602 unique `(model, security, observation session)` forecasts. Body/index verification and four no-update/no-delete SQL triggers per ledger passed. No duplicate publication or original-body rewriting was found. E6.

The old forecasts' 19 October entry is not a matured five-session outcome after only that session; 20 October does not count as a trading session. New forecasts' entry has not occurred. The pipeline's reconciliation receipts have zero inserted outcomes. Counts of 300 and 456 pending inside individual run receipts are **pre-inference reconciliation counts**, not the final combined 633. The expanded worker's reconciliation does not by itself prove future operation of the separate original 31-record service. Independent minimum dates, outcomes, security coverage, statistical/economic evidence and reviewer approval remain unchanged and unmet.

## 6. Dashboard diagnosis

The native app remained available at <http://127.0.0.1:8017/nse-market>: login returned **200**, anonymous private API **401**, PostgreSQL `SELECT 1` succeeded, and the existing native app/PostgreSQL processes remained running. No restart or deployment was used. A fresh native authenticated browser run was **not** performed; read-only backend characterization is the scope below. E8–E9.

**Instrument-master expiry explains the reproducible unavailable-evidence path.** The previous verified master was observed 19 October **21:30:34.690458**, expired 20 October **21:30:34.690458**. The 20:30 run used it while valid; the interrupted 21:30 launch did not refresh it. The 22:30 run obtained a new master at **22:30:16.832160**, expiring 21 October at that same time. Both snapshots' checksums and current eligibility were verified. E4.

In isolated authenticated ASGI checks using actual saved production market data and a provider client patched to reject acquisition, the six research/status/universe/instrument/search/freshness GET routes returned **200**, with live saved research reflecting **499/500 coverage for 19 October** and 302 current V2 scores. Injecting only a stale-master error reproduced **503 `NSE_MARKET_SAVED_EVIDENCE_INVALID`** for research/status/universe and **503 `UNIVERSE_STALE_REFRESH_REQUIRED`** for current provider identities. `nse_market._read` groups saved research loading and current-master freshness in the same failure boundary. This hides otherwise valid dated research when identity metadata expires. Current identity freshness must remain strict; this audit did not widen its TTL. E8; source: `apps/api/src/alphalens_api/nse_market.py`, `workers/providers/universe.py`.

The native `.local-data/scheduled-repair-native-start.err.log` has a 503 at **22:02:43.856265**, consistent with that expiry interval. Its redacted entry does not retain the URL, so the exact historical endpoint is not independently recoverable. The isolated reproduction establishes the code path, not proof that every user-visible error had that cause.

**The 6 October chart is a different data source.** The saved archive route `/api/v1/stocks/tejhq:isin:INE002A01018` returned **200**, date range 22 June 2011–**6 October 2026**. `StockWorkspace.tsx` has separate provider and frozen-archive sources. The archive's end does not represent the expanded store, whose latest qualified date is **19 October**. No frozen archive was changed or blended with provider history. No live provider chart/quote GET was made in this audit, so fresh provider chart retrieval is not newly certified. E8.

**Windows task monitoring is stale even while collection data is current.** The saved dashboard task snapshot still reports **19 October 22:30, result 1, next 20 October 20:30**, observed 19 October 23:12:12.132293. Actual Windows now reports **20 October 22:30, result 0, next 21 October 20:30**. The latest completed-run receipt, full-cohort candle coverage and shared actual-GET counters are current; the saved task observer is not. Legacy RELIANCE task metadata similarly retains a stale 17 October next-run value. Viewing these endpoints caused zero provider GETs. E2, E6, E8.

Further misleading fields: the second daily receipt's `pending_securities=250` is pre-batch, not the final one missing; function-level `scheduled_collection_enabled=false` scaffolding conflicts with the authorized wrapper/actual installed task. These are monitoring/schema interpretation defects, not evidence that acquisition was disabled. No UI/backend repair was deployed during this audit.

## 7. Preservation, verification and security scope

- **4,544 protected pre-repair files checked, zero changed**, against `.local-data/scheduled-repair-backup-20261019T171117Z/manifest.private.json`. The original 331 V2 forecast bodies match; legitimate new records were counted separately. E4, E6.
- **2,485 frozen research files / 8,505,278,241 bytes** verified. Original 47 alerts checksum remains `dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41`. V1 model/evaluation/source copies and original tracked evidence remain unchanged. E9.
- Existing account/password, personal-record and protected-configuration comparisons passed. Four protected credential fingerprints matched without printing values; no Credential Manager modification was performed. PostgreSQL SELECT-only connectivity passed. This is preservation verification, not a new full database backup/restore certification. E9.
- **Two isolated TEST_ONLY characterization tests passed in 3.21 seconds**, covering the unchanged exact 24-hour identity boundary and stale-master/saved-research failure coupling. These demonstrate a defect and boundary, not an externally repaired service. An initial command containing unsupported `--no-cov` was rejected before test execution; the recorded supported command completed with two passes. E8.
- Six isolated authenticated normal GET cases passed, four injected stale-master cases reproduced 503, and saved archive checks returned 200. Native login/private-access boundaries passed. No new full backend/frontend CI, authenticated browser regression, dependency audit or container rescan was run for this read-only audit. Previous passing repair CI/security evidence remains **dated baseline evidence**, not a new scan or collection proof.
- The three historical unverified secret detections remain disclosed in `docs/security/final-secret-history-audit.md`; no suppression/history rewrite/new full-history pass is claimed. No production source, models, credentials, financial records, task definitions, quotas or safety gates were modified.

## 8. Required next actions and bounded remediation

1. **Use the existing authorized next triggers:** RELIANCE **21 October 08:30 IST**; expanded **21 October 20:30/21:30/22:30 IST**, with next Windows trigger verified as 20:30. Keep the approved operator logged in, the lid open, machine awake and on AC. Do not manually add an attempt, reset reservations, change tasks or fabricate RRECL's missing candle. These usage precautions do not alter Windows policy.
2. After the next completed scheduled run, inspect actual per-security receipts and shared ledger, including RRECL catch-up and the next genuinely published session. Verify source-qualified new vectors, future-entry timestamps and immutable new forecast counts. Source publication is not guaranteed at a particular scheduled minute.
3. **Seek operator approval before production repairs:** decouple display of dated saved research from current identity freshness; preserve strict identity gating for new current/provider actions. Refresh metadata with safe headroom inside existing authorized collecting runs/request ceilings, without adding off-slot requests or extending TTL. The current master's 21 October 22:30:16 expiry risks another narrow boundary around the final slot.
4. Correct monitoring to use a fresh bounded local Windows task observation or visibly label its observed timestamp/age; show pre/post-batch pending counts and distinguish function defaults from installed scheduled authorization. No provider requests or task-definition changes are needed to read Windows state. Test these changes in isolation before any approved deployment.
5. If interruption diagnosis is required, obtain explicit approval to enable Task Scheduler Operational history and/or add earlier import-stage diagnostics. Current System facts establish standby/power risk, not its termination initiator. No audit-setting change is authorized by this report.
6. Fresh LSTM inference is not part of the completed daily V2 path; show its **16 October** date rather than implying 19 October updates. Do not retrain or invent missing sequence scores. Continue genuine prospective tracking; no five-session outcomes or independent acceptance can be declared today.

Read-only follow-up commands (do not use `--collect` or start a task manually):

```powershell
Set-Location D:\al-research\p28-worktree
Get-ScheduledTask -TaskName 'AlphaLens-Private-NSE-Market-Research','AlphaLens-Private-EOD-Watchlist'
Get-ScheduledTaskInfo -TaskName 'AlphaLens-Private-NSE-Market-Research'
Get-ScheduledTaskInfo -TaskName 'AlphaLens-Private-EOD-Watchlist'
.\scripts\windows\project-python.cmd -m workers.nse_market status --root .local-data/nse-market-expansion --v2-root .local-data/experimental-nse-v2
```

The detailed audit is reproducible locally with the saved-evidence scripts in E1/E4/E6/E8/E9. Shared SQL accounting used `SELECT * FROM attempts ORDER BY provider,request_id,attempt` through the provider store's read-only connection, with IST-day filtering of `reserved_at`; reservations came from immutable `*.started.json`, not inferred from successful HTTP responses. All 499 individual accepted source references are retained in E1.

**Operational conclusion:** real qualified acquisition, V2 inference and forward forecast recording worked in two completed batches. Complete 500-stock collection, interruption reliability, current task-status presentation and fresh LSTM application have not all passed. The precise safe next step is to keep the existing operator environment available for the next authorized triggers and verify their receipts, while obtaining approval for the small metadata/monitoring reliability repairs above. No additional acquisition or deployment was performed to improve this verdict.
