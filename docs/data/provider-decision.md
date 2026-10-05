# Current research-fixture scope notice

The subsequent user-approved D36-D39 decision accepts bounded, local CC BY Mendeley
research fixtures with residual risk. P1 DEVELOPMENT validation is reported in
[p1-validation-report.md](p1-validation-report.md). This does not approve any paid
provider or live-market service. PRODUCTION_DATA_CLEARANCE remains OPEN.
The full preceding provider/free-source research below is retained as historical
evidence; its earlier no-sample/no-adapter statements describe that earlier scope.

---

# Current V1 decision: zero paid dependencies

Updated 2026-10-05 after the accepted provider research. D26-D35 in
[DECISIONS.md](../../DECISIONS.md) govern current scope. **No provider or adapter is
approved. P1 remains incomplete; P2 is prohibited.**

The earlier paid recommendation below was accepted as evidence, not approved for
implementation. Paid NSE Data & Analytics/NSE Indices, Global Datafeeds and EODHD
options are **ineligible as mandatory V1 dependencies**. Do not spend money, seek a
trial that later requires payment, or treat any old enquiry/purchase checklist as
current authorization.

The best conditional free investigation path is official dated NSE CM reports
plus historical reference/identity/action/session evidence. Public delivery alone
does not clear ML, backtesting, raw retention or output rights. MCP is not a
training-data fallback merely because it exposes historical queries.
No compatible end-to-end free dataset has yet been established.

- Prefer a dynamic, historically evidenced NSE universe; historical NIFTY 500 is
  optional. Current constituents never seed history.
- Disclose verified legally usable depth per family; no unconditional 10-15-year
  V1 gate or empirical five-year claim.
- FUNDAMENTAL_PIT_DATA = UNAVAILABLE; sector context is optional unless PIT-safe.
  Technical ML is a future conditional experiment, not demonstrated performance.
- Local free/open-source runtime is sufficient; cloud/auth/monitoring cannot
  introduce a mandatory paid dependency.
- The neutral provider.py remains unchanged. Its NIFTY_500-only universe literal
  and reported mapping gaps require versioned P1 review before any real mapping;
  the current task implements no adapter or schema change.
- Proposed P1_V1_FREE_v1 still requires compatible rights, a real representative
  sample, reproducible normalization/checksums and historical-universe evidence.
  None is passed by synthetic fixtures or documentation research.

Current evidence: [free source matrices](free-data-evaluation.md).
Proposed methodology, ML constraints, source-owner questions and sample protocol:
[free-data-strategy.md](free-data-strategy.md).
Current gate: [p1-validation-report.md](p1-validation-report.md).

## Historical record: original paid-provider recommendation retained verbatim

Everything below describes the earlier research state at
`f8400265f6e6877da4154a916d87cd163a59071d`. Its paid-selection, mandatory historical
universe and full-scope recommendations are superseded by the amendments above.
Its evidence, limitations and findings are preserved; they are not current approval.

---

# P1 provider decision recommendation

As of 2026-10-05: **NOT SELECTED; NOT APPROVED FOR PURCHASE OR ADAPTER WORK.**
This is a research recommendation for user review, not an amendment to DECISIONS.md
or a claim that a vendor satisfies the complete specification. Evidence states,
all 30 dimensions and source limitations are in [provider-evaluation.md](provider-evaluation.md)
and the [evidence register](provider-research-sources.md). P0 is complete. P2 remains
prohibited. No vendor contact, account, purchase or API capture occurred.

## Ranked recommendation

| Rank | Candidate/role | Reason and condition |
| --- | --- | --- |
| PRIMARY | NSE Data & Analytics for cash prices/reference/corporate disclosures; separately licensed NSE Indices membership | Strongest route to authoritative provenance and documented revision ingredients. Obtain exact archives, rights, samples and commercial quote before deciding. Not an assertion that every historical input exists. [N2] [N4] [I1] |
| SECONDARY / FALLBACK | Global Datafeeds for price delivery and potentially corporate data, with separate historical membership source | EOD since 2010 and raw/split-adjusted retrieval documented. Could simplify delivery if complete departed history and business rights are proved. PIT fundamentals and historical membership still unproved. [G1] [G2] [G7] |
| REJECTED FOR CURRENT REQUIREMENTS | EODHD as the sole/primary NSE source | Current NSE coverage is unresolved, documented rename-history route excludes NSE, and standard historical membership excludes NIFTY 500. Reconsider only with scoped evidence; rejection does not mean every EODHD product is unsupported. [E1] [E2] [E6] [E7] |

Ranking is an architectural judgement, not a weighted score, approval, cost
comparison or measured quality ranking. Unknown licensing, universe or PIT inputs
cannot be compensated for by convenient APIs. None passes the complete P1 gate.

## What the primary recommendation establishes

**Verified at documentation level:** CM EOD product, SFTP access mechanism and
typed file specification; public agreement-based usage restrictions. **Partially
verified:** historical products and corporate revision/timestamp ingredients.
No real sample has established completeness, accuracy or historical preservation.
[N1] [N2] [N4] [N5]

**Still UNKNOWN:** daily-bar archive depth for each security, original and revised
filing retention, publication/availability semantics, complete action/identifier
chains, departed coverage, historical sector assignments, SLA, full cost and all
AlphaLens-specific storage/raw/snapshot/ML/display/derived-output rights.

**Before money is spent:** obtain a product-specific written rights schedule and
itemized quote; resolve the documentation conflicts below; confirm budget and
historical scope; inspect a legally usable representative sample with the supplier.
The user must explicitly approve purchase/selection and subsequent adapter work.
Where delivery requires payment before samples, request another evidence route;
do not pay to discover whether a mandatory requirement exists.

**One provider sufficient?** Not demonstrated. Plan for at least a price/reference
source plus a separately entitled universe source. NSE Data & Analytics and NSE
Indices must not be treated as a single licence. A further PIT fundamentals source
may be necessary if NSE cannot supply original historical vintages. No such third
supplier is selected or assumed in this recommendation.

**Historical NIFTY 500 feasible?** Plausible through route **D**, a separate NSE
Indices licence, but unverified for the requested history and all exceptional
changes. This is a conditional feasibility inference from an actual constituent
product offering, not a reconstructed dataset. [I1]

**PIT fundamentals feasible?** Potentially, if original/revised disclosures,
stable revision links and evidenced public availability survive in the historical
archive. The documented fields make NSE the best enquiry target. They do not prove
that 10-15 years of originals can be retrieved. Full PIT fundamental support remains
UNKNOWN for every evaluated primary candidate.

## Proposed multi-source boundary (design only)

| Input | Proposed responsibility after approval | Consequence |
| --- | --- | --- |
| Prices/reference identifiers | NSE primary, GFD fallback after equivalent evidence | Keep source-specific representations behind actual vendor adapters; independently license fallback. |
| Corporate actions/disclosures | NSE products; GFD only if evidence proves equivalent coverage | Price adjustment must agree with action definitions and timing; incomplete actions block affected research. |
| Membership | NSE Indices historical component product | Separate source ID, licence, effective interval and publication evidence; no current-constituent substitution. |
| Fundamentals | NSE archive conditional on original-vintage proof | If unavailable, seek a separately evaluated source or request a fundamentals-excluding research scope. |

Reconcile securities using exchange/series, valid-dated identifiers and evidence
of corporate transitions. ISIN is useful but is not an eternal company identity;
mergers, share classes and identifier changes need explicit links. Never join
sources solely on today's ticker or company name. Preserve each source/version
and eligibility evidence. Conflict resolution must be documented; never average
conflicting records or switch vendors invisibly. Licences must permit combining
and retaining both feeds, and distributing the intended resulting outputs.

A composite domain boundary could delegate methods to approved adapters later.
The neutral MarketDataProvider method interface remains unchanged. Missing vendor
evidence is not a reason to relax required timestamps. The schema deficiencies
below must be resolved before real normalization. Calendar/reference representation
and large-file sample slicing also need review against actual samples. No composite,
calendar engine or ingestion pipeline is implemented in P1 research.

### Contract findings requiring a versioned schema review

Inspection of `ml/data/src/alphalens_data/contracts.py` against the reviewed
documentation exposes limitations in the current bounded foundation:

- `FundamentalRecord` has a period end but no period start/duration/type or
  standalone/consolidated basis. GFD explicitly distinguishes these [G3]. Losing
  them could conflate annual/quarterly or different reporting scopes. Add distinct
  period and reporting-basis metadata before accepting such records.
- `Provenance` has revision identity but no separate revision instant. A provider
  modification time must not be forced into publication, availability or ingestion.
  Preserve an evidenced optional revision time and its meaning; do not invent one.
- `PriceBar` has volume but no explicit volume-adjustment basis. EODHD documents
  adjusted volume beside raw OHLC [E3]. Reject an incompatible mapping until raw
  volume is obtained or a versioned schema represents the distinction explicitly.
- Identifier and sector histories lack typed records/methods here. Keep raw source
  evidence and design the neutral reference boundary before accepting such data;
  do not hide those histories in today's ticker or sector string.
- Runtime capability enum values differ from this research's four evidence
  states. Documentation VERIFIED is not automatic runtime VERIFIED_SUPPORTED;
  PARTIALLY_VERIFIED and untested required coverage must remain runtime UNKNOWN.
- Universe contracts currently accept only NIFTY_500. The proposed NIFTY 50 fallback
  needs user-approved scope and a deliberate schema change; it cannot be relabelled.

These are reported remediation requirements, not silently implemented migrations
or evidence that the existing schema already covers production provider semantics.
No financial/data code changed in this research commit. A versioned P1 contract
review with meaningful tests is required before approved adapter implementation.

Costs rise through separate entitlements, archive purchases, renewals, identifier
maintenance and reconciliation. A second feed does not automatically fill missing
historical versions. Obtain total cost for the agreed window and rights before
accepting this architecture; no price or infrastructure budget is invented.

## Contradictions and unresolved semantics to report

1. NSE product overview calls EOD files binary; the current CM technical document
   lists TXT/CSV. Confirm exact product/version and migration boundaries. [N1] [N2]
2. Corporate overview says SFTP after 20:00 IST; its linked technical document says
   FTP credentials and a 22:40-23:45 window. Confirm secure transport, actual release
   process and historic availability evidence. Do not hard-code either schedule.
   [N3] [N4]
3. GFD financial-item prose mentions publication dates, while its listed schema
   contains fiscal identifiers. Require actual timestamp/version fields and their
   semantics; descriptive prose alone does not pass PIT. [G4]
4. EODHD's current exchange catalogue omits NSE, but older NSE-labelled pages and
   an XNSE calendar example exist. A calendar code and stale page do not establish
   a current price entitlement. [E1] [E2] [E9]
5. EODHD describes some direct exchange contracts and other market-maker/CFD
   sourcing. Obtain the exact NSE product's provenance and licence; do not
   extrapolate either provenance claim to every feed. [E15]
6. EODHD's general historical-index language is broader than its standard
   S&P-only historical details and marketplace's S&P/Dow Jones description. No
   NIFTY membership claim follows from those statements. [E7] [E8]
7. NSE's corporate financial schema labels a field consolidated/non-consolidated
   but repeats cumulative/noncumulative descriptions for its values. Obtain the
   correct reporting-basis mapping; do not implement that apparent documentation
   error as financial semantics. [N4]

No conflict is resolved by changing AlphaLens policy or implementing an assumption.
This completes independent research while the affected selection gate stays open.

## Questions requiring written sales/support answers

These are prepared questions, **not sent messages**. Answers need product name,
version, market, time window, evidence/sample reference and contractual scope.

### All candidates / proposed licensors

1. Supply a per-security inventory with earliest/latest dates, missing sessions,
   listing/delisting/suspension status, symbol/ISIN transitions and all departed
   members for the proposed research window. Are any dead securities omitted?
2. Supply raw OHLCV and exact adjustment rules for every action type: splits,
   dividends, bonuses, mergers, demergers and renames. Is volume raw? Can prior
   adjustment vintages be retrieved? How are corrections identified?
3. Can you return a fundamental value as originally known and again after each
   revision, with fiscal period, public disclosure time, provider availability,
   revision link, timezone, source filing and correction history? Demonstrate an
   original/restated pair. Are any periods overwritten? How far back is this true?
4. Can you deliver actual NIFTY 500 start rosters and all dated changes, including
   off-cycle deletions, formerly listed companies, announcement time and effective
   interval? What is the oldest fully verified interval? Can NIFTY 50 be quoted
   separately if NIFTY 500 cannot be reconstructed?
5. Can historical sector assignments and taxonomy revisions be obtained as known
   then? Can historical calendar exceptions and changes be licensed?
6. Explicitly permit or deny: normalized storage, exact raw responses, immutable
   snapshots/backups, developer/test environments, cloud/subprocessors, ML training
   and retraining, weights/model retention, application price display, derived
   analytics/prediction display, exports, user counts and each distribution medium.
   Identify exchange pass-through requirements and all deletion obligations.
7. What survives expiry/termination: raw records, original/revised snapshots,
   audit hashes, derived features, trained weights, evaluation results and public
   outputs? Can old experiments legally be reproduced after subscription ends?
8. Provide complete costs: initial historical archive, updates, reference/actions,
   membership, commercial/non-display/ML/display/derived rights, support, taxes,
   users/sites/media and renewals. No bundle assumptions.
9. Provide rate/symbol/file limits, pagination/truncation guarantees, bulk methods,
   daily completion/correction markers, schema version policy, incident process,
   secure authentication and contractual SLA/remedies for the EOD products.
10. Provide a bounded representative sample with evaluation/retention permission,
    covering a departed member, each action category, a rename, listing, suspension,
    off-cycle index change, oldest coverage and original/restated filing pair.

### NSE Data & Analytics / NSE Indices

- Resolve corporate transport/time and price-file format conflicts. Which current
  documents and tariff rows bind the offered products?
- Does historical access include all original daily corporate files, trigger/release
  metadata and corrections, or only a current restated view? How do daily-reset
  sequences combine with dates/record type to form a stable identity?
- Are constituent histories supplied by NSE Indices under a distinct contract?
  Give exact NIFTY 500 history bounds, exceptional changes, licence and delivery
  schema. Does the price archive cover every member, including former ones?

### Global Datafeeds

- Are NSE CM histories since 2010 available for every departed/delisted security?
  How are renamed instruments retrieved and identifiers linked historically?
- What does split adjustment do for bonuses, volume, dividends and restructurings?
- Can monthly constituents be supplemented with all effective-dated changes and
  backfilled actual NIFTY 500 membership, with announcement evidence?
- Clarify financial publication fields, original/revised retrieval, and whether
  action receipt/save timestamps reflect provider arrival rather than public release.

### EODHD

- Is NSE cash currently supported under a licensed product? Resolve the omitted
  catalogue entry, failed exchange page, legacy instrument pages and calendar code.
- Identify NSE price provenance and contract chain; distinguish exchange records
  from indicative/CFD data. Provide departed coverage and event completeness.
- Is an NSE rename/history or NIFTY 500 product available beyond the documented
  US/S&P routes? Provide actual product evidence rather than a global assertion.
- Demonstrate NSE original/restated financials; are filing dates actual release
  dates, and are fiscal histories silently replaced? Quote commercial rights.

## Scope and exit decision

**AlphaLens cannot yet pass P1.** The original roadmap gate requires a representative
historical set through the abstraction. Research, schema fixtures and supplier
documentation do not satisfy it. No paid service, adapter or P2 is approved here.

A **reduced but scientifically valid scope is a conditional proposal**, not a
passed alternative: prices/actions only, a fully evidenced historical NIFTY 50
universe or shorter verified NIFTY 500 interval, all leavers included, and no claims
about fundamental predictions. It still requires licence, actual data, as-of
membership and representative validation plus explicit user scope approval.
If those cannot be obtained, delay historical research rather than substitute
today's survivors. Full intended scope remains the target until amended by the user.

<!-- Source URLs; evidence type and locator are in provider-research-sources.md. -->
[E1]: https://eodhd.com/list-of-stock-markets
[E2]: https://eodhd.com/financial-summary/STANLEY.NSE
[E3]: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes
[E6]: https://eodhd.com/financial-apis/us-stock-symbol-rename-history-api
[E7]: https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds
[E8]: https://eodhd.com/marketplace/unicornbay/spglobal
[E9]: https://eodhd.com/financial-apis/exchanges-api-trading-hours-and-stock-market-holidays
[E15]: https://eodhd.com/financial-apis/our-data-sources-and-data-partners
[G1]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/introduction/type-of-data-available/
[G2]: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/rest-api-documentation/function-gethistory/
[G3]: https://docs.globaldatafeeds.in/getfinancialresults-15575585e0
[G4]: https://docs.globaldatafeeds.in/getfinancialresultsitems-15575584e0
[G7]: https://docs.globaldatafeeds.in/index-constituents-933202m0
[I1]: https://www.niftyindices.com/offerings/data-subscription
[N1]: https://www.nseindia.com/static/market-data/eod-historical-data-subscription
[N2]: https://nsearchives.nseindia.com//web/mediaattachment/2025-11/EOD_CM_20251120105001.pdf
[N3]: https://www.nseindia.com/static/market-data/corporate-data-subscription
[N4]: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/EOD_DATA-Corporate_EODv1.2.pdf
[N5]: https://www.nseindia.com/static/market-data/nse-data-policy
