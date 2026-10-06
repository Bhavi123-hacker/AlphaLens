"""P9 orchestration invokes P7 unchanged: labels/alignment are built at each fold cutoff."""

import json
from pathlib import Path

from scripts.build_p6_test_fixture import day, instant
from scripts.build_p8_test_fixture import FEATURE_COLUMNS

from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.storage import publish
from alphalens_features.engine import build as build_features
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset, align
from alphalens_labels.engine import build
from alphalens_labels.models import LabelPlan


def snapshots(root: Path, features: FeatureDataset) -> dict[int, dict[str, SupervisedDataset]]:
    result: dict[int, dict[str, SupervisedDataset]] = {h: {} for h in (1, 5, 10, 20)}
    missing = [i for i in range(1, 4) if not (root / f"p9-training-1-fold-{i}.json").exists()]
    reader = (
        CanonicalReader(
            CanonicalBatch.model_validate(
                json.loads((root / "canonical/canonical-input.json").read_bytes())["batch"]
            )
        )
        if missing
        else None
    )
    for i, cutoff in enumerate((51, 59, 67), 1):
        historical_features = None
        labels = None
        if reader is not None and i in missing:
            historical_features = build_features(
                reader,
                features.feature_set.plan.model_copy(
                    update={
                        "decisions": tuple(
                            d
                            for d in features.feature_set.plan.decisions
                            if d.knowledge_cutoff <= instant(cutoff, 12)
                        )
                    }
                ),
            )
            labels = build(
                reader,
                historical_features,
                LabelPlan(outcome_cutoff=instant(cutoff, 12), outcome_end=day(cutoff)),
            )
        for horizon in result:
            path = root / f"p9-training-{horizon}-fold-{i}.json"
            if not path.exists():
                assert labels is not None and historical_features is not None
                data = align(
                    historical_features,
                    labels,
                    horizon=horizon,
                    training_as_of=instant(cutoff, 12),
                    feature_columns=FEATURE_COLUMNS,
                    allow_degraded=True,
                )
                publish(path, data.to_bytes())
            result[horizon][f"fold-{i}"] = SupervisedDataset.model_validate_json(path.read_bytes())
    return result
