"""TEST_ONLY economic replay, adverse outcomes and temporal boundary evidence."""

import copy
import json
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError
from scripts.build_p6_test_fixture import day, instant
from scripts.build_p10_test_inputs import calendar, definition
from scripts.verify_p9_test_only import definition as evaluation_definition

from alphalens_backtesting.contracts import BacktestDefinition, BenchmarkEvidence, scenarios
from alphalens_backtesting.engine import BacktestResult, run, select
from alphalens_backtesting.evidence import ExecutionEvidence
from alphalens_backtesting.metrics import annual_statistics
from alphalens_backtesting.money import parse_rational, rational
from alphalens_backtesting.storage import SCHEMAS, save, verify
from alphalens_data.canonical.models import PriceView
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import OOSPrediction, digest
from alphalens_evaluation.engine import evaluate
from alphalens_evaluation.storage import OOSDataset


@pytest.fixture(scope="module")
def execution(evaluation_source: Any) -> ExecutionEvidence:
    batch, features, _, _ = evaluation_source
    return ExecutionEvidence(CanonicalReader(batch), features, calendar(batch))


@pytest.fixture(scope="module")
def streams(evaluation_source: Any) -> dict[tuple[str, int], OOSDataset]:
    _, features, aligned, training = evaluation_source
    result = {}
    for task in ("classification", "regression"):
        family = "logistic" if task == "classification" else "ridge"
        for horizon in (1, 5, 10, 20):
            plan = evaluation_definition(aligned[horizon], features, task, training[horizon])
            plan = plan.model_copy(update={"model_families": (family,)})
            output = evaluate(aligned[horizon], features, plan, training[horizon])
            result[(task, horizon)] = OOSDataset(output.manifest, output.predictions)
            result[(task, horizon)].verify()
    return result


def plan(oos: OOSDataset, evidence: ExecutionEvidence, **changes: object) -> BacktestDefinition:
    return definition(oos, evidence, oos.predictions[0].model_family, scenarios()[1], **changes)


def economic_prefix(result: BacktestResult, until: date) -> tuple[Any, ...]:
    keys = (
        "security_id",
        "session_date",
        "status",
        "proposed_budget",
        "planned_entry",
        "planned_exit",
    )
    return (
        [r for r in result.equity if date.fromisoformat(r["session_date"]) <= until],
        [
            {k: r[k] for k in keys}
            for r in result.decisions
            if date.fromisoformat(r["session_date"]) <= until
        ],
    )


def changed_stream(oos: OOSDataset, mutate: Any) -> OOSDataset:
    rows = []
    for row in oos.predictions:
        values = row.model_dump(mode="json", exclude={"prediction_id"})
        mutate(values)
        rows.append(OOSPrediction.model_validate(values | {"prediction_id": digest(values)}))
    manifest = copy.deepcopy(oos.manifest)
    manifest["oos_prediction_dataset_id"] = digest([r.model_dump(mode="json") for r in rows])
    result = OOSDataset(manifest, tuple(rows))
    result.verify()
    return result


@pytest.mark.parametrize("task", ["classification", "regression"])
@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_independent_horizon_replay_cash_inventory_and_execution_boundaries(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    task: str,
    horizon: int,
) -> None:
    oos = streams[task, horizon]
    config = plan(oos, execution)
    first = run(oos, execution, config)
    assert first == run(oos, execution, config)
    assert first.trades
    for row in first.trades:
        assert row["decision_session"] < row["entry_session"] <= row["planned_exit"]
        assert row["prediction_available_at"] < row["entry_time"]
        assert row["entry_time_policy"] == "EXPLICIT_SESSION_OPEN_CONVENTION"
        assert row["classification"] == "TEST_ONLY"
        if row["exit_session"]:
            assert row["exit_session"] == row["planned_exit"]
            assert row["holding_sessions"] == horizon
    for row in first.session_pnl:
        assert Decimal(row["cash"]) >= 0
        assert row["open_positions"] <= config.maximum_positions
        if row["total_pnl"] is not None:
            # Decimal display rounds explicitly; exact reconciliation runs inside the engine.
            assert float(row["total_pnl"]) == pytest.approx(
                float(row["realized_pnl"]) + float(row["unrealized_pnl"])
            )
    assert first.summary["sharpe"] is None
    assert first.summary["cagr"] is None
    assert first.summary["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert first.summary["disclaimer"] == "TEST_ONLY — NOT A PERFORMANCE CLAIM"


def test_exact_costs_quantity_cash_and_normalized_capital(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 1]
    config = plan(oos, execution)
    first = run(oos, execution, config)
    scaled = run(oos, execution, plan(oos, execution, initial_capital=Decimal("1")))
    assert [r["normalized_wealth"] for r in first.equity] == [
        r["normalized_wealth"] for r in scaled.equity
    ]
    for trade in first.trades:
        quantity = Fraction(trade["quantity_rational"])
        budget = Fraction(trade["capital_allocation_rational"])
        entry = Fraction(trade["entry_price"]) * (1 + config.costs.slip_rate)
        assert quantity * entry * (1 + config.costs.fee_rate) == budget
        if trade["exit_session"]:
            exit_price = Fraction(trade["exit_price"]) * (1 - config.costs.slip_rate)
            net = quantity * exit_price * (1 - config.costs.fee_rate) - budget
            assert Fraction(trade["net_pnl_rational"]) == net
    assert first.manifest["backtest_id"] != scaled.manifest["backtest_id"]
    zero = run(oos, execution, definition(oos, execution, "logistic", scenarios()[0]))
    assert zero.summary["total_fees"] == zero.summary["total_slippage"] == 0
    assert zero.summary["net_total_return"] >= first.summary["net_total_return"]


@pytest.mark.parametrize("policy", ["TOP_K", "TOP_PERCENTILE", "PREDICTION_THRESHOLD"])
def test_fixed_selection_policies_and_explicit_zero_probability(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence, policy: str
) -> None:
    oos = streams["classification", 1]
    config = plan(oos, execution, selection_rule=policy, prediction_threshold=Decimal("0"))
    rows = [r for r in oos.predictions if r.session_date == day(52)]
    chosen = select(rows, config, 3)
    expected = 2 if policy == "TOP_K" else 1 if policy == "TOP_PERCENTILE" else 3
    assert len(chosen) == expected
    modified = changed_stream(oos, lambda r: r.update(probability=0.0, prediction=1.0))
    assert (
        select(
            [r for r in modified.predictions if r.session_date == day(52)],
            plan(modified, execution, selection_rule="PREDICTION_THRESHOLD"),
            3,
        )
        == []
    )
    assert (
        run(oos, execution, config).manifest["identity"]["definition"]["selection_rule"] == policy
    )


def test_future_outcome_and_prediction_changes_do_not_rewrite_past_decisions(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 5]
    first = run(oos, execution, plan(oos, execution))

    def mutate(row: dict[str, Any]) -> None:
        if row["actual_target"] is not None:
            row["actual_target"] = 1 - row["actual_target"]
            row["actual_forward_return"] = "999"
        if row["session_date"] >= day(60).isoformat():
            row["probability"] = 1 - row["probability"]
            row["prediction"] = 1 - row["prediction"]

    changed = changed_stream(oos, mutate)
    later = run(changed, execution, plan(changed, execution))
    assert economic_prefix(first, day(59)) == economic_prefix(later, day(59))
    targets_only = changed_stream(
        oos, lambda r: r.update(actual_target=999.0) if r["actual_target"] is not None else None
    )
    assert economic_prefix(first, day(89)) == economic_prefix(
        run(targets_only, execution, plan(targets_only, execution)), day(89)
    )


def test_missing_open_never_fills_or_incur_costs_and_no_fallback(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 1]
    original = execution.price

    def missing(security: str, session: date) -> PriceView | None:
        return None if session == day(53) else original(security, session)

    monkeypatch.setattr(execution, "price", missing)
    output = run(oos, execution, plan(oos, execution))
    assert not any(r["entry_session"] == day(53).isoformat() for r in output.trades)
    assert sum(r["status"] == "NO_FILL_MISSING_OR_REJECTED_OPEN" for r in output.decisions) == 2
    assert Decimal(output.session_pnl[1]["cumulative_fees"]) == 0
    assert Decimal(output.session_pnl[1]["cumulative_slippage"]) == 0
    assert output.equity[1]["portfolio_value"] == "100000"


def test_missing_exit_is_retained_even_when_later_price_exists(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 5]
    original = execution.price

    def missing(security: str, session: date) -> PriceView | None:
        return None if session == day(57) else original(security, session)

    monkeypatch.setattr(execution, "price", missing)
    output = run(oos, execution, plan(oos, execution))
    affected = [r for r in output.trades if r["entry_session"] == day(53).isoformat()]
    assert affected and all(r["exit_session"] is None for r in affected)
    assert all(
        r["exit_reason"] == "UNRESOLVED_HORIZON_EXIT_NO_RECOVERY_ASSUMPTION" for r in affected
    )
    assert all(r["portfolio_value"] is None for r in output.equity[5:])
    assert output.summary["net_total_return"] is None
    assert output.summary["maximum_drawdown"] is None
    assert output.positions[-1]["state"] == "UNRESOLVED"


def test_temporary_unknown_mark_does_not_invent_subsequent_drawdown(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 5]
    original = execution.price

    def missing(security: str, session: date) -> PriceView | None:
        return None if session == day(62) else original(security, session)

    monkeypatch.setattr(execution, "price", missing)
    output = run(oos, execution, plan(oos, execution, start_session=day(60)))
    assert output.equity[2]["portfolio_value"] is None
    assert output.equity[3]["portfolio_value"] is not None
    assert output.drawdown[3]["drawdown"] is None
    assert output.drawdown[3]["status"] == "UNRESOLVED_VALUATION_HISTORY"
    assert output.summary["net_total_return"] is None
    assert output.session_pnl[3]["session_pnl"] is None


def test_departed_security_with_unknown_outcome_is_not_removed_before_selection(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 5]
    depart = [
        r for r in oos.predictions if r.security_id == "TEST:DEPART" and r.session_date == day(52)
    ]
    assert depart and depart[0].scoring_status == "OUTCOME_EXCLUDED"
    config = plan(
        oos,
        execution,
        selection_rule="PREDICTION_THRESHOLD",
        prediction_threshold=Decimal("0"),
        maximum_positions=10,
    )
    output = run(oos, execution, config)
    ledger = [
        r
        for r in output.trades
        if r["security_id"] == "TEST:DEPART" and r["decision_session"] == day(52).isoformat()
    ]
    assert ledger and ledger[0]["exit_session"] is None
    assert ledger[0]["net_return"] is None
    assert output.summary["result_status"] == "UNRESOLVED_ECONOMIC_OUTCOMES"


def test_future_prices_only_change_subsequent_marks_and_exits(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["regression", 5]
    original = execution.price
    first = run(oos, execution, plan(oos, execution))

    def future_price(security: str, session: date) -> PriceView | None:
        view = original(security, session)
        if session >= day(61) and view and view.observation.values:
            values = view.observation.values.model_copy(update={"close": Decimal("999")})
            return view.model_copy(
                update={"observation": view.observation.model_copy(update={"values": values})}
            )
        return view

    monkeypatch.setattr(execution, "price", future_price)
    later = run(oos, execution, plan(oos, execution))
    assert economic_prefix(first, day(60)) == economic_prefix(later, day(60))
    assert first.equity[10] != later.equity[10]


def test_known_economic_action_after_entry_is_unresolved_without_adjustment(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 5]
    original = execution.economic_actions

    def known(security: str, start: date, session: date, cutoff: Any) -> tuple[str, ...]:
        if session >= day(54):
            return ("TEST_ONLY_KNOWN_SPLIT",)
        return original(security, start, session, cutoff)

    first = run(oos, execution, plan(oos, execution))
    monkeypatch.setattr(execution, "economic_actions", known)
    affected = run(oos, execution, plan(oos, execution))
    assert economic_prefix(first, day(53)) == economic_prefix(affected, day(53))
    assert affected.equity[2]["portfolio_value"] is None
    assert affected.trades[0]["corporate_action_state"] == "UNRESOLVED_KNOWN_ECONOMIC_ACTION"
    assert affected.trades[0]["audit_chain"]["known_economic_action_keys"] == [
        "TEST_ONLY_KNOWN_SPLIT"
    ]


def test_calendar_unknown_late_or_clock_unknown_stays_explicit(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 1]
    late_days = tuple(
        d.model_copy(update={"available_at": instant(89)}) for d in execution.calendar.days
    )
    late = ExecutionEvidence(
        execution.reader,
        execution.features,
        execution.calendar.model_copy(update={"days": late_days}),
    )
    output = run(oos, late, plan(oos, late))
    assert not output.trades
    assert output.summary["total_fees"] == 0
    assert output.summary["no_fill_count"] > 0
    unknown_days = tuple(
        d.model_copy(update={"open_at": None, "open_clock_policy": "UNKNOWN"})
        for d in execution.calendar.days
    )
    unknown = ExecutionEvidence(
        execution.reader,
        execution.features,
        execution.calendar.model_copy(update={"days": unknown_days}),
    )
    result = run(oos, unknown, plan(oos, unknown))
    assert result.trades and result.trades[0]["entry_time"] is None
    assert result.trades[0]["entry_time_policy"] == "UNKNOWN"
    with pytest.raises(DataContractError, match="PERIOD_OUTSIDE"):
        run(oos, execution, plan(oos, execution, end_session=day(100)))


def test_changed_holding_calendar_never_creates_wrong_horizon_exit(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 5]
    original = execution.confirmed
    config = plan(oos, execution, start_session=day(60))
    before = run(oos, execution, config)

    def changed(day_evidence: Any) -> bool:
        return False if day_evidence.session_date == day(62) else original(day_evidence)

    monkeypatch.setattr(execution, "confirmed", changed)
    after = run(oos, execution, config)
    assert economic_prefix(before, day(61)) == economic_prefix(after, day(61))
    affected = [t for t in after.trades if t["entry_session"] == day(61).isoformat()]
    assert affected and all(t["exit_session"] is None for t in affected)
    assert all(
        t["audit_chain"]["calendar_conflict_session"] == day(62).isoformat() for t in affected
    )
    assert after.summary["net_total_return"] is None
    assert after.equity[3]["portfolio_value"] is None


def test_oos_only_no_production_and_no_real_benchmark_name_for_fixtures(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 1]
    manifest = copy.deepcopy(oos.manifest)
    manifest["prediction_role"] = "TRAIN"
    with pytest.raises(DataContractError, match="OOS_MANIFEST"):
        run(OOSDataset(manifest, oos.predictions), execution, plan(oos, execution))
    with pytest.raises(ValidationError):
        plan(oos, execution, data_classification="PRODUCTION", benchmark=None)
    with pytest.raises(ValidationError):
        BenchmarkEvidence(
            security_id="TEST",
            name="NIFTY 50",
            classification="TEST_ONLY",
            canonical_input_id=execution.reader.batch.input_id,
            rights_evidence_reference="TEST_ONLY",
        )
    with pytest.raises(DataContractError, match="PINNED_INPUT"):
        run(oos, execution, plan(oos, execution, oos_prediction_dataset_id="a" * 64))


def test_local_artifacts_checksum_schema_deterministic_order_and_lineage(
    streams: dict[tuple[str, int], OOSDataset],
    execution: ExecutionEvidence,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oos = streams["classification", 1]
    result = run(oos, execution, plan(oos, execution))
    monkeypatch.chdir(tmp_path)
    directory = save(result, Path("data/artifacts"))
    manifest = verify(directory)
    assert "definition.json" in manifest["checksums"]
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert save(result, Path("data/artifacts")) == directory
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
    arena = run(oos, execution, plan(oos, execution, comparison_context_id="b" * 64))
    with pytest.raises(DataContractError, match="PINNED_COMPARISON_CONTEXT"):
        save(arena, Path("data/artifacts"))
    for name, schema in SCHEMAS.items():
        assert pq.read_table(directory / name).schema == schema
    for row in result.trades:
        chain = row["audit_chain"]
        assert chain["prediction_id"] == row["prediction_id"]
        assert chain["model_identity"]["training_supervised_dataset_id"]
        assert chain["p7_label_set_id"] and chain["p7_supervised_dataset_id"]
        assert chain["p6_feature_set_id"] and chain["p5_canonical_input_id"]
        assert chain["p4_universe_snapshot_id"] and chain["p3_report_ids"]
        assert chain["p2_source_artifacts"] and chain["p2_source_artifacts"][0]["sha256"]
        if row["exit_session"]:
            assert chain["exit_evidence"]["p3_report_ids"]
    (directory / "summary.json").write_bytes(b"{}")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        verify(directory)


def test_naive_cohort_and_seeded_control_are_not_validated_market_winners(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 1]
    for baseline in ("EQUAL_WEIGHT_ELIGIBLE_COHORT", "SEEDED_RANDOM_CONTROL"):
        config = plan(oos, execution, baseline=baseline, maximum_positions=10)
        result = run(oos, execution, config)
        assert result == run(oos, execution, config)
        assert result.summary["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        assert result.summary["production_claims_permitted"] is False
        assert result.trades
    limited = run(
        oos,
        execution,
        plan(oos, execution, baseline="EQUAL_WEIGHT_ELIGIBLE_COHORT", maximum_positions=1),
    )
    assert not limited.trades
    assert all(
        r["status"] == "BASELINE_CAPACITY_INSUFFICIENT_FOR_ENTIRE_COHORT" for r in limited.decisions
    )


def test_benchmark_unavailable_and_drawdown_matches_equity_peak(
    streams: dict[tuple[str, int], OOSDataset], execution: ExecutionEvidence
) -> None:
    oos = streams["classification", 1]
    result = run(oos, execution, plan(oos, execution, benchmark=None))
    peak = Fraction(100000)
    for row, draw in zip(result.equity, result.drawdown, strict=True):
        value = Fraction(row["value_rational"])
        peak = max(peak, value)
        assert draw["drawdown"] == float(value / peak - 1)
    assert result.summary["benchmark_return"] is None
    assert result.summary["benchmark_status"] == "UNAVAILABLE"
    closed_pnl = [Fraction(r["net_pnl_rational"]) for r in result.trades if r["exit_session"]]
    gains = sum((v for v in closed_pnl if v > 0), Fraction(0))
    losses = -sum((v for v in closed_pnl if v < 0), Fraction(0))
    assert result.summary["profit_factor"] == (
        pytest.approx(float(gains / losses)) if losses else None
    )
    assert json.loads(json.dumps(result.summary, allow_nan=False))["disclaimer"].startswith(
        "TEST_ONLY"
    )


def test_annual_math_undefined_ratios_and_short_fixture_evidence_are_separate() -> None:
    # Authored arithmetic examples verify formulas, not financial performance.
    result = annual_statistics([1.0, 1.1, 0.99, 1.188], 1.0, 365, 252, 0.0, 0.1)
    assert result["cagr"] == pytest.approx(1.188 ** (365.25 / 365) - 1)
    assert result["annualized_volatility"] == pytest.approx((7 / 300) ** 0.5 * 252**0.5)
    assert result["sharpe"] == pytest.approx((1 / 15) / (7 / 300) ** 0.5 * 252**0.5)
    assert result["cagr"] is not None
    assert result["calmar"] == pytest.approx(result["cagr"] / 0.1)
    constant = annual_statistics([1.0, 1.0, 1.0], 1.0, 365, 252, 0.0, 0.0)
    assert constant["sharpe"] is constant["sortino"] is constant["calmar"] is None
    assert constant["annualized_volatility"] == 0.0
    assert all(
        v is None for v in annual_statistics([1.0, 0.0, 1.0], 1.0, 365, 252, 0.0, 0.1).values()
    )
    large = Fraction(10**5000 + 1, 10**4999 + 3)
    assert parse_rational(rational(large)) == large
