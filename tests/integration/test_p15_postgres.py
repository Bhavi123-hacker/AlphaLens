"""Actual PostgreSQL durability, row-lock append and immutable mutation guards."""

import os
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection
from psycopg.conninfo import make_conninfo
from scripts.build_p15_test_fixture import account, bought, event
from test_p5_postgres import canonical_database as canonical_database

from alphalens_portfolio.storage import PostgresPortfolio

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.database
def test_p15_postgres_append_replay_restart_and_mutation(
    canonical_database: Connection[tuple[object, ...]],
) -> None:
    connection = canonical_database
    migration = (ROOT / "db/migrations/003_p15_portfolio.sql").read_text()
    connection.execute(migration)
    connection.execute(migration)
    repository = PostgresPortfolio(connection)
    repository.create(account().portfolio)
    repository.create(account().portfolio)
    for transaction in bought().transactions:
        repository.append(transaction)
        repository.append(transaction)
    assert repository.get("TEST_ONLY_MANUAL") == bought()
    with pytest.raises(ValueError, match="NO_SHORT"):
        repository.append(event("SELL", 3, "oversell", quantity="11"))
    assert repository.get("TEST_ONLY_MANUAL") == bought()
    with pytest.raises(ValueError, match="identity conflict"):
        repository.append(event("BUY", 2, "buy", price="999"))
    with pytest.raises(psycopg.Error, match="Immutable"), connection.transaction():
        connection.execute("DELETE FROM portfolio.transactions")
    with pytest.raises(psycopg.Error, match="Immutable"), connection.transaction():
        connection.execute("UPDATE portfolio.accounts SET payload='{}'")
    connection.commit()
    with psycopg.connect(
        make_conninfo(os.environ["ALPHALENS_TEST_DATABASE_URL"], dbname=connection.info.dbname)
    ) as reopened:
        assert PostgresPortfolio(reopened).get("TEST_ONLY_MANUAL") == bought()
