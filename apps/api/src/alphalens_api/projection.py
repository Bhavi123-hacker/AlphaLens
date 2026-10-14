"""Bounded Parquet date projection. Same rows/values; missing statistics never prune."""

import time
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .core.domain_errors import APIError


def date_rows(
    path: Path, columns: list[str], start: date, end: date, limit: int, deadline: float
) -> tuple[list[dict[str, Any]], bool]:
    parquet = pq.ParquetFile(path)
    date_columns = [
        i
        for i in range(len(parquet.schema.names))
        if parquet.schema.column(i).path == "session_date"
    ]
    if len(date_columns) != 1:
        raise APIError("ARTIFACT_SCHEMA_INVALID", "A unique stored session date is required.")
    groups = []
    for index in range(parquet.metadata.num_row_groups):
        if time.monotonic() > deadline:
            raise APIError("QUERY_TIMEOUT", "Market snapshot exceeded its read budget.", 504)
        stats = parquet.metadata.row_group(index).column(date_columns[0]).statistics
        if stats is not None and stats.has_min_max:
            lo, hi = stats.min, stats.max
            # Only exact DATE metadata can exclude a row group. Unknown/missing
            # statistics remain in scope; actual rows always receive the filter.
            if type(lo) is date and type(hi) is date and lo <= hi and (hi < start or lo > end):
                continue
        groups.append(index)
    rows: list[dict[str, Any]] = []
    # Coarse feature files avoid repeated native/Python batch boundaries;
    # fragmented canonical files keep small batches after date pruning.
    batch_size = 65536 if parquet.metadata.num_row_groups <= 8 else 4096
    for batch in parquet.iter_batches(
        row_groups=groups, columns=columns, batch_size=batch_size, use_threads=False
    ):
        if time.monotonic() > deadline:
            raise APIError("QUERY_TIMEOUT", "Market snapshot exceeded its read budget.", 504)
        dates = batch.column(batch.schema.get_field_index("session_date"))
        mask = pc.and_(
            pc.greater_equal(dates, pa.scalar(start)), pc.less_equal(dates, pa.scalar(end))
        )
        rows.extend(batch.filter(mask).to_pylist())
        if len(rows) > limit:
            return [], True
    rows.sort(key=lambda row: (row["security_id"], row["session_date"]))
    return rows, False
