"""TEST_ONLY authentication and saved-only collection health; no provider transport."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.experimental_nse.acquire import initialize
from workers.nse_market import collection_alerts, engine
from workers.providers.upstox import UpstoxClient

from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_collection_health_requires_auth_and_reads_no_raw_archive_or_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "nse-market-expansion"
    initialize(root)
    data = {
        "read_at": datetime.now(UTC).isoformat(),
        "provider_requests": 0,
        "coverage_session": "2025-01-03",
        "configured_securities": 500,
        "accepted_securities": 499,
        "missing_securities": 1,
        "missing_data_reasons": {"TEST_ONLY_PENDING": 1},
        "forecast_freshness": {"fresh_for_expected_session": False},
    }
    collection_alerts.publish(root, data, at=datetime.now(UTC), test_only=True)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("TEST_ONLY_RAW_REPLAY_OR_PROVIDER_FORBIDDEN")

    monkeypatch.setattr(engine, "snapshot", forbidden)
    monkeypatch.setattr(UpstoxClient, "get", forbidden)
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    authenticated = AuthenticatedTransport(app=app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/collection-health")).status_code == 401
    async with AsyncClient(transport=authenticated, base_url="http://testserver") as client:
        response = await client.get("/api/v1/nse-market/collection-health")
        assert response.status_code == 200
        saved = response.json()["data"]
        assert saved["accepted_securities"] == 499 and saved["missing_securities"] == 1
        assert saved["local_alerts"]["total"] == 2
        assert saved["provider_requests"] == 0 and saved["outbound_delivery"] is False
        assert (
            await client.get("/api/v1/nse-market/collection-health?limit=101")
        ).status_code == 422
        assert (await client.post("/api/v1/nse-market/collection-health")).status_code == 405
    assert collection_alerts.load(root) == data


async def test_collection_health_sqlite_failure_is_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    monkeypatch.setattr(
        collection_alerts,
        "listing",
        lambda *args, **kw: (_ for _ in ()).throw(sqlite3.DatabaseError("TEST_ONLY_PRIVATE_PATH")),
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/nse-market/collection-health")
        assert response.status_code == 503
        assert response.json()["error_code"] == "COLLECTION_HEALTH_EVIDENCE_INVALID"
        assert "TEST_ONLY_PRIVATE_PATH" not in response.text
