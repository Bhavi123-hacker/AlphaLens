"""Offline development command: local fixture -> immutable raw -> canonical -> replay."""

import argparse
import logging
import os
from pathlib import Path

import psycopg

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.acquisition import LocalFileSource
from alphalens_data.ingestion.contracts import ArtifactSpec
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository, PostgresMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, stable_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--data-root", type=Path, default=Path("data/p2"))
    parser.add_argument(
        "--spec", type=Path, required=True, help="Explicit classification/evidence JSON"
    )
    parser.add_argument("--postgres", action="store_true", help="Use ALPHALENS_TEST_DATABASE_URL")
    args = parser.parse_args()
    # Keep all third-party output within designated ignored local roots.
    root = args.data_root.resolve()
    if not any(
        root.is_relative_to((Path.cwd() / name).resolve()) for name in ("data", ".local-data")
    ):
        parser.error("data-root must be within ignored data/ or .local-data/")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        spec = ArtifactSpec.model_validate_json(args.spec.read_bytes())
        landing = RawLanding(root)

        def execute(pipeline: IngestionPipeline) -> None:
            result = pipeline.ingest(LocalFileSource(args.fixture), spec)
            pipeline.replay(result.manifest.artifact_id)
            print(stable_json(result.report.model_dump(mode="json")).decode())

        if args.postgres:
            url = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
            if not url:
                parser.error("ALPHALENS_TEST_DATABASE_URL required; apply db migration first")
            with psycopg.connect(url, connect_timeout=3) as connection:
                execute(
                    IngestionPipeline(
                        landing, PostgresMetadataRepository(connection), FixtureCSVParser()
                    )
                )
        else:
            execute(
                IngestionPipeline(
                    landing, FileMetadataRepository(root / "metadata"), FixtureCSVParser()
                )
            )
    except DataContractError as exc:
        logging.error(stable_json({"event": "ingestion_failed", "reason": exc.code}).decode())
        return 1
    except Exception:
        # Do not echo provider paths, DSNs, model-validation values or source contents.
        logging.error('{"event":"ingestion_failed","reason":"inspect_local_inputs_and_state"}')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
