"""Vendor preparation reuses P19 checkpoints using isolated TEST_ONLY native bodies."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from scripts.build_p19_test_evidence import AT, DAY, calendar, request
from workers.daily.engine import Worker
from workers.daily.features import definitions

from alphalens_data.daily.contracts import Provider, Request
from alphalens_data.daily.storage import Store
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_contracts import Instrument


def bundle(path: Path, provider: str, *, close: str = "101", day: Any = DAY) -> bytes:
    row = [str(day) + "T00:00:00+05:30", "100.123456789", "102", "99", close, 1000]
    native = json.dumps(
        {"status": "success", "data": {"candles": [row]}}
        if provider == "upstox"
        else {"status": True, "data": [row]}
    ).encode()
    identity = Instrument(
        provider=provider,
        provider_key="NSE_EQ|INE000A01001" if provider == "upstox" else "123",
        exchange="NSE",
        segment="NSE_EQ" if provider == "upstox" else "NSE",
        symbol="TEST_ONLY",
        isin="INE000A01001",
        series="EQ",
        name="TEST_ONLY LIMITED",
        observed_at=AT - timedelta(days=1),
        revision_sha256="b" * 64,
        identity_evidence="TEST_ONLY_NATIVE_FIXTURE",
        canonical_security_id="TEST_ONLY:SECURITY_A",
    )
    path.write_bytes(
        json.dumps(
            {
                "version": "p28.test-provider.v1",
                "classification": "TEST_ONLY",
                "price_basis": "RAW_UNADJUSTED",
                "provider": provider,
                "native_payload_hex": native.hex(),
                "native_payload_sha256": checksum(native),
                "instruments": [identity.model_dump(mode="json")],
            }
        ).encode()
    )
    return native


def vendor_request(path: Path, provider: str) -> Request:
    req = request(path)
    return req.model_copy(
        update={
            "source_filename": "TEST_ONLY_native.json",
            "provider": Provider(
                source=provider,
                dataset="test-only-nse",
                revision="TEST_ONLY_REVISION",
                status="SOURCE_NOT_CLEARED",
                evidence_reference="TEST_ONLY_NO_REAL_PRICE",
            ),
        }
    )


@pytest.mark.parametrize("provider", ["upstox", "angel-one"])
def test_native_release_normalizes_and_checkpoints_without_live_promotion(
    tmp_path: Path, provider: str
) -> None:
    path = tmp_path / "TEST_ONLY_source.json"
    native = bundle(path, provider)
    req = vendor_request(path, provider)
    worker = Worker(tmp_path / "TEST_ONLY_worker")
    receipt = worker.run(req, path)
    assert receipt["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    stored = worker.store.read(req.run_id, "normalized.json")
    assert stored["raw_manifest"]["sha256"] == checksum(native)
    assert stored["adapter_evidence"]["bundle_sha256"] == checksum(path.read_bytes())
    assert stored["rows"][0]["source"]["open"] == "100.123456789"
    assert stored["rows"][0]["source"]["classification"] == "TEST_ONLY"
    assert worker.run(req, path) == receipt
    assert Store(worker.store.root).receipt(req.run_id) == receipt
    assert receipt["inference_status"] == "UNAVAILABLE"


def test_daily_remains_blocked_even_with_claimed_source_permissions(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_source.json"
    bundle(path, "upstox")
    req = vendor_request(path, "upstox")
    provider = req.provider.model_copy(
        update={
            "status": "SOURCE_APPROVED_FOR_RESEARCH",
            "automation_permitted": True,
            "retention_permitted": True,
            "research_permitted": True,
        }
    )
    receipt = Worker(tmp_path / "TEST_ONLY_worker").run(
        req.model_copy(update={"mode": "DAILY", "provider": provider}), path
    )
    assert receipt["state"] == "BLOCKED_SOURCE"
    assert receipt["products"] == {}
    assert "AUTOMATED_SOURCE_ADAPTER_NOT_VERIFIED" in receipt["reasons"]


def test_non_trading_calendar_never_ingests_a_weekday_price(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_source.json"
    bundle(path, "upstox")
    req = vendor_request(path, "upstox")
    sessions = (req.calendar.sessions[0].model_copy(update={"status": "NON_TRADING"}),)
    req = req.model_copy(
        update={"calendar": req.calendar.model_copy(update={"sessions": sessions})}
    )
    receipt = Worker(tmp_path / "TEST_ONLY_worker").run(req, path)
    assert receipt["state"] == "BLOCKED_EVIDENCE"
    assert receipt["products"] == {}


def test_special_saturday_uses_explicit_session_evidence(tmp_path: Path) -> None:
    special = DAY + timedelta(days=2)
    at = AT + timedelta(days=3)
    path = tmp_path / "TEST_ONLY_special.json"
    bundle(path, "upstox", day=special)
    req = vendor_request(path, "upstox").model_copy(
        update={
            "session": special,
            "source_received_at": at,
            "calendar": calendar([special]),
            "feature_registry_id": checksum(
                stable_json([d.model_dump(mode="json") for d in definitions(special, at)])
            ),
        }
    )
    assert special.weekday() == 5
    assert Worker(tmp_path / "TEST_ONLY_worker").run(req, path)["state"] in {
        "COMPLETED",
        "COMPLETED_WITH_WARNINGS",
    }


def test_correction_preserves_both_raw_versions(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_source.json"
    bundle(path, "upstox")
    worker = Worker(tmp_path / "TEST_ONLY_worker")
    before = vendor_request(path, "upstox")
    worker.run(before, path)
    old = worker.store.read(before.run_id, "normalized.json")
    bundle(path, "upstox", close="101.5")
    after = vendor_request(path, "upstox")
    worker.run(after, path)
    assert before.run_id != after.run_id
    assert worker.store.read(before.run_id, "normalized.json") == old
    new = worker.store.read(after.run_id, "normalized.json")
    assert old["raw_manifest"]["sha256"] != new["raw_manifest"]["sha256"]


def test_interrupted_publication_recovers_prior_normalization(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_source.json"
    bundle(path, "upstox")
    req = vendor_request(path, "upstox")

    def interrupt(stage: str) -> None:
        if stage == "normalized":
            raise OSError("TEST_ONLY_INTERRUPTION")

    root = tmp_path / "TEST_ONLY_worker"
    with pytest.raises(Exception, match="RETRYABLE_FAILURE"):
        Worker(root, hook=interrupt).run(req, path)
    normalized = Store(root).read(req.run_id, "normalized.json")
    receipt = Worker(root).run(req, path)
    assert receipt["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert Store(root).read(req.run_id, "normalized.json") == normalized
