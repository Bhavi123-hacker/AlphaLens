"""PostgreSQL research-manifest isolation/replay; constructed examples are TEST_ONLY."""

import json
import os
import secrets
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from alphalens_data.canonical.research import save_manifest
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchProfile, lineage


@pytest.mark.database
def test_research_manifest_postgres_immutable_replay_and_isolation() -> None:
    url = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL not configured; no SQLite substitute")
    name = "alphalens_research_test_only_" + secrets.token_hex(4)
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(make_conninfo(url, dbname=name)) as connection:
                migration = Path("db/migrations/006_research_dataset_catalog.sql").read_text(
                    encoding="utf-8"
                )
                connection.execute(migration)
                connection.execute(migration)
                identity = dict(
                    **lineage(ResearchProfile()),
                    source="TEST_ONLY_CONSTRUCTED_NOT_MARKET_DATA",
                    files=[],
                )
                data = dict(identity=identity, dataset_id=checksum(stable_json(identity)))
                save_manifest(connection, data)
                save_manifest(connection, data)
                assert connection.execute("SELECT count(*) FROM research.datasets").fetchone() == (
                    1,
                )
                # Genuine local manifests are replayed only when the research stages exist.
                for path in (
                    "docs/data/research-canonical-summary.json",
                    "docs/data/research-dataset-identity.json",
                ):
                    p = Path(path)
                    if p.exists():
                        real = json.loads(p.read_bytes())
                        save_manifest(connection, real)
                        save_manifest(connection, real)
                with pytest.raises(psycopg.Error), connection.transaction():
                    connection.execute(
                        "UPDATE research.datasets SET classification=%s", ("PRODUCTION",)
                    )
                with pytest.raises(psycopg.Error), connection.transaction():
                    connection.execute("DELETE FROM research.datasets")
                connection.commit()
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
