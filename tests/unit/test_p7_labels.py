"""TEST_ONLY hand-verifiable targets, time gates, classification and separation proofs."""

import json
from datetime import timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.build_p6_test_fixture import START, build_history, day, instant

from alphalens_data.canonical.assembly import EvidenceAssembly
from alphalens_data.canonical.models import (
    ActionRevision,
    CanonicalBatch,
    IdentityRevision,
    Revision,
    SessionRevision,
)
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import stable_json
from alphalens_features.engine import build as build_features
from alphalens_features.models import BuildPlan, Decision, FeatureDataset
from alphalens_labels.alignment import SupervisedDataset, align
from alphalens_labels.cli import main
from alphalens_labels.engine import build
from alphalens_labels.models import LabelDataset, LabelPlan, LabelRow
from alphalens_labels.output import distribution, manifest, parquet_bytes, supervised_parquet


def feature_plan(*indices: int) -> BuildPlan:
    return BuildPlan(
        history_start=START,
        decisions=tuple(
            Decision(session_date=day(i), knowledge_cutoff=instant(i, 12)) for i in indices
        ),
    )


def outcome_plan(end: int = 69, horizons: tuple[int, ...] = (1, 5, 10, 20)) -> LabelPlan:
    return LabelPlan(outcome_cutoff=instant(end, 12), outcome_end=day(end), horizons=horizons)


@pytest.fixture(scope="module")
def history(tmp_path_factory: pytest.TempPathFactory) -> CanonicalBatch:
    return build_history(
        tmp_path_factory.mktemp("TEST_ONLY_p7"), overrides={(1, "TEST:ALPHA"): {"open": "102"}}
    )[0]


@pytest.fixture(scope="module")
def features(history: CanonicalBatch) -> FeatureDataset:
    return build_features(CanonicalReader(history), feature_plan(0, 20, 49, 54, 69))


@pytest.fixture(scope="module")
def labels(history: CanonicalBatch, features: FeatureDataset) -> LabelDataset:
    return build(CanonicalReader(history), features, outcome_plan())


def target(
    labels: LabelDataset, index: int, horizon: int, security: str = "TEST:ALPHA"
) -> LabelRow:
    return next(
        r
        for r in labels.rows
        if r.session_date == day(index) and r.horizon == horizon and r.security_id == security
    )


def reference(batch: CanonicalBatch, record: Revision, root: Path) -> CanonicalBatch:
    assembly = EvidenceAssembly(root, Classification.TEST_ONLY)
    assembly.reference(record)
    evidence = next(a for a in batch.artifacts if a.sha256 == record.provenance.artifact_sha256)
    assembly.link_reference(record, evidence, {"evidence_sha256": evidence.sha256})
    return batch.model_copy(
        update=dict(
            revisions=tuple(
                r
                for r in batch.revisions
                if (r.kind, r.logical_record_id, r.revision_id)
                != (record.kind, record.logical_record_id, record.revision_id)
            )
            + (record,),
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


@pytest.mark.parametrize(
    ("horizon", "numerator", "direction"), [(1, -1, 0), (5, 3, 1), (10, 8, 1), (20, 18, 1)]
)
def test_golden_forward_open_to_close(
    labels: LabelDataset, horizon: int, numerator: int, direction: int
) -> None:
    row = target(labels, 0, horizon)
    assert row.entry_session == day(1) and row.target_session == day(horizon)
    assert row.entry_price == Decimal(102) and row.exit_price == Decimal(100 + horizon)
    assert row.exact_numerator == Decimal(numerator) and row.exact_denominator == Decimal(102)
    assert float(row.return_value or 0) == pytest.approx(float(Fraction(numerator, 102)), abs=1e-16)
    assert row.direction_value == direction and row.maturity == "MATURE"
    assert row.label_available_at == instant(horizon)
    assert row.label_available_at > instant(horizon, 10)
    # 1-session close-to-close return would be positive; correct next-open outcome is negative.
    if horizon == 1:
        assert str(row.return_value) == "-0.0098039215686274509803921568627450980392"


def test_zero_is_nonpositive_and_decimal_context_is_pinned(tmp_path: Path) -> None:
    batch = build_history(tmp_path, length=3, overrides={(1, "TEST:ALPHA"): {"open": "101"}})[0]
    features = build_features(CanonicalReader(batch), feature_plan(0))
    with localcontext() as context:
        context.prec = 5
        result = build(CanonicalReader(batch), features, outcome_plan(2, (1,)))
    assert target(result, 0, 1).return_value == 0
    assert target(result, 0, 1).direction_value == 0


def test_end_of_dataset_maturity_and_no_fabricated_dates(labels: LabelDataset) -> None:
    row = target(labels, 69, 20)
    assert row.maturity == "NOT_YET_MATURE" and row.return_value is None
    assert (
        row.entry_session is None and row.target_session is None and row.label_available_at is None
    )
    row = target(labels, 54, 20)
    assert row.maturity == "NOT_YET_MATURE" and row.entry_session == day(55)
    assert row.target_session is None


def test_twenty_session_target_hidden_until_horizon(history: CanonicalBatch) -> None:
    features = build_features(CanonicalReader(history), feature_plan(20))
    before = build(CanonicalReader(history), features, outcome_plan(30, (20,)))
    after = build(CanonicalReader(history), features, outcome_plan(40, (20,)))
    assert target(before, 20, 20).maturity == "NOT_YET_MATURE"
    assert target(before, 20, 20).return_value is None
    assert target(after, 20, 20).maturity == "MATURE"
    assert target(after, 20, 20).label_available_at == instant(40)
    available_at = target(after, 20, 20).label_available_at
    assert available_at is not None and available_at <= outcome_plan(40).outcome_cutoff


def test_terminal_departure_preserves_row_without_zero_return(labels: LabelDataset) -> None:
    row = target(labels, 54, 5, "TEST:DEPART")
    assert row.maturity == "TERMINAL_EVENT" and row.return_value is None
    assert any("DELISTED" in reason for reason in row.reason_codes)
    assert target(labels, 20, 5, "TEST:DEPART").return_value is not None


def test_future_exit_changes_target_only(history: CanonicalBatch, tmp_path: Path) -> None:
    changed = build_history(
        tmp_path,
        length=41,
        overrides={
            (1, "TEST:ALPHA"): {"open": "102"},
            (25, "TEST:ALPHA"): {"close": "160", "high": "162"},
        },
    )[0]
    original_features = build_features(CanonicalReader(history), feature_plan(20))
    frozen_bytes = original_features.to_bytes()
    new_features = build_features(CanonicalReader(changed), feature_plan(20))
    a = build(CanonicalReader(history), original_features, outcome_plan(40))
    b = build(CanonicalReader(changed), new_features, outcome_plan(40))
    assert [r.values for r in original_features.rows] == [r.values for r in new_features.rows]
    assert target(a, 20, 5).return_value != target(b, 20, 5).return_value
    assert original_features.to_bytes() == frozen_bytes
    assert original_features.feature_set_id != new_features.feature_set_id


def test_later_revision_is_label_knowledge_not_historical_feature_input(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    changed = build_history(
        tmp_path,
        length=61,
        overrides={(1, "TEST:ALPHA"): {"open": "102"}},
        revision=(25, 50, "150"),
    )[0]
    a = build_features(CanonicalReader(history), feature_plan(20))
    b = build_features(CanonicalReader(changed), feature_plan(20))
    assert [r.values for r in a.rows] == [r.values for r in b.rows]
    old = build(CanonicalReader(changed), b, outcome_plan(40, (5,)))
    new = build(CanonicalReader(changed), b, outcome_plan(60, (5,)))
    assert target(old, 20, 5).return_value != target(new, 20, 5).return_value
    assert target(new, 20, 5).label_available_at == instant(50)
    aligned = align(
        b,
        new,
        horizon=5,
        training_as_of=instant(40, 12),
        feature_columns=("return_1",),
        allow_degraded=True,
    )
    row = next(r for r in aligned.rows if r.metadata["security_id"] == "TEST:ALPHA")
    assert row.targets["target_forward_return_5"] is None
    reasons = row.metadata["reason_codes"]
    assert isinstance(reasons, (tuple, list)) and "LABEL_NOT_MATURE" in reasons


@pytest.mark.parametrize("rejected_index", [21, 23, 25])
def test_rejected_and_missing_future_prices_are_not_substituted(
    tmp_path: Path, rejected_index: int
) -> None:
    batch = build_history(
        tmp_path, length=26, overrides={(rejected_index, "TEST:ALPHA"): {"close": ""}}
    )[0]
    features = build_features(CanonicalReader(batch), feature_plan(20))
    data = build(CanonicalReader(batch), features, outcome_plan(25, (1, 5)))
    assert (target(data, 20, 1).return_value is None) == (rejected_index == 21)
    assert target(data, 20, 5).maturity == "UNAVAILABLE"
    assert "FUTURE_PRICE_QUALITY_REJECTED_OR_UNAVAILABLE" in target(data, 20, 5).reason_codes


def test_quality_policy_and_known_action_are_explicit(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    identity = next(r for r in history.revisions if isinstance(r, IdentityRevision))
    action = ActionRevision(
        logical_record_id="TEST_ONLY_LABEL_SPLIT",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:ALPHA",
        effective_from=day(23),
        ex_date=day(23),
        corporate_action_id="TEST_ONLY_LABEL_SPLIT",
        event_type="SPLIT",
        provenance=identity.provenance.model_copy(update={"available_at": instant(23)}),
    )
    changed = reference(history, action, tmp_path)
    features = build_features(CanonicalReader(changed), feature_plan(20))
    assert not next(r for r in features.rows if r.security_id == "TEST:ALPHA").corporate_action_keys
    data = build(CanonicalReader(changed), features, outcome_plan(30, (5,)))
    row = target(data, 20, 5)
    assert row.return_value is not None and row.quality_state == "DEGRADED"
    assert any("CORPORATE_ACTION_UNADJUSTED" in r for r in row.reason_codes)
    aligned = align(
        features,
        data,
        horizon=5,
        training_as_of=instant(30, 12),
        feature_columns=("return_1",),
        allow_degraded=True,
    )
    assert (
        next(r for r in aligned.rows if r.metadata["security_id"] == "TEST:ALPHA").metadata[
            "training_eligibility"
        ]
        == "NOT_TRAINING_ELIGIBLE"
    )


def test_calendar_offsets_use_trading_sessions_and_gaps_fail_closed(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import PriceRevision

    # Remove the constructed day21 observation and explicitly evidence NON_TRADING.
    session = next(
        r for r in history.revisions if isinstance(r, SessionRevision) and r.session_date == day(21)
    )
    changed = reference(
        history,
        session.model_copy(update={"status": "VERIFIED_NON_TRADING_SESSION"}),
        tmp_path / "nontrading",
    )
    removed = {
        r.logical_record_id
        for r in changed.revisions
        if isinstance(r, PriceRevision) and r.session_date == day(21)
    }
    from alphalens_data.canonical.models import revision_key

    keys = {revision_key(r) for r in changed.revisions if r.logical_record_id in removed}
    changed = changed.model_copy(
        update=dict(
            revisions=tuple(r for r in changed.revisions if r.logical_record_id not in removed),
            lineage=tuple(link for link in changed.lineage if link.record_key not in keys),
        )
    )
    features = build_features(CanonicalReader(changed), feature_plan(20))
    data = build(CanonicalReader(changed), features, outcome_plan(30, (5,)))
    assert target(data, 20, 5).entry_session == day(22)
    assert target(data, 20, 5).target_session == day(26)
    unknown = reference(
        history,
        session.model_copy(update={"status": "UNKNOWN_SESSION_STATUS"}),
        tmp_path / "unknown",
    )
    features = build_features(CanonicalReader(unknown), feature_plan(20))
    result = build(CanonicalReader(unknown), features, outcome_plan(30, (5,)))
    assert target(result, 20, 5).maturity == "UNAVAILABLE"


def test_alignment_boundaries_maturity_and_no_row_drops(
    features: FeatureDataset, labels: LabelDataset
) -> None:
    data = align(
        features,
        labels,
        horizon=20,
        training_as_of=instant(40, 12),
        feature_columns=("return_1", "sma_5"),
        allow_degraded=True,
    )
    assert len(data.rows) == len(features.rows)
    assert not set(data.feature_columns) & set(data.target_columns)
    assert not set(data.feature_columns) & set(data.metadata_columns)
    early = next(
        r
        for r in data.rows
        if r.metadata["session_date"] == day(20).isoformat()
        and r.metadata["security_id"] == "TEST:ALPHA"
    )
    assert early.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
    late = next(
        r
        for r in data.rows
        if r.metadata["session_date"] == day(69).isoformat()
        and r.metadata["security_id"] == "TEST:ALPHA"
    )
    reasons = late.metadata["reason_codes"]
    assert isinstance(reasons, (tuple, list)) and "LABEL_NOT_MATURE" in reasons
    assert late.targets["target_forward_return_20"] is None
    with pytest.raises(DataContractError, match="REGISTERED_FEATURE"):
        align(
            features,
            labels,
            horizon=5,
            training_as_of=instant(69, 12),
            feature_columns=("target_forward_return_5",),
        )
    with pytest.raises(ValueError, match="disjoint"):
        SupervisedDataset.model_validate(
            data.model_dump() | {"feature_columns": data.target_columns}
        )


def test_deterministic_ids_outputs_and_descriptive_distribution(
    history: CanonicalBatch, features: FeatureDataset, labels: LabelDataset
) -> None:
    replay = build(CanonicalReader(history), features, outcome_plan())
    assert replay.to_bytes() == labels.to_bytes()
    assert parquet_bytes(replay) == parquet_bytes(labels)
    table = pq.read_table(pa.BufferReader(parquet_bytes(labels)))
    assert table.schema.field("return_value").type == pa.string()
    assert table.schema.field("direction_value").type == pa.int8()
    report = distribution(labels)
    assert report["classification"] == "TEST_ONLY"
    assert "NO_PREDICTIVE_SUCCESS" in str(report["report_scope"])
    assert manifest(labels)["row_count"] == len(labels.rows)
    joined = align(
        features,
        labels,
        horizon=5,
        training_as_of=instant(69, 12),
        feature_columns=("return_1",),
        allow_degraded=True,
    )
    assert supervised_parquet(joined) == supervised_parquet(
        align(
            features,
            labels,
            horizon=5,
            training_as_of=instant(69, 12),
            feature_columns=("return_1",),
            allow_degraded=True,
        )
    )
    matrix = pq.read_table(pa.BufferReader(supervised_parquet(joined)))
    assert matrix.schema.metadata and json.loads(matrix.schema.metadata[b"feature_columns"]) == [
        "return_1"
    ]
    assert matrix.schema.field("label_available_at").type == pa.timestamp("us", tz="UTC")
    assert (
        build(CanonicalReader(history), features, outcome_plan(69, (1,))).label_set_id
        != labels.label_set_id
    )


def test_classification_and_tampered_features_are_rejected(
    history: CanonicalBatch, features: FeatureDataset, labels: LabelDataset
) -> None:
    with pytest.raises(ValueError, match="classification"):
        LabelDataset.model_validate(labels.model_dump() | {"classification": "PRODUCTION"})
    with pytest.raises(DataContractError, match="REPLAY_MISMATCH"):
        build(
            CanonicalReader(history),
            features.model_copy(update={"feature_set_id": "f" * 64}),
            outcome_plan(),
        )
    with pytest.raises(DataContractError, match="DATASET_ID_MISMATCH"):
        align(
            features,
            labels.model_copy(update={"label_set_id": "f" * 64}),
            horizon=5,
            training_as_of=instant(69, 12),
        )
    with pytest.raises(DataContractError, match="CLASSIFICATION_MISMATCH"):
        build(
            CanonicalReader(history),
            features.model_copy(update={"classification": Classification.RESEARCH_FIXTURE}),
            outcome_plan(),
        )


def test_decision_after_entry_date_start_cannot_claim_open(history: CanonicalBatch) -> None:
    decision = Decision(session_date=day(20), knowledge_cutoff=instant(21, 5))
    features = build_features(
        CanonicalReader(history), BuildPlan(history_start=START, decisions=(decision,))
    )
    labels = build(CanonicalReader(history), features, outcome_plan(30, (1,)))
    assert target(labels, 20, 1).maturity == "UNAVAILABLE"
    assert "DECISION_NOT_PROVEN_BEFORE_ENTRY_OPEN" in target(labels, 20, 1).reason_codes


def test_chronological_split_columns_need_no_future_inputs(
    features: FeatureDataset, labels: LabelDataset
) -> None:
    data = align(
        features,
        labels,
        horizon=5,
        training_as_of=instant(69, 12),
        feature_columns=("return_1",),
        allow_degraded=True,
    )
    dates = [str(r.metadata["decision_time"]) for r in data.rows]
    assert dates == sorted(dates)
    assert len([r for r in data.rows if str(r.metadata["session_date"]) < day(50).isoformat()]) > 0
    assert all(set(r.features) == {"return_1"} for r in data.rows)
    assert all("label_available_at" not in r.features for r in data.rows)


def test_cli_writes_and_replays_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    batch = build_history(Path("data/s"), length=26)[0]
    features = build_features(CanonicalReader(batch), feature_plan(0, 20, 25))
    Path("data/features.json").write_bytes(features.to_bytes())
    Path("data/label-plan.json").write_bytes(stable_json(outcome_plan(25).model_dump(mode="json")))
    arguments = [
        "build",
        "data/s/canonical-input.json",
        "--features",
        "data/features.json",
        "--plan",
        "data/label-plan.json",
        "--output",
        "data/out",
        "--feature-columns",
        "return_1",
        "--allow-degraded",
    ]
    assert main(arguments) == 0
    first = capsys.readouterr().out
    assert main(arguments) == 0
    assert capsys.readouterr().out == first
    assert '"classification":"TEST_ONLY"' in first and '"training_eligible_count":' in first
    artifact = next(Path("data/out").glob("*/target-distribution.json"))
    assert json.loads(artifact.read_bytes())["classification"] == "TEST_ONLY"
    assert main(["build", "missing", "--features", "missing", "--plan", "missing"]) == 2


def test_plan_validation_and_label_float_rejection(labels: LabelDataset) -> None:
    with pytest.raises(ValueError):
        outcome_plan(69, (5, 1))
    with pytest.raises(ValueError):
        LabelPlan(outcome_end=day(70), outcome_cutoff=instant(69, 12))
    with pytest.raises(ValueError, match="Decimal"):
        LabelRow.model_validate(target(labels, 0, 1).model_dump() | {"return_value": -0.01})
    assert day(20) == START + timedelta(
        days=20
    )  # TEST_ONLY artificial schedule, not calendar-day label logic.


def test_feature_input_keys_exclude_future_targets_and_membership_knowledge(
    history: CanonicalBatch, features: FeatureDataset, labels: LabelDataset
) -> None:
    from alphalens_data.canonical.models import PriceRevision, revision_key

    prices = {revision_key(r): r for r in history.revisions if isinstance(r, PriceRevision)}
    pinned = features.to_bytes()
    for feature in features.rows:
        for key in feature.input_revision_keys:
            bar = prices.get(key)
            if bar is not None:
                assert bar.session_date <= feature.session_date
                assert (
                    bar.provenance.available_at is not None
                    and bar.provenance.available_at <= feature.knowledge_cutoff
                )
        if feature.session_date < day(35):
            assert feature.security_id != "TEST:NEW"
        if feature.security_id == "TEST:DEPART" and feature.session_date == day(20):
            assert feature.analytical_eligible
    for label in labels.rows:
        for key in label.input_revision_keys:
            bar = prices.get(key)
            if bar is not None:
                assert bar.session_date > label.session_date
    assert features.to_bytes() == pinned


def test_missing_exit_and_strict_quality_do_not_create_clean_labels(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import PriceRevision, revision_key

    bar = next(
        r
        for r in history.revisions
        if isinstance(r, PriceRevision)
        and r.security_id == "TEST:ALPHA"
        and r.session_date == day(25)
    )
    missing = history.model_copy(
        update=dict(
            revisions=tuple(r for r in history.revisions if r != bar),
            lineage=tuple(link for link in history.lineage if link.record_key != revision_key(bar)),
        )
    )
    features = build_features(CanonicalReader(missing), feature_plan(20))
    labels = build(CanonicalReader(missing), features, outcome_plan(30, (5,)))
    assert target(labels, 20, 5).return_value is None
    assert "REQUIRED_FUTURE_PRICE_UNAVAILABLE" in target(labels, 20, 5).reason_codes
    degraded = build_history(tmp_path, length=26, overrides={(23, "TEST:ALPHA"): {"volume": "0"}})[
        0
    ]
    features = build_features(CanonicalReader(degraded), feature_plan(20))
    plan = outcome_plan(25, (5,))
    allowed = build(CanonicalReader(degraded), features, plan)
    strict = build(
        CanonicalReader(degraded),
        features,
        plan.model_copy(update={"quality_policy": "VALID_ONLY"}),
    )
    assert target(allowed, 20, 5).return_value is not None
    assert target(allowed, 20, 5).quality_state == "DEGRADED"
    assert "DEGRADED_FUTURE_INPUT_DISALLOWED" in target(strict, 20, 5).reason_codes
    assert strict.label_set_id != allowed.label_set_id


def test_availability_uses_quality_receipt_and_degraded_policy_identity(
    history: CanonicalBatch, tmp_path: Path
) -> None:
    from alphalens_data.canonical.models import QualityRevision

    quality = next(
        r
        for r in history.revisions
        if isinstance(r, QualityRevision) and r.evidence.session_date == day(25)
    )
    new = quality.model_copy(
        update=dict(
            provenance=quality.provenance.model_copy(update={"available_at": instant(27)}),
            evidence=quality.evidence.model_copy(update={"available_at": instant(27)}),
        )
    )
    changed = reference(history, new, tmp_path)
    features = build_features(CanonicalReader(changed), feature_plan(20))
    labels = build(CanonicalReader(changed), features, outcome_plan(30, (5,)))
    assert target(labels, 20, 5).label_available_at == instant(27)
    a = align(
        features,
        labels,
        horizon=5,
        training_as_of=instant(30, 12),
        feature_columns=("return_1",),
        allow_degraded=False,
    )
    b = align(
        features,
        labels,
        horizon=5,
        training_as_of=instant(30, 12),
        feature_columns=("return_1",),
        allow_degraded=True,
    )
    assert a.supervised_dataset_id != b.supervised_dataset_id
