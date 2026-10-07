# Real-data historical backtest status

Status: **NOT_RUN_SOURCE_GATE_BLOCKED**. No genuine real P9 OOS stream exists for
this sprint; consequently no P10 experiment was run. Return/CAGR/volatility,
Sharpe/Sortino/Calmar, drawdown, win rate/profit factor/expectancy, turnover/trade
count/holding period, cost sensitivity and benchmark-relative results are
UNAVAILABLE. [Machine-readable status](backtest-comparison.json) uses null metrics.

Later permitted replay must use only P9 FOLD_TEST predictions, completed t evidence
and earliest evidenced t+1 open entry, matching existing P7/P10 horizon conventions.
Never use in-sample predictions or allocate based on future outcomes. P10 exact
accounting, missing fills, unresolved terminal/action values and calendar gates
remain authoritative. Annualization remains subject to existing evidence limits.

Keep ZERO_COST_DIAGNOSTIC, LOW_COST_ASSUMPTION and HIGHER_COST_STRESS separate;
these are development assumptions, not verified Indian brokerage/tax charges.
No Top-K, cost, feature or label tuning on outer-test periods is authorized.
NIFTY 50 comparison remains unavailable without usable permitted aligned benchmark
evidence; no constructed substitute is labeled NIFTY 50.

The [source audit](../data/real-data-source-audit.md) specifically records the
NSE simulation condition and TradingView non-display restrictions. A model-training
grant must not be assumed to include the requested hypothetical backtest. No real
broker connection, actual trade or P16 paper replay is part of this sprint.
