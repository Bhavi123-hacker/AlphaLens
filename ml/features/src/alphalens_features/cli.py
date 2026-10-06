"""Verified P5 envelope -> explicit decision plan -> immutable local feature artifacts."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_features.engine import build
from alphalens_features.models import BuildPlan
from alphalens_features.output import manifest, parquet_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P6 development features; no predictions")
    parser.add_argument("command", choices=["build"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/p6-features"))
    args = parser.parse_args(argv)
    try:
        envelope = json.loads(args.input.read_bytes())
        batch = verify_local_batch(
            CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
        )
        dataset = build(
            CanonicalReader(batch), BuildPlan.model_validate_json(args.plan.read_bytes())
        )
        base = local_output(args.output) / dataset.feature_set_id
        publish(base / "features.json", dataset.to_bytes())
        publish(base / "features.parquet", parquet_bytes(dataset))
        report = manifest(dataset)
        publish(base / "feature-manifest.json", stable_json(report))
        print(stable_json(report).decode())
        return 0
    except (DataContractError, ValidationError, ValueError, KeyError, OSError):
        print(stable_json(dict(status="REJECTED", reason="FEATURE_BUILD_FAILED")).decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
