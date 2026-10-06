"""Immutable JSON ranking snapshots; complete list persists independently of Top-N."""

import json
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import local_output
from alphalens_decision.ranking_contracts import RankSnapshot


def save(snapshot: RankSnapshot, root: Path) -> Path:
    snapshot = RankSnapshot.model_validate(snapshot.model_dump())
    directory = local_output(root) / snapshot.rank_snapshot_id
    content = stable_json(snapshot.model_dump(mode="json"))
    publish(directory / "rank-snapshot.json", content)
    publish(
        directory / "rank-manifest.json",
        stable_json(
            dict(
                rank_snapshot_id=snapshot.rank_snapshot_id,
                schema_version=snapshot.ranking_version,
                classification=snapshot.classification.value,
                disclaimer=snapshot.disclaimer,
                production_claims_permitted=False,
                checksum=checksum(content),
            )
        ),
    )
    return directory


def load(directory: Path) -> RankSnapshot:
    directory = local_output(directory)
    manifest = json.loads((directory / "rank-manifest.json").read_bytes())
    content = (directory / "rank-snapshot.json").read_bytes()
    if checksum(content) != manifest["checksum"]:
        raise DataContractError("RANKING_ARTIFACT_CHECKSUM_MISMATCH")
    snapshot = RankSnapshot.model_validate_json(content)
    if (
        snapshot.rank_snapshot_id != manifest["rank_snapshot_id"]
        or snapshot.ranking_version != manifest["schema_version"]
        or snapshot.classification.value != manifest["classification"]
        or snapshot.disclaimer != manifest["disclaimer"]
        or manifest["production_claims_permitted"] is not False
    ):
        raise DataContractError("RANKING_ARTIFACT_MANIFEST_MISMATCH")
    return snapshot
