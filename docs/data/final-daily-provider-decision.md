# Daily source decision - 2026-10-12 Asia/Kolkata

P19_LIVE_DATA_ACTIVATION = BLOCKED. Technical access and permission are independent.
Zero new market observations acquired. Previous frozen archive ends2026-10-06.
Audit receipt times are UTC2026-10-11T18:34:46Z-18:34:55Z (after local midnight).
Actual bounded metadata/HEAD receipts remain in private final-completion-runtime.

| Candidate | Actual access and decision | Remaining evidence |
| --- | --- | --- |
| [TejHQ API](https://tejhq.dev/docs) | SOURCE_CONDITIONALLY_SUPPORTED. Keyless GET https://api.tejhq.dev/v1/status returned200,250-byte JSON; HEAD https://api.tejhq.dev/v1/snapshot/nse?date=2026-10-09 returned200 JSON content type; no snapshot body downloaded. No account/key/KYC/payment required for these probes. | No verified permitted ongoing raw snapshot contract, exchange-rights evidence, rate quota, release completeness or revision identity established. HEAD success is not an ingested session. |
| [TejHQ HF](https://huggingface.co/datasets/tejhq/indian-markets) | SOURCE_CONDITIONALLY_SUPPORTED. Public metadata200, revision462800672774d71c1edb7e2c04adedff2a524aca, modified2026-10-09T20:50:00Z, card MIT. | Year rollups mutable; Git identity identifies versions but historical correction/availability clocks unknown. No new Parquet acquired. Pinned historical authorization remains separate. |
| [NSE website reports](https://www.nseindia.com/static/nse-terms-of-use) | SOURCE_NOT_CLEARED for automated website extraction; clauses8-9 restrict storage/use and systematic collection; simulation expressly restricted. No scraping attempted. | No issued exception/agreement. Public download availability is insufficient. |
| [NSE research route](https://www.nseindia.com/static/research/research-initiatives) | SOURCE_CONDITIONALLY_SUPPORTED; [disclaimer](https://www.nseindia.com/static/nse-disclaimer) describes research access within2GB and possible agreements/periodic reports. | Academic/noncommercial eligibility, approved scope, automatic ongoing delivery and zero-cost arrangement not issued. No application/identity submission made. |
| [Twelve Data](https://twelvedata.com/pricing) | SOURCE_NOT_CLEARED for this mandatory path. Free/keyed tier exists; [research arrangements](https://support.twelvedata.com/en/articles/11116616-non-profit-organisation-subscription) require application. | Free ongoing NSE breadth, source rights, retention/ML/derived display and action/identity semantics not established; no key/account created or price request attempted. |
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | SOURCE_NOT_CLEARED. Free key offer, documented Indian example is BSE, not proof of NSE coverage. | Required NSE broad EOD/identity/actions and usage rights not verified; no key/account/price query. |
| [Yahoo](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | SOURCE_NOT_CLEARED. Automated collection requires express permission; yfinance is not a licence. | No issued permission, dependable NSE action/identity/vintage evidence or benchmark clearance. No download. |

## TejHQ technical finding and precise gaps

Status actually advertises trading_date2026-10-09, stage derived, prices publication
2026-10-09T20:39:58Z and derived/generated2026-10-09T20:50:01Z. These are **publisher
reported clocks**, not verified exchange publication/completeness or price receipt.
HTTP metadata audit SHA c6043684b712daf42ddcbc0718e69943a6ca81bac05114b4bbbceedb84a93b47.
The public status parser now verifies bounded JSON/date/aware-clock/order semantics;
it never follows redirects, retries rate limits, acquires prices or grants permission.
The referenced tej-api repository returns404; no public implementation contract was
established there. Docs response200 by itself does not specify a validated payload.

[Publisher README](https://github.com/tejhq/tej-bazaar) describes raw OHLCV in INR,
share volume, symbol/series/observed ISIN, exchange EQ/BE/BZ scope and automatic
rollups. Current identifiers are not historical eligibility. Derived chains and
backfilled identifiers are publisher heuristics, not authoritative transitions.
Special-session coverage, suspended/departed completeness, partial releases,
historic revisions and actual publication timing remain unverified. Claimed
18:30/21:30 cron is not a guaranteed consumer availability window.

Publisher permits purported open reuse, while [its blog](https://tejhq.dev/blog/indian-market-data-pricing-explained)
claims no downstream restriction. Those representations conflict with specific
NSE restrictions; software MIT does not establish upstream data rights. Ongoing
automation, retention, ML inference/derived display and redistribution restrictions
therefore remain uncleared. There is no verified free usage quota/SLA. No paid tier,
broker dependency or personal identity disclosure is introduced.

Corporate-action trees exist by publisher description, but completeness, economic
terms, original announcement/availability clocks and identity transitions are not
verified for this use. They cannot resolve474 historical outcomes by assumption.
No independent NIFTY series/constituent benchmark is cleared. Original archive,
economic classifications and protocol stay frozen.

## Unsent permission inquiry for operator review

Please confirm in writing whether TejHQ's keyless status and NSE EOD snapshot
services permit recurring automated access, indefinite local retention and
noncommercial ML inference/feature computation, prospective evaluation and private
display of derived research. What contractual upstream exchange rights permit
those uses despite NSE website terms8-9? Please identify applicable agreement,
scope/limits, attribution, raw/derived redistribution restrictions and revocation
policy. Please provide versioned raw snapshot schema, security/series identity,
coverage/completeness rules, special-session calendar, action provenance,
publication/retrieval clocks, correction IDs, rate limits and allowed catch-up.

This inquiry is prepared, **not sent or approved**. No acquisition/schedule is enabled.
