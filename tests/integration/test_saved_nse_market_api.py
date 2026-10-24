"""TEST_ONLY saved-market auth and bounded read tests, no provider transport."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.nse_market.saved_market import project

from alphalens_api import nse_saved
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


def saved_view() -> dict[str, object]:
    return project(
        {
            "dataset_id": "TEST_ONLY",
            "sessions": ["2026-10-19", "2026-10-21"],
            "identities": [
                {"provider_key": "NSE_EQ|INE000000000", "symbol": "TEST_ONLY", "name": None}
            ],
            "rows": [
                {
                    "key": "NSE_EQ|INE000000000",
                    "session": day,
                    "open": "100",
                    "high": "115",
                    "low": "85",
                    "close": close,
                    "volume": 123,
                    "received_at": "2026-10-22T10:00:00+00:00",
                }
                for day, close in [("2026-10-19", "100"), ("2026-10-21", "110")]
            ],
            "source_observed_at": "2026-10-22T10:00:00+00:00",
            "price_basis": "TEST_ONLY",
        },
        at=datetime(2026, 10, 24, 6, tzinfo=UTC),
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_saved_views_require_authentication_and_validate_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(build(tmp_path / "TEST_ONLY"))
    monkeypatch.setattr(nse_saved, "_view", lambda service: saved_view())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/saved-market")).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/saved-market?order=gainers")
        assert reply.status_code == 200
        assert reply.json()["data"]["provider_requests"] == 0
        assert reply.json()["data"]["rows"][0]["change"] == "10"
        assert (await client.get("/api/v1/nse-market/saved-market?limit=51")).status_code == 422
        assert (
            await client.get("/api/v1/nse-market/saved-market?order=unknown")
        ).status_code == 422
        reply = await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE000000000")
        assert reply.status_code == 200
        assert len(reply.json()["data"]["rows"]) == 2
        assert (
            await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE999999999")
        ).status_code == 404
        assert (
            await client.get("/api/v1/nse-market/saved-history?key=../secret")
        ).status_code == 422
