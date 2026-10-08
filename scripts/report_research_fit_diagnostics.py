"""Read-only optimization diagnostics from checksum-pinned locally created models.

This never fits, predicts, selects or tunes. Only reviewed sklearn LogisticRegression
artifacts are loaded; all other model families are explicitly outside this inspection.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import skops.io as sio
from sklearn.linear_model import LogisticRegression

from alphalens_data.ingestion.storage import stable_json
from alphalens_data.research import ResearchProfile, lineage
from alphalens_evaluation.research import file_hash
from alphalens_training.artifacts import REVIEWED_TYPES


def diagnose(root: Path) -> dict[str, Any]:
    plan = json.loads((root / "training-plan.json").read_bytes())
    profile = ResearchProfile.model_validate(plan["research_profile"])
    reports = json.loads((root / "p9/development-results.json").read_bytes())["reports"]
    for year in (2025, 2026):
        path = root / f"{year}-results.json"
        if path.exists():
            reports += json.loads(path.read_bytes())["reports"]
    diagnostics = []
    for report in reports:
        if report["model_family"] != "logistic":
            continue
        if report["dataset_id"] != plan["dataset_id"]:
            raise ValueError("FIT_DIAGNOSTIC_DATASET_MISMATCH")
        path = root / "p9" / report["model_file"]
        if file_hash(path) != report["model_sha256"]:
            raise ValueError("FIT_DIAGNOSTIC_ARTIFACT_CHECKSUM_MISMATCH")
        if not set(sio.get_untrusted_types(file=path)) <= REVIEWED_TYPES:
            raise ValueError("FIT_DIAGNOSTIC_UNREVIEWED_ARTIFACT_TYPE")
        model = sio.load(path, trusted=sorted(REVIEWED_TYPES))
        estimator = model.named_steps["estimator"]
        if not isinstance(estimator, LogisticRegression):
            raise ValueError("FIT_DIAGNOSTIC_ESTIMATOR_MISMATCH")
        iterations = [int(i) for i in estimator.n_iter_]
        limit = int(estimator.max_iter)
        diagnostics.append(
            dict(
                model_run_id=report["model_run_id"],
                model_sha256=report["model_sha256"],
                horizon=report["horizon"],
                fold_id=report["fold_id"],
                iterations=iterations,
                configured_iteration_limit=limit,
                iteration_limit_reached=any(i >= limit for i in iterations),
                method="STORED_TRAINING_OPTIMIZER_ITERATIONS_NOT_OOS_PERFORMANCE",
            )
        )
    return dict(
        **lineage(profile),
        dataset_id=plan["dataset_id"],
        diagnostics=sorted(diagnostics, key=lambda r: (r["horizon"], r["fold_id"])),
        policy="DISCLOSURE_ONLY_NO_CONFIG_CHANGE_OR_RESELECTION",
        other_families="NOT_INSPECTED_BY_LOGISTIC_ITERATION_METHOD",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.output)
    Path("docs/ml/real-model-fit-diagnostics.json").write_bytes(stable_json(result))
    print(json.dumps(dict(logistic_fits=len(result["diagnostics"]))))


if __name__ == "__main__":
    main()
