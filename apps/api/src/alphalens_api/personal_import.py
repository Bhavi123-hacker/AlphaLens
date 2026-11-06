"""Owned CSV preview/confirmation, exact shared rules and atomic all-or-none commit."""

import csv
import io
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import JsonValue
from starlette.concurrency import run_in_threadpool
from workers.personal.contracts import ManualEntry
from workers.personal.store import apply_entry

from .core.domain_errors import APIError
from .personal import body, safe, store, verified, wrap
from .routes import Research
from .schemas import Envelope

router = APIRouter(
    prefix="/api/v1/personal/portfolios", tags=["confirmed owned manual CSV records"]
)


@dataclass
class Preview:
    owner: str
    portfolio: str
    revision: int
    entries: list[tuple[ManualEntry, dict[str, Any] | None]]
    created: float = field(default_factory=time.monotonic)
    confirmed: bool = False


_lock = threading.Lock()
_previews: dict[str, Preview] = {}
FIELDS = {
    "kind",
    "isin",
    "symbol",
    "session",
    "quantity",
    "price",
    "fees",
    "fees_known",
    "cash_amount",
    "notes",
}


def _prepare(identity: str, request: Request, service: Research, text: str) -> dict[str, Any]:
    owned = store(request)
    current = owned.get("portfolios", identity)
    reader = csv.DictReader(io.StringIO(text.removeprefix("\ufeff")), strict=True)
    if (
        not reader.fieldnames
        or len(reader.fieldnames) != len(FIELDS)
        or set(reader.fieldnames) != FIELDS
    ):
        raise ValueError("MANUAL_CSV_EXACT_HEADER_REQUIRED")
    value = current["value"]
    entries: list[tuple[ManualEntry, dict[str, Any] | None]] = []
    rows = []
    at = datetime.now(UTC)
    for row in reader:
        if len(entries) >= 100 or None in row or any(v is None for v in row.values()):
            raise ValueError("MANUAL_CSV_ROW_OR_COLUMN_LIMIT")
        data = {k: v.strip() for k, v in row.items()}
        position = data["kind"] in {"OPENING_POSITION", "BUY", "SELL"}
        key = "NSE_EQ|" + data["isin"] if position else None
        metadata = verified(service, key) if key else None
        if position and metadata and data["symbol"] != metadata["symbol"]:
            raise ValueError("MANUAL_CSV_ISIN_SYMBOL_MISMATCH")
        if not position and (data["isin"] or data["symbol"]):
            raise ValueError("MANUAL_CSV_CASH_IDENTITY_REJECTED")
        if data["fees_known"].lower() not in {"true", "false", "1", "0"}:
            raise ValueError("MANUAL_CSV_EXPLICIT_FEE_KNOWLEDGE_REQUIRED")
        entry = ManualEntry.model_validate(
            {
                "request_id": uuid4().hex,
                "kind": data["kind"],
                "instrument_key": key,
                "session": data["session"],
                **{k: data[k] or "0" for k in ("quantity", "price", "fees", "cash_amount")},
                "fees_known": data["fees_known"].lower() in {"true", "1"},
                "notes": data["notes"],
            }
        )
        value = apply_entry(value, identity, entry, metadata, at)
        entries.append((entry, metadata))
        rows.append(
            {
                "row": len(entries),
                "symbol": metadata["symbol"] if metadata else None,
                "isin": metadata["isin"] if metadata else None,
                "entry": entry.model_dump(mode="json"),
                "identity_basis": "CURRENT_MASTER_NOT_VERIFIED_HISTORICAL_EXECUTION"
                if position
                else "OPERATOR_RECORDED_CASH_EVENT",
            }
        )
    if not entries:
        raise ValueError("MANUAL_CSV_EMPTY")
    preview_id = uuid4().hex
    with _lock:
        for key in list(_previews):
            if time.monotonic() - _previews[key].created >= 600:
                _previews.pop(key)
        if len(_previews) >= 20:
            raise ValueError("MANUAL_CSV_PREVIEW_LIMIT")
        _previews[preview_id] = Preview(owned.owner, identity, current["revision"], entries)
    return {
        "preview_id": preview_id,
        "portfolio_id": identity,
        "expected_revision": current["revision"],
        "rows": rows,
        "writes_performed": False,
        "confirmation_required": True,
        "expires_in_seconds": 600,
        "price_source": "USER_CSV_NOT_PROVIDER_OR_BROKER",
    }


def prepare(identity: str, request: Request, service: Research, text: str) -> dict[str, Any]:
    try:
        return _prepare(identity, request, service, text)
    except csv.Error as exc:
        raise ValueError("MANUAL_CSV_MALFORMED") from exc


@router.post("/{identity}/import-preview")
async def preview(identity: str, request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"csv"} or not isinstance(value["csv"], str):
        raise APIError("INVALID_REQUEST", "Provide one bounded CSV text input.", 422)
    return wrap(
        await run_in_threadpool(safe, lambda: prepare(identity, request, service, value["csv"]))
    )


@router.post("/{identity}/import-confirm")
async def confirm(identity: str, request: Request) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"preview_id"} or not isinstance(value["preview_id"], str):
        raise APIError("INVALID_REQUEST", "Confirm the owned unchanged preview identifier.", 422)

    def commit() -> dict[str, Any]:
        owned = store(request)
        with _lock:
            preview = _previews.get(value["preview_id"])
            if not preview or time.monotonic() - preview.created >= 600:
                raise ValueError("MANUAL_CSV_PREVIEW_EXPIRED")
            if preview.owner != owned.owner or preview.portfolio != identity:
                raise ValueError("PERSONAL_OWNER_MISMATCH")
            if not preview.confirmed:
                owned.record_many(identity, preview.entries, preview.revision)
                preview.confirmed = True
            return {
                "confirmed": True,
                "imported_rows": len(preview.entries),
                "idempotent": True,
                "portfolio_id": identity,
            }

    return wrap(await run_in_threadpool(safe, commit))
