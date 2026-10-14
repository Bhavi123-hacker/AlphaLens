# P30 daily collection and current-model audit — 2026-10-14

This audit separates genuine provider access, software execution, source-use
evidence and model acceptance. Frozen historical results were not rerun or changed.

| Capability | Actual evidence | Present result | Exact next action |
| --- | --- | --- | --- |
| Upstox connectivity | Protected credential readback; authenticated official candle/quote/holiday/timing GETs returned 200 | PASSED for tested market GETs | Refresh an expired/revoked credential through local setup; do not infer additional account scopes |
| NSE identity and EOD candles | Official current NSE master matched RELIANCE / INE002A01018 / NSE_EQ; 1,240 observed dates in five-year response | PASSED for one identity; latest returned date 2026-10-13 | Validate any additional identity and its permitted scope before expanding |
| Latest availability | Final bounded request covered 13–14 October; returned only 13 October; official 14 October timings had elapsed | 14 October market closed; provider EOD candle still pending at verification | Recheck the protected manual view; never manufacture a missing candle or substitute LTP |
| Automated API access | Official Analytics documentation describes automated pipelines and read-only market APIs without static IP | Documented technical use; no trading access implemented | Keep the documented GET-only scope and conservative request budget |
| Retaining market prices | User states no separate retention permission; reviewed general terms do not establish this project's market-data retention rights | BLOCKED_EVIDENCE for durable collection | Obtain an applicable API/exchange contract clause or provider confirmation specifying duration, private storage and permitted derived use; record the exact reference locally |
| Private ML use | No supplied/reviewed grant explicitly covers using retained NSE observations with the frozen ML models | BLOCKED_EVIDENCE | Obtain the applicable private ML/research-use clause; API authentication cannot supply it |
| Public data display | No redistribution grant; static bundle contains only synthetic observations | Real provider redistribution disabled; synthetic demo deployed | Obtain separate redistribution rights before changing the public data source |
| Daily worker software | Existing P19 worker now accepts a gated Upstox operational release; acquisition uses the existing P28 quota ledger and fixed official endpoints | Offline TEST_ONLY orchestration, idempotent replay, interruption recovery and corrections passed | After genuine source-use clearance, run one permitted real retained session and verify its receipt before task activation |
| Scheduler | Disabled least-privilege Windows task XML parsed by actual Task Scheduler COM; guarded daily command supplied | Prepared and disabled; no registered/enabled daily task | Supply current explicit official calendar facts, complete source evidence, verify one retained live run, then review/register the disabled task and activate only the qualified data action |
| Session/identity eligibility | Current master has 2,701 EQ-type candidates, no dated historical common-equity denominator; only RELIANCE tested | Not an eligible full-market universe | Supply dated series/security-type and membership evidence, including renamed/departed/suspended coverage; never substitute today's master for historical membership |
| Price compatibility | Provider basis, publication time, corporate-action coverage and final close are unknown | Descriptive chart allowed; canonical model join disabled | Establish raw/adjusted basis and action evidence for the complete feature window and compare with the frozen training basis |
| Numerical inputs | Same exact 38-column order verified in all four frozen candidates; 37 descriptive numerical inputs available from returned slots | 0 of 38 inputs eligible for current inference | Validate calendar slots, source clocks, dated eligibility, basis/actions and compatible trailing history; numerical availability alone is insufficient |
| Cross-sectional momentum | One verified watchlist identity; no complete eligible session peer set | momentum_percentile_20 unavailable | Supply the verified decision-time peer universe and complete eligible return_20 values; use existing P6 peer calculation with peer revision lineage, not a one-stock percentile |
| Model serialization | Four checksum-pinned candidates inspected; exact XGBoost artifact deserialized successfully with 38 inputs and native XGBoost 3.0.5 | Technical XGBoost type blocker repaired for the exact checksum only | Re-review any changed artifact/types; no global allowlist extension or arbitrary loading |
| Independent model acceptance | Stored candidate statuses remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE; prospective forecast/outcome count is zero | No current accepted classifier or ranking model | Complete independent acceptance under the frozen methodology and legitimately available prospective evidence; do not rerun/retune the frozen holdout to promote a model |
| Economic/risk evidence | 30 stored backtests have raw-path diagnostics; 474 retain unresolved economic outcomes; action/identity limitations remain | No profitability or current risk clearance | Resolve the outstanding action/identity/economic evidence and create contemporaneous verified P11 risk/universe snapshots |
| Top 5/10/20 | P12 frozen non-TEST_ONLY policy returns MODEL_SELECTION_INSUFFICIENT_EVIDENCE; current risk/universe and accepted model evidence absent | No legitimate real current rankings; synthetic interface available | Supply accepted model-selection evidence, eligible complete cohort and contemporaneous risk inputs through the unchanged policy; classifier output alone does not authorize ranking |

## Software repairs and their limits

`workers/daily/engine.py` formerly returned `BLOCKED_SOURCE` for every DAILY
request, even when all source flags were true. That unconditional return is now
replaced with explicit source, official-session, new-session and checksum gates.
Supported Upstox releases pass through `workers/providers/operational_release.py`
and the existing P19 locked, checksum-verified Store. The original P28 TEST_ONLY
bundle cannot be relabeled as a real release. Other unverified adapters remain blocked.

`workers/providers/daily.py` performs bounded acquisition only after all existing
Access/source gates pass. It processes explicit past official sessions from the
last 30 days, at most three GETs per run, for the verified RELIANCE key. The first
capture survives interruption; an unchanged replay uses no second GET. Native
responses and versioned observations are stored only in the separate protected
P30 operational root after retention clearance. Changed prices get distinct
economic observation identities; historical data is never overwritten. A separate
explicit revision workflow is required to acquire corrections to an already captured
session; the automatic path does not repeatedly reacquire completed captures.

Unknown basis/actions/publication remain unknown in operational observations.
They cannot enter the historical RAW_UNADJUSTED canonical contract, model inputs,
Research Intelligence's historical metrics or accepted rankings. Technical
collection and model promotion are separate. A working staged release does not
mean current inference is available.

`workers/daily/artifact_reviews.py` grants the two inspected XGBoost serialized
types only to the exact checksum-pinned frozen horizon-10 artifact. Extra types,
different bytes and other artifacts fail closed. Existing loading authorization,
artifact checksum, candidate lineage, chronology and model acceptance remain
required. No predictions were generated by artifact inspection.

The original P6 cross-sectional calculation already exists in
`ml/features/src/alphalens_features/engine.py`. The bounded P19 affected-security
feature update correctly reports missing complete peer context. Computing a
percentile over RELIANCE alone would change the research methodology. No such
substitution was added.

## Source references and interpretation

- [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/)
- [Analytics launch](https://upstox.com/developer/api-documentation/announcements/analytics-token/)
- [Automated analytics update, effective 6 June 2026](https://upstox.com/developer/api-documentation/announcements/analytics-token-static-ip/)
- [General terms, last updated 15 August 2026](https://upstox.com/terms-of-use-and-privacy-policy/)

The automated-analytics announcement supports the technical use of read-only API
access. It does not specify this project's retention duration, ML licence or
redistribution rights. The general terms' customer-data retention section describes
Upstox's processing obligations; interpreting it as a market-data licence to the
operator would be unsupported. This is an evidence gap, not a claim that all local
analytics are prohibited. Manual private transient descriptive charts remain enabled.

No additional licensing question is pending: the user's supplied answer is preserved.
The next required evidence is the specific applicable source-use clause, not a token,
password or generic approval to proceed with engineering.
