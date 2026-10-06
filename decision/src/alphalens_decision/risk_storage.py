"""Immutable trusted-local risk snapshots, version and SHA256 checked on replay."""

import json
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_decision.risk_contracts import RiskSnapshot


def save(snapshot: RiskSnapshot, root: Path) -> Path:
    snapshot = RiskSnapshot.model_validate(snapshot.model_dump())
    directory = local_output(root) / snapshot.risk_snapshot_id
    content = stable_json(snapshot.model_dump(mode="json"))
    publish(directory / "risk-snapshot.json", content)
    publish(
        directory / "risk-manifest.json",
        stable_json(
            dict(
                risk_snapshot_id=snapshot.risk_snapshot_id,
                schema_version=snapshot.risk_engine_version,
                classification=snapshot.classification.value,
                disclaimer=snapshot.disclaimer,
                production_claims_permitted=False,
                checksum=checksum(content),
            )
        ),
    )
    return directory


def load(directory: Path) -> RiskSnapshot:
    directory = local_output(directory)
    manifest = json.loads((directory / "risk-manifest.json").read_bytes())
    content = (directory / "risk-snapshot.json").read_bytes()
    if checksum(content) != manifest["checksum"]:
        raise DataContractError("RISK_ARTIFACT_CHECKSUM_MISMATCH")
    snapshot = RiskSnapshot.model_validate_json(content)
    if (
        snapshot.risk_snapshot_id != manifest["risk_snapshot_id"]
        or snapshot.risk_engine_version != manifest["schema_version"]
        or snapshot.classification.value != manifest["classification"]
        or manifest["production_claims_permitted"] is not False
        or snapshot.disclaimer != manifest["disclaimer"]
    ):
        raise DataContractError("RISK_ARTIFACT_MANIFEST_MISMATCH")
    return snapshot
