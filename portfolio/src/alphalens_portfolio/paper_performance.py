"""Paper chart series use P15 values; no annualization or manufactured benchmark."""

from fractions import Fraction

from alphalens_backtesting.contracts import BenchmarkEvidence
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.contracts import Contract

from .history import BenchmarkComparison, History, benchmark_comparison
from .paper import cash_reserved, order_states
from .paper_contracts import PaperState, paper_disclaimer


class PaperPerformance(Contract):
    starting_capital: Fraction
    equity: Fraction | None
    cash: Fraction
    reserved_cash: Fraction
    available_cash: Fraction
    market_value: Fraction | None
    realized_pnl: Fraction
    unrealized_pnl: Fraction | None
    total_pnl: Fraction | None
    session_pnl: Fraction | None
    return_percentage: Fraction | None
    maximum_drawdown: Fraction | None
    simulated_fill_count: int
    closed_position_cycles: int
    wins: int
    losses: int
    breakeven_cycles: int
    fees: Fraction
    slippage_amount: Fraction
    classification: str
    freshness: str
    disclaimer: str
    benchmark_availability: str = "UNAVAILABLE"
    benchmark_reason: str = "BENCHMARK_EVIDENCE_UNAVAILABLE_USE_P15_ALIGNMENT_WHEN_EVIDENCED"


def chart_series(state: PaperState) -> dict[str, object]:
    equity = []
    pnl = []
    drawdown = []
    per_security: dict[str, list[dict[str, object]]] = {}
    peak = Fraction(0)
    valid_count = 0
    for report in state.reports:
        v = report.valuation
        marked = v.portfolio_value if v.freshness == "EOD_COMPLETE" else None
        if marked is not None:
            valid_count += 1
            peak = max(peak, marked)
        dd = (peak - marked) / peak if marked is not None and peak and valid_count >= 2 else None
        equity.append(
            {
                "session": report.session.isoformat(),
                "equity": str(marked) if marked is not None else None,
                "freshness": v.freshness,
                "report_id": report.report_id,
            }
        )
        pnl.append(
            {
                "session": report.session.isoformat(),
                "total_pnl": str(v.total_pnl) if v.total_pnl is not None else None,
                "session_pnl": str(v.session_pnl) if v.session_pnl is not None else None,
            }
        )
        drawdown.append(
            {"session": report.session.isoformat(), "drawdown": str(dd) if dd is not None else None}
        )
        for p in v.positions:
            per_security.setdefault(p.accounting.security_id, []).append(
                {
                    "session": report.session.isoformat(),
                    "quantity": str(p.accounting.quantity),
                    "total_pnl": str(p.total_pnl) if p.total_pnl is not None else None,
                    "freshness": p.freshness,
                    "annotations": [a.model_dump(mode="json") for a in p.decisions.annotations],
                }
            )
    statuses = order_states(state)
    return {
        "equity": equity,
        "pnl": pnl,
        "drawdown": drawdown,
        "per_security": per_security,
        "trade_markers": [f.model_dump(mode="json") for f in state.fills],
        "signal_markers": [
            o.explanation.annotation().model_dump(mode="json")
            for o in state.orders
            if o.explanation
        ],
        "order_states": statuses,
        "classification": state.classification,
        "disclaimer": paper_disclaimer(state.classification),
    }


def performance(state: PaperState) -> PaperPerformance:
    if not state.reports:
        return PaperPerformance(
            starting_capital=state.starting_cash,
            equity=state.starting_cash,
            cash=state.starting_cash,
            reserved_cash=Fraction(0),
            available_cash=state.starting_cash,
            market_value=Fraction(0),
            realized_pnl=Fraction(0),
            unrealized_pnl=Fraction(0),
            total_pnl=Fraction(0),
            session_pnl=None,
            return_percentage=Fraction(0),
            maximum_drawdown=None,
            simulated_fill_count=0,
            closed_position_cycles=0,
            wins=0,
            losses=0,
            breakeven_cycles=0,
            fees=Fraction(0),
            slippage_amount=Fraction(0),
            classification=state.classification,
            freshness="CASH_ONLY_NO_MARKET_VALUATION",
            disclaimer=paper_disclaimer(state.classification),
        )
    last = state.reports[-1]
    # Closed cycles reconstructed from actual immutable fills; partial exits are not wins/losses.
    orders = {o.order_id: o for o in state.orders}
    previous_closed_realized: dict[str, Fraction] = {}
    closed: list[Fraction] = []
    fills = {f.fill_id: f for f in state.fills}
    for report in state.reports:
        exited = {orders[fills[f].order_id].security_id for f in report.exits}
        for p in report.valuation.ledger_state.positions:
            if p.security_id in exited and p.quantity == 0:
                closed.append(
                    p.realized_pnl - previous_closed_realized.get(p.security_id, Fraction(0))
                )
                previous_closed_realized[p.security_id] = p.realized_pnl
    charts = chart_series(state)
    points = charts["drawdown"]
    if not isinstance(points, list):
        raise ValueError("Drawdown contract mismatch")
    dd = [Fraction(p["drawdown"]) for p in points if p["drawdown"] is not None]
    v = last.valuation
    return PaperPerformance(
        starting_capital=state.starting_cash,
        equity=v.portfolio_value,
        cash=v.ledger_state.cash,
        reserved_cash=cash_reserved(state),
        available_cash=v.ledger_state.cash - cash_reserved(state),
        market_value=v.total_market_value,
        realized_pnl=v.realized_pnl,
        unrealized_pnl=v.unrealized_pnl,
        total_pnl=v.total_pnl,
        session_pnl=v.session_pnl,
        return_percentage=100 * v.total_pnl / state.starting_cash
        if v.total_pnl is not None
        else None,
        maximum_drawdown=max(dd) if dd else None,
        simulated_fill_count=len(state.fills),
        closed_position_cycles=len(closed),
        wins=sum(p > 0 for p in closed),
        losses=sum(p < 0 for p in closed),
        breakeven_cycles=sum(p == 0 for p in closed),
        fees=sum((f.fees for f in state.fills), Fraction(0)),
        slippage_amount=sum((f.slippage_amount for f in state.fills), Fraction(0)),
        classification=state.classification,
        freshness=v.freshness,
        disclaimer=paper_disclaimer(state.classification),
    )


def compare_benchmark(
    state: PaperState, reader: CanonicalReader, evidence: BenchmarkEvidence | None = None
) -> BenchmarkComparison:
    history = History(
        valuations=tuple(r.valuation for r in state.reports), per_security={}, portfolio_series=()
    )
    return benchmark_comparison(history, reader, evidence)
