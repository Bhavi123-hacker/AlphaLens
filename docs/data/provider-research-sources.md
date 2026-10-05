# P1 provider research evidence register

Reviewed 2026-10-04 to 2026-10-05 (Asia/Kolkata). Public documentation only;
no accounts, subscriptions, vendor correspondence, authenticated API calls or
market-data downloads. No vendor sample has been validated. URLs are primary
sources. Page content can change; locators and bounded evidence below record what
was observed. No entire vendor documents or credential-bearing examples are copied.

Evidence types: **DOC** = technical documentation; **CLAIM** = vendor product or
marketing statement; **TERMS** = public policy/terms, not an executed AlphaLens
contract. Inferences and recommendations are in provider-decision.md. These types
are distinct from the four capability evidence states in provider-evaluation.md.

## NSE Data & Analytics

| ID | Type; source and locator | Specific evidence and limit |
| --- | --- | --- |
| N1 | CLAIM; [EOD/historical products](https://www.nseindia.com/static/market-data/eod-historical-data-subscription), EOD and Historical Trade sections; updated 2026-09-02 | CM EOD and historical trade products; public CM trade sample links. Summary calls EOD files binary. Historical trade availability does not establish a complete daily-bar archive. Sample files were not downloaded. |
| N2 | DOC; [CM EOD specification v1.2](https://nsearchives.nseindia.com//web/mediaattachment/2025-11/EOD_CM_20251120105001.pdf), dated 2025-10-13, pp.7-14, 22 | SFTP user ID, public key and static IP; two active servers; dated TXT/CSV files. Price/volume and corporate-action-purpose schemas. Does not establish vintage retention or all corporate-action categories. |
| N3 | CLAIM; [Corporate products](https://www.nseindia.com/static/market-data/corporate-data-subscription), EOD announcement section; updated 2026-06-11 | EOD corporate delivery described as SFTP after 20:00 IST; annual domestic fee INR 500,000. Timing/protocol differs from N4. |
| N4 | DOC; [Corporate EOD v1.2](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/EOD_DATA-Corporate_EODv1.2.pdf), dated 2025-01-23, pp.8-17 | CSV/GZ, daily-reset sequences and completion trigger; FTP credentials and 22:40-23:45 IST download window. Financial period boundaries, revision/refiling/regrouping flag/link, result creation time and record timestamp. Meaning, original vintages and historical retention need confirmation. |
| N5 | TERMS; [Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy), Providing Market Data and Limitations sections | Intended use/handling/dissemination must be in the relevant agreement. Redistribution requires agreement; ownership stays with NSE. No AlphaLens retention, training or output rights established. |
| N6 | CLAIM/commercial tariff; [Domestic tariff effective 2026-04-01](https://nsearchives.nseindia.com//web/mediaattachment/2026-04/Download_Pricing_file_-_Domestic_clients_20260424122229.pdf), pp.7-8; linked from [tariff page](https://www.nseindia.com/static/market-data/products-tariff) | CM EOD INR 100,000/year/site/display medium; corporate EOD INR 500,000/year/site; historical CM trade INR 110,000/year/site. Taxes extra. Product fees do not prove archival entitlements, ML rights or total AlphaLens cost. |
| N7 | DOC; [Master data v1.10](https://nsearchives.nseindia.com//web/mediaattachment/2026-08/NSE-Masters_Data-v1.10_20260814161753.pdf), CM security section, pp.9-13 | Identifiers, security status/deletion, local database update time and ISIN. A current master with deletion flags does not prove complete historic identifier/name chains or retention of departed prices. |
| N8 | DOC; [Market timings and holidays](https://www.nseindia.com/resources/exchange-communication-holidays), calendar section | Exchange publishes session/holiday information and separately notified special-session timing. Complete historical machine-readable calendar and its licence remain unverified. |

## Global Datafeeds

| ID | Type; source and locator | Specific evidence and limit |
| --- | --- | --- |
| G1 | DOC; [Available data](https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/introduction/type-of-data-available/), NSE CM backfill table | NSE cash daily/weekly/monthly history advertised since 2010. No per-security completeness or departed-security inventory supplied. |
| G2 | DOC; [REST GetHistory](https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/rest-api-documentation/function-gethistory/), parameter/return tables | DAY requests, date range, maximum count, access key and JSON/XML/CSV. Split adjustment defaults on and can be disabled. Returns OHLC, traded quantity and epoch trade time. Dividend/bonus adjustment semantics and historical vintages are not specified. |
| G3 | DOC; [Financial results](https://docs.globaldatafeeds.in/getfinancialresults-15575585e0), return fields and request | Period/year, report type and standalone/consolidated requests; labelled values with units/precision. No documented as-of-vintage selector in the inspected request. Example is BSE, so it does not validate NSE coverage. |
| G4 | DOC; [Financial result items](https://docs.globaldatafeeds.in/getfinancialresultsitems-15575584e0), description and sample; [query-item schema](https://docs.globaldatafeeds.in/finresultsqueryitem-5999232d0) | Prose mentions publication dates, but listed fields/sample expose year, instrument, report nature/type and fiscal period. Actual publication timestamp and revision linkage are not established by that sample. |
| G5 | DOC; [CorporateActionsItem](https://docs.globaldatafeeds.in/corporateactionsitem-5999221d0), schema | Separate announcement, event, modification, receipt and save dates, action identifier, ISIN and reference number. No proof of original-vintage retrieval, timestamp timezone, NSE completeness or event taxonomy. |
| G6 | DOC; [SectoralClassificationItem](https://docs.globaldatafeeds.in/sectoralclassificationitem-5999268d0), schema; [classification endpoint](https://docs.globaldatafeeds.in/getsectoralclassification-15575605e0) | Four classification levels, allocation-start date, ISIN and receipt/save timestamps. Historical change chain and effective-end semantics are unverified. |
| G7 | DOC; [Index constituents](https://docs.globaldatafeeds.in/index-constituents-933202m0), delivery table; modified 2025-08-03 | NSE/BSE constituent CSV dumps by email monthly, annual subscription; identifiers/ISIN/company/industry. Historical NIFTY 500 archive, announcement/effective dates and off-cycle changes not established. |
| G8 | DOC; [Authentication/request/response](https://docs.globaldatafeeds.in/authentication-request-response-923682m0) | Access key in GET query; configurable formats; diagnostic text may replace data. Requires bounded error handling and credential redaction, not blind retries. |
| G9 | DOC; [API FAQ](https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/faqs/faqs/), limits and maintenance | Symbol and hourly quotas depend on account; 1,800/3,600/7,200 are examples, not AlphaLens entitlements. Scheduled maintenance windows documented. |
| G10 | CLAIM/commercial; [API pricing](https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/pricing-sales/api-pricing/), pricing/notes | API pricing requires a tailored quote. Desktop prices are not an API/commercial quote. Plain-text diagnostics and session restrictions are documented. |
| G11 | TERMS; [Terms](https://globaldatafeeds.in/terms-and-conditions/), Licence/Warranty | Redistribution needs explicit written permission; source-exchange obligations remain with users. Breach termination requires destruction of licensed materials. No specific ML, raw archive, snapshot or model-output grant. |
| G12 | CLAIM/licensing explanation; [Authorised-vendor FAQ](https://globaldatafeeds.in/global-datafeeds-nsebse-mcx-authorized-data-vendor/), commercial-use answer | Ordinary API offers are personal; commercial use requires exchange agreement and fees. This is an explanation of restrictions, not an executed commercial licence. |
| G13 | CLAIM; [Fundamental product](https://globaldatafeeds.in/fundamental-data-apis/), features | Advertises dividends, splits, bonuses, merger announcements, financial results/ratios and annual reports. No complete NSE action/filing audit is provided. |
| G14 | CLAIM; [Fundamentals introduction](https://docs.globaldatafeeds.in/), Why us | Claims exchange sourcing and 99.995% uptime; no measured AlphaLens availability or contractual SLA established. |

## EODHD

| ID | Type; source and locator | Specific evidence and limit |
| --- | --- | --- |
| E1 | DOC; [Current exchange catalogue](https://eodhd.com/list-of-stock-markets), displayed exchange list | NSE/India was absent from the rendered pricing/fundamentals catalogue. Absence is not proof of permanent non-support. |
| E2 | CLAIM, stale page; [STANLEY.NSE summary](https://eodhd.com/financial-summary/STANLEY.NSE), heading/as-of | NSE-labelled INR instrument page exists but returned an as-of date in October 2025. Linked NSE exchange page failed. This conflicts with assuming current NSE entitlement from old instrument pages. No prices copied as evidence of accuracy. |
| E3 | DOC; [EOD API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes), adjustment/schema/history sections | Raw OHLC, split-adjusted volume, split/dividend-adjusted close; adjusted close is recomputed through history. Single-symbol date ranges, CSV/JSON. Global/US depth examples do not establish NSE history or original-volume access. |
| E4 | DOC; [Splits/dividends](https://eodhd.com/financial-apis/api-splits-dividends), endpoint/schema sections | Split ratios and dividend dates/amounts are documented globally. NSE completeness, bonuses, merger/demerger treatment and version retention unverified. |
| E5 | DOC; [Delisted data](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), availability table | Delisted list and regular endpoints; before-2018 table limits data to EOD. Examples do not establish an exhaustive NSE departed-security inventory. |
| E6 | DOC; [Symbol rename history](https://eodhd.com/financial-apis/us-stock-symbol-rename-history-api), scope | Explicitly US-only, beginning 2022-07-22. This endpoint cannot supply NSE rename history. |
| E7 | DOC; [Fundamentals](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds), Financials/Earnings/Indices | Statements have period and filing dates; earnings have reporting dates. Standard historical membership covers specified S&P families; historical snapshots are S&P 500-only. No NSE fundamental vintage-retention guarantee found. API version is not data revision identity. |
| E8 | CLAIM/DOC; [Constituent marketplace](https://eodhd.com/marketplace/unicornbay/spglobal), product description | S&P/Dow Jones membership product; no NIFTY 500 evidence. Broader wording elsewhere cannot establish Indian index coverage. |
| E9 | DOC; [Trading hours/holidays](https://eodhd.com/financial-apis/exchanges-api-trading-hours-and-stock-market-holidays), v2 list/fields | XNSE appears in example calendar codes; trading hours and holidays are separate from price-exchange coverage. Historical completeness untested. |
| E10 | DOC; [Bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends), parameters | Whole exchange for one date; paid entitlement required. Non-session/future dates can resolve to another session. Response dates require validation. NSE delivery untested. |
| E11 | DOC; [API limits](https://eodhd.com/financial-apis/api-limits), limits/call-cost tables | Default 1,000 requests/minute; free 20 calls/day, paid from 100,000/day. EOD costs 1, fundamentals 10, whole-exchange bulk 100 calls. Request quota differs from billable call quota. |
| E12 | TERMS; [Terms](https://eodhd.com/financial-apis/terms-conditions), Personal/Commercial, Provision, Termination | Private non-commercial storage/analysis allowed; personal redistribution/display prohibited. Availability is best-effort, no uninterrupted/error-free warranty. AlphaLens commercial retention/training/output rights ungranted. |
| E13 | CLAIM/licensing explanation; [Commercial use](https://eodhd.com/financial-apis/commercial-vs-personal-license-use) | Personal packages do not authorize business/group use; separate commercial quote required. |
| E14 | CLAIM/commercial; [Pricing](https://eodhd.com/pricing), personal-plan table | Monthly USD 19.99 EOD, USD 59.99 fundamentals, USD 99.99 all-in-one. Commercial quote separate. Free plan/trial described, but no NSE sample validated. |
| E15 | CLAIM/provenance; [Sources and partners](https://eodhd.com/financial-apis/our-data-sources-and-data-partners) | Some EOD feeds have exchange contracts; others use CFDs/market makers. Named contracts do not establish NSE provenance. Fundamentals are compiled/standardized. Obtain product-specific source evidence. |
| E16 | DOC; [Exchange/ticker API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours), parameters/behaviour | Token authentication; active and delisted queries separate; symbol list has no pagination and can silently omit unmatched requested symbols. Full-response retrieval does not prove complete historical coverage. |

## Supplemental source: NSE Indices Limited

This is a separate entity/product/permission boundary, not an entitlement bundled
with NSE Data & Analytics prices and not a complete alternative price provider.

| ID | Type; source and locator | Specific evidence and limit |
| --- | --- | --- |
| I1 | CLAIM; [Data subscription](https://www.niftyindices.com/offerings/data-subscription), product description | Ongoing/historical constituent data with names, identifiers, weights and prices is offered. NIFTY 500-specific start date, daily/off-cycle completeness, publication timing, departed members, cost and granted rights require confirmation. |
| I2 | DOC; [NIFTY 500 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500), Downloads | Constituent download is presented with current index information; it is not a historical membership ledger. |
| I3 | DOC; [Industry classification](https://www.niftyindices.com/resources/industry-classification) | Four-level taxonomy documented; historical company assignments and taxonomy versions not established. |
| I4 | TERMS; [Website terms](https://www.niftyindices.com/terms-of-use), clauses 7, 12, 20 | Copying/distribution and automated collection need permission; site use limited to personal/non-commercial use. Public visibility is not a data licence. |

## Retrieval limitations and conflicts

- NSE tariff initially timed out; a later fetch succeeded. A historical-trade PDF
  fetched initially but timed out on follow-up; no precise history-depth assertion
  relies on it. The separate dotex terms PDF could not be retrieved; N5 was read.
- A guessed NSE master-data URL failed; the official Paid Master Data link and
  specification succeeded. The static holiday URL failed; the official linked URL
  succeeded. Neither failure is evidence that the underlying product is absent.
- EODHD's NSE exchange page returned 404 and its legacy instrument link failed.
  E1/E2/E9 describe conflicting coverage signals, not verified current NSE prices.
- Public documentation examples were inspected as documentation only. Embedded
  demo keys were not used or copied to project files. No example numerical values
  were ingested, no raw market payload was retained, and no provider was contacted.
- NSE's binary-versus-CSV description and corporate protocol/time disagreement,
  GFD's publication-date prose versus result schema, and EODHD's mixed sourcing
  statements are unresolved. They block corresponding adapter assumptions.
- Resume spot-checks confirmed the primary membership offering, NSE revision
  fields and usage policy, GFD split toggle/restrictions, and EODHD's catalogue,
  historical-index scope and personal-use restrictions. NSE N4 p.12 also repeats
  cumulative/noncumulative descriptions under its consolidated reporting field;
  the decision report flags this mapping conflict. N4 p.15 also documents selected
  result ratios, including return on assets; this does not prove a ratio-history
  product. No new provider was approved.

Searches also covered delisted names, historical sector assignments, revisions,
retention, ML/display rights and SLA terms. No adequate evidence found means
UNKNOWN, not NOT_SUPPORTED. Search-engine snippets and third-party/forum content
were discovery leads only, not the basis for a passed capability or licence.
