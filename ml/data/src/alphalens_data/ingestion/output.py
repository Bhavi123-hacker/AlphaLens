"""Exact typed Parquet plus authoritative deterministic canonical JSON."""

import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_data.ingestion.contracts import CanonicalEOD, RawManifest


def parquet_bytes(records: tuple[CanonicalEOD, ...], manifest: RawManifest) -> bytes:
    fields = CanonicalEOD.model_fields
    decimals = {"open", "high", "low", "close"}
    integers = {"volume", "source_row_number"}
    timestamps = {"acquired_at", "session_close_at", "published_at", "available_at"}
    schema = pa.schema(
        [
            pa.field(
                name,
                pa.decimal128(38, 18)
                if name in decimals
                else pa.int64()
                if name in integers
                else pa.timestamp("us", tz="UTC")
                if name in timestamps
                else pa.date32()
                if name == "session_date"
                else pa.bool_()
                if name == "production_claims_permitted"
                else pa.string(),
            )
            for name in fields
        ],
        metadata={
            b"classification": manifest.spec.classification.value.encode(),
            b"artifact_id": manifest.artifact_id.encode(),
            b"schema_version": manifest.versions.schema_version.encode(),
            b"production_claims_permitted": b"false",
        },
    )
    rows = []
    for record in records:
        value = record.model_dump()
        value["versions"] = record.versions.model_dump_json()
        rows.append(value)
    table = pa.Table.from_pylist(rows, schema=schema)
    stream = pa.BufferOutputStream()
    pq.write_table(table, stream, compression="zstd", version="2.6")
    return bytes(stream.getvalue().to_pybytes())
