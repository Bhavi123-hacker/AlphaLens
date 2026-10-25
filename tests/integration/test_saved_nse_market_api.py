"""TEST_ONLY saved-market auth and bounded read tests, no provider transport."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.nse_market.saved_market import project
from workers.providers import universe

from alphalens_api import nse_saved
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


def saved_view() -> dict[str, object]:
    return project(
        {
            "dataset_id": "TEST_ONLY",
            "sessions": ["2026-10-19", "2026-10-21"],
            "identities": [
                {"provider_key": "NSE_EQ|INE000000000", "symbol": "TEST_ONLY", "name": None}
            ],
            "rows": [
                {
                    "key": "NSE_EQ|INE000000000",
                    "session": day,
                    "open": "100",
                    "high": "115",
                    "low": "85",
                    "close": close,
                    "volume": 123,
                    "received_at": "2026-10-22T10:00:00+00:00",
                }
                for day, close in [("2026-10-19", "100"), ("2026-10-21", "110")]
            ],
            "source_observed_at": "2026-10-22T10:00:00+00:00",
            "price_basis": "TEST_ONLY",
        },
        at=datetime(2026, 10, 24, 6, tzinfo=UTC),
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_saved_views_require_authentication_and_validate_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(build(tmp_path / "TEST_ONLY"))
    monkeypatch.setattr(nse_saved, "_view", lambda service: saved_view())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/saved-market")).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/saved-market?order=gainers")
        assert reply.status_code == 200
        assert reply.json()["data"]["provider_requests"] == 0
        assert reply.json()["data"]["rows"][0]["change"] == "10"
        assert (await client.get("/api/v1/nse-market/saved-market?limit=51")).status_code == 422
        assert (
            await client.get("/api/v1/nse-market/saved-market?order=unknown")
        ).status_code == 422

        reply = await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE000000000")
        assert reply.status_code == 200
        assert len(reply.json()["data"]["rows"]) == 2
        assert (
            await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE999999999")
        ).status_code == 404
        assert (
            await client.get("/api/v1/nse-market/saved-history?key=../secret")
        ).status_code == 422


@pytest.mark.parametrize("supported", [True, False])
async def test_master_only_stock_detail_opens_without_candles_or_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supported: bool
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    monkeypatch.setattr(nse_saved, "_view", lambda service: saved_view())
    record = {
        "instrument_key": "NSE_EQ|INE999999999",
        "isin": "INE999999999",
        "symbol": "TEST_ONLY_NO_HISTORY",
        "name": "TEST_ONLY company",
        "eligible_common_equity": supported,
        "classification": "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"
        if supported
        else "UNSUPPORTED_NON_COMMON_SERIES",
    }
    snapshot = universe.Snapshot("0" * 64, datetime(2026, 10, 20, tzinfo=UTC), (), (record,), {})
    monkeypatch.setattr(universe, "load", lambda root: snapshot)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE999999999")
        assert reply.status_code == 200
        result = reply.json()["data"]
        assert result["rows"] == [] and result["provider_requests"] == 0
        row = result["security"]
        assert row["support_status"] == (
            "SUPPORTED_EQUITY_NO_SAVED_HISTORY" if supported else "UNSUPPORTED_INSTRUMENT"
        )
        assert row["close"] is row["volume"] is row["change"] is row["session"] is None
        assert row["ml_status"] == "NO_COMPATIBLE_SAVED_PREDICTION"
        assert row["identity_status"]["current_identity_actions_available"] is False


async def test_master_discovery_works_before_any_market_projection_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphalens_api.core.domain_errors import APIError

    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )

    def missing(service: object) -> dict[str, object]:
        raise APIError("SAVED_MARKET_PUBLICATION_PENDING", "TEST_ONLY", 503)

    monkeypatch.setattr(nse_saved, "_view", missing)
    record = {
        "instrument_key": "NSE_EQ|INE999999999",
        "isin": "INE999999999",
        "symbol": "TEST_ONLY_NO_HISTORY",
        "name": "TEST_ONLY company",
        "eligible_common_equity": True,
        "classification": "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY",
    }
    snapshot = universe.Snapshot("0" * 64, datetime(2026, 10, 20, tzinfo=UTC), (), (record,), {})
    monkeypatch.setattr(universe, "load", lambda root: snapshot)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE999999999")
        assert reply.status_code == 200
        data = reply.json()["data"]
        assert data["latest_observed_session"] is None and data["rows"] == []
        assert data["security"]["close"] is None


async def test_detail_prediction_retains_original_dates_model_and_no_new_forecast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES

    app = create_app(build(tmp_path / "TEST_ONLY"))
    view = saved_view()
    original = datetime.now(UTC) - timedelta(days=2)
    candidate = {
        "key": "NSE_EQ|INE000000000",
        "symbol": "TEST_ONLY",
        "score": 0.61,
        "model_id": "TEST_ONLY_MODEL",
        "session": original.date().isoformat(),
        "inference_at": original.isoformat(),
        "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
        "observed_price": "100",
        "feature_names": list(LOCAL_FEATURE_NAMES),
        "features": [0.1] * 16,
        "risk": {"return_daily_sd_20": 0.1, "historical_price_drawdown_60": -0.1, "volume": 100},
        "identity": {
            "provider_key": "NSE_EQ|INE000000000",
            "symbol": "TEST_ONLY",
            "isin": "INE000000000",
            "segment": "NSE_EQ",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "name": "TEST_ONLY company",
        },
    }
    view["research_workspace"] = {"candidates": [candidate]}
    monkeypatch.setattr(nse_saved, "_view", lambda service: view)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/nse-market/saved-history?key=NSE_EQ%7CINE000000000")
        assert response.status_code == 200
        security = response.json()["data"]["security"]
        saved = security["saved_prediction"]
        assert saved["inference_at"] == original.isoformat()
        assert saved["session"] == original.date().isoformat()
        assert saved["model_id"] == "TEST_ONLY_MODEL" and saved["horizon_sessions"] == 5
        assert saved["forecast_created_by_this_request"] is False
        assert saved["calibrated_probability"] is None
        assert security["descriptive_risk"]["reason"] == "INSUFFICIENT_21_OBSERVED_CLOSES"


async def test_coverage_endpoint_authentication_and_full_master_denominator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    monkeypatch.setattr(nse_saved, "_view", lambda service: saved_view())
    records = tuple(
        {"instrument_key": f"NSE_EQ|INE{index:09}", "eligible_common_equity": True}
        for index in range(1200)
    )
    snapshot = universe.Snapshot("0" * 64, datetime(2026, 10, 20, tzinfo=UTC), (), records, {})
    monkeypatch.setattr(universe, "load", lambda root: snapshot)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/universe-coverage")).status_code == 401
        assert (
            await client.get("/api/v1/nse-market/identity-history?key=NSE_EQ%7CINE000000000")
        ).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/universe-coverage")
        assert reply.status_code == 200
        data = reply.json()["data"]
        assert data["supported_equities"] == data["searchable_equities"] == 1200
        assert data["available_saved_prices"] == 1
        assert data["exclusions"]["no_saved_price"] == 1199
        assert data["provider_requests"] == 0
