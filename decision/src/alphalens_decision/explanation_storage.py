"""Immutable explanation artifacts and annotation contract, trusted local only."""

import json
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_decision.explanation_contracts import ExplainabilitySnapshot


def save(snapshot: ExplainabilitySnapshot, root: Path) -> Path:
    snapshot = ExplainabilitySnapshot.model_validate(snapshot.model_dump())
    directory = local_output(root) / snapshot.explanation_id
    files = {
        "explanation-snapshot.json": stable_json(snapshot.model_dump(mode="json")),
        "chart-annotation.json": stable_json(snapshot.annotation().model_dump(mode="json")),
    }
    for name, content in files.items():
        publish(directory / name, content)
    publish(
        directory / "explanation-manifest.json",
        stable_json(
            dict(
                explanation_id=snapshot.explanation_id,
                schema_version=snapshot.version,
                classification=snapshot.classification.value,
                disclaimer=snapshot.disclaimer,
                production_claims_permitted=False,
                checksums={name: checksum(content) for name, content in files.items()},
            )
        ),
    )
    return directory


def load(directory: Path) -> ExplainabilitySnapshot:
    directory = local_output(directory)
    manifest = json.loads((directory / "explanation-manifest.json").read_bytes())
    required = {"explanation-snapshot.json", "chart-annotation.json"}
    if set(manifest["checksums"]) != required:
        raise DataContractError("EXPLANATION_MANIFEST_FILE_MISMATCH")
    files = {name: (directory / name).read_bytes() for name in sorted(required)}
    if any(checksum(content) != manifest["checksums"][name] for name, content in files.items()):
        raise DataContractError("EXPLANATION_ARTIFACT_CHECKSUM_MISMATCH")
    snapshot = ExplainabilitySnapshot.model_validate_json(files["explanation-snapshot.json"])
    if manifest != dict(
        explanation_id=snapshot.explanation_id,
        schema_version=snapshot.version,
        classification=snapshot.classification.value,
        disclaimer=snapshot.disclaimer,
        production_claims_permitted=False,
        checksums={name: checksum(content) for name, content in files.items()},
    ) or json.loads(files["chart-annotation.json"]) != snapshot.annotation().model_dump(
        mode="json"
    ):
        raise DataContractError("EXPLANATION_ARTIFACT_LINEAGE_MISMATCH")
    return snapshot
