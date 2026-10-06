"""Developer walk-forward replay; never a stock recommendation."""

import argparse
from pathlib import Path

from alphalens_data.ingestion.storage import stable_json
from alphalens_evaluation.contracts import WalkForwardDefinition
from alphalens_evaluation.engine import evaluate
from alphalens_evaluation.storage import save
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset


def main() -> int:
    parser = argparse.ArgumentParser(description="P9 walk-forward development evaluation")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--training-dataset",
        action="append",
        required=True,
        help="Repeat FOLD_ID=PATH for cutoff-specific P7 aligned inputs",
    )
    args = parser.parse_args()
    result = evaluate(
        SupervisedDataset.model_validate_json(args.dataset.read_bytes()),
        FeatureDataset.model_validate_json(args.features.read_bytes()),
        WalkForwardDefinition.model_validate_json(args.definition.read_bytes()),
        {
            item.split("=", 1)[0]: SupervisedDataset.model_validate_json(
                Path(item.split("=", 1)[1]).read_bytes()
            )
            for item in args.training_dataset
        },
    )
    path = save(result, args.output)
    print(
        stable_json(
            dict(
                evaluation_id=result.manifest["evaluation_id"],
                disclaimer=result.manifest["disclaimer"],
                classification=result.manifest["data_classification"],
                prediction_count=len(result.predictions),
                output=str(path),
            )
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
