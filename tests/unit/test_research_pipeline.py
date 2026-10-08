"""TEST_ONLY partitioned P5-P7 replay with a real-calendar missing-slot contract."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts import build_tejhq_research as replay
from scripts.acquire_tejhq_research import digest_file

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchProfile, calendar, lineage


def test_partitioned_features_labels_preserve_missing_slots_and_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_save = replay.save

    def save(path: Path, value: Any) -> None:
        original_save(tmp_path / path if str(path).startswith("docs") else path, value)

    monkeypatch.setattr(replay, "save", save)
    start = date(2023, 1, 2)
    observed = {
        start + timedelta(days=i) for i in range(365) if (start + timedelta(days=i)).weekday() < 5
    }
    profile = ResearchProfile()
    sessions = calendar(observed, profile)
    save(tmp_path / "research-calendar.json", sessions.model_dump(mode="json"))
    rows = []
    for s in range(2):
        for i, day in enumerate(sorted(observed)):
            price = Decimal(str(100 + s * 10 + i / 10 + np.sin(i / 5)))
            rows.append(
                dict(
                    security_id=f"TEST_ONLY_{s}",
                    session_date=day,
                    symbol=f"TEST_ONLY_{s}",
                    isin=None,
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    volume=1000 + i % 50,
                    quality="VALID",
                    quality_reasons=[],
                    analytical_type="RESEARCH_EQUITY_CANDIDATE",
                    economic_action=False,
                    canonical_record_id=checksum(f"TEST_ONLY:{s}:{day}".encode()),
                    assumed_available_at=sessions.availability(day),
                )
            )
    directory = tmp_path / "canonical"
    directory.mkdir()
    path = directory / "bucket-00.parquet"
    schema = replay.CANONICAL_SCHEMA.with_metadata(
        {b"research_lineage": stable_json(lineage(profile))}
    )
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    identity = dict(
        **lineage(profile),
        calendar_id=sessions.calendar_id,
        files=[
            dict(
                path=str(path.relative_to(tmp_path)),
                rows=len(rows),
                sha256=digest_file(path),
            )
        ],
    )
    save(
        tmp_path / "canonical-manifest.json",
        dict(identity=identity, dataset_id=checksum(stable_json(identity))),
    )
    result = replay.features_stage(tmp_path)
    assert result["feature_rows"] == len(rows)
    assert result["identity"]["final_vintage"] == "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
    report = json.loads((tmp_path / "docs/ml/feature-availability.json").read_bytes())
    assert report["availability"]["sma_200"]["available_count"] > 0
    assert report["missing_muhurat_affected"]["sma_200"] > 0
    output = pq.ParquetFile(tmp_path / "features-labels/bucket-00.parquet").read()
    assert date(2023, 11, 12) not in output.column("session_date").to_pylist()
    previous = [r for r in output.to_pylist() if r["session_date"] == date(2023, 11, 10)]
    assert len(previous) == 2
    assert all(
        r["maturity_1"] == "UNAVAILABLE"
        and r["target_return_1"] is None
        and not r["training_eligible_1"]
        for r in previous
    )
    following = [r for r in output.to_pylist() if r["session_date"] == date(2023, 11, 13)]
    assert all(r["sma_200"] is None for r in following)
