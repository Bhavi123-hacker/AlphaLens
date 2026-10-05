"""Bounded synchronous P2 orchestration with deterministic replay and safe events."""

import logging
from dataclasses import dataclass

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.acquisition import ArtifactSource
from alphalens_data.ingestion.contracts import (
    ArtifactSpec,
    CanonicalEOD,
    QuarantineRecord,
    RawManifest,
    RunReport,
    Versions,
)
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.output import parquet_bytes
from alphalens_data.ingestion.parsing import EODParser
from alphalens_data.ingestion.repository import MetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json
from alphalens_data.normalization import checksum

LOGGER = logging.getLogger("alphalens_data.ingestion")


def event(name: str, **details: str | int | bool) -> None:
    LOGGER.info(stable_json({"event": name, **details}).decode())


@dataclass(frozen=True)
class IngestionResult:
    manifest: RawManifest
    report: RunReport
    records: tuple[CanonicalEOD, ...]
    quarantine: tuple[QuarantineRecord, ...]
    duplicate: bool


class IngestionPipeline:
    def __init__(
        self, landing: RawLanding, repository: MetadataRepository, parser: EODParser
    ) -> None:
        self.landing = landing
        self.repository = repository
        self.parser = parser

    def ingest(self, source: ArtifactSource, spec: ArtifactSpec) -> IngestionResult:
        spec = ArtifactSpec.model_validate(spec.model_dump())
        event("ingestion_started")
        payload = source.acquire()
        event("artifact_acquired", byte_size=len(payload))
        versions = Versions(parser=self.parser.version)
        _, artifact_id = self.landing.identity(payload, spec)
        known = self.repository.get_manifest(artifact_id)
        manifest, duplicate = self.landing.capture(payload, spec, versions, known)
        event("checksum_generated", artifact_id=manifest.artifact_id, sha256=manifest.sha256)
        if duplicate:
            event("duplicate_detected", artifact_id=manifest.artifact_id)
        self.repository.save_manifest(manifest)
        result = self._process(manifest, duplicate)
        base = self.landing.root / "canonical" / result.report.run_id
        publish(base / "canonical.json", self._canonical(result.records))
        publish(base / "normalized.json", self._normalized(result.records))
        publish(base / "quarantine.json", self._quarantine(result.quarantine))
        publish(base / "canonical.parquet", parquet_bytes(result.records, manifest))
        publish(base / "report.json", stable_json(result.report.model_dump(mode="json")))
        self.repository.save_run(result.report)
        return result

    @staticmethod
    def _normalized(records: tuple[CanonicalEOD, ...]) -> bytes:
        return stable_json([r.model_dump(mode="json", exclude={"record_id"}) for r in records])

    @staticmethod
    def _canonical(records: tuple[CanonicalEOD, ...]) -> bytes:
        return stable_json([r.model_dump(mode="json") for r in records])

    @staticmethod
    def _quarantine(records: tuple[QuarantineRecord, ...]) -> bytes:
        return stable_json([r.model_dump(mode="json") for r in records])

    def _process(self, manifest: RawManifest, duplicate: bool) -> IngestionResult:
        if manifest.versions != Versions(parser=self.parser.version):
            raise DataContractError("REPLAY_VERSION_MISMATCH")
        rows = self.parser.parse(self.landing.read(manifest))
        event("parsing_complete", artifact_id=manifest.artifact_id, row_count=len(rows))
        records, quarantine = normalize(rows, manifest)
        if quarantine:
            event(
                "validation_failures", artifact_id=manifest.artifact_id, error_count=len(quarantine)
            )
        event("normalization_complete", artifact_id=manifest.artifact_id, record_count=len(records))
        versions = manifest.versions.model_dump()
        report = RunReport(
            run_id=checksum(stable_json([manifest.artifact_id, versions])),
            artifact_id=manifest.artifact_id,
            versions=manifest.versions,
            classification=manifest.spec.classification,
            canonical_sha256=checksum(self._canonical(records)),
            quarantine_sha256=checksum(self._quarantine(quarantine)),
            canonical_count=len(records),
            quarantined_row_count=len({r.source_row_number for r in quarantine}),
            validation_error_count=len(quarantine),
            status="UNAVAILABLE" if not records else "DEGRADED" if quarantine else "AVAILABLE",
        )
        return IngestionResult(manifest, report, records, quarantine, duplicate)

    def replay(self, artifact_id: str) -> IngestionResult:
        manifest = self.repository.get_manifest(artifact_id)
        if manifest is None:
            raise DataContractError("REPLAY_ARTIFACT_NOT_FOUND")
        result = self._process(manifest, True)
        previous = self.repository.get_run(result.report.run_id)
        base = self.landing.root / "canonical" / result.report.run_id
        matched = (
            previous == result.report
            and (base / "canonical.json").read_bytes() == self._canonical(result.records)
            and (base / "normalized.json").read_bytes() == self._normalized(result.records)
            and (base / "quarantine.json").read_bytes() == self._quarantine(result.quarantine)
            and (base / "canonical.parquet").read_bytes() == parquet_bytes(result.records, manifest)
        )
        event("replay_result", artifact_id=artifact_id, matched=matched)
        if not matched:
            raise DataContractError("REPLAY_OUTPUT_MISMATCH")
        return result
