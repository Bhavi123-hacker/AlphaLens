# P1 free official-data evidence review

Reviewed 2026-10-05. Scope: NSE cash equities, INR, EOD, zero paid dependencies.
This is public-source research, not source approval, data ingestion or a legal
permission grant. No accounts, purchases, vendor messages, MCP calls, bulk downloads,
adapters or numerical datasets were created. The earlier
[paid-provider evidence](provider-research-sources.md) remains historical evidence.

**Finding:** official public reports are a credible technical investigation path,
but a complete, legally compatible free ML/backtesting dataset is **not established**.
No empirically verified continuous price-history interval exists in AlphaLens yet.
Five years is a documented MCP claim, not an acquired or permission-cleared dataset.
See [strategy and proposed validation](free-data-strategy.md) for the conditional
universe method and [P1 status](p1-validation-report.md) for the unpassed gate.

## Evidence rules

Each matrix cell assigns exactly one state to its narrowly stated capability:

- VERIFIED: directly observed fact in an official document, public terms or named
  artifact. This does not verify all records, delivery quality or usage permission.
- PARTIALLY_VERIFIED: relevant official evidence exists, but coverage, delivery,
  semantics or the required entitlement is incomplete or untested.
- UNKNOWN: adequate evidence was not obtained; failed retrieval does not prove absence.
- NOT_SUPPORTED: the named public route explicitly lacks the stated capability or
  grant. This is scoped to that route, not a claim about every product of the owner.

DOC = official documentation/catalogue; CLAIM = an advertised capability not tested;
TERMS = public conditions, not an executed agreement; ARTIFACT = directly read public
filing/page. Matrix judgments and the proposed architecture are our inferences,
identified as such, rather than promises by NSE. Sources/locators are recorded below.

## Evaluated source boundaries

| Source | Exact scope |
| --- | --- |
| S1 | NSE public daily CM bhavcopy/UDiFF and historical daily-report archive. [F01] [F02] [F03] [F04] |
| S2 | Public security files, current tradable-security downloads, company-name/symbol changes and series classification. [F01] [F05] [F06] |
| S3 | NSE MCP historical bhavcopy route only; live tools excluded from V1. [F07] |
| S4 | NSE public corporate-action reports. [F08] |
| S5 | Public financial results, announcements and annual reports, including named real disclosure examples. [F09] [F10] [F11] [F12] [F13] |
| S6 | NSE Indices historical index levels and return-index downloads. [F14] |
| S7 | NIFTY 500 current constituent download and public industry taxonomy; not a historical constituent product. [F15] [F16] |
| S8 | NSE research-data request route and data catalogue, within its free eligibility/volume conditions. [F17] [F18] [L02] |
| S9 | NSE security-wise historical price/volume report. [F19] |
| S10 | NSE public delisted-company list and separate proposed-delisting lists. [F20] |
| S11 | NSE public holiday/session notices. [F21] |

## Access and historical coverage matrix

Payment-free access below distinguishes a readable public page from delivery of a
usable data file. No subscription or guaranteed continuing access is inferred.
Per-date coverage means security-level coverage usable to reconstruct that date's
opportunity set, not an index value or a current search result.

| Source | 1. Access without payment | 2. Historical depth | 3. Bulk retrieval | 4. Per-date security coverage | 5. Departed/delisted visibility |
| --- | --- | --- | --- | --- | --- |
| S1 | PARTIALLY_VERIFIED — public file catalogue; payload not tested. [F01] | PARTIALLY_VERIFIED — archives listed; oldest complete interval unknown. [F02] | PARTIALLY_VERIFIED — dated files/multiple-download control; delivery untested. [F01] | PARTIALLY_VERIFIED — daily whole-market report concept, completeness untested. [F01] | UNKNOWN — old files may contain leavers; none validated. |
| S2 | PARTIALLY_VERIFIED — public CSV/GZ links, no payload capture. [F01] [F05] | UNKNOWN — complete historical reference snapshots not established. | PARTIALLY_VERIFIED — security/changes files listed. [F05] | UNKNOWN — current reference is not an as-of archive. | UNKNOWN — change lists alone do not establish departed retention. |
| S3 | PARTIALLY_VERIFIED — no-auth configuration documented, endpoint not invoked. [F07] | PARTIALLY_VERIFIED — rolling five-year claim, not measured coverage. [F07] | PARTIALLY_VERIFIED — bulk quotes advertised, not full dated export. [F07] | UNKNOWN — historical all-security enumeration not demonstrated. | UNKNOWN — delisted-symbol lookup/retention not demonstrated. |
| S4 | PARTIALLY_VERIFIED — public date/purpose report and download control. [F08] | UNKNOWN — complete action-history bounds not established. | PARTIALLY_VERIFIED — CSV control, truncation/ranges untested. [F08] | UNKNOWN — event list is not a complete daily security roster. | UNKNOWN — all departed-company actions not established. |
| S5 | VERIFIED — named public announcement and historical PDF read without payment/account. [F12] [F13] | PARTIALLY_VERIFIED — a 2020 filing exists; no continuous panel demonstrated. [F13] | UNKNOWN — bulk original-vintage statement archive not established. | UNKNOWN — submissions do not enumerate all tradable securities. | UNKNOWN — departed-company filing retention untested. |
| S6 | PARTIALLY_VERIFIED — public historical CSV controls; payload not tested. [F14] | UNKNOWN — actual earliest/latest complete interval untested. | PARTIALLY_VERIFIED — date-range/index downloads documented on page. [F14] | NOT_SUPPORTED — index-level series do not enumerate constituents. [F14] | UNKNOWN — component prices/history not established by index levels. |
| S7 | PARTIALLY_VERIFIED — public current-constituent link/taxonomy page. [F15] [F16] | NOT_SUPPORTED — current download is not historical membership. [F15] | PARTIALLY_VERIFIED — current list download, not past rosters. [F15] | UNKNOWN — dated historical membership ledger not established. | UNKNOWN — today's list cannot establish former members. |
| S8 | PARTIALLY_VERIFIED — conditional free research scheme; AlphaLens eligibility unknown. [L02] | UNKNOWN — free supplied archive bounds/coverage not confirmed. | PARTIALLY_VERIFIED — request route and aggregate volume condition. [F17] [L02] | PARTIALLY_VERIFIED — daily available-security datasets catalogued, no delivery tested. [F18] | UNKNOWN — free delivery of complete departed histories not confirmed. |
| S9 | PARTIALLY_VERIFIED — public report/filter/download page. [F19] | PARTIALLY_VERIFIED — five-year/custom filters, not proof of populated coverage. [F19] | PARTIALLY_VERIFIED — security-wise CSV control; all-market bulk absent from evidence. [F19] | UNKNOWN — symbol-first querying does not establish a historical roster. | UNKNOWN — retrieval of every former symbol not tested. |
| S10 | PARTIALLY_VERIFIED — public delisted-company spreadsheet link. [F20] | UNKNOWN — complete date bounds and original snapshots untested. | PARTIALLY_VERIFIED — list download; payload not examined. [F20] | UNKNOWN — does not establish all securities present on each date. | PARTIALLY_VERIFIED — actual-delisted list separately named from proposed lists. [F20] |
| S11 | VERIFIED — public holiday page and special-session note read. [F21] | UNKNOWN — complete historical exception calendar not established. | UNKNOWN — historical machine-readable calendar export not established. | UNKNOWN — session schedule does not establish per-security tradability. | UNKNOWN — no departed-security coverage established. |

## Corporate actions, identity and revisions matrix

| Source | 6. Corporate actions | 7. Identifiers | 8. Revisions |
| --- | --- | --- | --- |
| S1 | UNKNOWN — price bars are not a complete action ledger. | UNKNOWN — exact free-payload identifier fields/mapping not verified; linked field-format retrieval failed. | PARTIALLY_VERIFIED — provisional/final naming documented; correction vintages not proved. [F04] |
| S2 | PARTIALLY_VERIFIED — name/symbol changes listed; economic actions not established. [F05] | PARTIALLY_VERIFIED — security/change lists and series legend; valid-dated identity chains untested. [F05] [F06] | UNKNOWN — historical original/revised master retention not documented here. |
| S3 | UNKNOWN — general catalogue language does not prove action-adjustment coverage. | PARTIALLY_VERIFIED — symbol search advertised; stable historical identity unknown. [F07] | UNKNOWN — overwrite policy and earlier vintages not established. |
| S4 | PARTIALLY_VERIFIED — purpose/date report; complete event terms and coverage untested. [F08] | PARTIALLY_VERIFIED — company/symbol report context; historical crosswalk untested. [F08] | UNKNOWN — original/corrected event retrieval and announcement linkage unproved. |
| S5 | UNKNOWN — a general announcement route does not prove economic-action coverage. | VERIFIED — named announcement identifies company and symbol; no claim of a stable crosswalk. [F12] | PARTIALLY_VERIFIED — actual restatement narrative found; original/revised numeric pairs unvalidated. [F13] |
| S6 | UNKNOWN — constituent-level action factors not established. | PARTIALLY_VERIFIED — named index selector, not security IDs. [F14] | UNKNOWN — corrected index-value vintages not established. |
| S7 | UNKNOWN — no complete economic-action history established. | PARTIALLY_VERIFIED — current constituents/taxonomy; dated security classifications unproved. [F15] [F16] | UNKNOWN — original historical roster/taxonomy assignments not established. |
| S8 | PARTIALLY_VERIFIED — action/disclosure datasets catalogued; free scope needs confirmation. [F18] | PARTIALLY_VERIFIED — security datasets catalogued; exact free schema untested. [F18] | UNKNOWN — version-preserving free archive not confirmed. |
| S9 | UNKNOWN — complete adjustment/action ledger not established. | PARTIALLY_VERIFIED — symbol/series filters; permanent historical links unproved. [F19] | UNKNOWN — replacement/correction behavior untested. |
| S10 | PARTIALLY_VERIFIED — delisting information route only. [F20] | PARTIALLY_VERIFIED — company list advertised; stable historical identifier mapping untested. [F20] | UNKNOWN — as-published list versions untested. |
| S11 | UNKNOWN — no security-action capability established. | UNKNOWN — not a security-identity source. | UNKNOWN — later timing notices do not prove preserved historical calendar revisions. |

## Retention and usage matrix

Restrictions are evidenced separately from granted rights. UNKNOWN retention means
no compatible AlphaLens grant established, not unrestricted copying. The ML column
assesses research/training/backtesting permission for this project. Application
display and derived/model outputs require their own scope even when raw data is hidden.

| Source | 9. Retention/raw snapshots | 10. Automated-access constraints | 11. ML/research implications | 12. Display/derived-output implications |
| --- | --- | --- | --- | --- |
| S1 | UNKNOWN — project retention grant unresolved. [L01] | NOT_SUPPORTED — general site terms prohibit systematic automated collection. [L01] | UNKNOWN — no project grant; simulation restriction is material. [L01] | UNKNOWN — no app/derived-output grant established. [L01] |
| S2 | UNKNOWN — project retention grant unresolved. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — compatible project permission absent. [L01] | UNKNOWN — no app/crosswalk redistribution grant. [L01] |
| S3 | UNKNOWN — immutable raw/snapshot retention grant absent. [F07] | PARTIALLY_VERIFIED — official MCP protocol offered for constrained uses; bulk limits unknown. [F07] | NOT_SUPPORTED — MCP access explicitly does not grant model-training/fine-tuning permission. [F07] | PARTIALLY_VERIFIED — informational noncommercial scope; commercial deployment excluded, project output rights unresolved. [F07] |
| S4 | UNKNOWN — retention grant unresolved. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — compatible project permission absent. [L01] | UNKNOWN — derived-adjustment/display grant absent. [L01] |
| S5 | UNKNOWN — reading a filing does not settle project retention rights. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — public disclosure is not a training/backtest licence. [L01] | UNKNOWN — filing/derived-output rights unresolved. [L01] |
| S6 | UNKNOWN — project archive/snapshot grant absent. [L03] | NOT_SUPPORTED — automated collection requires express written consent not obtained. [L03] | UNKNOWN — personal access does not establish model/benchmark permission. [L03] | UNKNOWN — app/index/derived-output rights unresolved. [L03] |
| S7 | UNKNOWN — project snapshot grant absent. [L03] | NOT_SUPPORTED — automated collection needs consent not obtained. [L03] | UNKNOWN — current roster access does not grant training use. [L03] | UNKNOWN — constituent/taxonomy/output rights unresolved. [L03] |
| S8 | UNKNOWN — institution-specific terms/NDA and retention not obtained. [L02] | UNKNOWN — approved delivery/automation conditions not obtained. [L02] | PARTIALLY_VERIFIED — eligible noncommercial research scheme exists; project eligibility/use not confirmed. [L02] | UNKNOWN — research access is not a user-facing distribution grant. [L02] |
| S9 | UNKNOWN — project retention grant unresolved. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — simulation/ML permission unresolved. [L01] | UNKNOWN — project display/derived grant absent. [L01] |
| S10 | UNKNOWN — project retention grant unresolved. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — model/research use not granted here. [L01] | UNKNOWN — project redistribution/output rights absent. [L01] |
| S11 | UNKNOWN — versioned project archive rights unresolved. [L01] | NOT_SUPPORTED — general site collection prohibition. [L01] | UNKNOWN — incorporation into project research not clarified. [L01] | UNKNOWN — project redistribution scope unresolved. [L01] |

### Binding limitations to resolve before collection or modelling

NSE terms clause 8 reserves storage/display and other uses to written permission,
with a download-related exception whose scope does not clearly clear this project.
It also prohibits simulation uses. Clause 9 prohibits systematic automated collection.
Clause 2 allows area-specific terms to take precedence. Obtain an explicit source-
and-purpose clarification covering backtesting, retention and outputs; local use
and the no-real-trades boundary are not inferred exemptions. [L01]

The MCP page's integration/AI language is not a training licence. Its disclaimer
limits purposes and expressly withholds training permission from access alone.
Use of an open-source client could avoid a paid assistant dependency, but would not
solve data rights. No rate limit, SLA, bulk-history guarantee or revision policy was
verified for that route. [F07]

The research route limits free data to an aggregate 2 GB and eligible academic/
research institutions or think tanks; purpose restrictions and possible NDA/reporting
requirements apply. AlphaLens qualification and ML/backtest/output permissions are
unknown. Do not split requests to evade the cap or assume chargeable archive items
are free because adjacent catalogue entries are public. [L02] [F17] [F18]

NSE Indices also reserves content uses, requires consent for automated collection
and describes personal noncommercial access. An index download link is not a
licence for app redistribution or model outputs. [L03]

These are conservative project gating judgments from published terms. No agreement
or exception has been obtained. If compatible no-fee permission is unavailable,
the source is ineligible for that purpose; payment is not a fallback under D26.

## Actual historical depth and PIT assessment

| Data family | Evidence established | AlphaLens usable coverage / PIT conclusion |
| --- | --- | --- |
| Daily equity prices | Public archive routes; legacy/common bhavcopy discontinued from 2024-07-08 in favour of UDiFF. [F01] [F02] | Zero records ingested; no complete interval measured. Format transition is not a verified history start or finish. |
| MCP prices | Latest five years advertised, previous-session final data. [F07] | Documented claim only; not a measured earliest date, complete departed coverage or legal ML grant. |
| Security-wise prices | Five-year/custom filter controls. [F19] | No populated continuous interval verified; cannot infer coverage from UI controls. |
| Reference / delistings | Current/change/delisting files listed. [F05] [F20] | Historical classification, intervals and availability remain unknown. |
| Corporate actions | Public report exists. [F08] | No complete action/adjustment-ready history; no verified usable date window. |
| Fundamental statements | Real 2020 restatement filing accessible; real financial clarification carries receipt/dissemination timestamps. [F12] [F13] | A dated document is not a complete vintage panel. FUNDAMENTAL_PIT_DATA = UNAVAILABLE. |
| Index levels / sectors / membership | Historical index controls; current NIFTY 500 download; industry taxonomy. [F14] [F15] [F16] | No acquired index interval, historical membership or historical sector assignments. Optional for V1. |
| Calendar | Current holiday page references special-session circulars. [F21] | Complete historical sessions/amendments unverified. Never project today's calendar backward. |

PIT timestamps remain separate: fiscal period, event/session, publication,
available_at, ingestion, effective interval, revision identity and evidenced revision
time. The actual announcement [F12] establishes receipt versus dissemination fields,
not complete original statement availability. The 2020 filing [F13] establishes
that a revision occurred, not a linked archive of every numeric vintage. A board-
approval date, URL timestamp or file name is not proof of public availability.

UDiFF guidance distinguishes provisional/final files and market/settlement variants;
the final-file time component can be `0000`. It must not become midnight
`published_at` or `available_at`. [F04] Capturing an old file now can demonstrate
replay of today's bytes but cannot prove which correction was known historically.
There is no proven no-overwrite guarantee in the reviewed free routes.

### Corporate-action detail

The action report is a discovery route, not a validated full ledger. Splits,
dividends and bonuses need actual terms, ex/effective/announcement dates and version
evidence; comprehensive coverage remains UNKNOWN. Merger/demerger consideration,
successor IDs, cash/share allocation and departed outcomes are also UNKNOWN.
Symbol/name-change file links are documented [F05], but complete dated identity
chains are not. No full adjusted/unadjusted price-and-volume reconciliation has
been demonstrated. Raw bars alone cannot make splits or reorganizations disappear.

## Cost and integration consequences

| Route | Known cost condition | Complexity / present decision |
| --- | --- | --- |
| Public official files + reference/actions | No paid checkout encountered for pages; file/use permissions not confirmed | Best conditional provenance path. Multiple formats, dates, identities and rights; not a turnkey licensed dataset. |
| Official MCP | No-auth setup documented; no paid client is architecturally required | Convenient query interface, but training grant absent and enumeration/vintages unproved. Not the primary ML training path. |
| Eligible research request | Conditional free volume; chargeable excess excluded | May clarify lawful delivery if project qualifies. Eligibility/NDA/purpose obligations must be resolved first. |
| Public indices/constituents | Public controls, permission unresolved | Optional context only. No need to acquire paid membership for V1. |
| Prior paid products/trials | Mandatory paid access incompatible with D26 | Preserved evidence, rejected as mandatory dependencies. No purchase alternative proposed. |

Several official source families would be needed for prices, classification,
actions and calendars. A single organization does not imply one licence or compatible
timestamps. Reconcile source IDs, schema versions, valid-dated identity and legal
scope explicitly. No monetary estimate or entitlement is invented.

## Source register and retrieval limits

All sources below were reviewed on 2026-10-05 using public web tools. Except for
named public pages/PDFs, a catalogue link is not a successfully downloaded payload.
Public-document examples were not imported into fixtures or model inputs.

| ID / type | Official source and specific evidence |
| --- | --- |
| F01 DOC | [All reports][F01]: CM report list, legacy discontinuation date, final UDiFF ZIP, full/deliverable bhavcopy and MII security GZ links; multiple-file control. Dynamic payloads not retrieved. |
| F02 DOC | [Historical CM reports][F02]: daily/monthly archives and security/index report links; no guaranteed start date. |
| F03 DOC | [UDiFF formats][F03]: guidance/versioned catalogues/file-format and explicitly labelled test-file links. File-format link retrieval failed in web tooling; exact payload schema not verified. Test files were not downloaded or used as historical evidence. |
| F04 DOC | [UDiFF guidance][F04], section 2.4, pp. 6–9: filename components, provisional/final, settlement/auction variants and final `0000` convention. No historical publication-time guarantee. |
| F05 DOC | [Securities available for trading][F05]: separate security classes, equity CSV, changes in company names/symbols. Current page, no historical master sampled. |
| F06 DOC | [Legend of series][F06]: EQ includes fully paid shares and ETFs; other series have differing trading/settlement rules and dated changes. Current legend is not historical instrument classification. |
| F07 CLAIM/TERMS | [NSE MCP][F07], Bhavcopy/tools, setup and disclaimer: rolling depth, no-auth protocol, constrained uses. No handshake, tool invocation or data capture. |
| F08 DOC | [Corporate actions][F08]: date/purpose filters and CSV control. Dynamic rows not available to this review; a symbol-specific search excerpt did not establish archive completeness. |
| F09 DOC | [Financial results][F09]: public search/download route; dynamic rows not treated as a tested statement dataset. |
| F10 DOC | [Announcements][F10]: discovery route; generic rendered page did not provide a complete historical ledger. |
| F11 DOC | [Annual reports][F11]: company-search route; no complete history or PIT field-level panel verified. |
| F12 ARTIFACT | [PIGL financial clarification][F12], announcement details: company, symbol, fiscal-quarter context, separate exchange-received/dissemination times. One real disclosure, no numerical statement ingestion. |
| F13 ARTIFACT | [Next Mediaworks filing][F13], restatement narrative on PDF pp. 16/20: June 2020 results revised in November after earlier approval, comparatives restated. No original/revised numeric pair validated. |
| F14 DOC | [Historical index data][F14]: OHLC, total/net return-index and valuation download controls. Historical index values do not establish historical components. |
| F15 DOC | [NIFTY 500][F15], constituent-download link: current roster only; download not captured. |
| F16 DOC | [Industry classification][F16]: classification framework, not evidenced company-level assignment history. |
| F17 DOC | [Research initiatives][F17]: data-seeking request route; no application submitted or eligibility asserted. |
| F18 DOC | [Research data list][F18], pp. 1–5 public/research categories; p. 6 distinguishes chargeable volume/items. Catalogue does not prove free delivery of an entire historical master. |
| F19 DOC | [Security-wise archive][F19]: symbol/series and date-range controls including 5Y/custom, CSV control. No actual coverage measurement. |
| F20 DOC | [Delisting lists][F20]: separate actual, proposed and in-process lists. Listed XLSX not captured or validated; no historical availability inference. |
| F21 DOC | [Holidays][F21]: current year and special-session notice referring to later timing circular. Historical exceptions not reconstructed. |
| L01 TERMS | [NSE terms][L01], clauses 2, 8 and 9: area-specific precedence, reserved uses/download wording, simulation and systematic-collection restrictions. |
| L02 TERMS | [NSE disclaimer][L02], research-data paragraphs: aggregate free threshold, eligible institutions/purposes, potential NDA and progress reporting. No AlphaLens-specific grant. |
| L03 TERMS | [NSE Indices terms][L03], clauses 7, 12 and 20: reserved content uses, automated-collection consent, personal/noncommercial scope. No executed licence. |
| R01 DOC | [Docker Engine][R01]: open-source engine under Apache 2.0; local free runtime direction, not an installed-runtime check. |
| R02 TERMS | [Docker Desktop licence][R02]: free eligibility depends on use/organization; do not mandate Desktop for every user. |
| R03 TERMS | [PostgreSQL licence][R03]: permissive PostgreSQL licence, supporting a local no-fee database path. |

Retrieval failures were not bypassed: the linked UDiFF file-format document and
some announcement URLs returned web-tool errors; dynamic tables often rendered
controls without rows. The successful named announcement/filing above provide
limited evidence only. Search snippets were discovery aids, not substitutes for a
validated dataset. No anti-bot workaround, cookie replay or automated scraper was used.

[F01]: https://www.nseindia.com/all-reports
[F02]: https://www.nseindia.com/static/resources/historical-reports-capital-market-daily-monthly-archives
[F03]: https://www.nseindia.com/static/resources/forms-formats-members
[F04]: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/UDiFF%20guidance%20document_Ver1.0.pdf
[F05]: https://www.nseindia.com/static/market-data/securities-available-for-trading
[F06]: https://www.nseindia.com/static/market-data/legend-of-series
[F07]: https://www.nseindia.com/nse-mcp
[F08]: https://www.nseindia.com/companies-listing/corporate-filings-actions
[F09]: https://www.nseindia.com/companies-listing/corporate-filings-financial-results
[F10]: https://www.nseindia.com/companies-listing/corporate-filings-announcements
[F11]: https://www.nseindia.com/companies-listing/corporate-filings-annual-reports
[F12]: https://www.nseindia.com/corporate/corporate-announcements/PIGL/Power%20%26%20Instrumentation%20%28Gujarat%29%20Limited?ann_dt=04022026163550&segtype=EOD&seqid=106519723
[F13]: https://nsearchives.nseindia.com/corporate/NEXTMEDIA_27112020132609_NMWOutomeOfBM27112020.pdf
[F14]: https://www.niftyindices.com/reports/historical-data
[F15]: https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500
[F16]: https://www.niftyindices.com/resources/industry-classification
[F17]: https://www.nseindia.com/static/research/research-initiatives
[F18]: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20list%20under%20NSE%20Data%20Sharing%20Policy%20for%20Research%20and%20Analysis_20250728.pdf
[F19]: https://www.nseindia.com/report-detail/eq_security
[F20]: https://www.nseindia.com/static/list/list-of-companies-proposed-to-be-delisted
[F21]: https://www.nseindia.com/resources/exchange-communication-holidays
[L01]: https://www.nseindia.com/static/nse-terms-of-use
[L02]: https://www.nseindia.com/static/nse-disclaimer
[L03]: https://www.niftyindices.com/terms-of-use
[R01]: https://docs.docker.com/engine/
[R02]: https://docs.docker.com/subscription-billing/desktop-license/
[R03]: https://www.postgresql.org/about/licence/
