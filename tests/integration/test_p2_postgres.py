"""Opt-in real PostgreSQL metadata and immutable persistence; TEST_ONLY artifacts."""

import os
from pathlib import Path

import psycopg
import pytest

from alphalens_data.ingestion.acquisition import LocalFileSource
from alphalens_data.ingestion.contracts import ArtifactSpec
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import PostgresMetadataRepository
from alphalens_data.ingestion.storage import RawLanding

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.database
def test_real_postgres_ingestion_persistence_and_immutability(tmp_path: Path) -> None:
    url = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL not configured: no SQLite substitute")
    # Hide connection details from assertion introspection and driver tracebacks.
    try:
        connection = psycopg.connect(url, connect_timeout=3)
    except psycopg.Error:
        pytest.fail("Real PostgreSQL connection failed (details redacted)", pytrace=False)
    with connection:
        connection.execute((ROOT / "db/migrations/001_p2_ingestion_metadata.sql").read_text())
        repository = PostgresMetadataRepository(connection)
        pipeline = IngestionPipeline(RawLanding(tmp_path), repository, FixtureCSVParser())
        spec = ArtifactSpec.model_validate_json(
            (ROOT / "tests/fixtures/p2/TEST_ONLY.spec.json").read_bytes()
        )
        source = LocalFileSource(ROOT / "tests/fixtures/p2/TEST_ONLY.csv")
        first = pipeline.ingest(source, spec)
        second = pipeline.ingest(source, spec)
        assert second.duplicate
        assert repository.get_manifest(first.manifest.artifact_id) == first.manifest
        assert repository.get_run(first.report.run_id) == first.report
        assert pipeline.replay(first.manifest.artifact_id).records == first.records
        count = connection.execute(
            "SELECT count(*) FROM p2_ingestion.raw_artifacts WHERE artifact_id = %s",
            (first.manifest.artifact_id,),
        ).fetchone()
        assert count == (1,)
        with pytest.raises(psycopg.errors.RaiseException), connection.transaction():
            connection.execute(
                "DELETE FROM p2_ingestion.raw_artifacts WHERE artifact_id = %s",
                (first.manifest.artifact_id,),
            )
        connection.commit()
    # Verify durable state after a new connection, not only an uncommitted transaction.
    with psycopg.connect(url, connect_timeout=3) as reopened:
        assert PostgresMetadataRepository(reopened).get_run(first.report.run_id) == first.report
