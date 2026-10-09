"""P17 isolated TEST_ONLY persisted contracts; never interpreted as real-market evidence."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from scripts.build_p17_test_evidence import OTHER, SECURITY, build

from alphalens_api.artifacts import confined, read_json
from alphalens_api.core.config import Settings
from alphalens_api.core.domain_errors import APIError
from alphalens_api.main import create_app
from alphalens_api.schemas import Envelope, PricePoint
from alphalens_api.services import ResearchService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def evidence(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return build(tmp_path_factory.mktemp("p17"))


def ids(settings: Settings) -> tuple[str, str]:
    service = ResearchService(settings)
    model = service.reports()[0]["model_run_id"]
    backtest = service.reader.report("backtesting/real-research-economic-audit.json")["runs"][0][
        "backtest_id"
    ]
    return model, backtest


async def test_health_readiness_and_freshness(evidence: Settings) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        health = await client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["data"]["production_ready"] is False
        ready = await client.get("/api/v1/ready")
        assert ready.status_code == 503
        assert ready.json()["data"]["research_read_ready"] is False
        current = await client.get("/api/v1/system/data-freshness")
        assert current.json()["as_of_session"] == "2013-11-05"
        assert current.json()["data"]["freshness"] == "STALE"
        assert current.json()["data"]["live_data"] == "UNAVAILABLE"


async def test_identity_continuity_and_no_isin_backfill(evidence: Settings) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        detail = (await client.get(f"/api/v1/stocks/{SECURITY}")).json()["data"]
        assert detail["security_id"] == SECURITY
        assert {r["symbol"] for r in detail["observed_identity_evidence"]} == {"TESTOLD", "TESTNEW"}
        price = (await client.get(f"/api/v1/stocks/{SECURITY}/history?limit=1")).json()
        assert price["data"][0]["isin"] is None
        assert price["classification"]["data_reality"] == "TEST_ONLY"
        Envelope[list[PricePoint]].model_validate(price)
        other = (await client.get(f"/api/v1/stocks/{OTHER}")).json()["data"]
        assert other["security_id"] != detail["security_id"]


async def test_price_filter_missing_session_and_page(evidence: Settings) -> None:
    app = create_app(evidence)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        uri = f"/api/v1/stocks/{SECURITY}/history?start=2013-11-03&end=2013-11-05&limit=2"
        first = (await client.get(uri)).json()
        assert first["page"] == {"limit": 2, "offset": 0, "has_more": True, "total": 3}
        missing = first["data"][0]
        assert missing["session"] == "2013-11-03"
        assert missing["observation_status"] == "PRICE_OBSERVATION_MISSING"
        assert all(missing[k] is None for k in ("open", "high", "low", "close", "volume"))
        assert first["data"][1]["open"] == "10.123456789012345678"
        second = (await client.get(uri + "&offset=2")).json()
        assert second["data"][0]["session"] == "2013-11-05"
        assert second["page"]["has_more"] is False
        assert (await client.get(uri)).json() == first
        domain = app.state.research.history(SECURITY, date(2013, 11, 3), date(2013, 11, 5), 2, 0)
        assert domain.model_dump(mode="json") == first


async def test_stock_search_sort_pagination_and_literal_query(evidence: Settings) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        a = (await client.get("/api/v1/stocks?q=TESTNEW&limit=1")).json()
        b = (await client.get("/api/v1/stocks?q=TESTNEW&limit=1&offset=1")).json()
        assert a["page"]["has_more"] is True
        assert a["data"][0]["security_id"] < b["data"][0]["security_id"]
        assert (await client.get("/api/v1/stocks?q=%25")).json()["data"] == []


async def test_indicators_warmup_and_projection(evidence: Settings) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get(f"/api/v1/stocks/{SECURITY}/indicators?feature=sma_200")
        assert result.status_code == 200
        data = result.json()["data"]
        assert data["points"][0]["value"] is None
        assert data["points"][0]["state"] == "UNAVAILABLE"
        assert data["points"][1]["value"] == 10.5
        assert data["units"] == "INR_RAW_PRICE"
        assert "TEST_ONLY_TARGET_MUST_NOT_LEAK" not in result.text
        invalid = await client.get(f"/api/v1/stocks/{SECURITY}/indicators?feature=target_return_1")
        assert invalid.status_code == 422
        assert invalid.json()["error_code"] == "FEATURE_NOT_SUPPORTED"


async def test_model_metrics_readonly_holdout_predictions(evidence: Settings) -> None:
    model, _ = ids(evidence)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get(f"/api/v1/research/models/{model}")
        assert result.json()["data"]["metrics"]["brier_score"] == 0.25
        holdout = await client.get("/api/v1/research/evaluation")
        assert holdout.json()["data"]["final_holdout_evaluated"] is True
        predictions = await client.get(
            f"/api/v1/research/predictions?model_id={model}&security_id={SECURITY}"
        )
        assert predictions.status_code == 200
        row = predictions.json()["data"][0]
        assert row["role"] == "FOLD_TEST"
        assert row["interpretation"] == "PERSISTED_OOS_RESEARCH_NOT_LIVE_SIGNAL"
        assert "TEST_ONLY_TARGET_MUST_NOT_LEAK" not in predictions.text
        assert (await client.get("/api/v1/research/models?phase=2026")).json()["page"]["total"] == 1
        assert (await client.post("/api/v1/research/evaluation")).status_code == 405


@pytest.mark.parametrize("route", ["opportunities", "rankings", "signals"])
async def test_current_decisions_remain_unavailable(evidence: Settings, route: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/" + route)
        assert result.status_code == 503
        assert result.json()["data"] is None
        assert "RESEARCH_METRICS_ARE_NOT_LIVE_SIGNALS" in result.json()["missing_data_reasons"]


async def test_security_decisions_unknown_security_and_error(evidence: Settings) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        assert (await client.get(f"/api/v1/signals/{SECURITY}")).status_code == 503
        assert (await client.get(f"/api/v1/explanations/{SECURITY}")).status_code == 503
        result = await client.get("/api/v1/stocks/TEST_ONLY_UNKNOWN")
        assert result.status_code == 404
        assert result.json()["error_code"] == "SECURITY_NOT_FOUND"


async def test_unresolved_backtest_never_becomes_profitability(evidence: Settings) -> None:
    _, backtest = ids(evidence)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        result = await client.get(f"/api/v1/research/backtests/{backtest}/performance")
        assert result.status_code == 200
        body = result.json()
        assert body["evidence_status"] == "UNRESOLVED_ECONOMIC_OUTCOMES"
        assert body["data"]["summary"]["total_return"] is None
        assert body["data"]["summary"]["sharpe"] is None
        assert body["data"]["equity"][0]["portfolio_value"] is None
        assert body["data"]["benchmark_status"] == "UNAVAILABLE"
        assert body["data"]["economic_evidence"]["cause_counts"] == {"TEST_ONLY_MISSING_PRICE": 1}


@pytest.mark.parametrize(
    "suffix",
    [
        "?limit=501",
        "?offset=10001",
        "?limit=0",
        "/TEST_ONLY_UNKNOWN/history?start=2026-01-02&end=2026-01-01",
    ],
)
async def test_validation_guards(evidence: Settings, suffix: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(evidence)), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/stocks" + suffix)).status_code == 422


async def test_missing_sources_are_not_successful_empty_datasets() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(Settings(environment="test"))),
        base_url="http://testserver",
    ) as client:
        for route in (
            "stocks",
            "research/models",
            "research/backtests",
            "portfolios",
            "paper/accounts",
        ):
            assert (await client.get("/api/v1/" + route)).status_code == 503


async def test_local_peer_origin_and_cors_security(evidence: Settings) -> None:
    app = create_app(evidence)
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("203.0.113.1", 1234)), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/portfolios")).status_code == 403
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (
            await client.get("/api/v1/health", headers={"Origin": "https://outside.invalid"})
        ).status_code == 403
        allowed = await client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" not in allowed.headers
        assert (await client.post("/api/v1/paper/accounts")).status_code == 405


async def test_response_size_limit_and_forwarded_header_not_trusted(evidence: Settings) -> None:
    app = create_app(evidence.model_copy(update={"max_response_bytes": 1024}))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        result = await client.get(f"/api/v1/stocks/{SECURITY}/history")
        assert result.status_code == 413
        assert result.json()["error_code"] == "RESPONSE_LIMIT"
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("203.0.113.1", 1234)),
        base_url="http://testserver",
    ) as client:
        result = await client.get("/api/v1/health", headers={"X-Forwarded-For": "127.0.0.1"})
        assert result.status_code == 403


def test_configuration_prevents_public_cors_and_test_mode_in_development() -> None:
    for origins in (("*",), ("https://public.example",), ("http://user:password@localhost",)):
        with pytest.raises(ValidationError):
            Settings(cors_origins=origins)
    with pytest.raises(ValidationError):
        Settings(test_only_evidence=True)


async def test_fixture_cannot_be_served_as_real_evidence(evidence: Settings) -> None:
    settings = evidence.model_copy(update={"test_only_evidence": False})
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/stocks")
        assert result.status_code == 503
        assert result.json()["error_code"] == "CLASSIFICATION_BLOCKED"


def test_openapi_contract_has_unique_operations_and_valid_references(evidence: Settings) -> None:
    schema = create_app(evidence).openapi()
    operations = [
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    ]
    assert len(operations) == len(set(operations))
    assert len(schema["paths"]) >= 30
    assert all(set(path) == {"get"} for path in schema["paths"].values())

    def verify(node: Any) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                target = schema
                for part in node["$ref"].removeprefix("#/").split("/"):
                    target = target[part]
            for value in node.values():
                verify(value)
        elif isinstance(node, list):
            for value in node:
                verify(value)

    verify(schema)


def test_checksum_tamper_fails_closed(evidence: Settings, tmp_path: Path) -> None:
    service = ResearchService(evidence)
    path = tmp_path / "TEST_ONLY_INVALID"
    path.write_bytes(b"TEST_ONLY_CORRUPT")
    with pytest.raises(APIError, match="checksum"):
        service.reader.verify(path, "0" * 64)
    with pytest.raises(APIError, match="reference"):
        confined(tmp_path, "../outside")


def test_capacity_guard_and_release(evidence: Settings) -> None:
    service = ResearchService(evidence.model_copy(update={"max_concurrent_reads": 1}))
    with service.reader.budget():
        with pytest.raises(APIError) as failure, service.reader.budget():
            pass
        assert failure.value.status == 429
    with service.reader.budget():
        pass


def test_build_index_does_not_change_sources(evidence: Settings) -> None:
    assert evidence.catalog_path is not None
    receipt = read_json(evidence.catalog_path.with_suffix(".sources.json"))
    assert receipt["data_reality"] == "TEST_ONLY"
    assert receipt["usage_classification"] == "TEST_ONLY"
    assert receipt["alias_groups"] == 4
    assert json.dumps(receipt).find("TEST_ONLY_SOURCE") >= 0


def test_uvicorn_exception_diagnostics_redact_private_record_text() -> None:
    script = """
import logging
import uvicorn
from alphalens_api.core.logging import server_logging_config
uvicorn.Config('alphalens_api.main:app', log_config=server_logging_config(), access_log=False)
try:
    raise ValueError('TEST_ONLY_PRIVATE_RECORD')
except ValueError:
    logging.getLogger('uvicorn.error').exception('ASGI failed: TEST_ONLY_PRIVATE_RECORD')
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True, timeout=15
    )
    assert "TEST_ONLY_PRIVATE_RECORD" not in result.stderr
    assert "Traceback" not in result.stderr
    diagnostic = json.loads(result.stderr)
    assert diagnostic["event"] == "redacted"
    assert diagnostic["severity"] == "ERROR"
    assert diagnostic["service"] == "alphalens-api"
