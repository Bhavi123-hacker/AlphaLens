# P34 private Upstox source-use decision — 15 October 2026

New evidence changes the previous unresolved private-retention assessment. It
does not amend any frozen dataset or grant public redistribution/model acceptance.

[Official community topic17302, post3, 1September2026](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3)
responds to a specifically private, non-commercial question about API historical
OHLCV retention, derived features, backtesting and private ML. The reply states:

> Yes, you can retain the historical data obtained through the Upstox API locally

The rest of the reply permits private feature/statistics/model retention and
private ML development without a separate licence for that use, subject to API
terms/rate limits. This is specific market-data evidence, unlike customer-data
retention language. The first response was by a community administrator/manager;
the substantive response is by Anand_Sajankar, whose public Discourse profile
and post metadata identify **Software Engineer, Upstox**. Reviewed the actual
thread, not just a search snippet. The user profile is not admin/moderator; the
staff title and official-hosted support conversation are recorded accurately.

The [Analytics Token announcement](https://upstox.com/developer/api-documentation/announcements/analytics-token/)
describes programmatic retrieval/analytics pipelines; the
[token contract](https://upstox.com/developer/api-documentation/analytics-token/)
documents read-only GET access to historical/market data. Combined with the
specific private-use reply, this supports bounded repeated private historical
retrieval and retention. [Documented rate limits](https://upstox.com/developer/api-documentation/rate-limiting/)
remain mandatory. The much smaller existing three-GET worker budget is retained.

| Operation | P34 decision | Actual scope |
| --- | --- | --- |
| Private local historical OHLCV retention | ACCEPTED_WITH_SOURCE_SPECIFIC_SUPPORT_EVIDENCE | Single authorized operator, non-commercial; new ignored protected operational root |
| Private derived features/statistics/ML artifacts | PERMITTED_PRIVATE_RESEARCH_USE | Permission alone supplies no compatible basis, peers or model acceptance |
| Repeated programmatic EOD retrieval | ACCEPTED_FOR_BOUNDED_PRIVATE_COLLECTION | Existing read-only token, quotas, exact verified key, official elapsed past session |
| Own local derived analytics/portfolio display | PRIVATE_ANALYSIS_SCOPE_ONLY | No raw export, public access or adviser-readiness claim |
| Public raw/derived data or model/signal redistribution | NOT_CLEARED | The question expressly excludes these activities; no new public display |
| Production or financial-advice readiness | NOT_CLEARED | Independent security/model/regulatory requirements remain |

The exact permission reference propagated into new P19 request identities is
`UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN`.
Original P30 denied-access configuration remains unchanged. A new private P34
configuration and isolated operational root use these scoped permissions. No
global gate defaults, P6 formula, artifact allowlist or acceptance rule changes.

Residual limits: this is provider staff's written interpretation, not an executed
bespoke agreement. No account-specific API clickwrap document was available in the
repository. Future applicable terms can restrict this scope; keep access personal,
non-commercial, private and within quotas. The reply does not state an explicit
retention duration or exhaustive termination obligations. No broader commercial or
exchange redistribution rights are inferred. A ready-to-send clarification follows;
it has **not** been sent by the agent.

## Optional remaining clarification to Upstox

Subject: Confirm private Analytics Token EOD retention scope and applicable terms

Hello Upstox API Support,

Your engineer's1September2026 reply in topic17302/post3 permits private historical
API-data retention, feature generation, backtesting and ML artifacts. AlphaLens is
a single-operator, non-commercial local research application with no broker orders
or public real-data access. We intend one bounded daily NSE-equity EOD retrieval,
private local OHLCV/features/models and a private derived research/portfolio view.

Please identify the applicable API/market-data agreement/version and confirm any
storage-duration, automated retrieval, deletion or token/account-termination
conditions for that precise scope. Does the private-use confirmation cover the
local derived dashboard as well as offline analysis? We understand it does not
authorize raw/derived/model/signal redistribution or a public market-data service;
please identify any separate permission that those different uses would require.

No token, account identifier, financial records or market payload is attached.
