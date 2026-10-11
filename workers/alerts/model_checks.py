"""Read and checksum frozen metadata only. No estimator loading or inference."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_data.daily.providers import BASELINE
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from workers.daily.features import definitions
from workers.daily.inference import CANDIDATES, verify_model

from .contracts import Event
from .store import AlertError, AlertStore


def inspect_models(alerts: AlertStore, root: Path) -> dict[str, Any]:
    inventory = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs/backtesting/real-research-economic-audit.json"
        ).read_bytes()
    )["artifact_inventory"]
    expected = {r["path"].replace("\\", "/"): r["sha256"] for r in inventory}
    name = "2026-results.json"
    payload = (root / name).read_bytes()
    if expected.get(name) != checksum(payload):
        raise AlertError("FROZEN_MODEL_REPORT_CHECKSUM_INVALID")
    report = json.loads(payload)
    rows = [
        r
        for r in report["reports"]
        if r["task"] == "classification" and CANDIDATES.get(r["horizon"]) == r["model_family"]
    ]
    if sorted(r["horizon"] for r in rows) != [1, 5, 10, 20]:
        raise AlertError("FIXED_CANDIDATE_METADATA_INCOMPLETE")
    result = []
    for original in rows:
        row = dict(
            original, phase="2026"
        )  # Scope comes from the checksum-pinned report, not metrics.
        code, reason = "INFERENCE_BLOCKED", "SOURCE_AND_DAILY_FEATURE_ACCEPTANCE_NOT_ESTABLISHED"
        try:
            verify_model(root / "p9", row, BASELINE)
            status = "FROZEN_ARTIFACT_METADATA_VERIFIED"
        except FileNotFoundError:
            code, reason, status = "MODEL_MISSING", "TRUSTED_MODEL_ARTIFACT_MISSING", "UNAVAILABLE"
        except (DataContractError, OSError, ValueError, KeyError):
            code, reason, status = (
                "INTEGRITY_FAILURE",
                "TRUSTED_MODEL_METADATA_OR_CHECKSUM_INVALID",
                "UNAVAILABLE",
            )
        schema_match = tuple(row["model_identity"]["feature_columns"]) == tuple(
            d.feature_name for d in definitions(datetime.now(UTC).date(), datetime.now(UTC))
        )
        if status == "FROZEN_ARTIFACT_METADATA_VERIFIED" and not schema_match:
            code, reason = "FEATURE_SCHEMA", "STORED_FEATURE_ORDER_DIFFERS_FROM_P6_REGISTRY"
        evidence = dict(
            model_run_id=row["model_run_id"],
            model_sha256=row["model_sha256"],
            feature_columns=row["model_identity"]["feature_columns"],
            training_cutoff=row["model_identity"]["configuration"]["training_cutoff"],
            preprocessing=row["model_identity"]["preprocessing"],
            feature_order_matches_p6=schema_match,
            horizon=row["horizon"],
            status=status,
            reason=reason,
        )
        identity = checksum(stable_json(evidence))
        event = Event(
            code=code,
            component="P19",
            evidence_ref=f"model-check:{row['model_run_id']}",
            evidence_sha256=checksum(payload),
            event_at=datetime.now(UTC),
            time_basis="DETECTOR_OBSERVATION_TIME",
            classification="RESEARCH_ONLY",
            final_vintage="FINAL_VINTAGE_RESEARCH_ASSUMPTION",
            mode="DAILY",
            reasons=(reason,),
            group="P19:MODEL_ACCEPTANCE",
            identity=identity,
        )
        published = alerts.publish(f"P19:model:{row['model_run_id']}", identity, [event])
        result.append(
            dict(
                horizon=row["horizon"],
                family=row["model_family"],
                model_run_id=row["model_run_id"],
                training_cutoff=evidence["training_cutoff"],
                feature_count=len(evidence["feature_columns"]),
                feature_order_matches_p6=schema_match,
                status=status,
                inference="UNAVAILABLE",
                reason=reason,
                alerts_published=published,
            )
        )
    return {
        "models": result,
        "inference": "UNAVAILABLE",
        "estimator_loaded": False,
        "holdout_evaluated": False,
    }
