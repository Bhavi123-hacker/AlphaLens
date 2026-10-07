"""Actual P2–P7 replay with later revisions/listings/actions hidden from early P9 folds."""

from pathlib import Path

import numpy as np
from scripts.build_p6_test_fixture import START, day, instant

from alphalens_data.canonical.assembly import EvidenceAssembly
from alphalens_data.canonical.models import (
    ActionRevision,
    CanonicalBatch,
    MembershipRevision,
    Revision,
    revision_key,
)
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.universe.models import SecurityType
from alphalens_evaluation.contracts import Fold, WalkForwardDefinition
from alphalens_evaluation.engine import evaluate
from alphalens_features.engine import build as build_features
from alphalens_features.models import BuildPlan, Decision, FeatureDataset
from alphalens_labels.alignment import SupervisedDataset, align
from alphalens_labels.engine import build as build_labels
from alphalens_labels.models import LabelPlan


def append_reference(batch: CanonicalBatch, record: Revision, root: Path) -> CanonicalBatch:
    assembly = EvidenceAssembly(root, Classification.TEST_ONLY)
    assembly.reference(record)
    artifact = next(a for a in batch.artifacts if a.sha256 == record.provenance.artifact_sha256)
    assembly.link_reference(record, artifact, {"evidence_sha256": artifact.sha256})
    return batch.model_copy(
        update=dict(
            revisions=(*batch.revisions, record),
            artifacts=(*batch.artifacts, *assembly.artifacts.values()),
            normalized=tuple(
                {
                    n.normalized_record_id: n
                    for n in (*batch.normalized, *assembly.normalized.values())
                }.values()
            ),
            lineage=(*batch.lineage, *assembly.lineage),
        )
    )


def early_inputs(
    batch: CanonicalBatch,
) -> tuple[FeatureDataset, SupervisedDataset, dict[str, SupervisedDataset]]:
    reader = CanonicalReader(batch)
    data = {}
    scoring_features = None
    for key, cutoff, decisions in (
        ("fold-1", 27, (20, 24)),
        ("fold-2", 31, (20, 24, 28)),
        ("scoring", 34, (20, 24, 28, 32)),
    ):
        features = build_features(
            reader,
            BuildPlan(
                history_start=START,
                decisions=tuple(
                    Decision(session_date=day(i), knowledge_cutoff=instant(i, 12))
                    for i in decisions
                ),
            ),
        )
        labels = build_labels(
            reader,
            features,
            LabelPlan(outcome_cutoff=instant(cutoff, 12), outcome_end=day(cutoff), horizons=(1,)),
        )
        data[key] = align(
            features,
            labels,
            horizon=1,
            training_as_of=instant(cutoff, 12),
            feature_columns=("return_1", "sma_5"),
            allow_degraded=True,
        )
        if key == "scoring":
            scoring_features = features
    assert scoring_features is not None
    return scoring_features, data["scoring"], {k: data[k] for k in ("fold-1", "fold-2")}


def test_future_actions_constituent_revision_listing_and_observations_leave_early_models_unchanged(
    tmp_path: Path,
) -> None:
    # Share the already generated P9 module fixture through pytest's fixture namespace
    # is deliberately avoided: this focused replay builds a short independent history.
    from scripts.build_p6_test_fixture import build_history
    from scripts.build_p8_test_fixture import overrides

    batch = build_history(
        tmp_path / "canonical", length=40, overrides=overrides(40), revision=(29, 80, "999")
    )[0]
    old = next(
        r
        for r in batch.revisions
        if isinstance(r, MembershipRevision) and r.security_id == "TEST:ALPHA"
    )
    provenance = old.provenance.model_copy(update={"available_at": instant(80)})
    fact = old.fact.model_copy(
        update=dict(
            revision_id="r2",
            supersedes_revision_id="r1",
            security_type=SecurityType.ETF,
            provenance=provenance,
        )
    )
    revised = old.model_copy(
        update=dict(
            revision_id="r2",
            revision_number=2,
            supersedes_revision_id="r1",
            provenance=provenance,
            fact=fact,
        )
    )
    future = append_reference(batch, revised, tmp_path / "future-membership")
    action = ActionRevision(
        logical_record_id="TEST_ONLY_LATE_ACTION",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:ALPHA",
        effective_from=day(25),
        provenance=provenance,
        corporate_action_id="TEST_ONLY_LATE_ACTION",
        event_type="SPLIT",
        ex_date=day(25),
        factor="2",
    )
    future = append_reference(future, action, tmp_path / "future-action")
    revisions = tuple(r for r in future.revisions if r.effective_from < day(35))
    keys = {revision_key(r) for r in revisions}
    future = future.model_copy(
        update=dict(
            revisions=revisions,
            lineage=tuple(link for link in future.lineage if link.record_key in keys),
        )
    )
    # P10 additionally compares a late price correction against the original vintage.
    original_revisions = tuple(r for r in batch.revisions if r.revision_number == 1)
    original_keys = {revision_key(r) for r in original_revisions}
    batch = batch.model_copy(
        update=dict(
            revisions=original_revisions,
            lineage=tuple(link for link in batch.lineage if link.record_key in original_keys),
        )
    )
    outputs = []
    economic_outputs = []
    risk_outputs = []
    rank_outputs = []
    signal_outputs = []
    explanation_outputs = []
    for candidate in (batch, future):
        features, scoring, training = early_inputs(candidate)
        plan = WalkForwardDefinition(
            feature_set_id=scoring.feature_set_id,
            label_set_id=scoring.label_set_id,
            canonical_dataset_id=features.canonical_dataset_id,
            supervised_dataset_id=scoring.supervised_dataset_id,
            training_dataset_ids={k: v.supervised_dataset_id for k, v in training.items()},
            task="classification",
            horizon=1,
            model_families=("logistic",),
            folds=(
                Fold(
                    fold_id="fold-1",
                    training_cutoff=instant(27, 12),
                    test_start=day(28),
                    test_end=day(28),
                ),
                Fold(
                    fold_id="fold-2",
                    training_cutoff=instant(31, 12),
                    test_start=day(32),
                    test_end=day(32),
                ),
            ),
            minimum_training_rows=2,
            minimum_test_rows=2,
            data_classification=Classification.TEST_ONLY,
        )
        result = evaluate(scoring, features, plan, training)
        assert all(r.security_id != "TEST:NEW" for r in result.predictions)
        assert len(result.predictions) >= 6
        outputs.append(result)
        from scripts.build_p10_test_inputs import calendar

        from alphalens_backtesting.contracts import BacktestDefinition, scenarios
        from alphalens_backtesting.engine import run
        from alphalens_backtesting.evidence import ExecutionEvidence
        from alphalens_evaluation.storage import OOSDataset

        evidence = ExecutionEvidence(CanonicalReader(candidate), features, calendar(candidate))
        backtest = BacktestDefinition(
            evaluation_id=result.manifest["evaluation_id"],
            oos_prediction_dataset_id=result.manifest["oos_prediction_dataset_id"],
            canonical_input_id=candidate.input_id,
            feature_set_id=features.feature_set_id,
            execution_calendar_id=evidence.calendar.calendar_id,
            universe_definition_id=candidate.definition.universe_id,
            model_family="logistic",
            horizon=1,
            start_session=day(28),
            end_session=day(34),
            costs=scenarios()[1],
            data_classification=Classification.TEST_ONLY,
        )
        economics = run(OOSDataset(result.manifest, result.predictions), evidence, backtest)
        assert economics.trades and all(r["security_id"] != "TEST:NEW" for r in economics.trades)
        assert all(
            r["corporate_action_state"] == "COVERAGE_NOT_ESTABLISHED" for r in economics.trades
        )
        economic_outputs.append(economics)
        from alphalens_decision.evidence import project
        from alphalens_decision.risk import RiskEngine

        risk = RiskEngine(
            CanonicalReader(candidate),
            features,
            project(OOSDataset(result.manifest, result.predictions), result.fold_metrics),
        )
        risk_outputs.append(risk.evaluate("TEST:ALPHA", day(32), 1))
        from alphalens_decision.ranking import RankingEngine
        from alphalens_decision.ranking_contracts import RankingPolicy

        rank_outputs.append(RankingEngine(risk).evaluate(day(32), RankingPolicy(horizon=1)))
        from alphalens_decision.signal_contracts import SignalPolicy
        from alphalens_decision.signals import evaluate as evaluate_signal

        signal_outputs.append(
            evaluate_signal(
                rank_outputs[-1], "TEST:ALPHA", (risk_outputs[-1],), SignalPolicy(horizon=1)
            )
        )
        from alphalens_decision.explanations import explain

        explanation_outputs.append(
            explain(signal_outputs[-1], rank_outputs[-1], (risk_outputs[-1],), features)
        )
    assert [(r.session_date, r.security_id, r.probability) for r in outputs[0].predictions] == [
        (r.session_date, r.security_id, r.probability) for r in outputs[1].predictions
    ]
    for left, right in zip(
        outputs[0].fold_models.values(), outputs[1].fold_models.values(), strict=True
    ):
        np.testing.assert_array_equal(
            left.named_steps["imputer"].statistics_, right.named_steps["imputer"].statistics_
        )
        np.testing.assert_array_equal(
            left.named_steps["estimator"].coef_, right.named_steps["estimator"].coef_
        )
    assert economic_outputs[0].equity == economic_outputs[1].equity
    assert risk_outputs[0].components == risk_outputs[1].components
    assert risk_outputs[0].overall_level == risk_outputs[1].overall_level
    assert risk_outputs[0].reasons == risk_outputs[1].reasons
    assert signal_outputs[0].state == signal_outputs[1].state
    assert signal_outputs[0].positive_reasons == signal_outputs[1].positive_reasons
    assert signal_outputs[0].negative_reasons == signal_outputs[1].negative_reasons
    assert signal_outputs[0].entry_conditions == signal_outputs[1].entry_conditions
    assert signal_outputs[0].symbol == signal_outputs[1].symbol
    assert (
        explanation_outputs[0].plain_language_summary
        == explanation_outputs[1].plain_language_summary
    )
    assert explanation_outputs[0].risk_factors == explanation_outputs[1].risk_factors
    assert [(f.code, f.text) for f in explanation_outputs[0].positive_factors] == [
        (f.code, f.text) for f in explanation_outputs[1].positive_factors
    ]
    assert [(f.code, f.text) for f in explanation_outputs[0].negative_factors] == [
        (f.code, f.text) for f in explanation_outputs[1].negative_factors
    ]
    assert {
        name: (v["value"], v["availability"], v["reasons"])
        for name, v in explanation_outputs[0].feature_values.items()
    } == {
        name: (v["value"], v["availability"], v["reasons"])
        for name, v in explanation_outputs[1].feature_values.items()
    }
    assert [(r.security_id, r.risk_adjusted_score) for r in rank_outputs[0].ranked] == [
        (r.security_id, r.risk_adjusted_score) for r in rank_outputs[1].ranked
    ]
    assert [(r.security_id, r.reasons) for r in rank_outputs[0].excluded] == [
        (r.security_id, r.reasons) for r in rank_outputs[1].excluded
    ]
    assert all(r.security_id != "TEST:NEW" for r in rank_outputs[0].ranked)
    economic_fields = (
        "security_id",
        "entry_session",
        "exit_session",
        "entry_price",
        "exit_price",
        "quantity",
        "total_costs",
        "net_pnl",
    )
    assert [tuple(t[k] for k in economic_fields) for t in economic_outputs[0].trades] == [
        tuple(t[k] for k in economic_fields) for t in economic_outputs[1].trades
    ]
