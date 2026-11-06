# P30 Upstox private source decision ? 2026-10-14

Provider: Upstox Securities Private Limited. Reviewed official sources:

- [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/)
- [Analytics launch](https://upstox.com/developer/api-documentation/announcements/analytics-token/)
- [Automated analytics / static-IP update](https://upstox.com/developer/api-documentation/announcements/analytics-token-static-ip/)
- [General terms](https://upstox.com/terms-of-use-and-privacy-policy/)
- [Instrument master](https://upstox.com/developer/api-documentation/instruments/)
- [Daily candles V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
- [Full quote V3](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/)
- [Rate limits](https://upstox.com/developer/api-documentation/rate-limiting/)

## Decisions

Official documentation supports free read-only market/historical GETs, dashboards
and automated analytics. Market GETs do not require a static IP. The local operator
confirmed the imported credential is an Analytics Token. Successful market GETs
establish acceptance/access, not independent scope introspection or account status.
No account, holdings, orders, trades, payments or brokerage-write endpoint is called.
The token is stored under the separate existing P28 current-user Credential Manager
target AlphaLens/UpstoxReadOnlyAnalytics. Alpha Vantage is untouched.

User-authorized bounded testing and a manual private descriptive dashboard are
implemented. Raw candle/quote payloads and prices remain in process memory; only
sanitized verification receipts, API counters and current instrument/calendar metadata
are written. Backend cache lifetime is ten minutes; browser query memory is cleared
on logout. The static demo has no real provider data or private application dependency.

Indefinite local price retention, ML training/research data use and public redistribution
of derived NSE observations are NOT CLEARED. Neither an HTTP200 nor documented API
access is an explicit licence for these separate uses. The user confirmed no separate
written evidence exists. Durable operational ingestion, unattended collection and
source-dependent forecasts remain blocked; no prices are merged into the frozen vintage.

## Scope and live evidence

Current official NSE master:2701 NSE_EQ / EQ-type candidates. EQ alone does not prove
historical common-equity eligibility, active listing, series, departed coverage or
per-date membership. RELIANCE / INE002A01018 / NSE_EQ|INE002A01018 matched exactly.
No BSE substitution. One authorized watchlist identity tested;9 valid daily candles
in the first bounded14-day probe:2026-09-30,10-01,10-05,10-06,10-07,10-08,10-09,
10-12,10-13. Newest returned past daily session:2026-10-13. Provider daily close,
not independently established official final close. Decimal OHLC ranges/integer
volumes and aware Kolkata timestamps validated. Unknown missing sessions, actions,
adjustment basis and original publication times remain unknown.

Full quote V3 returned200 and matched the instrument, but its timestamp was about
2seconds after local receipt and was rejected. No clock tolerance introduced, and
no quote is treated as a completed daily close. Initial network failure and a later
master rejection are retained in verification history; bounded retry succeeded.
Holiday/timing GETs returned200:18 explicit current-year NSE schedule facts and
13Oct exchange session elapsed. Elapsed trading hours do not prove EOD publication.
No normal weekdays or historical calendar knowledge are inferred from this snapshot.

## Limits and failure behavior

Official other-standard-API limits explicitly include historical candles:
50/second,500/minute,2000/30minutes, per API and per user. Full Quote V3 documents
at most500 instruments/request; that is a batch limit, not proof of identical quotas
for every user/category/endpoint. No limit-exhaustion experiment was performed.
AlphaLens applies the existing P28 conservative aggregate Upstox ledger across
all calls, including failures/retries, plus per-run budgets. Frontend controls do
not poll, reconnect-refetch or trigger broad ingestion. Private view uses one fixed
instrument and one bounded request; range buttons only filter already returned data.

401/403 fail closed without retries;429 observes Retry-After and does not shorten
server waits;5xx/network errors use bounded retries/backoff when explicitly requested.
Default retries are zero. Redirects, arbitrary URLs, BSE keys, oversized/malformed
responses and credential echoes are rejected. Failure bodies/exceptions are redacted.
Auth/expiry/quota/outage failure tests are TEST_ONLY; live200 access is separately
recorded. Expiry was not tested by waiting a year or intentionally invalidating the token.
