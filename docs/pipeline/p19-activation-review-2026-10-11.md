# P19 activation decision — 2026-10-11

`P19_LIVE_DATA_ACTIVATION = BLOCKED`. Prior P19 development acceptance is unchanged.
No new market observations were downloaded, ingested, scored or published. No
acquisition scheduler or outbound notifications were enabled. Frozen source ends
2026-10-06; metadata changes do not establish a later observation's completeness.

## Current primary evidence

| Candidate | Decision | Evidence and precise limitation |
| --- | --- | --- |
| Official NSE downloadable EOD reports | SOURCE_CONDITIONALLY_SUPPORTED | [NSE research data list, 2025-07-28](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20list%20under%20NSE%20Data%20Sharing%20Policy%20for%20Research%20and%20Analysis_20250728.pdf) places OHLC/volume, bhavcopy, securities and corporate actions in its research basket; voluminous datasets above 2 GB can be chargeable. [Website terms](https://www.nseindia.com/static/nse-terms-of-use), clauses 8–9, still restrict reuse and automated collection and prohibit website-data simulation. This is a real potential research route, not clearance for this worker. |
| NSE approved research request/agreement | SOURCE_CONDITIONALLY_SUPPORTED | [Research initiative](https://www.nseindia.com/static/research/research-initiatives) offers academic/noncommercial applications. [Data policy](https://www.nseindia.com/static/market-data/nse-data-policy) specifies agreements and approved use; pricing/waivers require case-specific resolution. AlphaLens has no issued permission or demonstrated zero-cost ongoing delivery agreement. No application/email was sent. |
| TejHQ ongoing HF publications | SOURCE_CONDITIONALLY_SUPPORTED | [Dataset](https://huggingface.co/datasets/tejhq/indian-markets), [publisher pipeline](https://github.com/tejhq/tej-bazaar), [publisher account of redistribution rights](https://tejhq.dev/blog/indian-market-data-pricing-explained). Public metadata fetched successfully: revision `462800672774d71c1edb7e2c04adedff2a524aca`, lastModified `2026-10-09T20:50:00.000Z`. That is repository metadata, not exchange publication or verified latest session. Publisher representations and historical D69 permission do not settle the contrary ongoing NSE website terms. New revision was detected without downloading prices. |
| Alpha Vantage free API | SOURCE_CONDITIONALLY_SUPPORTED | [Terms](https://www.alphavantage.co/terms_of_service/) allow specified private individual research; [support](https://www.alphavantage.co/support/) advertises 25 daily requests and possible verified educational/open-source exemptions. No key or exemption was requested. Genuine NSE daily instrument coverage, identities, release clocks and sufficient coverage at the free quota remain unverified. No paid endpoint was introduced. |
| Yahoo/yfinance route | SOURCE_NOT_CLEARED | [Official Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) could not be fetched (999). An open-source wrapper grants no upstream data rights. NSE-wide raw EOD, revision, identity and special-session coverage were not established. No scraping, authentication bypass or alternate anti-bot route was attempted. |

These are source-specific research decisions. None is production clearance.
No candidate is `SOURCE_APPROVED_FOR_RESEARCH` for ongoing P19 automation.

## Required technical and usage evidence

“Unverified” retains a hard gate; it never means permitted or technically complete.

| Criterion | Official NSE website | Approved NSE agreement route | TejHQ ongoing | Alpha Vantage free | Yahoo route |
| --- | --- | --- | --- | --- | --- |
| New NSE EOD | Official report facility | Requested scope unissued | Publisher claim; metadata only checked | Unverified | Unverified |
| Free ongoing use | Public basket; bulk can cost | Zero-cost terms unissued | Public metadata free | 25 calls/day advertised | Unverified |
| Automated download | Website restriction | Permission unissued | Ongoing upstream permission unresolved | API offered; NSE scope unverified | Unverified |
| Local research retention | Scope unresolved | Agreement unissued | Ongoing rights unresolved | Individual scope conditional | Unverified |
| Derived features/ML | Scope unresolved | Agreement unissued | Ongoing rights unresolved | Exact NSE use unverified | Unverified |
| Instrument identity | Master facility, dated semantics unverified | Scope unissued | Existing schema; new identities unverified | Unverified | Unverified |
| OHLCV/session coverage | Report facility; no new release checked | Scope unissued | Historical archive verified; new coverage unverified | Unverified | Unverified |
| Special sessions | Official announcements exist | Delivery scope unissued | Completeness unverified | Unverified | Unverified |
| Publication vs retrieval | Actual release clocks unverified | Clocks unissued | Repository/retrieval clock is not publication | Unverified | Unverified |
| Revisions | Release identification unverified | Revision protocol unissued | Git revision available; historical correction clocks unknown | Unverified | Unverified |
| Rate limits/terms | Automation gate fails | Unissued | Fixed metadata checks bounded; prices uncleared | Quota insufficiently validated | Unverified |
| Corporate actions | Official facility; complete dated linkage unverified | Scope unissued | Coverage/revision semantics unverified | Adjusted products exist; exact raw NSE linkage unverified | Unverified |

[Official holidays page](https://www.nseindia.com/resources/exchange-communication-holidays)
specifically announces Muhurat trading on the 2026-11-08 holiday, with times to
follow in a circular. A holiday list or weekday rule alone cannot establish the
full session schedule or expected source-release window. No such window was invented.
The new freshness alert reader requires an evidenced session and documented release
expectation and refuses real missing-session alerts while the source registry is blocked.

## Models and policy

Read-only checks reuse the checksum-pinned `2026-results.json` and its four fixed
classification candidates; no metrics are recalculated or used for selection.
Artifacts are in the existing `p9/models` directory. All four checksum/identity,
family/horizon, stored preprocessing and training-cutoff metadata checks passed.
Their 38-column order matches the unchanged P6 registry. Training cutoff remains
`2025-12-30T18:29:59.999999Z`.

This does not establish a complete eligible new-session feature vector, publication
timing, warm-up history, cross-section or current action evidence. Estimators were
not deserialized and predictions were not generated. Experimental inference,
ranking/signals, stock notifications and scheduling remain unavailable under the
unchanged P11–P14/P19 policies. Existing probabilities/thresholds were not changed.

Unblocking requires actual permitted access, an integrated bounded adapter, verified
new-session calendar/identity/action/feature evidence, independently satisfied model
acceptance, and explicit operator scheduling approval. Current software cannot
approve a provider by accepting caller-written flags.
