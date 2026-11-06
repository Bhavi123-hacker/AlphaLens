# AlphaLens sequence benchmark V1 — registered development experiment

Registered 17 October 2026 before executing this experiment. Family
`ALPHALENS_SEQUENCE_BENCHMARK_V1`; original V1/V2 artifacts and acceptance gates
remain unchanged. One run per immutable dataset/protocol; retain failed runs.

Hypothesis: a compact recurrent representation of recent, source-compatible
price states may improve five-observed-session direction/ranking over a tabular
representation and simple reversal/momentum. This is an untested architecture
comparison, not a promise of predictive advantage. No architecture/target search.

## Inputs and target

Use the predeclared first 100 current equities from the immutable expanded
100-stock plan (original 50 plus positive current EQ identities sorted by ISIN,
then symbol). Do not select winners or replace missing securities. Provider-only
real private observations, original action exclusions and missing-slot rejection.
The original current fixed cohort is not historical point-in-time membership.
Source split/bonus-adjusted OHLC is not dividend-inclusive total return. Unknown
full corporate-action coverage and historical publication/vintage remain unknown.
Additional unqualified session dates are quarantined. No volume features.

Reuse the exact V2 16-feature formulas. Sequence contract
`nse.price-state.sequence20x8.v1`: 20 consecutive eligible observed slots of
`price_return_1`, `price_return_5`, `price_return_20`, `return_sd_20`,
`ma_distance_20`, `rsi_14`, `atr_14_over_close`, `open_close_return`, in that order.
All sequence states precede or equal the decision close. Reject any missing or
action-excluded feature state. Target is the exact V2 price-component return
`fifth subsequent observed close / first subsequent observed open - 1`; positive
versus nonpositive direction. Target must mature with all five observations and
existing action/calendar-gap checks. It is not a tradable same-close return,
total shareholder return or verified execution.

## Chronology and fixed budget

- Training decisions: 2022–2023, with target session strictly before 2024-01-01.
- Development validation: 2024, first 20 observed dates embargoed; target strictly
  before 2025-01-01. Only validation may choose early-stopping epoch.
- Development report: 2025 through last matured historical observation; first 20
  observed dates embargoed. These are known V1/V2-era development dates, **not an
  untouched final or prospective test**. No selection or tuning on report results.
- One fixed seed 1729. Train-only mean/SD over sequence inputs, never report data.
- One LSTM: input8 → hidden16, one recurrent layer, output dropout0.1 → dense1;
  BCE logits, Adam learning rate0.001, batch512, max20 epochs, patience3 validation
  BCE, gradient norm clip1, CPU two threads, deterministic algorithms.
- Same eligible samples for all comparisons. Traditional models receive the same
  20×8 observations flattened: balanced logistic C1/max_iter1000; random forest
  100 trees/max_depth6/min_samples_leaf30; histogram boosting100iterations/
  max_leaf_nodes15/l2_regularization1; ridge alpha10 on return; XGBoost100trees/
  max_depth3/learning_rate0.05/subsample1/colsample1/CPU2 if already available.
  No grid search, ensembling, post-result feature or threshold changes.
- Majority uses training direction frequency; momentum/reversal use the last
  observed five-session return; constant-score ranking ties use exact key order.
  Classifier threshold0.5; ridge direction threshold0. Baselines and every failed
  candidate remain in the report. No winning model automatically replaces V2.

## Measurement and non-acceptance

Report counts, exclusions, dates, BA/precision/recall/AUC/Brier (classifier scores
only; not claimed calibrated), date-wise Spearman IC, rank separation, ridge
return MAE/RMSE, period stability and paired date-block bootstrap uncertainty
(20-date moving blocks, 500 replicates, seed1729) against reversal. Multiple
comparisons are exploratory; no independent significance or profitability claim.

Hypothetical reference strategies use nonoverlapping five-session decisions,
equal allocations to actual Top5/10/20, equal eligible cohort, momentum,
mean-reversion and low-volatility baselines. Costs: predeclared 25/50/100bps
round trip plus 5bps slippage per side; sensitivity is assumptions, not a verified
tax schedule or fills. Report gross/net reference returns, endpoint drawdown,
turnover, exposure and limitations. Price/volume history does not prove fill
capacity, spread or executable full-path P&L. No verified external benchmark
series is available; the observed equal-weight cohort is not an NSE index.

Save plain numeric JSON model state and exact train scaling with checksums;
reconstruct only the reviewed fixed architecture, never arbitrary pickle loading.
Saved report inference is read-only and authenticated. Current scores require
complete compatible sequences and actual future-entry timing. Never invent
prospective records from historical report predictions. Independent confirmation
requires genuinely future frozen forecasts and the existing 126-date/1,000-outcome/
30-security/two-quarter statistical/economic and independent-review protocol.
