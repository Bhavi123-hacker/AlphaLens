"""P5 evidenced EOD marks, exact P&L and optional immutable decision references."""

from datetime import date, datetime
from fractions import Fraction
from typing import Any, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, model_validator

from alphalens_data.canonical.models import PriceView, ReadContext, revision_key
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_decision.explanation_contracts import ChartAnnotation, ExplainabilitySnapshot
from alphalens_decision.models import PredictionEvidence
from alphalens_decision.ranking_contracts import RankSnapshot
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_decision.signal_contracts import SignalSnapshot
from alphalens_evaluation.contracts import digest

from .accounting import reconstruct
from .contracts import AccountingState, Ledger, Position


class DecisionHistory(Contract):
    predictions: tuple[PredictionEvidence, ...] = ()
    risks: tuple[RiskSnapshot, ...] = ()
    rankings: tuple[RankSnapshot, ...] = ()
    signals: tuple[SignalSnapshot, ...] = ()
    explanations: tuple[ExplainabilitySnapshot, ...] = ()

    @model_validator(mode="after")
    def verify(self) -> Self:
        for records in (
            self.risks,
            self.rankings,
            self.signals,
            self.explanations,
            self.predictions,
        ):
            for record in records:
                type(record).model_validate(record.model_dump(mode="json"))
        return self


class DecisionReferences(Contract):
    risk_snapshot_id: str | None = None
    risk_level: str = "UNAVAILABLE"
    ranks: dict[str, int] = {}
    ranking_ids: tuple[str, ...] = ()
    signals: dict[str, str] = {}
    signal_ids: tuple[str, ...] = ()
    prediction_ids: tuple[str, ...] = ()
    annotations: tuple[ChartAnnotation, ...] = ()


class PositionValue(Contract):
    accounting: Position
    symbol: str
    average_display_cost: Fraction | None
    valuation_price: Fraction | None
    valuation_session: date | None
    price_basis: str | None
    quality: str
    freshness: Literal["EOD_COMPLETE", "STALE", "UNAVAILABLE", "UNRESOLVED"]
    price_revision_key: str | None
    source_lineage: dict[str, object]
    market_value: Fraction | None
    unrealized_pnl: Fraction | None
    total_pnl: Fraction | None
    return_percentage: Fraction | None
    session_pnl: Fraction | None = None
    reasons: tuple[str, ...]
    decisions: DecisionReferences


class PortfolioSnapshot(Contract):
    snapshot_id: Hash
    version: Literal["p15.valuation.v1"] = "p15.valuation.v1"
    portfolio_id: str
    session: date
    knowledge_cutoff: AwareDatetime
    ledger_state: AccountingState
    canonical_dataset_id: Hash
    canonical_input_id: Hash
    accounting_policy_id: Hash
    positions: tuple[PositionValue, ...]
    total_cost_basis: Fraction
    total_market_value: Fraction | None
    portfolio_value: Fraction | None
    realized_pnl: Fraction
    unrealized_pnl: Fraction | None
    total_pnl: Fraction | None
    cumulative_return_percentage: Fraction | None
    session_pnl: Fraction | None
    number_of_holdings: int
    freshness: str
    stale_positions: tuple[str, ...]
    unavailable_positions: tuple[str, ...]
    risk_summary: dict[str, object]
    portfolio_classification: str
    market_classification: Classification
    execution_classifications: tuple[str, ...]
    disclaimer: str
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def immutable(self) -> Self:
        if self.snapshot_id != digest(self.model_dump(mode="json", exclude={"snapshot_id"})):
            raise ValueError("Portfolio snapshot identity mismatch")
        return self


def references(
    history: DecisionHistory,
    security: str,
    session: date,
    cutoff: datetime,
    classification: Classification,
) -> DecisionReferences:
    # Constructors enforce source identities; revalidate copied/mutated Pydantic values.
    risks = sorted(
        (
            RiskSnapshot.model_validate(r.model_dump(mode="json"))
            for r in history.risks
            if r.security_id == security
            and r.session_date <= session
            and r.knowledge_cutoff <= cutoff
            and r.classification == classification
        ),
        key=lambda r: (r.session_date, r.knowledge_cutoff, r.risk_snapshot_id),
    )
    signals = sorted(
        (
            SignalSnapshot.model_validate(s.model_dump(mode="json"))
            for s in history.signals
            if s.security_id == security
            and s.session_date <= session
            and s.knowledge_cutoff <= cutoff
            and s.classification == classification
        ),
        key=lambda s: (s.session_date, s.knowledge_cutoff, s.signal_snapshot_id),
    )
    latest_signals = {str(s.horizon): s for s in signals}
    ranks: dict[str, int] = {}
    ranking_ids: dict[str, str] = {}
    for r in sorted(
        history.rankings, key=lambda r: (r.session_date, r.knowledge_cutoff, r.rank_snapshot_id)
    ):
        if (
            r.session_date > session
            or r.knowledge_cutoff > cutoff
            or r.classification != classification
        ):
            continue
        RankSnapshot.model_validate(r.model_dump(mode="json"))
        candidate = next((c for c in r.ranked if c.security_id == security), None)
        if candidate:
            ranks[str(r.horizon)] = candidate.rank
            ranking_ids[str(r.horizon)] = r.rank_snapshot_id
        else:
            ranks.pop(str(r.horizon), None)
            ranking_ids.pop(str(r.horizon), None)
    ids = {s.signal_snapshot_id for s in signals}
    annotations = tuple(
        e.annotation()
        for e in sorted(
            history.explanations, key=lambda e: (e.session_date, e.horizon, e.explanation_id)
        )
        if e.signal_snapshot_id in ids
        and e.knowledge_cutoff <= cutoff
        and e.classification == classification
    )
    return DecisionReferences(
        risk_snapshot_id=risks[-1].risk_snapshot_id if risks else None,
        risk_level=risks[-1].overall_level if risks else "UNAVAILABLE",
        ranks=ranks,
        ranking_ids=tuple(ranking_ids[k] for k in sorted(ranking_ids)),
        signals={h: s.state for h, s in sorted(latest_signals.items())},
        signal_ids=tuple(s.signal_snapshot_id for _, s in sorted(latest_signals.items())),
        prediction_ids=tuple(sorted({p for s in signals for p in s.prediction_ids})),
        annotations=annotations,
    )


def valid_price(view: PriceView) -> bool:
    o = view.observation
    return (
        view.quality == "VALID"
        and view.availability == "AVAILABLE"
        and o.values is not None
        and o.currency == "INR"
        and o.price_basis == "RAW_UNADJUSTED"
    )


def value(
    ledger: Ledger,
    reader: CanonicalReader,
    session: date,
    cutoff: datetime,
    history: DecisionHistory | None = None,
    previous: PortfolioSnapshot | None = None,
) -> PortfolioSnapshot:
    if cutoff.astimezone(ZoneInfo("Asia/Kolkata")).date() < session:
        raise ValueError("Valuation session follows cutoff")
    state = reconstruct(ledger, session, cutoff)
    context = ReadContext(knowledge_cutoff=cutoff)
    try:
        dataset = reader.build(date.min, session, context)
        dataset_id = dataset.dataset_id
    except DataContractError as error:
        if error.code != "CANONICAL_SNAPSHOT_HAS_NO_KNOWN_SESSIONS":
            raise
        dataset_id = digest(
            {
                "version": "p15.empty_price_read.v1",
                "canonical_input_id": reader.batch.input_id,
                "knowledge_cutoff": cutoff.isoformat(),
                "session": session.isoformat(),
            }
        )
    classification = reader.batch.classification
    prices = reader.prices_as_of(date.min, session, context).records
    actions_at_cutoff = reader.corporate_actions_as_of(context).records
    classification_blocked = ledger.portfolio.classification != classification.value
    # USER_RECORDED is a real-holding declaration, not permission to use research/fixture marks.
    result: list[PositionValue] = []
    for p in state.positions:
        symbol = next(
            (
                e.fact.symbol
                for e in reader.security_metadata_as_of(session, context).records
                if e.security_id == p.security_id
            ),
            p.transaction_symbol,
        )
        reasons: list[str] = []
        candidates = [
            v
            for v in prices
            if v.observation.security_id == p.security_id
            and v.observation.session_date >= p.first_session
            and valid_price(v)
        ]
        latest = max(candidates, key=lambda v: v.observation.session_date) if candidates else None
        actions = [
            a
            for a in actions_at_cutoff
            if a.security_id == p.security_id
            and p.first_session <= (a.ex_date or a.effective_from) <= session
            and a.event_type != "SYMBOL_CHANGE"
        ]
        universe = reader.universe_as_of(session, context)
        entry = next(
            (
                e
                for e in (*universe.eligible_securities, *universe.excluded_securities)
                if e.security_id == p.security_id
            ),
            None,
        )
        terminal = bool(
            entry
            and entry.membership_evidence
            and entry.membership_evidence.listing_status == "DELISTED"
        )
        price: Fraction | None = None
        freshness: Literal["EOD_COMPLETE", "STALE", "UNAVAILABLE", "UNRESOLVED"] = "UNAVAILABLE"
        if p.quantity == 0:
            freshness = "EOD_COMPLETE"
        elif classification_blocked:
            reasons.append("CLASSIFICATION_BLOCKED")
        elif actions or terminal:
            freshness = "UNRESOLVED"
            reasons.append(
                "CORPORATE_ACTION_UNRESOLVED" if actions else "TERMINAL_VALUE_UNRESOLVED"
            )
        elif latest and latest.observation.values:
            price = Fraction(latest.observation.values.close)
            freshness = "EOD_COMPLETE" if latest.observation.session_date == session else "STALE"
            if freshness == "STALE":
                reasons.append("LATEST_VALID_EOD_IS_OLDER_THAN_REQUESTED_SESSION")
        else:
            reasons.append("VALID_RAW_EOD_PRICE_UNAVAILABLE")
        mv = price * p.quantity if price is not None else Fraction(0) if not p.quantity else None
        unrealized = mv - p.cost_basis if mv is not None else None
        total = p.realized_pnl + unrealized if unrealized is not None else None
        old = (
            next((v for v in previous.positions if v.accounting.security_id == p.security_id), None)
            if previous
            else None
        )
        session_pnl = (
            total - old.total_pnl
            if total is not None
            and old
            and old.total_pnl is not None
            and freshness == "EOD_COMPLETE"
            and old.freshness == "EOD_COMPLETE"
            else None
        )
        result.append(
            PositionValue(
                accounting=p,
                symbol=symbol,
                average_display_cost=p.cost_basis / p.quantity if p.quantity else None,
                valuation_price=price,
                valuation_session=latest.observation.session_date
                if price is not None and latest
                else None,
                price_basis=latest.observation.price_basis
                if price is not None and latest
                else None,
                quality=str(latest.quality) if price is not None and latest else "UNAVAILABLE",
                freshness=freshness,
                price_revision_key=revision_key(latest.observation)
                if price is not None and latest
                else None,
                source_lineage=latest.observation.provenance.model_dump(mode="json")
                if price is not None and latest
                else {},
                market_value=mv,
                unrealized_pnl=unrealized,
                total_pnl=total,
                return_percentage=100 * total / p.gross_acquisition_basis
                if total is not None and p.gross_acquisition_basis
                else None,
                session_pnl=session_pnl,
                reasons=tuple(reasons),
                decisions=references(
                    history or DecisionHistory(),
                    p.security_id,
                    session,
                    cutoff,
                    classification,
                ),
            )
        )
    if previous and (
        previous.portfolio_id != ledger.portfolio.portfolio_id
        or previous.session >= session
        or previous.knowledge_cutoff > cutoff
        or previous.market_classification != classification
        or previous.accounting_policy_id
        != digest(ledger.portfolio.accounting_policy.model_dump(mode="json"))
    ):
        raise ValueError("Session P&L requires compatible strictly prior snapshot")
    unpriced = any(p.market_value is None for p in result)
    market = None if unpriced else sum((p.market_value or Fraction(0) for p in result), Fraction(0))
    unreal = (
        None if unpriced else sum((p.unrealized_pnl or Fraction(0) for p in result), Fraction(0))
    )
    realized = sum((p.accounting.realized_pnl for p in result), Fraction(0))
    total = realized + unreal if unreal is not None else None
    equity = state.cash + market if market is not None else None
    session_pnl = (
        equity
        - previous.portfolio_value
        - (state.net_external_capital - previous.ledger_state.net_external_capital)
        if equity is not None
        and previous
        and previous.portfolio_value is not None
        and previous.freshness == "EOD_COMPLETE"
        and all(p.freshness == "EOD_COMPLETE" for p in result)
        else None
    )
    counts: dict[str, int] = {}
    values: dict[str, str | None] = {}
    for position_value in result:
        if not position_value.accounting.quantity:
            continue
        level = position_value.decisions.risk_level
        counts[level] = counts.get(level, 0) + 1
        if position_value.market_value is None or (level in values and values[level] is None):
            values[level] = None
        else:
            values[level] = str(Fraction(values.get(level) or "0") + position_value.market_value)
    stale = tuple(p.accounting.security_id for p in result if p.freshness == "STALE")
    unavailable = tuple(
        p.accounting.security_id for p in result if p.freshness in {"UNAVAILABLE", "UNRESOLVED"}
    )
    freshness = "UNAVAILABLE" if unavailable else "STALE" if stale else "EOD_COMPLETE"
    gross = sum((p.accounting.gross_acquisition_basis for p in result), Fraction(0))
    data = dict(
        version="p15.valuation.v1",
        portfolio_id=ledger.portfolio.portfolio_id,
        session=session,
        knowledge_cutoff=cutoff,
        ledger_state=state,
        canonical_dataset_id=dataset_id,
        canonical_input_id=reader.batch.input_id,
        accounting_policy_id=digest(ledger.portfolio.accounting_policy.model_dump(mode="json")),
        positions=tuple(result),
        total_cost_basis=sum((p.accounting.cost_basis for p in result), Fraction(0)),
        total_market_value=market,
        portfolio_value=equity,
        realized_pnl=realized,
        unrealized_pnl=unreal,
        total_pnl=total,
        cumulative_return_percentage=100 * total / gross if total is not None and gross else None,
        session_pnl=session_pnl,
        number_of_holdings=sum(bool(p.accounting.quantity) for p in result),
        freshness=freshness,
        stale_positions=stale,
        unavailable_positions=unavailable,
        risk_summary={
            "method": "SECURITY_RISK_SUMMARY_NOT_PORTFOLIO_RISK_MODEL",
            "count_by_level": counts,
            "market_value_by_level": values,
            "largest_position_fraction": str(
                max((p.market_value or Fraction(0) for p in result), default=Fraction(0)) / market
            )
            if market
            else None,
        },
        portfolio_classification=ledger.portfolio.classification,
        market_classification=classification,
        execution_classifications=tuple(
            sorted(
                {
                    t.classification
                    for t in ledger.transactions
                    if t.transaction_id in state.transaction_ids
                }
            )
        ),
        disclaimer="TEST_ONLY — NOT A REAL MARKET VALUATION"
        if classification == Classification.TEST_ONLY
        else "RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED",
        production_claims_permitted=False,
    )
    return PortfolioSnapshot.model_validate({"snapshot_id": digest(_json_data(data)), **data})


def _json_data(data: dict[str, Any]) -> dict[str, Any]:
    # Generate the contract's exact JSON representation before computing its identity.
    provisional = PortfolioSnapshot.model_construct(snapshot_id="0" * 64, **data)
    return provisional.model_dump(mode="json", exclude={"snapshot_id"})
