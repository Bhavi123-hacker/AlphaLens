## D70 backtest preparation

Research P10 execution is implemented but genuine real OOS backtests have not run.
Only checksum-verified FOLD_TEST predictions are accepted. Decisions use completed
t evidence; fills require the next calendar slot's actual open. Missing Muhurat
opens never skip forward or fill. Raw economic actions leave holdings unresolved;
no adjusted price, recovery or dividend is invented. The three existing cost
scenarios remain engineering assumptions; HIGHER_COST_STRESS is the existing
stress scenario corresponding to the requested STRESS_COST_ASSUMPTION display.
Genuine benchmark comparison remains UNAVAILABLE. Historical D69 status follows.

# Real-data backtest status after D69

**NOT_RUN_HISTORICAL_EVIDENCE_GATE_BLOCKED**. No genuine P9 OOS predictions exist,
so P10 was not run. Total return, CAGR, volatility, Sharpe, Sortino, drawdown,
Calmar, win/loss rates, profit factor, expectancy, exposure, turnover and trade
count are UNAVAILABLE. No equity/P&L/drawdown/trade-marker curve was fabricated.

The configured future replay remains completed t evidence -> earliest evidenced
t+1 open, with existing TOP_K/TOP_PERCENTILE/PREDICTION_THRESHOLD policies. Costs
remain ZERO_COST_DIAGNOSTIC, LOW_COST_ASSUMPTION and STRESS_COST_ASSUMPTION;
none was run or optimized, and they are not actual Indian brokerage/tax charges.

Benchmark is UNAVAILABLE: the pinned repository has no identified genuine NIFTY
benchmark tree. No constructed portfolio/proxy is named NIFTY 50. Uncertain
corporate-action factors, terminal values and fills are not invented. Paper
simulation was not run on this unqualified history.

[Machine-readable status](backtest-comparison.json) preserves REAL_MARKET_OBSERVATIONS /
RESEARCH_ONLY and NOT_CLEARED production use. Historical source-audit status follows.

---

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
