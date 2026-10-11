"""TEST_ONLY published receipts and unavailable daily outputs, never live signals."""

from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p19_test_evidence import parquet, request
from workers.daily.engine import Worker

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_unconfigured_status_is_not_live_ready() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(Settings(environment="test"))),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/daily/status")
        assert response.status_code == 200
        assert response.json()["data"]["configured"] is False
        assert response.json()["data"]["live_data_activation"] == "BLOCKED"
        assert response.json()["classification"]["production_market_data_use"] == "NOT_CLEARED"
        for endpoint in ("latest", "predictions", "rankings", "signals"):
            assert (await client.get(f"/api/v1/daily/{endpoint}")).status_code == 503


async def test_published_replay_not_current_data(tmp_path: Path) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    req = request(payload)
    root = tmp_path / "daily"
    Worker(root).run(req, payload)
    settings = Settings(environment="test", test_only_evidence=True, daily_root=root)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        runs = await client.get("/api/v1/daily/runs?limit=1")
        assert runs.json()["page"]["total"] == 1
        row = (await client.get(f"/api/v1/daily/runs/{req.run_id}")).json()
        assert row["classification"]["usage_classification"] == "TEST_ONLY"
        assert "identity" not in row["data"] and "products" not in row["data"]
        assert (await client.get("/api/v1/daily/latest")).status_code == 503
        assert (
            await client.get(f"/api/v1/daily/data-quality?run_id={req.run_id}")
        ).status_code == 200
        prices = await client.get(f"/api/v1/daily/runs/{req.run_id}/prices?limit=1")
        assert prices.json()["classification"]["usage_classification"] == "TEST_ONLY"
        assert Decimal(prices.json()["data"][0]["close"]) == Decimal("101")
        features = await client.get(f"/api/v1/daily/runs/{req.run_id}/features?limit=1")
        assert features.json()["data"][0]["values"]["sma_200"]["value"] is None
        assert (await client.post("/api/v1/daily/runs")).status_code == 405
        assert (await client.get("/api/v1/daily/runs?limit=101")).status_code == 422
        assert (await client.get("/api/v1/daily/runs/invalid")).status_code == 422
        assert (await client.get(f"/api/v1/daily/runs/{'b' * 64}")).status_code == 404


async def test_test_only_cannot_be_served_as_real(tmp_path: Path) -> None:
    payload = parquet(tmp_path / "TEST_ONLY.parquet")
    Worker(tmp_path / "daily").run(request(payload), payload)
    app = create_app(Settings(environment="test", daily_root=tmp_path / "daily"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/daily/status")).status_code == 503


async def test_partial_run_not_published(tmp_path: Path) -> None:
    req = request()
    Worker(tmp_path / "daily").store.write(req.run_id, "request.json", req.model_dump(mode="json"))
    app = create_app(Settings(environment="test", daily_root=tmp_path / "daily"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/daily/runs")).json()["data"] == []


async def test_openapi_additive_get_only() -> None:
    app = create_app(Settings(environment="test"))
    paths = app.openapi()["paths"]
    assert "/api/v1/research/predictions" in paths
    for route, methods in paths.items():
        if route.startswith("/api/v1/daily/"):
            assert set(methods) == {"get"}
