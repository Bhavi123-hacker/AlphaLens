"""Explicit evidence assembly over verified P2 runs; no availability inference."""

import json
from pathlib import Path

from alphalens_data.canonical.models import (
    CanonicalBatch,
    NormalizedEvidence,
    QuarantineEvidence,
    RecordLineage,
    Revision,
    revision_key,
)
from alphalens_data.canonical.validation import validate_batch
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import (
    ArtifactSpec,
    Classification,
    RawManifest,
    RunReport,
    Versions,
)
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.storage import RawLanding, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.files import load_run
from alphalens_data.quality.models import ValidationInput


class EvidenceAssembly:
    def __init__(self, root: Path, classification: Classification) -> None:
        self.root = root
        self.classification = classification
        self.artifacts: dict[str, RawManifest] = {}
        self.roots: dict[str, str] = {}
        self.normalized: dict[str, NormalizedEvidence] = {}
        self.quarantine: dict[str, QuarantineEvidence] = {}
        self.runs: list[RunReport] = []
        self.lineage: list[RecordLineage] = []

    def capture(self, payload: bytes, name: str) -> RawManifest:
        spec = ArtifactSpec(
            source="test-only",
            dataset="canonical-evidence",
            source_identifier="TEST_ONLY constructed canonical evidence",
            original_filename=name,
            classification=self.classification,
        )
        manifest, _ = RawLanding(self.root).capture(
            payload, spec, Versions(parser="p5.reference.v1")
        )
        self.artifacts[manifest.artifact_id] = manifest
        self.roots[manifest.artifact_id] = str(self.root.resolve())
        return manifest

    def reference(self, record: Revision, raw: bytes | None = None) -> None:
        # Receipt of the authored declaration is separate from its asserted knowledge times.
        payload = record.model_dump(mode="json")
        manifest = self.capture(stable_json(payload), revision_key(record) + ".json")
        self.link_reference(record, manifest, payload)
        if raw is not None:
            evidence = self.capture(raw, record.provenance.artifact_sha256 + ".evidence")
            if evidence.sha256 != record.provenance.artifact_sha256:
                raise DataContractError("DECLARED_REFERENCE_CHECKSUM_MISMATCH")
            self.link_reference(record, evidence, {"evidence_sha256": evidence.sha256})

    def link_reference(
        self, record: Revision, manifest: RawManifest, payload: dict[str, object]
    ) -> None:
        version = "p5.reference.v1"
        identity = checksum(stable_json([manifest.artifact_id, version, payload]))
        self.normalized[identity] = NormalizedEvidence(
            normalized_record_id=identity,
            artifact_id=manifest.artifact_id,
            normalization_version=version,
            payload=payload,
        )
        self.lineage.append(
            RecordLineage(
                record_key=revision_key(record),
                artifact_id=manifest.artifact_id,
                normalized_record_id=identity,
                evidence_reference="EXPLICIT_AUTHORED_DECLARATION",
            )
        )

    def load_prices(self, path: Path) -> ValidationInput:
        data = load_run(path)
        artifact = data.artifacts[0]
        self.artifacts[artifact.manifest.artifact_id] = artifact.manifest
        self.roots[artifact.manifest.artifact_id] = str(path.resolve().parent.parent.parent)
        if artifact.run:
            self.runs.append(artifact.run)
        normalized = json.loads((path.parent / "normalized.json").read_bytes())
        for payload in normalized:
            identity = payload["normalized_record_id"]
            self.normalized[identity] = NormalizedEvidence(
                normalized_record_id=identity,
                artifact_id=artifact.manifest.artifact_id,
                normalization_version="p2.eod.v1",
                payload=payload,
            )
        for q in data.quarantine:
            identity = checksum(stable_json(q.model_dump(mode="json")))
            self.quarantine[identity] = QuarantineEvidence(quarantine_key=identity, record=q)
        return data


def verify_local_batch(batch: CanonicalBatch, roots: dict[str, str]) -> CanonicalBatch:
    normalized = {n.normalized_record_id: n for n in batch.normalized}
    quarantined = {q.quarantine_key: q.record for q in batch.quarantine}
    for artifact in batch.artifacts:
        root = roots.get(artifact.artifact_id)
        if root is None:
            raise DataContractError("RAW_ROOT_NOT_PROVIDED")
        captured = RawManifest.model_validate_json(
            (Path(root) / "manifests" / (artifact.artifact_id + ".json")).read_bytes()
        )
        if captured != artifact:
            raise DataContractError("CAPTURED_MANIFEST_REPLAY_MISMATCH")
        raw = RawLanding(Path(root)).read(artifact)
        if RawLanding.identity(raw, artifact.spec) != (artifact.nominal_id, artifact.artifact_id):
            raise DataContractError("RAW_MANIFEST_IDENTITY_MISMATCH")
        if artifact.versions.parser == FixtureCSVParser.version:
            records, quarantine = normalize(FixtureCSVParser().parse(raw), artifact)
            for record in records:
                n = normalized.get(record.normalized_record_id)
                if n is None or n.payload != record.model_dump(mode="json", exclude={"record_id"}):
                    raise DataContractError("P2_NORMALIZATION_REPLAY_MISMATCH")
            for q in quarantine:
                if quarantined.get(checksum(stable_json(q.model_dump(mode="json")))) != q:
                    raise DataContractError("P2_QUARANTINE_REPLAY_MISMATCH")
        elif artifact.versions.parser == "p5.reference.v1":
            for n in batch.normalized:
                if n.artifact_id != artifact.artifact_id:
                    continue
                if n.payload == {"evidence_sha256": artifact.sha256}:
                    continue
                try:
                    parsed = json.loads(raw)
                except ValueError:
                    raise DataContractError("REFERENCE_JSON_REQUIRED") from None
                if parsed != n.payload:
                    raise DataContractError("REFERENCE_NORMALIZATION_REPLAY_MISMATCH")
        else:
            raise DataContractError("CANONICAL_REPLAY_PARSER_NOT_SUPPORTED")
    return validate_batch(batch)
