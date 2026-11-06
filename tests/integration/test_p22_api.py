"""Actual persisted TEST_ONLY sessions; private monitoring has no authentication bypass."""

import secrets
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.main import create_app
from alphalens_api.operations.store import OperationsStore

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize("path", ["status", "metrics", "history"])
async def test_monitoring_requires_genuine_operator(tmp_path: Path, path: str) -> None:
    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    password = secrets.token_urlsafe(24)
    auth.bootstrap("test_operator", password)
    ops = OperationsStore(tmp_path / "ops")
    ops.initialize()
    app = create_app(Settings(environment="test", auth_root=auth.root, operations_root=ops.root))
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://127.0.0.1"
    ) as client:
        assert (await client.get(f"/api/v1/operations/{path}")).status_code == 401
        raw, _ = auth.login("test_operator", password)
        client.cookies.set("alphalens_session", raw)
        response = await client.get(f"/api/v1/operations/{path}")
        assert response.status_code == 200
        assert str(tmp_path) not in response.text
        assert raw not in response.text
        assert "SECRET" not in response.text


async def test_test_only_history_not_served_as_real_operations(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    auth = AuthStore(tmp_path / "auth")
    auth.initialize()
    password = secrets.token_urlsafe(24)
    auth.bootstrap("test_operator", password)
    raw, _ = auth.login("test_operator", password)
    ops = OperationsStore(tmp_path / "ops")
    ops.initialize()
    ops.record({"observed_at": datetime.now(UTC).isoformat(), "components": {}}, test_only=True)
    app = create_app(Settings(environment="test", auth_root=auth.root, operations_root=ops.root))
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://127.0.0.1"
    ) as client:
        client.cookies.set("alphalens_session", raw)
        assert (await client.get("/api/v1/operations/history")).status_code == 503
