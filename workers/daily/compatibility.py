"""Read-only frozen candidate audit, no estimator loading or new research evaluation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import skops.io as sio

from alphalens_data.daily.providers import BASELINE
from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from alphalens_training.artifacts import REVIEWED_TYPES

from .artifact_reviews import scoped_review
from .inference import verify_model

REPORT_SHA256 = "9243ec7c9a5a08808c0ffbb6dfa04dd20b5732707659cb2836c896b204876e42"


def audit(root: Path) -> dict[str, Any]:
    payload = (root / "2026-results.json").read_bytes()
    if checksum(payload) != REPORT_SHA256:
        raise DataContractError("FROZEN_MODEL_REPORT_CHECKSUM_MISMATCH")
    reports = json.loads(payload)["reports"]
    if sorted(r["horizon"] for r in reports) != [1, 5, 10, 20]:
        raise DataContractError("FROZEN_CANDIDATE_SCOPE_INVALID")
    output = []
    for report in reports:
        path = verify_model(root / "p9", report, BASELINE)
        # skops schema/type inspection does not deserialize/execute the estimator.
        unknown = set(sio.get_untrusted_types(file=path))
        scoped = scoped_review(report["model_sha256"], unknown, REVIEWED_TYPES)
        unsupported = sorted(unknown - REVIEWED_TYPES - scoped)
        identity = report["model_identity"]
        output.append(
            dict(
                horizon=report["horizon"],
                family=report["model_family"],
                model_run_id=report["model_run_id"],
                model_sha256=report["model_sha256"],
                artifact_checksum="VERIFIED",
                feature_columns=identity["feature_columns"],
                training_cutoff=identity["configuration"]["training_cutoff"],
                preprocessing=identity["preprocessing"],
                type_review="BLOCKED_UNREVIEWED_TYPES"
                if unsupported
                else "EXACT_ARTIFACT_SCOPED_REVIEW"
                if scoped
                else "REVIEWED_TYPES_ONLY",
                artifact_scoped_types=sorted(scoped),
                global_type_allowlist_changed=False,
                unsupported_types=unsupported,
                inference="UNAVAILABLE",
                reasons=[
                    "NO_PERMITTED_NEW_SESSION",
                    "NEW_FEATURE_UNIVERSE_ACTION_EVIDENCE_NOT_VERIFIED",
                    "INDEPENDENT_MODEL_ACCEPTANCE_NOT_PASSED",
                ]
                + (["UNREVIEWED_ARTIFACT_TYPES"] if unsupported else []),
            )
        )
    return dict(
        version="p19.compatibility-audit.v1",
        verified_at=datetime.now(UTC).isoformat(),
        report_sha256=REPORT_SHA256,
        candidates=output,
        classification="RESEARCH_ONLY",
        estimator_deserialized=False,
        predictions_generated=0,
        rankings="UNAVAILABLE_UNCHANGED_POLICY",
    )
