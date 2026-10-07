"""Explicitly authored TEST_ONLY state and temporal evidence, never market claims."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from scripts.build_p6_test_fixture import day, instant

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_decision.ranking_contracts import RankingPolicy, RankSnapshot
from alphalens_decision.risk_contracts import RiskPolicy, RiskSnapshot, level
from alphalens_decision.signal_contracts import PositionEvidence, SignalPolicy, SignalSnapshot
from alphalens_decision.signal_storage import load, save
from alphalens_decision.signals import evaluate
from alphalens_evaluation.contracts import digest, disclaimer


def sealed(model: type[BaseModel], key: str, **payload: Any) -> Any:
    typed: dict[str, Any] = {
        name: TypeAdapter(model.model_fields[name].annotation).validate_python(value)
        for name, value in payload.items()
    }
    typed[key] = "0" * 64
    draft = model.model_construct(**typed)
    content = draft.model_dump(mode="json", exclude={key})
    return model.model_validate({key: digest(content), **content})


def evidence(
    index: int = 60,
    horizon: Any = 5,
    probability: float = 0.85,
    uncertainty: float = 0.1,
    severity: float = 0.1,
    quality: str = "VALID",
    corporate: bool = False,
) -> tuple[RankSnapshot, RiskSnapshot]:
    """All numeric evidence here is constructed, not replayed market history."""
    names = (
        "volatility_risk",
        "drawdown_risk",
        "liquidity_proxy_risk",
        "gap_risk",
        "market_risk",
        "model_uncertainty",
        "data_quality_risk",
        "corporate_action_risk",
        "historical_evidence",
    )
    components = {
        n: dict(
            metrics={"TEST_ONLY_measure": 0.1},
            severity=uncertainty if n == "model_uncertainty" else severity,
            level=level(uncertainty if n == "model_uncertainty" else severity),
            availability="DEGRADED",
            reasons=("CORPORATE_ACTION_UNCERTAINTY",)
            if corporate and n == "corporate_action_risk"
            else (),
        )
        for n in names
    }
    refs = dict(
        feature_set_id=digest("features"),
        canonical_input_id=digest("input"),
        canonical_dataset_id=digest(index),
        universe_snapshot_id=digest((index, "universe")),
        universe_definition_id="TEST_ONLY_UNIVERSE",
    )
    risk = sealed(
        RiskSnapshot,
        "risk_snapshot_id",
        security_id="TEST:A",
        symbol="TEST_A",
        session_date=day(index),
        decision_time=instant(index),
        knowledge_cutoff=instant(index),
        horizon=horizon,
        **refs,
        observed_price_available_at=instant(index, 10),
        source_quality=quality,
        feature_availability="DEGRADED",
        classification="TEST_ONLY",
        policy=RiskPolicy(),
        components=components,
        overall_level=level(max(severity, uncertainty)),
        model_confidence="INSUFFICIENT_EVIDENCE",
        evidence_sufficiency="SUFFICIENT",
        analysis_permitted=True,
        availability="DEGRADED",
        reasons=("CORPORATE_ACTION_UNCERTAINTY",) if corporate else (),
        prediction_evidence_ids=(digest("prediction"),),
        diagnostic_evidence_ids=(),
        model_run_ids=(digest("model"),),
        evaluation_ids=(digest("evaluation"),),
        disclaimer=disclaimer(Classification.TEST_ONLY),
    )
    from alphalens_decision.ranking import score

    policy = RankingPolicy(horizon=horizon)
    parts, raw, penalties, adjusted = score(probability, 0.03, 0.75, risk, policy)
    ranked = dict(
        rank=1,
        security_id="TEST:A",
        symbol="TEST_A",
        session_date=day(index),
        horizon=horizon,
        probability=probability,
        predicted_return=0.03,
        components=parts,
        raw_opportunity_score=raw,
        penalties=penalties,
        risk_adjusted_score=adjusted,
        overall_risk=risk.overall_level,
        quality_state=quality,
        availability="DEGRADED",
        observed_price_available_at=risk.observed_price_available_at,
        reasons=(),
        prediction_evidence_ids=risk.prediction_evidence_ids,
        model_run_ids=risk.model_run_ids,
        evaluation_ids=risk.evaluation_ids,
        feature_set_id=refs["feature_set_id"],
        canonical_dataset_id=refs["canonical_dataset_id"],
        universe_snapshot_id=refs["universe_snapshot_id"],
        risk_snapshot_id=risk.risk_snapshot_id,
    )
    ranking = sealed(
        RankSnapshot,
        "rank_snapshot_id",
        session_date=day(index),
        knowledge_cutoff=instant(index),
        horizon=horizon,
        policy=policy,
        classification="TEST_ONLY",
        **refs,
        prediction_set_id=digest(index),
        risk_snapshot_ids=(risk.risk_snapshot_id,),
        model_selection_status="TEST_ONLY_SELECTED_CANDIDATE",
        model_comparison={},
        ranked=(ranked,),
        excluded=(),
        previous_snapshot_id=None,
        downstream_references={},
        disclaimer=disclaimer(Classification.TEST_ONLY),
    )
    return ranking, risk


def demo(horizon: Any = 5, **changes: Any) -> SignalPolicy:
    return SignalPolicy(horizon=horizon, test_only_state_demonstration=True, **changes)


def position(**changes: Any) -> PositionEvidence:
    return PositionEvidence.model_validate(
        dict(
            context_id="TEST_ONLY_POSITION",
            security_id="TEST:A",
            horizon=5,
            entry_at=instant(58),
            available_at=instant(59),
            evidence_reference="TEST_ONLY_RECORD",
            **changes,
        )
    )


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_confirmation_and_independent_horizons(horizon: Any) -> None:
    first, risk = evidence(60, horizon)
    policy = demo(horizon)
    setup = evaluate(first, "TEST:A", (risk,), policy)
    assert setup.state == "SETUP_FORMING" and setup.confirmation_count == 1
    second, risk2 = evidence(61, horizon)
    entry = evaluate(second, "TEST:A", (risk2,), policy, (setup,))
    assert entry.state == "ENTRY_SIGNAL" and entry.previous_state == "SETUP_FORMING"
    assert entry.horizon == horizon and entry.prediction_horizon == horizon
    assert entry.expected_return_label == "MODEL ESTIMATE — NOT GUARANTEED"
    assert entry.model_confidence == "INSUFFICIENT_EVIDENCE"
    assert entry.signal_confidence == "TEST_ONLY_DEVELOPMENT_EVIDENCE"
    assert entry == evaluate(second, "TEST:A", (risk2,), policy, (setup,))


def test_default_insufficient_evidence_never_produces_entry() -> None:
    ranking, risk = evidence()
    signal = evaluate(
        ranking, "TEST:A", (risk,), SignalPolicy(horizon=5, confirmation_observations=1)
    )
    assert signal.state == "SETUP_FORMING"
    assert not signal.entry_conditions["model_evidence"]
    assert "MODEL_EVIDENCE_UNAVAILABLE" in signal.negative_reasons


def test_hysteresis_and_deterioration() -> None:
    policy = demo(confirmation_observations=1)
    rank1, risk1 = evidence(60)
    entry = evaluate(rank1, "TEST:A", (risk1,), policy)
    rank2, risk2 = evidence(61, probability=0.58)
    retained = evaluate(rank2, "TEST:A", (risk2,), policy, (entry,))
    assert retained.state == "ENTRY_SIGNAL" and not retained.entry_conditions["probability"]
    assert retained.transition_reasons == ("ENTRY_RETAINED_BY_HYSTERESIS",)
    rank3, risk3 = evidence(62, probability=0.40, severity=0.9)
    assert evaluate(rank3, "TEST:A", (risk3,), policy, (entry, retained)).state == "WATCH"


def test_position_lifecycle_requires_evidence_and_no_position_is_inferred() -> None:
    ranking, risk = evidence()
    policy = demo(confirmation_observations=1)
    assert evaluate(ranking, "TEST:A", (risk,), policy).context == "MARKET_OPPORTUNITY_STATE"
    held = evaluate(ranking, "TEST:A", (risk,), policy, positions=(position(),))
    assert held.state == "HOLD"
    review = evaluate(
        ranking, "TEST:A", (risk,), policy, positions=(position(profit_review_requested=True),)
    )
    assert review.state == "TAKE_PROFIT_REVIEW"
    poor, poor_risk = evidence(severity=0.9)
    assert (
        evaluate(poor, "TEST:A", (poor_risk,), policy, positions=(position(),)).state
        == "EXIT_SIGNAL"
    )
    exited = evaluate(
        ranking, "TEST:A", (risk,), policy, positions=(position(exit_at=instant(59, 10)),)
    )
    assert exited.state == "EXITED" and exited.position_evidence is not None
    assert held.technical_invalidation_price is None


@pytest.mark.parametrize(
    "changes, reason",
    [
        ({"severity": 0.9}, "RISK_EXCEEDS_LIMIT"),
        ({"uncertainty": 0.7}, "MODEL_CONFIDENCE_DROPS"),
        ({"quality": "DEGRADED"}, "DATA_QUALITY_DEGRADES"),
        ({"corporate": True}, "CORPORATE_ACTION_UNCERTAINTY"),
        ({"probability": 0.3}, "PREDICTIVE_STRENGTH_BELOW_THRESHOLD"),
    ],
)
def test_entry_requires_multiple_conditions(changes: dict[str, Any], reason: str) -> None:
    ranking, risk = evidence(**changes)
    result = evaluate(ranking, "TEST:A", (risk,), demo(confirmation_observations=1))
    assert result.state != "ENTRY_SIGNAL" and reason in result.negative_reasons
    assert result.negative_reasons == tuple(sorted(set(result.negative_reasons)))


def test_future_risk_rank_history_position_symbol_and_policy_are_invisible() -> None:
    ranking, risk = evidence()
    future, future_risk = evidence(65, severity=0.9)
    policy = demo(confirmation_observations=1)
    earlier = evaluate(ranking, "TEST:A", (risk,), policy)
    future_signal = evaluate(future, "TEST:A", (future_risk,), policy)
    future_position = PositionEvidence.model_validate(
        dict(position().model_dump(), available_at=instant(65), exit_at=instant(64))
    )
    assert earlier == evaluate(
        ranking, "TEST:A", (risk, future_risk), policy, (future_signal,), (future_position,)
    )
    assert (
        evaluate(
            ranking, "TEST:A", (risk,), demo(revision="new", confirmation_observations=1)
        ).signal_snapshot_id
        != earlier.signal_snapshot_id
    )
    with pytest.raises(DataContractError, match="NOT_KNOWN"):
        evaluate(ranking, "TEST:FUTURE_MEMBER", (risk,), policy)
    assert "TEST:FUTURE_MEMBER" not in str(earlier.model_dump())


def test_history_uses_only_past_compatible_unique_observations() -> None:
    ranking, risk = evidence(60)
    first = evaluate(ranking, "TEST:A", (risk,), demo())
    later, risk2 = evidence(70)
    assert evaluate(later, "TEST:A", (risk2,), demo(), (first,)).confirmation_count == 1
    with pytest.raises(DataContractError, match="AMBIGUOUS_SIGNAL_HISTORY"):
        evaluate(later, "TEST:A", (risk2,), demo(), (first, first))
    changed = evaluate(ranking, "TEST:A", (risk,), demo(revision="different"))
    assert evaluate(later, "TEST:A", (risk2,), demo(), (changed,)).previous_state is None


def test_missing_or_mismatched_risk_never_becomes_low() -> None:
    ranking, risk = evidence()
    absent = evaluate(ranking, "TEST:A", (), demo(confirmation_observations=1))
    assert absent.state == "WATCH" and absent.risk_level == "UNAVAILABLE"
    assert absent.data_freshness == "UNAVAILABLE"
    _, different = evidence(probability=0.7, severity=0.2)
    with pytest.raises(DataContractError, match="LINEAGE"):
        evaluate(ranking, "TEST:A", (different,), demo())
    with pytest.raises(DataContractError, match="AMBIGUOUS_SIGNAL_RISK"):
        evaluate(ranking, "TEST:A", (risk, risk), demo())


def test_artifact_identity_checksum_and_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ranking, risk = evidence()
    result = evaluate(
        ranking, "TEST:A", (risk,), demo(confirmation_observations=1, review_horizon=1)
    )
    directory = save(result, tmp_path / "data")
    assert load(directory) == result and save(result, tmp_path / "data") == directory
    assert result.data_freshness == "EOD_COMPLETE" and result.preferred_review_horizon == 1
    assert "TEST_ONLY" in result.disclaimer
    for changes in (
        {"classification": "PRODUCTION"},
        {"state": "EXITED"},
        {"production_claims_permitted": True},
        {"expected_return_estimate": 0.8},
    ):
        with pytest.raises(ValidationError):
            SignalSnapshot.model_validate(dict(result.model_dump(), **changes))
    (directory / "signal-snapshot.json").write_bytes(b"{}")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(directory)


def test_target_fields_and_impossible_event_times_rejected() -> None:
    with pytest.raises(ValidationError):
        SignalPolicy.model_validate(dict(horizon=5, target_return=0.99))
    with pytest.raises(ValidationError):
        PositionEvidence.model_validate(dict(position().model_dump(), available_at=instant(57)))
    with pytest.raises(ValidationError):
        SignalPolicy(horizon=1, review_horizon=20)


@pytest.mark.parametrize(
    "field,value,failed",
    [
        ("evidence_sufficiency", "LIMITED", "history"),
        ("feature_availability", "STALE", "freshness"),
    ],
)
def test_missing_evidence_is_not_entry_confidence(field: str, value: str, failed: str) -> None:
    ranking, risk = evidence()
    changed = sealed(
        RiskSnapshot,
        "risk_snapshot_id",
        **dict(risk.model_dump(exclude={"risk_snapshot_id"}), **{field: value}),
    )
    candidate = ranking.ranked[0].model_copy(update={"risk_snapshot_id": changed.risk_snapshot_id})
    updated = sealed(
        RankSnapshot,
        "rank_snapshot_id",
        **dict(
            ranking.model_dump(exclude={"rank_snapshot_id"}),
            ranked=(candidate,),
            risk_snapshot_ids=(changed.risk_snapshot_id,),
        ),
    )
    result = evaluate(updated, "TEST:A", (changed,), demo(confirmation_observations=1))
    assert result.state != "ENTRY_SIGNAL" and not result.entry_conditions[failed]
    assert result.signal_confidence == "INSUFFICIENT_EVIDENCE"
