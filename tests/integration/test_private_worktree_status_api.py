"""TEST_ONLY saved status and empty research desk; no provider calls or live writes."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.personal.store import PersonalStore
from workers.providers.upstox import UpstoxClient

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_read_only_private_worktree_pages_need_no_enabled_live_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = tmp_path / "TEST_ONLY_data_checkout"
    private = owner / ".local-data"
    config = private / "p34-runtime" / "daily-config.json"
    config.parent.mkdir(parents=True)
    restrict(private)
    restrict(config.parent)
    pipeline = private / "p34-private-operational-test"
    config.write_text(
        json.dumps(
            {
                "pipeline_root": str(pipeline),
                "access": {"provider": "upstox"},
                "calendar": {
                    "sessions": [
                        {
                            "session": "2025-01-03",
                            "status": "TRADING",
                            "known_at": "2025-01-02T12:00:00+00:00",
                            "evidence_reference": "TEST_ONLY",
                            "evidence_type": "TEST_ONLY",
                        }
                    ]
                },
                "instrument_keys": ["NSE_EQ|INE002A01018"],
            }
        )
    )
    restrict(config)
    original_config = config.read_bytes()
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={
            "personal_root": tmp_path / "TEST_ONLY_personal",
            "personal_mutations": False,
            "upstox_private_view": False,
            "private_eod_config": config,
        }
    )
    app = create_app(settings)
    transport = AuthenticatedTransport(app=app)
    account = AuthStore(app.state.settings.auth_root).session(transport._session)["account_id"]
    assert settings.personal_root is not None
    PersonalStore(settings.personal_root, account).initialize()

    def no_provider(*args: object, **kwargs: object) -> None:
        raise AssertionError("TEST_ONLY_PROVIDER_REQUEST_FORBIDDEN")

    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        desk = await client.get("/api/v1/personal/decision-desk")
        assert desk.status_code == 200
        data = desk.json()["data"]
        assert data["entries"] == [] and data["missing_instruments"] == []
        assert data["provider_requests"] == 0 and data["current_ml_predictions"] == 0
        selected = await client.get(
            "/api/v1/personal/decision-desk?instrument_keys=NSE_EQ%7CINE002A01018"
        )
        assert selected.status_code == 503  # The nonempty provider gate remains strict.
        assert "PRIVATE_PROVIDER_VIEW_DISABLED" in selected.text
        reply = await client.get("/api/v1/providers/private-eod-status")
        assert reply.status_code == 200
        data = reply.json()["data"]
        assert data["configured"] is True and data["selected_count"] == 1
        assert data["observations"] == 0 and data["inference"] == "UNAVAILABLE"
        assert data["readiness"]["state"] == "BLOCKED_EVIDENCE"
        assert data["readiness"]["network_calls"] == 0
        assert "SOURCE_USAGE_NOT_CLEARED" in data["readiness"]["blockers"]
        assert not data["scheduler_enabled"] and data["prices_in_status_response"] is False
        assert str(owner) not in reply.text
    assert not pipeline.exists() and config.read_bytes() == original_config
