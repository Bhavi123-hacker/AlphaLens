"""Metadata repositories only; raw and canonical bytes stay on the filesystem."""

from pathlib import Path
from typing import Protocol

from psycopg import Connection

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import RawManifest, RunReport
from alphalens_data.ingestion.storage import publish, stable_json


class MetadataRepository(Protocol):
    def save_manifest(self, manifest: RawManifest) -> None: ...

    def save_run(self, run: RunReport) -> None: ...

    def get_manifest(self, artifact_id: str) -> RawManifest | None: ...

    def get_run(self, run_id: str) -> RunReport | None: ...


class FileMetadataRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, kind: str, identity: str) -> Path:
        if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
            raise DataContractError("INVALID_METADATA_ID")
        return self.root / kind / f"{identity}.json"

    def save_manifest(self, manifest: RawManifest) -> None:
        publish(
            self._path("artifacts", manifest.artifact_id),
            stable_json(manifest.model_dump(mode="json")),
        )

    def save_run(self, run: RunReport) -> None:
        publish(self._path("runs", run.run_id), stable_json(run.model_dump(mode="json")))

    def get_manifest(self, artifact_id: str) -> RawManifest | None:
        path = self._path("artifacts", artifact_id)
        return RawManifest.model_validate_json(path.read_bytes()) if path.exists() else None

    def get_run(self, run_id: str) -> RunReport | None:
        path = self._path("runs", run_id)
        return RunReport.model_validate_json(path.read_bytes()) if path.exists() else None


class PostgresMetadataRepository:
    """Caller owns connection/transaction; migrations are exclusively owned by db/."""

    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.connection = connection

    def save_manifest(self, manifest: RawManifest) -> None:
        payload = manifest.model_dump_json()
        self.connection.execute(
            "INSERT INTO p2_ingestion.raw_artifacts (artifact_id, manifest) VALUES (%s, %s::jsonb) "
            "ON CONFLICT (artifact_id) DO NOTHING",
            (manifest.artifact_id, payload),
        )
        if self.get_manifest(manifest.artifact_id) != manifest:
            raise DataContractError("IMMUTABLE_METADATA_CONFLICT")

    def save_run(self, run: RunReport) -> None:
        self.connection.execute(
            "INSERT INTO p2_ingestion.runs (run_id, artifact_id, report) "
            "VALUES (%s, %s, %s::jsonb) "
            "ON CONFLICT (run_id) DO NOTHING",
            (run.run_id, run.artifact_id, run.model_dump_json()),
        )
        if self.get_run(run.run_id) != run:
            raise DataContractError("IMMUTABLE_METADATA_CONFLICT")

    def get_manifest(self, artifact_id: str) -> RawManifest | None:
        row = self.connection.execute(
            "SELECT manifest::text FROM p2_ingestion.raw_artifacts WHERE artifact_id = %s",
            (artifact_id,),
        ).fetchone()
        return RawManifest.model_validate_json(str(row[0])) if row else None

    def get_run(self, run_id: str) -> RunReport | None:
        row = self.connection.execute(
            "SELECT report::text FROM p2_ingestion.runs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        return RunReport.model_validate_json(str(row[0])) if row else None
