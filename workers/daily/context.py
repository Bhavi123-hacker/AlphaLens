"""Bounded column-projected research history, never training labels or predictions."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds
from scripts.acquire_tejhq_research import digest_file

from alphalens_data.daily.contracts import Calendar
from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum

CANONICAL_ID = "37693f7796bc42b4c33fad117196c6a75545dd690d5edd7f597204bc7e24f490"


def trailing(
    root: Path,
    security_ids: tuple[str, ...],
    calendar: Calendar,
    session: date,
    cutoff: datetime,
    maximum_securities: int = 128,
) -> list[dict[str, Any]]:
    if not security_ids or len(set(security_ids)) > maximum_securities:
        raise DataContractError("EXPLICIT_BOUNDED_SECURITY_SCOPE_REQUIRED")
    manifest = json.loads((root / "canonical-manifest.json").read_bytes())
    if manifest["dataset_id"] != CANONICAL_ID:
        raise DataContractError("FROZEN_CANONICAL_BASELINE_MISMATCH")
    dates = calendar.trailing(session, cutoff, 201)
    if not dates:
        return []
    buckets = {int(checksum(s.encode())[:8], 16) % 64 for s in security_ids}
    output = []
    columns = [
        "security_id",
        "session_date",
        "close",
        "high",
        "low",
        "volume",
        "quality",
        "analytical_type",
        "economic_action",
        "assumed_available_at",
    ]
    for bucket in sorted(buckets):
        relative = f"canonical/bucket-{bucket:02}.parquet"
        entry = next(
            f for f in manifest["identity"]["files"] if f["path"].replace("\\", "/") == relative
        )
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or digest_file(path) != entry["sha256"]:
            raise DataContractError("FROZEN_CONTEXT_CHECKSUM_MISMATCH")
        predicate = ds.field("security_id").isin(security_ids) & ds.field("session_date").isin(
            dates
        )
        for batch in (
            ds.dataset(path, format="parquet")
            .scanner(columns=columns, filter=predicate, batch_size=4096)
            .to_batches()
        ):
            for row in batch.to_pylist():
                if row["session_date"] >= session or row["assumed_available_at"] > cutoff:
                    continue
                row["session_date"] = row["session_date"].isoformat()
                row["received_at"] = row.pop("assumed_available_at").isoformat()
                for name in ("close", "high", "low"):
                    row[name] = str(row[name])
                output.append(row)
    return sorted(output, key=lambda r: (r["security_id"], r["session_date"]))
