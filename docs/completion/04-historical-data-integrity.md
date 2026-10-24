# Historical data integrity — 24 October 2026

Status: **RESEARCH_COMPLETE_WITH_LIMITATIONS** for the frozen replay;
**BLOCKED_EXTERNAL_EVIDENCE** for verified production point-in-time use.
This campaign inspected saved evidence without downloading observations,
rebuilding training inputs, or reevaluating the final holdout.

The actual discovery baseline was `da4382242371c17ebdf2cecc620541931b91e313`.
`8507f7fd5457fe5e53e016c2cd7b8f14e6b6e430` and
`4133ac90b27ecabf27a11f19e53c33baa0d3c616` are ancestors of that HEAD;
research is present in this application lineage. Historical report statements
that P17 was not started describe their original checkpoint, not today's API.

| Evidence category | Actual status | Supporting evidence |
| --- | --- | --- |
| Genuine historical observations | COMPLETE_VERIFIED as preserved research inputs | Pinned TejHQ revision `14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98`; 35 originals, 193,167,839 bytes; original hashes in `docs/data/research-canonical-summary.json` and `docs/backtesting/real-research-economic-audit.json` |
| Final-vintage replay | COMPLETE_VERIFIED within registered assumptions | `RESEARCH_EOD_FINAL_VINTAGE_V1`, canonical `37693f7796bc42b4c33fad117196c6a75545dd690d5edd7f597204bc7e24f490`, supervised `f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2` |
| Production point-in-time data | BLOCKED_EXTERNAL_EVIDENCE | Actual historical publication, availability and revision vintages absent; research assumptions do not certify them |
| Original frozen results | COMPLETE_VERIFIED for preservation | Campaign verifier rehashed 2,485 files / 8,505,278,241 bytes and checked 47 original alerts; see final preservation report |
| Private provider history | PARTIAL for full market | Separate versioned V1/V2/expanded stores; current fixed cohorts, not historical constituent universes |

The frozen source spans 4 January 2010–6 October 2026 and retains 7,225,761
observations, including identities absent from the latest date. P3 recorded
5,288,138 VALID and 1,937,623 DEGRADED rows. The canonical research universe has
6,827,699 equity-candidate rows, 385,840 excluded non-equity rows and 12,222
unknown/unusable rows. Research classification never upgrades DEGRADED quality
or establishes authoritative historical common-equity type.

The 7,911 research IDs include 4,381 observed-ISIN identities and 3,530
source-year provisional identities. They are not 7,911 verified distinct
companies. There are 438 observed-ISIN identities with multiple symbols and
1,439 historical observed-ISIN identities absent from the latest session.
Disappearance proves neither delisting nor zero recovery. Missing ISINs are
never filled backward using a future instrument master.

The calendar retains 4,128 observed dates plus five independently documented
missing-price Muhurat slots: 2013-11-03, 2016-10-30, 2019-10-27, 2020-11-14 and
2023-11-12. It remains an incomplete authoritative NSE calendar. Missing slots
invalidate affected rolling windows and outcomes; they are not skipped or filled.
SMA100 and SMA200 availability was respectively 73.1147% and 55.4085%, including
explicitly allowed degraded inputs. These are saved audit results, not a new run.

Frozen raw prices are RAW_UNADJUSTED. Their 20,776 raw action rows are useful
research evidence but do not supply a complete entitlement/payment/conversion
ledger. The final-vintage profile assumes next-session pre-open availability;
this assumption is explicitly distinct from an observed publication timestamp.
No production provenance field is promoted by the research profile.

GLOBAL's four identity-gap dates, 19/20/21/25 October 2022, remain unresolved:
the held identity is `INE291W01011`; source prices exist under `INE291W01029`.
Ticker equality does not establish the dated conversion ratio, entitlement or
economic continuity. The audit also retains 34 action/price ISIN mismatches.
No verified new reconciliation source was supplied in this campaign, so no
replacement history or speculative identity merger was produced.

Private Upstox V1/V2 history uses its own source-compatible contracts. The
recorded private noncommercial retention/derived research scope is narrow;
public redistribution and production use do not follow. V2 documented
split/bonus-adjusted price-component returns, with dividends and complete
rights/demerger/vintage evidence unresolved. Its 50-stock development study,
later 100-stock sequence study and 500-stock current collection cannot replace
historical membership in the TejHQ replay. No new rights claim was made here.

Next reconciliation must be additive and versioned: pin legally usable source
bytes, effective identity intervals, original/raw hashes, adjustment conventions,
event/publication/availability/ingestion times and missingness decisions. Require
dated GLOBAL continuity and terminal-consideration evidence before calculating
economic outcomes. Retain both unresolved original results and any future
separate reconciliation. No corrected final-holdout evaluation is authorized by
this inventory.

Sources inspected: `docs/data/real-10y-ingestion-report.md`,
`docs/data/research-methodology-amendment.md`, `docs/data/real-data-readiness.json`,
`docs/data/ml-v2-source-and-target-audit.md`,
`docs/development/alphalens-ml-v2-performance-and-acceptance.md`, and the economic
audit. The campaign's regression and preservation receipts are summarized in
`14-end-to-end-verification.md`; no data-acquisition call was made by this audit.
