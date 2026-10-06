"""Disposable real PostgreSQL P5 schema, immutable replay and PIT verification."""

import os
import secrets
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection, sql
from psycopg.conninfo import make_conninfo
from scripts.build_p5_test_fixture import build_fixture_p5

from alphalens_data.canonical.models import PriceRevision, ReadContext, revision_key
from alphalens_data.canonical.postgres import PostgresCanonical
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def canonical_database() -> Iterator[Connection[tuple[object, ...]]]:
    url = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL not configured: no SQLite substitute")
    try:
        admin = psycopg.connect(url, connect_timeout=3, autocommit=True)
    except psycopg.Error:
        pytest.fail("Real PostgreSQL connection failed (details redacted)", pytrace=False)
    name = "alphalens_p5_test_only_" + secrets.token_hex(4)
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(make_conninfo(url, dbname=name), connect_timeout=3) as connection:
                yield connection
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.mark.database
def test_real_postgres_canonical_schema_replay_constraints_and_pit(
    tmp_path: Path,
    canonical_database: Connection[tuple[object, ...]],
) -> None:
    connection = canonical_database
    reopen_url = make_conninfo(
        os.environ["ALPHALENS_TEST_DATABASE_URL"], dbname=connection.info.dbname
    )
    batch, _ = build_fixture_p5(tmp_path)
    with connection:
        for name in ("001_p2_ingestion_metadata.sql", "002_p5_canonical.sql"):
            connection.execute((ROOT / "db/migrations" / name).read_text())
        # Migration replay must preserve existing evidence.
        connection.execute((ROOT / "db/migrations/002_p5_canonical.sql").read_text())
        repository = PostgresCanonical(connection)
        repository.save_input(batch)
        repository.save_input(batch)
        repository.save_input(
            batch.model_copy(update={"revisions": tuple(reversed(batch.revisions))})
        )
        pinned = repository.get_input(batch.input_id)
        assert pinned is not None and pinned.to_bytes() == batch.to_bytes()
        reader = CanonicalReader(pinned)
        old = reader.build(
            date(2024, 1, 1),
            date(2024, 1, 10),
            ReadContext(knowledge_cutoff=datetime(2024, 1, 10, 12, tzinfo=UTC)),
        )
        new = reader.build(
            date(2024, 1, 1),
            date(2024, 1, 20),
            ReadContext(knowledge_cutoff=datetime(2024, 1, 20, 12, tzinfo=UTC)),
        )
        for snapshot in (old, new):
            repository.save_snapshot(snapshot)
            repository.save_snapshot(snapshot)
        assert repository.get_snapshot(old.dataset_id) == old
        assert repository.get_snapshot(new.dataset_id) == new
        assert old.dataset_id != new.dataset_id
        assert repository.get_security("TEST:C") is not None
        bars = repository.list_revisions("BAR", "TEST:A")
        assert len(bars) == 6
        corrected = next(r for r in bars if r.revision_number == 2)
        assert repository.get_revision(revision_key(corrected)) == corrected
        # The relational availability predicate agrees with the canonical read service.
        known = connection.execute(
            "SELECT revision_id FROM canonical.record_revisions WHERE kind='BAR' "
            "AND security_id='TEST:A' AND effective_from='2024-01-10' AND available_at<=%s "
            "ORDER BY revision_number DESC LIMIT 1",
            (old.context.knowledge_cutoff,),
        ).fetchone()
        assert known == ("r1",)
        count = connection.execute("SELECT count(*) FROM canonical.record_revisions").fetchone()
        assert count == (len(batch.revisions),)
        indexes = connection.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname='canonical'"
        ).fetchall()
        assert {
            "canonical_revision_pit",
            "canonical_bar_history",
            "canonical_identity_isin",
            "canonical_snapshot_lookup",
        } <= {str(r[0]) for r in indexes}
        with pytest.raises(DataContractError, match="IMMUTABLE"), connection.transaction():
            repository.put_revision(corrected.model_copy(update={"currency": None}))
        with pytest.raises(psycopg.errors.RaiseException), connection.transaction():
            connection.execute(
                "DELETE FROM canonical.record_revisions WHERE record_key=%s",
                (revision_key(corrected),),
            )
        with pytest.raises(psycopg.errors.RaiseException), connection.transaction():
            repository.put_revision(
                corrected.model_copy(
                    update={
                        "revision_id": "r3",
                        "revision_number": 3,
                        "supersedes_revision_id": "r1",
                    }
                )
            )
        # DB hard invariants run even for direct SQL clients; no Python-only protection.
        bar = next(
            r
            for r in bars
            if isinstance(r, PriceRevision)
            and r.revision_number == 1
            and r.session_date == date(2024, 1, 10)
        )
        for values in (
            (100, 99, 90, 100, 10),
            (100, 110, 90, 100, -1),
            (0, 110, 90, 100, 10),
            (100, "NaN", 90, 100, 10),
        ):
            with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
                connection.execute(
                    "INSERT INTO canonical.record_revisions SELECT %s,kind,source,'TEST_ONLY:bad',"
                    "revision_id,revision_number,parent_key,security_id,classification,effective_from,"
                    "effective_to,published_at,available_at,ingested_at,artifact_sha256,"
                    "jsonb_set(jsonb_set(payload,'{logical_record_id}','\"TEST_ONLY:bad\"'),'{values}',"
                    "jsonb_build_object('open',%s::text,'high',%s::text,'low',%s::text,"
                    "'close',%s::text,'volume',%s::text)) "
                    "FROM canonical.record_revisions WHERE record_key=%s",
                    ("f" * 64, *values, revision_key(bar)),
                )
                connection.execute(
                    "INSERT INTO canonical.market_bars_eod "
                    "(record_key,security_id,session_date,price_basis,open,high,low,close,volume,"
                    "currency,quality_key,rejection_reason_codes) "
                    "VALUES (%s,'TEST:A','2024-01-10','OBSERVED_UNKNOWN_BASIS',"
                    "%s,%s,%s,%s,%s,%s,%s,'{}')",
                    ("f" * 64, *values, bar.currency, bar.quality_key),
                )
        with pytest.raises(psycopg.errors.ForeignKeyViolation), connection.transaction():
            connection.execute(
                "INSERT INTO canonical.record_lineage "
                "(lineage_id,record_key,artifact_id,normalized_record_id,evidence_reference) "
                "VALUES (%s,%s,%s,%s,'TEST_ONLY')",
                ("f" * 64, revision_key(bar), "f" * 64, "f" * 64),
            )
        with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
            connection.execute(
                "INSERT INTO canonical.securities VALUES ('TEST:PROD','NSE','PRODUCTION')"
            )
        # A direct SQL writer cannot attach unrelated raw bytes as provenance.
        with pytest.raises(psycopg.errors.RaiseException), connection.transaction():
            connection.execute(
                "INSERT INTO canonical.record_revisions SELECT %s,kind,source,"
                "'TEST_ONLY:bad-lineage',"
                "revision_id,revision_number,parent_key,security_id,classification,effective_from,"
                "effective_to,published_at,available_at,ingested_at,%s,"
                "jsonb_set(jsonb_set(payload,'{logical_record_id}','\"TEST_ONLY:bad-lineage\"'),"
                "'{provenance,artifact_sha256}',to_jsonb(%s::text)) "
                "FROM canonical.record_revisions WHERE record_key=%s",
                ("e" * 64, "0" * 64, "0" * 64, revision_key(bar)),
            )
            connection.execute(
                "INSERT INTO canonical.record_lineage SELECT %s,%s,artifact_id,"
                "normalized_record_id,"
                "quarantine_key,source_record_id,evidence_reference FROM canonical.record_lineage "
                "WHERE record_key=%s LIMIT 1",
                ("e" * 64, "e" * 64, revision_key(bar)),
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        connection.commit()
    with psycopg.connect(reopen_url, connect_timeout=3) as reopened:
        assert PostgresCanonical(reopened).get_snapshot(old.dataset_id) == old
