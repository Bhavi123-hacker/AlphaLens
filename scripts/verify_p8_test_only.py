"""Exercise all six fixed models/four horizons on already captured TEST_ONLY P7 data."""

import argparse
from pathlib import Path

from scripts.build_p8_test_fixture import config

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.artifacts import LocalRegistry
from alphalens_training.engine import train


def verify(input_root: Path, output_root: Path) -> dict[str, object]:
    registry = LocalRegistry(output_root)
    reports = []
    for horizon in (1, 5, 10, 20):
        data = SupervisedDataset.model_validate_json(
            (input_root / f"supervised-{horizon}.json").read_bytes()
        )
        if data.classification != Classification.TEST_ONLY:
            raise DataContractError("THIS_VERIFICATION_REQUIRES_TEST_ONLY")
        for task, families in (
            ("classification", ("logistic", "random_forest", "hist_gradient_boosting")),
            ("regression", ("ridge", "random_forest", "hist_gradient_boosting")),
        ):
            for family in families:
                plan = config(horizon, task, family)
                result = train(data, plan)
                repeated = train(data, plan)
                if stable_json(result.manifest) != stable_json(repeated.manifest) or stable_json(
                    result.report
                ) != stable_json(repeated.report):
                    raise DataContractError("FIXTURE_RUN_NOT_REPRODUCIBLE")
                entry = registry.save(result)
                report = registry.evaluate(entry.model_run_id, data)
                reports.append(report | {"artifact_checksums": entry.checksums})
                print(
                    stable_json(
                        dict(
                            model_run_id=entry.model_run_id,
                            task=task,
                            model_family=family,
                            horizon=horizon,
                            training_rows=report["training_rows"],
                            validation_rows=report["validation_rows"],
                            classification="TEST_ONLY",
                            disclaimer="NOT A PERFORMANCE CLAIM",
                            primary_comparison=report["primary_comparison"],
                        )
                    ).decode()
                )
    summary: dict[str, object] = dict(
        schema_version="p8.baseline.v1",
        classification="TEST_ONLY",
        disclaimer="TEST_ONLY — NOT A PERFORMANCE CLAIM",
        production_claims_permitted=False,
        evidence_status="INSUFFICIENT_EVIDENCE",
        run_count=len(reports),
        deterministic_replay="PASS_EQUIVALENT_BEHAVIOR_METRICS",
        serialization_roundtrip="PASS",
        reports=reports,
    )
    publish(registry.root / "suite-summary.TEST_ONLY.json", stable_json(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="TEST_ONLY — NOT A PERFORMANCE CLAIM")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("data/p8-verification-models"))
    args = parser.parse_args()
    verify(local_output(args.input_root), local_output(args.output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
