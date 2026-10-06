"""Lossless decimal text targets, deterministic artifacts and descriptive fixture statistics."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, localcontext
from statistics import mean, median, stdev

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_data.ingestion.storage import stable_json
from alphalens_labels.alignment import SupervisedDataset
from alphalens_labels.models import LabelDataset


def manifest(dataset: LabelDataset) -> dict[str, object]:
    return dict(
        label_set_id=dataset.label_set_id,
        schema_version=dataset.schema_version,
        canonical_dataset_id=dataset.canonical_dataset_id,
        canonical_input_id=dataset.canonical_input_id,
        feature_set_compatibility=dataset.feature_set_id,
        classification=dataset.classification,
        universe_definition_version=dataset.universe_definition_version,
        label_definitions=[d.model_dump(mode="json") for d in dataset.definitions],
        horizons=dataset.plan.horizons,
        parameters=dataset.plan.model_dump(mode="json"),
        price_basis=dataset.definitions[0].price_basis,
        row_count=len(dataset.rows),
        maturity_counts=dict(Counter(r.maturity for r in dataset.rows)),
        quality_counts=dict(Counter(r.quality_state for r in dataset.rows)),
        first_session=min(r.session_date for r in dataset.rows).isoformat()
        if dataset.rows
        else None,
        last_session=max(r.session_date for r in dataset.rows).isoformat()
        if dataset.rows
        else None,
        corporate_action_coverage=dataset.corporate_action_coverage,
        production_claims_permitted=False,
    )


def distribution(dataset: LabelDataset) -> dict[str, object]:
    report: dict[str, object] = dict(
        classification=dataset.classification,
        report_scope="DESCRIPTIVE_FIXTURE_OUTCOMES_ONLY_NO_PREDICTIVE_SUCCESS",
        label_set_id=dataset.label_set_id,
        production_claims_permitted=False,
    )
    horizons: dict[str, object] = {}
    with localcontext() as context:
        context.prec = 76
        for horizon in dataset.plan.horizons:
            rows = [r for r in dataset.rows if r.horizon == horizon]
            values = [r.return_value for r in rows if r.return_value is not None]
            horizons[str(horizon)] = dict(
                count=len(values),
                total_count=len(rows),
                mean=str(mean(values)) if values else None,
                median=str(median(values)) if values else None,
                standard_deviation=str(stdev(values)) if len(values) > 1 else None,
                positive_proportion=str(Decimal(sum(v > 0 for v in values)) / len(values))
                if values
                else None,
                missing_proportion=str(Decimal(len(rows) - len(values)) / len(rows))
                if rows
                else None,
            )
    report["horizons"] = horizons
    return report


def _parquet(rows: list[dict[str, object]], schema: pa.Schema) -> bytes:
    buffer = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema),
        buffer,
        compression="NONE",
        use_dictionary=False,
        write_statistics=False,
        version="2.6",
    )
    return bytes(buffer.getvalue())


def parquet_bytes(dataset: LabelDataset) -> bytes:
    schema = pa.schema(
        [
            pa.field("security_id", pa.string(), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("decision_time", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("horizon", pa.int32(), nullable=False),
            pa.field("entry_session", pa.date32()),
            pa.field("target_session", pa.date32()),
            pa.field("label_available_at", pa.timestamp("us", tz="UTC")),
            *[
                pa.field(n, pa.string())
                for n in (
                    "return_value",
                    "entry_price",
                    "exit_price",
                    "exact_numerator",
                    "exact_denominator",
                )
            ],
            pa.field("direction_value", pa.int8()),
            *[
                pa.field(n, pa.string(), nullable=False)
                for n in (
                    "maturity",
                    "quality_state",
                    "classification",
                    "price_basis",
                    "canonical_dataset_id",
                    "feature_canonical_dataset_id",
                    "universe_snapshot_id",
                )
            ],
            pa.field("label_evidence_json", pa.string(), nullable=False),
        ],
        metadata={
            b"manifest": stable_json(manifest(dataset)),
            b"label_set_id": dataset.label_set_id.encode(),
            b"schema_version": dataset.schema_version.encode(),
            b"decimal_encoding": b"LOSSLESS_TEXT_PRECISION_38_WITH_EXACT_RATIONAL_EVIDENCE",
        },
    )
    rows: list[dict[str, object]] = []
    for row in dataset.rows:
        values = {
            name: getattr(row, name) for name in schema.names if name != "label_evidence_json"
        }
        for name in (
            "return_value",
            "entry_price",
            "exit_price",
            "exact_numerator",
            "exact_denominator",
        ):
            value = getattr(row, name)
            values[name] = str(value) if value is not None else None
        values["label_evidence_json"] = stable_json(row.model_dump(mode="json")).decode()
        rows.append(values)
    return _parquet(rows, schema)


def supervised_parquet(dataset: SupervisedDataset) -> bytes:
    schema = pa.schema(
        [
            *[pa.field(n, pa.float64()) for n in dataset.feature_columns],
            *[
                pa.field(n, pa.int8() if "direction" in n else pa.string())
                for n in dataset.target_columns
            ],
            pa.field("security_id", pa.string(), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("decision_time", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("feature_canonical_dataset_id", pa.string(), nullable=False),
            pa.field("universe_snapshot_id", pa.string(), nullable=False),
            pa.field("label_available_at", pa.timestamp("us", tz="UTC")),
            pa.field("classification", pa.string(), nullable=False),
            pa.field("training_eligibility", pa.string(), nullable=False),
            pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        ],
        metadata={
            b"alignment_contract": stable_json(dataset.model_dump(mode="json", exclude={"rows"})),
            b"feature_columns": stable_json(dataset.feature_columns),
            b"target_columns": stable_json(dataset.target_columns),
            b"metadata_columns": stable_json(dataset.metadata_columns),
        },
    )
    rows: list[dict[str, object]] = []
    for row in dataset.rows:
        data: dict[str, object] = dict(row.features)
        data.update(row.targets)
        data.update(row.metadata)
        data["session_date"] = date.fromisoformat(str(row.metadata["session_date"]))
        data["decision_time"] = datetime.fromisoformat(str(row.metadata["decision_time"]))
        available_at = row.metadata["label_available_at"]
        data["label_available_at"] = (
            datetime.fromisoformat(str(available_at)) if available_at is not None else None
        )
        rows.append(data)
    return _parquet(rows, schema)
