"""Deterministic float64 feature matrix plus full immutable JSON evidence and manifest."""

from collections import Counter

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_data.ingestion.storage import stable_json
from alphalens_features.models import FeatureDataset


def manifest(dataset: FeatureDataset) -> dict[str, object]:
    rows = dataset.rows
    return dict(
        feature_set_id=dataset.feature_set_id,
        feature_set_version=dataset.schema_version,
        canonical_dataset_id=dataset.canonical_dataset_id,
        canonical_input_id=dataset.canonical_input_id,
        universe_definition_version=dataset.universe_definition_version,
        feature_definitions=[d.model_dump(mode="json") for d in dataset.feature_set.definitions],
        parameters=dataset.feature_set.plan.model_dump(mode="json"),
        created_with=dataset.schema_version,
        classification=dataset.classification,
        price_basis=dataset.feature_set.plan.price_basis,
        first_session=min(r.session_date for r in rows).isoformat() if rows else None,
        last_session=max(r.session_date for r in rows).isoformat() if rows else None,
        security_count=len({r.security_id for r in rows}),
        row_count=len(rows),
        feature_count=len(dataset.feature_set.definitions),
        unavailable_counts={
            d.feature_name: sum(r.values[d.feature_name].value is None for r in rows)
            for d in dataset.feature_set.definitions
        },
        quality_counts=dict(Counter(r.quality_state for r in rows)),
        fundamental_pit_data="UNAVAILABLE",
        corporate_action_coverage=dataset.corporate_action_coverage,
        production_claims_permitted=False,
    )


def parquet_bytes(dataset: FeatureDataset) -> bytes:
    names = [d.feature_name for d in dataset.feature_set.definitions]
    schema = pa.schema(
        [
            pa.field("security_id", pa.string(), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("decision_time", pa.timestamp("us", tz="UTC"), nullable=False),
            *[
                pa.field(n, pa.string(), nullable=False)
                for n in (
                    "canonical_dataset_id",
                    "universe_snapshot_id",
                    "classification",
                    "price_basis",
                    "quality_state",
                    "feature_set_version",
                )
            ],
            pa.field("analytical_eligible", pa.bool_(), nullable=False),
            *[pa.field(n, pa.float64()) for n in names],
            pa.field("feature_evidence_json", pa.string(), nullable=False),
        ],
        metadata={
            b"manifest": stable_json(manifest(dataset)),
            b"feature_set_id": dataset.feature_set_id.encode(),
            b"schema_version": dataset.schema_version.encode(),
        },
    )
    rows = []
    for row in dataset.rows:
        data = {
            n: getattr(row, n)
            for n in (
                "security_id",
                "session_date",
                "decision_time",
                "canonical_dataset_id",
                "universe_snapshot_id",
                "classification",
                "price_basis",
                "quality_state",
                "feature_set_version",
                "analytical_eligible",
            )
        }
        data.update({n: row.values[n].value for n in names})
        data["feature_evidence_json"] = stable_json(row.model_dump(mode="json")).decode()
        rows.append(data)
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
