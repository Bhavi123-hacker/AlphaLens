"""TEST_ONLY authenticated provider boundaries; no live network in these cases."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def evidence(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return build(tmp_path_factory.mktemp("TEST_ONLY_p30"))


async def test_validation_and_private_prices_require_existing_authentication(
    evidence: Settings,
) -> None:
    app = create_app(evidence)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for path in ("upstox-validation", "upstox-private/reliance"):
            assert (await client.get("/api/v1/providers/" + path)).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/providers/upstox-validation")
        assert (
            result.status_code == 200 and result.json()["data"]["authentication"] == "NOT_VERIFIED"
        )
        assert result.headers["cache-control"] == "no-store"
        assert (await client.get("/api/v1/providers/upstox-private/reliance")).status_code == 503
        assert (await client.post("/api/v1/providers/upstox-private/reliance")).status_code == 405
        assert (
            await client.get(
                "/api/v1/providers/upstox-validation", headers={"Origin": "https://foreign.invalid"}
            )
        ).status_code == 403


async def test_missing_master_never_falls_back_to_an_archive_or_synthetic_price(
    evidence: Settings, tmp_path: Path
) -> None:
    settings = evidence.model_copy(
        update={"upstox_private_view": True, "upstox_validation_root": tmp_path}
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/providers/upstox-private/reliance")
        assert result.status_code == 503
        assert (
            "PRIVATE_PROVIDER_VIEW_UNAVAILABLE" in result.text and "last_price" not in result.text
        )
