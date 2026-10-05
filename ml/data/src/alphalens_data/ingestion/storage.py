"""Exclusive immutable publication with checksum verification and revision lineage."""

import json
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import ArtifactSpec, RawManifest, Versions
from alphalens_data.normalization import checksum


def stable_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def publish(path: Path, payload: bytes) -> None:
    """Publish complete bytes exclusively; never overwrite, even after interrupted runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise DataContractError("IMMUTABLE_FILE_CONFLICT") from None
    finally:
        temporary.unlink()


class RawLanding:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise DataContractError("ARTIFACT_PATH_ESCAPES_ROOT")
        return path

    @contextmanager
    def lock(self) -> Iterator[None]:
        """Fail explicitly on concurrent capture; no last-writer-wins lineage."""
        path = self.root / ".capture.lock"
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise DataContractError("CAPTURE_BUSY_OR_INTERRUPTED_LOCK") from None
        try:
            os.close(descriptor)
            yield
        finally:
            path.unlink()

    @staticmethod
    def identity(payload: bytes, spec: ArtifactSpec) -> tuple[str, str]:
        nominal = checksum(
            stable_json(
                [
                    spec.source,
                    spec.dataset,
                    spec.source_session_date and spec.source_session_date.isoformat(),
                    spec.original_filename,
                ]
            )
        )
        return nominal, checksum(stable_json([nominal, checksum(payload)]))

    def capture(
        self,
        payload: bytes,
        spec: ArtifactSpec,
        versions: Versions,
        known: RawManifest | None = None,
    ) -> tuple[RawManifest, bool]:
        spec = ArtifactSpec.model_validate(spec.model_dump())
        digest = checksum(payload)
        nominal, artifact_id = self.identity(payload, spec)
        if known is not None and (
            known.artifact_id != artifact_id
            or known.spec != spec
            or known.versions != versions
            or known.sha256 != digest
            or known.byte_size != len(payload)
        ):
            raise DataContractError("DUPLICATE_METADATA_CONFLICT")
        manifest_path = self.root / "manifests" / f"{artifact_id}.json"
        with self.lock():
            if manifest_path.exists():
                manifest = RawManifest.model_validate_json(manifest_path.read_bytes())
                self.read(manifest)
                if manifest.spec != spec or manifest.versions != versions:
                    raise DataContractError("DUPLICATE_METADATA_CONFLICT")
                if known is not None and known != manifest:
                    raise DataContractError("LOCAL_REPOSITORY_MANIFEST_CONFLICT")
                return manifest, True
            previous = sorted(
                (
                    RawManifest.model_validate_json(p.read_bytes())
                    for p in (self.root / "manifests").glob("*.json")
                ),
                key=lambda m: (m.acquired_at, m.artifact_id),
            )
            acquired = datetime.now(UTC)
            day = spec.source_session_date or acquired.date()
            relative = f"raw/{spec.source}/{spec.dataset}/{day:%Y/%m/%d}/{artifact_id}/payload"
            manifest = known or RawManifest(
                artifact_id=artifact_id,
                nominal_id=nominal,
                spec=spec,
                acquired_at=acquired,
                raw_path=relative,
                byte_size=len(payload),
                sha256=digest,
                versions=versions,
                prior_revision_ids=tuple(
                    m.artifact_id for m in previous if m.nominal_id == nominal
                ),
            )
            publish(self.resolve(manifest.raw_path), payload)
            self.resolve(manifest.raw_path).chmod(stat.S_IREAD)
            publish(manifest_path, stable_json(manifest.model_dump(mode="json")))
            return manifest, known is not None

    def read(self, manifest: RawManifest) -> bytes:
        payload = self.resolve(manifest.raw_path).read_bytes()
        if len(payload) != manifest.byte_size or checksum(payload) != manifest.sha256:
            raise DataContractError("RAW_ARTIFACT_CHECKSUM_OR_SIZE_MISMATCH")
        return payload
