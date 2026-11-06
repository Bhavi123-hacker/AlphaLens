"""Score-only updates using the saved experiment; never refit or reevaluate its holdout."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from workers.providers.daily_clock import guard

from .acquire import FAMILY, digest, encoded, private_path, write_new
from .models import load_model, save_model, score
from .prospective import append_forecasts
from .refresh import current_dataset
from .workspace import read_workspace


def infer(root: Path) -> dict[str, Any]:
    # Fully validate the previous saved run before opening any artifact for loading.
    previous = read_workspace(root)
    if previous["model"] is None:
        raise ValueError("TRAINED_EXPERIMENTAL_MODEL_REQUIRED")
    clock = guard()
    pointer = json.loads(private_path(root, "latest.json").read_bytes())
    previous_run = private_path(root, "runs", pointer["run_id"])
    receipt = json.loads((previous_run / "receipt.json").read_bytes())
    model = load_model(previous_run / "model.json", receipt["files"]["model"])
    evaluation = json.loads((previous_run / "evaluation.json").read_bytes())
    dataset = current_dataset(root)
    if dataset["sessions"][-1] <= previous["dataset"]["end"]:
        return {
            "run_id": pointer["run_id"],
            "model_id": model["model_id"],
            "dataset_id": previous["dataset"]["id"],
            "scored": len(previous["candidates"]),
            "model_refit": False,
            "holdout_reevaluated": False,
            "provider_gets": 0,
            "state": "NO_NEW_COHORT_SESSION_SAVED_RESEARCH_PRESERVED",
            "forecasts": {"inserted": 0, "replayed": len(previous["candidates"])},
        }
    observed = datetime.fromisoformat(dataset["source_observed_at"])
    at = datetime.now(UTC)
    completed = dataset.get("completed_session")
    if completed is not None and completed["session"] == dataset["sessions"][-1]:
        scores = score(
            model,
            dataset["rows"],
            dataset["sessions"],
            at,
            observed,
            completed_session_end=datetime.fromisoformat(completed["end"]),
        )
    else:
        scores = score(model, dataset["rows"], dataset["sessions"], at, observed)
    for row in scores:
        row["training_dataset_id"] = model["dataset_id"]
        row["dataset_id"] = dataset["dataset_id"]
    forecasts = append_forecasts(root, model["model_id"], dataset["dataset_id"], scores, observed)
    run_id = uuid4().hex
    run = private_path(root, "runs", run_id)
    run.mkdir()
    files = {"model": save_model(run / "model.json", model)}
    info = {
        **previous["dataset"],
        "id": dataset["dataset_id"],
        "training_dataset_id": model["dataset_id"],
        "observations": len(dataset["rows"]),
        "start": dataset["sessions"][0],
        "end": dataset["sessions"][-1],
        "observed_session_dates": len(dataset["sessions"]),
        "source_observed_at": dataset["source_observed_at"],
        "exclusions": dataset["manifest"]["exclusions"],
        "api_calls": dataset["manifest"]["api_calls"],
        "correction_coverage": dataset["manifest"].get(
            "correction_coverage", "ORIGINAL_RETRIEVAL_ONLY"
        ),
    }
    for name, value in (("evaluation", evaluation), ("scores", scores), ("dataset", info)):
        body = encoded(value)
        write_new(run / (name + ".json"), body)
        files[name] = digest(body)
    receipt_body = encoded(
        {
            "family": FAMILY,
            "run_id": run_id,
            "files": files,
            "inference_at": at.isoformat(),
            "forecasts": forecasts,
            "independent_clock": clock,
            "model_refit": False,
            "holdout_reevaluated": False,
        }
    )
    write_new(run / "receipt.json", receipt_body)
    temporary = root / ("latest-" + uuid4().hex + ".json")
    write_new(temporary, encoded({"run_id": run_id, "receipt_sha256": digest(receipt_body)}))
    os.replace(temporary, root / "latest.json")
    return {
        "run_id": run_id,
        "model_id": model["model_id"],
        "dataset_id": dataset["dataset_id"],
        "scored": len(scores),
        "forecasts": forecasts,
        "model_refit": False,
        "holdout_reevaluated": False,
        "provider_gets": 0,
    }
