# P31 private provider terminal

This is a local authenticated descriptive market view, separate from the retained
P19 research pipeline and frozen P5/P6/P9/P10 evidence. Production data and model
acceptance are not cleared. No orders, account/broker mutations, ingestion,
scheduling, model training or model predictions are performed by these routes.

`GET /api/v1/providers/upstox-private/instruments?q=...` explicitly loads/searches
the official current NSE instrument master. Results are limited to20, with exact
symbol/ISIN matches first. Current NSE_EQ and instrument_type EQ must agree with
the ISIN-based instrument key. This is current metadata, not historical membership
or a verified common-equity universe. Name matching discovers candidates only.

`GET /api/v1/providers/upstox-private/snapshot?security_id=...` resolves the latest
canonical ISIN AND symbol to one current master entry. Missing or ambiguous
identity, a changed ISIN or changed symbol blocks mapping; it never joins by name.
Alternatively `instrument_keys=...` accepts one to three positively verified master
keys. These two selection modes are exclusive. Archive links require a unique
catalogue ISIN and symbol match. Neither link merges source prices or adjustments.

An explicit snapshot makes at most seven GETs: one current master and session
timing when their caches need refreshing, one batched Full Quote V3, one batched
OHLC V3 with interval1d, and one bounded five-year daily-candle request per equity.
The existing central quota/backoff ledger remains authoritative. There are no
automatic transport retries; auth/permission/rate rejection stops further price
requests. The legacy protected RELIANCE route remains for compatibility.

Provider prices stay in process/browser memory. Passive expiry removes server
snapshots after600seconds even if no next read occurs. The browser removes active
snapshots at the remaining server TTL and inactive queries immediately. Expiry,
focus and reconnection do not fetch another price. Login/logout keeps P21 privacy
and origin/CSRF rules; the token stays in Windows Credential Manager/backend.
No private provider bodies, price snapshots or credentials are persisted in Git.

The primary header prefers a validated LTP quote snapshot. Absolute and percentage
change use `last_price - prev_close_price` and division by that same documented
previous close. `ohlc.close` is not substituted. A rejected/unavailable quote falls
back to an explicitly labeled provider daily candle close and observed candle
change. Previous returned candle is not necessarily the previous exchange session.
Current/previous OHLC snapshots and their dates stay separate; absent prev_ohlc
stays null. No provider daily candle or OHLC snapshot establishes an independently
verified official final close. Current EOD absence stays pending/unavailable.

Quote identity, symbol, positive finite Decimal prices, offset-aware snapshot time
and epoch-millisecond last-trade time are validated. Future snapshot/last-trade
timestamps are rejected, including when the HTTPS Date header is ahead of the
local clock. HTTP Date skew is diagnostic evidence with one-second precision,
not an NTP correction or tolerance. Observed trade date, generation time, local
receipt and cache age remain distinct. No OS clock is changed by the application.

Charts use provider-observed dates, volume and unchanged P6 descriptive formulas.
Calendar completeness, historical identity continuity, adjustment basis, corporate
actions and retained/ML usage are unverified. Missing prices and warm-up values
are not filled. Currency display uses two decimals; exact source strings remain
available in protected evidence details. The independent archive keeps its frozen
dates, RAW_UNADJUSTED basis and explicit age. No provider row enters that archive.

Private provider envelopes use `p31.provider.v1`, PRIVATE_TRANSIENT_DESCRIPTIVE,
no final-vintage/research-profile claim, and unchanged OPEN/NOT_CLEARED production
gates. The retained research status belongs in Research Automation/Data Health,
not in the status of an observed manual Upstox request.

Official contracts reviewed:
[Full Quote V3](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/)
and [OHLC V3](https://upstox.com/developer/api-documentation/get-market-quote-ohlc-v3/).
The [Pro Web page](https://upstox.com/upstox-pro-web-online-trading/) was a high-level
UX reference only; the AlphaLens design and assets are original/existing open source.
