"""TEST_ONLY genuine auth/ownership/CSRF and local writes; provider never contacted."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.personal.store import PersonalStore

from alphalens_api.auth.store import AuthStore
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_authentication_default_write_gate_and_guarded_preferences(tmp_path: Path) -> None:
    settings = build(tmp_path / "TEST_ONLY_evidence")
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/personal/workspace")).status_code == 401
    transport = AuthenticatedTransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.post("/api/v1/personal/profile", json={})).status_code == 404
        assert not any(
            "POST" in getattr(r, "methods", set())
            and getattr(r, "path", "").startswith("/api/v1/personal/")
            for r in app.routes
        )
    configured = settings.model_copy(
        update={"personal_root": tmp_path / "TEST_ONLY_owned", "personal_mutations": True}
    )
    enabled = create_app(configured)
    transport = AuthenticatedTransport(app=enabled)
    operator = AuthStore(enabled.state.settings.auth_root).session(transport._session)
    assert configured.personal_root is not None
    PersonalStore(configured.personal_root, operator["account_id"]).initialize()
    headers = {"Origin": "http://127.0.0.1:5173", "X-AlphaLens-Local": "p32"}
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        state = (await client.get("/api/v1/personal/workspace")).json()["data"]
        assert (
            state["profile"]["value"]["budget_inr"] is None
            and state["current_eligible_ml_predictions"] == 0
        )
        payload = {
            "revision": 0,
            "profile": {**state["profile"]["value"], "budget_inr": "100000", "desired_stocks": 5},
        }
        assert (await client.post("/api/v1/personal/profile", json=payload)).status_code == 403
        assert (
            await client.post(
                "/api/v1/personal/profile",
                json=payload,
                headers={**headers, "X-CSRF-Token": "invalid"},
            )
        ).status_code == 403
        assert (
            await client.post(
                "/api/v1/personal/profile",
                json=payload,
                headers={**headers, "Origin": "https://foreign.invalid"},
            )
        ).status_code == 403
        result = await client.post("/api/v1/personal/profile", json=payload, headers=headers)
        assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
        assert result.json()["classification"]["final_vintage"] is None
        assert (
            await client.post("/api/v1/personal/profile", json=payload, headers=headers)
        ).status_code == 409
        create = await client.post(
            "/api/v1/personal/portfolios", json={"name": "TEST_ONLY portfolio"}, headers=headers
        )
        assert (
            create.status_code == 200
            and not create.json()["data"]["value"]["ledger"]["transactions"]
        )
        assert (
            await client.post(
                "/api/v1/personal/records/watchlists",
                json={
                    "id": "",
                    "revision": 0,
                    "value": {"name": "TEST_ONLY watchlist", "instrument_keys": []},
                },
                headers=headers,
            )
        ).status_code == 200
        assert (
            await client.post(
                "/api/v1/personal/profile",
                json={**payload, "owner": "TEST_ONLY_attacker"},
                headers=headers,
            )
        ).status_code == 422


async def test_personal_store_rejects_authenticated_different_owner(tmp_path: Path) -> None:
    configured = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={"personal_root": tmp_path / "TEST_ONLY_other"}
    )
    assert configured.personal_root is not None
    PersonalStore(configured.personal_root, "TEST_ONLY_different_owner").initialize()
    app = create_app(configured)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/personal/workspace")
        assert response.status_code == 403
        assert response.json()["error_code"] == "PERSONAL_OWNER_MISMATCH"


async def test_owned_csv_preview_atomic_confirmation_and_query_sizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={
            "personal_root": tmp_path / "TEST_ONLY_csv",
            "personal_mutations": True,
            "upstox_private_view": True,
            "upstox_validation_root": tmp_path / "TEST_ONLY_provider",
        }
    )
    app = create_app(settings)
    transport = AuthenticatedTransport(app=app)
    assert settings.personal_root is not None
    owner = AuthStore(app.state.settings.auth_root).session(transport._session)["account_id"]
    owned = PersonalStore(settings.personal_root, owner)
    owned.initialize()
    metadata = {
        "provider_key": "NSE_EQ|INE000000001",
        "isin": "INE000000001",
        "symbol": "TEST_ONLY_ALPHA",
    }
    monkeypatch.setattr("alphalens_api.personal_import.verified", lambda service, key: metadata)
    headers = {"Origin": "http://127.0.0.1:5173", "X-AlphaLens-Local": "p32"}
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for size in (5, 10, 20):
            response = await client.get(f"/api/v1/personal/candidates?size={size}")
            assert (
                response.status_code == 200
                and response.json()["data"]["eligible_prediction_count"] == 0
            )
        assert (await client.get("/api/v1/personal/candidates?size=7")).status_code == 422
        portfolio = (
            await client.post(
                "/api/v1/personal/portfolios", json={"name": "TEST_ONLY CSV"}, headers=headers
            )
        ).json()["data"]
        identity = portfolio["id"]
        text = (
            "kind,isin,symbol,session,quantity,price,fees,fees_known,cash_amount,notes\n"
            "OPENING_POSITION,INE000000001,TEST_ONLY_ALPHA,2024-01-02,10,100,10,true,0,TEST_ONLY\n"
            "SELL,INE000000001,TEST_ONLY_ALPHA,2024-01-03,4,150,5,true,0,TEST_ONLY\n"
        )
        prefix = f"/api/v1/personal/portfolios/{identity}"
        result = await client.post(prefix + "/import-preview", json={"csv": text}, headers=headers)
        assert result.status_code == 200 and result.json()["data"]["writes_performed"] is False
        assert not owned.get("portfolios", identity)["value"]["ledger"]["transactions"]
        preview = result.json()["data"]["preview_id"]
        for _ in range(2):
            confirmed = await client.post(
                prefix + "/import-confirm", json={"preview_id": preview}, headers=headers
            )
            assert confirmed.status_code == 200 and confirmed.json()["data"]["imported_rows"] == 2
        assert len(owned.get("portfolios", identity)["value"]["ledger"]["transactions"]) == 2
        bad = await client.post(
            prefix + "/import-preview",
            json={"csv": text.replace("TEST_ONLY_ALPHA", "TEST_ONLY_WRONG")},
            headers=headers,
        )
        assert bad.status_code == 422
        assert len(owned.get("portfolios", identity)["value"]["ledger"]["transactions"]) == 2
