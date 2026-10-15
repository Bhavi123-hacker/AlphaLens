"""Explicit current company/action reference; never historical PIT or ledger adjustments."""

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .store import ProviderStore
from .transient import expire_after
from .upstox import Operation, UpstoxClient
from .upstox_terminal import _lock, master, selected

_guard = threading.Lock()
_memory: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def current_sector(root: Path, key: str) -> dict[str, Any] | None:
    """Use an already explicitly loaded, unexpired current reference only."""
    with _guard:
        entry = _memory.get((str(root.resolve()), key))
        if entry is None or time.monotonic() - entry[0] >= 600:
            return None
        for row in entry[1]["observations"]:
            sector = (
                row["data"].get("sector")
                if row["kind"] == "profile" and isinstance(row["data"], dict)
                else None
            )
            if isinstance(sector, str) and 0 < len(sector) <= 120:
                return {
                    "value": sector,
                    "source": "UPSTOX_CURRENT_COMPANY_PROFILE",
                    "observed_at": row["received_at"],
                    "historical_pit": False,
                    "expires_in_seconds": max(0, 600 - (time.monotonic() - entry[0])),
                }
    return None


def load(root: Path, key: str) -> dict[str, Any]:
    with _guard:
        now = time.monotonic()
        for expired_key in list(_memory):
            if now - _memory[expired_key][0] >= 600:
                _memory.pop(expired_key)
        cache_key = (str(root.resolve()), key)
        if cache_key in _memory:
            began, value = _memory[cache_key]
            return {
                **value,
                "expires_in_seconds": max(0, 600 - (now - began)),
                "api_calls_this_request": 0,
            }
        client = UpstoxClient(ProviderStore(root), budget=4)
        with _lock:
            identity = selected(master(root, client, datetime.now(UTC)), key)
        observations = []
        operations: tuple[Operation, ...] = ("profile", "ratios", "actions")
        for operation in operations:
            reply = client.get(operation, key=identity.provider_key)
            data = None
            state = reply.state
            if reply.status == 200:
                state = "MALFORMED_REFERENCE"
                try:
                    document = json.loads(reply.body)
                    if document.get("status") == "success" and isinstance(
                        document.get("data"), (dict, list)
                    ):
                        data, state = document["data"], "PROVIDER_CURRENT_REFERENCE"
                except (ValueError, AttributeError):
                    state = "MALFORMED_REFERENCE"
            observations.append(
                {
                    "kind": operation,
                    "state": state,
                    "data": data,
                    "received_at": reply.received_at.isoformat(),
                    "provider_effective_at": None,
                }
            )
        value = {
            "instrument_key": key,
            "isin": identity.isin,
            "symbol": identity.symbol,
            "source": "UPSTOX_FUNDAMENTALS_V2_CURRENT_REFERENCE",
            "observations": observations,
            "expires_in_seconds": 600,
            "api_calls_this_request": client.calls,
            "historical_pit_eligible": False,
            "action_coverage_complete": False,
            "ledger_adjustments_applied": False,
            "retained": False,
            "limitations": [
                "PROVIDER_CURRENT_CLASSIFICATION_NOT_HISTORICAL_TAXONOMY",
                "SECTOR_MARKET_CAP_IS_NOT_COMPANY_MARKET_CAP",
                "PUBLICATION_REVISION_CLOCKS_NOT_ESTABLISHED",
                "ACTION_COMPLETENESS_NOT_ESTABLISHED",
                "NO_AUTOMATIC_P15_OR_MODEL_COMPATIBILITY_UPGRADE",
            ],
        }
        if len(_memory) >= 50:
            _memory.pop(next(iter(_memory)))
        _memory[cache_key] = (time.monotonic(), value)
        expire_after(_memory, cache_key, _memory[cache_key][0], _guard, 600)
        return value
