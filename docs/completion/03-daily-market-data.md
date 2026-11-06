# Daily NSE market-data readiness — 24 October 2026

Audit branch: `alphalens-master-completion`; starting HEAD `da4382242371c17ebdf2cecc620541931b91e313`. Campaign software changes were local/uncommitted during these checks; the final release report records the delivered commit.

**PARTIAL.** The existing private collector persists genuine daily observations, but complete daily 500-stock coverage is not established. This campaign audit made **zero market-data provider requests**, changed no task/configuration and retained all source evidence. Local documentation reads and offline tests do not qualify a new live endpoint.

## Current evidence

The checked exact-cohort configuration is `.local-data/full-nse-runtime/market-workflow-500.json`: 500 securities; 250 selections/run; 600 reserved GETs/run; 1,800 reserved/IST day; three collecting attempts/day; at least 60 conservative minutes between reservations; 20:30/21:30/22:30 IST; 31-day bounded catch-up. The policy hash remains `4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778`. The existing approval binds the cohort, source scope, cadence and storage assumptions; unused capacity does not authorize extra manual calls.

| Receipt | Saved result | Interpretation |
| --- | --- | --- |
| 21 October 20:30 IST, `e71cb300c51841b5a1fde1df098ae04e` | 251 GETs; 250 successful empty candle bodies; no accepted candles | `PARTIAL_OR_PUBLICATION_PENDING`, not a successful fresh session |
| 21 October 21:30 IST, `a6f8d0cd575c49528440e964765702b6` | 250 GETs; successful empty candle bodies; no accepted candles | The oldest missing cohort was retried; these are not 500 unique queried securities |
| 22 October 10:45 IST, `69d81cf9042348269f5d838fee01b4a2` | 499 GETs; 248 accepted 21 October observations; two pending responses | Genuine catch-up; `NO_FUTURE_ENTRY`, zero new forecasts |
| 22 October 23:42 IST, `42b4d2a204384900bbea63a78b82a259` | Independent-clock preflight failed; zero GETs | No acquisition/reservation success follows |

The latest qualified retained daily session is **21 October, 248/500**, leaving **252 pending**. **19 October has 499/500**. Neither statistic is 24 October freshness. Existing independent audit files checked 747 accepted record/source hashes and requested-session membership; `verify_new_candles.py` additionally checked all 248 new records against raw/normalized/action/session evidence. See [the detailed saved-source audit](08-live-collection-reliability.md) and private `.local-data/completion-collection-audit/{audit.private.json,new-candles.private.json}`. Those files are private evidence, not public market-data artifacts.

The campaign also performed one explicit full saved-source reconstruction and derived market-view publication on 24 October: **448,230 qualified observations, 500 retained securities, 248 on the latest 21 October session**, dataset `b25bb59d7c7387622a3be2dfacce0834f91dcdb04ffcb6aa39ee821982c911a2`. Snapshot reconstruction took **230.690 s** and projection/persistence **4.439 s** in this dated run. The new checked `market-view-latest.json` points only to separate derived display artifacts, with 120 observed chart slots/security and zero provider requests. Original source/model/forecast records were not changed. Audit: `.local-data/completion-20261024/saved-market-publication.private.json`.

## Implemented safeguards

| Requirement | Existing implementation | Status / limitation |
| --- | --- | --- |
| Session and holiday/special-session handling | `daily._timing`, `operational._latest_session`; dated official timing bodies; latest completed session searched within 31 days | Software fixture verified; no weekday or holiday inference replaces missing official evidence |
| Publication validation | A nonempty, normalized requested-session candle must exist after official close | Empty/incomplete results remain retryable pending evidence; no fabricated close |
| Identity | Exact approved NSE key/ISIN; dated checksum-verified common-equity master and explicit revision metadata | Fresh current identity still needs the 24-hour master gate |
| OHLCV | Decimal price/range validation, integer volume, aware session clocks, raw/normalized lineage | Provider adjustment basis and full economic entitlement remain separate limits |
| Duplicate prevention | Immutable checked response/action/record files; snapshot keyed by security/session; incompatible revisions fail closed | Preserves original evidence rather than silently replacing data |
| Missing observations | Oldest missing security first, stable key tie-break; 31-day catch-up bounds | A persistent empty oldest stock can consume later retry slots; coverage remains explicit |
| Retry/restart | Existing bodies replay without GET; actions retry separately; crash reservations remain consumed | Interrupted launchers may lack a worker terminal receipt |
| Quotas | Per-run meter plus shared aggregate ledger and immutable daily workflow reservations | Actual GETs, completed HTTP responses, reservations and accepted candles are distinct |
| Display | Saved/session/source timestamps and per-security stale/unavailable state | Saved daily observations are not intraday streaming |

## 21 October empty responses

Saved official timing establishes a 21 October NSE session (09:15–15:30 IST); the corresponding empty bodies do not prove a holiday, authentication failure, rate-limit failure or no trading. The subsequent 248 accepted observations support a delayed availability or endpoint explanation **for that subset**, but do not identify its publication instant or resolve the remaining 252 names. RRECL remains without accepted 19/21 October daily evidence.

`daily.py` currently requests historical daily candles even for a same-day target. The existing transport also implements a separate current-day `intraday_candles` operation. The [official intraday V3 contract](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data/) explicitly supports current-trading-day OHLC and `days/1`; [historical V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/) is a separate endpoint. This is a concrete qualification hypothesis, **not a proven cause or permission to switch acquisition**. A bounded, approved current-day comparison must preserve exact identity, official completed-session gating, raw clocks, adjustment compatibility, per-run budget and immutable evidence before any live change.

## Quote V3 and optional Feed V3

The quote adapter already calls `/v3/market-quote/quotes`, with an application bound of 500 keys, and V3 OHLC with 50 keys. The [official Full Quotes V3 contract](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/) documents snapshots for up to 500 instruments. The selected private terminal uses bounded explicit requests and in-memory storage; ordinary saved NSE page reads do not call it. Strict quote clocks and timing-unverified indicative-display exclusions remain unchanged.

No Feed V3 subscriber was found in the reviewed implementation; the terminal explicitly reports `streaming: false`. The [official Feed V3 contract](https://upstox.com/developer/api-documentation/v3/get-market-data-feed/) describes an authenticated Protobuf WebSocket, normal two-connection/user limit and mode-specific subscription limits. The [current Analytics Token documentation](https://upstox.com/developer/api-documentation/analytics-token/) explicitly includes Websocket among supported categories without a static-IP requirement; token type alone is therefore not a streaming prohibition. Category support does not establish successful account-specific authorization, private display/retention scope or a working installed client. **Streaming: NOT_STARTED; activation: BLOCKED_EVIDENCE.** No connection or paid tier was attempted.

## Verification and remaining work

On this campaign branch, 56 daily/clock/quota/preflight/cohort/capacity cases passed in **11.59 s**, and 60 source/replay/identity/diagnostic/task-observation cases passed in **21.96 s**, both with `-W error` and `ALPHALENS_TEST_TEMP_ROOT=D:\al-tests`. These are **TEST_ONLY offline evidence**, not new provider acceptance. Exact commands are in [daily automation](09-daily-automation.md).

Release blockers are dependable independent time evidence, unresolved process interruption, bounded current-day endpoint/publication qualification, missing accepted securities and fresh current identity evidence. No strict gate, request ceiling, source permission or scientific acceptance condition was relaxed.
