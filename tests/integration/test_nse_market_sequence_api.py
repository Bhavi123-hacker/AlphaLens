"""TEST_ONLY saved sequence evidence, chronology and authenticated read contracts."""

import copy
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from workers.experimental_nse.acquire import digest
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES
from workers.nse_market import engine, forward_cohort
from workers.providers.upstox import UpstoxClient

from alphalens_api import nse_market
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio
KEY = "NSE_EQ|INE002A01018"


async def test_same_experiment_economics_are_saved_only_and_do_not_expose_decision_bodies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(build(tmp_path / "TEST_ONLY_evidence"))
    top: dict[str, Any] = {
        "decision_count": 3,
        "mean_membership_turnover": 0.8,
        "decisions": [{"TEST_ONLY_PRIVATE": True}],
        "scenarios": [
            {
                "round_trip_cost_bps": 50,
                "slippage_bps_each_side": 5,
                "net_compounded_reference_return": -0.2,
                "curve": [{"TEST_ONLY": 1}],
            }
        ],
    }
    report: dict[str, Any] = {
        "comparisons": {
            name: {
                "metrics": {"sample_count": 99},
                "economic_sensitivity": {"strategies": {"top5": copy.deepcopy(top)}},
            }
            for name in ("LSTM", "XGBOOST", "mean_reversion")
        },
        "current_scores": [],
    }
    monkeypatch.setattr(nse_market, "_sequence", lambda service: (tmp_path, report))
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/sequence")
    assert reply.status_code == 200
    data = reply.json()["data"]
    assert data["provider_requests"] == 0
    for name in report["comparisons"]:
        result = data["comparisons"][name]["top5_reference"]
        assert result["decision_count"] == 3
        assert result["scenarios"][0]["net_compounded_reference_return"] == -0.2
        assert "decisions" not in result and "curve" not in result["scenarios"][0]
    assert report["comparisons"]["LSTM"]["economic_sensitivity"]["strategies"]["top5"] == top


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def candidate() -> dict[str, Any]:
    yesterday = datetime.now(UTC) - timedelta(days=1)
    return {
        "key": KEY,
        "symbol": "TEST_ONLY",
        "session": yesterday.date().isoformat(),
        "observed_price": "100",
        "inference_at": yesterday.isoformat(),
        "score": 0.55,
        "feature_names": list(LOCAL_FEATURE_NAMES),
        "features": [0.01] * 16,
        "risk": {"return_daily_sd_20": 0.01, "historical_price_drawdown_60": -0.1, "volume": 10},
        "identity": {
            "provider_key": KEY,
            "symbol": "TEST_ONLY",
            "isin": KEY.split("|")[1],
            "name": "TEST_ONLY COMPANY",
            "exchange": "NSE",
            "segment": "NSE_EQ",
            "instrument_type": "EQ",
        },
    }


def save_sequence(
    root: Path, *, change: dict[str, Any] | None = None, historical_future: bool = False
) -> None:
    root.mkdir()
    yesterday = datetime.now(UTC) - timedelta(days=1)
    model = {"protocol_sha256": "a" * 64}
    engine._checked(root / "model.json", model)
    sha = digest((root / "model.json").read_bytes())
    score = {
        "key": KEY,
        "symbol": "TEST_ONLY",
        "session": yesterday.date().isoformat(),
        "score": 0.55,
        "model_sha256": sha,
        "inference_at": yesterday.isoformat(),
        "source_observed_at": (yesterday - timedelta(hours=1)).isoformat(),
        "classification": "EXPERIMENTAL_ML",
        "calibration_status": "NOT_ESTABLISHED",
        "forecast_created": False,
    }
    if change:
        score.update(change)
    report = {
        "family": "ALPHALENS_SEQUENCE_BENCHMARK_V1",
        "state": "EXPERIMENTAL_UNVALIDATED",
        "feature_version": "nse.price-state.sequence20x8.v1",
        "accepted_rankings": 0,
        "prospective_forecasts": 0,
        "matured_prospective_outcomes": 0,
        "model_sha256": sha,
        "protocol_sha256": model["protocol_sha256"],
        "completed_at": (yesterday + timedelta(minutes=1)).isoformat(),
        "current_scores": [score],
        "comparisons": {
            "LSTM": {
                "metrics": {"balanced_accuracy": 0.5},
                "economic_sensitivity": {"strategies": {}},
            }
        },
    }
    engine._checked(root / "report.json", report)
    engine._checked(
        root / "historical-predictions.json",
        {
            "model_sha256": sha,
            "rows": [
                {
                    "key": KEY,
                    "decision_session": (yesterday - timedelta(days=10)).date().isoformat(),
                    "target_session": (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
                    if historical_future
                    else yesterday.date().isoformat(),
                    "actual_price_component_return": 0.01,
                    "actual_positive": 1,
                    "ridge_return_estimate": 0.005,
                    "scores": {"LSTM": 0.55},
                    "classification": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
                }
            ],
        },
    )


def no_provider(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("TEST_ONLY saved research must never call provider")


async def test_sequence_and_stock_research_are_authenticated_and_missing_inputs_remain_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "v2"}
        )
    )
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    monkeypatch.setattr(nse_market, "_read", lambda service: {"candidates": []})
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/sequence")).status_code == 401
        assert (await client.get("/api/v1/nse-market/stock-research?key=" + KEY)).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        missing = await client.get("/api/v1/nse-market/stock-research?key=" + KEY)
        assert missing.status_code == 200 and missing.headers["cache-control"] == "no-store"
        data = missing.json()["data"]
        assert data["state"] == "NO_COMPLETE_COMPATIBLE_SAVED_INPUTS"
        assert data["v2"] is data["lstm"] is None
        assert (
            data["missing_evidence"]
            and data["accepted_rankings"] == data["prospective_outcomes"] == 0
        )
        assert (await client.get("/api/v1/nse-market/sequence")).json()["data"][
            "state"
        ] == "NOT_YET_AVAILABLE"


async def test_stock_research_rejects_future_v2_decision_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "v2"}
        )
    )
    row = candidate()
    row["inference_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    monkeypatch.setattr(nse_market, "_read", lambda service: {"candidates": [copy.deepcopy(row)]})
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/stock-research?key=" + KEY)).status_code == 503


@pytest.mark.parametrize("corrupt", [False, True])
async def test_stock_forward_history_updates_without_acquisition_and_corruption_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: bool
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "v2"}
        )
    )
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    monkeypatch.setattr(nse_market, "_read", lambda service: {"candidates": []})

    def history(*args: Any) -> dict[str, Any]:
        if corrupt:
            raise sqlite3.DatabaseError("TEST_ONLY unreadable ledger")
        return {"forecast_count": 3, "matured_outcomes": 2, "pending_forecasts": 1, "rows": []}

    monkeypatch.setattr(forward_cohort, "stock_history", history)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        reply = await client.get("/api/v1/nse-market/stock-research?key=" + KEY)
        if corrupt:
            assert reply.status_code == 503
            assert "TEST_ONLY unreadable ledger" not in reply.text
        else:
            assert reply.status_code == 200
            data = reply.json()["data"]
            assert data["prospective_outcomes"] == 2
            assert data["prospective_history"]["pending_forecasts"] == 1
            assert data["accepted_rankings"] == data["provider_requests"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"inference_at": "2099-01-01T00:00:00+00:00"},
        {"source_observed_at": "2099-01-01T00:00:00+00:00"},
        {"session": "2099-01-01"},
        {"score": 1.1},
        {"forecast_created": True},
    ],
)
async def test_sequence_rejects_future_or_incompatible_saved_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: dict[str, Any]
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "v2"}
        )
    )
    save_sequence(tmp_path / "sequence-benchmark-v1", change=change)
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/sequence")).status_code == 503


async def test_genuine_shape_sequence_history_stays_descriptive_and_rejects_unmatured_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(
        build(tmp_path / "TEST_ONLY_evidence").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "v2"}
        )
    )
    save_sequence(tmp_path / "sequence-benchmark-v1", historical_future=True)
    monkeypatch.setattr(UpstoxClient, "get", no_provider)
    monkeypatch.setattr(nse_market, "_read", lambda service: {"candidates": [candidate()]})
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        sequence = await client.get("/api/v1/nse-market/sequence")
        assert sequence.status_code == 200
        assert sequence.json()["data"]["current_scored_count"] == 1
        assert sequence.json()["data"]["prospective_forecasts"] == 0
        assert (await client.get("/api/v1/nse-market/stock-research?key=" + KEY)).status_code == 503
