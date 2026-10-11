"""Compiled deployment preserves private API boundaries and strict static allowlists."""

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from alphalens_api.core.config import Settings
from alphalens_api.local.cli import configured
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def frontend(tmp_path: Path) -> Path:
    root = tmp_path / "frontend"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text('<script type="module" src="/assets/app.js"></script>')
    (root / "assets/app.js").write_text("/* TEST_ONLY compiled shell */")
    (root / ".env").write_text("TEST_ONLY_PRIVATE_MARKER")
    (root / "assets/private.sqlite3").write_text("TEST_ONLY_PRIVATE_MARKER")
    return root


async def test_shell_csp_routes_private_api_and_static_files(frontend: Path) -> None:
    app = create_app(Settings(environment="test", frontend_root=frontend))
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("127.0.0.1", 1)), base_url="http://127.0.0.1"
    ) as client:
        for path in (
            "/",
            "/login",
            "/notifications",
            "/stocks/tejhq:isin:INE002A01018",
            "/assets/app.js",
        ):
            response = await client.get(path)
            assert response.status_code == 200
            assert "script-src 'self'" in response.headers["Content-Security-Policy"]
            assert "no-store" in response.headers["Cache-Control"]
        for path in (
            "/.env",
            "/assets/private.sqlite3",
            "/api/v1/not-a-route",
            "/unrecognized",
            "/assets/missing.js",
        ):
            response = await client.get(path)
            assert response.status_code == 404
            assert "TEST_ONLY_PRIVATE_MARKER" not in response.text
            assert "<script" not in response.text
        for path in (
            "/api/v1/alerts",
            "/api/v1/operations/status",
            "/api/v1/research/models",
            "/openapi.json",
        ):
            assert (await client.get(path)).status_code == 401
        assert (await client.post("/notifications")).status_code == 405
        assert (
            await client.get("/login", headers={"Origin": "https://evil.example"})
        ).status_code == 403
        assert (await client.get("/login", headers={"Host": "evil.example"})).status_code == 400


async def test_remote_shell_is_rejected(frontend: Path) -> None:
    app = create_app(Settings(environment="test", frontend_root=frontend))
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.1", 1)), base_url="http://127.0.0.1"
    ) as client:
        assert (await client.get("/login")).status_code == 403


def test_private_storage_cannot_be_frontend(frontend: Path) -> None:
    with pytest.raises(ValueError, match="OVERLAP"):
        create_app(
            Settings(environment="test", frontend_root=frontend, auth_root=frontend / "auth")
        )


def test_config_requires_same_origin_and_excludes_secrets(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"port": 8017}))
    with pytest.raises(ValueError, match="SAME_ORIGIN"):
        configured(path)
    path.write_text(json.dumps({"database_url": "TEST_ONLY_REDACTED"}))
    with pytest.raises(ValueError, match="SECRETS"):
        configured(path)
    path.write_text(json.dumps({"port": 8017, "cors_origins": ["http://127.0.0.1:8017"]}))
    assert configured(path).port == 8017


async def test_port_conflict_does_not_claim_or_stop_listener(tmp_path: Path) -> None:
    import socket

    from alphalens_api.local.cli import serve

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        settings = Settings(port=listener.getsockname()[1])
        with pytest.raises(OSError):
            await serve(settings, tmp_path)
        assert listener.fileno() >= 0
        assert not (tmp_path / "instance.json").exists()
