"""TEST_ONLY routing: genuine source acquisition and scores are never mocked as market evidence."""

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport

from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_v2_reads_require_authentication_and_do_not_publish_accepted_rankings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.experimental_nse_v2 import workspace

    calls: list[Path | None] = []

    def read(root: Path | None) -> dict[str, Any]:
        calls.append(root)
        return {"available": False, "candidates": [], "accepted_current_rankings": 0}

    monkeypatch.setattr(workspace, "read_workspace", read)
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
    )
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/experimental-nse-v2/research")).status_code == 401
        assert calls == []
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/experimental-nse-v2/research")
        assert result.status_code == 200
        assert result.headers["cache-control"] == "no-store"
        assert result.json()["data"]["accepted_current_rankings"] == 0
        assert result.json()["classification"]["research_profile"] == (
            "ALPHALENS_EXPERIMENTAL_NSE_V2"
        )
        assert (await client.post("/api/v1/experimental-nse-v2/research", json={})).status_code in {
            403,
            405,
        }
    assert calls == [settings.experimental_nse_v2_root]


@pytest.mark.parametrize("reason", ["invalid_evidence", "attempted_promotion"])
async def test_v2_invalid_evidence_cannot_substitute_or_promote_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    from workers.experimental_nse_v2 import workspace

    def invalid(root: Path | None) -> dict[str, Any]:
        if reason == "invalid_evidence":
            raise ValueError("TEST_ONLY_PRIVATE_HASH")
        return {"accepted_current_rankings": 1}

    monkeypatch.setattr(workspace, "read_workspace", invalid)
    app = create_app(build(tmp_path / "TEST_ONLY_evidence"))
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/experimental-nse-v2/research")
        assert result.status_code == 503
        assert "TEST_ONLY_PRIVATE_HASH" not in result.text
