"""TEST_ONLY pending publication can resume; no fabricated live EOD claim."""

import json
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from scripts.build_p19_test_evidence import AT, DAY
from test_p30_daily_readiness import fixture_release
from workers.providers import daily
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply, UpstoxClient

from alphalens_data.providers.multi_contracts import Access, Instrument


@pytest.mark.parametrize("production_clock", [False, True])
def test_empty_eod_response_is_pending_and_can_be_fetched_later_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_clock: bool
) -> None:
    payload = tmp_path / "TEST_ONLY.json"
    request = fixture_release(payload)
    envelope = json.loads(payload.read_bytes())
    instrument = Instrument.model_validate(envelope["instrument"]).model_copy(
        update={"instrument_type": "EQ"}
    )
    if production_clock:
        instrument = instrument.model_copy(update={"observed_at": AT - timedelta(days=2)})
        monkeypatch.setattr(
            daily,
            "guard",
            lambda: {
                "lower_at": AT.isoformat(),
                "upper_at": (AT + timedelta(milliseconds=20)).isoformat(),
                "session_date": str(AT.date()),
                "state": "TEST_ONLY_INDEPENDENT_DATE",
            },
        )

        def master(root: Path, client: UpstoxClient, at: Any) -> tuple[Instrument, ...]:
            client.calls += 1
            return (instrument.model_copy(update={"observed_at": AT}),)

        monkeypatch.setattr("workers.providers.upstox_terminal.master", master)
    root = tmp_path / "provider"
    ProviderStore(root).initialize()
    (root / "master-identity-test.json").write_text(instrument.model_dump_json(), encoding="utf-8")
    pipeline = tmp_path / "pipeline"
    access = Access(
        provider="upstox",
        account_status="ACTIVE",
        credential_configured=True,
        permission_reference="TEST_ONLY_SCOPED_RIGHTS",
        automation_permitted=True,
        retention_permitted=True,
        research_permitted=True,
        display_permitted=True,
        nse_verified=True,
        token_kind="READ_ONLY_ANALYTICS",
        operator_activation=True,
    )
    responses = [
        json.dumps({"status": "success", "data": {"candles": []}}).encode(),
        envelope["response"].encode(),
    ]
    calls = []

    def get(self: UpstoxClient, operation: str, **kwargs: Any) -> Reply:
        assert operation == "candles"
        self.calls += 1
        calls.append(operation)
        return Reply(200, responses.pop(0), AT, "ACCEPTED")

    monkeypatch.setattr(UpstoxClient, "get", get)

    def run() -> dict[str, Any]:
        return daily.run(
            access,
            request.calendar,
            root,
            pipeline,
            at=None if production_clock else AT,
            instrument_key=instrument.provider_key,
        )

    pending = run()
    assert pending["api_calls"] == (2 if production_clock else 1)
    assert pending["sessions"][0]["state"] == "EOD_CANDLE_PENDING"
    capture = (
        pipeline
        / ("instrument-" + sha256(instrument.provider_key.encode()).hexdigest()[:16])
        / "captures"
        / f"{DAY}.json"
    )
    assert not capture.exists()
    accepted = run()
    assert accepted["sessions"][0]["counts"]["observations"] == 1
    assert accepted["sessions"][0]["counts"]["predictions"] == 0
    assert run()["api_calls"] == 0 and calls == ["candles", "candles"]

    original = capture.read_bytes()
    responses.append(envelope["response"].encode())
    unchanged = daily.run(
        access,
        request.calendar,
        root,
        pipeline,
        at=AT,
        instrument_key=instrument.provider_key,
        correction_session=DAY,
        budget=1,
    )
    assert unchanged["api_calls"] == 1
    assert unchanged["sessions"][0]["state"] == "CORRECTION_CHECK_UNCHANGED_NO_NEW_REVISION"
    assert capture.read_bytes() == original
    changed = json.loads(envelope["response"])
    changed["data"]["candles"][0][4] = 102
    responses.append(json.dumps(changed).encode())
    correction = daily.run(
        access,
        request.calendar,
        root,
        pipeline,
        at=AT,
        instrument_key=instrument.provider_key,
        correction_session=DAY,
        budget=1,
    )
    assert correction["api_calls"] == 1 and correction["sessions"][0]["counts"]["observations"] == 1
    assert list((capture.parent / "revisions").glob("*.json"))
    assert capture.read_bytes() == original
    assert run()["sessions"] == accepted["sessions"] and run()["api_calls"] == 0
    responses.append(json.dumps(changed).encode())
    repeated_correction = daily.run(
        access,
        request.calendar,
        root,
        pipeline,
        at=AT,
        instrument_key=instrument.provider_key,
        correction_session=DAY,
        budget=1,
    )
    assert (
        repeated_correction["sessions"][0]["state"] == "CORRECTION_CHECK_UNCHANGED_NO_NEW_REVISION"
    )
    assert len(list((capture.parent / "revisions").glob("*.json"))) == 1
