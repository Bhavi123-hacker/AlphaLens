# ML V2 source, adjustment and target audit

Reviewed 16 October 2026 for the separate V2 experiment. This audit changes no V1
dataset, original frozen research, accepted model gate or scheduled collection.
Public primary documents and the official community's read-only JSON endpoints
were inspected; this audit made no authenticated provider request and sent no
message to Upstox.

## New evidence: the historical price basis is partly established

The earlier V1 audit recorded the adjustment basis as wholly unknown. A deeper
review found a specific, recent answer from **Anand_Sajankar, Software Engineer,
Upstox**, dated **30 September 2026**, in
[topic 17456, post 5](https://community.upstox.com/t/historical-candle-data-volume-differences-corporate-action-adjustments-and-cas-handling/17456/5).
The answer confirms historical chart adjustments for splits and bonuses, applied
consistently to daily and intraday prices; dividends are excluded. It also states
that candles use executed trades, daily volume includes post-closing trades, and
historical beginning-of-day instrument data is unavailable. It leaves finality
and further adjustment details unresolved. The subsequent user's examples are
questions and observations, not provider confirmations.

This answer is directly linked by the same staff member on **1 October 2026** in
the explicitly V3-specific
[topic 17694, post 3](https://community.upstox.com/t/historical-candle-v3/17694/3).
An earlier
[19 January 2026 answer by Ketan, Developer at Upstox](https://community.upstox.com/t/does-historical-candle-data-api-takes-care-of-corporate-actions/13555/2)
also confirms retrospective corporate-action readjustment. A
[12 June 2024 answer by Pradeep_Jaiswar, Associate Director — Engineering](https://community.upstox.com/t/historical-stock-data-are-they-adjusted-for-dividends-splits/5942/2)
identifies bonuses and splits as the adjustment types then supported. The recent
specific response is the principal evidence; these older replies corroborate it.

The generic web reader could not open these community pages. The public official
Discourse responses at `/t/17456.json`, `/t/17694.json`, `/t/13555.json`,
`/t/5942.json` and `/t/17302.json` returned HTTP 200 and were actually inspected,
including post numbers, author titles and creation dates. No third-party forum
comment or unrelated broker's adjustment policy is substituted for this evidence.

Public-source receipt metadata, UTC 16 October 2026, was recorded without retaining
the thread's user-supplied market examples. Hashes below are SHA-256 of the exact
UTF-8 `cooked` HTML for the named official staff post, rather than a checksum of a
rewritten paraphrase:

| Topic/post | Observed UTC | Staff-post HTML SHA-256 |
|---|---|---|
| 17456/5 | 15:37:08.531621 | `7258f3aaf5613bb6ee73f577f1b45a2829d2c620e10642cb868d7bab254b799a` |
| 17694/3 | 15:37:09.555171 | `bad4506dbc1a9150b0489a78507ed23221a679c7d9278b864568f0baf246cd10` |
| 13555/2 | 15:37:10.572320 | `30c51842072677bf46fead628bae6491433d4ceafafe17e22419242bc4a126d7` |
| 17302/3 | 15:37:11.616355 | `317b0353c515183175f98a4de5794837816528560377b52cfba1c2d0bda23800` |

| Field | Evidence-supported V2 interpretation | Remaining uncertainty |
|---|---|---|
| Daily OHLC price basis | Provider-staff-confirmed split/bonus-adjusted history | Exact factors, rounding, other action types and per-row adjustment versions absent |
| Dividends | Staff explicitly says prices are not dividend adjusted | Complete cash entitlement/payment series unavailable; price return is not total shareholder return |
| Rights, mergers, demergers, capital reductions | Not established by this answer | Known events require exclusions; absence of a returned event does not prove absence |
| Volume | Daily coverage differs from regular-session minute totals | No precise split/bonus volume formula confirmed; exclude cross-session volume features until compatible evidence exists |
| Candle close | Provider executed-trade historical candle close | Not automatically NSE's official closing-price calculation, guaranteed fill, or trade confirmation |
| Revisions | Historical prices may be readjusted | No supplied historical revision clock, original vintage or complete adjustment-factor series |

V2 may record the basis as
`PROVIDER_STAFF_CONFIRMED_SPLIT_BONUS_ADJUSTED_NOT_DIVIDEND` with this citation.
It must not label the complete adjustment/action contract independently verified.
Do **not** apply another split/bonus factor to this already adjusted series.

## Economically meaningful target now supportable with limitations

A defensible exploratory price-performance target is
`C[t+h] / O[t+1] - 1`, for predeclared horizons `h = 5, 10, 20`, where indices are
the complete observed-cohort session grid and both prices come from the same
immutable source snapshot. Enter at the next observed session's opening reference,
exit at the h-th subsequent observed session's closing reference. This models one
continuous holding interval and differs from V1's product of daily daytime returns.

This is a **split/bonus-adjusted price return**, excluding cash dividends, rights
entitlements and other distributions. It is final-vintage fixed-cohort research.
Known unsupported action windows must be excluded. Any still incomplete action
coverage must remain explicit and prevents claiming fully verified economic P&L.
Use the source's existing adjustments rather than inferred or fabricated factors.
The forward label requires every expected observed slot and the actual exit
candle; no row or trading day may be interpolated.

Chronological feature construction uses observations through `t` only. A feature
or label window crossing a known unsupported action is unavailable. A subsequent
action lookup may identify a retrospective exclusion but does not make knowledge
available to an earlier historical decision. Record that difference in manifests.
Contemporaneous publication history is absent, so historical training is not a
point-in-time availability replay even when mathematical feature lookahead is zero.

For actual new forecasts, the decision is the real inference timestamp **after**
input retrieval/publication evidence and **before** the verified next eligible
session opens. Do not pretend today's EOD was executable after publication. If the
forecast was recorded after an already elapsed next open, that horizon is not an
eligible prospective forecast; wait for a new complete observation/session or
explicitly version a different future entry target before issuing it.

Opening/closing bars provide observed reference prices, not guaranteed executions.
A cost scenario may apply declared proportional costs/slippage at those later
references and show reference-fill hypothetical returns, drawdown and turnover.
It must disclose that order feasibility, market impact, auction participation,
lot constraints and contemporaneous liquidity are unverified. Do not turn this
into verified executable profit or accepted economic edge. A total-return target
needs complete compatible cash/action entitlement treatment; it is not currently
established by the source evidence reviewed here.

If unsupported action or basis evidence makes a particular holding window
ineligible, fail that window rather than silently substitute a different target.
The limited alternative `C[t+1] / O[t+1] - 1` is next-session daytime price
performance from an earlier EOD decision, conditional on internally consistent
same-candle multiplicative adjustments. It is neither a five-session holding
target nor proof of executable profitability. Register any such alternative
separately; do not use its results to claim the holding-return target passed.

## Corporate-action endpoint: useful evidence, no completeness guarantee

[Official Corporate Actions documentation](https://upstox.com/developer/api-documentation/get-corporate-actions/)
specifies `GET /v2/fundamentals/{ISIN}/corporate-actions`. A successful response
has `status=success` and `data[]` containing `name`, `expiry_date` (ex/effective
date), `amount`, `ratio`, and `event_details[]` name/value pairs such as
announcement, ex and record dates. No date-range, pagination, history-start,
completeness, adjustment-factor or revision-version contract is documented.

A bounded probe should validate ISIN/request binding, response structure, event
dates and action names; count known events and earliest/latest dates; preserve
actual receipt/checksum lineage; report unsupported event/date formats rather
than guessing. Reconcile duplicate conflicting events as conflicts. An empty or
short recent list is not evidence of an action-free five-year history. Do not
derive a stock-split ratio's direction merely from the example `1:1` string.

The private historical-data permission expressly covers historical OHLCV and
derived private ML. The Analytics Token technically supports free read-only
Fundamentals GET access. Neither fact is a blanket redistribution grant for all
reference payloads. A bounded private action inspection and metadata audit can
inform exclusions; retain source scope and any residual reference-retention
uncertainty explicitly rather than enlarging the old permission by implication.
No outbound clarification was sent.

For this manual pilot, the narrow scope interpretation is transient action
inspection plus retained **derived exclusion metadata** (ISIN, event kind/date,
source/receipt/hash) needed to validate the permitted historical-ML experiment.
This is a disclosed interpretation of private derived-research use, not an
express separate licence for permanent raw Fundamentals datasets. Raw action
payloads should remain transient; no public redistribution or expanded automatic
Fundamentals collection follows from this interpretation.

## Permission, capacity and cohort expansion

The [specific 1 September 2026 Upstox staff reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3)
supports historical API retention and private feature/statistics/model retention
for personal noncommercial ML, subject to terms and rate limits. It supplies no
public market-data/adviser/commercial redistribution licence. Residual retention
and termination limits remain documented in the
[P34 source-use decision](p34-private-upstox-use-decision.md).

[Historical V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
documents daily data availability from January 2000 and up to ten years per
daily request. Its seven-position response specifies timestamp, OHLC, volume and
open interest but no complete identity echo, adjustment flag or historical
publication/revision clock. A documented provider capability is not proof of
actual coverage for a requested security. Pin exact verified key, ISIN, symbol,
raw checksum, retrieval time, returned range and validation/exclusion report.

[Standard historical API limits](https://upstox.com/developer/api-documentation/rate-limiting/)
are 50 requests/second, 500/minute and 2,000/30 minutes per API/user. A separately
bounded manual addition of 20 predeclared securities and necessary evidence calls
can fit these documented limits, using the existing shared quota reservation and
failure ledger. The old scheduled RELIANCE budget/configuration must remain
unchanged. There is no scientific benefit in expanding merely to advertise a
larger universe; first measure action quality and per-security observed coverage.

For a 50-name manual pilot, predeclare 20 additions by an explicit diversified
fixed-watchlist policy before examining their outcomes, resolve all identities
exactly, and report exclusions without winner-based replacements. This produces
a **current fixed-cohort retrospective** study, not historical NSE membership or
survivorship-free performance. Additional unattended cohort collection still
needs the user's separate approval and its own clock/calendar/quota/replay tests.

## Calendar, identity and availability controls

[Upstox instrument documentation](https://upstox.com/developer/api-documentation/instruments/)
describes current beginning-of-day instruments, recommends `instrument_key`
instead of reusable exchange tokens, and supplies current NSE_EQ/type-EQ/ISIN
fields. The recent staff answer above explicitly says historical BOD data is
unavailable. Current classifications, sector information and membership therefore
cannot certify historical common-equity eligibility. Never substitute current
NIFTY constituents or current company sectors as dated historical facts.

[NSE's 2026 capital-market calendar](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf)
and [2025 calendar](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf)
are dated exchange facts, including holidays and special Muhurat provisions.
Their existence does not certify a complete 2022–2026 session grid without later
amendments and special-session circulars. An observed union of cohort candle
dates is a useful explicitly observational grid; missing per-security slots must
invalidate affected windows. It must not be called an exhaustive NSE calendar.

[Dated Upstox market timing](https://upstox.com/developer/api-documentation/get-market-timings/)
provides exchange-specific opening/closing timestamps for a requested date.
[Holiday lookup](https://upstox.com/developer/api-documentation/get-market-holidays/)
provides current-year or specific-date holiday/open-exchange information. Use
independent dated evidence for prospective next-entry/session checks and current
collection; do not infer every weekday is tradable or invent guaranteed EOD
publication time. Retrospective retrieval timestamps are today's availability
evidence and must never be rewritten as historical publication timestamps.

NSE's [data-use policy](https://www.nseindia.com/static/market-data/nse-data-policy)
requires source-specific arrangements for direct NSE market data. A publicly
visible corporate-filings download is not an automatic free unrestricted
automated dataset licence. The present bounded Upstox scope should not be
replaced by unlicensed bulk direct-NSE acquisition merely to fill an evidence gap.

The official [Nifty Equity Indices methodology, March 2026](https://nsearchives.nseindia.com/content/indices/Method_NIFTY_Equity_Indices.pdf)
separately distinguishes bonus/split share changes, rights, special dividends,
mergers and demergers. This corroborates why different action types need distinct
treatment. It is an **index methodology**, not evidence of Upstox's price factors
or a permission to apply index divisor rules to an individual stock. It cannot
close the provider-specific rights/demerger gap.

## Decision for implementation

Proceed with a separately registered exploratory V2 split/bonus-adjusted
next-open-to-horizon-close **price-return** experiment, known-event exclusions,
complete observed windows and explicit residual action/vintage/execution limits.
Audit source-compatible momentum/trend/volatility and dimensionless candle
features; omit unverified volume-adjustment and dated sector/index features.
Keep V1 untouched. Historical V2 periods are development/walk-forward evidence;
none of the already inspected V1 final period is a new untouched test. Independent
confirmation requires genuinely later forecasts, matured compatible outcomes,
predeclared uncertainty/economic requirements and an actual independent reviewer.
