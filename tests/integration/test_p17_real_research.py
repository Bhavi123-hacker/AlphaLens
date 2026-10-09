"""Opt-in reads of actual frozen TejHQ/P6/P9/P10 evidence; never re-evaluate a model."""

import asyncio
import os
from datetime import date
from pathlib import Path

import pyarrow.dataset as ds
import pytest
from httpx import ASGITransport, AsyncClient

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app
from alphalens_api.services import ResearchService


@pytest.fixture(scope="module")
def real_service() -> ResearchService:
    names = (
        "ALPHALENS_TEST_REAL_DATA_ROOT",
        "ALPHALENS_TEST_REAL_RUN_ROOT",
        "ALPHALENS_TEST_REAL_REPORT_ROOT",
        "ALPHALENS_TEST_REAL_CATALOG",
    )
    if not all(os.environ.get(name) for name in names):
        pytest.skip("Local-only frozen research artifacts not configured; no synthetic substitute")
    return ResearchService(
        Settings(
            research_data_root=Path(os.environ[names[0]]),
            research_run_root=Path(os.environ[names[1]]),
            research_report_root=Path(os.environ[names[2]]),
            catalog_path=Path(os.environ[names[3]]),
        )
    )


def test_real_price_history_parity_missing_muhurat_and_research_classification(
    real_service: ResearchService,
) -> None:
    security = "tejhq:isin:INE002A01018"
    result = real_service.history(security, date(2023, 11, 10), date(2023, 11, 14), 100, 0)
    assert result.classification.data_reality == "REAL_MARKET_OBSERVATIONS"
    assert result.classification.usage_classification == "RESEARCH_ONLY"
    assert result.classification.production_market_data_use == "NOT_CLEARED"
    missing = next(p for p in result.data if p.session == date(2023, 11, 12))
    assert missing.open is None and missing.close is None and missing.volume is None
    manifest = real_service.reader.manifest("canonical-manifest.json")
    with real_service.reader.budget() as deadline:
        path = real_service.reader.partition(manifest, security, deadline)
    persisted = (
        ds.dataset(path)
        .to_table(
            columns=["session_date", "open", "close"],
            filter=(ds.field("security_id") == security)
            & (ds.field("session_date") == date(2023, 11, 10)),
        )
        .to_pylist()[0]
    )
    assert result.data[0].open == persisted["open"]
    assert result.data[0].close == persisted["close"]


def test_real_sma200_read_is_exact_stored_feature(real_service: ResearchService) -> None:
    security = "tejhq:isin:INE002A01018"
    day = date(2026, 1, 1)
    result = real_service.indicators(security, "sma_200", day, day, 1, 0)
    manifest = real_service.reader.manifest("supervised-manifest.json")
    with real_service.reader.budget() as deadline:
        path = real_service.reader.partition(manifest, security, deadline)
    persisted = (
        ds.dataset(path)
        .to_table(
            columns=["sma_200", "sma_200__state"],
            filter=(ds.field("security_id") == security) & (ds.field("session_date") == day),
        )
        .to_pylist()[0]
    )
    assert isinstance(result.data, dict)
    points = result.data["points"]
    assert isinstance(points, list) and isinstance(points[0], dict)
    assert points[0]["value"] == persisted["sma_200"]
    assert points[0]["state"] == persisted["sma_200__state"]


def test_real_oos_prediction_and_once_evaluated_holdout_read_only(
    real_service: ResearchService,
) -> None:
    reports = real_service.reports()
    assert len(reports) == 152
    report = next(r for r in reports if r["fold_id"] == "2022" and r["task"] == "classification")
    result = real_service.predictions(
        report["model_run_id"], "tejhq:isin:INE001A01036", None, None, 2, 0
    )
    assert result.data and result.data[0].role == "FOLD_TEST"
    with real_service.reader.budget() as deadline:
        path = real_service.reader.oos(report, deadline)
    persisted = (
        ds.dataset(path)
        .to_table(
            columns=["prediction_id", "score"],
            filter=ds.field("security_id") == "tejhq:isin:INE001A01036",
        )
        .to_pylist()[0]
    )
    assert result.data[0].prediction_id == persisted["prediction_id"]
    assert result.data[0].score == persisted["score"]
    document = real_service.reader.report("ml/real-model-comparison.json")
    assert real_service.evaluation().data == document
    assert {r["research_status"] for r in document["selected"].values()} == {
        "REAL_RESEARCH_INSUFFICIENT_EVIDENCE"
    }


def test_all_real_unresolved_backtests_retain_unavailable_economic_metrics(
    real_service: ResearchService,
) -> None:
    audit = real_service.reader.report("backtesting/real-research-economic-audit.json")
    unresolved = [r for r in audit["runs"] if r["status"] == "UNRESOLVED_ECONOMIC_OUTCOMES"]
    assert len(audit["runs"]) == 504 and len(unresolved) == 474
    for run in unresolved:
        detail = real_service.backtests(run["backtest_id"], None, None, 1, 0)
        assert isinstance(detail.data, dict)
        summary = detail.data["summary"]
        assert isinstance(summary, dict)
        assert all(
            summary[k] is None
            for k in ("total_return", "cagr", "sharpe", "sortino", "maximum_drawdown")
        )
        assert detail.evidence_status == "UNRESOLVED_ECONOMIC_OUTCOMES"
        assert detail.data["economic_evidence"] == run


def test_real_http_routes_match_service_and_frozen_provenance(
    real_service: ResearchService,
) -> None:
    async def verify() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=create_app(real_service.reader.settings)),
            base_url="http://localhost",
        ) as client:
            result = await client.get(
                "/api/v1/stocks/tejhq:isin:INE002A01018/history?start=2023-11-10&end=2023-11-14"
            )
            assert result.status_code == 200
            expected = real_service.history(
                "tejhq:isin:INE002A01018", date(2023, 11, 10), date(2023, 11, 14), 250, 0
            )
            assert result.json() == expected.model_dump(mode="json")
            assert result.json()["provenance"]["dataset"] == "tejhq/indian-markets"
            assert (
                result.json()["provenance"]["revision"]
                == "14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98"
            )
            signals = await client.get("/api/v1/signals/tejhq:isin:INE002A01018")
            assert signals.status_code == 503
            assert signals.json()["data"] is None

    asyncio.run(verify())
