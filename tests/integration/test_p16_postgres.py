"""Real PostgreSQL immutable paper event recovery and atomic accounting persistence."""

import os
from datetime import date
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection
from psycopg.conninfo import make_conninfo
from scripts.build_p6_test_fixture import build_history
from scripts.build_p15_test_fixture import clock
from scripts.build_p16_test_fixture import account, calendar, request
from test_p5_postgres import canonical_database as canonical_database

from alphalens_data.canonical.services import CanonicalReader
from alphalens_portfolio.paper import process_session
from alphalens_portfolio.paper_storage import PostgresPaper

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.database
def test_p16_postgres_atomic_unique_events_and_restart(
    canonical_database: Connection[tuple[object, ...]],
    tmp_path: Path,
) -> None:
    connection = canonical_database
    for name in ("003_p15_portfolio.sql", "004_p16_paper.sql"):
        connection.execute((ROOT / "db/migrations" / name).read_text(encoding="utf-8"))
    connection.execute((ROOT / "db/migrations/004_p16_paper.sql").read_text(encoding="utf-8"))
    reader = CanonicalReader(build_history(tmp_path, length=4)[0])
    repository = PostgresPaper(connection)
    state = account()
    repository.save(state)
    assert repository.get(state.ledger.portfolio.portfolio_id) == state
    state = process_session(
        state,
        reader,
        calendar(reader),
        date(2024, 1, 1),
        clock(1),
        manual=(request("alpha"), request("beta", security="TEST:BETA")),
    )
    repository.save(state)
    restored = repository.get(state.ledger.portfolio.portfolio_id)
    assert restored == state
    filled = process_session(restored, reader, calendar(reader), date(2024, 1, 2), clock(2))
    assert len(filled.fills) == 2
    repository.save(filled)
    repository.save(filled)
    assert repository.get(state.ledger.portfolio.portfolio_id) == filled
    count = connection.execute("SELECT count(*) FROM portfolio.paper_events").fetchone()
    assert count == (
        len(filled.orders) + len(filled.events) + len(filled.fills) + len(filled.reports),
    )
    with pytest.raises(ValueError, match="prefix conflict"):
        repository.save(state)
    assert repository.get(state.ledger.portfolio.portfolio_id) == filled
    with pytest.raises(psycopg.Error, match="Immutable"), connection.transaction():
        connection.execute("DELETE FROM portfolio.paper_events")
    connection.commit()
    assert repository.get(state.ledger.portfolio.portfolio_id) == filled
    with psycopg.connect(
        make_conninfo(os.environ["ALPHALENS_TEST_DATABASE_URL"], dbname=connection.info.dbname)
    ) as recovered:
        assert PostgresPaper(recovered).get(state.ledger.portfolio.portfolio_id) == filled
