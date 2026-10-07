"""Offline publisher-native TejHQ Parquet adapter into existing P2 row contracts.

Source float64 values become their round-trip decimal text, not reconstructed
exchange decimals. No historical clocks, asset types or ISIN backfill are inferred.
"""

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pyarrow.parquet as pq

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.normalization import checksum

VERSION = "tejhq.parquet.v1"
REQUIRED = {"date", "symbol", "series", "isin", "name", "open", "high", "low", "close", "volume"}


def observed_id(row: dict[str, Any]) -> str:
    if row.get("isin"):
        return f"tejhq:isin:{row['isin']}"
    return (
        f"tejhq:symbol:{quote(row.get('symbol') or '', safe='')}:"
        f"{quote(row.get('series') or '', safe='')}"
    )


def parse_batch(
    rows: list[dict[str, Any]], first_row: int, duplicates: set[tuple[str, date]] | None = None
) -> tuple[ParsedRow, ...]:
    result = []
    for number, row in enumerate(rows, first_row):
        names = tuple(sorted(row))
        original = tuple("" if row[n] is None else str(row[n]) for n in names)
        session = row.get("date")
        security = observed_id(row)
        fields = tuple(
            (name, "" if value is None else str(value))
            for name, value in (
                ("security_id", security if row.get("isin") else ""),
                ("session_date", session),
                ("symbol", row.get("symbol")),
                ("isin", row.get("isin")),
                ("series", row.get("series")),
                ("source_row_identifier", f"parquet-row:{number - 2}"),
                *((name, row.get(name)) for name in ("open", "high", "low", "close", "volume")),
            )
        )
        error = None
        if not row.get("symbol"):
            error = "REQUIRED_IDENTIFIER"
        elif duplicates and (security, session) in duplicates:
            error = "DUPLICATE_SECURITY_SESSION_VERSION"
        result.append(ParsedRow(number, original, fields, error))
    return tuple(result)


def iter_batches(
    path: Path,
    batch_size: int = 4096,
    duplicates: set[tuple[str, date]] | None = None,
    shards: int = 1,
    shard_index: int = 0,
) -> Iterator[tuple[ParsedRow, ...]]:
    if shards < 1 or not 0 <= shard_index < shards:
        raise ValueError("INVALID_IDENTITY_SHARD")
    source = pq.ParquetFile(path)
    if not REQUIRED.issubset(source.schema_arrow.names):
        raise DataContractError("TEJHQ_SCHEMA_MISSING_REQUIRED_COLUMNS")
    first = 2  # P2/P3 row-number contract; row 2 means zero-based Parquet row 0.
    for batch in source.iter_batches(batch_size=batch_size):
        rows = batch.to_pylist()
        parsed = parse_batch(rows, first, duplicates)
        if shards > 1:
            parsed = tuple(
                r
                for r in parsed
                if int(checksum(observed_id(rows[r.row_number - first]).encode())[:16], 16) % shards
                == shard_index
            )
        if parsed:
            yield parsed
        first += len(rows)
