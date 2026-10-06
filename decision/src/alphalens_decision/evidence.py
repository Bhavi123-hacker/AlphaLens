"""Project verified P9 outputs; future fold metrics remain unavailable until mature."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_decision.models import ModelDiagnostic, ModelEvidence, PredictionEvidence
from alphalens_evaluation.contracts import digest
from alphalens_evaluation.storage import OOSDataset, load


def project(oos: OOSDataset, reports: list[dict[str, Any]] | None = None) -> ModelEvidence:
    definition = oos.verify()
    predictions = tuple(
        PredictionEvidence(
            origin="P9_FOLD_TEST",
            evaluation_id=row.evaluation_id,
            model_run_id=row.model_run_id,
            family=row.model_family,
            task=row.task,
            horizon=row.horizon,
            security_id=row.security_id,
            session_date=row.session_date,
            decision_time=row.decision_time,
            available_at=row.prediction_available_at,
            training_cutoff=datetime.fromisoformat(
                oos.manifest["fold_models"][row.model_run_id]["effective_training_cutoff"]
            ),
            feature_set_id=row.feature_set_id,
            canonical_dataset_id=row.feature_canonical_dataset_id,
            universe_snapshot_id=row.universe_snapshot_id,
            prediction=row.prediction,
            probability=row.probability,
            classification=row.classification,
        )
        for row in oos.predictions
    )
    diagnostics = []
    for report in reports or []:
        if report["status"] != "EVALUATED":
            continue
        model = oos.manifest["fold_models"].get(report["model_run_id"])
        if (
            not model
            or model["fold"]["fold_id"] != report["fold_id"]
            or model["model_family"] != report["model_family"]
            or report["test_period"][1] != model["fold"]["test_end"]
        ):
            raise DataContractError("MODEL_DIAGNOSTIC_REFERENCE_MISMATCH")
        scored = [
            p
            for p in oos.predictions
            if p.model_run_id == report["model_run_id"] and p.scoring_status == "SCORABLE"
        ]
        times = [p.target_available_at for p in scored if p.target_available_at is not None]
        if not scored or len(times) != len(scored):
            continue
        primary = "brier_score" if definition.task == "classification" else "mae"
        naive = "training_positive_rate" if definition.task == "classification" else "training_mean"
        metric = report["metrics"].get(primary)
        naive_metric = report["naive_metrics"][naive].get(primary)
        diagnostics.append(
            ModelDiagnostic(
                origin="P9_FOLD_TEST",
                evaluation_id=oos.manifest["evaluation_id"],
                model_run_id=report["model_run_id"],
                family=report["model_family"],
                task=definition.task,
                horizon=definition.horizon,
                fold_id=report["fold_id"],
                period_end=report["test_period"][1],
                available_at=max(times),
                report_checksum=digest(report),
                sample_count=len(scored),
                primary_metric=metric,
                naive_improvement=naive_metric - metric
                if naive_metric is not None and metric is not None
                else None,
                brier_score=report["metrics"].get("brier_score"),
                calibration_available=report["metrics"].get("calibration", {}).get("status")
                == "DESCRIPTIVE_ONLY_NO_CALIBRATOR_FIT",
                classification=definition.data_classification,
            )
        )
    return ModelEvidence(
        classification=definition.data_classification,
        predictions=predictions,
        diagnostics=tuple(diagnostics),
    )


def load_models(paths: list[Path]) -> ModelEvidence | None:
    bundles = []
    for path in paths:
        oos = load(path)
        reports = json.loads((path / "fold-metrics.json").read_bytes())["folds"]
        bundles.append(project(oos, reports))
    if not bundles:
        return None
    return ModelEvidence(
        classification=bundles[0].classification,
        predictions=tuple(p for bundle in bundles for p in bundle.predictions),
        diagnostics=tuple(d for bundle in bundles for d in bundle.diagnostics),
    )
