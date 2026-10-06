"""Hypothetical economics; undefined/short/unresolved statistics stay unavailable."""

from collections import defaultdict
from typing import Any

import numpy as np

from alphalens_backtesting.contracts import BacktestDefinition
from alphalens_backtesting.money import parse_rational


def annual_statistics(
    values: list[float],
    capital: float,
    duration_days: int,
    annual_sessions: int,
    risk_free_annual: float,
    max_drawdown: float | None,
) -> dict[str, float | None]:
    """Mathematical helper; caller owns minimum history and evidence classification."""
    array = np.asarray(values, dtype="float64")
    if len(array) < 3 or not np.isfinite(array).all() or (array <= 0).any() or duration_days <= 0:
        return dict(cagr=None, annualized_volatility=None, sharpe=None, sortino=None, calmar=None)
    returns = np.diff(array) / array[:-1]
    rf = (1 + risk_free_annual) ** (1 / annual_sessions) - 1
    excess = returns - rf
    cagr = float((array[-1] / capital) ** (365.25 / duration_days) - 1)
    std = float(np.std(returns, ddof=1))
    downside = float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))
    return dict(
        cagr=cagr,
        annualized_volatility=float(std * np.sqrt(annual_sessions)),
        sharpe=float(excess.mean() / std * np.sqrt(annual_sessions)) if std else None,
        sortino=float(excess.mean() / downside * np.sqrt(annual_sessions)) if downside else None,
        calmar=float(cagr / max_drawdown) if max_drawdown else None,
    )


def summarize(
    definition: BacktestDefinition,
    equity: list[dict[str, Any]],
    drawdown: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    pnl: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    capital = float(definition.initial_capital)
    marked = all(r["portfolio_value"] is not None for r in equity)
    closed = [r for r in trades if r["exit_session"] is not None]
    unfinished = [r for r in trades if r["exit_session"] is None]
    net_returns = [float(r["net_return"]) for r in closed]
    trade_pnl = [float(parse_rational(r["net_pnl_rational"])) for r in closed]
    gains = sum(v for v in trade_pnl if v > 0)
    losses = -sum(v for v in trade_pnl if v < 0)
    final = float(equity[-1]["portfolio_value"]) if marked else None
    fees = float(pnl[-1]["cumulative_fees"]) if pnl else 0.0
    slip = float(pnl[-1]["cumulative_slippage"]) if pnl else 0.0
    draw_values = [r["drawdown"] for r in drawdown if r["drawdown"] is not None]
    max_drawdown = -min([0.0, *draw_values]) if marked else None
    duration = (definition.end_session - definition.start_session).days
    annual_available = (
        marked
        and len(pnl) >= definition.annualization_minimum_sessions
        and duration >= 365
        and definition.data_classification.value != "TEST_ONLY"
    )
    cagr = volatility = sharpe = sortino = calmar = None
    annual_status = "INSUFFICIENT_EVIDENCE_SHORT_OR_TEST_ONLY_OR_UNRESOLVED"
    if annual_available:
        annual_metrics = annual_statistics(
            [float(r["portfolio_value"]) for r in equity],
            capital,
            duration,
            definition.annual_sessions_assumption,
            float(definition.risk_free_annual_assumption),
            max_drawdown,
        )
        cagr = annual_metrics["cagr"]
        volatility = annual_metrics["annualized_volatility"]
        sharpe = annual_metrics["sharpe"]
        sortino = annual_metrics["sortino"]
        calmar = annual_metrics["calmar"]
        annual_status = (
            "DESCRIPTIVE_ASSUMPTION_BASED_NOT_PRODUCTION_VALIDATED"
            if cagr is not None
            else "UNAVAILABLE_NONPOSITIVE_WEALTH"
        )
    benchmark = equity[-1]["benchmark_wealth"]
    benchmark_return = (
        float(benchmark) - 1 if benchmark is not None and definition.benchmark else None
    )
    traded = sum(float(r["quantity"]) * float(r["entry_price"]) for r in trades)
    traded += sum(float(r["quantity"]) * float(r["exit_price"]) for r in closed)
    mean_nav = float(np.mean([float(r["portfolio_value"]) for r in equity])) if marked else None
    by_fold: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trades:
        by_fold[row["fold_id"]].append(row)
    return dict(
        model_family=definition.model_family,
        horizon=definition.horizon,
        selection_rule=definition.selection_rule,
        baseline=definition.baseline,
        cost_scenario=definition.costs.name,
        cost_status=definition.costs.status,
        period=[definition.start_session.isoformat(), definition.end_session.isoformat()],
        data_classification=definition.data_classification.value,
        result_status="UNRESOLVED_ECONOMIC_OUTCOMES"
        if not marked
        else "RAW_PRICE_DIAGNOSTIC_COVERAGE_NOT_ESTABLISHED",
        evidence_status="INSUFFICIENT_EVIDENCE",
        initial_capital=str(definition.initial_capital),
        normalized_final_wealth=final / capital if final is not None else None,
        net_total_return=final / capital - 1 if final is not None else None,
        gross_total_return=(final + fees + slip) / capital - 1 if final is not None else None,
        gross_basis="SAME_EXECUTED_QUANTITIES_FEES_SLIPPAGE_ADDED_BACK_NOT_REINVESTED",
        total_fees=fees,
        total_slippage=slip,
        maximum_drawdown=max_drawdown,
        cagr=float(cagr) if cagr is not None else None,
        annualized_volatility=float(volatility) if volatility is not None else None,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        annualized_metrics_status=annual_status,
        annual_sessions_assumption=definition.annual_sessions_assumption,
        risk_free_annual_assumption=str(definition.risk_free_annual_assumption),
        trade_count=len(trades),
        closed_trade_count=len(closed),
        open_or_unresolved_trade_count=len(unfinished),
        win_rate=sum(v > 0 for v in net_returns) / len(closed) if closed else None,
        loss_rate=sum(v < 0 for v in net_returns) / len(closed) if closed else None,
        flat_rate=sum(v == 0 for v in net_returns) / len(closed) if closed else None,
        average_trade_return=float(np.mean(net_returns)) if closed else None,
        median_trade_return=float(np.median(net_returns)) if closed else None,
        profit_factor=gains / losses if losses else None,
        profit_factor_status="AVAILABLE" if losses else "UNAVAILABLE_NO_LOSING_CLOSED_TRADES",
        expectancy=float(np.mean(trade_pnl)) if closed else None,
        expectancy_basis="MEAN_CLOSED_TRADE_NET_PNL_NOT_EXPECTED_FUTURE_RETURN",
        trade_statistics_scope="CLOSED_ONLY_UNRESOLVED_COUNT_RETAINED",
        turnover=traded / mean_nav if mean_nav and marked else None,
        turnover_basis="ENTRY_PLUS_EXIT_NOMINAL_NOTIONAL_DIVIDED_BY_MEAN_SESSION_NAV",
        average_holding_sessions=float(np.mean([r["holding_sessions"] for r in closed]))
        if closed
        else None,
        exposure=float(np.mean([r["open_positions"] > 0 for r in pnl])) if pnl else None,
        cash_utilization=float(np.mean([r["cash_utilization"] for r in pnl]))
        if pnl and marked
        else None,
        benchmark_name=definition.benchmark.name if definition.benchmark else None,
        benchmark_return=benchmark_return,
        benchmark_relative_return=final / capital - 1 - benchmark_return
        if final is not None and benchmark_return is not None
        else None,
        benchmark_status="PRICE_ONLY_COST_FREE_REFERENCE"
        if benchmark_return is not None
        else "UNAVAILABLE",
        no_fill_count=sum(str(d["status"]).startswith("NO_FILL") for d in decisions),
        fold_trade_diagnostics={
            fold: dict(
                trade_count=len(rows),
                closed_trade_count=sum(r["exit_session"] is not None for r in rows),
                unresolved_count=sum(r["exit_session"] is None for r in rows),
                closed_net_pnl=sum(float(r["net_pnl"]) for r in rows if r["net_pnl"] is not None),
                basis="TRADE_ORIGIN_FOLD_NOT_INDEPENDENT_FOLD_PORTFOLIO_RETURN",
            )
            for fold, rows in sorted(by_fold.items())
        },
    )
