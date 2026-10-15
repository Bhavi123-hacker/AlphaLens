# P33 audited feature matrix

Baseline: clean P32 `243d48345356c4d969ff4f05a79c4f829c7458f6`; original C/P26
worktree separate. Classification describes the audited P32 gap; P33 changes are
verified separately in the final report, with exact run counts and limitations.

| Requested feature family / individual capabilities | P32 classification | P33 action or genuine dependency |
| --- | --- | --- |
| Dynamic company/symbol/ISIN/key discovery, NSE_EQ/type-EQ filtering, ranking, autocomplete, pagination, thousands of identities | COMPLETE_AND_VERIFIED | Preserve indexed master and realistic-cohort performance; actual six-stock regression. |
| Identity changes, missing/inactive instruments, no BSE substitution, historical identity separation | COMPLETE_AND_VERIFIED | Preserve exact current-master verification and absent-identity errors; no current-universe historical backfill. |
| LTP, previous close, change, OHLCV, quote generation vs last trade vs daily candle, freshness, manual refresh | COMPLETE_AND_VERIFIED | Preserve strict clocks and source separation; fresh real-sample receipts. |
| Batching, quotas, transient caching, request cancellation, bounded retries, no full-universe polling | COMPLETE_AND_VERIFIED | Inspect new reference/derived-view expiry; no acquisition on expiry. |
| Provider-first candles/line, volume, SMA20/50/100/200, EMA12/26, RSI, MACD, Bollinger, ATR, volatility | COMPLETE_AND_VERIFIED | Reuse original P6 indicators and warm-up; no indicator from a single quote. |
| Zoom/pan/crosshair, fullscreen, ranges/custom dates, rounded prices/tooltips | COMPLETE_AND_VERIFIED | Compiled regression preserves controls and precision. |
| Dark/light, sidebar, readable responsive layouts, keyboard and contrast | COMPLETE_AND_VERIFIED | Add Decision Desk/alert forms and test accessibility/mobile overflow. |
| Homepage market focus, portfolio/research navigation, separate P19 diagnostics | PARTIALLY_FUNCTIONAL | Add direct Decision Desk/historical links; retain compact market source and collapsible diagnostics. |
| Observed movers/gainers/losers/active-volume/volatility, heatmap and screening | COMPLETE_AND_VERIFIED | Preserve explicitly observed-cohort views; no inferred full-NSE breadth. |
| Complete live NSE breadth/index strip/full-market heatmap | CONTRACTUAL_OR_REGULATORY_DEPENDENCY | Retained/full-cohort observation and index rights/coverage absent; bounded observed cohort remains functional. |
| Sector grouping and sector exposure | DATA_DEPENDENCY | New explicitly loaded current Upstox sector reference can filter/review current observations; historical taxonomy and full-cohort coverage remain unavailable. |
| Price/volume/change/RSI/MA/MACD/volatility/drawdown/momentum/favorite/freshness screener | COMPLETE_AND_VERIFIED | Preserve missing-input exclusions; connect explicit numerical preferences. |
| Multi-stock normalized-price/risk/correlation comparison | COMPLETE_AND_VERIFIED | Preserve sample/source/adjustment disclosures. |
| Persistent budget/risk/horizon/sectors/cap/dividend/style/drawdown/exposure/count/holdings/liquidity preferences | COMPLETE_AND_VERIFIED | Preserve single operator; add optional momentum/RSI/MA/MACD conditions. |
| Preference-to-live-descriptive discovery and exclusion reasons | PARTIALLY_FUNCTIONAL | Add immediately refreshed Decision Desk keyed by preference revision and current watchlist; enforce adequate requested horizon. |
| Calibrated Low/Moderate/High suitability mapping | MODEL_EVIDENCE_DEPENDENCY | No calibrated mapping invented; editable explicit numerical constraints operate independently. |
| Growth/value/dividend/market-cap/PIT fundamental filters | DATA_DEPENDENCY | New current ratio/reference view does not supply PIT/units/complete company-cap acceptance. Keep unsupported dimensions visible. |
| Potential Entry Research Candidates | BUILT_BUT_NOT_CONNECTED | Dedicated Desk with actual metrics, dates, applied filters and evidence gaps; no BUY instruction. |
| Holding concentration, volatility, drawdown, declining momentum, stale/missing marks | PARTIALLY_FUNCTIONAL | Connect actual manual positions to Desk and add declining-momentum review. |
| Holding target/stop review | BUILT_BUT_NOT_CONNECTED | Enabled owned price rules now supply explicit threshold-review reasons; quote-only/source constraints respected. |
| Hypothetical keep/add/reduce/shock/target weights/cash change | COMPLETE_AND_VERIFIED | Preserve zero writes; add declared cost, trade-flow subtotal and original-P15 FIFO reduction effect. |
| Actual actionable personalized BUY/HOLD/SELL | CONTRACTUAL_OR_REGULATORY_DEPENDENCY | Independent model/data/publication and applicable financial-advice review remain separate; interface reports real blockers. |
| Historical leaders 1M/3M/6M/1Y | COMPLETE_AND_VERIFIED | Remeasure exact observed/cohort/exclusion counts; no model evaluation. |
| Strict 3Y/5Y leaders returning zero | DATA_DEPENDENCY | Diagnose common missing 2023-11-12 observation; preserve calendar slot. Add separately labelled contiguous and dated-endpoint comparisons without path-risk invention. |
| Historical coverage, excluded identity reasons, actual dates, custom windows | PARTIALLY_FUNCTIONAL | Per-security requested/observed/used slots, identity/price causes; selected and whole-cohort scans use same reducer. |
| Saved ML leaderboard, folds/calibration/baselines/rank IC/economics | COMPLETE_AND_VERIFIED | Reuse saved research/reliability pages; 474 unresolved backtests unchanged. |
| 38-feature numerical/temporal/peer/artifact readiness | PARTIALLY_FUNCTIONAL | New machine-readable registry/order inspection and Desk display; exact checksum-scoped loading restrictions preserved. |
| Independent prospective model acceptance | MODEL_EVIDENCE_DEPENDENCY | Versioned registration/power/maturity/baseline/calibration/stability/economic-review protocol; no arbitrary approving thresholds or frozen holdout rerun. |
| Current Top5/10/20 ML predictions | MODEL_EVIDENCE_DEPENDENCY | Zero accepted current predictions; descriptive/historical Top5/10/20 remain usable. |
| Named watchlists, favorite identities, recently researched history, sort/filter | COMPLETE_AND_VERIFIED | Preserve existing local records and bounded source loads. |
| Manual holdings, opening funds, purchase lots, known fees, partial sale, exact FIFO | COMPLETE_AND_VERIFIED | Add funded-purchase browser journey and immutable reduction tests. |
| Indicative value/unrealized P&L, source timestamp, cost allocation | COMPLETE_AND_VERIFIED | Preserve accepted-economic-value separation; add reference-source expiry for sector data. |
| Realized P&L/activity, journal hypothesis/horizon/risks/outcome/lessons | COMPLETE_AND_VERIFIED | Preserve exact user records and editable journal; grounded activity copilot answer. |
| CSV validation/preview/explicit atomic idempotent confirmation | COMPLETE_AND_VERIFIED | Reuse existing identity and owner/revision guards. |
| Personal transaction export | PARTIALLY_FUNCTIONAL | New authenticated owned JSON export/download; no provider observations or credentials. |
| Consistent personal preferences/watchlists/portfolios/journal/rules/recent backup | BUG_OR_BROKEN | Personal sidecar absent from P22 recovery; add online SQLite snapshot and versioned integrity manifest, backward-compatible restore and owner verification. |
| Isolated restore and stop/restart persistence | PARTIALLY_FUNCTIONAL | Actual operator-owned test-store backup/restoration, corruption/foreign-owner refusal and before/after personal-record equality. |
| Full accepted economic portfolio history/drawdown/dividend-adjusted valuation | DATA_DEPENDENCY | Corporate actions, compatible historical marks and complete financial events absent. No interpolation or assumed cash. |
| Smart alert creation, source/threshold/direction, preview, edit/enable/delete | PARTIALLY_FUNCTIONAL | New guided form with verified search, transient preview, revision-safe lifecycle controls and expiry. |
| Deduplicated in-app personal notifications | BUG_OR_BROKEN | Frontend omitted P32 event component; fix decoder/evidence link and use scoped P20 in-app delivery respecting existing preferences. |
| Background checks/outbound notifications | CONTRACTUAL_OR_REGULATORY_DEPENDENCY | Remain disabled; manual cache evaluation makes zero network requests. |
| Daily calendar/delay/quota/capture/idempotency/resume/corrections/recovery | PARTIALLY_FUNCTIONAL | Existing P19/P30 mechanics retained; generalise bounded explicit verified-key orchestration with separate capture roots; TEST_ONLY replay for another key. |
| Real durable daily acquisition/scheduling/ML use | CONTRACTUAL_OR_REGULATORY_DEPENDENCY | Source-specific market-data storage/analysis terms and eligible official retained session required; access alone insufficient. |
| Current company ratios/sector/corporate-action reference | DATA_DEPENDENCY | Official documentation and actual bounded TCS GETs verified; new transient private view. No PIT or complete action-coverage claim. |
| Corporate events/earnings/dividend timeline | DATA_DEPENDENCY | Show returned provider corporate events/dates separately; no invented earnings calendar or applied ledger action. |
| Fundamental/benchmark/index source contracts | DATA_DEPENDENCY | Official candidate-source catalogue and exact clock/identity/rights/coverage requirements; no paid acquisition or scraping. |
| Guided copilot / sourced explanations | PARTIALLY_FUNCTIONAL | Preference/exclusion/period/activity/scenario questions and owned historical-scan explanation; no general LLM claim. |
| Evidence Passport, regimes/reliability/drift and research diagnostics | COMPLETE_AND_VERIFIED | Reuse P29/P31 source-specific evidence; connect Desk and saved model readiness. |
| Synthetic preference/portfolio/FIFO/review/risk/leaderboard/journal demo | BUILT_BUT_NOT_CONNECTED | Extend independent static demo using original P15 generated TEST_ONLY records; preserve no-private-API CSP. |
| Multi-user private/public service | SECURITY_DEPENDENCY | Actual single operator preserved; no invented ownership isolation or public backend. |
| Frozen research, 152 fits/504 backtests/38 features, original alerts, credentials and source separation | COMPLETE_AND_VERIFIED | Fresh read-only preservation/credential checks; no research reruns or paid services. |
| Lazy chart performance, scan latency, index payloads and cache eviction | PARTIALLY_FUNCTIONAL | Measure actual reads/builds; chart remains lazy, small numerical scopes and explicit expiry. Existing large chart chunk warning disclosed. |
| Strict container CVEs | SECURITY_DEPENDENCY | Investigate fresh strict scan and official Debian status; compatible upgrades already applied, no unsupported distro mixing/suppression. |

The final software acceptance matrix in `p33-final-gap-closure-report.md` separates
working descriptive/local capabilities from these independent real-world gates.
