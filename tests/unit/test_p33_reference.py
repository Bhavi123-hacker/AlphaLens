"""TEST_ONLY current-reference cache bounds; no actual provider access or PIT upgrade."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from workers.personal.model_readiness import inspect
from workers.providers import reference
from workers.providers.upstox import Reply

from alphalens_data.providers.multi_contracts import Instrument


def test_current_reference_memory_and_error_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    at = datetime.now(UTC)
    instrument = Instrument(
        provider="upstox",
        provider_key="NSE_EQ|INE000000001",
        exchange="NSE",
        segment="NSE_EQ",
        instrument_type="EQ",
        symbol="TEST_ONLY",
        isin="INE000000001",
        observed_at=at,
        revision_sha256="a" * 64,
        identity_evidence="TEST_ONLY",
    )

    class Client:
        def __init__(self, *_: object, **__: object) -> None:
            self.calls = 0

        def get(self, operation: str, **kwargs: object) -> Reply:
            self.calls += 1
            assert kwargs["key"] == instrument.provider_key
            if operation == "actions":
                return Reply(403, b"{}", at, "PERMISSION_OR_SEGMENT_REJECTED")
            return Reply(
                200,
                json.dumps({"status": "success", "data": {"TEST_ONLY": True}}).encode(),
                at,
                "ACCEPTED",
            )

    monkeypatch.setattr(reference, "UpstoxClient", Client)
    monkeypatch.setattr(reference, "master", lambda *_: (instrument,))
    monkeypatch.setattr(reference, "selected", lambda *_: instrument)
    first = reference.load(tmp_path, instrument.provider_key)
    second = reference.load(tmp_path, instrument.provider_key)
    assert first["api_calls_this_request"] == 3 and second["api_calls_this_request"] == 0
    assert not first["historical_pit_eligible"] and not first["ledger_adjustments_applied"]
    assert first["observations"][-1]["data"] is None
    assert first["observations"][-1]["state"] == "PERMISSION_OR_SEGMENT_REJECTED"
    assert not list(tmp_path.glob("*.json"))


def test_frozen_38_feature_order_and_model_acceptance_remain_separate() -> None:
    value = inspect(Path("docs/development/p30-model-compatibility.json"))
    assert value["feature_count"] == 38
    assert len(value["candidates"]) == 4
    assert all(c["feature_order_matches_registry"] for c in value["candidates"])
    assert value["predictions_generated"] == 0 and value["models_loaded"] is False
    assert value["current_eligible_feature_count"] == 0
