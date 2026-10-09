"""P17 real PostgreSQL 17 reads of visibly TEST_ONLY ledgers and paper records."""

import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import Connection
from scripts.build_p15_test_fixture import bought
from scripts.build_p16_test_fixture import account
from scripts.build_p17_test_evidence import build
from test_p5_postgres import canonical_database as canonical_database

from alphalens_api.core.config import Settings
from alphalens_api.main import create_app
from alphalens_api.portfolio_reads import PortfolioReads
from alphalens_portfolio.accounting import reconstruct
from alphalens_portfolio.paper_storage import PostgresPaper
from alphalens_portfolio.storage import PostgresPortfolio

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.database, pytest.mark.anyio]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def prepare(connection: Connection[tuple[object, ...]]) -> Settings:
    for name in ("003_p15_portfolio.sql", "004_p16_paper.sql"):
        connection.execute((ROOT / "db/migrations" / name).read_text(encoding="utf-8"))
    connection.commit()
    parts = urlsplit(os.environ["ALPHALENS_TEST_DATABASE_URL"])
    return Settings(
        environment="test", database_url=parts._replace(path="/" + connection.info.dbname).geturl()
    )


async def test_p17_fifo_records_unavailable_valuation_and_readonly_connection(
    canonical_database: Connection[tuple[object, ...]],
) -> None:
    connection = canonical_database
    settings = prepare(connection)
    ledger = bought()
    repository = PostgresPortfolio(connection)
    repository.create(ledger.portfolio)
    for transaction in ledger.transactions:
        repository.append(transaction)
    connection.commit()
    now = datetime.now(UTC)
    expected = reconstruct(ledger, now.date(), now)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        accounts = await client.get("/api/v1/portfolios")
        assert accounts.status_code == 200
        assert len(accounts.json()["data"]) == 1
        holdings = await client.get(f"/api/v1/portfolios/{ledger.portfolio.portfolio_id}/holdings")
        assert holdings.status_code == 200
        body = holdings.json()
        assert body["data"]["market_value"] is None
        assert body["data"]["positions"] == [p.model_dump(mode="json") for p in expected.positions]
        assert body["classification"]["usage_classification"] == "TEST_ONLY"
        performance = await client.get(
            f"/api/v1/portfolios/{ledger.portfolio.portfolio_id}/performance"
        )
        assert performance.json()["data"]["accounting"] == expected.model_dump(mode="json")
        assert performance.json()["data"]["portfolio_value"] is None
        assert performance.json()["data"]["unrealized_pnl"] is None
        transactions = await client.get(
            f"/api/v1/portfolios/{ledger.portfolio.portfolio_id}/transactions?limit=1"
        )
        assert transactions.json()["page"]["has_more"] is True
        assert (await client.get("/api/v1/portfolios/TEST_ONLY_UNKNOWN")).status_code == 404
        assert (
            await client.post(f"/api/v1/portfolios/{ledger.portfolio.portfolio_id}/transactions")
        ).status_code == 405
    with (
        PortfolioReads(settings).connection() as read_connection,
        pytest.raises(psycopg.errors.ReadOnlySqlTransaction),
    ):
        read_connection.execute("CREATE TABLE test_only_write_rejected (id INTEGER)")
    assert repository.get(ledger.portfolio.portfolio_id) == ledger


async def test_p17_paper_empty_state_no_execution_and_bounded_records(
    canonical_database: Connection[tuple[object, ...]],
) -> None:
    connection = canonical_database
    settings = prepare(connection)
    state = account()
    repository = PostgresPaper(connection)
    repository.save(state)
    connection.commit()
    before = repository.get(state.ledger.portfolio.portfolio_id)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        accounts = await client.get("/api/v1/paper/accounts")
        assert accounts.status_code == 200
        assert len(accounts.json()["data"]) == 1
        for suffix in ("", "/orders", "/trades", "/performance"):
            result = await client.get(
                f"/api/v1/paper/accounts/{state.ledger.portfolio.portfolio_id}" + suffix
            )
            assert result.status_code == 200
            assert result.json()["data"]["simulation_only"] is True
            assert result.json()["classification"]["usage_classification"] == "TEST_ONLY_PAPER"
        assert (
            await client.get(f"/api/v1/paper/accounts/{state.ledger.portfolio.portfolio_id}/trades")
        ).json()["data"]["trades"] == []
        assert (
            await client.post(
                f"/api/v1/paper/accounts/{state.ledger.portfolio.portfolio_id}/orders"
            )
        ).status_code == 405
    assert repository.get(state.ledger.portfolio.portfolio_id) == before


async def test_p17_empty_database_is_empty_records_not_missing_database(
    canonical_database: Connection[tuple[object, ...]],
) -> None:
    settings = prepare(canonical_database)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/portfolios")).json()["data"] == []
        assert (await client.get("/api/v1/paper/accounts")).json()["data"] == []


async def test_p17_configured_research_readiness_is_not_production_ready(
    canonical_database: Connection[tuple[object, ...]],
    tmp_path: Path,
) -> None:
    database = prepare(canonical_database)
    settings = build(tmp_path / "TEST_ONLY_READY").model_copy(
        update={"database_url": database.database_url}
    )
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings)), base_url="http://testserver"
    ) as client:
        result = await client.get("/api/v1/ready")
        assert result.status_code == 200
        assert result.json()["data"]["research_read_ready"] is True
        assert result.json()["data"]["production_ready"] is False
        assert result.json()["data"]["components"]["database"]["access"] == "TRANSACTION_READ_ONLY"
