# P1 provider evaluation

Research completed 2026-10-05; sources reviewed 2026-10-04/05. Scope: NSE cash
equities, INR, EOD, historically reconstructible universe. **No provider selected
or approved.** No accounts, paid services, API credentials or real captures acquired.
P0 is complete by user approval. P2 remains prohibited.

The [source register](provider-research-sources.md) records source type, URL,
locator, evidence and retrieval limits. DOC, CLAIM and TERMS distinguish technical
documentation, vendor assertions and public licensing text. No executed contract
or empirical provider verification exists. Recommendations are explicitly separated
in [provider-decision.md](provider-decision.md).

## Evidence states and scope

Every capability cell uses exactly one state:

- **VERIFIED**: the narrowly stated fact is directly established in the cited
  documentation or public terms. This does not mean delivered data was tested.
- **PARTIALLY_VERIFIED**: some relevant evidence exists, but market scope,
  historical completeness, semantics or entitlement remains unproved.
- **UNKNOWN**: no adequate evidence establishes the required capability. An
  unavailable page or a current-only example cannot establish non-support.
- **NOT_SUPPORTED**: explicit documentation excludes the stated capability in
  the named product/plan. This does not exclude a future bespoke contract.

Numbers correspond to the user's 30 mandatory dimensions. Subrows keep distinct
actions, timestamp meanings and rights separate. Generic API facts never establish
NSE coverage. A documented field is not proof it is populated correctly. Rights
are evaluated for AlphaLens business/application use, not private investing.

## Capability matrix

| Dimension | NSE Data & Analytics | Global Datafeeds | EODHD |
| --- | --- | --- | --- |
| 1. NSE cash-equity product | VERIFIED — CM EOD specification [N2] | VERIFIED — NSE CM API documented [G1] | UNKNOWN — catalogue/legacy-page conflict [E1] [E2] |
| 2. Historical EOD OHLCV depth | PARTIALLY_VERIFIED — historical products exist; per-security EOD start/completeness absent [N1] | PARTIALLY_VERIFIED — daily since 2010 stated; completeness untested [G1] | UNKNOWN — global depth cannot establish NSE depth [E3] |
| 3a. Unadjusted prices | PARTIALLY_VERIFIED — exchange price fields; adjustment/vintage policy needs confirmation [N2] | VERIFIED — split adjustment can be disabled in GetHistory [G2] | PARTIALLY_VERIFIED — global raw OHLC documented, NSE entitlement unclear [E3] |
| 3b. Adjusted prices | UNKNOWN — no complete documented adjusted series established | PARTIALLY_VERIFIED — split-adjusted option, not total-return/action completeness [G2] | PARTIALLY_VERIFIED — global adjusted close, NSE unconfirmed [E3] |
| 4a. Splits | UNKNOWN — generic action-purpose file does not establish complete split events [N2] | PARTIALLY_VERIFIED — offering names splits [G13] | PARTIALLY_VERIFIED — global split endpoint, NSE unconfirmed [E4] |
| 4b. Dividends | UNKNOWN — amount/ex/payment-date completeness unverified | PARTIALLY_VERIFIED — offering names dividends [G13] | PARTIALLY_VERIFIED — global dividend endpoint, NSE unconfirmed [E4] |
| 4c. Bonuses | UNKNOWN — explicit event coverage/treatment not established | PARTIALLY_VERIFIED — offering names bonus issues [G13] | UNKNOWN — do not infer from splits |
| 4d. Mergers | UNKNOWN — complete event/successor mapping not established | PARTIALLY_VERIFIED — merger announcements claimed, not complete terms/mapping [G13] | UNKNOWN — no NSE event/successor evidence |
| 4e. Demergers | UNKNOWN — complete terms/allocation history not established | UNKNOWN — not established by generic action schema | UNKNOWN — no NSE event/allocation evidence |
| 4f. Symbol changes as events | UNKNOWN — current master is insufficient [N7] | UNKNOWN — current identifiers are insufficient | NOT_SUPPORTED — documented rename endpoint is US-only [E6] |
| 5. Delisted/departed prices and records | PARTIALLY_VERIFIED — deletion/status fields; historic retention unknown [N7] | UNKNOWN — no exhaustive departed inventory found | UNKNOWN — generic delisted examples do not verify NSE [E5] |
| 6. Historical ticker/company-name chains | PARTIALLY_VERIFIED — reference master, not proven historical chains [N7] | UNKNOWN — no effective-dated complete chain established | NOT_SUPPORTED — documented rename-history route excludes NSE [E6]; any alternative unknown |
| 7. Actual historical NIFTY 500 membership | UNKNOWN — separate NSE Indices licence/product required | UNKNOWN — monthly dumps do not prove historic/off-cycle ledger [G7] | NOT_SUPPORTED — standard historical membership is S&P-scoped [E7]; bespoke alternative unknown |
| 8. Historical sector assignments | UNKNOWN — taxonomy is not assignment history | PARTIALLY_VERIFIED — allocation-start field and classifications; retained history unknown [G6] | UNKNOWN — current sector fields are insufficient |
| 9a. Financial statements | PARTIALLY_VERIFIED — company-result schema [N4] | PARTIALLY_VERIFIED — financial-result types/values [G3] | PARTIALLY_VERIFIED — global statements; NSE unconfirmed [E7] |
| 9b. Ratios | PARTIALLY_VERIFIED — selected result ratios (such as return on assets); full ratio history unproved [N4] | PARTIALLY_VERIFIED — ratios offered [G13] | PARTIALLY_VERIFIED — global valuation fields; historical NSE scope unknown [E7] |
| 9c. Earnings | PARTIALLY_VERIFIED — company/quick-result records [N4] | PARTIALLY_VERIFIED — quarterly/annual results [G3] | PARTIALLY_VERIFIED — earnings reporting fields; NSE unknown [E7] |
| 9d. Fundamental publication timestamps | PARTIALLY_VERIFIED — timestamps exist; exact publication semantics unknown [N4] | UNKNOWN — prose/schema mismatch [G4] | UNKNOWN — filing date alone is not verified availability [E7] |
| 9e. Original and restated fundamentals | PARTIALLY_VERIFIED — revision linkage exists; historical originals unproved [N4] | UNKNOWN — version retrieval/retention unproved | UNKNOWN — no NSE vintage retrieval guarantee found |
| 10. Complete PIT suitability | UNKNOWN — originals/availability/coverage not demonstrated | UNKNOWN — original fundamentals and universe unproved | UNKNOWN — NSE coverage and original vintages unproved |
| 11. Separate timestamp meanings | PARTIALLY_VERIFIED — see PIT matrix [N4] | PARTIALLY_VERIFIED — action timing fields; not proven for fundamentals [G5] | PARTIALLY_VERIFIED — global fiscal/filing/reporting dates; not full PIT [E7] |
| 12. Whether historic fundamentals are overwritten | UNKNOWN — revision flag does not prove preservation | UNKNOWN — modification field does not prove preservation | UNKNOWN — current financial response is not a vintage audit |
| 13. Trading calendar | PARTIALLY_VERIFIED — official calendar; historic feed/licence unknown [N8] | UNKNOWN — exchange holiday links are not a historical calendar API | PARTIALLY_VERIFIED — XNSE calendar example, historical scope unknown [E9] |
| 14a. Pagination / complete retrieval | PARTIALLY_VERIFIED — dated file delivery, archive completeness untested [N2] | PARTIALLY_VERIFIED — range/max controls; truncation/boundaries untested [G2] | VERIFIED — generic ticker list is unpaginated; missing-symbol caveat [E16] |
| 14b. Bulk history | PARTIALLY_VERIFIED — file-based products, archive scope unknown [N1] | PARTIALLY_VERIFIED — ranged per-symbol retrieval; full backfill untested [G2] | PARTIALLY_VERIFIED — exchange/date bulk exists, NSE unconfirmed [E10] |
| 15. Rate/volume limits | UNKNOWN — transfer/archive quotas require agreement | PARTIALLY_VERIFIED — account-specific hourly/symbol quotas [G9] | VERIFIED — documented global request/call limits [E11]; actual entitlement not acquired |
| 16a. Reliability evidence | PARTIALLY_VERIFIED — redundant servers documented, not measured [N2] | PARTIALLY_VERIFIED — uptime claim, maintenance disclosed [G14] [G9] | PARTIALLY_VERIFIED — best-effort terms, no measured NSE service [E12] |
| 16b. Binding SLA | UNKNOWN — no AlphaLens agreement | UNKNOWN — uptime claim is not SLA | UNKNOWN — no scoped commercial SLA obtained |
| 25. Subscription/cost basis | PARTIALLY_VERIFIED — public tariff, full quote missing [N6] | PARTIALLY_VERIFIED — tailored quote required, amount unknown [G10] | PARTIALLY_VERIFIED — personal prices published, commercial quote unknown [E14] [E13] |
| 26. Trial/sample availability | PARTIALLY_VERIFIED — CM trade samples linked, scope not validated [N1] | PARTIALLY_VERIFIED — public examples; NSE representative sample not obtained [G3] [G7] | PARTIALLY_VERIFIED — demo/free offering; no NSE sample established [E3] [E14] |
| 27. Authentication | VERIFIED — CM SFTP key/static-IP/user-ID model [N2]; corporate protocol disputed | VERIFIED — access key in query [G8] | VERIFIED — API token in query [E16] |
| 28. Format/schema quality | PARTIALLY_VERIFIED — typed specification, binary/CSV summary conflict [N1] [N2] | PARTIALLY_VERIFIED — schemas/formats, diagnostic text exception [G8] | PARTIALLY_VERIFIED — structured formats, silent date fallback in bulk [E10] |
| 29. Provider revision behaviour | PARTIALLY_VERIFIED — revision fields, retention policy missing [N4] | PARTIALLY_VERIFIED — action modification metadata, retention missing [G5] | VERIFIED — adjusted-price history recomputed [E3]; fundamental version behaviour assessed separately in dimension 12 |
| 30. Demonstrated reproducible NSE research suitability | UNKNOWN — licensed complete archive and universe not tested | UNKNOWN — missing departed/universe/vintage evidence | UNKNOWN — coverage conflict plus historical-scope gaps |

No verified price product in row 1 certifies all eligible equities, series,
suspended names, delistings, history length or data accuracy. No action category is
inferred from an unexplained price jump. Row 6's NOT_SUPPORTED is scoped to the
documented EODHD endpoint; company-name prose on a profile is not a history service.

## Licensing and usage-rights matrix

These states address permission for AlphaLens's intended use. Public policy
evidence of a restriction does not constitute a grant. No private subscription may
be used as a shortcut to business research or application distribution.

| Dimension / permission | NSE Data & Analytics | Global Datafeeds | EODHD |
| --- | --- | --- | --- |
| 17. Store normalized data for AlphaLens | UNKNOWN — agreement-specific [N5] | UNKNOWN — product licence needed [G11] | UNKNOWN — private storage permission is not a business grant [E12] |
| 18. Retain exact raw responses/files | UNKNOWN | UNKNOWN | UNKNOWN |
| 19. Retain immutable historical snapshots/backups | UNKNOWN | UNKNOWN | UNKNOWN |
| 20. ML training, retraining and retained model artefacts | UNKNOWN | UNKNOWN | UNKNOWN |
| 21. Display provider data in AlphaLens | UNKNOWN — display tariff is not signed entitlement [N5] [N6] | UNKNOWN — needs written permission/exchange terms [G11] [G12] | UNKNOWN — separate commercial terms needed [E12] [E13] |
| 22. Display derived analytics/model outputs | UNKNOWN — non-display/derived definitions required | UNKNOWN — transformed data rights must be explicit | UNKNOWN — private repackaged-data restrictions do not grant model rights |
| 23. Redistribution restrictions | VERIFIED — agreement controls redistribution [N5] | VERIFIED — explicit written permission required [G11] | VERIFIED — personal redistribution/display prohibited [E12] |
| 24. Commercial-use restrictions | VERIFIED — intended use licensed and priced [N5] | VERIFIED — ordinary offer personal; exchange arrangement/fees needed [G12] | VERIFIED — business use requires commercial arrangement [E13] |
| 24a. Commercial app under ordinary personal plan | UNKNOWN — no applicable personal plan evaluated | NOT_SUPPORTED — ordinary personal API offer [G12] | NOT_SUPPORTED — personal-use terms exclude it [E12] |
| Additional: post-termination reproducibility/retention | UNKNOWN | UNKNOWN — breach-destruction clause is a material concern [G11] | UNKNOWN |
| Additional: cloud storage, subcontractors, geography, users/sites/media | UNKNOWN | UNKNOWN | UNKNOWN |

Seek written licences covering research and launch separately, including irreversibly derived
outputs, cached displays, exports, backup retention, deletion and model survival.
No public price is treated as permission to train or redistribute.

## Point-in-time suitability matrix

| Temporal capability | NSE Data & Analytics | Global Datafeeds | EODHD |
| --- | --- | --- | --- |
| Fiscal period distinct from delivery | VERIFIED — period boundaries [N4] | VERIFIED — fiscal period/year [G3] | VERIFIED — period versus filing fields, global schema [E7] |
| published_at / original public dissemination | PARTIALLY_VERIFIED — record timing requires semantic confirmation [N4] | UNKNOWN — result dates not established [G4] | UNKNOWN — date-level filing coverage/meaning for NSE unverified |
| available_at for licensed historical decision eligibility | UNKNOWN — timing disagreement and archive evidence absent | UNKNOWN — API receipt now cannot date historical knowledge | UNKNOWN — calendar/filing labels do not date historical availability |
| revised_at and immutable revision identity | PARTIALLY_VERIFIED — link/flag/create time [N4] | PARTIALLY_VERIFIED — action ID/modification metadata only [G5] | UNKNOWN — API version/UpdatedAt is not per-value vintage history |
| Ingestion time separate from publication | UNKNOWN — AlphaLens capture not performed | PARTIALLY_VERIFIED — provider receipt/save fields on actions [G5]; AlphaLens ingestion still separate | UNKNOWN — AlphaLens capture not performed |
| Event/session date separate from availability | PARTIALLY_VERIFIED — dated files/events [N2] | PARTIALLY_VERIFIED — trade epoch/event fields [G2] [G5] | PARTIALLY_VERIFIED — bar/event dates globally [E3] [E4] |
| Membership effective intervals and announcement times | UNKNOWN | UNKNOWN — monthly file has no proven complete change log | NOT_SUPPORTED — standard historical route excludes NIFTY 500 [E7] |
| Original statements retrievable after restatement | UNKNOWN | UNKNOWN | UNKNOWN |
| As-of sector assignments | UNKNOWN | PARTIALLY_VERIFIED — start field only, history unproved [G6] | UNKNOWN |
| Full intended NSE PIT backtesting inputs demonstrated | UNKNOWN | UNKNOWN | UNKNOWN |

`available_at` remains canonical in AlphaLens. Derive it only from documented
evidence about when the relevant version became accessible; preserve fiscal
period, publication, event, effective, revision and capture times separately.
An EOD publication schedule is neither the actual arrival time nor a safe fixed
historical timestamp. A date-only filing requires an explicitly justified
conservative policy later; do not silently assign midnight or a standard lag.

NSE provides the strongest documented ingredients for investigating PIT
fundamentals. This is an **inference about research priority**, not proof of a
usable PIT archive. GFD's action timestamps cannot be transplanted onto financial
statements. EODHD's stock statement endpoint's date filters for index history do
not implement as-of fundamental retrieval. Today's restated statements cannot be
made historical by changing their fiscal dates.

## Universe and survivorship assessment

All three fail to demonstrate the complete required historical universe now.
NSE's daily master is a promising audit input, GFD's monthly index delivery may
support checks at particular dates, and EODHD's generic delisted endpoint may help
in supported markets. None is proof of actual NIFTY 500 membership at every
historical decision date. [N7] [G7] [E5]

**Recommended route D: separately licensed NSE Indices membership data.** I1
establishes a credible product enquiry, not verified NIFTY 500 completeness. Obtain
a start-of-window roster, every regular and exceptional addition/removal, effective
dates and original announcement times, identifiers and all later-departed names.
Reconcile each interval against prices/actions and preserve corrections. Index
membership exit and exchange delisting are different events. An index level or
current constituent CSV cannot reconstruct actual membership. [I1] [I2]

If that route fails, propose **B**, historical NIFTY 50 over an independently
verified shorter interval, including all leavers, with a separately approved scope
change. This alternative is **not yet verified**. If neither universe can be
substantiated/licensed, choose **C**, delay the requirement and the historical
research gate. No change to approved historical NIFTY 500 scope is made here.

### Supplemental NSE Indices evaluation (not a standalone price provider)

This table explicitly limits the extra source to its potential membership role;
it does not inherit NSE Data & Analytics evidence or rights.

| Dimension(s) | Evidence state | Finding |
| --- | --- | --- |
| 1. NSE cash constituent coverage | PARTIALLY_VERIFIED | NSE index components offered [I1] [I2] |
| 2. Historical EOD OHLCV depth | UNKNOWN | Constituent prices are not a complete OHLCV service |
| 3. Adjusted/unadjusted prices | UNKNOWN | Methodology/coverage not established |
| 4. Splits, dividends, bonuses, mergers, demergers, symbol events | UNKNOWN | No complete event service established for any category |
| 5. Departed securities | UNKNOWN | Need retained prior constituents and all their records |
| 6. Historical ticker/name chains | UNKNOWN | Identifiers in a product are insufficient |
| 7. Historical NIFTY 500 membership | PARTIALLY_VERIFIED | Historical component product offered; exact archive unverified [I1] |
| 8. Historical sectors | PARTIALLY_VERIFIED | Taxonomy documented; assignment vintages unknown [I3] |
| 9. Statements, ratios, earnings, publication and restatements | UNKNOWN | Not established for this supplemental product |
| 10. PIT suitability | UNKNOWN | Full intervals and announcement times unverified |
| 11. Distinct fiscal/publication/availability/revision/ingestion times | UNKNOWN | Delivery schema/timestamp semantics not obtained |
| 12. Overwrite behaviour | UNKNOWN | Archive correction policy unknown |
| 13. Historical trading calendar | UNKNOWN | Not established by membership product |
| 14. Bulk/pagination | UNKNOWN | Licensed delivery specification unavailable |
| 15. Limits | UNKNOWN | Quote/technical confirmation needed |
| 16. Reliability/SLA | UNKNOWN | No scoped contract |
| 17. Storage | UNKNOWN | No AlphaLens licence |
| 18. Raw retention | UNKNOWN | No AlphaLens licence |
| 19. Snapshot retention | UNKNOWN | No AlphaLens licence |
| 20. ML training | UNKNOWN | No AlphaLens licence |
| 21. Application display | UNKNOWN | No AlphaLens licence |
| 22. Derived outputs | UNKNOWN | No AlphaLens licence |
| 23. Redistribution restrictions | VERIFIED | Website copying/distribution requires permission [I4] |
| 24. Commercial restrictions | VERIFIED | Website terms do not authorize commercial collection [I4] |
| 25. Subscription/cost | PARTIALLY_VERIFIED | Subscription offering; price unconfirmed [I1] |
| 26. Representative historical sample | UNKNOWN | No licensed sample obtained |
| 27. Authentication | UNKNOWN | No subscriber delivery details obtained |
| 28. Schema quality | PARTIALLY_VERIFIED | Component identifiers/weights/prices described; no schema audit [I1] |
| 29. Revision policy | UNKNOWN | Original/revised versions not demonstrated |
| 30. Reproducible historical suitability | UNKNOWN | Samples, rights and coverage gate still open |

## Cost and operational complexity

| Candidate/route | Public cost evidence (no purchase) | AlphaLens cost/complexity inference |
| --- | --- | --- |
| NSE Data & Analytics | CM EOD INR 100,000/year/site/display medium; corporate EOD INR 500,000/year/site [N6]. Archive/master/rights scope must be quoted separately. | High direct-feed integration burden: versioned files, schema transitions, archive reconciliation, permitted secure transport and availability evidence. No complete cost established. |
| Global Datafeeds | Tailored API quote [G10]; separate commercial obligations [G12] | Potentially simpler REST delivery. Historical symbol reconciliation, revision archives, monthly membership and separate rights remain substantial work. Cannot assert cheaper without quote. |
| EODHD | Personal USD 19.99 EOD / USD 59.99 fundamentals / USD 99.99 all-in-one monthly [E14]; commercial quote [E13] | Convenient API shape but unproven NSE scope; low advertised price cannot offset failed evidence gates. Marketplace additions can cost extra without solving NSE. |
| NSE Indices supplement | Subscription/quote, no public amount established [I1] | Additional contract and identity/effective-time reconciliation. Do not add a guessed price to a total. |

No currency conversion, discount assumption or estimated complete annual bill is
invented. Historical archive licence, users/sites/display media, cloud/backups,
taxes and derived/ML rights can change the total. Engineering effort is a qualitative
inference, not a measured benchmark. Recommendation/questions and the staged real
sample gate are in provider-decision.md and p1-validation-report.md.

<!-- Source URLs; evidence type and locator are in provider-research-sources.md. -->
[E1]: https://eodhd.com/list-of-stock-markets
[E2]: https://eodhd.com/financial-summary/STANLEY.NSE
[E3]: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes
[E4]: https://eodhd.com/financial-apis/api-splits-dividends
[E5]: https://eodhd.com/financial-apis/delisted-stock-companies-data-2
[E6]: https://eodhd.com/financial-apis/us-stock-symbol-rename-history-api
[E7]: https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds
[E9]: https://eodhd.com/financial-apis/exchanges-api-trading-hours-and-stock-market-holidays
[E10]: https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends
[E11]: https://eodhd.com/financial-apis/api-limits
[E12]: https://eodhd.com/financial-apis/terms-conditions
[E13]: https://eodhd.com/financial-apis/commercial-vs-personal-license-use
[E14]: https://eodhd.com/pricing
[E16]: https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours
[G1]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/introduction/type-of-data-available/
[G2]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/rest-api-documentation/function-gethistory/
[G3]: https://docs.globaldatafeeds.in/getfinancialresults-15575585e0
[G4]: https://docs.globaldatafeeds.in/getfinancialresultsitems-15575584e0
[G5]: https://docs.globaldatafeeds.in/corporateactionsitem-5999221d0
[G6]: https://docs.globaldatafeeds.in/sectoralclassificationitem-5999268d0
[G7]: https://docs.globaldatafeeds.in/index-constituents-933202m0
[G8]: https://docs.globaldatafeeds.in/authentication-request-response-923682m0
[G9]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/faqs/faqs/
[G10]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/pricing-sales/api-pricing/
[G11]: https://globaldatafeeds.in/terms-and-conditions/
[G12]: https://globaldatafeeds.in/global-datafeeds-nsebse-mcx-authorized-data-vendor/
[G13]: https://globaldatafeeds.in/fundamental-data-apis/
[G14]: https://docs.globaldatafeeds.in/
[I1]: https://www.niftyindices.com/offerings/data-subscription
[I2]: https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500
[I3]: https://www.niftyindices.com/resources/industry-classification
[I4]: https://www.niftyindices.com/terms-of-use
[N1]: https://www.nseindia.com/static/market-data/eod-historical-data-subscription
[N2]: https://nsearchives.nseindia.com//web/mediaattachment/2025-11/EOD_CM_20251120105001.pdf
[N4]: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/EOD_DATA-Corporate_EODv1.2.pdf
[N5]: https://www.nseindia.com/static/market-data/nse-data-policy
[N6]: https://nsearchives.nseindia.com//web/mediaattachment/2026-04/Download_Pricing_file_-_Domestic_clients_20260424122229.pdf
[N7]: https://nsearchives.nseindia.com//web/mediaattachment/2026-08/NSE-Masters_Data-v1.10_20260814161753.pdf
[N8]: https://www.nseindia.com/resources/exchange-communication-holidays
