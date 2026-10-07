"""Immutable checksum-pinned signal history, trusted local artifacts only."""

import json
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_decision.signal_contracts import SignalSnapshot


def save(snapshot: SignalSnapshot, root: Path) -> Path:
    snapshot = SignalSnapshot.model_validate(snapshot.model_dump())
    directory = local_output(root) / snapshot.signal_snapshot_id
    content = stable_json(snapshot.model_dump(mode="json"))
    publish(directory / "signal-snapshot.json", content)
    publish(
        directory / "signal-manifest.json",
        stable_json(
            dict(
                signal_snapshot_id=snapshot.signal_snapshot_id,
                schema_version=snapshot.signal_engine_version,
                classification=snapshot.classification.value,
                disclaimer=snapshot.disclaimer,
                production_claims_permitted=False,
                checksum=checksum(content),
            )
        ),
    )
    return directory


def load(directory: Path) -> SignalSnapshot:
    directory = local_output(directory)
    content = (directory / "signal-snapshot.json").read_bytes()
    manifest = json.loads((directory / "signal-manifest.json").read_bytes())
    if checksum(content) != manifest["checksum"]:
        raise DataContractError("SIGNAL_ARTIFACT_CHECKSUM_MISMATCH")
    snapshot = SignalSnapshot.model_validate_json(content)
    expected = dict(
        signal_snapshot_id=snapshot.signal_snapshot_id,
        schema_version=snapshot.signal_engine_version,
        classification=snapshot.classification.value,
        disclaimer=snapshot.disclaimer,
        production_claims_permitted=False,
        checksum=checksum(content),
    )
    if manifest != expected:
        raise DataContractError("SIGNAL_ARTIFACT_MANIFEST_MISMATCH")
    return snapshot
