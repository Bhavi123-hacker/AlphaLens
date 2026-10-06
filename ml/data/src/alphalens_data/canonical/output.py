"""Deterministic typed analytical projection; immutable JSON retains full evidence."""

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_data.canonical.models import SCHEMA_VERSION, CanonicalDataset, revision_key


def parquet_bytes(dataset: CanonicalDataset) -> bytes:
    schema = pa.schema(
        [
            pa.field("record_key", pa.string(), nullable=False),
            pa.field("security_id", pa.string(), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("revision_id", pa.string(), nullable=False),
            pa.field("price_basis", pa.string(), nullable=False),
            *[pa.field(n, pa.decimal128(38, 18)) for n in ("open", "high", "low", "close")],
            pa.field("volume", pa.int64()),
            pa.field("turnover", pa.decimal128(38, 18)),
            pa.field("trade_count", pa.int64()),
            pa.field("vwap", pa.decimal128(38, 18)),
            pa.field("currency", pa.string()),
            pa.field("published_at", pa.timestamp("us", tz="UTC")),
            pa.field("session_close_at", pa.timestamp("us", tz="UTC")),
            pa.field("available_at", pa.timestamp("us", tz="UTC")),
            pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("artifact_sha256", pa.string(), nullable=False),
            pa.field("quality_key", pa.string()),
            pa.field("corporate_action_key", pa.string()),
            pa.field("original_price_key", pa.string()),
            pa.field("classification", pa.string(), nullable=False),
            pa.field("quality", pa.string(), nullable=False),
            pa.field("availability", pa.string(), nullable=False),
            pa.field("universe_membership", pa.bool_(), nullable=False),
            pa.field("analysis_eligible", pa.bool_(), nullable=False),
        ],
        metadata={
            b"canonical_schema_version": SCHEMA_VERSION.encode(),
            b"dataset_id": dataset.dataset_id.encode(),
            b"input_id": dataset.input_id.encode(),
            b"knowledge_cutoff": dataset.context.knowledge_cutoff.isoformat().encode(),
        },
    )
    rows: list[dict[str, object]] = []
    for view in dataset.prices:
        record = view.observation
        row: dict[str, object] = dict(
            record_key=revision_key(record),
            security_id=record.security_id,
            session_date=record.session_date,
            revision_id=record.revision_id,
            price_basis=record.price_basis,
            currency=record.currency,
            available_at=record.provenance.available_at,
            ingested_at=record.provenance.ingested_at,
            source=record.provenance.source,
            artifact_sha256=record.provenance.artifact_sha256,
            published_at=record.provenance.published_at,
            session_close_at=record.session_close_at,
            quality_key=record.quality_key,
            corporate_action_key=record.adjustment.corporate_action_key
            if record.adjustment
            else None,
            original_price_key=record.adjustment.original_price_key if record.adjustment else None,
            classification=record.provenance.classification,
            quality=view.quality,
            availability=view.availability,
            universe_membership=view.universe_membership,
            analysis_eligible=view.analysis_eligible,
        )
        row.update(
            {
                n: getattr(record.values, n) if record.values else None
                for n in (
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "turnover",
                    "trade_count",
                    "vwap",
                )
            }
        )
        rows.append(row)
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
