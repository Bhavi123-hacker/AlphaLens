"""TEST_ONLY adversarial P8 contracts, scientific controls and P2-P7 integration."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import skops.io as sio
from scripts.build_p6_test_fixture import START, day, instant
from scripts.build_p8_test_fixture import config, prepare

from alphalens_data.canonical.assembly import EvidenceAssembly
from alphalens_data.canonical.models import (
    CanonicalBatch,
    IdentityRevision,
    MembershipRevision,
    Revision,
    Security,
    revision_key,
)
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.universe.models import SecurityType
from alphalens_features.engine import build as build_features
from alphalens_features.models import BuildPlan, Decision
from alphalens_labels.alignment import AlignedRow, SupervisedDataset, align
from alphalens_labels.engine import build as build_labels
from alphalens_labels.models import LabelPlan
from alphalens_training.artifacts import LocalRegistry, RegistryEntry
from alphalens_training.cli import model_main, train_main
from alphalens_training.contracts import TrainingConfig
from alphalens_training.engine import pipeline, train
from alphalens_training.metrics import classification_metrics, regression_metrics
from alphalens_training.split import split


@pytest.fixture(scope="module")
def source(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[CanonicalBatch, dict[int, SupervisedDataset]]:
    root = tmp_path_factory.mktemp("TEST_ONLY_p8")
    aligned = prepare(root)
    batch = CanonicalBatch.model_validate(
        json.loads((root / "canonical/canonical-input.json").read_bytes())["batch"]
    )
    return batch, aligned


@pytest.fixture(scope="module")
def aligned(
    source: tuple[CanonicalBatch, dict[int, SupervisedDataset]],
) -> dict[int, SupervisedDataset]:
    return source[1]


def repin(data: SupervisedDataset, **updates: Any) -> SupervisedDataset:
    data = data.model_copy(update=updates)
    return SupervisedDataset.model_validate(
        data.model_dump()
        | {
            "supervised_dataset_id": checksum(
                stable_json(data.model_dump(mode="json", exclude={"supervised_dataset_id"}))
            )
        }
    )


def changed(
    data: SupervisedDataset, transform: Callable[[AlignedRow], AlignedRow]
) -> SupervisedDataset:
    return repin(data, rows=tuple(transform(row) for row in data.rows))


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
def test_chronology_maturity_overlap_and_upstream_exclusions(
    aligned: dict[int, SupervisedDataset], horizon: int
) -> None:
    data = aligned[horizon]
    fold = split(data, config(horizon))
    assert all(
        m.session_date < day(52)
        and m.decision_time <= instant(51, 12)
        and m.label_available_at is not None
        and m.label_available_at <= instant(51, 12)
        for m in fold.train_metadata
    )
    assert all(day(52) <= m.session_date <= day(68) for m in fold.validation_metadata)
    assert not {m.session_date for m in fold.train_metadata} & {
        m.session_date for m in fold.validation_metadata
    }
    assert fold.excluded_rows + len(fold.y_train) + len(fold.y_validation) == len(data.rows)
    assert fold.exclusion_counts["FEATURE_UNAVAILABLE"] > 0
    assert fold.exclusion_counts["UNIVERSE_INELIGIBLE"] > 0
    if horizon > 1:
        assert fold.exclusion_counts["TARGET_OVERLAP_PURGED"] > 0
        assert fold.exclusion_counts["LABEL_AFTER_TRAINING_CUTOFF"] > 0
    assert fold.feature_columns == data.feature_columns


@pytest.mark.parametrize(
    ("task", "family"),
    [
        ("classification", "logistic"),
        ("classification", "random_forest"),
        ("classification", "hist_gradient_boosting"),
        ("regression", "ridge"),
        ("regression", "random_forest"),
        ("regression", "hist_gradient_boosting"),
    ],
)
def test_all_models_naive_comparisons_roundtrip_and_determinism(
    aligned: dict[int, SupervisedDataset],
    task: str,
    family: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    data, plan = aligned[5], config(5, task, family)
    first, second = train(data, plan), train(data, plan)
    assert first.manifest == second.manifest
    assert first.report == second.report
    np.testing.assert_allclose(
        first.model.predict(first.holdout.x_validation),
        second.model.predict(second.holdout.x_validation),
        rtol=0,
        atol=0,
    )
    assert len(first.report["naive_metrics"]) == 2
    assert first.report["comparisons"]
    assert first.report["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert first.report["top_k"]["status"] == "UNAVAILABLE_P8_DISABLED"
    registry = LocalRegistry(Path("data/models"))
    entry = registry.save(first)
    assert registry.save(second) == entry
    assert registry.evaluate(entry.model_run_id, data) == json.loads(stable_json(first.report))
    assert entry.status == "TEST_ONLY" and entry.classification == "TEST_ONLY"
    _, manifest, _, _ = registry.verify(entry.model_run_id)
    identity = manifest["identity"]
    assert identity["supervised_dataset_id"] == data.supervised_dataset_id
    assert identity["feature_set_id"] == data.feature_set_id
    assert identity["label_set_id"] == data.label_set_id
    assert manifest["feature_order"] == list(first.holdout.feature_columns)
    assert first.report["disclaimer"] == "TEST_ONLY — NOT A PERFORMANCE CLAIM"
    assert first.report["production_claims_permitted"] is False


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
@pytest.mark.parametrize(
    ("task", "family"), [("classification", "logistic"), ("regression", "ridge")]
)
def test_independent_per_horizon_training(
    aligned: dict[int, SupervisedDataset], horizon: int, task: str, family: str
) -> None:
    result = train(aligned[horizon], config(horizon, task, family))
    assert result.report["horizon"] == horizon and result.report["task"] == task


def test_validation_features_targets_never_fit_preprocessing(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]

    def mutate(row: AlignedRow) -> AlignedRow:
        if str(row.metadata["session_date"]) < day(52).isoformat():
            return row
        targets = dict(row.targets)
        if targets["target_forward_return_5"] is not None:
            targets.update(target_forward_return_5="-0.4", target_direction_5=0)
        return row.model_copy(
            update={"features": {k: 1e6 for k in row.features}, "targets": targets}
        )

    changed_data = changed(data, mutate)
    first, second = train(data, config()), train(changed_data, config())
    np.testing.assert_array_equal(first.holdout.x_train, second.holdout.x_train)
    np.testing.assert_array_equal(first.holdout.y_train, second.holdout.y_train)
    for name, attribute in (("imputer", "statistics_"), ("scaler", "mean_"), ("scaler", "scale_")):
        np.testing.assert_array_equal(
            getattr(first.model.named_steps[name], attribute),
            getattr(second.model.named_steps[name], attribute),
        )
    np.testing.assert_array_equal(
        first.model.named_steps["scaler"].mean_, first.holdout.x_train.mean(axis=0)
    )
    assert first.manifest["model_run_id"] != second.manifest["model_run_id"]
    # Changing validation targets alone also cannot influence coefficients.
    targets_only = changed(data, lambda r: r.model_copy(update={"targets": mutate(r).targets}))
    third = train(targets_only, config())
    np.testing.assert_array_equal(
        first.model.named_steps["estimator"].coef_, third.model.named_steps["estimator"].coef_
    )


def test_explicit_train_median_and_no_neutral_fill() -> None:
    model = pipeline(config())
    x = np.asarray([[1.0, np.nan], [3.0, 10.0], [5.0, 20.0], [7.0, 30.0]])
    model.fit(x, np.asarray([0, 1, 0, 1]))
    np.testing.assert_array_equal(model.named_steps["imputer"].statistics_, [4.0, 20.0])
    assert model.named_steps["imputer"].transform([[9.0, np.nan]])[0, 1] == 20.0


def test_p7_ineligible_nulls_never_revived_and_eligible_nulls_rejected(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    eligible = next(
        r for r in data.rows if r.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
    )
    invalid = changed(
        data,
        lambda r: (
            r.model_copy(update={"features": dict(r.features) | {"sma_5": None}})
            if r == eligible
            else r
        ),
    )
    with pytest.raises(DataContractError, match="ELIGIBILITY_CONTRADICTION"):
        split(invalid, config())
    fold = split(data, config())
    assert np.isfinite(fold.x_train).all() and np.isfinite(fold.x_validation).all()


def test_availability_cutoff_equality_and_future_label_exclusion(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    chosen = next(
        r
        for r in data.rows
        if r.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
        and r.metadata["session_date"] == day(24).isoformat()
    )

    def available(at: str) -> SupervisedDataset:
        return changed(
            data,
            lambda r: (
                r.model_copy(update={"metadata": dict(r.metadata) | {"label_available_at": at}})
                if r == chosen
                else r
            ),
        )

    equal = split(available(instant(51, 12).isoformat()), config())
    later = split(available(instant(51, 13).isoformat()), config())
    overlap = split(available(instant(52).isoformat()), config())
    assert len(equal.y_train) == len(later.y_train) + 1
    assert (
        later.exclusion_counts["LABEL_AFTER_TRAINING_CUTOFF"]
        == equal.exclusion_counts["LABEL_AFTER_TRAINING_CUTOFF"] + 1
    )
    assert (
        overlap.exclusion_counts["TARGET_OVERLAP_PURGED"]
        == equal.exclusion_counts["TARGET_OVERLAP_PURGED"] + 1
    )


def test_no_random_shuffle_and_target_metadata_feature_injection(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    with pytest.raises(DataContractError, match="CHRONOLOGICAL"):
        split(repin(data, rows=tuple(reversed(data.rows))), config())
    for column in ("target_forward_return_5", "security_id", "label_available_at"):
        with pytest.raises(ValueError):
            repin(data, feature_columns=(*data.feature_columns, column))
    # An otherwise coherent envelope cannot launder metadata into a new feature namespace.
    forged = repin(
        data,
        feature_columns=tuple("session_proxy" if n == "sma_5" else n for n in data.feature_columns),
        rows=tuple(
            r.model_copy(
                update={
                    "features": {
                        ("session_proxy" if k == "sma_5" else k): v for k, v in r.features.items()
                    }
                }
            )
            for r in data.rows
        ),
    )
    with pytest.raises(DataContractError, match="ONLY_P6_FEATURE_NAMES"):
        split(forged, config())
    with pytest.raises(ValueError):
        TrainingConfig.model_validate(config().model_dump() | {"shuffle": True})


def test_constant_removal_and_feature_order_train_only(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    constant = changed(
        data,
        lambda r: (
            r.model_copy(
                update={
                    "features": dict(r.features)
                    | {
                        "sma_5": 1.0
                        if str(r.metadata["session_date"]) < day(52).isoformat()
                        else 500.0
                    }
                }
            )
            if r.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
            else r
        ),
    )
    fold = split(constant, config())
    assert fold.removed_features == ("sma_5",)
    assert fold.feature_columns == ("return_1", "volatility_5", "volume_ratio_20")
    reverse = repin(data, feature_columns=tuple(reversed(data.feature_columns)))
    reversed_fold = split(reverse, config())
    assert reversed_fold.feature_columns == tuple(
        reversed(fold.feature_columns[:1] + ("sma_5",) + fold.feature_columns[1:])
    )
    np.testing.assert_array_equal(reversed_fold.x_train, split(data, config()).x_train[:, ::-1])


def test_metric_math_and_single_class_no_fabricated_auc() -> None:
    actual, probabilities = np.asarray([0.0, 0.0, 1.0, 1.0]), np.asarray([0.1, 0.8, 0.7, 0.9])
    metrics = classification_metrics(actual, probabilities, config())
    assert metrics["accuracy"] == 0.75 and metrics["balanced_accuracy"] == 0.75
    assert metrics["precision"] == pytest.approx(2 / 3) and metrics["recall"] == 1
    assert metrics["f1"] == 0.8 and metrics["brier_score"] == pytest.approx(0.1875)
    assert metrics["confusion_counts"] == dict(tn=1, fp=1, fn=0, tp=2)
    single = classification_metrics(np.ones(4), probabilities, config())
    assert single["roc_auc"] is None and single["pr_auc_average_precision"] is None
    assert single["auc_status"] == "UNAVAILABLE_SINGLE_CLASS"
    regression = regression_metrics(np.asarray([1.0, 2.0, 3.0]), np.asarray([1.0, 2.0, 2.0]))
    assert regression["mae"] == pytest.approx(1 / 3)
    assert regression["rmse"] == pytest.approx(np.sqrt(1 / 3)) and regression["r2"] == 0.5
    assert regression_metrics(np.ones(4), np.zeros(4))["r2"] is None


def test_calibration_bins_counts_edges_and_small_data() -> None:
    values = np.tile(np.asarray([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]), 4)
    metrics = classification_metrics((values > 0.5).astype("float64"), values, config())
    assert sum(b["count"] for b in metrics["calibration"]["bins"]) == len(values)
    assert metrics["calibration"]["bins"][-1]["count"] == 8
    assert (
        classification_metrics(np.ones(4), np.ones(4), config())["calibration"]["status"]
        == "UNAVAILABLE_TOO_FEW_ROWS"
    )


def test_scientific_negative_control_never_claims_meaningful_signal(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    rng = np.random.default_rng(2718)
    returns = [
        r.targets["target_forward_return_5"]
        for r in data.rows
        if r.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
    ]
    rng.shuffle(returns)  # targets ONLY in an explicitly TEST_ONLY negative control
    values = iter(returns)

    def shuffle_targets(row: AlignedRow) -> AlignedRow:
        if row.metadata["training_eligibility"] != "TRAINING_ELIGIBLE":
            return row
        target = next(values)
        return row.model_copy(
            update={
                "targets": {
                    "target_forward_return_5": target,
                    "target_direction_5": int(float(str(target)) > 0),
                }
            }
        )

    result = train(changed(data, shuffle_targets), config())
    assert result.report["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert result.manifest["status"] == "TEST_ONLY"
    assert result.report["production_claims_permitted"] is False
    # No chance-accuracy assertion on a small constructed sample.


def test_identity_all_meaningful_changes_and_classification_protection(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    first = train(data, config()).manifest["model_run_id"]
    for update in (
        {"random_seed": 1730},
        {"model_family": "random_forest"},
        {"training_cutoff": instant(50, 12)},
    ):
        assert (
            train(data, TrainingConfig.model_validate(config().model_dump() | update)).manifest[
                "model_run_id"
            ]
            != first
        )
    for update in ({"feature_set_id": "a" * 64}, {"label_set_id": "b" * 64}):
        assert train(repin(data, **update), config()).manifest["model_run_id"] != first
    with pytest.raises(ValueError, match="Production"):
        repin(data, classification=Classification.PRODUCTION)
    with pytest.raises(ValueError):
        TrainingConfig.model_validate(config().model_dump() | {"production_claims_permitted": True})


def test_reject_nonfinite_corruption_insufficient_and_single_class(
    aligned: dict[int, SupervisedDataset],
) -> None:
    data = aligned[5]
    with pytest.raises(DataContractError, match="DATASET_ID_MISMATCH"):
        split(data.model_copy(update={"supervised_dataset_id": "0" * 64}), config())
    bad = changed(
        data,
        lambda r: r.model_copy(update={"features": dict(r.features) | {"sma_5": float("inf")}}),
    )
    with pytest.raises(DataContractError, match="NONFINITE_FEATURE"):
        split(bad, config())
    with pytest.raises(DataContractError, match="INSUFFICIENT_MATURE"):
        train(
            data,
            TrainingConfig.model_validate(config().model_dump() | {"minimum_training_rows": 10000}),
        )
    single = changed(
        data,
        lambda r: (
            r.model_copy(
                update={"targets": {"target_forward_return_5": "0.1", "target_direction_5": 1}}
            )
            if r.targets["target_forward_return_5"] is not None
            else r
        ),
    )
    with pytest.raises(DataContractError, match="INSUFFICIENT_TRAINING_CLASSES"):
        train(single, config())


def test_artifact_corruption_no_promotion_and_exact_dataset_evaluation(
    aligned: dict[int, SupervisedDataset], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    registry = LocalRegistry(Path("data/models"))
    result = train(aligned[5], config())
    entry = registry.save(result)
    with pytest.raises(ValueError):
        RegistryEntry.model_validate(entry.model_dump() | {"status": "PRODUCTION"})
    with pytest.raises(DataContractError, match="INVALID_MODEL_RUN_ID"):
        registry.load("../escape")
    with pytest.raises(DataContractError, match="EXACT_PINNED"):
        registry.evaluate(entry.model_run_id, repin(aligned[5], feature_set_id="a" * 64))
    model = registry.root / entry.artifact_path / "model.skops"
    model.write_bytes(model.read_bytes() + b"TEST_ONLY corruption")
    with pytest.raises(DataContractError, match="CHECKSUM_MISMATCH"):
        registry.load(entry.model_run_id)
    with pytest.raises(DataContractError, match="IGNORED_LOCAL"):
        LocalRegistry(Path("public-artifacts"))


@dataclass
class UnreviewedFixtureArtifact:
    """A harmless TEST_ONLY object whose type must still never be automatically trusted."""

    value: int


def test_unreviewed_serialized_types_rejected_even_with_matching_checksum(
    aligned: dict[int, SupervisedDataset], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    registry = LocalRegistry(Path("data/models"))
    entry = registry.save(train(aligned[5], config()))
    payload = sio.dumps(UnreviewedFixtureArtifact(1))
    (registry.root / entry.artifact_path / "model.skops").write_bytes(payload)
    changed_entry = RegistryEntry.model_validate(
        entry.model_dump()
        | {"checksums": dict(entry.checksums) | {"model.skops": checksum(payload)}}
    )
    (registry.root / "registry" / f"{entry.model_run_id}.json").write_bytes(
        stable_json(changed_entry.model_dump(mode="json"))
    )
    with pytest.raises(DataContractError, match="UNREVIEWED_ARTIFACT_TYPES"):
        registry.load(entry.model_run_id)


def test_cli_train_evaluate_and_safe_errors(
    aligned: dict[int, SupervisedDataset],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("supervised.json").write_bytes(aligned[5].to_bytes())
    Path("config.json").write_bytes(stable_json(config().model_dump(mode="json")))
    args = ["baseline", "supervised.json", "--config", "config.json"]
    assert train_main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["classification"] == "TEST_ONLY" and output["naive_metrics"]
    assert model_main(["evaluate", output["model_run_id"], "--input", "supervised.json"]) == 0
    assert json.loads(capsys.readouterr().out)["metrics"] == output["metrics"]
    assert train_main(["baseline", "missing", "--config", "config.json"]) == 2
    assert "BASELINE_TRAINING_FAILED" in capsys.readouterr().out


def early_aligned(batch: CanonicalBatch) -> SupervisedDataset:
    reader = CanonicalReader(batch)
    features = build_features(
        reader,
        BuildPlan(
            history_start=START,
            decisions=tuple(
                Decision(session_date=day(i), knowledge_cutoff=instant(i, 12))
                for i in (20, 24, 28, 32)
            ),
        ),
    )
    labels = build_labels(
        reader,
        features,
        LabelPlan(
            outcome_cutoff=instant(34, 12),
            outcome_end=day(34),
            horizons=(1,),
        ),
    )
    return align(
        features,
        labels,
        horizon=1,
        training_as_of=instant(34, 12),
        feature_columns=("return_1", "sma_5"),
        allow_degraded=True,
    )


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


def test_actual_future_revisions_listings_members_and_observations_cannot_change_training(
    source: tuple[CanonicalBatch, dict[int, SupervisedDataset]], tmp_path: Path
) -> None:
    batch = source[0]
    original = early_aligned(batch)
    plan = TrainingConfig.model_validate(
        dict(
            task="classification",
            horizon=1,
            model_family="logistic",
            training_cutoff=instant(27, 12),
            validation_start=day(28),
            validation_end=day(32),
            minimum_training_rows=2,
            minimum_validation_rows=2,
        )
    )
    fold = split(original, plan)
    assert all(
        m.security_id != "TEST:NEW" for m in (*fold.train_metadata, *fold.validation_metadata)
    )
    old = next(
        r
        for r in batch.revisions
        if isinstance(r, MembershipRevision) and r.security_id == "TEST:ALPHA"
    )
    fact = old.fact.model_copy(
        update=dict(
            revision_id="r2",
            supersedes_revision_id="r1",
            security_type=SecurityType.ETF,
            provenance=old.provenance.model_copy(update={"available_at": instant(80)}),
        )
    )
    revised = old.model_copy(
        update=dict(
            revision_id="r2",
            revision_number=2,
            supersedes_revision_id="r1",
            provenance=fact.provenance,
            fact=fact,
        )
    )
    changed_batch = append_reference(batch, revised, tmp_path / "revision")
    # A newly pinned future-known member, even effective earlier, remains invisible.
    member_fact = old.fact.model_copy(
        update=dict(
            fact_id="TEST_ONLY_FUTURE_MEMBER",
            security_id="TEST:FUTURE",
            effective_from=day(24),
            provenance=old.provenance.model_copy(update={"available_at": instant(80)}),
        )
    )
    member = old.model_copy(
        update=dict(
            logical_record_id=member_fact.fact_id,
            security_id=member_fact.security_id,
            effective_from=member_fact.effective_from,
            provenance=member_fact.provenance,
            fact=member_fact,
        )
    )
    changed_batch = changed_batch.model_copy(
        update={
            "securities": (
                *changed_batch.securities,
                Security(security_id="TEST:FUTURE", classification=Classification.TEST_ONLY),
            )
        }
    )
    changed_batch = append_reference(changed_batch, member, tmp_path / "future-member")
    identity = next(
        r
        for r in batch.revisions
        if isinstance(r, IdentityRevision) and r.security_id == "TEST:ALPHA"
    )
    identity_fact = identity.fact.model_copy(
        update=dict(
            fact_id="TEST_ONLY_FUTURE_IDENTITY",
            security_id="TEST:FUTURE",
            source_security_id="TEST:FUTURE",
            effective_from=day(24),
            provenance=member_fact.provenance,
        )
    )
    changed_batch = append_reference(
        changed_batch,
        identity.model_copy(
            update=dict(
                logical_record_id=identity_fact.fact_id,
                security_id=identity_fact.security_id,
                effective_from=identity_fact.effective_from,
                provenance=identity_fact.provenance,
                fact=identity_fact,
            )
        ),
        tmp_path / "future-identity",
    )
    altered = early_aligned(changed_batch)
    new_fold = split(altered, plan)
    np.testing.assert_array_equal(fold.x_train, new_fold.x_train)
    np.testing.assert_array_equal(fold.y_train, new_fold.y_train)
    assert all(
        m.security_id != "TEST:FUTURE"
        for m in (*new_fold.train_metadata, *new_fold.validation_metadata)
    )
    # Remove all later observations/evidence. Earlier matrices must remain the same.
    revisions = tuple(r for r in batch.revisions if r.effective_from < day(35))
    keys = {revision_key(r) for r in revisions}
    truncated = batch.model_copy(
        update=dict(
            revisions=revisions,
            lineage=tuple(link for link in batch.lineage if link.record_key in keys),
        )
    )
    limited = split(early_aligned(truncated), plan)
    np.testing.assert_array_equal(fold.x_train, limited.x_train)
    np.testing.assert_array_equal(fold.y_train, limited.y_train)
