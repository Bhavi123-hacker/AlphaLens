# P33 source and activation assessment — 15 October 2026

This is a source-specific technical/contract assessment, not a licence grant or
legal opinion. Existing explicit private read-only observation scope is retained.
No paid product is purchased and no background acquisition is activated.

| Question | Official evidence and applicability | Current implementation / required activation evidence |
| --- | --- | --- |
| Automated technical access | [Analytics Token, Supported APIs / Restrictions](https://upstox.com/developer/api-documentation/analytics-token/) describes a free, one-year read-only token, including market quotes, history, information and fundamentals without a static IP. It states “only GET APIs are supported”. | Explicit private GETs use backend-only protected token; this is access evidence, not a durable ML/redistribution grant. |
| Quotas | [Rate Limits, Other Standard APIs](https://upstox.com/developer/api-documentation/rate-limiting/) documents 50/s, 500/min, 2,000/30min per API/user. | P28 quota ledger and smaller explicit request budgets remain. No whole-universe polling or retry loop. |
| Private caching / durable retention | [Terms, Data retention](https://upstox.com/terms-of-use-and-privacy-policy/) concerns “customer data such as personal, financial, and transactional information”. | That clause does not license market-data storage. The existing maximum 600-second transient scope is an application limit, not a claimed contractual allowance. Durable acquisition needs the applicable market-data end-user agreement with explicit permitted storage/duration. |
| Private ML / derived views | Reviewed token and general terms do not establish the specific retained-model use needed here. | Require the applicable upstream/broker agreement covering private analysis, ML and derived presentation; keep research ingestion/inference separately gated. |
| Redistribution | [NSE Data Policy, Limitations on Usage, clauses 6.1–6.5](https://www.nseindia.com/static/market-data/nse-data-policy) makes intended use agreement-specific and permits redistribution only “except as agreed in the Relevant Agreement”. Scope includes market/corporate data; research use has separate documentation. | No real data in public demo. Provider authentication does not supply redistribution rights. |
| Free direct NSE research | [NSE disclaimer, Research-oriented data](https://www.nseindia.com/static/nse-disclaimer) describes a 2GB threshold with accredited-institution/research-organisation eligibility and possible NDA/reporting requirements. | Not a universal free ingestion licence. Do not scrape/collect based solely on web accessibility. |

## Newly documented current-reference endpoints

[Company Profile](https://upstox.com/developer/api-documentation/get-company-profile/)
documents `/v2/fundamentals/{isin}/profile`, with business description, sector and
**sector** market cap (not company market cap). It supplies no historical
classification vintage in the reviewed schema. [Key Ratios](https://upstox.com/developer/api-documentation/get-key-ratios/)
and [Corporate Actions](https://upstox.com/developer/api-documentation/get-corporate-actions/)
document current financial reference and dated event lists. Their existence does
not establish revision/publication completeness or consistent price adjustments.

P33 adds an explicit authenticated, verified-current-ISIN three-GET reference view,
maximum 600-second memory, with per-operation unavailable states. No raw responses
are saved, used in personal backups, applied to P15 quantities or promoted to P6
historical features. Empty events never mean complete action coverage. Current
provider sector is not silently a historical NSE taxonomy. Explicitly loaded current
sector evidence supports current-provider sector preference checks and cost-basis
exposure summaries with coverage disclosed. Historical sector filters, company
market-cap filters and fundamental growth/value/dividend suitability remain
unsupported until compatible timestamp/identity/taxonomy and use evidence is
established. Actual endpoint receipts are recorded in the final report.

## Remaining source families and exact requirements

| Input | Candidate official source | Evidence needed before a real integration/activation |
| --- | --- | --- |
| Sector/security taxonomy | Upstox current company profile; NSE dated security/master files | Authoritative taxonomy, dated effective intervals, historical revisions and allowed local use. No current-sector backfill. |
| Company market cap | Issuer shares-outstanding filings plus compatible dated price; provider company-specific ratios if explicitly defined | Company-level units/date, issued vs free-float shares, action handling. Sector cap is not a substitute. |
| Statements/ratios | [NSE XBRL filing information](https://www.nseindia.com/static/companies-listing/xbrl-information), issuer investor-relations disclosures, documented Upstox statement/ratio endpoints | Original filing, publication/receipt/revision clocks, period and consolidated/standalone basis, units, retention/research-use rights. No retroactive PIT assumption. |
| Dividends/splits/bonus | NSE corporate-action filings and provider event reference | Known-at clock, ex/record/effective dates, complete coverage and exact P15 adjustment semantics; no price-jump inference. |
| Earnings timeline | Exchange/issuer dated announcements | Verified publication and event clocks; proposed vs actual event distinction. No invented calendar. |
| Historical index membership/benchmark | NSE Indices official dated constituent/index records | Departed/renamed coverage, per-date knowledge, licensed non-display/derived/retained use. Current lists cannot reconstruct history. |

After genuine source clearance, the existing protected P30/P19 release workflow
must first verify one retained official session and its identity/calendar/quality/
revision receipt. P33 generalises the bounded worker to an explicit verified key
in an isolated per-instrument operational subroot; default legacy capture paths
remain unchanged. Publication delays remain pending, corrections become new
revisions, and replay/resume uses pinned captures. CLI configuration may select
one verified key; at most three GETs/run. Register/enable no task until source,
calendar, retention, permitted analysis and operator gates all pass. Scheduling,
outbound alerts and current-model publication remain independent disabled actions.
