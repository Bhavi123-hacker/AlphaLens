# P33 additive personal research contracts

All endpoints below retain the P21 single active ADMIN identity, authentication,
same-origin/CSRF controls and private no-store responses. Writes require existing
personal_mutations opt-in and the P32 local-write namespace. No second account or
public private-API access is introduced. P32 contracts apply except as extended here.

* `GET /api/v1/personal/decision-desk?watchlist_id=...&instrument_keys=...`
  reads active cached observations, the saved preference revision and owned
  portfolios/rules. Returns independent descriptive entries, preference exclusions,
  holding reviews and exact model readiness. It performs no provider acquisition,
  predictions or ledger writes. Price stop/target rules retain their chosen source.
* `GET /api/v1/personal/model-readiness` compares the actual P6 ordered38-feature
  registry with saved P30 candidates. No estimator is loaded or promoted. Missing
  contemporaneous peers, corporate-action compatibility and independent acceptance
  remain explicit. Current eligible feature/prediction counts remain zero.
* Profile adds optional minimum_momentum_percent, minimum_rsi, maximum_rsi and
  technical_condition (Any / ABOVE_SMA20 / MACD_POSITIVE). RSI bounds must be
  ordered. Short/Medium/Long descriptive horizons require20/60/252 observations.
  Risk category alone never supplies an invented numerical suitability threshold.
* `GET /api/v1/personal/portfolios/{id}/export` returns only the owned user-entered
  ledger/details in JSON, with provider_market_observations=false. Existing CSV
  preview/confirm remains the validated import path; JSON export is not silently
  imported or executed.
* Scenario input adds transaction_cost_inr. Results separate remaining-holdings
  value, hypothetical trade cash flow, declared cash and costs. Reductions use
  unchanged P15 append/reconstruct in memory for hypothetical FIFO basis/realized
  change. All writes_performed fields remain false; this is not a real sale.
* Historical scan preparation adds comparison_mode: strict, available_window,
  observed_endpoints. Selected and whole-cohort scans use the same reducer.
  Available-window means the latest contiguous known-identity valid-price path,
  not the best-performing subperiod. Endpoint mode supplies raw endpoint movement
  only; volatility, drawdown, consistency and other path metrics remain unavailable.
  Coverage contains requested/observed/dated/used slots and actual dates. Completed
  owned scans remain usable by historical-leader copilot navigation until expiry;
  unmount cancels only unfinished work. No background scan continues on its own.
* `GET /api/v1/personal/copilot?question=historical-leader&scan_id=...&security_id=...`
  explains an actual result from the completed owned scan and its pinned profile.
  Other guided questions cover preferences, exclusions, period, recorded activity
  and scenario assumptions. All summaries are deterministic sourced analytics.
* Alert rule input adds evidence_source: LATEST_SUPPORTED, QUOTE_ONLY or
  DAILY_CANDLES. New stock rules require a stock; concentration requires an owned
  portfolio. Preview writes zero events. Manual evaluation makes zero network
  requests. Quote volume and candle indicator observations carry distinct source
  dates. P20 in-app delivery is scoped to generated rule groups, honors its existing
  preferences/cooldown and retains only IDs/codes/date/hash, never observed prices.
  Existing incomplete legacy rules remain visible as insufficient evidence.
* `GET /api/v1/providers/upstox-private/reference?instrument_key=...` explicitly
  loads verified-current profile/key-ratios/corporate-actions via literal official
  GET paths. Maximum4GETs including a cold master, no retry,600-second memory-only
  reference cache capped at50entries and passive expiry. An empty event list is
  not complete coverage. No PIT/ledger-adjustment promotion. Explicitly loaded
  current sector can support current preference/cost-exposure checks only.

Personal recovery is a local CLI operation, not a remote restore endpoint.
`p33.backup.v2` adds the owner-bound personal sidecar; original v1 restore remains
supported. See the [Windows recovery runbook](../development/p33-windows-commands.md).
