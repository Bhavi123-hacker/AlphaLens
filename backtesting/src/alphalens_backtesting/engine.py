"""Exact cash/inventory event replay; OOS scores alone decide experimental selection."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction
from math import ceil
from typing import Any

from alphalens_backtesting.contracts import VERSION, BacktestDefinition, CalendarDay
from alphalens_backtesting.evidence import ExecutionEvidence, date_end
from alphalens_backtesting.money import rational, text_money
from alphalens_data.canonical.models import revision_key
from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import OOSPrediction, digest, disclaimer
from alphalens_evaluation.models import versions
from alphalens_evaluation.storage import OOSDataset
from alphalens_training.contracts import boundary


def score(row: OOSPrediction) -> float:
    return row.probability if row.probability is not None else row.prediction


def select(
    rows: list[OOSPrediction], definition: BacktestDefinition, slots: int
) -> list[OOSPrediction]:
    if definition.baseline == "SEEDED_RANDOM_CONTROL":
        ordered = sorted(
            rows,
            key=lambda r: digest(
                [definition.random_seed, r.session_date.isoformat(), r.security_id]
            ),
        )
    else:
        ordered = sorted(rows, key=lambda r: (-score(r), r.security_id))
    if definition.baseline == "EQUAL_WEIGHT_ELIGIBLE_COHORT":
        if len(ordered) > slots:
            return []  # Explicit capacity failure; do not sample a supposed whole universe.
        return ordered
    if definition.selection_rule == "TOP_K":
        ordered = ordered[: definition.top_k]
    elif definition.selection_rule == "TOP_PERCENTILE":
        ordered = ordered[: ceil(len(ordered) * Fraction(definition.top_percentile))]
    else:
        ordered = [
            r
            for r in ordered
            if Fraction(str(score(r))) >= Fraction(definition.prediction_threshold)
        ]
    return ordered[:slots]


@dataclass
class Position:
    row: OOSPrediction
    quantity: Fraction
    entry_nominal: Fraction
    entry_effective: Fraction
    entry_fee: Fraction
    budget: Fraction
    exit_day: CalendarDay
    ledger: dict[str, Any]
    unresolved: bool = False


@dataclass(frozen=True)
class BacktestResult:
    manifest: dict[str, Any]
    summary: dict[str, Any]
    equity: list[dict[str, Any]]
    drawdown: list[dict[str, Any]]
    trades: list[dict[str, Any]]
    positions: list[dict[str, Any]]
    session_pnl: list[dict[str, Any]]
    decisions: list[dict[str, Any]]


def run(
    oos: OOSDataset, evidence: ExecutionEvidence, definition: BacktestDefinition
) -> BacktestResult:
    definition = BacktestDefinition.model_validate(definition.model_dump())
    evidence.verify(oos, definition)
    if (
        definition.start_session < evidence.calendar.days[0].session_date
        or definition.end_session > evidence.calendar.days[-1].session_date
    ):
        raise DataContractError("P10_PERIOD_OUTSIDE_EVIDENCED_CALENDAR")
    calendar_days = {d.session_date: d for d in evidence.calendar.days}
    cursor = definition.start_session
    while cursor <= definition.end_session:
        if cursor not in calendar_days or calendar_days[cursor].status == "UNKNOWN_SESSION_STATUS":
            raise DataContractError("P10_PERIOD_CALENDAR_INCOMPLETE")
        cursor += timedelta(days=1)
    identity = dict(
        version=VERSION,
        definition=definition.model_dump(mode="json"),
        environment=versions(),
        monetary_arithmetic="EXACT_RATIONAL",
        display_arithmetic="DECIMAL_76_HALF_EVEN_WITH_RATIONAL_STATE",
        metric_boundary="FLOAT64_FROM_EXACT_STATE",
        prediction_role="FOLD_TEST_ONLY_NO_TARGET_BASED_SELECTION",
    )
    backtest_id = digest(identity)
    capital = Fraction(definition.initial_capital)
    cash, realized, fees, slippage = capital, Fraction(0), Fraction(0), Fraction(0)
    inventory: dict[str, Position] = {}
    pending: dict[
        Any, list[tuple[OOSPrediction, CalendarDay, CalendarDay, Fraction, dict[str, Any]]]
    ] = defaultdict(list)
    by_session: dict[Any, list[OOSPrediction]] = defaultdict(list)
    for row in oos.predictions:
        if (
            row.model_family == definition.model_family
            and definition.start_session <= row.session_date <= definition.end_session
        ):
            by_session[row.session_date].append(row)
    if not by_session:
        raise DataContractError("INSUFFICIENT_OOS_MODEL_PREDICTIONS_IN_PERIOD")
    equity: list[dict[str, Any]] = []
    drawdown: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    pnl: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    previous_value: Fraction | None = capital
    peak: Fraction = capital
    peak_known = True
    benchmark_quantity: Fraction | None = None
    benchmark_first = True
    fee_rate, slip = definition.costs.fee_rate, definition.costs.slip_rate
    for day in evidence.calendar.days:
        session = day.session_date
        if not definition.start_session <= session <= definition.end_session:
            continue
        if day.status != "VERIFIED_TRADING_SESSION":
            if session in by_session:
                raise DataContractError("P10_PREDICTION_ON_UNVERIFIED_SESSION")
            continue
        # Pending allocations were fixed at the preceding decision, before seeing this open.
        for row, entry_day, exit_day, budget, decision in pending.pop(session, []):
            view = evidence.price(row.security_id, session)
            entry_bound = entry_day.open_at or boundary(session)
            reason = None
            if row.prediction_available_at >= boundary(session):
                reason = "NO_FILL_PREDICTION_NOT_BEFORE_ENTRY_DATE"
            elif not evidence.confirmed(entry_day):
                reason = "NO_FILL_SESSION_NOT_CONFIRMED"
            elif view is None:
                reason = "NO_FILL_MISSING_OR_REJECTED_OPEN"
            elif not evidence.member_at_open(row.security_id, session, entry_bound):
                reason = "NO_FILL_KNOWN_UNIVERSE_INELIGIBILITY"
            elif evidence.economic_actions(row.security_id, session, session, entry_bound):
                reason = "NO_FILL_KNOWN_UNADJUSTED_ECONOMIC_ACTION"
            elif len(inventory) >= definition.maximum_positions or budget > cash or budget <= 0:
                reason = "NO_FILL_CAPITAL_OR_CAPACITY"
            if reason:
                decision["status"] = reason
                continue
            if view is None or view.observation.values is None:
                raise DataContractError("P10_OPEN_EVIDENCE_REQUIRED")
            nominal = Fraction(view.observation.values.open)
            effective = nominal * (1 + slip)
            quantity = budget / (effective * (1 + fee_rate))
            entry_fee = quantity * effective * fee_rate
            debit = quantity * effective + entry_fee
            cash -= debit
            realized -= entry_fee
            fees += entry_fee
            slippage += quantity * (effective - nominal)
            decision["status"] = "FILLED_HYPOTHETICAL"
            audit = evidence.audit(row, oos, view)
            ledger = dict(
                trade_id=digest([backtest_id, decision["decision_id"], row.prediction_id]),
                backtest_id=backtest_id,
                selection_decision_id=decision["decision_id"],
                security_id=row.security_id,
                prediction_id=row.prediction_id,
                model_run_id=row.model_run_id,
                fold_id=row.fold_id,
                decision_session=row.session_date.isoformat(),
                prediction_available_at=row.prediction_available_at.isoformat(),
                entry_session=session.isoformat(),
                entry_time=entry_day.open_at.isoformat() if entry_day.open_at else None,
                entry_time_policy=entry_day.open_clock_policy,
                entry_price=text_money(nominal),
                entry_effective_price=text_money(effective),
                entry_price_available_at=view.observation.provenance.available_at.isoformat()
                if view.observation.provenance.available_at
                else None,
                quantity=text_money(quantity),
                quantity_rational=rational(quantity),
                capital_allocation=text_money(debit),
                capital_allocation_rational=rational(debit),
                entry_costs=text_money(entry_fee),
                exit_costs=None,
                total_costs=text_money(entry_fee),
                slippage_cost=text_money(quantity * (effective - nominal)),
                planned_exit=exit_day.session_date.isoformat(),
                exit_session=None,
                exit_time=None,
                exit_price=None,
                exit_effective_price=None,
                gross_return=None,
                net_return=None,
                net_pnl=None,
                net_pnl_rational=None,
                holding_sessions=None,
                exit_reason="OPEN_POSITION",
                data_quality_state=str(view.quality),
                corporate_action_state="COVERAGE_NOT_ESTABLISHED",
                classification=definition.data_classification.value,
                audit_chain=audit,
                entry_revision_key=revision_key(view.observation),
                exit_revision_key=None,
                cost_scenario=definition.costs.name,
                horizon=definition.horizon,
            )
            position = Position(
                row, quantity, nominal, effective, entry_fee, debit, exit_day, ledger
            )
            inventory[row.security_id] = position
            trades.append(ledger)
        market = Fraction(0)
        unrealized = Fraction(0)
        complete = True
        for security, position in sorted(tuple(inventory.items())):
            view = evidence.price(security, session)
            if not evidence.confirmed(day):
                position.unresolved = True
                position.ledger["exit_reason"] = "UNRESOLVED_HOLDING_CALENDAR_CONFLICT"
                position.ledger["audit_chain"]["calendar_conflict_session"] = session.isoformat()
            actions = evidence.economic_actions(
                security, position.row.session_date, session, date_end(session)
            )
            if actions:
                position.unresolved = True
                position.ledger["corporate_action_state"] = "UNRESOLVED_KNOWN_ECONOMIC_ACTION"
                position.ledger["audit_chain"]["known_economic_action_keys"] = list(actions)
            valid = view is not None and not position.unresolved and evidence.confirmed(day)
            if session == position.exit_day.session_date:
                if (
                    valid
                    and view is not None
                    and view.observation.values is not None
                    and evidence.confirmed(day)
                ):
                    nominal_exit = Fraction(view.observation.values.close)
                    effective_exit = nominal_exit * (1 - slip)
                    exit_fee = position.quantity * effective_exit * fee_rate
                    proceeds = position.quantity * effective_exit - exit_fee
                    cash += proceeds
                    trade_pnl = proceeds - position.budget
                    realized += (
                        position.quantity * (effective_exit - position.entry_effective) - exit_fee
                    )
                    fees += exit_fee
                    exit_slip = position.quantity * (nominal_exit - effective_exit)
                    slippage += exit_slip
                    position.ledger.update(
                        exit_session=session.isoformat(),
                        exit_time=view.observation.session_close_at.isoformat()
                        if view.observation.session_close_at
                        else None,
                        exit_price=text_money(nominal_exit),
                        exit_effective_price=text_money(effective_exit),
                        exit_costs=text_money(exit_fee),
                        total_costs=text_money(position.entry_fee + exit_fee),
                        slippage_cost=text_money(
                            position.quantity * (position.entry_effective - position.entry_nominal)
                            + exit_slip
                        ),
                        gross_return=text_money(nominal_exit / position.entry_nominal - 1),
                        net_return=text_money(trade_pnl / position.budget),
                        net_pnl=text_money(trade_pnl),
                        net_pnl_rational=rational(trade_pnl),
                        exit_reason="HORIZON_CLOSE",
                        holding_sessions=definition.horizon,
                        exit_revision_key=revision_key(view.observation),
                    )
                    position.ledger["audit_chain"]["exit_evidence"] = evidence.audit(
                        position.row, oos, view
                    )
                    del inventory[security]
                    continue
                position.unresolved = True
                position.ledger["exit_reason"] = "UNRESOLVED_HORIZON_EXIT_NO_RECOVERY_ASSUMPTION"
            if not valid or position.unresolved or view is None or view.observation.values is None:
                complete = False
                value = None
                position.ledger["data_quality_state"] = "UNRESOLVED_PRICE_OR_ECONOMIC_OUTCOME"
            else:
                value = position.quantity * Fraction(view.observation.values.close)
                market += value
                unrealized += value - position.quantity * position.entry_effective
            snapshots.append(
                dict(
                    session_date=session.isoformat(),
                    trade_id=position.ledger["trade_id"],
                    security_id=security,
                    fold_id=position.row.fold_id,
                    quantity=text_money(position.quantity),
                    quantity_rational=rational(position.quantity),
                    market_value=text_money(value),
                    state="MARKED" if value is not None else "UNRESOLVED",
                    planned_exit=position.exit_day.session_date.isoformat(),
                    classification=definition.data_classification.value,
                )
            )
        value = cash + market if complete else None
        if cash < 0 or len(inventory) > definition.maximum_positions:
            raise DataContractError("P10_CAPITAL_OR_POSITION_INVARIANT")
        if value is not None and value - capital != realized + unrealized:
            raise DataContractError("P10_PNL_RECONCILIATION_FAILED")
        benchmark_value = None
        if definition.benchmark:
            benchmark_view = (
                evidence.price(definition.benchmark.security_id, session)
                if evidence.confirmed(day)
                else None
            )
            if benchmark_first and session > definition.start_session:
                benchmark_first = False
                if benchmark_view and benchmark_view.observation.values:
                    benchmark_quantity = Fraction(1) / Fraction(
                        benchmark_view.observation.values.open
                    )
            if (
                benchmark_quantity is not None
                and benchmark_view
                and benchmark_view.observation.values
            ) and not evidence.economic_actions(
                definition.benchmark.security_id,
                definition.start_session,
                session,
                date_end(session),
            ):
                benchmark_value = benchmark_quantity * Fraction(
                    benchmark_view.observation.values.close
                )
        if value is not None:
            peak = max(peak, value)
        else:
            peak_known = False
        draw = value / peak - 1 if value is not None and peak_known else None
        equity.append(
            dict(
                session_date=session.isoformat(),
                portfolio_value=text_money(value),
                cash=text_money(cash),
                market_value=text_money(market) if complete else None,
                normalized_wealth=text_money(value / capital) if value is not None else None,
                value_rational=rational(value) if value is not None else None,
                state="MARKED" if complete else "UNRESOLVED",
                benchmark_wealth=text_money(benchmark_value),
            )
        )
        drawdown.append(
            dict(
                session_date=session.isoformat(),
                drawdown=float(draw) if draw is not None else None,
                status="UNRESOLVED"
                if not complete
                else "AVAILABLE"
                if peak_known
                else "UNRESOLVED_VALUATION_HISTORY",
            )
        )
        pnl.append(
            dict(
                session_date=session.isoformat(),
                portfolio_value=text_money(value),
                cash=text_money(cash),
                market_value=text_money(market) if complete else None,
                realized_pnl=text_money(realized),
                unrealized_pnl=text_money(unrealized) if complete else None,
                total_pnl=text_money(value - capital) if value is not None else None,
                session_pnl=text_money(value - previous_value)
                if value is not None and previous_value is not None
                else None,
                cumulative_fees=text_money(fees),
                cumulative_slippage=text_money(slippage),
                gross_pnl=text_money(value - capital + fees + slippage)
                if value is not None
                else None,
                open_positions=len(inventory),
                occupied_fraction=len(inventory) / definition.maximum_positions,
                cash_utilization=float(market / value) if value is not None and value > 0 else None,
                state="MARKED" if complete else "UNRESOLVED",
                classification=definition.data_classification.value,
            )
        )
        previous_value = value
        candidates = by_session.get(session, [])
        if not candidates:
            continue
        held = set(inventory) | {
            r.security_id for requests in pending.values() for r, _, _, _, _ in requests
        }
        free = definition.maximum_positions - len(held)
        selectable = [r for r in candidates if r.security_id not in held]
        chosen = select(selectable, definition, free)
        reserved = sum(
            (budget for requests in pending.values() for _, _, _, budget, _ in requests),
            Fraction(0),
        )
        denominator = len(chosen) if definition.baseline == "EQUAL_WEIGHT_ELIGIBLE_COHORT" else free
        budget = (cash - reserved) / denominator if denominator > 0 else Fraction(0)
        chosen_ids = {r.prediction_id for r in chosen}
        for row in sorted(candidates, key=lambda r: r.security_id):
            decision = dict(
                decision_id=digest([backtest_id, row.prediction_id]),
                security_id=row.security_id,
                prediction_id=row.prediction_id,
                model_run_id=row.model_run_id,
                session_date=session.isoformat(),
                prediction_available_at=row.prediction_available_at.isoformat(),
                status="NOT_SELECTED_FIXED_POLICY",
                proposed_budget=None,
                planned_entry=None,
                planned_exit=None,
                classification=definition.data_classification.value,
            )
            decisions.append(decision)
            if row.security_id in held:
                decision["status"] = "ALREADY_HELD_OR_RESERVED"
            elif definition.baseline == "EQUAL_WEIGHT_ELIGIBLE_COHORT" and len(selectable) > free:
                decision["status"] = "BASELINE_CAPACITY_INSUFFICIENT_FOR_ENTIRE_COHORT"
            elif row.prediction_id in chosen_ids:
                entry, planned_exit, reason = evidence.plan(row, definition.horizon)
                if reason or entry is None or planned_exit is None:
                    decision["status"] = reason or "NO_FILL_UNKNOWN_CALENDAR"
                elif row.prediction_available_at >= boundary(entry.session_date):
                    decision["status"] = "NO_FILL_PREDICTION_NOT_BEFORE_ENTRY_DATE"
                else:
                    decision.update(
                        status="PLANNED",
                        proposed_budget=text_money(budget),
                        planned_entry=entry.session_date.isoformat(),
                        planned_exit=planned_exit.session_date.isoformat(),
                    )
                    pending[entry.session_date].append((row, entry, planned_exit, budget, decision))
    for position in inventory.values():
        if position.ledger["exit_reason"] == "OPEN_POSITION":
            position.ledger["exit_reason"] = "OPEN_POSITION_END_OF_PERIOD"
    for requests in pending.values():
        for _, _, _, _, decision in requests:
            decision["status"] = "NO_FILL_ENTRY_OUTSIDE_BACKTEST_PERIOD"
    from alphalens_backtesting.metrics import summarize

    if not equity:
        raise DataContractError("P10_NO_EVIDENCED_VALUATION_SESSIONS")
    summary = summarize(definition, equity, drawdown, trades, pnl, decisions)
    common = dict(
        backtest_id=backtest_id,
        version=VERSION,
        classification=definition.data_classification.value,
        disclaimer=disclaimer(definition.data_classification),
        production_claims_permitted=False,
    )
    summary.update(common)
    manifest = dict(
        **common,
        identity=identity,
        price_basis=definition.price_basis,
        corporate_action_coverage="NOT_ESTABLISHED",
        selection_counts=dict(Counter(d["status"] for d in decisions)),
        prediction_count=sum(len(v) for v in by_session.values()),
        limitations=[
            "Hypothetical fractional quantities; no exchange orders or recommendations",
            "Cost/slippage/risk-free/session-count values are explicit assumptions",
            "Daily open price is evidenced ex post; calendar clock is a declared convention",
            "Known unadjusted economic actions and unknown recovery remain unresolved",
            "No real historical NSE universe or production-quality economics established",
            "All final user-facing risk/ranking/signals/portfolio work remains deferred",
        ],
    )
    return BacktestResult(manifest, summary, equity, drawdown, trades, snapshots, pnl, decisions)
