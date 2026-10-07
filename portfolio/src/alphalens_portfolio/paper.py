"""Forward EOD session simulation. P15 exclusively owns cash, FIFO and valuation."""

from datetime import date, datetime, timedelta
from fractions import Fraction
from typing import Any, Literal
from zoneinfo import ZoneInfo

from alphalens_backtesting.contracts import ExecutionCalendar
from alphalens_data.canonical.models import ReadContext, revision_key
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.contracts import Contract
from alphalens_decision.signal_contracts import PositionEvidence
from alphalens_evaluation.contracts import digest

from .accounting import append, reconstruct
from .contracts import Ledger, Portfolio, Transaction
from .paper_contracts import (
    ManualPaperOrder,
    OrderEvent,
    PaperFill,
    PaperOrder,
    PaperPolicy,
    PaperReport,
    PaperState,
    market_class,
    paper_disclaimer,
)
from .valuation import DecisionHistory, valid_price, value


def seal[T: Contract](model: type[T], identity: str, **data: Any) -> T:
    """Internal typed engine values; external input always goes through model_validate."""
    draft = model.model_construct(**{identity: "0" * 64, **data})
    payload = draft.model_dump(mode="json", exclude={identity})
    return model.model_validate({identity: digest(payload), **payload})


def create(portfolio: Portfolio, starting_cash: Fraction) -> PaperState:
    if portfolio.portfolio_type != "PAPER" or starting_cash <= 0:
        raise ValueError("Funded PAPER portfolio required")
    classification: Literal["PAPER", "TEST_ONLY_PAPER"] = (
        "TEST_ONLY_PAPER" if portfolio.classification == "TEST_ONLY" else "PAPER"
    )
    deposit = Transaction(
        transaction_id=digest((portfolio.portfolio_id, "P16_STARTING_CAPITAL")),
        portfolio_id=portfolio.portfolio_id,
        kind="CASH_DEPOSIT",
        session=portfolio.created_at.astimezone(ZoneInfo("Asia/Kolkata")).date(),
        effective_at=portfolio.created_at,
        recorded_at=portfolio.created_at,
        cash_amount=starting_cash,
        source="P16_SIMULATED_STARTING_CAPITAL",
        classification=classification,
        evidence_reference="P16_DECLARED_SIMULATED_CAPITAL",
    )
    return PaperState(
        ledger=append(Ledger(portfolio=portfolio), deposit), starting_cash=starting_cash
    )


def order_states(state: PaperState) -> dict[str, str]:
    return {event.order_id: event.state for event in state.events}


def pending(state: PaperState) -> tuple[PaperOrder, ...]:
    statuses = order_states(state)
    return tuple(o for o in state.orders if statuses[o.order_id] == "PENDING")


def cash_reserved(state: PaperState) -> Fraction:
    return sum((o.reserved_cash for o in pending(state)), Fraction(0))


def _event(
    order: PaperOrder, at: datetime, status: str, reason: str, fill: PaperFill | None = None
) -> OrderEvent:
    return seal(
        OrderEvent,
        "event_id",
        order_id=order.order_id,
        recorded_at=at,
        state=status,
        reason=reason,
        fill_id=fill.fill_id if fill else None,
    )


def cancel(state: PaperState, order_id: str, at: datetime, reason: str) -> PaperState:
    if state.reports and at < state.reports[-1].knowledge_cutoff:
        raise ValueError("Cancellation cannot rewrite earlier paper state")
    order = next((o for o in pending(state) if o.order_id == order_id), None)
    if not order or at < order.decision_at:
        raise ValueError("Only a known pending order can be cancelled")
    return PaperState.model_validate(
        {
            **state.model_dump(mode="python"),
            "events": (*state.events, _event(order, at, "CANCELLED", reason)),
        }
    )


def next_open(calendar: ExecutionCalendar, session: date, cutoff: datetime) -> Any:
    days = {d.session_date: d for d in calendar.days if d.available_at <= cutoff}
    cursor = session + timedelta(days=1)
    while cursor in days:
        day = days[cursor]
        if day.status == "VERIFIED_TRADING_SESSION":
            if not day.open_at or day.open_clock_policy == "UNKNOWN":
                raise ValueError("NEXT_OPEN_CLOCK_UNAVAILABLE")
            if day.open_at <= cutoff:
                raise ValueError("NEXT_OPEN_ALREADY_PASSED_NO_RETROACTIVE_INTENT")
            return day
        if day.status != "VERIFIED_NON_TRADING_SESSION":
            break
        cursor += timedelta(days=1)
    raise ValueError("NEXT_SESSION_EVIDENCE_UNAVAILABLE")


def _fill(
    state: PaperState,
    order: PaperOrder,
    reader: CanonicalReader,
    session: date,
    cutoff: datetime,
) -> tuple[PaperFill | None, Ledger, str]:
    views = reader.prices_as_of(session, session, ReadContext(knowledge_cutoff=cutoff)).records
    bars = [v for v in views if v.observation.security_id == order.security_id and valid_price(v)]
    if len(bars) != 1 or not bars[0].observation.values:
        return None, state.ledger, "NEXT_OPEN_MISSING_REJECTED_OR_UNAVAILABLE"
    bar = bars[0].observation
    if bar.values is None:
        return None, state.ledger, "NEXT_OPEN_UNAVAILABLE"
    if not bar.provenance.available_at or not order.target.open_at:
        return None, state.ledger, "PRICE_OR_OPEN_CLOCK_UNAVAILABLE"
    # P4 must establish contemporaneous listing before the simulated open.
    universe = reader.universe_as_of(session, ReadContext(knowledge_cutoff=order.target.open_at))
    if order.security_id not in {e.security_id for e in universe.eligible_securities}:
        return None, state.ledger, "HISTORICAL_ELIGIBILITY_UNAVAILABLE"
    actions = reader.corporate_actions_as_of(ReadContext(knowledge_cutoff=cutoff)).records
    action_start = order.decision_session
    if order.side == "SELL":
        position = next(
            (
                p
                for p in reconstruct(state.ledger, session, cutoff).positions
                if p.security_id == order.security_id
            ),
            None,
        )
        if position:
            action_start = position.first_session - timedelta(days=1)
    if any(
        a.security_id == order.security_id
        and (a.ex_date or a.effective_from) <= session
        and (a.ex_date or a.effective_from) > action_start
        and a.event_type != "SYMBOL_CHANGE"
        for a in actions
    ):
        return None, state.ledger, "CORPORATE_ACTION_UNRESOLVED"
    observed = Fraction(bar.values.open)
    scenario = order.policy.costs
    price = observed * (1 + scenario.slip_rate if order.side == "BUY" else 1 - scenario.slip_rate)
    quantity = order.quantity
    if quantity is None:
        quantity = int(order.reserved_cash / (price * (1 + scenario.fee_rate)))
    if quantity <= 0:
        return None, state.ledger, "BUDGET_BELOW_ONE_SHARE"
    fees = price * quantity * scenario.fee_rate
    cost = quantity * price + fees
    state_cash = reconstruct(state.ledger, session, cutoff).cash
    if order.side == "BUY" and (cost > order.reserved_cash or cost > state_cash):
        return None, state.ledger, "RESERVED_CASH_LIMIT_EXCEEDED"
    transaction_id = digest((order.order_id, "SIMULATED_FILL_TRANSACTION"))
    fill_symbol = next(
        (
            r.fact.symbol
            for r in reader.security_metadata_as_of(
                session, ReadContext(knowledge_cutoff=order.target.open_at)
            ).records
            if r.security_id == order.security_id
        ),
        order.symbol,
    )
    fill = seal(
        PaperFill,
        "fill_id",
        order_id=order.order_id,
        session=session,
        simulated_at=order.target.open_at,
        evidence_available_at=bar.provenance.available_at,
        quantity=quantity,
        observed_open=observed,
        simulated_price=price,
        fees=fees,
        slippage_amount=abs(price - observed) * quantity,
        price_revision_key=revision_key(bar),
        canonical_input_id=reader.batch.input_id,
        source_lineage={
            **bar.provenance.model_dump(mode="json"),
            "p3_quality_key": bar.quality_key,
            "symbol_at_simulated_open": fill_symbol,
            "p2_links": [
                link.model_dump(mode="json")
                for link in reader.batch.lineage
                if link.record_key == revision_key(bar)
            ],
            "cost_scenario": scenario.model_dump(mode="json"),
        },
        transaction_id=transaction_id,
        classification=state.classification,
        execution="SIMULATED_FILL_NOT_REAL_EXECUTION",
    )
    transaction = Transaction(
        transaction_id=transaction_id,
        portfolio_id=order.account_id,
        kind=order.side,
        security_id=order.security_id,
        symbol=fill_symbol,
        session=session,
        effective_at=order.target.open_at,
        recorded_at=cutoff,
        quantity=Fraction(quantity),
        price=price,
        fees=fees,
        source="P16_SIMULATED_FILL",
        classification=state.classification,
        evidence_reference=fill.fill_id,
        notes=order.reason,
    )
    try:
        ledger = append(state.ledger, transaction)
    except ValueError:
        return None, state.ledger, "ACCOUNTING_POLICY_BLOCKED"
    return fill, ledger, "EVIDENCED_NEXT_OPEN_SIMULATED_FILL"


def process_session(
    state: PaperState,
    reader: CanonicalReader,
    calendar: ExecutionCalendar,
    session: date,
    cutoff: datetime,
    policy: PaperPolicy | None = None,
    manual: tuple[ManualPaperOrder, ...] = (),
    history: DecisionHistory | None = None,
) -> PaperState:
    state = PaperState.model_validate(state.model_dump(mode="json"))
    if any(r.session == session for r in state.reports):
        return state  # Decision was already locked. Later inputs/policies never rewrite it.
    if state.reports and (
        session <= state.reports[-1].session or cutoff <= state.reports[-1].knowledge_cutoff
    ):
        raise ValueError("Forward processing requires strictly increasing session/cutoff")
    if any(event.recorded_at > cutoff for event in state.events):
        raise ValueError("Future paper events require an earlier persisted stream prefix")
    if cutoff.astimezone(ZoneInfo("Asia/Kolkata")).date() < session:
        raise ValueError("Future processing session")
    if (
        reader.batch.classification != market_class(state)
        or calendar.classification != market_class(state)
        or calendar.canonical_input_id != reader.batch.input_id
    ):
        raise ValueError("Paper market/calendar classification/input mismatch")
    policy = policy or PaperPolicy()
    context = ReadContext(knowledge_cutoff=cutoff)
    sessions = reader.sessions_as_of(session, session, context).records
    if (
        len(sessions) != 1
        or sessions[0].status != "VERIFIED_TRADING_SESSION"
        or not sessions[0].session_close_at
        or sessions[0].session_close_at > cutoff
    ):
        raise ValueError("COMPLETED_EVIDENCED_EOD_SESSION_REQUIRED")
    starting_cash = reconstruct(state.ledger, session, cutoff).cash
    fills_this: list[str] = []
    exits_this: list[str] = []
    for order in pending(state):
        if order.target.session_date > session:
            continue
        if order.target.session_date < session:
            event = _event(
                order, cutoff, "EXPIRED", "TARGET_SESSION_NOT_PROCESSED_NO_RETROACTIVE_FILL"
            )
            state = state.model_copy(update={"events": (*state.events, event)})
            continue
        fill, ledger, fill_reason = _fill(state, order, reader, session, cutoff)
        event = _event(order, cutoff, "FILLED" if fill else "NO_FILL", fill_reason, fill)
        state = state.model_copy(
            update={
                "ledger": ledger,
                "events": (*state.events, event),
                "fills": (*state.fills, fill) if fill else state.fills,
            }
        )
        if fill:
            fills_this.append(fill.fill_id)
            if order.side == "SELL":
                exits_this.append(fill.fill_id)
    considered = []
    skipped: list[dict[str, str]] = []
    intents: list[tuple[ManualPaperOrder, Any, Any, str]] = [
        (r, None, None, "MANUAL_PAPER_ORDER") for r in sorted(manual, key=lambda r: r.request_id)
    ]
    if len({r.request_id for r in manual}) != len(manual):
        raise ValueError("Duplicate manual request identity")
    evidence = history or DecisionHistory()
    latest_signals: dict[str, Any] = {}
    for signal in evidence.signals:
        if signal.session_date > session or signal.knowledge_cutoff > cutoff:
            continue
        if signal.horizon != policy.controlling_horizon:
            continue
        previous_signal = latest_signals.get(signal.security_id)
        if (
            previous_signal
            and previous_signal.knowledge_cutoff == signal.knowledge_cutoff
            and previous_signal.signal_snapshot_id != signal.signal_snapshot_id
        ):
            raise ValueError("AMBIGUOUS_SIGNAL_AT_CUTOFF")
        if previous_signal is None or previous_signal.knowledge_cutoff < signal.knowledge_cutoff:
            latest_signals[signal.security_id] = signal
    for signal in sorted(
        latest_signals.values(),
        key=lambda s: (s.opportunity_rank is None, s.opportunity_rank or 0, s.security_id),
    ):
        considered.append(signal.signal_snapshot_id)
        reason: str | None = None
        explanation = next(
            (
                e
                for e in evidence.explanations
                if e.signal_snapshot_id == signal.signal_snapshot_id
                and e.knowledge_cutoff <= cutoff
            ),
            None,
        )
        if not policy.signal_orders_enabled:
            reason = "PAPER_POLICY_DISABLED"
        elif signal.classification != market_class(state):
            reason = "CLASSIFICATION_BLOCKED"
        elif signal.data_freshness != "EOD_COMPLETE" or signal.session_date != session:
            reason = "STALE_DATA"
        elif not explanation:
            reason = "EXPLANATION_UNAVAILABLE"
        elif signal.state == "ENTRY_SIGNAL" and (
            not signal.risk_snapshot_id
            or signal.risk_level not in ("LOW", "MEDIUM", "HIGH")
            or ("LOW", "MEDIUM", "HIGH").index(signal.risk_level)
            > ("LOW", "MEDIUM", "HIGH").index(policy.maximum_risk)
        ):
            reason = "RISK_POLICY_BLOCKED"
        elif signal.state not in {"ENTRY_SIGNAL", "EXIT_SIGNAL", "TAKE_PROFIT_REVIEW"}:
            reason = "NO_ORDER_FOR_STATE"
        elif signal.state == "ENTRY_SIGNAL" and (
            signal.opportunity_rank is None or signal.opportunity_rank > policy.maximum_entry_rank
        ):
            reason = "RANK_POLICY_BLOCKED"
        elif signal.state == "EXIT_SIGNAL" and not policy.exit_signal_enabled:
            reason = "EXIT_POLICY_DISABLED"
        elif signal.state == "TAKE_PROFIT_REVIEW" and not policy.take_profit_review_auto_exit:
            reason = "TAKE_PROFIT_REVIEW_REQUIRES_MANUAL_DECISION"
        if reason:
            skipped.append(
                {
                    "reference": signal.signal_snapshot_id,
                    "security_id": signal.security_id,
                    "reason": reason,
                }
            )
            continue
        current = reconstruct(state.ledger, session, cutoff)
        position = next(
            (p for p in current.positions if p.security_id == signal.security_id and p.quantity),
            None,
        )
        available = current.cash - cash_reserved(state)
        slots = policy.maximum_positions - len(
            {p.security_id for p in current.positions if p.quantity}
            | {o.security_id for o in pending(state) if o.side == "BUY"}
        )
        if signal.state == "ENTRY_SIGNAL":
            budget = (
                policy.fixed_cash_per_position
                if policy.sizing == "FIXED_CASH_PER_POSITION"
                else available / max(slots, 1)
            )
            if budget <= 0:
                skipped.append(
                    {
                        "reference": signal.signal_snapshot_id,
                        "security_id": signal.security_id,
                        "reason": "INSUFFICIENT_CASH",
                    }
                )
                continue
            request = ManualPaperOrder(
                request_id=signal.signal_snapshot_id,
                security_id=signal.security_id,
                symbol=signal.symbol or signal.security_id,
                side="BUY",
                maximum_cash=budget,
                reason="VERSIONED_ENTRY_SIGNAL_PAPER_POLICY",
            )
        else:
            expected = position_context(
                state, signal.security_id, signal.horizon, signal.knowledge_cutoff
            )
            if expected and signal.position_evidence:
                expected = expected.model_copy(
                    update={
                        "profit_review_requested": signal.position_evidence.profit_review_requested
                    }
                )
            if not position or not expected or signal.position_evidence != expected:
                skipped.append(
                    {
                        "reference": signal.signal_snapshot_id,
                        "security_id": signal.security_id,
                        "reason": "POSITION_CONTEXT_MISMATCH",
                    }
                )
                continue
            request = ManualPaperOrder(
                request_id=signal.signal_snapshot_id,
                security_id=signal.security_id,
                symbol=signal.symbol or signal.security_id,
                side="SELL",
                quantity=int(position.quantity),
                reason="VERSIONED_POSITION_EXIT_PAPER_POLICY",
            )
        intents.append((request, signal, explanation, "SIGNAL_POLICY_PAPER_ORDER"))
    created = []
    for request, signal, explanation, origin in intents:
        reason = None
        current = reconstruct(state.ledger, session, cutoff)
        held = {p.security_id: p.quantity for p in current.positions if p.quantity}
        pending_orders = pending(state)
        prior_requests = {o.request_id for o in state.orders}
        if request.request_id in prior_requests:
            reason = "REQUEST_ALREADY_RECORDED"
        elif request.side == "BUY" and request.security_id in held:
            reason = "ALREADY_HELD"
        elif any(o.security_id == request.security_id for o in pending_orders):
            reason = "ALREADY_PENDING"
        elif request.side == "SELL" and (request.quantity or 0) > held.get(
            request.security_id, Fraction(0)
        ):
            reason = "NO_SHORT_SELLING"
        elif (
            request.side == "BUY"
            and len(set(held) | {o.security_id for o in pending_orders if o.side == "BUY"})
            >= policy.maximum_positions
        ):
            reason = "MAX_POSITIONS"
        elif request.side == "BUY" and (request.maximum_cash or 0) > current.cash - cash_reserved(
            state
        ):
            reason = "INSUFFICIENT_CASH"
        views = reader.prices_as_of(session, session, context).records
        if (
            not reason
            and request.side == "BUY"
            and not any(
                v.observation.security_id == request.security_id and valid_price(v) for v in views
            )
        ):
            reason = "UNAVAILABLE_PRICE"
        try:
            target = next_open(calendar, session, cutoff)
        except ValueError as error:
            reason = reason or str(error)
            target = None
        if reason:
            skipped.append(
                {
                    "reference": request.request_id,
                    "security_id": request.security_id,
                    "reason": reason,
                }
            )
            continue
        order = seal(
            PaperOrder,
            "order_id",
            account_id=state.ledger.portfolio.portfolio_id,
            request_id=request.request_id,
            security_id=request.security_id,
            symbol=request.symbol,
            side=request.side,
            decision_session=session,
            decision_at=cutoff,
            target=target,
            calendar_id=calendar.calendar_id,
            canonical_input_id=reader.batch.input_id,
            policy=policy,
            intent_source=origin,
            quantity=request.quantity,
            reserved_cash=request.maximum_cash or Fraction(0),
            signal=signal,
            explanation=explanation,
            reason=request.reason,
            classification=state.classification,
        )
        state = state.model_copy(
            update={
                "orders": (*state.orders, order),
                "events": (
                    *state.events,
                    _event(order, cutoff, "PENDING", "LOCKED_FUTURE_SIMULATED_INTENT"),
                ),
            }
        )
        created.append(order.order_id)
    state = state.model_copy(
        update={
            "ledger": Ledger(
                portfolio=state.ledger.portfolio,
                transactions=tuple(
                    sorted(
                        state.ledger.transactions,
                        key=lambda t: (t.recorded_at, t.effective_at, t.transaction_id),
                    )
                ),
            )
        }
    )
    valuation = value(
        state.ledger,
        reader,
        session,
        cutoff,
        evidence,
        state.reports[-1].valuation if state.reports else None,
    )
    reserve = cash_reserved(state)
    report = seal(
        PaperReport,
        "report_id",
        session=session,
        knowledge_cutoff=cutoff,
        policy_id=policy.policy_id,
        policy=policy,
        valuation=valuation,
        starting_cash=starting_cash,
        ending_cash=valuation.ledger_state.cash,
        available_cash=valuation.ledger_state.cash - reserve,
        reserved_cash=reserve,
        orders_created=tuple(created),
        fills=tuple(fills_this),
        exits=tuple(exits_this),
        signals_considered=tuple(considered),
        skipped=tuple(skipped),
        classification=state.classification,
        disclaimer=paper_disclaimer(state.classification),
        production_claims_permitted=False,
    )
    return PaperState.model_validate(
        {**state.model_dump(mode="python"), "reports": (*state.reports, report)}
    )


def position_context(
    state: PaperState, security: str, horizon: Any, cutoff: datetime
) -> PositionEvidence | None:
    """Existing P13 accepts explicitly synthetic TEST_ONLY context only; never upgrade it."""
    if state.classification != "TEST_ONLY_PAPER":
        return None
    transactions = {
        t.transaction_id: t for t in state.ledger.transactions if t.recorded_at <= cutoff
    }
    orders = {o.order_id: o for o in state.orders}
    fills = [
        f
        for f in state.fills
        if orders[f.order_id].security_id == security and f.transaction_id in transactions
    ]
    entries = [f for f in fills if orders[f.order_id].side == "BUY"]
    if not entries:
        return None
    entry = entries[-1]
    after = [f for f in fills if f.simulated_at >= entry.simulated_at]
    exits = [f for f in after if orders[f.order_id].side == "SELL"]
    quantity = sum((f.quantity * (1 if orders[f.order_id].side == "BUY" else -1) for f in after), 0)
    last = after[-1]
    return PositionEvidence(
        context_id=digest((state.ledger.portfolio.portfolio_id, entry.fill_id, horizon)),
        security_id=security,
        horizon=horizon,
        entry_at=entry.simulated_at,
        available_at=transactions[last.transaction_id].recorded_at,
        exit_at=exits[-1].simulated_at if quantity == 0 and exits else None,
        evidence_reference="TEST_ONLY_PAPER_FILLED:" + last.fill_id,
    )
