"""Construct P2->P7 TEST_ONLY inputs. These prices/metrics are never market evidence."""

import argparse
from pathlib import Path

from scripts.build_p6_test_fixture import START, build_history, day, instant

from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_features.engine import build as build_features
from alphalens_features.models import BuildPlan, Decision, FeatureDataset
from alphalens_labels.alignment import SupervisedDataset, align
from alphalens_labels.engine import build as build_labels
from alphalens_labels.models import LabelPlan
from alphalens_training.contracts import TrainingConfig

FEATURE_COLUMNS = ("return_1", "sma_5", "volatility_5", "volume_ratio_20")
SECURITIES = ("TEST:ALPHA", "TEST:BETA", "TEST:BENCHMARK", "TEST:NEW", "TEST:DEPART")


def overrides(length: int = 90) -> dict[tuple[int, str], dict[str, str]]:
    result = {}
    for index in range(length):
        for offset, security in enumerate(SECURITIES):
            # Authored deterministic oscillations; no implied predictive process.
            close = 200 + ((index + offset * 7) % 32 - 16) * 2 + index // 8
            opening = close + (3 if (index + offset) % 2 else -3)
            result[index, security] = dict(
                close=str(close),
                open=str(opening),
                high=str(close + 5),
                low=str(close - 5),
                volume=str(1000 + ((index + offset) % 17) * 20),
            )
    return result


def config(
    horizon: int = 5, task: str = "classification", family: str = "logistic"
) -> TrainingConfig:
    return TrainingConfig.model_validate(
        dict(
            task=task,
            horizon=horizon,
            model_family=family,
            training_cutoff=instant(51, 12),
            validation_start=day(52),
            validation_end=day(68),
        )
    )


def datasets(batch: CanonicalBatch) -> tuple[FeatureDataset, dict[int, SupervisedDataset]]:
    reader = CanonicalReader(batch)
    features = build_features(
        reader,
        BuildPlan(
            history_start=START,
            decisions=tuple(
                Decision(session_date=day(i), knowledge_cutoff=instant(i, 12))
                for i in sorted({*range(0, 69, 4), 30})
            ),
        ),
    )
    labels = build_labels(
        reader, features, LabelPlan(outcome_cutoff=instant(89, 12), outcome_end=day(89))
    )
    return features, {
        h: align(
            features,
            labels,
            horizon=h,
            training_as_of=instant(89, 12),
            feature_columns=FEATURE_COLUMNS,
            allow_degraded=True,
        )
        for h in (1, 5, 10, 20)
    }


def prepare(root: Path) -> dict[int, SupervisedDataset]:
    batch = build_history(root / "canonical", length=90, overrides=overrides())[0]
    features, aligned = datasets(batch)
    publish(root / "features.json", features.to_bytes())
    for horizon, data in aligned.items():
        publish(root / f"supervised-{horizon}.json", data.to_bytes())
        for task, families in (
            ("classification", ("logistic", "random_forest", "hist_gradient_boosting")),
            ("regression", ("ridge", "random_forest", "hist_gradient_boosting")),
        ):
            for family in families:
                publish(
                    root / f"config-{task}-{family}-{horizon}.json",
                    stable_json(config(horizon, task, family).model_dump(mode="json")),
                )
    return aligned


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct TEST_ONLY P8 software evidence")
    parser.add_argument("--data-root", type=Path, default=Path("data/p8-test-only"))
    args = parser.parse_args()
    aligned = prepare(local_output(args.data_root))
    print(
        stable_json(
            dict(
                classification="TEST_ONLY",
                disclaimer="NOT A PERFORMANCE CLAIM",
                datasets={h: d.supervised_dataset_id for h, d in aligned.items()},
            )
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
