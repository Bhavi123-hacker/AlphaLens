"""Verified private experimental workspace; no acquisition or accepted-service writes."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_api.auth.permissions import verify

from .acquire import FAMILY, digest, encoded, private_path

SCHEMA = "alphalens.experimental_nse.workspace.v1"
LABEL = "EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED"


def empty() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "family": FAMILY,
        "status": "EXPERIMENTAL_UNVALIDATED_RESEARCH",
        "label": LABEL,
        "available": False,
        "model": None,
        "dataset": None,
        "evaluation": None,
        "candidates": [],
        "exclusions": ["NO_VERIFIED_EXPERIMENTAL_RUN"],
        "prospective": {
            "forecasts": 0,
            "outcomes": 0,
            "metrics": None,
            "status": "NO_RECORDED_FORECASTS",
        },
        "accepted_current_rankings": 0,
    }


def read_workspace(root: Path | None) -> dict[str, Any]:
    if root is None:
        return empty()
    pointer_path = private_path(root, "latest.json")
    if not pointer_path.exists():
        return empty()
    verify(root)
    pointer = json.loads(pointer_path.read_bytes())
    if set(pointer) != {"run_id", "receipt_sha256"}:
        raise ValueError("EXPERIMENTAL_RUN_POINTER_REJECTED")
    run_id = pointer["run_id"]
    if (
        not isinstance(run_id, str)
        or len(run_id) != 32
        or any(c not in "0123456789abcdef" for c in run_id)
    ):
        raise ValueError("EXPERIMENTAL_RUN_PATH_REJECTED")
    run = private_path(root, "runs", run_id)
    receipt_bytes = private_path(root, "runs", run_id, "receipt.json").read_bytes()
    if digest(receipt_bytes) != pointer["receipt_sha256"]:
        raise ValueError("EXPERIMENTAL_RECEIPT_CHECKSUM_REJECTED")
    receipt = json.loads(receipt_bytes)
    if receipt["family"] != FAMILY or receipt["run_id"] != run_id:
        raise ValueError("EXPERIMENTAL_FAMILY_REJECTED")
    values = {}
    for name in ("model", "evaluation", "scores", "dataset"):
        body = private_path(root, "runs", run_id, name + ".json").read_bytes()
        if digest(body) != receipt["files"][name]:
            raise ValueError("EXPERIMENTAL_EVIDENCE_CHECKSUM_REJECTED")
        values[name] = json.loads(body)
    # Constrained schema contains coefficients only, never executable serialized objects.
    from .models import load_model
    from .prospective import summary

    model = load_model(run / "model.json", receipt["files"]["model"])
    evaluation, scores, dataset = values["evaluation"], values["scores"], values["dataset"]
    if (
        model["dataset_id"] != dataset.get("training_dataset_id", dataset["id"])
        or evaluation["model_id"] != model["model_id"]
    ):
        raise ValueError("EXPERIMENTAL_MODEL_DATASET_LINEAGE_REJECTED")
    candidates = []
    pending_path = private_path(root, "refresh-pending.json")
    pending = json.loads(pending_path.read_bytes()) if pending_path.exists() else None
    if pending is not None:
        dataset["latest_query"] = {
            "through": pending["end"],
            "exclusions": pending["exclusions"],
            "state": "NO_NEW_ELIGIBLE_SESSION_OR_INCOMPLETE_PUBLICATION",
            "market_requests_from_page": 0,
        }
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    for row in scores:
        if row["model_id"] != model["model_id"] or row["dataset_id"] != dataset["id"]:
            raise ValueError("EXPERIMENTAL_SCORE_LINEAGE_REJECTED")
        risk = row["risk"]
        age = (today - date.fromisoformat(row["session"])).days
        if age < 0:
            raise ValueError("EXPERIMENTAL_FUTURE_OBSERVATION_REJECTED")
        candidates.append(
            {
                **row,
                "observation_date": row["session"],
                "observation_age_days": age,
                "data_freshness": (
                    "STALE"
                    if age > 7
                    else "DATED_PRIOR_EOD_OBSERVATION"
                    if age
                    else "SAME_DAY_EOD_OBSERVATION"
                ),
                "volatility_percent": risk["open_close_daily_sd_20"] * 100,
                "drawdown_percent": risk["open_close_compounded_drawdown_20"] * 100,
                "preference_metrics": {
                    "gross_price": float(row["observed_price"]),
                    "volume": risk["volume"],
                },
                "preference_matches": [],
                "exclusions": [],
                "held": False,
                "forecast_timing": (
                    "Recorded at actual inference time from prior EOD; the first target session "
                    "may already have begun. This is not a fully prospective forecast."
                ),
            }
        )
    return {
        "schema": SCHEMA,
        "family": FAMILY,
        "status": "EXPERIMENTAL_UNVALIDATED_RESEARCH",
        "label": LABEL,
        "available": bool(candidates),
        "model": {
            "id": model["model_id"],
            "algorithm": model["algorithm"],
            "feature_version": model["feature_version"],
            "features": model["feature_names"],
            "horizon": "5 observed-session daytime movements (not a holding return)",
            "target": evaluation["target_description"],
            "trained_at": model["trained_at"],
            "inference_at": receipt["inference_at"],
            "current_inference_scope": "PRIOR_EOD_RESEARCH_TARGET_MAY_HAVE_PARTLY_ELAPSED",
            "score_calibration": "UNCALIBRATED_NOT_EMPIRICAL_CONFIDENCE",
        },
        "dataset": dataset,
        "evaluation": {**evaluation, **evaluation["evaluation"]},
        "candidates": candidates,
        "exclusions": dataset["exclusions"],
        "prospective": summary(root),
        "accepted_current_rankings": 0,
        "read_at": datetime.now(UTC).isoformat(),
        "receipt_sha256": digest(encoded(receipt)),
    }
