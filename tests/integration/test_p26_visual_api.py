"""Isolated TEST_ONLY visual contracts; never a live-market success fixture."""

from datetime import date
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import SECURITY, build
from scripts.build_p21_test_auth import AuthenticatedTransport

from alphalens_api.core.config import Settings
from alphalens_api.core.domain_errors import APIError
from alphalens_api.main import create_app
from alphalens_api.provider_capabilities import DisabledProvider, ProviderGate
from alphalens_api.services import ResearchService
from alphalens_api.visual import build_market, describe

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def evidence(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return build(tmp_path_factory.mktemp("TEST_ONLY_p26"))


async def test_market_real_persisted_fixture_pagination_and_cache(evidence: Settings) -> None:
    app = create_app(evidence)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/visual/market?limit=1")
        assert result.status_code == 200
        body = result.json()
        assert body["classification"]["data_reality"] == "TEST_ONLY"
        assert body["data"]["session"] == "2013-11-05"
        assert body["data"]["coverage"] == 2
        assert len(body["data"]["rows"]) == 1
        assert body["page"]["has_more"] is True
        following = (await client.get("/api/v1/visual/market?limit=1&offset=1")).json()
        assert following["data"]["rows"][0]["security_id"] != body["data"]["rows"][0]["security_id"]
        assert len(app.state.research.visual_market.cache) == 1


@pytest.mark.parametrize("path", ["market", "providers", f"stocks/{SECURITY}/statistics"])
async def test_private_visual_routes_require_auth(evidence: Settings, path: str) -> None:
    app = create_app(evidence)
    AuthenticatedTransport(app=app)  # Bootstrap an isolated store, but supply no session.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/visual/" + path)).status_code == 401


async def test_origin_and_forwarded_header_rejected(evidence: Settings) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        for headers in ({"Origin": "https://foreign.invalid"}, {"X-Forwarded-For": "127.0.0.1"}):
            assert (
                await client.get("/api/v1/visual/providers", headers=headers)
            ).status_code == 403


async def test_missing_calendar_not_weekday_assumption(
    evidence: Settings,
) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/visual/market?session=2013-11-03")).status_code == 422
        body = (await client.get("/api/v1/visual/market?session=2013-11-04")).json()["data"]
        assert body["comparable"] == 0
        assert all(r["return_1"] is None for r in body["rows"])
        assert any(p["close"] is None for p in body["rows"][0]["sparkline"])


async def test_statistics_latest_range_and_missing_slots(
    evidence: Settings,
) -> None:
    service = ResearchService(evidence)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/v1/visual/stocks/{SECURITY}/statistics")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["latest"]["session"] == service.catalog.security(SECURITY)["last_observed"]
        assert data["missing_slots"] == 1
        assert data["curve"][1]["return_1"] is None
        assert data["curve"][-1]["cumulative_return"] is None
        assert (
            await client.get(
                f"/api/v1/visual/stocks/{SECURITY}/statistics?start=2025-01-01&end=2024-01-01"
            )
        ).status_code == 422


async def test_disabled_provider_has_no_quote_or_credentials(
    evidence: Settings,
) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/visual/providers")
        data = response.json()["data"]
        assert data["acquisition_enabled"] is False
        assert all(v["state"] == "UNAVAILABLE" for v in data["capabilities"].values())
        assert all(p["configured"] is False for p in data["providers"])
        assert "access_token" not in response.text


@pytest.mark.parametrize("status", ["UNDER_REVIEW", "INACTIVE", "NOT_CONFIGURED"])
def test_inactive_provider_explanations(status: Any) -> None:
    provider = DisabledProvider(ProviderGate(configured=True, account_status=status))
    assert provider.quote("TEST_ONLY").reason == "ACCOUNT_" + status
    assert provider.option_chain("TEST_ONLY").publication_time is None


def test_missing_price_is_not_zero_return_or_cumulative_fill() -> None:
    result = describe(
        [
            {"session": "TEST_ONLY_1", "close": "100.123456789", "high": "101", "low": "99"},
            {"session": "TEST_ONLY_2", "close": None, "high": None, "low": None},
            {"session": "TEST_ONLY_3", "close": "102", "high": "103", "low": "101"},
        ]
    )
    assert result["latest"]["close"] == "102"
    assert result["curve"][-1]["return_1"] is None
    assert result["curve"][-1]["cumulative_return"] is None
    assert sum(b["count"] for b in result["distribution"]) == 0


def test_duplicate_identity_rejected_in_descriptive_cohort() -> None:
    row = {"session_date": date(2026, 1, 1)}
    with pytest.raises(APIError, match="Duplicate"):
        build_market({"TEST_ONLY": [row, row]}, {}, "2026-01-01", None, [])


def test_market_cache_invalidates_changed_artifact(evidence: Settings) -> None:
    service = ResearchService(evidence)
    service.visual_market.snapshot(None)
    entry = service.reader.manifest("canonical-manifest.json")["identity"]["files"][0]
    assert evidence.research_data_root is not None
    path = evidence.research_data_root / entry["path"]
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"TEST_ONLY_TAMPER")
        with pytest.raises(APIError, match="checksum"):
            service.visual_market.snapshot(None)
    finally:
        path.write_bytes(original)


def test_search_exact_symbol_prefers_newer_canonical_evidence(evidence: Settings) -> None:
    service = ResearchService(evidence)
    rows, _ = service.catalog.search("TESTNEW", 10, 0)
    assert len(rows) == 2
    assert all(r["latest_observed_symbol"] == "TESTNEW" for r in rows)
    assert service.catalog.search("%", 10, 0)[0] == []
