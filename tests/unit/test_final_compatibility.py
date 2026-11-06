"""Stored metadata compatibility, no model execution or research evaluation."""

from pathlib import Path
from typing import Any

import pytest
from workers.daily.inference import verify_model

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum


def report(root: Path) -> dict[str, Any]:
    identity = dict(
        family="hist_gradient_boosting",
        horizon=1,
        dataset_id="a" * 64,
        feature_columns=["return_1"],
        fold=dict(fold_id="2026"),
        preprocessing="FRESH_TRAIN_ONLY_MEDIAN_LINEAR_SCALER_CONSTANT_REMOVAL",
        configuration=dict(training_cutoff="2025-12-30T18:29:59Z"),
    )
    key = checksum(stable_json(identity))
    path = root / f"models/{key}.skops"
    path.parent.mkdir()
    path.write_bytes(b"TEST_ONLY_METADATA_CHECK_NOT_SERIALIZED_MODEL")
    return dict(
        model_identity=identity,
        model_run_id=key,
        dataset_id="a" * 64,
        horizon=1,
        model_family="hist_gradient_boosting",
        task="classification",
        fold_id="2026",
        fold=dict(fold_id="2026"),
        usage_classification="RESEARCH_ONLY",
        model_file=f"models/{key}.skops",
        model_sha256=checksum(path.read_bytes()),
    )


def test_actual_raw_fold_contract_is_accepted_without_deserialization(tmp_path: Path) -> None:
    value = report(tmp_path)
    assert verify_model(tmp_path, value, "a" * 64).is_file()
    assert verify_model(tmp_path, value | dict(phase="2026"), "a" * 64).is_file()


@pytest.mark.parametrize(
    "change",
    [
        dict(fold=dict(fold_id="2025")),
        dict(phase="2025"),
        dict(model_sha256="b" * 64),
        dict(model_file="../model.skops"),
    ],
)
def test_rejects_changed_fold_checksum_and_path(tmp_path: Path, change: Any) -> None:
    with pytest.raises(DataContractError):
        verify_model(tmp_path, report(tmp_path) | change, "a" * 64)
