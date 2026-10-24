# Daily NSE collection reliability

Audit: 24 October 2026 IST. Scope: saved local evidence and read-only Windows task observation. No provider requests, manual collection, task changes, reservation reset or deployment were performed by this audit.

**Status: PARTIAL.** Genuine collection and persistence work, but current evidence does not establish reliable complete 500-security daily coverage. The latest qualified daily session is **21 October, 248/500**, leaving **252** without that session. The earlier **499/500** result belongs to **19 October**, received on 20 October; it is not 20 October trading-session coverage.

## Current saved evidence

The isolated audit `.local-data/completion-collection-audit/audit.py` produced `.local-data/completion-collection-audit/audit.private.json`. It checked all **747 accepted daily records** (499 for 19 October and 248 for 21 October), checked their immutable receipt checksums, raw-response hashes and requested-session presence, and matched provider keys/ISINs to the approved 500-stock plan. Dated identity observation/revision metadata differs from the original plan as expected after master refresh; those metadata changes were recorded, rather than rewriting historical identities. Raw/normalized/frame parity for the original 499 has additional prior independent evidence in `docs/development/alphalens-2026-10-20-live-collection-verification.md`.

The separate read-only `.local-data/completion-collection-audit/verify_new_candles.py` independently verified **all 248 new records**: raw/normalized equality, exactly one requested-session row per security, record-to-response/action checksums, and official session close before receipt. Its saved result is `new-candles.private.json` (**248 checked; all assertions passed; zero provider requests**). This verifies saved observations, not full total-return economics or independent market-wide coverage.

| Saved execution, IST | Actual expanded GET attempts | New accepted candles | Evidence and interpretation |
| --- | ---: | ---: | --- |
| 21 October 20:30–20:32 | 251 | 0 | Run `e71cb300c51841b5a1fde1df098ae04e`: 250 successful empty candle responses plus one timing GET; `PARTIAL_OR_PUBLICATION_PENDING`. |
| 21 October 21:30–21:33 | 250 | 0 | Run `a6f8d0cd575c49528440e964765702b6`: 250 successful empty candle responses; all 500 cohort members still pending. The same oldest-missing batch was retried; 500 requests do not mean 500 distinct stocks were queried. |
| 22 October 10:45–10:51 | 499 | 248 | Run `69d81cf9042348269f5d838fee01b4a2`: catch-up for 21 October accepted 248, retained two successful empty responses; no new forecasts because the next entry had elapsed (`NO_FUTURE_ENTRY`). |
| 22 October 23:42:26 | 0 | 0 | Run `42b4d2a204384900bbea63a78b82a259`: `FAILED`, `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`, before reservation/provider access. |

Terminal SHA-256 values, respectively: `953d168f4e78fea4ae8d5867b3f71c9c78eaffa3ed5104c3af39ebb815d7e249`, `334ac61ab7f9ab5820354ae2a6b0fd089a5365af0957d46c3f38c3f58fabfb07`, `817a3af296d84f81ada9c3c044199534c15bb183198e2f2e60c726c3cd324307`, `5752e22659b160ac0c60caeef96a0b5f962d190aa1a3594c72b32b843066aaee`. Files reside under `.local-data/nse-market-expansion/operational/runs/` and remain private.

There is no newer saved worker terminal receipt in the audit than 22 October 23:42. Read-only Windows inspection on 24 October reports the expanded task's last start **23 October 22:50:33**, result **3221225786 / 0xC000013A**, next **24 October 20:30**, state **Ready**. The separate original watchlist task reports last start **24 October 09:21:09**, the same interruption result, next **25 October 08:30**, state Ready. Those observations establish task state and interruption codes; they do not establish who terminated a process, why a trigger ran late, or successful acquisition. No task settings were modified.

## Empty-response diagnosis

Retained checksummed official timing responses establish an NSE session on **21 October, 09:15–15:30 IST**. The 20 October timing body contains no NSE session. Thus 21 October's empties cannot be classified as a known non-trading day. The bodies have provider `success` with zero candles, not an observed HTTP authentication/rate-limit failure or rejected quality record.

The next morning's 248 nonempty responses establish that those 21 October observations became accessible by their later receipt times. This supports a publication/endpoint-availability explanation for at least that subset. It does **not** establish exactly when the provider published them or resolve the other 252 stocks. RRECL (`NSE_EQ|INE0AK901016`) has no accepted record for either 19 or 21 October; publication delay, no trade, suspension and coverage defects remain distinguishable hypotheses, not conclusions.

Code review found the daily collector uses the provider's **historical** daily endpoint, including for the current date. Upstox separately documents a current-trading-day **intraday** endpoint with `days/1`; see [official V3 historical documentation](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) and [official V3 intraday documentation](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data/). A current-day endpoint qualification is a concrete next investigation, but these documents do not certify the cause of this saved incident. No endpoint switch or provider probe was made here. Any qualification request requires explicit bounded acquisition approval; a deployment changing live collection behavior requires deployment approval.

## Budgets, forecasts and recovery

The protected exact-cohort configuration remains **500 securities**, **250/run**, **600 reserved GETs/run**, **1,800/day**, **three attempts/day**, **60-minute cooldown**, **20:30/21:30/22:30 IST**, and **31-day catch-up**. These limits are enforced in `workers/nse_market/operational.py`, not only configuration. The two collecting starts on 21 October reserve **1,200**; the collecting start on 22 October reserves **600**. A preflight clock failure does not erase consumed reservations or create another approved slot.

The shared request ledger contains **3,505 ordered rows** at audit time: **1,004 on 20 October**, **501 on 21 October**, **501 on 22 October**, and no 23/24 October rows. The 22 October expanded terminal reports 499, while the shared ledger includes two other-client attempts; workflow and shared accounting are separate. Absence of a saved attempt is not proof that an interrupted launcher never ran. Current per-security source status remains authoritative.

All **633 saved V2 forecast bodies** match their 21 October baseline hashes; there are **zero outcome records** and no new forecasts after the 20 October issuance cycle. The historical baseline contains **602 unique model/security/observation decisions**, so records must not be treated as independent samples. A five-session outcome requires the registered subsequent sessions, official timing lineage, eligible prices and later receipt; calendar time alone cannot mature it. No forward accuracy or profitability can be calculated from the current empty outcome ledgers. Separate original and expanded forecast stores remain intact.

Existing safeguards preserve crash reservations, kernel worker locks, action retries without redownloading saved candle responses, zero-GET replay, pending empty responses, oldest-missing-first catch-up and the no-backdated-forecast rule. Forecasts and model checkpoints were not replaced. The audit also verified the baseline model/configuration hashes unchanged.

## Isolated monitoring repair and verification

An interrupted launcher can stop before writing a worker `*.attempt.json`, so `unfinished_attempts_total=0` can coexist with a newer Windows task start and no matching terminal evidence. The new display-only `task_run_evidence` in `apps/api/src/alphalens_api/nse_monitoring.py` compares the observed task start with the last saved terminal completion. It explicitly reports a missing terminal receipt, or a pending receipt for a Running task, without claiming actual GET counts or successful candle capture. `apps/web/src/components/NseOperations.tsx` displays this gap even when no unfinished worker receipt exists. Existing acquisition, scheduler, quote, quota and model logic are unchanged.

Six deterministic TEST_ONLY backend cases passed (`tests/unit/test_nse_monitoring.py -k 'launcher_only or task_receipt'`, **6 passed**, **8.77 s**); they include Ready/exit 0, Ready/interruption, Running, stale observations, naive time and future terminal evidence. Focused Ruff and format checks passed. The component test in `apps/web/tests/nse-operations.test.tsx` verifies the launcher gap is visible without any fetch. Final campaign regression/frontend results are recorded in `14-end-to-end-verification.md`; the initial sandbox run of the broader monitoring group encountered existing temporary/cache ACL access errors and is not claimed as a passing run.

Remaining blockers: dependable independent clock evidence, process interruption diagnosis, genuine publication qualification, completion of missing security/session observations, and enough future eligible outcomes. These do not justify relaxing source validation, clock gates or budgets. Keep task and request-policy changes behind their explicit approval gates.

## Daily operator verification without extra collection

1. Read `Get-ScheduledTask` / `Get-ScheduledTaskInfo` for the two existing tasks. Compare task starts with immutable terminal receipt times; a late start or `Ready` is not evidence of market capture. Preserve process diagnostic facts before any approved local application restart.
2. Read the shared ledger and the existing `*.started.json` reservations independently. Do not clear an interrupted reservation. An NTP/independent-clock preflight failure needs actual bounded clock evidence; local time display alone cannot clear it.
3. Inspect the existing accepted target-session records, action evidence, raw-body hashes and pending publication attempts. The separate `.local-data/completion-collection-audit/verify_new_candles.py` checks the 248 new records without provider calls. Keep the 252 pending slots visible.
4. Verify protected credential availability through the existing readiness boolean only; never print a token or request headers. An empty successful candle response is not an authentication diagnosis.
5. Let only the unchanged approved triggers collect. After completion, compare qualified per-security session coverage, actual GETs, reservations, inference time and appended forecast count. If publication only appears after the next entry opens, `NO_FUTURE_ENTRY` is correct; never backdate a forecast to manufacture daily throughput.
6. Treat the source publication qualification and Windows interruption/clock investigation as separate issues. A local web restart cannot establish provider publication or independent time readiness. Keep hypothetical endpoint/cadence changes as reviewed proposals until approved and qualified.
