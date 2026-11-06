"""Explicit progressive archive reads: bounded per request, cancelled by stopping steps."""

import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import Field, JsonValue
from starlette.concurrency import run_in_threadpool
from workers.personal.contracts import Closed, Profile
from workers.personal.historical import rank, reduce_partition

from .artifacts import confined
from .core.domain_errors import APIError
from .personal import body, profile, safe
from .projection import date_rows
from .routes import Research
from .schemas import Envelope

router = APIRouter(prefix="/api/v1/personal/historical-scan", tags=["bounded archive discovery"])


class Inputs(Closed):
    start: date
    end: date
    category: Literal[
        "price_return", "risk_adjusted", "drawdown", "consistency", "low_volatility", "volume"
    ] = "price_return"
    size: Literal[5, 10, 20] = 10
    apply_preferences: bool = False
    comparison_mode: Literal["strict", "available_window", "observed_endpoints"] = "strict"
    securities: list[str] = Field(default_factory=list, max_length=20)


@dataclass
class Scan:
    owner: str
    inputs: Inputs
    profile: Profile
    manifest: dict[str, Any]
    sessions: list[str]
    created: float = field(default_factory=time.monotonic)
    position: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    session_coverage: Counter[str] = field(default_factory=Counter)
    lock: threading.Lock = field(default_factory=threading.Lock)


_lock = threading.Lock()
_scans: dict[str, Scan] = {}


@router.post("/cancel")
async def cancel(request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"scan_id"} or not isinstance(value["scan_id"], str):
        raise APIError("INVALID_REQUEST", "Provide an owned scan identifier.", 422)
    with _lock:
        scan = _scans.get(value["scan_id"])
        if scan and scan.owner != request.state.operator["account_id"]:
            raise APIError(
                "HISTORICAL_SCAN_OWNER_REQUIRED", "The initiating operator is required.", 403
            )
        _scans.pop(value["scan_id"], None)
    return service.response({"cancelled": True}, "EXPLICIT_HISTORICAL_READ_CANCELLED")


@router.post("/prepare")
async def prepare(request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    options = safe(lambda: Inputs.model_validate(value))
    if options.start > options.end or (options.end - options.start).days > 1830:
        raise APIError(
            "HISTORICAL_WINDOW_INVALID", "Choose an ordered window of at most five years.", 422
        )
    calendar = service.reader.calendar()["sessions"]
    if not calendar or options.end > date.fromisoformat(max(s["session_date"] for s in calendar)):
        raise APIError(
            "HISTORICAL_WINDOW_AFTER_ARCHIVE", "The selected end exceeds the frozen archive.", 422
        )
    sessions = [
        s["session_date"]
        for s in calendar
        if str(options.start) <= s["session_date"] <= str(options.end)
    ]
    if len(sessions) < 2:
        raise APIError(
            "HISTORICAL_WINDOW_EMPTY", "Choose at least two observed-calendar slots.", 422
        )
    preferences = safe(lambda: profile(request))
    manifest = service.reader.manifest("canonical-manifest.json")
    identity = uuid4().hex
    with _lock:
        for key in list(_scans):
            if time.monotonic() - _scans[key].created >= 900 or _scans[key].position >= len(
                _scans[key].manifest["identity"]["files"]
            ):
                _scans.pop(key)
        if len(_scans) >= 4:
            raise APIError(
                "HISTORICAL_SCAN_CAPACITY", "Finish or cancel an existing archive scan.", 429
            )
        _scans[identity] = Scan(
            request.state.operator["account_id"], options, preferences, manifest, sessions
        )
    return service.response(
        {
            "scan_id": identity,
            "completed_partitions": 0,
            "total_partitions": len(manifest["identity"]["files"]),
            "provider_requests": 0,
            "background_work": False,
            "source": "FROZEN_ARCHIVE_ONLY",
            "expires_in_seconds": 900,
        },
        "EXPLICIT_BOUNDED_HISTORICAL_READ_PREPARATION",
    )


@router.post("/step")
async def step(request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"scan_id"} or not isinstance(value["scan_id"], str):
        raise APIError("INVALID_REQUEST", "Provide the owned scan identifier.", 422)
    return await run_in_threadpool(advance, request, service, value["scan_id"])


def advance(request: Request, service: Research, identity: str) -> Envelope[JsonValue]:
    with _lock:
        scan = _scans.get(identity)
    if not scan or time.monotonic() - scan.created >= 900:
        raise APIError("HISTORICAL_SCAN_EXPIRED", "Restart the explicit archive read.", 410)
    if scan.owner != request.state.operator["account_id"]:
        raise APIError(
            "HISTORICAL_SCAN_OWNER_REQUIRED", "The initiating operator is required.", 403
        )
    if not scan.lock.acquire(blocking=False):
        raise APIError("READ_CAPACITY", "This archive scan is already processing one step.", 429)
    try:
        entries = scan.manifest["identity"]["files"]
        root = service.reader.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "The research archive is unavailable.", 503)
        if scan.position < len(entries):
            entry = entries[scan.position]
            with service.reader.budget() as deadline:
                path = service.reader.verify(
                    confined(root, entry["path"]), entry["sha256"], deadline
                )
                rows, more = date_rows(
                    path,
                    [
                        "security_id",
                        "session_date",
                        "symbol",
                        "isin",
                        "analytical_type",
                        "close",
                        "volume",
                        "quality",
                    ],
                    scan.inputs.start,
                    scan.inputs.end,
                    250000,
                    deadline,
                )
                if more:
                    raise APIError("HISTORICAL_PARTITION_LIMIT", "Narrow the archive window.", 422)
                if scan.inputs.securities:
                    rows = [r for r in rows if r["security_id"] in scan.inputs.securities]
                scan.session_coverage.update(
                    str(r["session_date"])
                    for r in rows
                    if r["close"] is not None
                    and r["quality"] in {"VALID", "DEGRADED"}
                    and r["analytical_type"] == "RESEARCH_EQUITY_CANDIDATE"
                )
                reduced = reduce_partition(
                    rows, scan.sessions, scan.profile, scan.inputs.comparison_mode
                )
                if time.monotonic() > deadline:
                    raise APIError("QUERY_TIMEOUT", "Narrow the archive window.", 504)
                if {r["security_id"] for r in scan.rows}.intersection(
                    r["security_id"] for r in reduced
                ):
                    raise APIError(
                        "HISTORICAL_IDENTITY_PARTITION_CONFLICT",
                        "Archive identity partitions overlap.",
                        409,
                    )
                scan.rows.extend(reduced)
                scan.position += 1
        complete = scan.position == len(entries)
        result = (
            rank(scan.rows, scan.inputs.category, scan.inputs.size, scan.inputs.apply_preferences)
            if complete
            else None
        )
        if result:
            result.update(
                latency_ms=round((time.monotonic() - scan.created) * 1000),
                artifact_id=scan.manifest["dataset_id"],
                start=str(scan.inputs.start),
                end=str(scan.inputs.end),
                actual_first_session=scan.sessions[0],
                actual_last_session=scan.sessions[-1],
                comparison_mode=scan.inputs.comparison_mode,
                slots_with_zero_observed_equities=[
                    day for day in scan.sessions if not scan.session_coverage[day]
                ],
            )
        return service.response(
            {
                "scan_id": identity,
                "completed_partitions": scan.position,
                "total_partitions": len(entries),
                "complete": complete,
                "observed_identities_so_far": len(scan.rows),
                "provider_requests": 0,
                "result": result,
            },
            "CHECKSUM_VERIFIED_PROGRESSIVE_HISTORICAL_READ",
        )
    finally:
        scan.lock.release()
