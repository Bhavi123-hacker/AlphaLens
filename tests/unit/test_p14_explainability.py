"""Constructed TEST_ONLY evidence; attribution mechanics are not market performance."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import skops.io as sio
from pydantic import ValidationError
from scripts.build_p6_test_fixture import day, instant
from test_p13_signals import demo, evidence, position, sealed
from threadpoolctl import threadpool_limits

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_decision.attribution import local_attribution
from alphalens_decision.explanation_contracts import ExplainabilitySnapshot, ExplanationPolicy
from alphalens_decision.explanation_models import from_p9
from alphalens_decision.explanation_storage import load, save
from alphalens_decision.explanations import explain
from alphalens_decision.models import PredictionEvidence
from alphalens_decision.ranking_contracts import RankSnapshot
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_decision.signals import evaluate
from alphalens_evaluation.contracts import digest
from alphalens_evaluation.models import build_model
from alphalens_features.models import BuildPlan, Decision, FeatureDataset, FeatureRow, FeatureValue
from alphalens_features.registry import default_set
from alphalens_training.contracts import TrainingConfig


class UnreviewedTestOnlyObject:
    """Inert authored object whose serialized type must never gain implicit trust."""


def with_features(ranking: RankSnapshot, risk: RiskSnapshot) -> tuple[Any, ...]:
    definitions = default_set(
        BuildPlan(
            history_start=day(0),
            decisions=(
                Decision(session_date=risk.session_date, knowledge_cutoff=risk.knowledge_cutoff),
            ),
        )
    )
    measured = {
        "rsi_14": 63.2,
        "return_1": 0.02,
        "return_20": 0.03,
        "momentum_percentile_20": 0.75,
        "volatility_20": 0.01,
    }
    values = {
        d.feature_name: FeatureValue(
            value=measured.get(d.feature_name),
            state="AVAILABLE" if d.feature_name in measured else "UNAVAILABLE",
            reason_codes=() if d.feature_name in measured else ("TEST_ONLY_UNAVAILABLE",),
        )
        for d in definitions.definitions
    }
    row = FeatureRow(
        security_id=risk.security_id,
        session_date=risk.session_date,
        decision_time=risk.decision_time,
        knowledge_cutoff=risk.knowledge_cutoff,
        canonical_dataset_id=risk.canonical_dataset_id,
        universe_snapshot_id=risk.universe_snapshot_id,
        input_versions=("TEST_ONLY_SOURCE_V1",),
        input_revision_keys=(digest("TEST_ONLY_REVISION"),),
        classification=Classification.TEST_ONLY,
        price_basis="UNADJUSTED",
        quality_state="AVAILABLE",
        analytical_eligible=True,
        reason_codes=(),
        corporate_action_keys=(),
        values=values,
    )
    features = sealed(
        FeatureDataset,
        "feature_set_id",
        canonical_dataset_id=digest("full_source_dataset"),
        canonical_input_id=risk.canonical_input_id,
        classification=Classification.TEST_ONLY,
        universe_definition_version="TEST_ONLY",
        feature_set=definitions,
        rows=(row,),
    )
    updated_risk = sealed(
        RiskSnapshot,
        "risk_snapshot_id",
        **dict(
            risk.model_dump(exclude={"risk_snapshot_id"}), feature_set_id=features.feature_set_id
        ),
    )
    candidate = ranking.ranked[0].model_copy(
        update=dict(
            feature_set_id=features.feature_set_id, risk_snapshot_id=updated_risk.risk_snapshot_id
        )
    )
    updated_rank = sealed(
        RankSnapshot,
        "rank_snapshot_id",
        **dict(
            ranking.model_dump(exclude={"rank_snapshot_id"}),
            feature_set_id=features.feature_set_id,
            ranked=(candidate,),
            risk_snapshot_ids=(updated_risk.risk_snapshot_id,),
        ),
    )
    return features, updated_rank, updated_risk


def authored_model(
    family: Any, task: str = "classification", missing: bool = False
) -> tuple[Any, ...]:
    features, _, _ = with_features(*evidence())
    if missing:
        row = features.rows[0]
        values = dict(
            row.values,
            return_1=FeatureValue(
                value=None, state="UNAVAILABLE", reason_codes=("TEST_ONLY_MISSING",)
            ),
        )
        features = sealed(
            FeatureDataset,
            "feature_set_id",
            **dict(
                features.model_dump(exclude={"feature_set_id"}),
                rows=(row.model_copy(update=dict(values=values)),),
            ),
        )
    config = TrainingConfig.model_validate(
        dict(
            task=task,
            horizon=5,
            model_family="logistic" if task == "classification" else "ridge",
            training_cutoff=instant(50),
            validation_start=day(60),
            validation_end=day(65),
        )
    )
    model = build_model(family, config)
    index = np.arange(80, dtype="float64")
    x = np.column_stack((np.linspace(-0.1, 0.1, 80), 45 + 20 * np.sin(index / 7)))
    y = 0.3 * x[:, 0] - 0.001 * x[:, 1]
    if task == "classification":
        y = (y > np.median(y)).astype(int)
    raw = [
        [
            features.rows[0].values[n].value
            if features.rows[0].values[n].value is not None
            else np.nan
            for n in ("return_1", "rsi_14")
        ]
    ]
    with threadpool_limits(limits=1):
        model.fit(x, y)
        probability = float(model.predict_proba(raw)[0, 1]) if task == "classification" else None
        prediction = float(model.predict(raw)[0])
    identity = dict(
        evaluation_id=digest("TEST_ONLY_evaluation"),
        model_family=family,
        effective_training_cutoff=instant(50).isoformat(),
        feature_order=("return_1", "rsi_14"),
        configuration=config.model_dump(mode="json"),
        hyperparameters=model.named_steps["estimator"].get_params(deep=False),
        training_row_digest=digest("80_TEST_ONLY_AUTHORED_TRAIN_ROWS"),
    )
    row = features.rows[0]
    p = PredictionEvidence(
        origin="TEST_ONLY_AUTHORED",
        evaluation_id=identity["evaluation_id"],
        model_run_id=digest(identity),
        family=family,
        task=task,
        horizon=5,
        security_id=row.security_id,
        session_date=row.session_date,
        decision_time=row.decision_time,
        available_at=row.decision_time,
        training_cutoff=instant(50),
        feature_set_id=features.feature_set_id,
        canonical_dataset_id=row.canonical_dataset_id,
        universe_snapshot_id=row.universe_snapshot_id,
        prediction=prediction,
        probability=probability,
        classification=Classification.TEST_ONLY,
    )
    return model, identity, p, features


@pytest.mark.parametrize(
    "task,family",
    [
        (task, family)
        for task in ("classification", "regression")
        for family in (
            (
                "logistic",
                "random_forest",
                "hist_gradient_boosting",
                "lightgbm",
                "catboost",
                "xgboost",
            )
            if task == "classification"
            else (
                "ridge",
                "random_forest",
                "hist_gradient_boosting",
                "lightgbm",
                "catboost",
                "xgboost",
            )
        )
    ],
)
def test_local_methods_reconstruct_real_fitted_prediction(task: str, family: str) -> None:
    model, identity, p, features = authored_model(family, task)
    first = local_attribution(model, identity, p, features)
    assert first == local_attribution(model, identity, p, features)
    assert sum(c.contribution for c in first.contributions) + first.base_value == pytest.approx(
        first.explained_output, abs=1e-6
    )
    assert first.contributions[1].actual_value == 63.2
    assert (
        first.classification == Classification.TEST_ONLY
        and "NOT A PERFORMANCE CLAIM" in first.disclaimer
    )
    assert first.scope == "LOCAL_PREDICTION"
    if family in {"lightgbm", "catboost", "xgboost"}:
        assert first.method == "NATIVE_TREE_SHAP" and first.output_space == (
            "LOG_ODDS" if task == "classification" else "RETURN"
        )
    elif family in {"logistic", "ridge"}:
        assert first.method == "LINEAR_COEFFICIENT"
        transformed = np.asarray(model[:-1].transform([[0.02, 63.2]])).reshape(-1)
        coefficients = np.asarray(model.named_steps["estimator"].coef_).reshape(-1)
        np.testing.assert_allclose(
            [c.contribution for c in first.contributions], transformed * coefficients
        )
    else:
        assert first.method == "ORDERED_TRAIN_MEDIAN_PATH"
        assert "ORDER_DEPENDENT_INTERACTIONS_ASSIGNED_TO_LATER_FEATURES" in first.limitations


def test_imputation_disclosure_never_fabricates_raw_feature() -> None:
    model, identity, p, features = authored_model("logistic", missing=True)
    result = local_attribution(model, identity, p, features)
    assert result.contributions[0].actual_value is None
    assert (
        result.contributions[0].imputed
        and result.contributions[0].raw_availability == "UNAVAILABLE"
    )
    assert result.contributions[0].effective_value == model.named_steps["imputer"].statistics_[0]


def test_local_positive_negative_values_trace_to_selected_predictions() -> None:
    from alphalens_decision.ranking import score

    cm, ci, cp, features = authored_model("logistic")
    rm, ri, rp, _ = authored_model("ridge", "regression")
    _, ranking, risk = with_features(*evidence())
    predictions = (cp, rp)
    updated_risk = sealed(
        RiskSnapshot,
        "risk_snapshot_id",
        **dict(
            risk.model_dump(exclude={"risk_snapshot_id"}),
            prediction_evidence_ids=tuple(p.evidence_id for p in predictions),
            model_run_ids=tuple(p.model_run_id for p in predictions),
            evaluation_ids=(cp.evaluation_id,),
        ),
    )
    parts, raw, penalties, adjusted = score(
        cp.probability, rp.prediction, 0.75, updated_risk, ranking.policy
    )
    candidate = ranking.ranked[0].model_copy(
        update=dict(
            probability=cp.probability,
            predicted_return=rp.prediction,
            components=parts,
            raw_opportunity_score=raw,
            penalties=penalties,
            risk_adjusted_score=adjusted,
            risk_snapshot_id=updated_risk.risk_snapshot_id,
            prediction_evidence_ids=updated_risk.prediction_evidence_ids,
            model_run_ids=updated_risk.model_run_ids,
            evaluation_ids=updated_risk.evaluation_ids,
        )
    )
    ranking = sealed(
        RankSnapshot,
        "rank_snapshot_id",
        **dict(
            ranking.model_dump(exclude={"rank_snapshot_id"}),
            ranked=(candidate,),
            risk_snapshot_ids=(updated_risk.risk_snapshot_id,),
        ),
    )
    signal = evaluate(ranking, "TEST:A", (updated_risk,), demo())
    attributes = (local_attribution(cm, ci, cp, features), local_attribution(rm, ri, rp, features))
    result = explain(signal, ranking, (updated_risk,), features, attributions=attributes)
    local_positive = [f for f in result.positive_factors if f.code.startswith("LOCAL_")]
    local_negative = [f for f in result.negative_factors if f.code.startswith("LOCAL_")]
    assert local_positive and local_negative
    assert all(f.evidence["contribution"] > 0 for f in local_positive)
    assert all(f.evidence["contribution"] < 0 for f in local_negative)
    assert all(
        f.source_reference in {a.attribution_id for a in attributes}
        for f in (*local_positive, *local_negative)
    )
    assert any("63.2" in f.text for f in (*local_positive, *local_negative))
    assert "LOCAL_ATTRIBUTION_UNAVAILABLE" not in {f.code for f in result.missing_evidence}
    assert result.model_evidence["probability"] == cp.probability
    with pytest.raises(DataContractError, match="AMBIGUOUS"):
        explain(
            signal, ranking, (updated_risk,), features, attributions=(attributes[0], attributes[0])
        )


def test_attribution_rejects_wrong_prediction_identity_and_future_training() -> None:
    model, identity, p, features = authored_model("logistic")
    wrong = p.model_copy(update=dict(probability=0.001))
    with pytest.raises(DataContractError, match="PREDICTION_REPLAY"):
        local_attribution(model, identity, wrong, features)
    with pytest.raises(DataContractError, match="LINEAGE"):
        local_attribution(model, dict(identity, model_family="ridge"), p, features)
    with pytest.raises(ValidationError):
        PredictionEvidence.model_validate(dict(p.model_dump(), training_cutoff=instant(65)))


def test_loader_requires_checksum_and_rejects_unreviewed_serialized_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphalens_data.normalization import checksum
    from alphalens_decision import explanation_models

    monkeypatch.chdir(tmp_path)
    model, identity, prediction, features = authored_model("logistic")
    p = prediction.model_copy(update=dict(origin="P9_FOLD_TEST"))
    directory = tmp_path / "data" / "TEST_ONLY_models"
    directory.mkdir(parents=True)
    model_path = directory / "models" / f"{p.model_run_id}.skops"
    model_path.parent.mkdir()
    model.unreviewed_extension = UnreviewedTestOnlyObject()
    content = sio.dumps(model)
    model_path.write_bytes(content)
    manifest = dict(
        fold_models={p.model_run_id: identity}, evaluation_id=p.evaluation_id, checksums={}
    )
    monkeypatch.setattr(explanation_models, "load", lambda _: SimpleNamespace(manifest=manifest))
    with pytest.raises(DataContractError, match="CHECKSUM_REQUIRED"):
        from_p9(directory, p, features)
    manifest["checksums"][f"models/{p.model_run_id}.skops"] = checksum(content)
    with pytest.raises(DataContractError, match="UNREVIEWED_MODEL_TYPES"):
        from_p9(directory, p, features)


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_layers_actual_values_risk_rank_horizon_and_lineage(horizon: Any) -> None:
    features, ranking, risk = with_features(*evidence(horizon=horizon))
    signal = evaluate(ranking, "TEST:A", (risk,), demo(horizon))
    result = explain(signal, ranking, (risk,), features)
    assert result.state == "SETUP_FORMING" and result.horizon == horizon
    assert result.feature_values["rsi_14"]["value"] == 63.2
    assert result.feature_values["momentum_percentile_20"]["value"] == 0.75
    assert result.risk_factors["components"] == {
        n: c.model_dump(mode="json") for n, c in risk.components.items()
    }
    breakdown = result.ranking_breakdown
    assert sum(breakdown["weighted_raw_contributions"].values()) == pytest.approx(signal.raw_score)
    assert breakdown["raw_score"] - sum(breakdown["penalties"].values()) == pytest.approx(
        signal.risk_adjusted_score
    )
    assert breakdown["threshold_status"] == "DEVELOPMENT_ASSUMPTION"
    assert result.invalidation_conditions == signal.invalidation_conditions
    assert result.state_transition_conditions["confirmation"] == dict(observed=1, required=2)
    assert "MODEL ESTIMATE — NOT GUARANTEED" in " ".join(result.plain_language_summary)
    assert result.plain_language_summary[0] == "TEST_ONLY — NOT A PERFORMANCE CLAIM"
    assert {f.code for f in result.positive_factors} == set(signal.positive_reasons)
    assert {f.code for f in result.negative_factors} == set(signal.negative_reasons)
    assert all(f.source_reference == signal.signal_snapshot_id for f in result.positive_factors)
    for name in (
        "signal_snapshot_id",
        "ranking_snapshot_id",
        "risk_snapshot_id",
        "feature_set_id",
        "canonical_input_id",
        "canonical_dataset_id",
        "universe_snapshot_id",
        "prediction_ids",
        "model_run_ids",
        "evaluation_ids",
        "signal_policy_id",
        "ranking_policy_id",
    ):
        assert result.lineage[name] is not None
    assert result.data_freshness["scope"] == "HISTORICAL_EOD_NOT_LIVE"
    assert result.model_evidence["global_importance"] == "UNAVAILABLE_NOT_USED_AS_LOCAL"
    assert result == explain(signal, ranking, (risk,), features)


def test_missing_evidence_and_no_hallucinated_causal_or_news_claims() -> None:
    ranking, risk = evidence(severity=0.9, corporate=True)
    signal = evaluate(ranking, "TEST:A", (risk,), demo())
    result = explain(signal, ranking, (risk,))
    missing = {f.code: f.text for f in result.missing_evidence}
    assert missing["FUNDAMENTAL_PIT_UNAVAILABLE"] == "Fundamental PIT analysis unavailable."
    assert {
        "NEWS_UNAVAILABLE",
        "BENCHMARK_UNAVAILABLE",
        "LIVE_INTRADAY_UNAVAILABLE",
        "CORPORATE_ACTION_COVERAGE_NOT_ESTABLISHED",
        "LOCAL_ATTRIBUTION_UNAVAILABLE",
    } <= set(missing)
    assert result.risk_factors["components"]["volatility_risk"]["level"] == "VERY_HIGH"
    texts = " ".join(
        (
            *result.plain_language_summary,
            *(f.text for f in result.positive_factors),
            *(f.text for f in result.negative_factors),
        )
    ).lower()
    for unsupported in (
        "caused the stock",
        "investors are optimistic",
        "earnings growth",
        "sector strength",
        "you will earn",
        "guaranteed stop",
    ):
        assert unsupported not in texts
    assert "risk" in result.state_transition_conditions["why_not_entry"]


@pytest.mark.parametrize(
    "context,state",
    [
        (None, "ENTRY_SIGNAL"),
        ("active", "HOLD"),
        ("review", "TAKE_PROFIT_REVIEW"),
        ("poor", "EXIT_SIGNAL"),
        ("exited", "EXITED"),
    ],
)
def test_signal_context_explanation_and_price_free_annotation(
    context: str | None, state: str
) -> None:
    ranking, risk = evidence(severity=0.9 if context == "poor" else 0.1)
    positions = (
        ()
        if context is None
        else (
            position(
                profit_review_requested=context == "review",
                exit_at=instant(59, 10) if context == "exited" else None,
            ),
        )
    )
    signal = evaluate(
        ranking, "TEST:A", (risk,), demo(confirmation_observations=1), positions=positions
    )
    result = explain(signal, ranking, (risk,))
    assert result.state == state
    annotation = result.annotation().model_dump(mode="json")
    assert annotation["signal_snapshot_id"] == signal.signal_snapshot_id
    assert annotation["explanation_id"] == result.explanation_id
    assert "price" not in annotation and annotation["classification"] == "TEST_ONLY"


def test_future_risk_history_and_attribution_do_not_change_earlier_explanation() -> None:
    features, ranking, risk = with_features(*evidence())
    signal = evaluate(ranking, "TEST:A", (risk,), demo())
    future, future_risk = evidence(65)
    future_signal = evaluate(future, "TEST:A", (future_risk,), demo())
    model, identity, prediction, model_features = authored_model("logistic")
    local = local_attribution(model, identity, prediction, model_features)
    # A future local attribution is filtered before validation/identity use.
    later = local.model_copy(
        update=dict(
            prediction=prediction.model_copy(
                update=dict(
                    session_date=day(65), decision_time=instant(65), available_at=instant(65)
                )
            )
        )
    )
    earlier = explain(signal, ranking, (risk,), features)
    assert earlier == explain(
        signal, ranking, (risk, future_risk), features, (future_signal,), (later,)
    )
    assert (
        explain(
            signal, ranking, (risk,), features, policy=ExplanationPolicy(revision="next")
        ).explanation_id
        != earlier.explanation_id
    )


def test_wrong_ranking_features_history_or_attribution_rejected() -> None:
    features, ranking, risk = with_features(*evidence())
    signal = evaluate(ranking, "TEST:A", (risk,), demo())
    different, other_risk = evidence(61)
    with pytest.raises(DataContractError, match="REPLAY"):
        explain(signal, different, (other_risk,), features)
    changed = features.model_copy(
        update=dict(
            rows=(
                features.rows[0].model_copy(
                    update=dict(
                        values=dict(
                            features.rows[0].values,
                            rsi_14=FeatureValue(value=99, state="AVAILABLE"),
                        )
                    )
                ),
            )
        )
    )
    with pytest.raises(DataContractError, match="CHECKSUM"):
        explain(signal, ranking, (risk,), changed)
    model, identity, p, model_features = authored_model("logistic")
    attribution = local_attribution(model, identity, p, model_features)
    with pytest.raises(DataContractError, match="ATTRIBUTION_LINEAGE"):
        explain(signal, ranking, (risk,), features, attributions=(attribution,))


def test_immutable_storage_annotation_checksum_and_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ranking, risk = evidence()
    signal = evaluate(ranking, "TEST:A", (risk,), demo())
    result = explain(signal, ranking, (risk,))
    directory = save(result, tmp_path / "data")
    assert load(directory) == result and save(result, tmp_path / "data") == directory
    for changes in (
        dict(classification="PRODUCTION"),
        dict(plain_language_summary=("You will earn",)),
        dict(production_claims_permitted=True),
    ):
        with pytest.raises(ValidationError):
            ExplainabilitySnapshot.model_validate(dict(result.model_dump(), **changes))
    (directory / "chart-annotation.json").write_bytes(b"{}")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(directory)
