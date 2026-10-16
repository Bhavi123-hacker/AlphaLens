"""TEST_ONLY score-only orchestration preserves model and final evaluation bytes."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse import inference, models
from workers.experimental_nse.acquire import FAMILY, digest, encoded, initialize, write_new
from workers.experimental_nse.features import FEATURE_NAMES, FEATURE_VERSION, TARGET_VERSION


def initialized(root: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    initialize(root)
    now = datetime.now(UTC)
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    model = {
        "schema": models.MODEL_SCHEMA,
        "family": FAMILY,
        "feature_version": FEATURE_VERSION,
        "target_version": TARGET_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "dataset_id": "TEST_ONLY_TRAINING_DATASET",
        "trained_at": (now - timedelta(days=2)).isoformat(),
        "training_last_session": "2024-01-01",
        "training_target_last_session": "2024-01-08",
        "algorithm": "STANDARD_SCALER_LOGISTIC_REGRESSION",
        "parameters": {"C": 1.0, "class_weight": "balanced", "max_iter": 1000, "random_state": 42},
        "mean": [0.0] * len(FEATURE_NAMES),
        "scale": [1.0] * len(FEATURE_NAMES),
        "coefficients": [0.1] * len(FEATURE_NAMES),
        "intercept": 0.0,
    }
    model["model_id"] = digest(encoded(model))
    run = root / "runs" / ("0" * 32)
    run.mkdir(parents=True)
    files = {"model": models.save_model(run / "model.json", model)}
    report = {
        "model_id": model["model_id"],
        "evaluation": {"final": {"TEST_ONLY": True}},
        "target_description": "TEST_ONLY five daytime movements",
    }
    dataset = {
        "id": model["dataset_id"],
        "securities": 2,
        "end": (now.date() - timedelta(days=2)).isoformat(),
        "source": "TEST_ONLY",
        "exclusions": [],
    }
    for name, value in (("evaluation", report), ("dataset", dataset), ("scores", [])):
        payload = encoded(value)
        write_new(run / (name + ".json"), payload)
        files[name] = digest(payload)
    receipt = encoded(
        {"family": FAMILY, "run_id": run.name, "files": files, "inference_at": now.isoformat()}
    )
    write_new(run / "receipt.json", receipt)
    write_new(
        root / "latest.json", encoded({"run_id": run.name, "receipt_sha256": digest(receipt)})
    )
    current = {
        "dataset_id": "TEST_ONLY_NEW_INPUT_DATASET",
        "rows": [{"session": yesterday, "source": "TEST_ONLY"}],
        "sessions": [yesterday],
        "source_observed_at": (now - timedelta(seconds=1)).isoformat(),
        "manifest": {"exclusions": [], "api_calls": 0},
    }
    write_new(root / "TEST_ONLY_source.json", encoded(current))
    return model, run, current


def test_score_only_does_not_train_or_change_frozen_experiment_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY_experiment"
    model, previous, current = initialized(root)
    original = {name: (previous / name).read_bytes() for name in ("model.json", "evaluation.json")}
    source_bytes = (root / "TEST_ONLY_source.json").read_bytes()
    calls: list[tuple[str, str]] = []

    def forbid_train(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Score-only update must never fit or reevaluate a model")

    def saved_score(
        saved: dict[str, Any], rows: Any, sessions: Any, at: datetime, observed: datetime
    ) -> list[dict[str, Any]]:
        assert rows == current["rows"] and sessions == current["sessions"]
        assert observed <= at
        calls.append((saved["model_id"], saved["dataset_id"]))
        return [
            {
                "key": "NSE_EQ|INE" + str(index).zfill(9),
                "symbol": "TEST_ONLY_" + str(index),
                "session": sessions[-1],
                "score": 0.5 + index / 10,
                "vector": [0.0] * len(FEATURE_NAMES),
                "feature_names": list(FEATURE_NAMES),
                "feature_version": FEATURE_VERSION,
                "model_id": saved["model_id"],
                "dataset_id": saved["dataset_id"],
                "inference_at": at.isoformat(),
                "source": "TEST_ONLY",
                "observed_price": "100",
                "risk": {
                    "open_close_daily_sd_20": 0.01,
                    "open_close_compounded_drawdown_20": -0.02,
                    "volume": 1000,
                },
            }
            for index in range(2)
        ]

    monkeypatch.setattr(models, "train", forbid_train)
    monkeypatch.setattr(inference, "guard", lambda: {"classification": "TEST_ONLY_CLOCK"})
    monkeypatch.setattr(
        inference,
        "current_dataset",
        lambda owned: json.loads((owned / "TEST_ONLY_source.json").read_bytes()),
    )
    monkeypatch.setattr(inference, "score", saved_score)
    result = inference.infer(root)
    latest = root / "runs" / result["run_id"]
    assert calls == [(model["model_id"], model["dataset_id"])]
    assert result["scored"] == 2 and result["provider_gets"] == 0
    assert result["model_refit"] is False and result["holdout_reevaluated"] is False
    for name, payload in original.items():
        assert (previous / name).read_bytes() == payload
        assert (latest / name).read_bytes() == payload
    assert (root / "TEST_ONLY_source.json").read_bytes() == source_bytes
    info = json.loads((latest / "dataset.json").read_bytes())
    assert info["training_dataset_id"] == model["dataset_id"]
    assert info["id"] == current["dataset_id"] != model["dataset_id"]
    scores = json.loads((latest / "scores.json").read_bytes())
    assert {row["dataset_id"] for row in scores} == {current["dataset_id"]}
    assert {row["training_dataset_id"] for row in scores} == {model["dataset_id"]}
    previous_pointer = (root / "latest.json").read_bytes()
    replayed = inference.infer(root)
    assert replayed["state"] == "NO_NEW_COHORT_SESSION_SAVED_RESEARCH_PRESERVED"
    assert replayed["forecasts"]["inserted"] == 0
    assert (root / "latest.json").read_bytes() == previous_pointer
    assert len(calls) == 1


def test_score_only_rejects_future_retrieval_without_changing_latest_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "TEST_ONLY_experiment"
    _, _, current = initialized(root)
    previous_pointer = (root / "latest.json").read_bytes()
    future = copy.deepcopy(current)
    future["source_observed_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    monkeypatch.setattr(inference, "guard", lambda: {"classification": "TEST_ONLY_CLOCK"})
    monkeypatch.setattr(inference, "current_dataset", lambda owned: future)
    with pytest.raises(ValueError, match="INPUT_AND_MODEL_MUST_PRECEDE_DECISION"):
        inference.infer(root)
    assert (root / "latest.json").read_bytes() == previous_pointer
