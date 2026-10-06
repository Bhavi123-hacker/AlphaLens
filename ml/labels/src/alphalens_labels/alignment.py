"""Explicit feature/target/metadata boundary and training eligibility; no model fitting."""

from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from alphalens_data.canonical.models import Availability
from alphalens_data.contracts import Contract, NonEmpty
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification, Hash
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_features.models import FeatureDataset
from alphalens_features.registry import default_set
from alphalens_labels.models import LabelDataset

METADATA_COLUMNS = (
    "security_id",
    "session_date",
    "decision_time",
    "feature_canonical_dataset_id",
    "universe_snapshot_id",
    "label_available_at",
    "classification",
    "training_eligibility",
    "reason_codes",
)


class AlignedRow(Contract):
    features: dict[str, float | None]
    targets: dict[str, str | int | None]
    metadata: dict[str, object]


class SupervisedDataset(Contract):
    supervised_dataset_id: Hash
    schema_version: Literal["p7.alignment.v1"] = "p7.alignment.v1"
    feature_set_id: Hash
    label_set_id: Hash
    feature_columns: tuple[NonEmpty, ...]
    target_columns: tuple[NonEmpty, ...]
    metadata_columns: tuple[NonEmpty, ...] = METADATA_COLUMNS
    classification: Classification
    training_as_of: AwareDatetime
    horizon: int
    allow_degraded: bool
    rows: tuple[AlignedRow, ...]
    production_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def boundaries(self) -> Self:
        features, targets, metadata = (
            set(self.feature_columns),
            set(self.target_columns),
            set(self.metadata_columns),
        )
        if not features or features & targets or features & metadata or targets & metadata:
            raise ValueError("Feature, target and metadata columns must be nonempty and disjoint")
        if self.classification == Classification.PRODUCTION:
            raise ValueError("Production supervised data not cleared")
        for row in self.rows:
            if (
                set(row.features) != features
                or set(row.targets) != targets
                or set(row.metadata) != metadata
            ):
                raise ValueError("Each row must match its explicit column boundaries")
            if row.metadata.get("classification") != self.classification:
                raise ValueError("Classification mismatch")
        return self

    def to_bytes(self) -> bytes:
        return stable_json(self.model_dump(mode="json"))


def align(
    features: FeatureDataset,
    labels: LabelDataset,
    *,
    horizon: int,
    training_as_of: datetime,
    feature_columns: tuple[str, ...] | None = None,
    allow_degraded: bool = False,
) -> SupervisedDataset:
    if training_as_of.tzinfo is None or training_as_of.utcoffset() is None:
        raise DataContractError("NAIVE_TRAINING_CUTOFF")
    if features.feature_set != default_set(features.feature_set.plan):
        raise DataContractError("ONLY_SUPPORTED_FEATURE_REGISTRY_ALLOWED")
    for actual, payload, field in (
        (
            features.feature_set_id,
            features.model_dump(mode="json", exclude={"feature_set_id"}),
            "FEATURE",
        ),
        (labels.label_set_id, labels.model_dump(mode="json", exclude={"label_set_id"}), "LABEL"),
    ):
        if checksum(stable_json(payload)) != actual:
            raise DataContractError(f"{field}_DATASET_ID_MISMATCH")
    if (
        labels.feature_set_id != features.feature_set_id
        or labels.canonical_input_id != features.canonical_input_id
    ):
        raise DataContractError("FEATURE_LABEL_IDENTITY_MISMATCH")
    if labels.classification != features.classification:
        raise DataContractError("CLASSIFICATION_MISMATCH")
    if training_as_of > labels.plan.outcome_cutoff:
        raise DataContractError("TRAINING_CUTOFF_BEYOND_LABEL_KNOWLEDGE")
    definition = next((d for d in labels.definitions if d.horizon == horizon), None)
    if definition is None:
        raise DataContractError("LABEL_HORIZON_UNAVAILABLE")
    registered = tuple(d.feature_name for d in features.feature_set.definitions)
    columns = feature_columns if feature_columns is not None else registered
    if not columns or len(columns) != len(set(columns)) or not set(columns) <= set(registered):
        raise DataContractError("ONLY_REGISTERED_FEATURE_COLUMNS_ALLOWED")
    target_columns = (f"target_{definition.label_name}", f"target_{definition.direction_name}")
    keyed = {(r.security_id, r.session_date): r for r in labels.rows if r.horizon == horizon}
    if len(keyed) != len(features.rows):
        raise DataContractError("LABEL_ROW_ALIGNMENT_MISMATCH")
    rows: list[AlignedRow] = []
    for feature in features.rows:
        label = keyed.get((feature.security_id, feature.session_date))
        if (
            label is None
            or label.decision_time != feature.decision_time
            or label.feature_canonical_dataset_id != feature.canonical_dataset_id
        ):
            raise DataContractError("STABLE_FEATURE_LABEL_KEY_MISMATCH")
        reasons: set[str] = set()
        if feature.decision_time > training_as_of:
            reasons.add("FEATURE_DECISION_NOT_YET_AVAILABLE")
        if not feature.analytical_eligible:
            reasons.add("UNIVERSE_INELIGIBLE")
        if any(feature.values[n].value is None for n in columns):
            reasons.add("FEATURE_UNAVAILABLE")
        if not allow_degraded and any(
            feature.values[n].state != Availability.AVAILABLE for n in columns
        ):
            reasons.add("FEATURE_QUALITY_NOT_ACCEPTED")
        if (
            label.maturity == "NOT_YET_MATURE"
            or label.label_available_at is not None
            and label.label_available_at > training_as_of
        ):
            reasons.add("LABEL_NOT_MATURE")
        elif (
            label.maturity != "MATURE"
            or label.return_value is None
            or label.label_available_at is None
        ):
            reasons.add("LABEL_UNAVAILABLE")
        if label.quality_state == Availability.DEGRADED and not allow_degraded:
            reasons.add("LABEL_QUALITY_NOT_ACCEPTED")
        if any("CORPORATE_ACTION_UNADJUSTED" in reason for reason in label.reason_codes):
            # Never admit a known discontinuity as clean strategy economics.
            reasons.add("CORPORATE_ACTION_UNADJUSTED")
        eligible = not reasons
        # Targets after training_as_of stay NULL even though artifact scope may be later.
        visible = (
            label.maturity == "MATURE"
            and label.label_available_at is not None
            and label.label_available_at <= training_as_of
        )
        rows.append(
            AlignedRow(
                features={n: feature.values[n].value for n in columns},
                targets={
                    target_columns[0]: str(label.return_value) if visible else None,
                    target_columns[1]: label.direction_value if visible else None,
                },
                metadata=dict(
                    security_id=feature.security_id,
                    session_date=feature.session_date.isoformat(),
                    decision_time=feature.decision_time.isoformat(),
                    feature_canonical_dataset_id=feature.canonical_dataset_id,
                    universe_snapshot_id=feature.universe_snapshot_id,
                    label_available_at=label.label_available_at.isoformat()
                    if label.label_available_at
                    else None,
                    classification=feature.classification,
                    training_eligibility="TRAINING_ELIGIBLE"
                    if eligible
                    else "NOT_TRAINING_ELIGIBLE",
                    reason_codes=tuple(sorted(reasons)),
                ),
            )
        )
    dataset = SupervisedDataset(
        supervised_dataset_id="0" * 64,
        feature_set_id=features.feature_set_id,
        label_set_id=labels.label_set_id,
        feature_columns=columns,
        target_columns=target_columns,
        classification=features.classification,
        training_as_of=training_as_of,
        horizon=horizon,
        allow_degraded=allow_degraded,
        rows=tuple(rows),
    )
    return dataset.model_copy(
        update={
            "supervised_dataset_id": checksum(
                stable_json(dataset.model_dump(mode="json", exclude={"supervised_dataset_id"}))
            )
        }
    )
