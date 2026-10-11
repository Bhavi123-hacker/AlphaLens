"""Explicit TEST_ONLY P19 fixtures; never used as runtime market data."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from workers.daily.features import definitions

from alphalens_data.daily.contracts import Calendar, Provider, Request, Session
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum

AT = datetime(2026, 10, 9, 12, tzinfo=UTC)
DAY = date(2026, 10, 8)


def calendar(days: list[date]) -> Calendar:
    return Calendar(
        sessions=tuple(
            Session(
                session=d,
                status="TRADING",
                known_at=AT - timedelta(days=900),
                evidence_reference="TEST_ONLY_CALENDAR",
                evidence_type="TEST_ONLY",
            )
            for d in days
        )
    )


def request(payload: Path | None = None, history: list[dict[str, Any]] | None = None) -> Request:
    return Request(
        mode="TEST_ONLY",
        session=DAY,
        source_received_at=AT,
        provider=Provider(
            revision="TEST_ONLY", status="SOURCE_NOT_CLEARED", evidence_reference="TEST_ONLY"
        ),
        calendar=calendar([DAY]),
        baseline_identity="a" * 64,
        feature_registry_id=checksum(
            stable_json([d.model_dump(mode="json") for d in definitions(DAY, AT)])
        ),
        payload_sha256=checksum(payload.read_bytes()) if payload else None,
        context_sha256=checksum(stable_json(history or [])),
    )


def parquet(
    path: Path, *, close: float = 101, isin: str = "INE000A01001", name: str = "TEST_ONLY LIMITED"
) -> Path:
    pq.write_table(
        pa.Table.from_pylist(
            [
                dict(
                    date=DAY,
                    symbol="TEST_ONLY",
                    series="EQ",
                    isin=isin,
                    name=name,
                    open=100.0,
                    high=102.0,
                    low=99.0,
                    close=close,
                    volume=1000,
                )
            ]
        ),
        path,
    )
    return path
