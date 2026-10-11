"""Local-only alert controls; isolated TEST_ONLY notifications."""

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p20_test_evidence import AT, event
from workers.alerts.contracts import Preferences
from workers.alerts.store import AlertStore

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio
HEADERS = {"Origin": "http://127.0.0.1:5173", "X-AlphaLens-Local": "p20"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def store(tmp_path: Path) -> AlertStore:
    value = AlertStore(tmp_path / "alerts")
    value.initialize()
    value.publish("TEST_ONLY", "one", [event()], now=AT)
    value.deliver(now=AT)
    return value


def client(
    store: AlertStore, *, enabled: bool = False, test_only: bool = True, peer: str = "127.0.0.1"
) -> AsyncClient:
    settings = Settings(
        environment="test",
        test_only_evidence=test_only,
        alerts_root=store.root,
        alert_mutations=enabled,
    )
    return AsyncClient(
        transport=ASGITransport(app=create_app(settings), client=(peer, 4321)),
        base_url="http://testserver",
    )


async def test_counts_filters_detail_and_projection_actions(store: AlertStore) -> None:
    async with client(store, enabled=True) as api:
        result = (await api.get("/api/v1/alerts?severity=WARNING&limit=1")).json()
        assert result["page"]["total"] == 1
        row = result["data"][0]
        assert row["evidence"]["classification"] == "TEST_ONLY"
        assert "root" not in str(row) and "password" not in str(row)
        assert (await api.get("/api/v1/alerts/unread-count")).json()["data"]["count"] == 1
        url = f"/api/v1/alerts/{row['id']}/state"
        assert (await api.post(url, json={"state": "READ"}, headers=HEADERS)).status_code == 200
        assert (await api.get("/api/v1/alerts/unread-count")).json()["data"]["count"] == 0
        assert (
            await api.post(url, json={"state": "ACKNOWLEDGED"}, headers=HEADERS)
        ).status_code == 200
        assert (await api.post(url, json={"state": "RESOLVED"}, headers=HEADERS)).status_code == 200
        assert (await api.post(url, json={"state": "READ"}, headers=HEADERS)).status_code == 409
        assert (await api.get(f"/api/v1/alerts/{row['id']}")).json()["data"][
            "delivery"
        ] == "DELIVERED"


async def test_default_server_cannot_mutate(store: AlertStore) -> None:
    async with client(store) as api:
        assert (await api.get("/api/v1/alerts/preferences")).json()["data"][
            "mutations_enabled"
        ] is False
        assert (
            await api.post(
                f"/api/v1/alerts/{event().alert_id}/state", json={"state": "READ"}, headers=HEADERS
            )
        ).status_code == 404
        assert (
            await api.post("/api/v1/alerts/preferences", json={}, headers=HEADERS)
        ).status_code == 405
        assert store.get(event().alert_id, test_only=True)["lifecycle"] == "NEW"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "null", "X-AlphaLens-Local": "p20"},
        {"Origin": "https://outside.invalid", "X-AlphaLens-Local": "p20"},
        {"Origin": "http://127.0.0.1:5173"},
    ],
)
async def test_write_context_rejected(store: AlertStore, headers: dict[str, str]) -> None:
    async with client(store, enabled=True) as api:
        assert (
            await api.post(
                "/api/v1/alerts/preferences",
                json=Preferences().model_dump(mode="json"),
                headers=headers,
            )
        ).status_code == 403


async def test_remote_peer_cannot_read_or_mutate(store: AlertStore) -> None:
    async with client(store, enabled=True, peer="192.0.2.1") as api:
        assert (await api.get("/api/v1/alerts")).status_code == 403
        assert (
            await api.post("/api/v1/alerts/preferences", json={}, headers=HEADERS)
        ).status_code == 403


async def test_preferences_work_and_disabled_channels_cannot_enable(store: AlertStore) -> None:
    async with client(store, enabled=True) as api:
        body = Preferences(include_info=True, quiet_enabled=True).model_dump(mode="json")
        assert (
            await api.post("/api/v1/alerts/preferences", json=body, headers=HEADERS)
        ).status_code == 200
        assert store.preferences().include_info
        assert (
            await api.post(
                "/api/v1/alerts/preferences", json=body | {"email": True}, headers=HEADERS
            )
        ).status_code == 422
        channels = (await api.get("/api/v1/alerts/preferences")).json()["data"]["channels"]
        assert channels["EMAIL"].startswith("UNAVAILABLE")


@pytest.mark.parametrize(
    "body",
    [
        {"state": "BUY"},
        {"state": ["READ"]},
        {"state": "READ", "message": "TEST_ONLY_INJECTION"},
        {},
    ],
)
async def test_state_validation(store: AlertStore, body: dict[str, Any]) -> None:
    async with client(store, enabled=True) as api:
        assert (
            await api.post(f"/api/v1/alerts/{event().alert_id}/state", json=body, headers=HEADERS)
        ).status_code == 422


async def test_large_body_unknown_alert_and_no_ingestion_endpoint(store: AlertStore) -> None:
    async with client(store, enabled=True) as api:
        assert (
            await api.post(
                "/api/v1/alerts/preferences", json={"message": "x" * 9000}, headers=HEADERS
            )
        ).status_code == 413
        assert (await api.get(f"/api/v1/alerts/{'b' * 64}")).status_code == 404
        assert (await api.get("/api/v1/alerts?limit=101")).status_code == 422
        assert (await api.post("/api/v1/alerts", json={})).status_code == 405
        preflight = await api.options(
            "/api/v1/alerts/preferences",
            headers={
                "Origin": HEADERS["Origin"],
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-AlphaLens-Local,Content-Type",
            },
        )
        assert preflight.status_code == 400


async def test_application_refuses_test_evidence(store: AlertStore) -> None:
    async with client(store, test_only=False, enabled=True) as api:
        assert (await api.get("/api/v1/alerts")).status_code == 503
        assert (await api.get("/api/v1/alerts/unread-count")).status_code == 503
        assert (await api.get(f"/api/v1/alerts/{event().alert_id}")).status_code == 503
        assert (
            await api.post(
                f"/api/v1/alerts/{event().alert_id}/state", json={"state": "READ"}, headers=HEADERS
            )
        ).status_code == 503
