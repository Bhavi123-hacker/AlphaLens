# Provider evaluation checklist

Status: pre-selection; no subscriptions, credentials, trial access or real samples.
Source DOCX §§6.8, 23, 24, 27. No shortlist entry is approved.

| Candidate | Public documentation leads | Current decision |
| --- | --- | --- |
| NSE Data & Analytics | [Historical/EOD products](https://www.nseindia.com/static/market-data/eod-historical-data-subscription), [usage policy](https://www.nseindia.com/static/market-data/nse-data-policy) | NOT SELECTED; all AlphaLens-specific capabilities/rights UNKNOWN. |
| Global Datafeeds | [Price API example](https://globaldatafeeds.in/resources/API_Example_pdf/GFDL_REST_GetHistory_JSON_FORMAT.pdf), [fundamental offering](https://docs.globaldatafeeds.in/) | NOT SELECTED; coverage/depth/PIT/rights UNKNOWN. |
| EODHD | [Delisted documentation](https://eodhd.com/financial-apis/delisted-stock-companies-data-2) | NOT SELECTED; Indian-market coverage cannot be inferred from US examples. |

Links are investigation leads, not proof of licensed capabilities. No price or
commercial plan is assumed. Current contract terms and written evidence are
needed for selection; no automatic vendor contact or purchase is authorized.

## Mandatory evidence matrix

For EACH candidate, every item below is currently UNKNOWN. Record status,
verification date, source/sample/contract reference, exact market/date scope and
observed limitations before marking VERIFIED_SUPPORTED or VERIFIED_UNSUPPORTED.

1. NSE cash equity coverage and stable instrument/ticker mapping.
2. Earliest/latest actual EOD history per security; target 10–15 years where reliable.
3. Delisted, merged, renamed, suspended and newly listed securities.
4. Historical NIFTY 500 effective membership and departed-member prices.
5. Historical sector and identifiers; index/benchmark coverage and methodology.
6. Corporate actions, raw versus adjusted prices, split/dividend/bonus adjustments.
7. Historical fundamentals with original publication, availability and revisions;
   fiscal period labels alone do not establish PIT correctness.
8. Exchange sessions/holidays and timestamps; units/currencies/volume/turnover.
9. Full pagination/bulk history, update/revision policy, API quotas/latency/outages.
10. Real representative sample, source discrepancies and documented completeness.
11. Subscription costs, ongoing costs, access requirements; all are UNKNOWN now.
12. Written rights: raw retention, backups, training, derived outputs, application
    display, redistribution/export, cached values, sample commitment and termination.
13. Source/data residency, deletion/retention obligations and post-termination
    reproducibility constraints.

## Selection gate

No weighted score can compensate for failed licensing or unavailable required
historical universe/PIT data. One provider may be insufficient; separate price and
reference/fundamental sources would need explicit mappings and conflict policy.

Selection requires evidence, approved access and an explicit licensing assessment.
Unknown is not unsupported, and unsupported is not silently acceptable. If historical
NIFTY 500 is infeasible, report evidence and propose a smaller reconstructible
universe for user approval. A smaller data set must still include departed securities
and honest availability. Do not invent that alternative before evidence exists.

## Real sample protocol (blocked)

Choose actual securities after access: ordinary long history, action cases, rename/
delisting, recent listing, missing-session case, original/revised filing and dated
membership changes. Probe oldest claimed coverage separately. Verify data and
license scope; do not persist anything until retention rights are established.
Require raw checksums, mapping methodology and replay comparisons. Record all gaps.
TEST-ONLY fixtures are never substitutes for these real-provider tests.
