"""Build pinned development snapshots from verified canonical input declarations."""

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

import psycopg
from pydantic import ValidationError

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch, ReadContext
from alphalens_data.canonical.output import parquet_bytes
from alphalens_data.canonical.postgres import PostgresCanonical
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P5 canonical development build; no recommendations"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--knowledge-cutoff", type=datetime.fromisoformat, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/p5-snapshots"))
    parser.add_argument("--postgres", action="store_true")
    args = parser.parse_args(argv)
    try:
        envelope = json.loads(args.input.read_bytes())
        batch = verify_local_batch(
            CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
        )
        dataset = CanonicalReader(batch).build(
            args.start, args.end, ReadContext(knowledge_cutoff=args.knowledge_cutoff)
        )
        if args.postgres:
            url = os.environ.get("ALPHALENS_DATABASE_URL")
            if not url:
                raise DataContractError("POSTGRES_URL_UNAVAILABLE")
            with psycopg.connect(url, connect_timeout=3) as connection:
                repository = PostgresCanonical(connection)
                repository.save_input(batch)
                repository.save_snapshot(dataset)
        base = local_output(args.output) / dataset.dataset_id
        publish(base / "canonical-dataset.json", dataset.to_bytes())
        publish(base / "market-bars.parquet", parquet_bytes(dataset))
        print(
            stable_json(
                dict(
                    dataset_id=dataset.dataset_id,
                    schema_version=dataset.schema_version,
                    knowledge_cutoff=dataset.context.knowledge_cutoff.isoformat(),
                    classification=dataset.classification,
                    security_count=len(batch.securities),
                    record_count=len(dataset.prices),
                    family_states=dataset.family_states,
                    production_claims_permitted=False,
                )
            ).decode()
        )
        return 0
    except (DataContractError, ValidationError, ValueError, KeyError, OSError, psycopg.Error):
        # Never expose dataset contents, URLs or driver connection details.
        print(stable_json({"status": "REJECTED", "reason": "CANONICAL_BUILD_FAILED"}).decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
