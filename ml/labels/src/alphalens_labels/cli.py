"""Developer outcome and alignment build; no training, metrics or recommendations."""

import argparse
import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import align
from alphalens_labels.engine import build
from alphalens_labels.models import LabelPlan
from alphalens_labels.output import distribution, manifest, parquet_bytes, supervised_parquet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P7 supervised targets; no ML or performance claims"
    )
    parser.add_argument("command", choices=["build"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/p7-labels"))
    parser.add_argument("--join-horizon", type=int, default=5)
    parser.add_argument("--feature-columns", nargs="+")
    parser.add_argument("--allow-degraded", action="store_true")
    args = parser.parse_args(argv)
    try:
        envelope = json.loads(args.input.read_bytes())
        batch = verify_local_batch(
            CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
        )
        features = FeatureDataset.model_validate_json(args.features.read_bytes())
        plan = LabelPlan.model_validate_json(args.plan.read_bytes())
        labels = build(CanonicalReader(batch), features, plan)
        joined = align(
            features,
            labels,
            horizon=args.join_horizon,
            training_as_of=plan.outcome_cutoff,
            feature_columns=tuple(args.feature_columns) if args.feature_columns else None,
            allow_degraded=args.allow_degraded,
        )
        base = local_output(args.output) / labels.label_set_id
        publish(base / "labels.json", labels.to_bytes())
        publish(base / "labels.parquet", parquet_bytes(labels))
        publish(base / "label-manifest.json", stable_json(manifest(labels)))
        publish(base / "target-distribution.json", stable_json(distribution(labels)))
        join_base = base / joined.supervised_dataset_id
        publish(join_base / "supervised.json", joined.to_bytes())
        publish(join_base / "supervised.parquet", supervised_parquet(joined))
        print(
            stable_json(
                dict(
                    label_set_id=labels.label_set_id,
                    rows=len(labels.rows),
                    horizons=plan.horizons,
                    maturity_counts=dict(Counter(r.maturity for r in labels.rows)),
                    training_eligible_count=sum(
                        r.metadata["training_eligibility"] == "TRAINING_ELIGIBLE"
                        for r in joined.rows
                    ),
                    supervised_dataset_id=joined.supervised_dataset_id,
                    classification=labels.classification,
                    production_claims_permitted=False,
                )
            ).decode()
        )
        return 0
    except (DataContractError, ValidationError, ValueError, KeyError, OSError):
        print(stable_json(dict(status="REJECTED", reason="LABEL_BUILD_FAILED")).decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
