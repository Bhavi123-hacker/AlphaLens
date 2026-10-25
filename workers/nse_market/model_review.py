"""Read saved candidate verdicts without fitting, evaluating or promoting a model."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from workers.experimental_nse_v2 import acceptance

VERDICTS = (
    "ACCEPTED_FOR_PRIVATE_RESEARCH",
    "EXPERIMENTAL_INSUFFICIENT_EVIDENCE",
    "REJECTED",
    "BLOCKED_DATA_QUALITY",
)


def evidence(path: Path, *, relative_to: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pin bytes, verify an existing immutable sidecar, and never deserialize models."""
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("MODEL_REVIEW_SYMLINK_FORBIDDEN")
    raw = path.read_bytes()
    actual = sha256(raw).hexdigest()
    sidecars = (path.with_suffix(path.suffix + ".sha256"), path.with_suffix(".sha256"))
    checked = []
    for sidecar in dict.fromkeys(sidecars):
        if sidecar.exists():
            if sidecar.is_symlink() or sidecar.read_text(encoding="utf-8").strip() != actual:
                raise ValueError("MODEL_REVIEW_EVIDENCE_CHECKSUM_MISMATCH")
            checked.append(str(sidecar.relative_to(relative_to)))
    body = json.loads(raw)
    if not isinstance(body, dict):
        raise ValueError("MODEL_REVIEW_OBJECT_REQUIRED")
    return body, {
        "path": str(path.relative_to(relative_to)),
        "sha256": actual,
        "verified_sidecars": checked,
    }


def candidate_verdict(
    *, integrity_valid: bool, native_verdict: str | None, limitations: list[str]
) -> dict[str, Any]:
    """No local metric/boolean or this agent's audit substitutes for external review."""
    return {
        "verdict": "EXPERIMENTAL_INSUFFICIENT_EVIDENCE"
        if integrity_valid
        else "BLOCKED_DATA_QUALITY",
        "native_saved_verdict": native_verdict,
        "reasons": limitations
        if integrity_valid
        else ["MISSING_OR_UNVERIFIABLE_SAVED_EVIDENCE", *limitations],
        "independent_review_supplied_by_this_audit": False,
        "model_promoted_by_this_audit": False,
        "accepted_publication": False,
    }


def registry(repository: Path, *, private_root: Path | None = None) -> dict[str, Any]:
    private = private_root if private_root is not None else repository / ".local-data"
    manifest, manifest_ref = evidence(
        repository / "docs/completion/model-readiness-manifest.json", relative_to=repository
    )
    original, original_ref = evidence(
        repository / "docs/ml/real-model-comparison.json", relative_to=repository
    )
    original_plan = repository / "docs/ml/real-research-evaluation-plan.json"
    original_standard = repository / "docs/ml/p33-prospective-acceptance-protocol.md"
    context_protocol = repository / "docs/development/ml-v2-registered-protocol.md"
    companion_protocol = repository / "docs/development/ml-v2-price-only-registered-protocol.md"
    sequence_protocol = repository / "docs/development/ml-sequence-v1-registered-protocol.md"
    v1_protocol = repository / "docs/development/experimental-nse-v1-predeclared-study.md"
    protocols = {
        str(path.relative_to(repository)): sha256(path.read_bytes()).hexdigest()
        for path in (
            original_plan,
            original_standard,
            context_protocol,
            companion_protocol,
            sequence_protocol,
            v1_protocol,
        )
    }
    rows: list[dict[str, Any]] = []
    selected = {
        (row.get("algorithm"), row.get("horizon_sessions")): row
        for row in manifest["entries"]
        if row["family"] == "FROZEN_TEJHQ_RESEARCH"
    }
    for saved in original["models"]:
        family, task, horizon = saved["model_family"], saved["task"], saved["horizon"]
        serving = selected.get((family, horizon), {}) if task == "classification" else {}
        rows.append(
            {
                "candidate_id": f"original:{task}:{family}:h{horizon}",
                "family": "FROZEN_TEJHQ_RESEARCH",
                "algorithm": family,
                "task": task,
                "horizon_sessions": horizon,
                "model_id": serving.get("model_id"),
                "model_id_scope": "SELECTED_FINAL_ARTIFACT"
                if serving
                else "CANDIDATE_SPEC_MULTIPLE_TEMPORAL_FITS",
                "evidence": original_ref,
                "acceptance_standard": str(original_standard.relative_to(repository)),
                "registered_plan": str(original_plan.relative_to(repository)),
                **candidate_verdict(
                    integrity_valid=True,
                    native_verdict=saved.get("research_status"),
                    limitations=[
                        "FINAL_VINTAGE_NOT_PRODUCTION_PIT",
                        "INDEPENDENT_POWER_AND_SUCCESS_MARGIN_REGISTRATION_REQUIRED",
                        "INDEPENDENT_PROSPECTIVE_REVIEW_ABSENT",
                        "474_ECONOMICALLY_UNRESOLVED_BACKTESTS",
                    ],
                ),
            }
        )
    expected_original = {
        f"original:{task}:{algorithm}:h{horizon}"
        for task, algorithms in (
            (
                "classification",
                (
                    "catboost",
                    "hist_gradient_boosting",
                    "lightgbm",
                    "logistic",
                    "random_forest",
                    "xgboost",
                ),
            ),
            (
                "regression",
                (
                    "catboost",
                    "hist_gradient_boosting",
                    "lightgbm",
                    "random_forest",
                    "ridge",
                    "xgboost",
                ),
            ),
        )
        for algorithm in algorithms
        for horizon in (1, 5, 10, 20)
    }
    if len(rows) != 48 or {row["candidate_id"] for row in rows} != expected_original:
        raise ValueError("COMPLETE_ORIGINAL_48_CANDIDATE_INVENTORY_REQUIRED")
    v1_pointer, _ = evidence(private / "experimental-nse-v1/latest.json", relative_to=repository)
    if not re.fullmatch(r"[0-9a-f]{32}", str(v1_pointer.get("run_id", ""))):
        raise ValueError("MODEL_REVIEW_FROZEN_V1_RUN_ID_REQUIRED")
    v1_path = private / "experimental-nse-v1/runs" / v1_pointer["run_id"] / "evaluation.json"
    v1, v1_ref = evidence(v1_path, relative_to=repository)
    rows.append(
        {
            "candidate_id": "experimental-v1:LOGISTIC:h5-daytime",
            "family": "ALPHALENS_EXPERIMENTAL_NSE_V1",
            "algorithm": "LOGISTIC",
            "task": "classification",
            "horizon_sessions": 5,
            "model_id": v1["model_id"],
            "target_version": v1["target_version"],
            "evidence": v1_ref,
            "acceptance_standard": str(v1_protocol.relative_to(repository)),
            **candidate_verdict(
                integrity_valid=True,
                native_verdict=str(v1.get("independent_model_accepted")),
                limitations=[
                    "DISTINCT_DAYTIME_CHAIN_TARGET_NOT_HOLDING_RETURN",
                    "NO_DECLARED_INDEPENDENT_ACCEPTANCE_REGISTRATION",
                    "HISTORICAL_PIT_ACTION_AND_CALENDAR_LIMITATIONS",
                    "NO_MODEL_PROMOTION_FROM_EXPLORATORY_METRICS",
                ],
            ),
        }
    )
    for variant, directory, protocol in (
        ("context20", private / "experimental-nse-v2", context_protocol),
        ("price-only16", private / "experimental-nse-v2/price-only", companion_protocol),
    ):
        saved, saved_ref = evidence(directory / "evaluation.json", relative_to=repository)
        if set(saved["candidate_summary"]) != {
            "HIST_GRADIENT_BOOSTING",
            "LOGISTIC",
            "RANDOM_FOREST",
            "RIDGE",
        }:
            raise ValueError("COMPLETE_REGISTERED_V2_CANDIDATE_INVENTORY_REQUIRED")
        protocol_ok = saved["protocol_id"] == sha256(protocol.read_bytes()).hexdigest()
        for algorithm in sorted(saved["candidate_summary"]):
            rows.append(
                {
                    "candidate_id": f"experimental-v2:{variant}:{algorithm}:h5",
                    "family": "ALPHALENS_EXPERIMENTAL_NSE_V2",
                    "algorithm": algorithm,
                    "task": "regression" if algorithm == "RIDGE" else "classification",
                    "feature_version": saved["feature_version"],
                    "horizon_sessions": 5,
                    "model_id": saved["model_id"]
                    if algorithm == saved["selected_algorithm"]
                    else None,
                    "model_id_scope": "SELECTED_FULL_DEVELOPMENT_REFIT"
                    if algorithm == saved["selected_algorithm"]
                    else "CANDIDATE_SPEC_MULTIPLE_TEMPORAL_FITS",
                    "evidence": saved_ref,
                    "acceptance_standard": str(protocol.relative_to(repository)),
                    **candidate_verdict(
                        integrity_valid=protocol_ok,
                        native_verdict=saved["evidence_conclusion"],
                        limitations=[
                            "KNOWN_PERIOD_DEVELOPMENT_NOT_INDEPENDENT_HOLDOUT",
                            "NO_QUALIFIED_FUTURE_SAMPLE_OR_EXTERNAL_REVIEW",
                            "UNCALIBRATED_SCORES",
                            "INDEPENDENT_ACTION_BENCHMARK_COST_AND_ECONOMIC_EVIDENCE_ABSENT",
                        ],
                    ),
                }
            )
    sequence, sequence_ref = evidence(
        private / "sequence-benchmark-v1/report-final.json", relative_to=repository
    )
    if {name for name in sequence["comparisons"] if name.isupper()} != {
        "LSTM",
        "HIST_GRADIENT_BOOSTING",
        "LOGISTIC",
        "RANDOM_FOREST",
        "RIDGE",
        "XGBOOST",
    }:
        raise ValueError("COMPLETE_REGISTERED_SEQUENCE_CANDIDATE_INVENTORY_REQUIRED")
    for algorithm in sorted(name for name in sequence["comparisons"] if name.isupper()):
        rows.append(
            {
                "candidate_id": f"sequence-v1:{algorithm}:h5",
                "family": "ALPHALENS_SEQUENCE_BENCHMARK_V1",
                "algorithm": algorithm,
                "task": "regression" if algorithm == "RIDGE" else "classification",
                "horizon_sessions": 5,
                "model_sha256": sequence["model_sha256"] if algorithm == "LSTM" else None,
                "evidence": sequence_ref,
                "acceptance_standard": str(sequence_protocol.relative_to(repository)),
                **candidate_verdict(
                    integrity_valid=sequence["protocol_sha256"]
                    == sha256(sequence_protocol.read_bytes()).hexdigest(),
                    native_verdict=sequence["edge_status"],
                    limitations=[
                        "KNOWN_PERIOD_DEVELOPMENT_NOT_INDEPENDENT_TEST",
                        "NO_QUALIFIED_PROSPECTIVE_SAMPLE",
                        "REGISTERED_DATE_BLOCK_AND_MULTIPLE_COMPARISON_LIMITATIONS",
                        "NO_EXTERNAL_ACCEPTANCE_OR_COMPLETE_ECONOMICS",
                    ],
                ),
            }
        )
    if len(rows) != 63:
        raise ValueError("COMPLETE_63_CANDIDATE_ACCEPTANCE_AUDIT_REQUIRED")
    return {
        "schema": "alphalens.model.verdict.audit.v1",
        "review_kind": "SOFTWARE_AND_SAVED_EVIDENCE_AUDIT_NOT_EXTERNAL_INDEPENDENT_REVIEW",
        "models": rows,
        "model_count": len(rows),
        "accepted_models": 0,
        "verdict_counts": {
            verdict: sum(row["verdict"] == verdict for row in rows) for verdict in VERDICTS
        },
        "registered_protocol_sha256": protocols,
        "selected_manifest_evidence": manifest_ref,
        "v2_and_sequence_criteria": dict(acceptance.CRITERIA),
        "v2_criteria_version": acceptance.CRITERIA_VERSION,
        "v2_criteria_sha256": sha256(
            json.dumps(
                {"version": acceptance.CRITERIA_VERSION, "criteria": acceptance.CRITERIA},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "original_criteria": (
            "INDEPENDENT_NUMERIC_POWER_MARGIN_COVERAGE_REGISTRATION_REQUIRED_"
            "NO_UNIVERSAL_SAMPLE_COUNT"
        ),
        "model_fits": 0,
        "holdout_reevaluations": 0,
        "model_promotions": 0,
    }
