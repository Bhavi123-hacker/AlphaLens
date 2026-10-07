"""Forward-only TEST_ONLY paper decisions, independent cash/fill/leakage oracles."""

import json
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from scripts.build_p6_test_fixture import build_history as build_prices
from scripts.build_p15_test_fixture import clock
from scripts.build_p16_test_fixture import account, calendar, request
from test_p13_signals import demo, evidence, sealed

from alphalens_backtesting.contracts import scenarios
from alphalens_data.canonical.models import PriceRevision, ReadContext, revision_key
from alphalens_data.canonical.services import CanonicalReader
from alphalens_decision.explanations import explain
from alphalens_decision.ranking_contracts import RankSnapshot
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_decision.signals import evaluate
from alphalens_portfolio.paper import (
    cancel,
    cash_reserved,
    order_states,
    position_context,
    process_session,
)
from alphalens_portfolio.paper_contracts import PaperPolicy, PaperState
from alphalens_portfolio.paper_performance import chart_series, performance
from alphalens_portfolio.paper_storage import load, save
from alphalens_portfolio.valuation import DecisionHistory


@pytest.fixture(scope="module")
def reader(tmp_path_factory: pytest.TempPathFactory) -> CanonicalReader:
    return CanonicalReader(
        build_prices(tmp_path_factory.mktemp("p16"), length=20, revision=(4, 19, "999"))[0]
    )


def process(state: PaperState, reader: CanonicalReader, day: int, **kwargs: Any) -> PaperState:
    return process_session(
        state, reader, calendar(reader), date(2024, 1, day), clock(day), **kwargs
    )


def intent(reader: CanonicalReader, **kwargs: Any) -> PaperState:
    return process(account(), reader, 1, manual=(request(**kwargs),))


def signals(
    reader: CanonicalReader,
    day: int,
    state: PaperState | None = None,
    probability: float = 0.85,
    severity: float = 0.1,
    horizon: Any = 5,
    review: bool = False,
) -> DecisionHistory:
    ranking, risk = evidence(day - 1, horizon, probability=probability, severity=severity)
    refs = dict(
        canonical_input_id=reader.batch.input_id,
        canonical_dataset_id=reader.build(
            date.min, date(2024, 1, day), ReadContext(knowledge_cutoff=clock(day))
        ).dataset_id,
    )
    risk = sealed(
        RiskSnapshot,
        "risk_snapshot_id",
        **{
            **risk.model_dump(exclude={"risk_snapshot_id"}),
            **refs,
            "security_id": "TEST:ALPHA",
            "symbol": "TEST_ALPHA",
        },
    )
    candidate = {
        **ranking.ranked[0].model_dump(),
        "security_id": "TEST:ALPHA",
        "symbol": "TEST_ALPHA",
        "risk_snapshot_id": risk.risk_snapshot_id,
        "canonical_dataset_id": refs["canonical_dataset_id"],
    }
    ranking = sealed(
        RankSnapshot,
        "rank_snapshot_id",
        **{
            **ranking.model_dump(exclude={"rank_snapshot_id"}),
            **refs,
            "ranked": (candidate,),
            "risk_snapshot_ids": (risk.risk_snapshot_id,),
        },
    )
    context = (
        position_context(state, "TEST:ALPHA", horizon, risk.knowledge_cutoff) if state else None
    )
    if context and review:
        context = context.model_copy(update={"profit_review_requested": True})
    signal = evaluate(
        ranking,
        "TEST:ALPHA",
        (risk,),
        demo(horizon, confirmation_observations=1),
        positions=(context,) if context else (),
    )
    explanation = explain(signal, ranking, (risk,))
    return DecisionHistory(
        risks=(risk,), rankings=(ranking,), signals=(signal,), explanations=(explanation,)
    )


def test_manual_default_intent_is_not_signal_or_fill(reader: CanonicalReader) -> None:
    state = intent(reader)
    assert (
        len(state.orders) == 1
        and state.fills == ()
        and state.reports[0].valuation.number_of_holdings == 0
    )
    assert cash_reserved(state) == 1000 and state.reports[0].available_cash == 9000
    assert order_states(state) == {state.orders[0].order_id: "PENDING"}
    assert state.orders[0].intent_source == "MANUAL_PAPER_ORDER" and state.orders[0].signal is None


def test_entry_only_evidenced_next_open_not_decision_close(reader: CanonicalReader) -> None:
    state = intent(reader)
    filled = process(state, reader, 2)
    assert len(filled.fills) == 1 and filled.fills[0].simulated_at > state.orders[0].decision_at
    bar = next(
        v.observation
        for v in reader.prices_as_of(
            date(2024, 1, 2), date(2024, 1, 2), ReadContext(knowledge_cutoff=clock(2))
        ).records
        if v.observation.security_id == "TEST:ALPHA"
    )
    assert bar.values is not None
    fill = filled.fills[0]
    assert fill.observed_open == Fraction(bar.values.open) == fill.simulated_price
    assert fill.quantity == int(Fraction(1000) / Fraction(bar.values.open))
    assert filled.reports[-1].ending_cash == 10000 - fill.quantity * fill.simulated_price
    assert filled.reports[-1].valuation.positions[0].accounting.quantity == fill.quantity
    assert cash_reserved(filled) == 0 and fill.execution == "SIMULATED_FILL_NOT_REAL_EXECUTION"


def test_exit_after_decision_then_exited_context(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    quantity = state.fills[0].quantity
    pending = process(state, reader, 3, manual=(request("exit", side="SELL", quantity=quantity),))
    pending_context = position_context(pending, "TEST:ALPHA", 5, clock(3))
    assert len(pending.fills) == 1 and pending_context and pending_context.exit_at is None
    exited = process(pending, reader, 4)
    assert len(exited.fills) == 2 and exited.fills[-1].simulated_at > pending.orders[-1].decision_at
    assert exited.reports[-1].valuation.positions[0].accounting.quantity == 0
    context = position_context(exited, "TEST:ALPHA", 5, clock(4))
    assert context and context.exit_at == exited.fills[-1].simulated_at
    p = performance(exited)
    assert p.closed_position_cycles == 1 and p.wins + p.losses + p.breakeven_cycles == 1
    assert p.realized_pnl == exited.reports[-1].valuation.realized_pnl


def test_repeated_session_no_double_fill_fee_order_transaction(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    repeated = process(
        state, reader, 2, manual=(request("duplicate"),), policy=PaperPolicy(revision="later")
    )
    assert repeated == state and repeated.state_id == state.state_id
    assert len(repeated.ledger.transactions) == 2 and len(repeated.fills) == 1


def test_cash_reservations_no_overspending(reader: CanonicalReader) -> None:
    state = process(
        account(),
        reader,
        1,
        manual=(request("a", budget="9000"), request("b", security="TEST:BETA", budget="2000")),
    )
    assert len(state.orders) == 1 and cash_reserved(state) == 9000
    assert state.reports[0].skipped[0]["reason"] == "INSUFFICIENT_CASH"
    filled = process(state, reader, 2)
    assert filled.reports[-1].ending_cash >= 0


def test_no_pyramiding_or_duplicate_pending(reader: CanonicalReader) -> None:
    state = process(account(), reader, 1, manual=(request("a"), request("b")))
    assert len(state.orders) == 1 and state.reports[-1].skipped[0]["reason"] == "ALREADY_PENDING"
    filled = process(state, reader, 2, manual=(request("c"),))
    assert len(filled.orders) == 1 and filled.reports[-1].skipped[0]["reason"] == "ALREADY_HELD"


def test_max_positions_and_oversell_are_explicit_skips(reader: CanonicalReader) -> None:
    state = process(
        account(),
        reader,
        1,
        policy=PaperPolicy(maximum_positions=1),
        manual=(request("a"), request("b", security="TEST:BETA")),
    )
    assert state.reports[-1].skipped[0]["reason"] == "MAX_POSITIONS"
    state = process(state, reader, 2, manual=(request("oversell", side="SELL", quantity=1000),))
    assert state.reports[-1].skipped[0]["reason"] == "NO_SHORT_SELLING"


def test_budget_caps_manual_quantity_at_future_open(reader: CanonicalReader) -> None:
    state = process(intent(reader, quantity=1000), reader, 2)
    assert state.fills == () and order_states(state)[state.orders[0].order_id] == "NO_FILL"
    assert state.reports[-1].ending_cash == 10000 and cash_reserved(state) == 0


@pytest.mark.parametrize("costs", scenarios())
def test_exact_cost_slippage_scenarios_use_p15(reader: CanonicalReader, costs: Any) -> None:
    state = process(account(), reader, 1, policy=PaperPolicy(costs=costs), manual=(request(),))
    state = process(state, reader, 2, policy=PaperPolicy(revision="new", costs=scenarios()[0]))
    fill = state.fills[0]
    assert fill.simulated_price == fill.observed_open * (1 + costs.slip_rate)
    assert fill.fees == fill.quantity * fill.simulated_price * costs.fee_rate
    assert (
        state.reports[-1].valuation.positions[0].accounting.cost_basis
        == fill.quantity * fill.simulated_price + fill.fees
    )


def test_missing_open_no_substitution(reader: CanonicalReader) -> None:
    state = intent(reader)
    revisions = tuple(
        r
        for r in reader.batch.revisions
        if not (
            isinstance(r, PriceRevision)
            and r.session_date == date(2024, 1, 2)
            and r.security_id == "TEST:ALPHA"
        )
    )
    keys = {revision_key(r) for r in revisions}
    changed = CanonicalReader(
        reader.batch.model_copy(
            update={
                "revisions": revisions,
                "lineage": tuple(link for link in reader.batch.lineage if link.record_key in keys),
            }
        )
    )
    result = process(state, changed, 2)
    assert result.fills == () and order_states(result)[state.orders[0].order_id] == "NO_FILL"
    assert result.orders == state.orders


def test_cancel_and_expiry_release_reserved_cash(reader: CanonicalReader) -> None:
    state = intent(reader)
    cancelled = cancel(state, state.orders[0].order_id, clock(1, 13), "MANUAL_CANCELLATION")
    assert (
        cash_reserved(cancelled) == 0
        and order_states(cancelled)[state.orders[0].order_id] == "CANCELLED"
    )
    expired = process(state, reader, 3)
    assert expired.fills == () and order_states(expired)[state.orders[0].order_id] == "EXPIRED"
    assert cash_reserved(expired) == 0


def test_not_completed_session_cannot_process_or_fill(reader: CanonicalReader) -> None:
    state = intent(reader)
    with pytest.raises(ValueError, match="COMPLETED"):
        process_session(state, reader, calendar(reader), date(2024, 1, 2), clock(2, 4))
    assert state.fills == ()


def test_forward_only_no_retroactive_session_or_order(reader: CanonicalReader) -> None:
    state = process(account(), reader, 2)
    with pytest.raises(ValueError, match="strictly increasing"):
        process(state, reader, 1)
    late = process_session(
        account(), reader, calendar(reader), date(2024, 1, 1), clock(2, 12), manual=(request(),)
    )
    assert (
        late.orders == ()
        and late.reports[0].skipped[0]["reason"] == "NEXT_OPEN_ALREADY_PASSED_NO_RETROACTIVE_INTENT"
    )


def test_future_price_cannot_rewrite_old_intent(reader: CanonicalReader) -> None:
    state = intent(reader)
    after = process(state, reader, 20)
    assert after.orders[0] == state.orders[0] and after.reports[0] == state.reports[0]
    assert process(after, reader, 1, policy=PaperPolicy(revision="future")) == after


def test_disabled_signal_policy_records_reason(reader: CanonicalReader) -> None:
    history = signals(reader, 1)
    state = process(account(), reader, 1, history=history)
    assert state.orders == () and state.reports[-1].signals_considered == (
        history.signals[0].signal_snapshot_id,
    )
    assert state.reports[-1].skipped[0]["reason"] == "PAPER_POLICY_DISABLED"


def test_enabled_signal_policy_full_lineage_and_hold_exit_lifecycle(
    reader: CanonicalReader,
) -> None:
    policy = PaperPolicy(signal_orders_enabled=True)
    history = signals(reader, 1)
    assert history.signals[0].state == "ENTRY_SIGNAL"
    state = process(account(), reader, 1, policy=policy, history=history)
    assert (
        state.orders[0].signal == history.signals[0]
        and state.orders[0].explanation == history.explanations[0]
    )
    state = process(state, reader, 2, policy=policy)
    hold = signals(reader, 3, state)
    assert hold.signals[0].state == "HOLD"
    exit_evidence = signals(reader, 3, state, probability=0.1)
    assert exit_evidence.signals[0].state == "EXIT_SIGNAL"
    state = process(state, reader, 3, policy=policy, history=exit_evidence)
    assert state.orders[-1].side == "SELL" and state.orders[-1].signal == exit_evidence.signals[0]
    state = process(state, reader, 4, policy=policy)
    exited = signals(reader, 5, state)
    assert exited.signals[0].state == "EXITED"


def test_review_no_auto_exit_default(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    review = signals(reader, 3, state, review=True)
    assert review.signals[0].state == "TAKE_PROFIT_REVIEW"
    result = process(
        state, reader, 3, policy=PaperPolicy(signal_orders_enabled=True), history=review
    )
    assert (
        len(result.orders) == 1
        and result.reports[-1].skipped[0]["reason"] == "TAKE_PROFIT_REVIEW_REQUIRES_MANUAL_DECISION"
    )


def test_fixed_horizon_and_future_signal_cannot_change_old_decision(
    reader: CanonicalReader,
) -> None:
    future = signals(reader, 5)
    empty = process(account(), reader, 1)
    assert process(account(), reader, 1, history=future) == empty
    other = signals(reader, 1, horizon=10)
    state = process(
        account(),
        reader,
        1,
        policy=PaperPolicy(signal_orders_enabled=True, controlling_horizon=5),
        history=other,
    )
    assert state.orders == () and state.reports[-1].signals_considered == ()


def test_checkpoint_restart_replay_same_orders_fills_pnl(
    reader: CanonicalReader, tmp_path: Path
) -> None:
    state = intent(reader)
    path = save(tmp_path, state)
    restored = load(path)
    assert restored == state and process(restored, reader, 2) == process(state, reader, 2)
    final = process(restored, reader, 2)
    assert load(save(tmp_path, final)) == final and chart_series(final)["trade_markers"]
    assert performance(final).maximum_drawdown is not None


def test_test_only_disclaimer_and_no_real_execution_path(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    assert state.classification == "TEST_ONLY_PAPER"
    assert (
        "TEST_ONLY PAPER SIMULATION" in state.reports[-1].disclaimer
        and "NOT REAL MARKET PERFORMANCE" in performance(state).disclaimer
    )
    assert performance(state).benchmark_availability == "UNAVAILABLE"
    root = Path(__file__).resolve().parents[2] / "portfolio/src"
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert all(
            f"import {name}" not in source
            for name in ("requests", "httpx", "kiteconnect", "upstox", "smartapi")
        )
    data = state.reports[-1].model_dump(mode="json")
    data["disclaimer"] = "REAL PERFORMANCE"
    from alphalens_portfolio.paper_contracts import PaperReport

    with pytest.raises(ValueError, match="disclaimer"):
        sealed(PaperReport, "report_id", **{k: v for k, v in data.items() if k != "report_id"})


def test_cli_history_and_performance_replay(
    reader: CanonicalReader,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import sys

    from alphalens_portfolio.paper_cli import main

    state = process(intent(reader), reader, 2)
    path = save(tmp_path, state)
    for command in ("orders", "positions", "performance", "history"):
        monkeypatch.setattr(sys, "argv", ["alphalens-paper", command, "--input", str(path)])
        assert main() == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == state.reports[-1].disclaimer
        assert json.loads(lines[1])


def test_rejected_next_open_creates_no_fill(tmp_path: Path) -> None:
    rejected = CanonicalReader(
        build_prices(tmp_path, length=3, overrides={(1, "TEST:ALPHA"): {"open": "-1"}})[0]
    )
    state = process(intent(rejected), rejected, 2)
    assert state.fills == () and order_states(state)[state.orders[0].order_id] == "NO_FILL"
    assert state.reports[-1].ending_cash == 10000


def test_equal_weight_sizing_uses_available_cash_free_slots(reader: CanonicalReader) -> None:
    history = signals(reader, 1)
    state = process(
        account(),
        reader,
        1,
        policy=PaperPolicy(
            signal_orders_enabled=True, sizing="EQUAL_WEIGHT_AVAILABLE_CAPITAL", maximum_positions=2
        ),
        history=history,
    )
    assert state.orders[0].reserved_cash == 5000


def test_enabled_policy_blocks_stale_missing_explanation(reader: CanonicalReader) -> None:
    history = signals(reader, 1)
    policy = PaperPolicy(signal_orders_enabled=True)
    stale = process(account(), reader, 2, policy=policy, history=history)
    assert stale.orders == () and stale.reports[0].skipped[0]["reason"] == "STALE_DATA"
    no_explanation = history.model_copy(update={"explanations": ()})
    missing = process(account(), reader, 1, policy=policy, history=no_explanation)
    assert (
        missing.orders == ()
        and missing.reports[0].skipped[0]["reason"] == "EXPLANATION_UNAVAILABLE"
    )


def test_classification_mismatch_blocks_account(reader: CanonicalReader) -> None:
    from alphalens_portfolio.contracts import Portfolio
    from alphalens_portfolio.paper import create

    real = Portfolio(
        portfolio_id="RESEARCH_PAPER",
        portfolio_name="RESEARCH PAPER",
        portfolio_type="PAPER",
        classification="RESEARCH_FIXTURE",
        created_at=clock(1, 0),
    )
    state = create(real, Fraction(10000))
    with pytest.raises(ValueError, match="classification"):
        process(state, reader, 1)


def test_optional_review_auto_exit_requires_evidenced_position(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    review = signals(reader, 3, state, review=True)
    result = process(
        state,
        reader,
        3,
        policy=PaperPolicy(signal_orders_enabled=True, take_profit_review_auto_exit=True),
        history=review,
    )
    assert len(result.orders) == 2 and result.orders[-1].side == "SELL"


def test_future_cancellation_cannot_suppress_earlier_fill(reader: CanonicalReader) -> None:
    state = intent(reader)
    future = cancel(state, state.orders[0].order_id, clock(10), "FUTURE_USER_DECISION")
    with pytest.raises(ValueError, match="Future paper events"):
        process(future, reader, 2)
    assert process(state, reader, 2).fills


def test_order_fill_identity_tamper_is_rejected(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    data = state.model_dump(mode="json")
    data["fills"][0]["simulated_price"] = "1"
    with pytest.raises(ValueError, match="fill identity"):
        PaperState.model_validate(data)


def test_signal_snapshot_horizon_not_optimistically_selected(reader: CanonicalReader) -> None:
    chosen = signals(reader, 1, horizon=5)
    other = signals(reader, 1, horizon=10, probability=0.99)
    both = DecisionHistory(
        signals=(*chosen.signals, *other.signals),
        explanations=(*chosen.explanations, *other.explanations),
    )
    state = process(
        account(),
        reader,
        1,
        policy=PaperPolicy(signal_orders_enabled=True, controlling_horizon=5),
        history=both,
    )
    assert len(state.orders) == 1 and state.orders[0].signal.horizon == 5  # type: ignore[union-attr]


def test_complete_closed_cycle_performance_reuses_p15_not_marked_wins(
    reader: CanonicalReader,
) -> None:
    state = process(intent(reader), reader, 2)
    assert (
        performance(state).closed_position_cycles
        == performance(state).wins
        == performance(state).losses
        == 0
    )
    state = process(state, reader, 3, manual=(request("partial", side="SELL", quantity=1),))
    state = process(state, reader, 4)
    assert performance(state).closed_position_cycles == 0
    assert performance(state).realized_pnl == state.reports[-1].valuation.realized_pnl


def test_high_risk_invalidation_does_not_block_configured_exit(reader: CanonicalReader) -> None:
    state = process(intent(reader), reader, 2)
    history = signals(reader, 3, state, severity=0.6)
    assert history.signals[0].state == "EXIT_SIGNAL" and history.signals[0].risk_level == "HIGH"
    state = process(
        state, reader, 3, policy=PaperPolicy(signal_orders_enabled=True), history=history
    )
    assert len(state.orders) == 2 and state.orders[-1].side == "SELL"


def test_fill_preserves_symbol_known_at_open_without_changing_intent(
    reader: CanonicalReader, tmp_path: Path
) -> None:
    from test_p9_future_knowledge import append_reference

    from alphalens_data.canonical.models import IdentityRevision

    state = intent(reader)
    old = next(
        r
        for r in reader.batch.revisions
        if isinstance(r, IdentityRevision) and r.security_id == "TEST:ALPHA"
    )
    provenance = old.provenance.model_copy(update={"available_at": clock(2, 0)})
    fact = old.fact.model_copy(
        update={
            "revision_id": "r2",
            "supersedes_revision_id": "r1",
            "symbol": "TEST_RENAMED",
            "provenance": provenance,
        }
    )
    revised = old.model_copy(
        update={
            "revision_id": "r2",
            "revision_number": 2,
            "supersedes_revision_id": "r1",
            "fact": fact,
            "provenance": provenance,
        }
    )
    changed = CanonicalReader(append_reference(reader.batch, revised, tmp_path / "rename"))
    filled = process(state, changed, 2)
    assert filled.orders == state.orders and filled.ledger.transactions[-1].symbol == "TEST_RENAMED"
    assert filled.fills[0].source_lineage["symbol_at_simulated_open"] == "TEST_RENAMED"
