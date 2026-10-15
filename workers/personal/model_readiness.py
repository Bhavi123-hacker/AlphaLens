"""Read-only feature/serialization evidence, never model loading or acceptance."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.daily.features import definitions


def inspect(report: Path) -> dict[str, Any]:
    now = datetime.now(UTC)
    registry = definitions(now.date(), now)
    columns = [d.feature_name for d in registry]
    candidates = []
    if report.is_file() and report.stat().st_size <= 250000:
        document = json.loads(report.read_bytes())
        for candidate in document.get("candidates", [])[:4]:
            candidates.append(
                {
                    "horizon": candidate["horizon"],
                    "family": candidate["family"],
                    "model_run_id": candidate["model_run_id"],
                    "feature_order_matches_registry": candidate["feature_columns"] == columns,
                    "artifact_checksum_evidence": candidate["artifact_checksum"],
                    "independent_acceptance": "NOT_PASSED",
                }
            )
    return {
        "version": "p33.model-readiness.v1",
        "ordered_feature_columns": columns,
        "feature_count": len(columns),
        "required_feature_count": 38,
        "candidates": candidates,
        "current_eligible_feature_count": 0,
        "peer_feature": "momentum_percentile_20",
        "peer_requirement": (
            "COMPLETE_CONTEMPORANEOUS_VERIFIED_ELIGIBLE_RETURN20_UNIVERSE_WITH_REVISION_LINEAGE"
        ),
        "blocking_requirements": [
            "SOURCE_RETAINED_ML_USE_CLEARANCE",
            "OFFICIAL_DECISION_TIME_CALENDAR",
            "ALL_38_NUMERICAL_AND_TEMPORAL_FEATURES",
            "COMPLETE_CURRENT_PEER_UNIVERSE",
            "COMPATIBLE_ACTION_AND_PRICE_BASIS",
            "DATED_CURRENT_RISK_AND_UNIVERSE",
            "INDEPENDENT_PROSPECTIVE_ACCEPTANCE",
            "UNCHANGED_P11_P14_PUBLICATION_GATES",
        ],
        "artifact_loading": "CHECKSUM_PINNED_TYPES_AND_EXISTING_SCOPED_REVIEW_ONLY",
        "protocol": "p33.prospective.v1_NOT_INDEPENDENTLY_APPROVED",
        "prospective_registration_numeric_minima": (
            "INDEPENDENT_POWER_ANALYSIS_REQUIRED_BEFORE_OUTCOMES"
        ),
        "models_loaded": False,
        "predictions_generated": 0,
        "current_rankings": "UNAVAILABLE",
    }
