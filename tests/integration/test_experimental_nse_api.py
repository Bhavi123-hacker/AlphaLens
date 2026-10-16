"""TEST_ONLY private experiment routing; no provider requests or genuine prediction claims."""

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


async def test_experimental_reads_are_authenticated_and_never_expose_write_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.experimental_nse import workspace

    calls: list[Path | None] = []

    def read(root: Path | None) -> dict[str, Any]:
        calls.append(root)
        return {
            "schema": "alphalens.experimental_nse.workspace.v1",
            "family": "ALPHALENS_EXPERIMENTAL_NSE_V1",
            "available": False,
            "candidates": [],
            "accepted_current_rankings": 0,
        }

    monkeypatch.setattr(workspace, "read_workspace", read)
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={"experimental_nse_root": tmp_path / "TEST_ONLY_experiment"}
    )
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/experimental-nse/research")).status_code == 401
        assert calls == []
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/experimental-nse/research")
        assert result.status_code == 200
        assert result.headers["cache-control"] == "no-store"
        assert result.json()["data"]["accepted_current_rankings"] == 0
        assert result.json()["classification"]["research_profile"] == (
            "ALPHALENS_EXPERIMENTAL_NSE_V1"
        )
        assert (await client.post("/api/v1/experimental-nse/research", json={})).status_code in {
            403,
            405,
        }
    assert calls == [settings.experimental_nse_root]
    assert not any(
        "POST" in getattr(route, "methods", set())
        and getattr(route, "path", "").startswith("/api/v1/experimental-nse/")
        for route in app.routes
    )


async def test_invalid_experiment_does_not_fall_back_to_archive_or_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.experimental_nse import workspace

    def invalid(root: Path | None) -> dict[str, Any]:
        raise ValueError("TEST_ONLY_corrupt_hash")

    monkeypatch.setattr(workspace, "read_workspace", invalid)
    app = create_app(build(tmp_path / "TEST_ONLY_evidence"))
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/experimental-nse/research")
        assert result.status_code == 503
        assert "TEST_ONLY_corrupt_hash" not in result.text
        assert "score" not in result.json()
