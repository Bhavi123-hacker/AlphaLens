"""TEST_ONLY saved metadata inventory; no model fitting or historical evaluation."""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from workers.nse_market import model_review


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture(root: Path) -> None:
    models = [
        {
            "task": task,
            "model_family": algorithm,
            "horizon": horizon,
            "research_status": "TEST_ONLY_INSUFFICIENT",
        }
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
    ]
    write(root / "docs/completion/model-readiness-manifest.json", {"entries": []})
    write(root / "docs/ml/real-model-comparison.json", {"models": models})
    write(root / "docs/ml/real-research-evaluation-plan.json", {"status": "TEST_ONLY_REGISTERED"})
    for relative in (
        "docs/ml/p33-prospective-acceptance-protocol.md",
        "docs/development/ml-v2-registered-protocol.md",
        "docs/development/ml-v2-price-only-registered-protocol.md",
        "docs/development/ml-sequence-v1-registered-protocol.md",
        "docs/development/experimental-nse-v1-predeclared-study.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("TEST_ONLY_REGISTERED_POLICY:" + relative, encoding="utf-8")
    private = root / ".local-data"
    run_id = "a" * 32
    write(private / "experimental-nse-v1/latest.json", {"run_id": run_id})
    write(
        private / f"experimental-nse-v1/runs/{run_id}/evaluation.json",
        {
            "model_id": "TEST_ONLY_V1",
            "target_version": "TEST_ONLY_DAYTIME",
            "independent_model_accepted": False,
        },
    )
    for variant, protocol in (
        ("experimental-nse-v2", "ml-v2-registered-protocol.md"),
        ("experimental-nse-v2/price-only", "ml-v2-price-only-registered-protocol.md"),
    ):
        write(
            private / variant / "evaluation.json",
            {
                "protocol_id": sha256(
                    (root / "docs/development" / protocol).read_bytes()
                ).hexdigest(),
                "candidate_summary": {
                    algorithm: {}
                    for algorithm in (
                        "HIST_GRADIENT_BOOSTING",
                        "LOGISTIC",
                        "RANDOM_FOREST",
                        "RIDGE",
                    )
                },
                "feature_version": "TEST_ONLY",
                "model_id": "TEST_ONLY_V2",
                "selected_algorithm": "HIST_GRADIENT_BOOSTING",
                "evidence_conclusion": "TEST_ONLY_PENDING",
            },
        )
    write(
        private / "sequence-benchmark-v1/report-final.json",
        {
            "comparisons": {
                algorithm: {}
                for algorithm in (
                    "LSTM",
                    "HIST_GRADIENT_BOOSTING",
                    "LOGISTIC",
                    "RANDOM_FOREST",
                    "RIDGE",
                    "XGBOOST",
                    "momentum",
                )
            },
            "model_sha256": "0" * 64,
            "protocol_sha256": sha256(
                (root / "docs/development/ml-sequence-v1-registered-protocol.md").read_bytes()
            ).hexdigest(),
            "edge_status": "TEST_ONLY_PENDING",
        },
    )


def test_every_original_and_experimental_candidate_has_explicit_unpromoted_verdict(
    tmp_path: Path,
) -> None:
    fixture(tmp_path)
    result = model_review.registry(tmp_path)
    assert result["model_count"] == len(result["models"]) == 63
    assert result["accepted_models"] == 0
    assert result["verdict_counts"]["EXPERIMENTAL_INSUFFICIENT_EVIDENCE"] == 63
    assert all(row["evidence"]["sha256"] and row["acceptance_standard"] for row in result["models"])
    assert (
        result["model_fits"] == result["holdout_reevaluations"] == result["model_promotions"] == 0
    )
    assert result["v2_and_sequence_criteria"]["future_decision_dates"] == 126
    assert result["v2_and_sequence_criteria"]["eligible_outcomes"] == 1000


def test_changed_registered_protocol_blocks_corresponding_saved_candidates(tmp_path: Path) -> None:
    fixture(tmp_path)
    (tmp_path / "docs/development/ml-v2-registered-protocol.md").write_text(
        "TEST_ONLY_CHANGED", encoding="utf-8"
    )
    result = model_review.registry(tmp_path)
    assert result["verdict_counts"]["BLOCKED_DATA_QUALITY"] == 4
    assert result["accepted_models"] == 0
    assert result["verdict_counts"]["EXPERIMENTAL_INSUFFICIENT_EVIDENCE"] == 59


def test_missing_candidate_cannot_silently_disappear_from_review(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "docs/ml/real-model-comparison.json"
    value = json.loads(path.read_text())
    value["models"].pop()
    write(path, value)
    with pytest.raises(ValueError, match="COMPLETE_ORIGINAL_48"):
        model_review.registry(tmp_path)
