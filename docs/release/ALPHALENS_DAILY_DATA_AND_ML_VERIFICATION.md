# AlphaLens daily data and ML verification — 2 November 2026

The two approved manual recovery attempts on **1 November 2026** obtained **994 genuine new candles**: 497 instruments each received the 29 and 30 October sessions. The protected source store now contains **450,970 observations across 500 saved stock histories**. The unchanged compatible experimental model generated **307 new, genuinely prospective individual forecasts** from the 30 October source snapshot on 1 November, before their 2 November 09:15 IST entry. Both workers nevertheless ended with clock failures during later stages. Daily automatic delivery therefore remains **FAIL / not reliably demonstrated for this release**.

At this report's 2 November verification, that entry has passed. There are **307 latest saved historical experimental scores, zero currently eligible new-entry predictions, zero independently accepted predictions and zero qualified forward outcomes**. These counts describe different states. A completed source capture or historical score does not establish a successful unattended run, investment edge or independent acceptance.

## Verified source and model state

| Item | Actual evidence |
|---|---|
| Latest accepted observation session | 30 October 2026 |
| Newly retained sessions | 29 and 30 October 2026; 497 candles per session, 994 total |
| Saved stock histories | 500; 497 contain the latest accepted session |
| Full saved observation count | 450,970 |
| Latest source dataset | `db71eb8358a13d0c0b75b7c8356656d84081209c3b76180e4c2210b9add3bb1f` |
| Source identity | `UPSTOX_OFFICIAL_HISTORICAL_CANDLES`; authorized private research retention, not public redistribution |
| Actual latest inference | 1 November 2026, 11:41:30.715042 UTC / 17:11:30.715042 IST |
| Latest model score count | 307, observation session 30 October; saved historical scores at verification |
| Forecast entry | 2 November 2026, 03:45 UTC / 09:15 IST; already passed |
| Latest individual forecast recording times | 1 November 11:41:38.318442–11:41:43.203710 UTC; before entry |
| Expanded immutable forecast records / unique decisions | 1,530 / 1,530 |
| Original separate forecast records | 31 preserved; combined record total 1,561 |
| Current new-entry eligibility / independent acceptance | 0 / 0 |
| Qualified forward outcomes | 0; no success percentage is justified |
| Model ID | `05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525` |
| Frozen model artifact SHA256 | `f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3` |
| Latest score receipt | `.local-data/nse-market-expansion/scores/f9de09dd336240c6b19d28d8780d50a1.json` |
| Score receipt SHA256 | `ddb065a1739caa0f9c7939a0c5545044e265cb10a373f8a5b6347abb044b8a3e` |

The expanded forecast ledger contains 300 decisions from 16 October, 302 from 19 October, 312 from 23 October, 309 from 28 October and 307 from 30 October. The original 31 records are separate evidence. Existing records, source dates and generation times were preserved; no old score was redated.

The model remains NSE-specific, `EXPERIMENTAL_UNVALIDATED`, with `NO_DEMONSTRATED_EDGE`. Its horizon is `NEXT_OPEN_TO_FIFTH_OBSERVED_CLOSE_PRICE_COMPONENT`. Full BSE discovery does not establish BSE model compatibility. Current-universe membership is not historical point-in-time membership; corporate-action coverage and independent model acceptance remain limited.

## Actual approved acquisition and terminal results

Both 1 November attempts used exact approved proposal SHA256 `831854538c4504d04b9c98e64072b124771f68d4d6b71a53f62afa364d594c9b` and the original 327-file live source aggregate `06e8a5631391fefbb9f8a209150269d4ed1a0e41e244c89ab926239f96c260e4`. The original Microsoft/Google independent clock hosts were unchanged. The first clock gates passed sufficiently to acquire real data; later failures were not bypassed.

| Run | Acquisition and partial durable result | Terminal result |
|---|---|---|
| 1 November manual attempt 1; worker `591887e776b044659c535cc31eaeef2e` | External start 09:21:33.743765 UTC / 14:51:33 IST; 600-request reservation. Provider SQLite ledger records 502 successful Upstox attempts in this interval. Accepted 247 instruments, two new sessions each: 494 candles. New source dataset `82b44b494320a1ea9ea1412c283a3cf8f6cf850b9e6fadead21a9beba92eebaa`. | Scoring's fresh clock acquisition failed with `NTP_SAMPLE_BOUNDS_REJECTED`. Worker failed 09:33:26.545856 UTC; external exit 1 at 09:33:44.624838 UTC. No forecasts were created by this attempt. |
| 1 November manual attempt 2; worker `79d9bda73e1044ef82ae5b7b1e584094` | External start 11:29:15.566739 UTC / 16:59:15 IST; separate 600-request reservation. Provider SQLite ledger records 500 successful Upstox attempts. Added 250 accepted instruments and 500 candles, bringing the new-session cohort to 497 instruments / 994 candles. Actual inference and 307 individual forecast records were saved before the next entry. | Later global-cohort/publication guard failed `NTP_RECEIPT_INTERVAL_TOO_WIDE`, wrapped as `DAILY_DATE_OR_CLOCK_DISCONTINUITY`. Worker failed 11:41:45.135085 UTC; external exit 1 at 11:42:11.753559 UTC. The 307 valid individual forecasts remain intact. |
| 2 November scheduled catch-up; worker `083f5d91d4af4709a4e7dfc710b11f7c` | Started 04:33:30.124611 UTC / 10:03:30 IST. | Failed preflight at 04:33:32.442653 UTC with `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE` / `NTP_OFFSET_OR_DISTANCE_REJECTED`; zero provider requests and no collection reservation. |

The two manual windows contain 1,002 successful ledger attempts in total; that is not a candle count. Master/calendar/source requests and valid but incomplete responses are separate from accepted observations. Both failed workers leave `source_requests_last_run` null in their final result because the exception prevented normal outcome assembly; the provider ledger and saved-source receipts supply the actual request evidence.

Three configured identities did not obtain accepted new records: `NSE_EQ|INE023A01030`, `NSE_EQ|INE029L01018` and `NSE_EQ|INE077P01034`. Successful HTTP status did not override incomplete publication/session evidence. They remain pending; no missing price, zero candle or rejected source record was fabricated to complete the cohort. Current-master series/symbol changes were recorded without rewriting historical identity or adding unapproved instruments.

Exact private receipts, relative to `D:\al-research\p28-worktree`:

- `.local-data/private-v1-20261101/manual-recovery-1.started.json` and `manual-recovery-1.finished.json`.
- `.local-data/private-v1-20261101/manual-recovery-2.started.json` and `manual-recovery-2.finished.json`.
- `.local-data/nse-market-expansion/operational/runs/591887e776b044659c535cc31eaeef2e.started.json`, `.attempt.json`, `.done.json` and their checksum sidecars.
- `.local-data/nse-market-expansion/operational/runs/79d9bda73e1044ef82ae5b7b1e584094.started.json`, `.attempt.json`, `.done.json` and their checksum sidecars.
- `.local-data/nse-market-expansion/operational/runs/083f5d91d4af4709a4e7dfc710b11f7c.done.json` and checksum sidecar.
- `.local-data/nse-market-expansion/daily/2026-10-30/` contains the 497 immutable accepted instrument records, including retained-response provenance and normalization/checksum evidence.
- Provider quota/request ledger: `D:\al-research\p28-runtime\provider-state\providers.sqlite3`, inspected read-only. No token or request headers were printed.

## Saved publication recovery and chronology

The first failed worker saved genuine source records before scoring but did not publish its normal derived market view. An explicitly authorized, zero-provider recovery published those 247 latest histories on 1 November. It preserved the prior 28 October score and immutable forecast ledger, showing the older score as stale relative to the new data. Receipt: `.local-data/private-v1-20261101/history-publication-once.finished.json`.

After both attempts terminated, a separate saved-publication recovery finished on **2 November 04:41:57.950368 UTC / 10:11:57.950368 IST**. Under the existing control-store writer lock it published the full saved source snapshot and the already saved 30 October score. It made **zero provider requests, zero clock acquisitions, zero model inference calls, zero new forecasts and zero task mutations**. Source inputs, live collector code, score pointer and forecast-ledger hashes were unchanged.

This operation updated truthful saved display state. It did not repair a failed scheduled run retroactively. The latest app market view is `.local-data/nse-market-expansion/market-views/55734c239d494339a2a3987e7fc5b838.json`, SHA256 `b3ff6956d4966a15631be711bc566b77965dad9dad7a7a1c5243d56300d2cb4e`; the corresponding market pointer SHA256 is `5fdcda3f50eae6994c7e5a3fb2ea7e9df2adc9202e0502c878951c9dc511dac5`.

Evidence: `.local-data/private-v1-20261102/saved-publication.started.json` and `saved-publication.finished.json`; the latter records the 450,970 source rows, 497 latest-session histories, 307 saved scores and preservation assertions.

The failed post-inference clock guard prevented a new **global prospective cohort declaration** for 30 October. Its absence is real. Now that the 2 November 09:15 IST entry has passed, creating that declaration or fresh forecasts would backdate prospective evidence and is prohibited. Preserve the 307 individual records with their actual pre-entry timestamps; evaluate any eventual outcomes only through the applicable registered policy and qualified future observations. No new cohort declaration, standalone scoring or collector run was used to make this report.

## Actual model replay and dynamic rankings

The read-only model audit completed on **2 November 04:43:21.833547 UTC / 10:13:21.833547 IST**. It verified the complete saved dataset, reconstructed **307 exact compatible feature vectors**, and reproduced **all 307 actual saved model scores twice** using the frozen compatible model. Feature names and ordering matched all 16 trained inputs. The audit made zero provider or clock calls and wrote zero forecasts. This replay verifies implementation and saved inference reproducibility; the actual new inference evidence remains the 1 November score receipt and pre-entry ledger records.

The same audit compared actual 28 October and 30 October snapshots:

| Ranking | Actual change | Consistency |
|---|---|---|
| Descending model score; stable instrument-key tie break | All 20 Top-20 positions changed; 309 prior candidates versus 307 latest candidates | Top 5 is a prefix of Top 10; Top 10 is a prefix of Top 20; 307 unique instruments |
| Existing UI risk adjustment, `model_score - daily_return_sd`, weight 1; stable instrument-key tie break | All 20 Top-20 positions changed | Both Top-N prefix checks pass; 307 eligible saved-score candidates |

The risk weight is an `ENGINEERING_ASSUMPTION_NOT_VALIDATED_EDGE`, not a proven profit adjustment. These are dated saved experimental research rankings. At verification the intended next entry has passed, so the UI must label them `SAVED_HISTORICAL_SCORE` / historical experimental research rather than `FRESH_ELIGIBLE_EXPERIMENTAL_SCORE`. Missing histories/features exclude only the affected securities. BSE instruments, derivatives and indices are not promoted into this NSE-compatible score population.

Exact audit: `.local-data/private-v1-20261102/daily-model-audit.json`. It records dataset/model IDs, 450,970 source rows, twice-exact score replay, forecast-session totals, zero outcomes, both ranking comparisons and terminal worker lifecycle evidence.

## Reproducible defects fixed in the candidate

Commit **`b4995f5bdd63d46b24e71b95c63c94a8195fdc81`**, pushed to `alphalens-master-completion`, changes only two production modules and their two focused test files.

1. **Saved-history publication ordering:** valid newly accepted candles were hidden from the app when scoring failed its clock guard. `workers/nse_market/daily.py` now attempts saved-market publication in the existing scoring block's `finally` path. It preserves strict scoring failure, unchanged old scores and immutable forecast chronology. The worker still fails when scoring fails; successful publication is not reported as successful inference. Two meaningful regression cases verify successful saved publication and failed publication without masking the original clock exception.
2. **Aged valid clock cache:** the second actual attempt reached cohort publication 13.270734 seconds after a valid 81.369153 ms calibration anchor. The unchanged conservative drift calculation exhausted the 100 ms width budget before the 30-second maximum cache age. `workers/providers/daily_clock.py` now permits one bounded renewal only when the original anchor is still valid, exactly recomputable, fresh and provably exhausted by age. It waits the existing acquisition cadence and invokes the existing strict refresh with six entirely new samples, the original eight-probe upper budget, unchanged bounds and continuity checks, and a maximum 32-second wait. Malformed, contradictory, stale, discontinuous or failed new evidence propagates; there is no retry-until-pass behavior or discarded bad sample.

| Verification | Result |
|---|---|
| Related clock-refresh, continuity, failure-diagnostic, operational-clock and publication suite | 106 passed in 16.70 s; before annotation/import/format cleanup |
| Routing, engine and saved-market-publication suite | 55 passed in 21.57 s |
| Postformat run using actual native collector interpreter; seven new clock cases and all thirteen publication cases | 20 passed in 8.64 s |
| Scoped Ruff check, format check and mypy for all four changed files | PASS |
| Bandit on both changed production modules | PASS |

Logs: `.campaign-worktree/.local-data/campaign-daily/ordering-fix-targeted-tests-20261102.log` and `ordering-clock-native-tests-20261102.log`. The 106-case result is retained in the execution transcript. The native runtime is `.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`; no environment replacement or package installation was performed for this repair.

**The candidate repair is not yet applied to the live collector.** Protected inactive proposal `.local-data/private-v1-ordering-clock-20261102/ordering-clock-source-proposal/proposal-INACTIVE.json` has SHA256 **`b1647d48dfa838de630b3442c4451c0a57b6c572ead26277b834061578447329`**. It binds frozen original and replacement bytes, the current policy, both current task definitions and actual task-file ACL hashes, rollback and fresh idle/source checks. It requires explicit operator approval before live mutation.

| Live source file | Exact current SHA256 | Proposed SHA256 |
|---|---|---|
| `workers/nse_market/daily.py` | `726704ed18c3eee0be177de5f7eb07aa97b945421e4aa317efb5da72b9c143b0` | `7683eda1f16689b3da85b7f00d4cea4746237e0233f4630dbebcf1406143b086` |
| `workers/providers/daily_clock.py` | `2fc028ec1d1a7f2d88082c42a42d603ab09a65c18db4d4e961fc4e8ea0de0c70` | `c4ddfb579ba8e419821fad950b66062b1cad086fc70ddc621044e00d6506a9e1` |

The current live aggregate remains 327 files / `06e8a5631391fefbb9f8a209150269d4ed1a0e41e244c89ab926239f96c260e4`. Applying only the proposed two files would yield 327 files / `177442ff1adcaa45daa4418b6aa6da62c782c2cc5a722fed56bd5c14abbe4d47`. Both tasks were Ready when the proposal was prepared; this is a read-only snapshot, not a substitute for the required fresh idle preflight immediately before any approved cutover.

## Clock availability remains an external operational dependency

The original 2 November diagnostic failed `NTP_SAMPLE_BOUNDS_REJECTED` even though each decoded sample independently passed: one Google sample's 98.279 ms interval exceeded the unchanged 100 ms combined budget after conservative projection over the acquisition interval. This is distinct from the valid cached-anchor aging defect. The candidate renewal deliberately does not retry this acquisition failure.

A single separately authorized, review-only Microsoft/Cloudflare diagnostic used the unchanged decoder, sample count, cadence and bounds, substituting hosts only inside that diagnostic process. It failed `NTP_TRANSPORT_TIMEOUT`; only the three Microsoft responses arrived. There was no repeated candidate probe, live configuration change or hostname proposal. Original sources remain `time.windows.com` and `time.google.com`. No OS time, service, clock tolerance or policy was changed. Neither probe made market API requests or mutated market data.

Private receipts: `.local-data/private-v1-20261102/clock-trace-once-result.json` and `cloudflare-candidate-clock-trace-once-result.json` (candidate receipt SHA256 `7decb8fb7034f010aba1b45549a18671e412dc302e6dd782b983df6c290d65ed`). Official public-endpoint review is `.local-data/private-v1-20261101/cloudflare-public-ntp-review.json`; the diagnostic is not collection authority. Independent unauthenticated NTP retains its documented common-path and source-trust assumptions.

## Preserved acquisition authority and source boundaries

Collection remains the separately approved 500-security NSE cohort: at most 250 securities and 600 request reservations per run, 1,800 per day, three runs per day and a 60-minute cooldown; normal approved trigger times remain 20:30, 21:30 and 22:30 IST. A crash or failure does not reset the ledger. Full NSE/BSE search discovery authorizes no whole-universe collection.

The bound policy SHA256 is `4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778`; cohort SHA256 is `6a527cb5a12a1948634255e159a765f54bd80db1d1c697b1529ba37076ddcfb6`. The provider permission reference remains `UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN`. Credentials were neither printed nor replaced. Approved current watchlist action, market-task triggers/principals/ACLs, runtime, source retention rules and calendars remain unchanged by this report and candidate-only repair.

The existing official Upstox adapter preserves URL-encoded `instrument_key`, provider provenance, strict schema/session/publication checks, quota reservation and bounded transport behavior. Current-day collection uses the supported `/v3/historical-candle/intraday/{instrument_key}/days/1` route; completed historical sessions use `/v3/historical-candle/{instrument_key}/days/1/{to_date}/{from_date}`. The 29/30 October catch-up used historical candles. No source blending, adjusted-series substitution, hidden scraper or public real-data redistribution was introduced.

The separate manual NSE final-bhavcopy recovery adapter remains an offline/operator-input path with review, provenance/schema/Decimal/identity/checksum/conflict protections. No live NSE file import was used for these results. An actual import still requires verified rights, a checksum-bound candidate and explicit approval of mutation scope; NSE recovery does not imply BSE coverage. Frozen models, original research/evaluations, 2,485 protected files, 47 original alerts, original forecasts, accounts and financial records remain protected by the broader release preservation checks; the saved recovery and audit specifically verify source/score/forecast immutability.

## Daily acceptance result

| Gate | Result supported by this evidence | Remaining work |
|---|---|---|
| C — genuine new observations | PASS: actual authorized 1 November acquisition retained 994 new genuine candles | Three configured identities still pending; no automatic expansion authorized |
| D — actual new compatible inference | PASS for 307 genuine individual pre-entry forecasts and actual compatible-model inference | Independent acceptance pending; no missing global cohort may be declared retrospectively |
| E — dynamic saved Top-N | PASS: actual new snapshot changes all 20 positions for raw and UI risk-adjusted rankings; both prefix properties pass | Saved historical labels must remain truthful; no current-entry eligibility after 2 November 09:15 IST |
| F — current scheduled reliability | FAIL: latest actual scheduled worker failed 2 November 04:33:32 UTC before acquisition | Apply only an approved exact repair, then obtain a genuine future authorized scheduled completion with matching worker/supervisor/task/publication evidence |

Historical 28 October scheduling evidence remains valid and separate: run `ee95bb9c4b7f4e07812f24f40cef40c3` captured data and exited zero, and `7f1fb6437e434834aabd5d6f0ce506bf` published a later partial/pending source snapshot with real scores. Those results do not override the later failures or establish uninterrupted current automation. The 31 October manual attempts and the resumed 1 November scheduled run also failed clock preflight with zero provider requests; their delayed wrapper completion after a power interruption was not a new capture.

The independent original RELIANCE/watchlist task also remains operationally unverified: read-only native evidence on 2 November shows last run 10:09:01 IST, `LastTaskResult=2147943467` (HRESULT low code 1067), Ready, next run 3 November 08:30 IST. The existing `p34-runtime/daily-last-run.json` and pipeline clock/capture evidence still date to 29 October 08:30; no new worker terminal receipt was observed. The Task Scheduler Operational event log is disabled, so this evidence does not establish a Python, import, authentication or other specific cause. The log was not enabled and the task, code and runtime were not altered as part of this investigation. The separate market-collector task's latest clock-failure terminal agrees with its task result 1; that agreement does not explain the watchlist failure.

Scientific labels remain `EXPERIMENTAL_RESEARCH`, `SAVED_HISTORICAL_SCORE`, `FORWARD_OUTCOME_PENDING` and `INDEPENDENT_ACCEPTANCE_PENDING`. Software replay and source acquisition are verified; predictive profitability, guaranteed accuracy and independently accepted recommendations are not established.
