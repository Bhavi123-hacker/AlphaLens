"""TEST_ONLY risk arithmetic, actual canonical evidence and availability guards."""

from pathlib import Path
from statistics import stdev
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p6_test_fixture import START, build_history, day, instant

from alphalens_data.canonical.assembly import EvidenceAssembly
from alphalens_data.canonical.models import ActionRevision
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.models import Horizon, ModelDiagnostic, ModelEvidence, PredictionEvidence
from alphalens_decision.risk import RiskEngine, model_uncertainty
from alphalens_decision.risk_contracts import RiskPolicy, RiskSnapshot
from alphalens_decision.risk_storage import load, save
from alphalens_evaluation.contracts import digest
from alphalens_features.engine import build
from alphalens_features.models import BuildPlan, Decision


@pytest.fixture(scope="module")
def engine(evaluation_source: Any) -> RiskEngine:
    batch, features, _, _ = evaluation_source
    return RiskEngine(CanonicalReader(batch), features)


@pytest.fixture(scope="module")
def adverse(tmp_path_factory: pytest.TempPathFactory) -> RiskEngine:
    changes = {(i, "TEST:ALPHA"): {"volume": "0"} for i in range(5, 26)}
    changes[25, "TEST:BETA"] = {"open": "60", "high": "65", "low": "45", "close": "50"}
    changes[25, "TEST:BENCHMARK"] = {"close": ""}
    batch = build_history(tmp_path_factory.mktemp("TEST_ONLY_risk"), length=26, overrides=changes)[
        0
    ]
    reader = CanonicalReader(batch)
    features = build(
        reader,
        BuildPlan(
            history_start=START,
            decisions=tuple(
                Decision(session_date=day(i), knowledge_cutoff=instant(i, 12)) for i in (10, 25)
            ),
        ),
    )
    return RiskEngine(reader, features)


def prediction(
    engine: RiskEngine, probability: float, family: str = "logistic", index: int = 60
) -> PredictionEvidence:
    row = engine.row("TEST:ALPHA", day(index))
    return PredictionEvidence.model_validate(
        dict(
            origin="TEST_ONLY_AUTHORED",
            evaluation_id=digest("TEST_ONLY evaluation"),
            model_run_id=digest(family),
            family=family,
            task="classification",
            horizon=5,
            security_id=row.security_id,
            session_date=row.session_date,
            decision_time=row.decision_time,
            available_at=row.decision_time,
            training_cutoff=instant(40, 12),
            feature_set_id=engine.features.feature_set_id,
            canonical_dataset_id=row.canonical_dataset_id,
            universe_snapshot_id=row.universe_snapshot_id,
            prediction=int(probability > 0.5),
            probability=probability,
            classification="TEST_ONLY",
        )
    )


def diagnostic(p: PredictionEvidence, **changes: Any) -> ModelDiagnostic:
    values = dict(
        origin="TEST_ONLY_AUTHORED",
        evaluation_id=p.evaluation_id,
        model_run_id=p.model_run_id,
        family=p.family,
        task=p.task,
        horizon=p.horizon,
        fold_id="TEST_ONLY prior fold",
        period_end=day(45),
        available_at=instant(46, 12),
        report_checksum=digest("TEST_ONLY diagnostics"),
        sample_count=120,
        primary_metric=0.04,
        naive_improvement=0.01,
        brier_score=0.04,
        calibration_available=True,
        classification="TEST_ONLY",
    )
    return ModelDiagnostic.model_validate(dict(values, **changes))


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_components_reuse_p6_and_snapshot_replay(engine: RiskEngine, horizon: Horizon) -> None:
    result = engine.evaluate("TEST:ALPHA", day(60), horizon)
    row = engine.row("TEST:ALPHA", day(60))
    assert result == engine.evaluate("TEST:ALPHA", day(60), horizon)
    assert (
        result.components["volatility_risk"].metrics["volatility_20"]
        == row.values["volatility_20"].value
    )
    assert (
        result.components["drawdown_risk"].metrics["current_drawdown"]
        == row.values["drawdown_20"].value
    )
    assert result.reasons == tuple(sorted(set(result.reasons)))
    assert result.model_confidence == "INSUFFICIENT_EVIDENCE"
    assert result.classification == Classification.TEST_ONLY
    assert result.disclaimer == "TEST_ONLY — NOT A PERFORMANCE CLAIM"


def test_gap_and_recent_drawdown_are_past_only_arithmetic(adverse: RiskEngine) -> None:
    result = adverse.evaluate("TEST:BETA", day(25), 5)
    snap = adverse.snapshot(adverse.row("TEST:BETA", day(25)))
    views = [v for v in snap.prices if v.observation.security_id == "TEST:BETA"]
    last, previous = views[-1].observation.values, views[-2].observation.values
    assert last and previous
    assert result.components["gap_risk"].metrics["latest_gap"] == pytest.approx(
        float(last.open / previous.close - 1)
    )
    assert result.components["drawdown_risk"].level == "VERY_HIGH"
    assert "DEEP_RECENT_DRAWDOWN" in result.reasons


def test_zero_volume_and_degraded_quality_are_not_neutral(adverse: RiskEngine) -> None:
    result = adverse.evaluate("TEST:ALPHA", day(25), 5)
    volume = result.components["liquidity_proxy_risk"]
    assert volume.metrics["proxy"] == "VOLUME_BASED_LIQUIDITY_PROXY"
    assert volume.metrics["zero_volume_frequency"] == 1
    assert volume.level == "VERY_HIGH"
    assert "DEGRADED_SOURCE_DATA" in result.reasons
    assert result.source_quality == "DEGRADED"
    assert result.availability == "DEGRADED"


def test_rejected_source_blocks_analysis(adverse: RiskEngine) -> None:
    result = adverse.evaluate("TEST:BENCHMARK", day(25), 5)
    assert not result.analysis_permitted
    assert result.overall_level == "UNAVAILABLE"
    assert "DATA_QUALITY_REJECTED" in result.reasons


def test_insufficient_history_and_benchmark_stay_unavailable(adverse: RiskEngine) -> None:
    result = adverse.evaluate("TEST:BETA", day(10), 1)
    assert result.evidence_sufficiency == "INSUFFICIENT"
    assert result.overall_level == "UNAVAILABLE"
    assert result.components["market_risk"].availability == "UNAVAILABLE"
    assert "BENCHMARK_UNAVAILABLE" in result.reasons
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_model_disagreement_calibration_and_count_policy(engine: RiskEngine) -> None:
    left, right = prediction(engine, 0.05), prediction(engine, 0.95, "random_forest")
    result = model_uncertainty([left, right], [diagnostic(left), diagnostic(right)], RiskPolicy())
    assert result.metrics["models_probability_positive"] == 1
    assert result.metrics["probability_dispersion"] == pytest.approx(0.45)
    assert result.metrics["historical_validation_rows_per_family_minimum"] == 120
    assert "MODEL_DISAGREEMENT" in result.reasons
    assert result.level == "VERY_HIGH"
    insufficient = model_uncertainty(
        [left, right],
        [diagnostic(left, sample_count=20), diagnostic(right, sample_count=20)],
        RiskPolicy(),
    )
    assert "INSUFFICIENT_MODEL_VALIDATION" in insufficient.reasons
    # Two models scoring the same small fold must not multiply the evidence count.
    assert insufficient.metrics["historical_validation_rows_per_family_minimum"] == 20


def test_future_models_and_diagnostics_do_not_change_prior_snapshot(engine: RiskEngine) -> None:
    current = prediction(engine, 0.9)
    known = diagnostic(current)
    future = prediction(engine, 0.1, "random_forest", index=68)
    late = diagnostic(
        current,
        fold_id="future fold",
        available_at=instant(80, 12),
        sample_count=10000,
        brier_score=0.99,
    )
    baseline = RiskEngine(
        engine.reader,
        engine.features,
        ModelEvidence(classification="TEST_ONLY", predictions=(current,), diagnostics=(known,)),
    )
    altered = RiskEngine(
        engine.reader,
        engine.features,
        ModelEvidence(
            classification="TEST_ONLY", predictions=(current, future), diagnostics=(known, late)
        ),
    )
    assert baseline.evaluate("TEST:ALPHA", day(60), 5) == altered.evaluate("TEST:ALPHA", day(60), 5)


def test_target_and_production_fields_are_rejected(engine: RiskEngine) -> None:
    p = prediction(engine, 0.6)
    with pytest.raises(ValidationError):
        PredictionEvidence.model_validate(dict(p.model_dump(), actual_target=1))
    with pytest.raises(ValidationError):
        PredictionEvidence.model_validate(dict(p.model_dump(), classification="PRODUCTION"))
    result = engine.evaluate("TEST:ALPHA", day(60), 5)
    with pytest.raises(ValidationError):
        RiskSnapshot.model_validate(dict(result.model_dump(), classification="PRODUCTION"))


def test_policy_and_input_identity_pins_are_enforced(engine: RiskEngine) -> None:
    first = engine.evaluate("TEST:ALPHA", day(60), 5)
    second = engine.evaluate("TEST:ALPHA", day(60), 5, RiskPolicy(volatility_scale=0.10))
    assert first.risk_snapshot_id != second.risk_snapshot_id
    assert first.feature_set_id == engine.features.feature_set_id
    with pytest.raises(DataContractError, match="IDENTITY"):
        RiskEngine(engine.reader, engine.features.model_copy(update={"feature_set_id": "0" * 64}))


def test_risk_artifact_roundtrip_and_tamper(
    engine: RiskEngine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = engine.evaluate("TEST:ALPHA", day(60), 5)
    directory = save(result, Path("data/risk"))
    assert save(result, Path("data/risk")) == directory
    assert load(directory) == result
    (directory / "risk-snapshot.json").write_bytes(stable_json({"tampered": True}))
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(directory)


def test_volume_instability_matches_sample_coefficient(engine: RiskEngine) -> None:
    result = engine.evaluate("TEST:ALPHA", day(60), 5)
    snap = engine.snapshot(engine.row("TEST:ALPHA", day(60)))
    volumes = [
        v.observation.values.volume
        for v in snap.prices
        if v.observation.security_id == "TEST:ALPHA" and v.observation.values
    ][-20:]
    assert result.components["liquidity_proxy_risk"].metrics["volume_cv"] == pytest.approx(
        stdev(volumes) / (sum(volumes) / len(volumes))
    )


def test_known_corporate_action_does_not_become_ordinary_gap(
    adverse: RiskEngine, tmp_path: Path
) -> None:
    old = adverse.reader.batch.revisions[0]
    action = ActionRevision(
        logical_record_id="TEST_ONLY risk split",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:BETA",
        effective_from=day(20),
        ex_date=day(20),
        corporate_action_id="TEST_ONLY risk split",
        event_type="SPLIT",
        provenance=old.provenance.model_copy(update={"available_at": instant(20)}),
    )
    original = adverse.reader.batch
    assembly = EvidenceAssembly(tmp_path, Classification.TEST_ONLY)
    assembly.reference(action)
    artifact = next(a for a in original.artifacts if a.sha256 == action.provenance.artifact_sha256)
    assembly.link_reference(action, artifact, {"evidence_sha256": artifact.sha256})
    batch = original.model_copy(
        update=dict(
            revisions=(*original.revisions, action),
            artifacts=(*original.artifacts, *assembly.artifacts.values()),
            normalized=tuple(
                {
                    n.normalized_record_id: n
                    for n in (*original.normalized, *assembly.normalized.values())
                }.values()
            ),
            lineage=(*original.lineage, *assembly.lineage),
        )
    )
    reader = CanonicalReader(batch)
    features = build(reader, adverse.features.feature_set.plan)
    result = RiskEngine(reader, features).evaluate("TEST:BETA", day(25), 5)
    assert "KNOWN_UNADJUSTED_CORPORATE_ACTION" in result.reasons
    assert result.components["gap_risk"].metrics["latest_gap"] is None
    assert not result.analysis_permitted


def test_evidenced_benchmark_uses_p6_relative_volatility(engine: RiskEngine) -> None:
    data = build(
        engine.reader,
        BuildPlan(
            history_start=START,
            decisions=(Decision(session_date=day(60), knowledge_cutoff=instant(60, 12)),),
            benchmark_security_id="TEST:BENCHMARK",
            benchmark_evidence_reference="TEST_ONLY benchmark",
        ),
    )
    result = RiskEngine(engine.reader, data).evaluate("TEST:ALPHA", day(60), 5)
    values = next(r.values for r in data.rows if r.security_id == "TEST:ALPHA")
    vol, market = values["volatility_20"].value, values["market_volatility_20"].value
    assert vol is not None and market is not None
    assert result.components["market_risk"].metrics["relative_volatility"] == pytest.approx(
        vol / market
    )


def test_regression_disagreement_and_weak_calibration(engine: RiskEngine) -> None:
    left, right = prediction(engine, 0.9), prediction(engine, 0.8, "random_forest")
    regressors = [
        PredictionEvidence.model_validate(
            dict(
                p.model_dump(),
                task="regression",
                family="ridge" if i == 0 else "random_forest",
                probability=None,
                prediction=-0.04 if i == 0 else 0.04,
            )
        )
        for i, p in enumerate((left, right))
    ]
    result = model_uncertainty(regressors, [], RiskPolicy())
    assert result.metrics["predicted_return_dispersion"] == pytest.approx(0.04)
    assert "MODEL_DISAGREEMENT" in result.reasons
    calibrated = model_uncertainty([left], [diagnostic(left, brier_score=0.30)], RiskPolicy())
    assert calibrated.level == "VERY_HIGH"
    assert "CALIBRATION_WEAKNESS" in calibrated.reasons


def test_duplicate_fold_diagnostics_cannot_multiply_evidence(engine: RiskEngine) -> None:
    current = prediction(engine, 0.9)
    first = diagnostic(current)
    duplicate = diagnostic(current, report_checksum=digest("other report"), sample_count=10000)
    with pytest.raises(ValidationError, match="Ambiguous diagnostic"):
        ModelEvidence(
            classification="TEST_ONLY", predictions=(current,), diagnostics=(first, duplicate)
        )
