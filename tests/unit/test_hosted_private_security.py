"""TEST_ONLY private hosting: no external requests, real accounts or market data."""

import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.hosted import serving_address, validate_state
from alphalens_api.main import LocalOnlyMiddleware, create_app

ORIGIN = "https://research.example.test"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def asgi_client(
    app: Any, *, base_url: str = "http://testserver", peer: tuple[str, int] = ("127.0.0.1", 12345)
) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app, client=peer), base_url=base_url)


@pytest.fixture
def hosted(tmp_path: Path) -> tuple[Settings, str]:
    root = tmp_path / "TEST_ONLY_persistent"
    root.mkdir()
    restrict(root)
    operations = root / "operations"
    operations.mkdir()
    restrict(operations)
    auth = AuthStore(root / "auth")
    auth.initialize()
    secret = secrets.token_urlsafe(24)
    auth.bootstrap("test_operator", secret)
    frontend = tmp_path / "TEST_ONLY_compiled"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text('<script src="/assets/test.js"></script>')
    (frontend / "assets/test.js").write_text("// TEST_ONLY compiled fixture")
    return (
        Settings(
            environment="test",
            access_mode="hosted_private",
            hosted_bind_host="0.0.0.0",
            public_origin=ORIGIN,
            allowed_hosts=("research.example.test",),
            cors_origins=(ORIGIN,),
            hosted_data_root=root,
            auth_root=auth.root,
            operations_root=operations,
            frontend_root=frontend,
        ),
        secret,
    )


def client(settings: Settings, *, base_url: str = ORIGIN) -> AsyncClient:
    return asgi_client(create_app(settings), base_url=base_url, peer=("198.51.100.25", 12345))


async def login(value: AsyncClient, secret: str, **changes: Any) -> Any:
    return await value.post(
        "/api/v1/auth/login",
        json={"username": "test_operator", "password": secret},
        headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21", **changes},
    )


@pytest.mark.parametrize(
    "change",
    [
        {"public_origin": "http://research.example.test"},
        {"public_origin": ORIGIN + "/"},
        {"public_origin": "https://research.example.test:443"},
        {"public_origin": "https://user@research.example.test"},
        {"public_origin": ORIGIN + "?token=TEST_ONLY"},
        {"allowed_hosts": ("*",)},
        {"allowed_hosts": ("*.example.test",)},
        {"allowed_hosts": ("elsewhere.example.test",)},
        {"cors_origins": (ORIGIN, "https://elsewhere.example.test")},
        {"auth_root": None},
        {"hosted_data_root": None},
        {"frontend_root": None},
        {"private_eod_config": Path("TEST_ONLY_collector.json")},
        {"hosted_bind_host": None},
        {"hosted_bind_host": "127.0.0.1"},
        {"hosted_bind_host": "not-an-address.example.test"},
    ],
)
def test_hosted_configuration_fails_closed(
    hosted: tuple[Settings, str], change: dict[str, Any]
) -> None:
    settings, _ = hosted
    with pytest.raises(ValidationError):
        Settings.model_validate({**settings.model_dump(), **change})


async def test_opt_in_does_not_relax_default_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "12345")
    local = Settings(environment="test")
    assert serving_address(local) == ("127.0.0.1", 8000)
    async with asgi_client(create_app(local), peer=("198.51.100.25", 12345)) as value:
        assert (await value.get("/api/v1/health/live")).status_code == 403
    async with asgi_client(create_app(local)) as value:
        assert (
            await value.get("/api/v1/health/live", headers={"X-Forwarded-Proto": "https"})
        ).status_code == 403
    with pytest.raises(ValidationError):
        Settings(cors_origins=(ORIGIN,))
    with pytest.raises(ValidationError):
        Settings(public_origin=ORIGIN)


async def test_hosted_login_secure_cookie_auth_csrf_and_logout(
    hosted: tuple[Settings, str],
) -> None:
    settings, secret = hosted
    async with client(settings) as value:
        assert (await value.get("/api/v1/auth/session")).status_code == 401
        response = await login(value, secret)
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and ("samesite=strict" in cookie)
        assert "domain=" not in cookie and "path=/api/v1" in cookie
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        session = await value.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.json()["transport"] == "HTTPS_EDGE_PRIVATE_HOSTING"
        assert (
            await value.post("/api/v1/auth/logout", json={}, headers={"Origin": ORIGIN})
        ).status_code == 403
        assert (
            await value.post(
                "/api/v1/auth/logout",
                json={},
                headers={"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]},
            )
        ).status_code == 200
        assert (await value.get("/api/v1/auth/session")).status_code == 401


async def test_forwarded_claims_never_authorize_or_replace_actual_host(
    hosted: tuple[Settings, str],
) -> None:
    settings, secret = hosted
    forged = {
        "X-Forwarded-Host": "research.example.test",
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Proto": "https",
    }
    async with client(settings, base_url="https://attacker.example.test") as value:
        assert (await value.get("/api/v1/health/live", headers=forged)).status_code == 400
    async with client(settings) as value:
        assert (await value.get("/api/v1/auth/session", headers=forged)).status_code == 401
        assert (
            await login(value, secret, Origin="https://attacker.example.test")
        ).status_code == 403
        assert (
            await value.post(
                "/api/v1/auth/login",
                json={"username": "test_operator", "password": secret},
                headers=[("Origin", ORIGIN), ("Origin", ORIGIN), ("X-AlphaLens-Local", "p21")],
            )
        ).status_code == 403
        assert (await login(value, secret, **forged)).status_code == 200
        assert (await value.get("/api/v1/auth/session", headers=forged)).status_code == 200
        assert (
            await value.get(
                "/api/v1/auth/session",
                headers=[("Host", "research.example.test"), ("Host", "attacker.example.test")],
            )
        ).status_code == 403


async def test_hosted_keeps_shell_public_and_financial_data_authenticated(
    hosted: tuple[Settings, str],
) -> None:
    settings, _ = hosted
    async with client(settings) as value:
        assert (await value.get("/login")).status_code == 200
        assert (await value.get("/assets/test.js")).status_code == 200
        assert (await value.get("/api/v1/health/live")).status_code == 200
        for path in (
            "/api/v1/nse-market/saved-market",
            "/api/v1/experimental-nse-v2/research",
            "/openapi.json",
        ):
            assert (await value.get(path)).status_code == 401
        assert (await value.get("/auth/auth.sqlite3")).status_code == 404
        assert (
            await value.get("/api/v1/health/live", headers={"Origin": "null"})
        ).status_code == 403


def test_hosted_requires_real_existing_private_operator_state(hosted: tuple[Settings, str]) -> None:
    settings, _ = hosted
    validate_state(settings)
    assert settings.auth_root is not None
    with AuthStore(settings.auth_root).connection(write=True) as connection:
        connection.execute("UPDATE accounts SET status='DISABLED'")
    with pytest.raises(ValueError, match="ACTIVE_OPERATOR"):
        validate_state(settings)
    assert settings.hosted_data_root is not None
    missing = settings.model_copy(
        update={"hosted_data_root": settings.hosted_data_root / "missing"}
    )
    with pytest.raises(ValueError, match="NOT_IMPORTED"):
        validate_state(missing)
    escaped = settings.model_copy(update={"operations_root": settings.hosted_data_root.parent})
    with pytest.raises(ValueError, match="OUTSIDE_PERSISTENT_ROOT"):
        validate_state(escaped)


@pytest.mark.parametrize("port", ["0", "80", "65536", "abc", "8000\n", " 8000", "８０００"])
def test_hosted_rejects_invalid_platform_port(
    hosted: tuple[Settings, str], monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    monkeypatch.setenv("PORT", port)
    with pytest.raises(ValueError, match="VALID_PORT"):
        serving_address(hosted[0])


def test_hosted_binds_platform_port_only_when_explicitly_enabled(
    hosted: tuple[Settings, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORT", "10000")
    assert serving_address(hosted[0]) == ("0.0.0.0", 10000)


async def test_hosted_forwarded_metadata_is_stripped_without_rewriting_peer(
    hosted: tuple[Settings, str],
) -> None:
    app = FastAPI()
    app.add_middleware(LocalOnlyMiddleware, settings=hosted[0])

    @app.get("/TEST_ONLY_transport")
    def inspect(request: Request) -> dict[str, Any]:
        return {
            "headers": dict(request.headers),
            "peer": request.client.host if request.client else None,
        }

    async with asgi_client(app, base_url=ORIGIN, peer=("198.51.100.25", 12345)) as value:
        result = (
            await value.get(
                "/TEST_ONLY_transport",
                headers={
                    "Forwarded": "for=127.0.0.1;proto=https;host=elsewhere.example.test",
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-Host": "elsewhere.example.test",
                    "X-Forwarded-For": "127.0.0.1",
                    "X-Forwarded-Anything": "TEST_ONLY",
                },
            )
        ).json()
    assert result["peer"] == "198.51.100.25"
    assert result["headers"]["host"] == "research.example.test"
    assert not any(
        key == "forwarded" or key.startswith("x-forwarded-") for key in result["headers"]
    )


def test_hosted_does_not_initialize_missing_account_or_data(hosted: tuple[Settings, str]) -> None:
    settings, _ = hosted
    assert settings.hosted_data_root is not None
    empty_auth = settings.hosted_data_root / "TEST_ONLY_empty_auth"
    empty_auth.mkdir()
    restrict(empty_auth)
    candidate = settings.model_copy(update={"auth_root": empty_auth})
    with pytest.raises(ValueError, match="AUTH_NOT_INITIALIZED"):
        create_app(candidate)
    assert not list(empty_auth.iterdir())
    empty_store = AuthStore(empty_auth)
    empty_store.initialize()
    with pytest.raises(ValueError, match="ACTIVE_OPERATOR"):
        create_app(candidate)


async def test_hosted_login_preserves_durable_rate_limiting(hosted: tuple[Settings, str]) -> None:
    settings, _ = hosted
    async with client(settings) as value:
        for _ in range(5):
            assert (await login(value, secrets.token_urlsafe(24))).status_code == 401
        assert (await login(value, secrets.token_urlsafe(24))).status_code == 429
    async with client(settings) as value:
        assert (await login(value, secrets.token_urlsafe(24))).status_code == 429
