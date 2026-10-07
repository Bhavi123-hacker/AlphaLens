"""Chart contracts reference actual snapshots and P5 bars; never interpolate."""

from datetime import date, datetime
from fractions import Fraction

from alphalens_backtesting.contracts import BenchmarkEvidence
from alphalens_data.canonical.models import PriceView, ReadContext
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.contracts import Contract

from .contracts import Ledger
from .valuation import DecisionHistory, PortfolioSnapshot, valid_price, value


class History(Contract):
    valuations: tuple[PortfolioSnapshot, ...]
    per_security: dict[str, tuple[dict[str, object], ...]]
    portfolio_series: tuple[dict[str, object], ...]


def monitoring_history(
    evidence: DecisionHistory,
    security: str,
    session: date,
    cutoff: datetime,
) -> dict[str, tuple[dict[str, object], ...]]:
    return {
        "risk": tuple(
            record.model_dump(mode="json")
            for record in evidence.risks
            if record.security_id == security
            and record.session_date <= session
            and record.knowledge_cutoff <= cutoff
        ),
        "rank": tuple(
            record.model_dump(mode="json")
            for record in evidence.rankings
            if record.session_date <= session
            and record.knowledge_cutoff <= cutoff
            and (
                any(c.security_id == security for c in record.ranked)
                or any(e.security_id == security for e in record.excluded)
            )
        ),
        "signal": tuple(
            s.model_dump(mode="json")
            for s in evidence.signals
            if s.security_id == security
            and s.session_date <= session
            and s.knowledge_cutoff <= cutoff
        ),
        "prediction": tuple(
            p.model_dump(mode="json")
            for p in evidence.predictions
            if p.security_id == security and p.session_date <= session and p.available_at <= cutoff
        ),
    }


def build_history(
    ledger: Ledger,
    reader: CanonicalReader,
    observations: tuple[tuple[date, datetime], ...],
    decisions: DecisionHistory | None = None,
) -> History:
    if list(observations) != sorted(set(observations)) or len({s for s, _ in observations}) != len(
        observations
    ):
        raise ValueError("Unique chronological observation sessions required")
    snapshots: list[PortfolioSnapshot] = []
    securities: dict[str, list[dict[str, object]]] = {}
    series: list[dict[str, object]] = []
    for session, cutoff in observations:
        if cutoff < ledger.portfolio.created_at:
            continue
        v = value(ledger, reader, session, cutoff, decisions, snapshots[-1] if snapshots else None)
        snapshots.append(v)
        series.append(
            {
                "session": session.isoformat(),
                "snapshot_id": v.snapshot_id,
                "cash": str(v.ledger_state.cash),
                "invested_value": str(v.total_cost_basis),
                "market_value": _text(v.total_market_value),
                "portfolio_value": _text(v.portfolio_value),
                "session_pnl": _text(v.session_pnl),
                "cumulative_pnl": _text(v.total_pnl),
                "cumulative_return_percentage": _text(v.cumulative_return_percentage),
                "freshness": v.freshness,
                "classification": v.market_classification.value,
            }
        )
        for p in v.positions:
            securities.setdefault(p.accounting.security_id, []).append(
                {
                    "session": session.isoformat(),
                    "snapshot_id": v.snapshot_id,
                    "quantity": str(p.accounting.quantity),
                    "market_price": _text(p.valuation_price),
                    "cost_basis": str(p.accounting.cost_basis),
                    "market_value": _text(p.market_value),
                    "realized_pnl": str(p.accounting.realized_pnl),
                    "unrealized_pnl": _text(p.unrealized_pnl),
                    "total_pnl": _text(p.total_pnl),
                    "return_percentage": _text(p.return_percentage),
                    "freshness": p.freshness,
                    "quality": p.quality,
                    "symbol": p.symbol,
                    "decisions": p.decisions.model_dump(mode="json"),
                }
            )
    return History(
        valuations=tuple(snapshots),
        per_security={k: tuple(v) for k, v in securities.items()},
        portfolio_series=tuple(series),
    )


def _text(value: Fraction | None) -> str | None:
    return str(value) if value is not None else None


def price_history(
    reader: CanonicalReader, security: str, start: date, end: date, cutoff: datetime
) -> tuple[PriceView, ...]:
    # Reuse P5 views including rejected/missing records and their declared quality/basis.
    return tuple(
        p
        for p in reader.prices_as_of(start, end, ReadContext(knowledge_cutoff=cutoff)).records
        if p.observation.security_id == security
    )


class BenchmarkComparison(Contract):
    availability: str
    reason: str
    name: str | None = None
    points: tuple[dict[str, object], ...] = ()
    normalization: str = "100_AT_COMMON_START_FLOW_ADJUSTED_PORTFOLIO_NOT_ANNUALIZED"


def benchmark_comparison(
    history: History,
    reader: CanonicalReader,
    evidence: BenchmarkEvidence | None = None,
) -> BenchmarkComparison:
    if not evidence:
        return BenchmarkComparison(
            availability="UNAVAILABLE", reason="BENCHMARK_EVIDENCE_UNAVAILABLE"
        )
    if (
        evidence.canonical_input_id != reader.batch.input_id
        or evidence.classification != reader.batch.classification
    ):
        raise ValueError("Benchmark input/classification mismatch")
    aligned: list[tuple[PortfolioSnapshot, Fraction]] = []
    for v in history.valuations:
        if v.freshness != "EOD_COMPLETE" or not v.portfolio_value:
            continue
        bars = price_history(reader, evidence.security_id, v.session, v.session, v.knowledge_cutoff)
        valid = [p for p in bars if valid_price(p)]
        if len(valid) == 1 and valid[0].observation.values:
            aligned.append((v, Fraction(valid[0].observation.values.close)))
    if not aligned:
        return BenchmarkComparison(
            availability="UNAVAILABLE", reason="NO_COMMON_EVIDENCED_SESSIONS", name=evidence.name
        )
    base = aligned[0][1]
    normalized = Fraction(100)
    points: list[dict[str, object]] = []
    previous: PortfolioSnapshot | None = None
    for v, price in aligned:
        if previous and previous.portfolio_value and v.portfolio_value:
            flows = v.ledger_state.net_external_capital - previous.ledger_state.net_external_capital
            normalized *= (v.portfolio_value - flows) / previous.portfolio_value
        benchmark = 100 * price / base
        points.append(
            {
                "session": v.session.isoformat(),
                "portfolio_normalized": str(normalized),
                "benchmark_normalized": str(benchmark),
                "portfolio_return": str(normalized / 100 - 1),
                "benchmark_return": str(benchmark / 100 - 1),
                "relative_return": str((normalized - benchmark) / 100),
                "classification": evidence.classification.value,
            }
        )
        previous = v
    return BenchmarkComparison(
        availability="AVAILABLE",
        reason="OBSERVED_PRICE_ONLY_NOT_TOTAL_RETURN",
        name=evidence.name,
        points=tuple(points),
    )
