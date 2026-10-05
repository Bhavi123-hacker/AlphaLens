"""Offline P3 validation CLI. Reports contain IDs and reasons, never recommendations."""

import argparse
from contextlib import suppress
from pathlib import Path

from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.engine import validate
from alphalens_data.quality.files import load_run, local_output
from alphalens_data.quality.models import VALIDATOR_VERSION


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical P2 development data")
    parser.add_argument("canonical_output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        output = local_output(
            args.output or args.canonical_output.parent / "validation-report.json"
        )
    except Exception:
        print(stable_json({"status": "REJECTED", "reason": "INVALID_OUTPUT_PATH"}).decode())
        return 2
    try:
        report = validate(load_run(args.canonical_output))
        publish(output, report.to_bytes())
        print(
            stable_json(
                {
                    "status": report.status,
                    "summary": report.summary.model_dump(mode="json"),
                    "report_sha256": checksum(report.to_bytes()),
                    "validator_version": VALIDATOR_VERSION,
                }
            ).decode()
        )
        return 2 if report.status == "REJECTED" else 0
    except Exception:
        # Do not print exception messages or source content/paths. Schema, raw checksum,
        # missing files and incompatible immutable output all fail closed.
        failure = stable_json(
            {
                "status": "REJECTED",
                "validator_version": VALIDATOR_VERSION,
                "classification": "UNAVAILABLE",
                "production_claims_permitted": False,
                "issues": [
                    {
                        "rule_id": "INPUT_OR_OUTPUT_INTEGRITY",
                        "severity": "FATAL",
                        "message": "Canonical schema, lineage or immutable output invalid",
                    }
                ],
            }
        )
        with suppress(Exception):
            publish(output, failure)
        print(failure.decode())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
