"""Gated persisted preprocessing/inference only; never fitting or holdout reevaluation."""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import numpy as np
import skops.io as sio
from threadpoolctl import threadpool_limits

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_training.artifacts import REVIEWED_TYPES

CANDIDATES = {
    1: "hist_gradient_boosting",
    5: "hist_gradient_boosting",
    10: "xgboost",
    20: "hist_gradient_boosting",
}


class Fitted(Protocol):
    def predict(self, values: Any) -> Any: ...
    def predict_proba(self, values: Any) -> Any: ...


def verify_model(root: Path, report: dict[str, Any], baseline: str) -> Path:
    identity = report["model_identity"]
    run_id = checksum(stable_json(identity))
    horizon = report["horizon"]
    if (
        run_id != report["model_run_id"]
        or report["dataset_id"] != baseline
        or report["model_family"] != CANDIDATES.get(horizon)
        or report["task"] != "classification"
        or report.get("phase", report.get("fold_id")) != "2026"
        or report["usage_classification"] != "RESEARCH_ONLY"
    ):
        raise DataContractError("MODEL_CANDIDATE_OR_DATASET_MISMATCH")
    if (
        identity["family"] != report["model_family"]
        or identity["horizon"] != horizon
        or identity["dataset_id"] != baseline
        or not identity.get("feature_columns")
        or identity.get("preprocessing") != "FRESH_TRAIN_ONLY_MEDIAN_LINEAR_SCALER_CONSTANT_REMOVAL"
        or not identity.get("configuration", {}).get("training_cutoff")
    ):
        raise DataContractError("MODEL_PREPROCESSING_OR_LINEAGE_MISMATCH")
    if (
        report.get("fold") != identity.get("fold")
        or identity.get("fold", {}).get("fold_id") != "2026"
    ):
        raise DataContractError("MODEL_FOLD_LINEAGE_MISMATCH")
    if report["model_file"] != f"models/{run_id}.skops":
        raise DataContractError("MODEL_PATH_INVALID")
    path = (root / str(report["model_file"])).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or checksum(path.read_bytes()) != report["model_sha256"]
    ):
        raise DataContractError("MODEL_ARTIFACT_CHECKSUM_MISMATCH")
    return path


def input_compatibility(
    expected: tuple[str, ...], features: dict[str, Any], *, allow_degraded: bool = False
) -> dict[str, Any]:
    """Project exact stored model order; missing/unsupported features never get imputed here."""
    reasons: list[str] = []
    values: list[float] = []
    excluded: dict[str, str] = {}
    if (
        not expected
        or len(set(expected)) != len(expected)
        or any(name.startswith(("label", "target", "metadata")) for name in expected)
    ):
        reasons.append("MODEL_FEATURE_SCHEMA_INVALID")
    for name in expected:
        item = features.get(name, {})
        value = item.get("value")
        state = item.get("state", "UNAVAILABLE")
        if state not in ({"AVAILABLE", "DEGRADED"} if allow_degraded else {"AVAILABLE"}):
            excluded[name] = "FEATURE_STATE_NOT_ELIGIBLE"
        elif (
            not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value)
        ):
            excluded[name] = "FEATURE_VALUE_NOT_FINITE"
        else:
            values.append(float(value))
    if excluded:
        reasons.append("REQUIRED_FEATURE_EVIDENCE_INCOMPLETE")
    return dict(
        compatible=not reasons,
        columns=list(expected),
        values=values if not reasons else None,
        excluded=excluded,
        reasons=reasons,
        inference_authorized=False,
    )


def predict(
    fitted: Fitted,
    values: list[float],
    columns: tuple[str, ...],
    expected_columns: tuple[str, ...],
    *,
    session: date,
    decision_time: datetime,
    receipt_time: datetime,
    training_cutoff: datetime,
    archive_end: date,
    authorized_experimental: bool,
) -> dict[str, Any]:
    if not authorized_experimental:
        raise DataContractError("EXPERIMENTAL_INFERENCE_NOT_ACTIVATED")
    if session <= max(archive_end, date(2026, 10, 6)):
        raise DataContractError("FROZEN_EVALUATION_SESSION_INFERENCE_FORBIDDEN")
    if any(
        t.tzinfo is None or t.utcoffset() is None
        for t in (decision_time, receipt_time, training_cutoff)
    ):
        raise DataContractError("AWARE_INFERENCE_CLOCKS_REQUIRED")
    if (
        decision_time < receipt_time
        or training_cutoff >= decision_time
        or decision_time.astimezone(ZoneInfo("Asia/Kolkata")).date() <= session
    ):
        raise DataContractError("INFERENCE_CHRONOLOGY_INVALID")
    if (
        columns != expected_columns
        or len(values) != len(columns)
        or any(n.startswith(("label", "target", "metadata")) for n in columns)
        or not np.isfinite(values).all()
    ):
        raise DataContractError("FEATURE_SCHEMA_OR_AVAILABILITY_INVALID")
    # Calls the already fitted Pipeline, including its original imputer/scaler.
    # No fit, fit_transform, or new preprocessing statistics can occur here.
    with threadpool_limits(limits=1):
        x = np.array([values], dtype="float64")
        result = float(np.asarray(fitted.predict(x)).ravel()[0])
        probability = float(np.asarray(fitted.predict_proba(x))[0, 1])
    if not np.isfinite(result) or not 0 <= probability <= 1:
        raise DataContractError("MODEL_OUTPUT_INVALID")
    return dict(
        prediction=result,
        model_probability=probability,
        interpretation="EXPERIMENTAL_RESEARCH_FORECAST_NOT_SIGNAL",
        research_status="REAL_RESEARCH_INSUFFICIENT_EVIDENCE",
        usage_classification="RESEARCH_ONLY",
        disclaimer="MODEL ESTIMATE — NOT GUARANTEED",
    )


def load(path: Path, expected_hash: str, *, authorized_experimental: bool) -> Fitted:
    if not authorized_experimental:
        raise DataContractError("EXPERIMENTAL_INFERENCE_NOT_ACTIVATED")
    payload = path.read_bytes()
    if checksum(payload) != expected_hash:
        raise DataContractError("MODEL_ARTIFACT_CHECKSUM_MISMATCH")
    unknown = set(sio.get_untrusted_types(data=payload))
    if not unknown <= REVIEWED_TYPES:
        raise DataContractError("UNREVIEWED_ARTIFACT_TYPES")
    fitted: Fitted = sio.loads(payload, trusted=sorted(unknown))
    return fitted


def infer_verified(
    root: Path,
    report: dict[str, Any],
    baseline: str,
    values: list[float],
    columns: tuple[str, ...],
    *,
    session: date,
    decision_time: datetime,
    receipt_time: datetime,
    authorized_experimental: bool = False,
) -> dict[str, Any]:
    if not authorized_experimental:
        raise DataContractError("EXPERIMENTAL_INFERENCE_NOT_ACTIVATED")
    if session <= date(2026, 10, 6):
        raise DataContractError("FROZEN_EVALUATION_SESSION_INFERENCE_FORBIDDEN")
    path = verify_model(root, report, baseline)
    identity = report["model_identity"]
    fitted = load(path, report["model_sha256"], authorized_experimental=True)
    return predict(
        fitted,
        values,
        columns,
        tuple(identity["feature_columns"]),
        session=session,
        decision_time=decision_time,
        receipt_time=receipt_time,
        training_cutoff=datetime.fromisoformat(identity["configuration"]["training_cutoff"]),
        archive_end=date(2026, 10, 6),
        authorized_experimental=True,
    )
