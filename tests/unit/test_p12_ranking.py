"""TEST_ONLY ranking arithmetic, full-universe gating and historical evidence boundaries."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p6_test_fixture import day, instant

from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_decision.comparison import (
    ComparisonEvidence,
    EconomicEvidence,
    FoldMetrics,
)
from alphalens_decision.evidence import project
from alphalens_decision.models import Horizon, ModelDiagnostic, ModelEvidence, PredictionEvidence
from alphalens_decision.ranking import RankingEngine, score
from alphalens_decision.ranking_contracts import RankingPolicy, RankSnapshot
from alphalens_decision.ranking_storage import load, save
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_contracts import RiskComponent, RiskSnapshot, level
from alphalens_evaluation.contracts import digest
from alphalens_evaluation.storage import OOSDataset


@pytest.fixture(scope="module")
def ranker(evaluation_source: Any) -> RankingEngine:
    batch, features, _, _ = evaluation_source
    predictions = []
    diagnostics = {}
    for row in features.rows:
        for horizon in (1, 5, 10, 20):
            for task, family in (("classification", "logistic"), ("regression", "ridge")):
                p = PredictionEvidence.model_validate(
                    dict(
                        origin="TEST_ONLY_AUTHORED",
                        evaluation_id=digest((task, horizon)),
                        model_run_id=digest((family, horizon)),
                        family=family,
                        task=task,
                        horizon=horizon,
                        security_id=row.security_id,
                        session_date=row.session_date,
                        decision_time=row.decision_time,
                        available_at=row.decision_time,
                        training_cutoff=instant(-1),
                        feature_set_id=features.feature_set_id,
                        canonical_dataset_id=row.canonical_dataset_id,
                        universe_snapshot_id=row.universe_snapshot_id,
                        prediction=0.02 if task == "regression" else 1,
                        probability=0.8 if task == "classification" else None,
                        classification="TEST_ONLY",
                    )
                )
                predictions.append(p)
                diagnostics[task, horizon] = ModelDiagnostic.model_validate(
                    dict(
                        origin="TEST_ONLY_AUTHORED",
                        evaluation_id=p.evaluation_id,
                        model_run_id=p.model_run_id,
                        family=family,
                        task=task,
                        horizon=horizon,
                        fold_id="TEST_ONLY completed fold",
                        period_end=day(44),
                        available_at=instant(48),
                        report_checksum=digest((task, horizon, "report")),
                        sample_count=30,
                        primary_metric=0.1,
                        naive_improvement=-0.01,
                        brier_score=0.1 if task == "classification" else None,
                        calibration_available=False,
                        classification="TEST_ONLY",
                    )
                )
    models = ModelEvidence(
        classification="TEST_ONLY",
        predictions=tuple(predictions),
        diagnostics=tuple(diagnostics.values()),
    )
    return RankingEngine(RiskEngine(CanonicalReader(batch), features, models))


def altered_risk(source: RiskSnapshot, severity: float, uncertainty: float) -> RiskSnapshot:
    data = source.model_dump(mode="json", exclude={"risk_snapshot_id"})
    for name, c in source.components.items():
        value = uncertainty if name == "model_uncertainty" else severity
        component = RiskComponent(
            metrics=c.metrics,
            severity=value,
            level=level(value),
            availability="DEGRADED",
            reasons=c.reasons,
        )
        data["components"][name] = component.model_dump(mode="json")
    data["overall_level"] = level(max(severity, uncertainty))
    return RiskSnapshot.model_validate(dict(risk_snapshot_id=digest(data), **data))


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_complete_rank_replay_horizon_and_exclusions(
    ranker: RankingEngine, horizon: Horizon
) -> None:
    policy = RankingPolicy(horizon=horizon)
    result = ranker.evaluate(day(60), policy)
    assert result == ranker.evaluate(day(60), policy)
    assert len(result.ranked) >= 3
    assert result.excluded
    assert ({r.security_id for r in result.ranked} | {r.security_id for r in result.excluded}) == {
        r.security_id for r in ranker.risk.features.rows if r.session_date == day(60)
    }
    assert all(r.horizon == horizon for r in result.ranked)
    assert result.top(1) == result.ranked[:1]
    assert len(result.top(20)) == len(result.ranked)
    assert result.model_selection_status == "TEST_ONLY_SELECTED_CANDIDATE"
    assert "TEST_ONLY" in result.disclaimer and "NOT A PERFORMANCE CLAIM" in result.disclaimer


def test_ties_use_security_id_and_top_n_never_changes_identity(ranker: RankingEngine) -> None:
    result = ranker.evaluate(
        day(60),
        RankingPolicy(horizon=5, context_weight=0, probability_weight=0.5, return_weight=0.5),
    )
    tied: dict[float, list[str]] = {}
    for row in result.ranked:
        tied.setdefault(row.risk_adjusted_score, []).append(row.security_id)
    assert any(len(group) >= 2 for group in tied.values())
    assert all(group == sorted(group) for group in tied.values())
    assert result.top(5) == result.top(10)
    with pytest.raises(ValueError):
        result.top(0)


def test_changing_one_horizon_cannot_change_another(ranker: RankingEngine) -> None:
    assert ranker.risk.models is not None
    models = ranker.risk.models
    predictions = tuple(
        PredictionEvidence.model_validate(dict(p.model_dump(), probability=0.1, prediction=0))
        if p.horizon == 20 and p.task == "classification"
        else p
        for p in models.predictions
    )
    altered = RankingEngine(
        RiskEngine(
            ranker.risk.reader,
            ranker.risk.features,
            ModelEvidence(
                classification="TEST_ONLY", predictions=predictions, diagnostics=models.diagnostics
            ),
        )
    )
    assert ranker.evaluate(day(60), RankingPolicy(horizon=5)) == altered.evaluate(
        day(60), RankingPolicy(horizon=5)
    )
    assert (
        ranker.evaluate(day(60), RankingPolicy(horizon=20)).rank_snapshot_id
        != altered.evaluate(day(60), RankingPolicy(horizon=20)).rank_snapshot_id
    )


def test_risk_and_uncertainty_materially_penalize_optimistic_prediction(
    ranker: RankingEngine,
) -> None:
    base = ranker.risk.evaluate("TEST:ALPHA", day(60), 5)
    low = altered_risk(base, 0.05, 0.05)
    high = altered_risk(base, 1, 1)
    policy = RankingPolicy(horizon=5)
    assert score(0.65, 0.01, 0.5, low, policy)[3] > score(0.95, 0.10, 0.5, high, policy)[3]
    assert (
        score(0.8, 0.01, 0.5, altered_risk(base, 0.05, 1), policy)[2]["uncertainty"]
        > score(0.8, 0.01, 0.5, low, policy)[2]["uncertainty"]
    )


def test_missing_return_is_explicit_not_neutral_and_units_are_normalized(
    ranker: RankingEngine,
) -> None:
    base = ranker.risk.evaluate("TEST:ALPHA", day(60), 5)
    components, raw, penalties, adjusted = score(0.8, None, None, base, RankingPolicy(horizon=5))
    assert components["normalized_return"] is None
    assert raw == 0.8
    assert penalties["missing_components"] == 0.1
    assert adjusted == pytest.approx(raw - sum(penalties.values()))
    zero = score(None, 0.0, None, base, RankingPolicy(horizon=5))
    assert (
        zero[0]["normalized_return"] == 0.5
    )  # evidenced zero-return prediction, not imputed absence


def test_configured_model_mapping_never_picks_optimistic_alternative(ranker: RankingEngine) -> None:
    assert ranker.risk.models is not None
    baseline = ranker.evaluate(day(60), RankingPolicy(horizon=5))
    extras = tuple(
        PredictionEvidence.model_validate(
            dict(
                p.model_dump(),
                family="random_forest",
                model_run_id=digest("other"),
                probability=0.999,
                prediction=1,
            )
        )
        for p in ranker.risk.models.predictions
        if p.task == "classification"
    )
    modified = RankingEngine(
        RiskEngine(
            ranker.risk.reader,
            ranker.risk.features,
            ModelEvidence(
                classification="TEST_ONLY",
                predictions=(*ranker.risk.models.predictions, *extras),
                diagnostics=ranker.risk.models.diagnostics,
            ),
        )
    )
    result = modified.evaluate(day(60), RankingPolicy(horizon=5))
    assert [r.probability for r in result.ranked] == [r.probability for r in baseline.ranked]
    assert all(digest("other") not in r.model_run_ids for r in result.ranked)
    assert (
        result.rank_snapshot_id != baseline.rank_snapshot_id
    )  # disclosed consensus uncertainty changed


def test_future_predictions_diagnostics_and_risks_are_invisible(ranker: RankingEngine) -> None:
    assert ranker.risk.models is not None
    models = ranker.risk.models
    early = ModelEvidence(
        classification="TEST_ONLY",
        predictions=tuple(p for p in models.predictions if p.session_date <= day(60)),
        diagnostics=models.diagnostics,
    )
    first = RankingEngine(RiskEngine(ranker.risk.reader, ranker.risk.features, early)).evaluate(
        day(60), RankingPolicy(horizon=5)
    )
    late = ModelDiagnostic.model_validate(
        dict(
            next(d for d in models.diagnostics if d.horizon == 5).model_dump(),
            fold_id="future",
            available_at=instant(85),
            report_checksum=digest("future report"),
        )
    )
    future = RankingEngine(
        RiskEngine(
            ranker.risk.reader,
            ranker.risk.features,
            ModelEvidence(
                classification="TEST_ONLY",
                predictions=models.predictions,
                diagnostics=(*models.diagnostics, late),
            ),
        )
    )
    risks = tuple(
        future.risk.evaluate(row.security_id, row.session_date, 5)
        for row in ranker.risk.features.rows
        if row.session_date in (day(60), day(68))
    )
    assert future.evaluate(day(60), RankingPolicy(horizon=5), risks) == first


def test_risk_artifact_mismatch_and_absence_do_not_assume_low(ranker: RankingEngine) -> None:
    missing = ranker.evaluate(day(60), RankingPolicy(horizon=5), ())
    assert not missing.ranked
    assert all("RISK_UNAVAILABLE" in r.reasons for r in missing.excluded)
    altered = altered_risk(ranker.risk.evaluate("TEST:ALPHA", day(60), 5), 0.01, 0.01)
    with pytest.raises(DataContractError, match="RISK_EVIDENCE"):
        ranker.evaluate(day(60), RankingPolicy(horizon=5), (altered,))


def test_historical_universe_and_insufficient_history_keep_exclusions(
    ranker: RankingEngine,
) -> None:
    result = ranker.evaluate(day(16), RankingPolicy(horizon=5))
    assert not result.ranked
    by_security = {r.security_id: r.reasons for r in result.excluded}
    assert "TEST:NEW" not in by_security  # no contemporaneous evidence of existence
    assert "INSUFFICIENT_HISTORY" in by_security["TEST:ALPHA"]


def test_rank_history_uses_only_past_compatible_snapshot(ranker: RankingEngine) -> None:
    policy = RankingPolicy(horizon=5)
    past = ranker.evaluate(day(56), policy)
    future = ranker.evaluate(day(68), policy)
    current = ranker.evaluate(day(60), policy, history=(past,))
    assert current == ranker.evaluate(day(60), policy, history=(future, past))
    previous = {r.security_id: r.rank for r in past.ranked}
    for r in current.ranked:
        assert r.previous_rank == previous.get(r.security_id)
        if r.previous_rank is not None:
            assert r.rank_change == r.previous_rank - r.rank
    incompatible = ranker.evaluate(day(56), RankingPolicy(horizon=1))
    assert ranker.evaluate(day(60), policy, history=(incompatible,)).previous_snapshot_id is None


def test_policy_identity_and_production_classification_guards(ranker: RankingEngine) -> None:
    first = ranker.evaluate(day(60), RankingPolicy(horizon=5))
    second = ranker.evaluate(day(60), RankingPolicy(horizon=5, return_scale=0.1))
    assert first.rank_snapshot_id != second.rank_snapshot_id
    with pytest.raises(ValidationError):
        RankSnapshot.model_validate(dict(first.model_dump(), classification="PRODUCTION"))
    with pytest.raises(ValidationError):
        RankingPolicy(horizon=5, risk_penalty_weight=0)
    with pytest.raises(ValidationError):
        FoldMetrics(diagnostic_id=digest("x"), metrics={"actual_target": 1})


def test_research_cannot_bypass_insufficient_selection_gate(ranker: RankingEngine) -> None:
    result = ranker.evaluate(day(60), RankingPolicy(horizon=5))
    data = result.model_dump(mode="json", exclude={"rank_snapshot_id"})
    data["classification"] = "RESEARCH_FIXTURE"
    data["disclaimer"] = "RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED"
    with pytest.raises(ValidationError, match="classification"):
        RankSnapshot.model_validate(dict(rank_snapshot_id=digest(data), **data))


def test_rank_artifacts_are_immutable_verified_and_complete(
    ranker: RankingEngine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = ranker.evaluate(day(60), RankingPolicy(horizon=5))
    directory = save(result, Path("data/ranks"))
    assert save(result, Path("data/ranks")) == directory
    assert load(directory) == result
    result.top(1)
    assert len(load(directory).ranked) == len(result.ranked)
    (directory / "rank-snapshot.json").write_bytes(stable_json({"tampered": True}))
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(directory)


def test_comparison_retains_weak_naive_performance_all_families(ranker: RankingEngine) -> None:
    result = ranker.evaluate(day(60), RankingPolicy(horizon=5))
    comparisons = result.model_comparison
    assert len(comparisons) == 12
    assert comparisons["classification:logistic"]["naive_improvement_mean"] < 0
    assert comparisons["classification:logistic"]["fraction_folds_beating_naive"] == 0
    assert comparisons["classification:xgboost"]["status"] == "UNAVAILABLE_AT_CUTOFF"
    assert all(not r["automatic_winner"] for r in comparisons.values())


def test_future_economic_report_does_not_change_rank_and_known_context_is_descriptive(
    ranker: RankingEngine,
) -> None:
    assert ranker.risk.models is not None
    prediction = next(p for p in ranker.risk.models.predictions if p.horizon == 5)
    economic = EconomicEvidence.model_validate(
        dict(
            origin="TEST_ONLY_AUTHORED",
            backtest_id=digest("past backtest"),
            evaluation_id=prediction.evaluation_id,
            oos_prediction_dataset_id=digest("OOS"),
            canonical_input_id=ranker.risk.reader.batch.input_id,
            feature_set_id=ranker.risk.features.feature_set_id,
            family=prediction.family,
            task=prediction.task,
            horizon=5,
            period_end=day(56),
            available_at=instant(57),
            cost_scenario="LOW_COST_ASSUMPTION",
            source_checksum=digest("summary"),
            net_return=-0.03,
            maximum_drawdown=-0.05,
            turnover=1.2,
            trade_count=4,
            unresolved_count=0,
            classification="TEST_ONLY",
        )
    )
    late = EconomicEvidence.model_validate(
        dict(
            economic.model_dump(),
            backtest_id=digest("future backtest"),
            period_end=day(80),
            available_at=instant(81),
            net_return=9,
        )
    )
    policy = RankingPolicy(horizon=5)
    plain = ranker.evaluate(day(60), policy)
    assert (
        RankingEngine(ranker.risk, ComparisonEvidence(economics=(late,))).evaluate(day(60), policy)
        == plain
    )
    known = RankingEngine(ranker.risk, ComparisonEvidence(economics=(economic,))).evaluate(
        day(60), policy
    )
    assert known.ranked == plain.ranked  # economics never select a more optimistic model
    assert (
        known.model_comparison[f"{prediction.task}:{prediction.family}"]["economics"][0][
            "net_return"
        ]
        == -0.03
    )
    assert known.rank_snapshot_id != plain.rank_snapshot_id


def test_quality_rejection_is_not_rank_eligible(tmp_path: Path) -> None:
    from scripts.build_p6_test_fixture import START, build_history

    from alphalens_features.engine import build
    from alphalens_features.models import BuildPlan, Decision

    batch = build_history(tmp_path, length=61, overrides={(60, "TEST:ALPHA"): {"close": ""}})[0]
    reader = CanonicalReader(batch)
    features = build(
        reader,
        BuildPlan(
            history_start=START,
            decisions=(Decision(session_date=day(60), knowledge_cutoff=instant(60, 12)),),
        ),
    )
    result = RankingEngine(RiskEngine(reader, features)).evaluate(day(60), RankingPolicy(horizon=5))
    alpha = next(r for r in result.excluded if r.security_id == "TEST:ALPHA")
    assert "DATA_QUALITY_REJECTED" in alpha.reasons


def test_verified_p9_p10_mapping_and_target_free_comparisons(
    evaluation_source: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.build_p10_test_inputs import calendar, definition
    from scripts.verify_p9_test_only import definition as evaluation_definition

    from alphalens_backtesting.contracts import scenarios
    from alphalens_backtesting.engine import run
    from alphalens_backtesting.evidence import ExecutionEvidence
    from alphalens_backtesting.storage import save as save_backtest
    from alphalens_decision.comparison import load_comparisons
    from alphalens_evaluation.engine import evaluate
    from alphalens_evaluation.storage import save as save_evaluation

    batch, features, aligned, training = evaluation_source
    plan = evaluation_definition(aligned[1], features, "classification", training[1]).model_copy(
        update={"model_families": ("logistic",)}
    )
    result = evaluate(aligned[1], features, plan, training[1])
    evidence = project(OOSDataset(result.manifest, result.predictions), result.fold_metrics)
    assert evidence.predictions
    assert all("actual_target" not in p.model_dump() for p in evidence.predictions)
    assert all(p.origin == "P9_FOLD_TEST" for p in evidence.predictions)
    monkeypatch.chdir(tmp_path)
    evaluation_path = save_evaluation(result, Path("data/evaluations"))
    execution = ExecutionEvidence(CanonicalReader(batch), features, calendar(batch))
    backtest = run(
        OOSDataset(result.manifest, result.predictions),
        execution,
        definition(
            OOSDataset(result.manifest, result.predictions),
            execution,
            "logistic",
            scenarios()[1],
            end_session=day(58),
        ),
    )
    backtest_path = save_backtest(backtest, Path("data/backtests"))
    comparisons = load_comparisons([evaluation_path], [backtest_path])
    assert comparisons.economics[0].task == "classification"
    assert comparisons.economics[0].origin == "P10_VERIFIED"
    engine = RankingEngine(RiskEngine(CanonicalReader(batch), features, evidence), comparisons)
    snapshot = engine.evaluate(day(60), RankingPolicy(horizon=1))
    assert snapshot.ranked
    summary = snapshot.model_comparison["classification:logistic"]
    assert summary["fold_count"] == 1
    assert "balanced_accuracy" in summary["metrics"]
    assert summary["economic_status"] == "DESCRIPTIVE_ONLY"
    assert (
        summary["ranking_status"] == "UNAVAILABLE_AT_CUTOFF"
    )  # later aggregate outcomes not mature
