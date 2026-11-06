"""Authenticated provider comparisons use TEST_ONLY stores, never external requests."""

import json
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.providers.store import ProviderStore

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def evidence(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return build(tmp_path_factory.mktemp("TEST_ONLY_p28"))


async def test_six_sources_dates_quota_and_permission_are_separate(evidence: Settings) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/providers/comparison")
        assert result.status_code == 200
        data = result.json()["data"]
        assert len(data["providers"]) == 6 and data["collection_enabled"] is False
        assert data["scheduler_enabled"] is False
        providers = {p["provider"]: p for p in data["providers"]}
        assert providers["tejhq"]["last_verified_session"] == "2013-11-05"
        assert providers["alpha-vantage"]["last_verified_session"] is None
        assert providers["alpha-vantage"]["credential_configured"] is False
        assert providers["upstox"]["account_status"] == "UNDER_REVIEW"
        assert all(p["provider_remaining_daily_allowance"] is None for p in data["providers"])
        assert data["ml_readiness"]["shortlists"]["top5"] == "UNAVAILABLE"
        assert "apikey=" not in json.dumps(data).lower()


async def test_private_comparison_rejects_unauthenticated_and_remote_origin(
    evidence: Settings,
) -> None:
    app = create_app(evidence)
    transport = AuthenticatedTransport(app=app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/providers/comparison")).status_code == 401
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (
            await client.get(
                "/api/v1/providers/comparison", headers={"Origin": "https://foreign.invalid"}
            )
        ).status_code == 403
        assert (
            await client.get(
                "/api/v1/providers/comparison", headers={"X-Forwarded-For": "127.0.0.1"}
            )
        ).status_code == 403
        assert (
            await client.post("/api/v1/providers/comparison", json={"enabled": True})
        ).status_code == 405


async def test_provider_selection_is_readonly_and_disabled(
    evidence: Settings, tmp_path: Path
) -> None:
    store = ProviderStore(tmp_path / "TEST_ONLY_provider")
    store.initialize()
    store.select("indstocks", time.time())
    settings = evidence.model_copy(update={"providers_root": store.root})
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        data = (await client.get("/api/v1/providers/comparison")).json()["data"]
        assert data["operational_store"] == "AVAILABLE_ACQUISITION_DISABLED"
        assert next(p for p in data["providers"] if p["selected"])["provider"] == "indstocks"
        assert data["collection_enabled"] is False


async def test_missing_catalog_does_not_hide_source_decision(evidence: Settings) -> None:
    settings = evidence.model_copy(update={"research_data_root": None})
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/providers/comparison")
        assert result.status_code == 200
        assert all(p["last_verified_session"] is None for p in result.json()["data"]["providers"])
