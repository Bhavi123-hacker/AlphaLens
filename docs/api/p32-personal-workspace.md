# P32 private research workspace

P32 extends P31's provider-first terminal. Current official-master NSE_EQ/EQ
identities are discoverable dynamically by name, symbol, ISIN or instrument key.
This is current identity coverage, not historical membership, quote entitlement,
verified sector classification or ML eligibility.

## Explicit market observations

`GET /api/v1/providers/upstox-private/instruments?q=&limit=20&offset=0` uses an
in-memory trigram index. The server returns at most100identities/page; search
ranking prefers exact symbol/ISIN/key and symbol prefixes. Refreshing the master
replaces its index; removed/renamed identities must be reverified. No BSE fallback.

`GET /api/v1/providers/upstox-private/watchlist?instrument_keys=...` accepts1–50
distinct verified keys. Official Full Quote V3 documents500keys/request; the local
cap is deliberately smaller. One batched quote plus, if required, one master GET;
no historical downloads, polling or retries. Valid cached full snapshots are
reused. `queried_count`, accepted-price `observed_count` and `valid_quote_count`
have distinct meanings. Rejected future quote timestamps never expose an LTP.
An inactive or invalid selected identity rejects the request and requires repair.

Full selected-stock snapshots retain P31's maximum3identities, bounded daily
history, separate current/previous OHLC, strict clocks and passive600-second
memory expiry. Official daily-candle closes are provider observations, not an
independently verified NSE final close. No adjustment equivalence is claimed.
Statistics, comparisons, candidates, portfolio marks, scenarios and copilot
answers use active cached observations and their remaining lifetime. Expiry does
not trigger provider acquisition. No durable provider-price table is introduced.

## Genuine single-operator persistence

`personal_root` is a new private SQLite sidecar governed by
`db/personal-workspace.sql`; original PostgreSQL schemas and privileges are
unchanged. Its owner must equal the existing active P21 ADMIN account ID.
Parameterized writes use transactions, optimistic revisions and bounded records.
Windows ACL protection is applied. This is not a multi-user account system.

`GET /api/v1/personal/workspace` returns profile, portfolio metadata, named lists,
journal, alert rules and recently researched identities. Profile dimensions that
require sectors, market caps, dividends or PIT fundamentals are saved but remain
unsupported in filtering. Numeric drawdown, volatility, volume and declared
research-budget caps use explicit available evidence; Low/Moderate/High has no
invented calibrated mapping. All defaults are editable research assumptions.

Personal POST routes exist only with explicit `personal_mutations=true`. Existing
P21 authentication, same-origin/CSRF checks and the narrow `X-AlphaLens-Local:p32`
write namespace apply. Bodies are capped at64KB and duplicate JSON keys rejected.
Legacy financial endpoints remain read-only. Record counts, watchlist identities,
ledger events and CSV previews have explicit bounds. No broker endpoint exists.

## Manual portfolio accounting

Manual opening positions, funded purchases, owned partial sales and recorded cash
events use the unchanged P15 ledger/FIFO accounting engine. Immutable events use
stable sequence IDs to resolve equal-resolution Windows timestamps; request IDs
provide idempotency. No future recording clock is fabricated. Operator dates do
not establish a verified historical execution time, broker position or funding.
Declared costs, exact realized FIFO gains/losses and remaining basis are distinct
from indicative provider marks. Unknown fees/actions remain explicit; no accepted
economic portfolio valuation, bank cash, dividend return or full-path portfolio
drawdown is invented. Concentration uses declared remaining cost weights.

`POST /personal/portfolios/{id}/import-preview` validates at most100CSV rows and
the complete resulting FIFO sequence without writes. Exact headers are shown in
the UI. ISIN and trading symbol must match the current master. The opaque plan is
owner/portfolio/revision bound and expires after600seconds. `import-confirm`
requires explicit confirmation and commits all rows atomically; unchanged repeat
confirmation is idempotent. User acquisition prices are user records, never saved
Upstox observations or verified brokerage executions.

Scenarios are pure calculations: share changes, an explicit uniform shock,
optional target weights and declared cash changes. They never modify holdings,
create orders or infer starting bank cash. The cash-change subtotal and target
allocations are educational calculations with execution costs/actions excluded.

## Research and alerts

Historical scans require explicit prepare/step requests, authenticated ownership,
checksum-verified bounded partition reads and cancellation. No worker continues
after the client stops requesting steps. At most4jobs and5year windows; each
partition keeps the original reader deadline. Rankings disclose observed cohort,
sample/missing counts, dated identities, exclusions and raw-price limitations.
Incomplete/changed-identity paths are excluded, not repaired. Mean daily price
movement divided by its volatility is not Sharpe, total profit or a future signal.

Descriptive candidates, Top5/10/20 limits and preference exclusions use real
observations. Empty results remain empty. The Historical ML Leaderboard links to
stored P9/P10 evidence;474unresolved backtests stay unresolved. No model loading,
fitting, holdout reevaluation or current ML gate bypass occurs.

Research alerts are manually evaluated against cached evidence. P20 receives only
source/session/rule IDs, condition codes and deduplication hashes, never provider
prices. No background acquisition, outbound delivery or execution is enabled.
The guided copilot is deterministic sourced analytics, not an external chat model.
Current eligible ML predictions remain zero until every original data,38-feature,
peer, adjustment, independent acceptance, risk and publication gate passes.

Public demo source and hosting are independent and synthetic. P32 neither publishes
the private backend nor establishes personalized financial-advice readiness.
