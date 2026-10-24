"""TEST_ONLY routing fixtures; no source acquisition or genuine prediction claims."""

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES
from workers.nse_market import engine
from workers.personal.contracts import Profile
from workers.personal.store import PersonalStore
from workers.providers import universe
from workers.providers.upstox import UpstoxClient

from alphalens_api import nse_market
from alphalens_api.auth.store import AuthStore
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


async def test_explicit_risk_budget_scenario_has_no_model_score_or_ledger_side_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = saved_reads(monkeypatch)
    root = tmp_path / "TEST_ONLY_v2"
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(update={"experimental_nse_v2_root": root})
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get(
            "/api/v1/nse-market/position-scenario",
            params={
                "key": data_fixture()["candidates"][0]["key"],
                "budget": "10000",
                "loss_budget": "500",
                "assumed_stop_percent": "5",
                "round_trip_cost_bps": "50",
            },
        )
        assert reply.status_code == 200
        result = reply.json()["data"]
        assert result["model_score_used_for_sizing"] is False
        assert result["provider_requests"] == 0
        assert result["stop_is_guaranteed"] is False
        assert result["verified_cash_balance"] is None
        assert result["quantity_whole_units"] > 0
        assert len(calls) == 1
        invalid = await client.get(
            "/api/v1/nse-market/position-scenario",
            params={
                "key": data_fixture()["candidates"][0]["key"],
                "budget": "10000",
                "loss_budget": "0",
                "assumed_stop_percent": "5",
                "round_trip_cost_bps": "50",
            },
        )
        assert invalid.status_code == 422


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_horizon_views_keep_five_session_model_separate_from_descriptive_ordering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_reads(monkeypatch)
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        for horizon in (5, 10, 20):
            reply = await client.get(
                "/api/v1/nse-market/research", params={"horizon": horizon, "page_size": 5}
            )
            assert reply.status_code == 200
            data = reply.json()["data"]
            assert data["research_horizon_sessions"] == horizon
            assert data["ml_horizon_supported"] is (horizon == 5)
            assert data["provider_requests"] == 0
            assert data["candidates"][0]["evidence"]["ml_horizon_sessions"] == 5
            if horizon != 5:
                assert "NOT_HORIZON_FORECAST" in data["ranking_basis"]
                assert (
                    data["candidates"][0]["evidence"]["classification"]
                    == "TECHNICAL_RESEARCH_CANDIDATE"
                )
        assert (await client.get("/api/v1/nse-market/research?horizon=6")).status_code == 422
        assert (await client.get("/api/v1/nse-market/economic-research")).json()["data"][
            "state"
        ] == "NOT_YET_AVAILABLE"


@pytest.mark.parametrize("page_size", [5, 10, 20])
async def test_top_n_excludes_stale_scores_before_pagination_and_retains_saved_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, page_size: int
) -> None:
    saved_reads(monkeypatch)
    source = data_fixture()
    source["candidates"] = source["candidates"][:4]
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    # TEST_ONLY: the highest stored score is stale; seven days is the existing
    # inclusive research-display boundary, not an official-session assertion.
    for row, age in zip(source["candidates"], (8, 7, 1, 9), strict=True):
        row["session"] = (today - timedelta(days=age)).isoformat()
    original = copy.deepcopy(source)
    monkeypatch.setattr(engine, "workspace", lambda *args: copy.deepcopy(source))
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get(
            "/api/v1/nse-market/research", params={"horizon": 5, "page_size": page_size}
        )
        assert reply.status_code == 200
        data = reply.json()["data"]
        assert [row["symbol"] for row in data["candidates"]] == [
            "TEST_ONLY_1",
            "TEST_ONLY_2",
        ]
        assert data["total"] == data["unfiltered_total"] == 2
        assert data["recommendation_eligibility"] == {
            "policy": "EXCLUDE_STALE_SAVED_FIVE_SESSION_CANDIDATES_V1",
            "maximum_observation_age_calendar_days": 7,
            "saved_candidates": 4,
            "eligible_candidates": 2,
            "stale_excluded": 2,
            "applied": True,
            "accepted_ml": False,
        }
        assert data["provider_requests"] == data["accepted_current_rankings"] == 0
        historical = (
            await client.get("/api/v1/nse-market/research?horizon=10&page_size=20")
        ).json()["data"]
        assert len(historical["candidates"]) == 4
        assert historical["recommendation_eligibility"]["applied"] is False
        assert historical["recommendation_eligibility"]["stale_excluded"] == 0
        assert historical["ml_horizon_supported"] is False
        assert source == original
        for row in source["candidates"]:
            row["session"] = (today - timedelta(days=8)).isoformat()
        empty = (await client.get("/api/v1/nse-market/research")).json()["data"]
        assert empty["candidates"] == [] and empty["total"] == 0
        assert empty["recommendation_eligibility"]["stale_excluded"] == 4


async def test_lstm_context_must_match_the_actual_v2_observation_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_reads(monkeypatch)
    key = data_fixture()["candidates"][0]["key"]
    monkeypatch.setattr(
        nse_market,
        "_sequence",
        lambda service: (
            tmp_path,
            {"current_scores": [{"key": key, "session": "2020-01-01", "score": 0.6}]},
        ),
    )
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/research?page_size=1")
        assert reply.status_code == 200
        assert reply.json()["data"]["candidates"][0]["current_lstm"] is None


async def test_risk_ordering_is_explicit_deterministic_and_excludes_invalid_risk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_reads(monkeypatch)
    source = data_fixture()
    source["candidates"] = source["candidates"][:8]
    for row, score, sd in zip(
        source["candidates"],
        (0.9, 0.875, 0.75, 0.99, 0.99, 0.99, 0.99, 0.99),
        (0.4, 0.25, 0.125, -0.1, float("nan"), True, None, float("inf")),
        strict=True,
    ):
        row["score"] = score
        row["risk"]["return_daily_sd_20"] = sd
    source["candidates"][6]["risk"].pop("return_daily_sd_20")
    monkeypatch.setattr(engine, "workspace", lambda *args: copy.deepcopy(source))
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/research?rank_policy=risk_adjusted")
        assert reply.status_code == 200
        data = reply.json()["data"]
        assert [row["symbol"] for row in data["candidates"]] == [
            "TEST_ONLY_1",
            "TEST_ONLY_2",
            "TEST_ONLY_0",
        ]
        assert [row["ranking_value"] for row in data["candidates"]] == [0.625, 0.625, 0.5]
        assert [row["score"] for row in data["candidates"]] == [0.875, 0.75, 0.9]
        assert data["ranking_policy"] == {
            "policy": "risk_adjusted",
            "daily_volatility_penalty_weight": 1,
            "ordering_formula": "model_score - daily_return_sd",
            "invalid_risk_excluded": 5,
            "evidence_basis": "REGISTERED_ENGINEERING_ASSUMPTION_NOT_VALIDATED_EDGE",
        }
        source["candidates"] = list(reversed(source["candidates"][:3]))
        score = (await client.get("/api/v1/nse-market/research")).json()["data"]
        assert [row["symbol"] for row in score["candidates"]] == [
            "TEST_ONLY_0",
            "TEST_ONLY_1",
            "TEST_ONLY_2",
        ]
        assert score["ranking_policy"]["policy"] == "model_score"
        assert score["ranking_policy"]["daily_volatility_penalty_weight"] == 0
        assert (
            await client.get("/api/v1/nse-market/research?rank_policy=invented")
        ).status_code == 422


def data_fixture() -> dict[str, Any]:
    yesterday = datetime.now(UTC) - timedelta(days=1)
    candidates = []
    for index in range(205):
        isin, symbol = "INE" + str(index).zfill(9), f"TEST_ONLY_{index}"
        vector = [0.01] * 16
        vector[2], vector[8] = 0.03, 50.0
        candidates.append(
            {
                "key": "NSE_EQ|" + isin,
                "symbol": symbol,
                "session": yesterday.date().isoformat(),
                "observed_price": str(index + 1),
                "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
                "inference_at": yesterday.isoformat(),
                "score": 0.9 - index / 1000,
                "feature_names": list(LOCAL_FEATURE_NAMES),
                "features": vector,
                "risk": {
                    "return_daily_sd_20": 0.01,
                    "historical_price_drawdown_60": -0.10,
                    "volume": 10000,
                },
                "identity": {
                    "provider_key": "NSE_EQ|" + isin,
                    "symbol": symbol,
                    "isin": isin,
                    "name": f"TEST_ONLY Company {index}",
                    "exchange": "NSE",
                    "segment": "NSE_EQ",
                    "instrument_type": "EQ",
                },
            }
        )
    return {
        "state": "AVAILABLE",
        "accepted_current_rankings": 0,
        "coverage": {
            "configured_securities": 250,
            "validated_historical_securities": 230,
            "observations": 20000,
            "provider_queried_securities": 245,
            "provider_accessible_securities": 240,
            "technical_feature_eligible_securities": 210,
            "experimental_scored_securities": len(candidates),
            "per_security": [{"key": f"TEST_ONLY_{i}"} for i in range(250)],
            "not_observed": [{"key": f"TEST_ONLY_{i}"} for i in range(200)],
        },
        "technical_exclusions": [{"reason": "TEST_ONLY_GAP"}] * 200,
        "scores": {
            "candidates": candidates,
            "scored_securities": len(candidates),
            "original_evaluation": {
                "candidate_summary": {"TEST_ONLY_MODEL": {"balanced_accuracy": 0.50}},
                "baseline_summary": {"TEST_ONLY_BASELINE": {"balanced_accuracy": 0.51}},
                "historical_folds": ["TEST_ONLY_LARGE_AUDIT"] * 200,
            },
            "exclusions": [{"reason": "TEST_ONLY_EXCLUSION"}] * 200,
        },
        "candidates": candidates,
    }


def snapshot() -> universe.Snapshot:
    records = tuple(
        {
            "instrument_key": f"NSE_EQ|TEST_ONLY_{i}",
            "isin": f"TEST_ONLY_{i}",
            "symbol": f"TEST_ONLY_{i}",
            "name": f"TEST_ONLY Company {i}",
            "eligible_common_equity": i < 200,
        }
        for i in range(205)
    )
    return universe.Snapshot(
        "0" * 64,
        datetime.now(UTC),
        (),
        records,
        {
            "discoverable_nse_cash_identities": 205,
            "discoverable_nse_eq_type_eq": 201,
            "verified_eligible_common_equities": 200,
        },
    )


def saved_reads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, Path | None]]:
    calls: list[tuple[Path, Path | None]] = []

    def read(root: Path, v2_root: Path | None = None) -> dict[str, Any]:
        calls.append((root, v2_root))
        return copy.deepcopy(data_fixture())

    def no_provider(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("TEST_ONLY: GET must not acquire provider data")

    monkeypatch.setattr(engine, "workspace", read)
    monkeypatch.setattr(universe, "fresh", lambda root: snapshot())
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    return calls


async def test_saved_reads_require_authentication_and_bound_nested_arrays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = saved_reads(monkeypatch)
    root = tmp_path / "TEST_ONLY_v2"
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(update={"experimental_nse_v2_root": root})
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for path in ("research", "status", "universe"):
            assert (await client.get("/api/v1/nse-market/" + path)).status_code == 401
        assert calls == []
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/nse-market/research?page=2&page_size=100")
        assert result.status_code == 200
        assert result.headers["cache-control"] == "no-store"
        data = result.json()["data"]
        assert data["candidates"][0]["symbol"] == "TEST_ONLY_100"
        assert len(data["candidates"]) == len(data["coverage"]["per_security"]) == 100
        assert len(data["technical_exclusions"]) == len(data["scores"]["exclusions"]) == 100
        assert "candidates" not in data["scores"]
        assert "historical_folds" not in data["scores"]["original_evaluation"]
        assert data["counts"]["verified_eligible_common_equities"] == 200
        assert data["counts"]["experimental_ml_eligible_stocks"] == 205
        assert data["counts"]["independently_accepted_ml_stocks"] == 0
        assert data["provider_requests"] == 0
        assert data["candidates"][0]["score"] == pytest.approx(0.8)
        assert data["candidates"][0]["company_name"] == "TEST_ONLY Company 100"
        assert data["candidates"][0]["preference_metrics"]["price_return_percent"] == 3
        assert data["candidates"][0]["volatility_percent"] == 1
        assert (await client.get("/api/v1/nse-market/research?page_size=101")).status_code == 422
        assert (await client.get("/api/v1/nse-market/universe?page=0")).status_code == 422
        state = (await client.get("/api/v1/nse-market/status")).json()["data"]
        assert state["candidates"] == [] and state["edge_status"] == "NO_DEMONSTRATED_EDGE"
        assert (await client.post("/api/v1/nse-market/research", json={})).status_code in {403, 405}
    assert calls[0] == (tmp_path / "nse-market-expansion", root)


async def test_actual_personal_preferences_filter_normalized_saved_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_reads(monkeypatch)
    personal_root = tmp_path / "TEST_ONLY_personal"
    settings = build(tmp_path / "TEST_ONLY_evidence").model_copy(
        update={
            "experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2",
            "personal_root": personal_root,
        }
    )
    app = create_app(settings)
    transport = AuthenticatedTransport(app=app)
    operator = AuthStore(app.state.settings.auth_root).session(transport._session)
    owned = PersonalStore(personal_root, operator["account_id"])
    owned.initialize()
    owned.save("profile", "default", Profile(budget_inr="100").model_dump(), 0)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        data = (
            await client.get("/api/v1/nse-market/research?matches_only=true&page_size=100")
        ).json()["data"]
        assert data["unfiltered_total"] == 205 and data["total"] == 20
        assert len(data["candidates"]) == 20
        assert data["candidates"][0]["preferences"]["state"] == "MATCHES_SUPPORTED_CONSTRAINTS"
        assert data["candidates"][0]["portfolio_context"] == []


async def test_universe_search_only_returns_saved_current_eligible_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_reads(monkeypatch)
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        data = (await client.get("/api/v1/nse-market/universe?q=Company%201&page_size=100")).json()[
            "data"
        ]
        assert data["total"] == 111 and len(data["rows"]) == 100
        assert all(row["eligible_common_equity"] for row in data["rows"])
        assert data["historical_membership_established"] is False
        assert data["provider_requests"] == 0


async def test_stale_master_keeps_all_discovery_but_blocks_current_identity_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    saved_reads(monkeypatch)
    dated = replace(snapshot(), observed_at=datetime.now(UTC) - timedelta(days=3))

    def stale(root: Path) -> universe.Snapshot:
        raise ValueError("UNIVERSE_STALE_REFRESH_REQUIRED")

    monkeypatch.setattr(universe, "fresh", stale)
    monkeypatch.setattr(universe, "load", lambda root: dated)
    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/nse-market/universe?page_size=100")
        assert result.status_code == 200
        data = result.json()["data"]
        assert data["total"] == 200
        assert data["identity_status"]["state"] == "STALE"
        assert data["identity_status"]["current_identity_actions_available"] is False
        assert data["provider_requests"] == 0
        state = (await client.get("/api/v1/nse-market/status")).json()["data"]
        assert state["counts"]["verified_eligible_common_equities"] == 200


@pytest.mark.parametrize("size", [5, 10, 20])
async def test_ranking_considers_all_eligible_saved_predictions_beyond_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    saved_reads(monkeypatch)
    data = data_fixture()
    template = data["candidates"][0]
    data["candidates"] = []
    for index in range(725):
        row = copy.deepcopy(template)
        key, symbol = f"NSE_EQ|INE{index:09}", f"TEST_ONLY_{index}"
        row.update(key=key, symbol=symbol, score=0.5 + index / 2000)
        row["identity"].update(provider_key=key, isin=key.removeprefix("NSE_EQ|"), symbol=symbol)
        data["candidates"].append(row)
    monkeypatch.setattr(engine, "workspace", lambda *args: copy.deepcopy(data))
    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get(
            f"/api/v1/nse-market/research?page_size={size}&rank_policy=risk_adjusted"
        )
        assert reply.status_code == 200
        result = reply.json()["data"]
        assert result["total"] == result["unfiltered_total"] == 725
        assert len(result["candidates"]) == size
        assert result["candidates"][0]["symbol"] == "TEST_ONLY_724"
        assert result["provider_requests"] == 0


@pytest.mark.parametrize("fault", ["accepted", "identity", "future", "corrupt", "stale_master"])
async def test_invalid_or_promoted_evidence_is_rejected_without_private_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    saved_reads(monkeypatch)

    def invalid(root: Path, v2_root: Path | None = None) -> dict[str, Any]:
        data = data_fixture()
        if fault == "accepted":
            data["accepted_current_rankings"] = 1
        if fault == "identity":
            data["candidates"][0]["identity"]["symbol"] = "TEST_ONLY_OTHER"
        if fault == "future":
            data["candidates"][0]["session"] = (
                (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
            )
        if fault == "corrupt":
            raise ValueError("TEST_ONLY_PRIVATE_EVIDENCE_DETAIL")
        return data

    monkeypatch.setattr(engine, "workspace", invalid)
    if fault == "stale_master":

        def stale(root: Path) -> universe.Snapshot:
            raise ValueError("TEST_ONLY_PRIVATE_EVIDENCE_DETAIL")

        monkeypatch.setattr(universe, "fresh", stale)
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/nse-market/research")
        if fault == "stale_master":
            assert result.status_code == 200
            data = result.json()["data"]
            assert data["identity_status"]["current_identity_actions_available"] is False
            assert data["counts"]["verified_eligible_common_equities"] is None
            assert len(data["candidates"]) > 0
            assert (await client.get("/api/v1/nse-market/universe")).status_code == 503
        else:
            assert result.status_code == 503
        assert "TEST_ONLY_PRIVATE_EVIDENCE_DETAIL" not in result.text
        assert "TEST_ONLY_OTHER" not in result.text
