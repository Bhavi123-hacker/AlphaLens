"""Reproducible TEST_ONLY arena across four horizons; no market-performance evidence."""

import argparse
from pathlib import Path
from typing import Any

from scripts.build_p6_test_fixture import day, instant
from scripts.build_p8_test_fixture import prepare
from scripts.build_p9_training_snapshots import snapshots

from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_evaluation.contracts import Fold, WalkForwardDefinition
from alphalens_evaluation.engine import evaluate
from alphalens_evaluation.storage import OOSDataset, load, save
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset


def definition(
    data: SupervisedDataset,
    features: FeatureDataset,
    task: str,
    training_data: dict[str, SupervisedDataset],
) -> WalkForwardDefinition:
    return WalkForwardDefinition.model_validate(
        dict(
            feature_set_id=data.feature_set_id,
            label_set_id=data.label_set_id,
            canonical_dataset_id=features.canonical_dataset_id,
            supervised_dataset_id=data.supervised_dataset_id,
            training_dataset_ids={fid: d.supervised_dataset_id for fid, d in training_data.items()},
            horizon=data.horizon,
            task=task,
            data_classification=data.classification,
            model_families=[
                "logistic" if task == "classification" else "ridge",
                "random_forest",
                "hist_gradient_boosting",
                "lightgbm",
                "catboost",
                "xgboost",
            ],
            folds=[
                Fold(
                    fold_id=f"fold-{i}",
                    training_cutoff=instant(start - 1, 12),
                    test_start=day(start),
                    test_end=day(end),
                )
                for i, (start, end) in enumerate(((52, 56), (60, 64), (68, 68)), 1)
            ],
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="TEST_ONLY — NOT A PERFORMANCE CLAIM")
    parser.add_argument("--inputs", type=Path, default=Path("data/p9-test-only"))
    parser.add_argument("--output", type=Path, default=Path("data/p9-evaluations"))
    args = parser.parse_args()
    if not (args.inputs / "features.json").exists():
        prepare(args.inputs)
    features = FeatureDataset.model_validate_json((args.inputs / "features.json").read_bytes())
    training = snapshots(args.inputs, features)
    summaries: list[dict[str, Any]] = []
    for horizon in (1, 5, 10, 20):
        data = SupervisedDataset.model_validate_json(
            (args.inputs / f"supervised-{horizon}.json").read_bytes()
        )
        for task in ("classification", "regression"):
            plan = definition(data, features, task, training[horizon])
            first, second = (
                evaluate(data, features, plan, training[horizon]),
                evaluate(data, features, plan, training[horizon]),
            )
            if (
                first.manifest != second.manifest
                or first.fold_metrics != second.fold_metrics
                or first.predictions != second.predictions
                or first.negative_control != second.negative_control
            ):
                raise RuntimeError("P9 deterministic replay mismatch")
            OOSDataset(first.manifest, first.predictions).verify()
            directory = save(first, args.output)
            if load(directory).predictions != first.predictions:
                raise RuntimeError("P9 OOS round trip mismatch")
            publish(
                args.inputs / f"p9-cutoff-definition-{task}-{horizon}.json",
                stable_json(plan.model_dump(mode="json")),
            )
            summaries.append(
                dict(
                    evaluation_id=first.manifest["evaluation_id"],
                    horizon=horizon,
                    task=task,
                    prediction_count=len(first.predictions),
                    fold_metrics=first.fold_metrics,
                    model_comparison=first.model_comparison,
                    stability=first.stability_report,
                    negative_control=first.negative_control,
                )
            )
            print(
                f"TEST_ONLY — NOT A PERFORMANCE CLAIM: {task} {horizon} "
                f"{len(first.predictions)} OOS rows"
            )
    publish(
        args.output / "suite-summary.TEST_ONLY.json",
        stable_json(
            dict(
                disclaimer="TEST_ONLY — NOT A PERFORMANCE CLAIM",
                data_classification="TEST_ONLY",
                production_claims_permitted=False,
                evaluations=summaries,
                deterministic_replay=True,
            )
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
