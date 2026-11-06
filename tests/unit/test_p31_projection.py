"""TEST_ONLY projection parity: boundaries, null prices and missing statistics."""

import time
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest

from alphalens_api.core.domain_errors import APIError
from alphalens_api.projection import date_rows


@pytest.mark.parametrize("statistics", [True, False])
def test_projection_preserves_exact_rows_and_excludes_only_out_of_window_dates(
    tmp_path: Path, statistics: bool
) -> None:
    path = tmp_path / "TEST_ONLY.parquet"
    rows = [
        {
            "security_id": "TEST_ONLY_B",
            "session_date": date(2020, 1, 4),
            "close": Decimal("100.123456789"),
            "quality": "TEST_ONLY_UNKNOWN",
        },
        {
            "security_id": "TEST_ONLY_A",
            "session_date": date(2020, 1, 3),
            "close": None,
            "quality": "TEST_ONLY_MISSING",
        },
        {
            "security_id": "TEST_ONLY_C",
            "session_date": date(2020, 1, 5),
            "close": Decimal("101"),
            "quality": "TEST_ONLY_FUTURE",
        },
        {
            "security_id": "TEST_ONLY_D",
            "session_date": date(2020, 1, 2),
            "close": Decimal("99"),
            "quality": "TEST_ONLY_OLD",
        },
    ]
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, row_group_size=1, write_statistics=statistics)
    start, end = date(2020, 1, 3), date(2020, 1, 4)
    expected = (
        ds.dataset(path, format="parquet")
        .to_table(filter=(ds.field("session_date") >= start) & (ds.field("session_date") <= end))
        .to_pylist()
    )
    expected.sort(key=lambda r: (r["security_id"], r["session_date"]))
    actual, more = date_rows(path, table.column_names, start, end, 10, time.monotonic() + 10)
    assert actual == expected and more is False
    assert actual[0]["close"] is None and actual[1]["close"] == Decimal("100.123456789")
    assert date_rows(path, table.column_names, start, end, 1, time.monotonic() + 10) == ([], True)
    with pytest.raises(APIError, match="read budget"):
        date_rows(path, table.column_names, start, end, 10, time.monotonic() - 1)
