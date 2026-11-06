"""Real authentication APIs, using only isolated TEST_ONLY local accounts."""

import secrets
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p20_test_evidence import event
from workers.alerts.store import AlertStore

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio
ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def account(tmp_path: Path) -> tuple[Settings, str, AuthStore]:
    root = tmp_path / "TEST_ONLY_auth"
    store = AuthStore(root)
    store.initialize()
    secret = secrets.token_urlsafe(24)
    store.bootstrap("test_operator", secret)
    alerts = AlertStore(tmp_path / "TEST_ONLY_alerts")
    alerts.initialize()
    alerts.publish("test_event", "test_fingerprint", [event()])
    alerts.deliver()
    return (
        Settings(
            environment="test",
            test_only_evidence=True,
            auth_root=root,
            alerts_root=alerts.root,
            alert_mutations=True,
        ),
        secret,
        store,
    )


async def login(client: AsyncClient, secret: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test_operator", "password": secret},
        headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21"},
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())  # Never log tokens.


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/stocks",
        "/api/v1/research/models",
        "/api/v1/research/predictions",
        "/api/v1/portfolios",
        "/api/v1/portfolios/other_owner/holdings",
        "/api/v1/paper/accounts",
        "/api/v1/paper/accounts/other_owner/trades",
        "/api/v1/alerts",
        "/api/v1/alerts/preferences",
        "/api/v1/daily/status",
        "/api/v1/auth/sessions",
        "/openapi.json",
    ],
)
async def test_private_routes_reject_unauthenticated(
    account: tuple[Settings, str, AuthStore], path: str
) -> None:
    settings, _, _ = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        assert (await client.get(path)).status_code == 401
        assert (await client.get("/api/v1/health/live")).status_code == 200


async def test_login_cookie_session_logout_and_unavailable_semantics(
    account: tuple[Settings, str, AuthStore],
) -> None:
    settings, secret, store = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        data = await login(client, secret)
        cookie = client.cookies.get("alphalens_session")
        assert cookie is not None
        assert (await client.get("/api/v1/auth/session")).status_code == 200
        assert (await client.get("/api/v1/signals")).status_code == 503
        assert (await client.get("/api/v1/alerts")).status_code == 200
        response = await client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Origin": ORIGIN, "X-CSRF-Token": data["csrf_token"]},
        )
        assert response.status_code == 200
        assert (await client.get("/api/v1/alerts")).status_code == 401
        with pytest.raises(ValueError):
            store.session(cookie)


@pytest.mark.parametrize(
    "kind",
    [
        "missing_origin",
        "bad_origin",
        "missing_context",
        "unknown_fields",
        "oversize",
        "invalid_credentials",
    ],
)
async def test_login_failure_and_closed_context(
    account: tuple[Settings, str, AuthStore], kind: str
) -> None:
    settings, secret, _ = account
    headers = {"Origin": ORIGIN, "X-AlphaLens-Local": "p21"}
    value = {"username": "test_operator", "password": secret}
    status = 403
    if kind == "missing_origin":
        headers.pop("Origin")
    if kind == "bad_origin":
        headers["Origin"] = "https://malicious.invalid"
    if kind == "missing_context":
        headers.pop("X-AlphaLens-Local")
    if kind == "unknown_fields":
        value["role"] = "ADMIN"
        status = 422
    if kind == "oversize":
        value["password"] = "x" * 9000
        status = 413
    if kind == "invalid_credentials":
        value["password"] = secrets.token_urlsafe(24)
        status = 401
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        assert (
            await client.post("/api/v1/auth/login", json=value, headers=headers)
        ).status_code == status
        assert (await client.get("/api/v1/alerts")).status_code == 401


@pytest.mark.parametrize("kind", ["missing_csrf", "wrong_csrf", "wrong_origin", "wrong_type"])
async def test_csrf_guards_and_authenticated_alert_mutation(
    account: tuple[Settings, str, AuthStore], kind: str
) -> None:
    settings, secret, _ = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        data = await login(client, secret)
        headers = {"Origin": ORIGIN, "X-AlphaLens-Local": "p20", "X-CSRF-Token": data["csrf_token"]}
        prefs = (await client.get("/api/v1/alerts/preferences")).json()["data"]["preferences"]
        invalid = dict(headers)
        if kind == "missing_csrf":
            invalid.pop("X-CSRF-Token")
        if kind == "wrong_csrf":
            invalid["X-CSRF-Token"] = "incorrect"
        if kind == "wrong_origin":
            invalid["Origin"] = "https://malicious.invalid"
        if kind == "wrong_type":
            invalid["Content-Type"] = "text/plain"
        assert (
            await client.post("/api/v1/alerts/preferences", json=prefs, headers=invalid)
        ).status_code == 403
        prefs["quiet_enabled"] = True
        assert (
            await client.post("/api/v1/alerts/preferences", json=prefs, headers=headers)
        ).status_code == 200
        row = (await client.get("/api/v1/alerts")).json()["data"][0]
        assert (
            await client.post(
                f"/api/v1/alerts/{row['id']}/state", json={"state": "ACKNOWLEDGED"}, headers=headers
            )
        ).status_code == 200


async def test_cookie_flags_fixation_revocation_and_password_change(
    account: tuple[Settings, str, AuthStore],
) -> None:
    settings, secret, _ = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_operator", "password": secret},
            headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21"},
        )
        flags = response.headers["set-cookie"].split(";", 1)[1].lower()
        assert "httponly" in flags and "samesite=strict" in flags and "secure" not in flags
        first = client.cookies.get("alphalens_session")
        second = await login(client, secret)
        assert first != client.cookies.get("alphalens_session")
        headers = {"Origin": ORIGIN, "X-CSRF-Token": second["csrf_token"]}
        assert (
            await client.post(
                "/api/v1/auth/sessions/revoke",
                json={"session_id": "unknown_session"},
                headers=headers,
            )
        ).status_code == 404
        assert (
            await client.post(
                "/api/v1/auth/password",
                json={"current_password": secret, "new_password": secrets.token_urlsafe(24)},
                headers=headers,
            )
        ).status_code == 200
        assert (await client.get("/api/v1/portfolios")).status_code == 401


@pytest.mark.parametrize("kind", ["remote", "forwarded", "host"])
async def test_local_network_controls_preserved(
    account: tuple[Settings, str, AuthStore], kind: str
) -> None:
    settings, _, _ = account
    peer = "192.0.2.1" if kind == "remote" else "127.0.0.1"
    headers = (
        {"X-Forwarded-For": "127.0.0.1"}
        if kind == "forwarded"
        else {"Host": "malicious.invalid"}
        if kind == "host"
        else {}
    )
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings), client=(peer, 1234)),
        base_url="http://127.0.0.1",
    ) as client:
        assert (await client.get("/api/v1/health/live", headers=headers)).status_code in {400, 403}


async def test_expired_disabled_and_rate_limited_access(
    account: tuple[Settings, str, AuthStore],
) -> None:
    settings, secret, store = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        await login(client, secret)
        with store.connection(write=True) as c:
            c.execute("UPDATE sessions SET absolute_expires=0")
        assert (await client.get("/api/v1/alerts")).status_code == 401
        await login(client, secret)
        store.status("DISABLED")
        assert (await client.get("/api/v1/portfolios")).status_code == 401
        for _ in range(5):
            denied = await client.post(
                "/api/v1/auth/login",
                json={"username": "test_operator", "password": secret},
                headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21"},
            )
            assert denied.status_code == 401
        assert (
            await client.post(
                "/api/v1/auth/login",
                json={"username": "test_operator", "password": secret},
                headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21"},
            )
        ).status_code == 429
        events = {x["event_type"] for x in store.diagnostics()["audit"]}
        assert {"UNAUTHORIZED_ACCESS", "LOGIN_FAILED", "LOGIN_RATE_LIMITED"} <= events


async def test_missing_storage_and_redacted_authentication_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "TEST_ONLY_absent_store"
    secret = secrets.token_urlsafe(24)
    app = create_app(Settings(environment="test", auth_root=root))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.post(
            "/api/v1/auth/login",
            json={"username": "test_operator", "password": secret},
            headers={"Origin": ORIGIN, "X-AlphaLens-Local": "p21"},
        )
        assert result.status_code == 503
        assert not root.exists()
        assert secret not in result.text and secret not in caplog.text
        assert "password_hash" not in result.text
        assert (
            await client.post("/api/v1/auth/password", json={}, headers={"Origin": ORIGIN})
        ).status_code == 401


async def test_every_declared_private_operation_requires_authentication(
    account: tuple[Settings, str, AuthStore],
) -> None:
    from alphalens_api.auth.routes import PUBLIC

    settings, _, _ = account
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for path, operations in app.openapi()["paths"].items():
            if path in PUBLIC:
                continue
            for method in operations:
                if method not in {"get", "post"}:
                    continue
                actual = (
                    path.replace("{security_id}", "not_owned")
                    .replace("{portfolio_id}", "not_owned")
                    .replace("{account_id}", "not_owned")
                    .replace("{alert_id}", "0" * 64)
                    .replace("{run_id}", "0" * 64)
                )
                assert (await client.request(method.upper(), actual)).status_code == 401


async def test_browser_scoped_schema_and_ambiguous_cookie_rejection(
    account: tuple[Settings, str, AuthStore],
) -> None:
    settings, secret, _ = account
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/openapi.json")).status_code == 401
        await login(client, secret)
        assert (await client.get("/api/v1/openapi.json")).status_code == 200
        raw = client.cookies.get("alphalens_session")
        assert (
            await client.get(
                "/api/v1/alerts",
                headers={"Cookie": f"alphalens_session={raw}; alphalens_session={raw}"},
            )
        ).status_code == 401


@pytest.mark.parametrize("kind", ["unicode", "duplicate"])
async def test_auth_payload_rejects_ambiguous_or_invalid_text(
    account: tuple[Settings, str, AuthStore], kind: str
) -> None:
    settings, _, _ = account
    payload = (
        b'{"username":"test_operator","password":"\\ud800"}'
        if kind == "unicode"
        else b'{"username":"test_operator","username":"other","password":"TEST_ONLY invalid value"}'
    )
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=payload,
            headers={
                "Origin": ORIGIN,
                "X-AlphaLens-Local": "p21",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 422
