"""TEST_ONLY real auth/CSRF/owner and isolated transient analytics, no network."""

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.alerts.store import AlertStore
from workers.personal.store import PersonalStore

from alphalens_api import personal
from alphalens_api.auth.store import AuthStore
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio
KEY = "NSE_EQ|INE000000001"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_decision_alert_lifecycle_preview_export_and_copilot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={
            "personal_root": tmp_path / "TEST_ONLY_personal",
            "personal_mutations": True,
            "upstox_private_view": True,
            "upstox_validation_root": tmp_path / "TEST_ONLY_provider",
        }
    )
    alerts = AlertStore(tmp_path / "TEST_ONLY_alerts")
    alerts.initialize()
    settings = settings.model_copy(update={"alerts_root": alerts.root})
    app = create_app(settings)
    transport = AuthenticatedTransport(app=app)
    owner = AuthStore(app.state.settings.auth_root).session(transport._session)["account_id"]
    assert settings.personal_root is not None
    owned = PersonalStore(settings.personal_root, owner)
    owned.initialize()
    item = {
        "instrument_key": KEY,
        "symbol": "TEST_ONLY",
        "source": "TEST_ONLY",
        "rows": [
            {
                "session": str(date(2024, 1, 1) + timedelta(days=i)),
                "close": str(100 + i),
                "volume": 100,
            }
            for i in range(60)
        ],
        "quote": {
            "state": "VALIDATED_SNAPSHOT",
            "ltp": "200",
            "last_trade_at": "2024-03-01T10:00:00+05:30",
            "snapshot_at": "2024-03-01T10:01:00+05:30",
            "freshness": "OLDER_TRADE",
        },
        "indicators": {"rsi_14": {"points": [{"value": 50}]}},
    }
    monkeypatch.setattr(personal, "cached", lambda *_: {KEY: item})
    monkeypatch.setattr(
        personal,
        "verified",
        lambda *_: {"provider_key": KEY, "isin": KEY.split("|")[1], "symbol": "TEST_ONLY"},
    )
    headers = {"Origin": "http://127.0.0.1:5173", "X-AlphaLens-Local": "p32"}
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        portfolio = await client.post(
            "/api/v1/personal/portfolios", json={"name": "TEST_ONLY"}, headers=headers
        )
        id_ = portfolio.json()["data"]["id"]
        reply = await client.post(
            f"/api/v1/personal/portfolios/{id_}/entries",
            json={
                "kind": "OPENING_POSITION",
                "request_id": uuid4().hex,
                "instrument_key": KEY,
                "session": "2024-01-02",
                "quantity": "10",
                "price": "100",
                "fees_known": True,
            },
            headers=headers,
        )
        assert reply.status_code == 200
        rule = {
            "name": "TEST_ONLY target",
            "kind": "PRICE_ABOVE",
            "instrument_key": KEY,
            "portfolio_id": id_,
            "threshold": "190",
            "enabled": True,
            "evidence_source": "QUOTE_ONLY",
        }
        invalid = await client.post(
            "/api/v1/personal/records/rules",
            json={"id": "", "revision": 0, "value": {**rule, "instrument_key": None}},
            headers=headers,
        )
        assert invalid.status_code == 422 and not owned.listing("rules")
        preview = await client.post(
            "/api/v1/personal/rules/evaluate", json={"preview": True, "rule": rule}, headers=headers
        )
        assert preview.status_code == 200 and preview.json()["data"]["new_alerts"] == 0
        assert preview.json()["data"]["results"][0]["state"] == "MATCHED"
        saved = (
            await client.post(
                "/api/v1/personal/records/rules",
                json={"id": "", "revision": 0, "value": rule},
                headers=headers,
            )
        ).json()["data"]
        desk = (
            await client.get(
                "/api/v1/personal/decision-desk",
                params={"instrument_keys": KEY, "portfolio_id": id_},
            )
        ).json()["data"]
        assert len(desk["entries"]) == 1 and desk["current_ml_predictions"] == 0
        assert "PRICE_TARGET_REACHED" in desk["holding_review"]["holdings"][0]["diagnostics"]
        assert desk["provider_requests"] == 0
        export = (await client.get(f"/api/v1/personal/portfolios/{id_}/export")).json()["data"]
        assert (
            not export["provider_market_observations"]
            and len(export["record"]["ledger"]["transactions"]) == 1
        )
        assert (
            await client.get("/api/v1/personal/portfolios/" + uuid4().hex + "/export")
        ).status_code == 404
        for expected in (1, 0):
            result = await client.post("/api/v1/personal/rules/evaluate", json={}, headers=headers)
            assert result.json()["data"]["new_alerts"] == expected
        assert alerts.unread() == 1
        updated = await client.post(
            "/api/v1/personal/records/rules",
            json={"id": saved["id"], "revision": 1, "value": {**rule, "enabled": False}},
            headers=headers,
        )
        assert updated.status_code == 200
        assert not (
            await client.post("/api/v1/personal/rules/evaluate", json={}, headers=headers)
        ).json()["data"]["results"]
        assert (
            await client.post(
                f"/api/v1/personal/records/rules/{saved['id']}/remove",
                json={"revision": 2},
                headers=headers,
            )
        ).status_code == 200
        for question in (
            "stock-preferences",
            "research-exclusions",
            "historical-period",
            "portfolio-activity",
            "scenario-assumptions",
        ):
            answer = await client.get(
                "/api/v1/personal/copilot",
                params={"question": question, "instrument_key": KEY, "portfolio_id": id_},
            )
            assert answer.status_code == 200 and answer.json()["data"]["claims"]
        item["quote"] = {"state": "QUOTE_TIME_REJECTED"}
        item.update(latest_close="150", latest_session="2024-03-01")
        rejected = await client.post(
            "/api/v1/personal/rules/evaluate", json={"preview": True, "rule": rule}, headers=headers
        )
        assert rejected.json()["data"]["results"][0]["state"] == "INSUFFICIENT_EVIDENCE"
