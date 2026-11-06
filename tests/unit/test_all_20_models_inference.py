"""Unit tests verifying all 20 trained ML models: loading, validation, and real-time inference."""

from __future__ import annotations

import math
from pathlib import Path
import pytest
import numpy as np

from workers.nse_market.multi_model_engine import (
    list_available_models,
    load_model,
    predict_with_model,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "data" / "models"

EXPECTED_20_MODELS = [
    # Horizon 1
    "HistGB_Classifier_H1",
    "RandomForest_Classifier_H1",
    "LogisticRegression_H1",
    "HistGB_Regressor_H1",
    "Ridge_Regressor_H1",
    # Horizon 5
    "HistGB_Classifier_H5",
    "RandomForest_Classifier_H5",
    "LogisticRegression_H5",
    "HistGB_Regressor_H5",
    "Ridge_Regressor_H5",
    # Horizon 10
    "HistGB_Classifier_H10",
    "RandomForest_Classifier_H10",
    "LogisticRegression_H10",
    "HistGB_Regressor_H10",
    "Ridge_Regressor_H10",
    # Horizon 20
    "HistGB_Classifier_H20",
    "RandomForest_Classifier_H20",
    "LogisticRegression_H20",
    "HistGB_Regressor_H20",
    "Ridge_Regressor_H20",
]


def test_all_20_model_artifacts_exist_on_disk() -> None:
    available = list_available_models(MODELS_DIR)
    assert len(available) == 20, f"Expected 20 models, found {len(available)}: {available}"
    assert available == sorted(EXPECTED_20_MODELS)


@pytest.mark.parametrize("model_name", EXPECTED_20_MODELS)
def test_each_model_loads_and_predicts(model_name: str) -> None:
    # 1. Load model artifact
    model = load_model(model_name, MODELS_DIR)
    assert model is not None

    # 2. Test with sample 12-feature vector
    # [ret_1, ret_5, ret_10, ret_20, vol_20, ma_dist_20, rsi_14, atr_14_rel, intraday, hl_range, volume_ratio_20, momentum_ratio]
    sample_features = [0.012, 0.035, 0.052, 0.081, 0.018, 0.025, 58.5, 0.015, 0.008, 0.021, 1.35, 1.94]

    result = predict_with_model(model_name, sample_features)
    assert result["model_name"] == model_name
    assert result["signal"] in ["BULLISH", "BEARISH"]

    if "Classifier" in model_name or "LogisticRegression" in model_name:
        assert result["type"] == "classification"
        assert 0.0 <= result["direction_probability"] <= 1.0
        assert result["predicted_direction"] in [0, 1]
    else:
        assert result["type"] == "regression"
        assert isinstance(result["expected_return"], float)
        assert math.isfinite(result["expected_return"])
        assert "expected_return_pct" in result


def test_horizon_coverage_across_all_20_models() -> None:
    horizons = [1, 5, 10, 20]
    architectures = [
        "HistGB_Classifier",
        "RandomForest_Classifier",
        "LogisticRegression",
        "HistGB_Regressor",
        "Ridge_Regressor",
    ]

    available = set(list_available_models(MODELS_DIR))
    for h in horizons:
        for arch in architectures:
            expected_key = f"{arch}_H{h}"
            assert expected_key in available, f"Missing {expected_key} in model registry"


def test_batch_inference_capability() -> None:
    # Test batch prediction for 100 stocks simultaneously
    clf = load_model("HistGB_Classifier_H5", MODELS_DIR)
    reg = load_model("HistGB_Regressor_H5", MODELS_DIR)

    X_batch = np.random.randn(100, 12)

    probs = clf.predict_proba(X_batch)[:, 1]
    assert len(probs) == 100
    assert np.all((probs >= 0.0) & (probs <= 1.0))

    returns = reg.predict(X_batch)
    assert len(returns) == 100
    assert np.all(np.isfinite(returns))


def test_model_execution_results_artifact_integrity() -> None:
    results_path = REPO_ROOT / "docs" / "ml" / "multi_model_execution_results.json"
    assert results_path.exists(), "multi_model_execution_results.json not found"

    import json
    data = json.loads(results_path.read_text(encoding="utf-8"))

    assert data["schema"] == "alphalens.multi_model_evaluation.v1"
    assert "metrics" in data
    assert len(data["metrics"]) == 20, f"Expected 20 evaluation metrics entries, found {len(data['metrics'])}"

    assert "rankings" in data
    for h in [1, 5, 10, 20]:
        h_key = f"Horizon_{h}"
        assert h_key in data["rankings"]
        h_data = data["rankings"][h_key]
        assert len(h_data["top_5"]) == 5
        assert len(h_data["top_10"]) == 10
        assert len(h_data["top_20"]) == 20
