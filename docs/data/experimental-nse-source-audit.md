# Experimental NSE source audit — 16 October 2026

This is a source and methodology assessment for the independently authorized
`ALPHALENS_EXPERIMENTAL_NSE_V1` pilot. It does not amend frozen P9–P14 research,
accepted ranking gates, the existing RELIANCE collection task or public-demo rights.
The checks below used public primary documentation; no credential or authenticated
market request was used for this audit.

## Private research permission

The [official Upstox support conversation, substantive reply dated 1 September
2026](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302)
expressly supports retaining historical API observations, derived statistics,
features and model artifacts for private non-commercial research, including ML.
It conditions this on applicable API terms and rate limits. This independently
reconfirms the existing [P34 scoped decision](p34-private-upstox-use-decision.md).
The reply is staff support evidence, not a bespoke executed exchange licence;
commercial use, public redistribution and adviser readiness are not established.
Keep raw observations, trained artifacts and private predictions in ignored,
protected local storage. Publish only code, provenance metadata and suitably
aggregated evaluation evidence. Retention/deletion obligations are not exhaustively
specified by this reply.

Permission reference:
`UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN`.

## Historical observations and budgets

[Historical Candle V3 documentation](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
defines exact instrument-key requests and timestamp/OHLC/volume/open-interest
response positions. Daily interval one has documented availability from January
2000 and a maximum ten-year range per request. This is a provider capability,
not proof that each selected security has that coverage. The response does not
echo a complete ISIN/symbol identity, publish an adjustment-basis field, or supply
historical publication/revision clocks. Pin the current verified master identity,
exact requested key, original response checksum, retrieval timestamp and dates.
Do not infer historical universe membership or historical availability from a
present retrieval.

[Standard API limits](https://upstox.com/developer/api-documentation/rate-limiting/)
cover historical candles: 50 requests/second, 500/minute and 2,000/30 minutes,
per API and user. A manually bounded pilot of one historical request per selected
instrument plus one master request is far smaller. Preserve the shared quota
ledger, explicit per-run budget, failure accounting and zero-request snapshot
replay; do not widen the existing scheduled worker's budget. Provider permissions
are not permission to download the complete market automatically.

## Adjustment and action evidence

[Corporate Actions API](https://upstox.com/developer/api-documentation/get-corporate-actions/)
is keyed by ISIN and documents dividends, splits, bonus and rights events,
including announcement/ex/record dates and amounts or ratios. It documents no
history-start guarantee, exhaustive coverage flag, revision chronology or
machine-verifiable adjustment relationship to candle data. Retaining a valid
response supports known-event exclusions; an empty response does not establish
an action-free history. Do not derive split factors from this contract alone.

The [official NSE corporate-action filings page](https://www.nseindia.com/companies-listing/corporate-filings-actions)
offers dated company/purpose filters and CSV download. It is useful for checking
specific events. The public page alone does not establish unrestricted automated
retention, complete point-in-time histories or an adjustment factor dataset.
This audit did not acquire its market records or infer additional storage rights.

Conclusion: provider candle adjustment basis and complete action coverage remain
`UNKNOWN`. Raw close-to-close, cross-session moving-average levels, ATR using a
previous close, volume comparisons across split boundaries and economic
buy-and-hold labels require additional compatible evidence. An unknown field
must remain visible even if a limited independent experiment is computable.

## Defensible limited pilot despite that uncertainty

The following is an engineering/mathematical inference, not an Upstox guarantee.
Within a candle, a uniform positive multiplicative price adjustment cancels from
`close/open`, `high/low`, body/range and close-location ratios. Therefore a
predeclared pilot can use same-session ratios and their trailing moments/sign
persistence without crossing an overnight split or dividend price discontinuity.
Require valid positive OHLC ordering, finite ratios, original timestamps, nonzero
denominators where required, and complete observed windows. Preserve action
uncertainty; known action windows may be excluded rather than adjusted. This
approach is not invariant to additive or inconsistent OHLC adjustments, bad
provider data or identity changes. It is limited research under that disclosed
within-candle consistency assumption.

A matching target can be the sign of the sum of future five observed-session
`log(close/open)` observations. Its magnitude describes compounded daytime price
movement. Name it precisely: **five observed sessions of open-to-close movement**.
It is not a five-day holding return, dividend-inclusive total return, an attainable
execution return or verified investment profit. Compare with predeclared trailing
daytime momentum and training-majority baselines. Do not report ordinary
buy-and-hold drawdown, turnover or cost-adjusted economic performance as verified
from this target. Illustrative daily-reset turnover/cost sensitivities need their
own explicit execution assumptions and cannot prove profitability.

Separate feature chronology from data vintage: only observations dated through
the feature date enter a vector; targets must mature before the next split;
normalization fits training only; shared dates stay in the same partition.
Retrospective observations downloaded now remain final-vintage/current-cohort
research, not historical point-in-time availability. Today's forecasts are recorded
at the actual inference time and may support future prospective evaluation only.

## Calendar options and limits

[NSE capital-market 2026 circular 71775, dated 12 December
2025](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf) supplies
dated holidays, including 20 October 2026, and identifies 8 November Sunday
Muhurat trading with timing to follow. [2025 circular 65587, dated 13 December
2024](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf) likewise
records annual holidays and special Muhurat trading. Annual schedules need later
amendments and special-session circulars before becoming exhaustive session
calendars; weekdays alone are insufficient.

[Upstox holidays documentation](https://upstox.com/developer/api-documentation/get-market-holidays/)
describes the current year and optional specific-date lookup, with exchange-level
closures and special timing. Its current-year bulk reply is not a historical
calendar. Retain the existing independently guarded dated timing checks for live
collection. No quote-timestamp relaxation is needed for historical experiments.

For a bounded retrospective pilot without a complete official historical
calendar, a separate observational grid may use the union of actual source candle
dates across the predeclared cohort. Keep that grid explicitly classified as
observed cohort dates. A security missing a grid date has missing data, not a
fabricated candle or presumed non-trading day. Exclude incomplete rolling/target
windows. Horizon maturity then means observed-session count, not certified NSE
session completeness. Do not use the grid to promote existing retained-ingestion
or accepted-model eligibility. Actual coverage and exclusion counts belong in
the experiment's dataset manifest and activation report.
