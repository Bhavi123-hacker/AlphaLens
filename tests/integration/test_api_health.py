"""TEST-ONLY local API assertions; no populated market/portfolio endpoints."""

from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_liveness_and_absence_of_product_endpoints() -> None:
    app = create_app(Settings(environment="test", database_url=None))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/health/live", headers={"X-Request-ID": "TEST_ONLY_INJECTION"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "alive", "scope": "foundation_only"}
        UUID(response.headers["X-Request-ID"])
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert (await client.get("/api/v1/stocks")).status_code == 404
        assert (await client.get("/docs")).status_code == 404


async def test_readiness_without_database_is_not_ready() -> None:
    app = create_app(Settings(environment="test", database_url=None))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json()["error_code"] == "DATABASE_NOT_CONFIGURED"
        assert response.json()["request_id"] == response.headers["X-Request-ID"]


async def test_database_failure_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(url: str) -> bool:
        return False

    monkeypatch.setattr("alphalens_api.health.check_database", unavailable)
    settings = Settings(
        environment="test",
        database_url="postgresql://test_only:TEST_ONLY_SECRET@localhost/test_only",
    )
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json()["error_code"] == "DATABASE_UNAVAILABLE"
        assert "TEST_ONLY_SECRET" not in response.text


async def test_unexpected_exception_does_not_expose_internal_details() -> None:
    app = create_app(Settings(environment="test", database_url=None))

    @app.get("/TEST_ONLY_failure")
    def failure() -> None:
        raise RuntimeError("TEST_ONLY_SECRET_AND_INTERNAL_PATH")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/TEST_ONLY_failure")
        assert response.status_code == 500
        assert response.json()["error_code"] == "INTERNAL_ERROR"
        assert "TEST_ONLY_SECRET" not in response.text
        UUID(response.headers["X-Request-ID"])
