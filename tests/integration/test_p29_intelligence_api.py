"""P29 authenticated TEST_ONLY persisted evidence; no model or source activation."""

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import SECURITY, build
from scripts.build_p21_test_auth import AuthenticatedTransport

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def evidence(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return build(tmp_path_factory.mktemp("TEST_ONLY_p29"))


async def test_passport_actual_observation_feature_missingness_and_gate_lineage(
    evidence: Settings,
) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get(f"/api/v1/intelligence/passport/{SECURITY}")
        assert result.status_code == 200
        body = result.json()
        assert body["classification"]["data_reality"] == "TEST_ONLY"
        data = body["data"]
        assert data["latest_observed_session"] == "2013-11-05"
        assert data["observed_identity"]["isin"] == "TESTISIN_A"
        assert data["missing_slots"] > 0 and data["evidence_confidence_percentage"] is None
        assert data["current_shortlist"] == "UNAVAILABLE"
        assert {b["layer"] for b in data["blockers"]} >= {"source", "actions", "model", "peers"}


async def test_regime_and_drift_use_actual_small_sample_unavailable_states(
    evidence: Settings,
) -> None:
    app = create_app(evidence)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/intelligence/regime?sessions=3")
        assert result.status_code == 200
        data = result.json()["data"]
        assert data["strict_pit"]["classification"] == "INSUFFICIENT_EVIDENCE"
        assert all(p["classification"] == "INSUFFICIENT_EVIDENCE" for p in data["timeline"])
        assert (await client.get("/api/v1/intelligence/drift?sessions=3")).status_code == 200
        assert len(app.state.research.intelligence_window.cache) == 1
        assert (await client.get("/api/v1/intelligence/regime?sessions=11")).status_code == 422


async def test_reliability_read_does_not_promote_or_re_evaluate(evidence: Settings) -> None:
    async with AsyncClient(
        transport=AuthenticatedTransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        data = (await client.get("/api/v1/intelligence/reliability")).json()["data"]
        assert data["matrix"][0]["current_inference"] == "NOT_ELIGIBLE"
        assert data["acceptance"] == "UNCHANGED_INSUFFICIENT_INDEPENDENT_EVIDENCE"
        assert (await client.get("/api/v1/intelligence/reliability?horizon=2")).status_code == 422


@pytest.mark.parametrize("path", ["regime", "drift", "reliability", f"passport/{SECURITY}"])
async def test_intelligence_routes_require_auth_and_reject_foreign_origins(
    evidence: Settings, path: str
) -> None:
    app = create_app(evidence)
    transport = AuthenticatedTransport(app=app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/intelligence/" + path)).status_code == 401
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (
            await client.get(
                "/api/v1/intelligence/" + path, headers={"Origin": "https://foreign.invalid"}
            )
        ).status_code == 403
