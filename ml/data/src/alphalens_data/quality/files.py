"""Read an existing P2 run with verified raw/normalized lineage; never parse vendors."""

from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import (
    CanonicalEOD,
    QuarantineRecord,
    RawManifest,
    RunReport,
)
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.parsing import EODParser, FixtureCSVParser
from alphalens_data.ingestion.storage import RawLanding
from alphalens_data.normalization import checksum
from alphalens_data.quality.models import ArtifactEvidence, QuarantineScope, ValidationInput


def local_output(path: Path) -> Path:
    resolved = path.resolve()
    workspace = Path.cwd().resolve()
    if not any(resolved.is_relative_to(workspace / name) for name in ("data", ".local-data")):
        raise DataContractError("OUTPUT_MUST_USE_IGNORED_LOCAL_STORAGE")
    return resolved


def load_run(path: Path, parser: EODParser | None = None) -> ValidationInput:
    path = path.resolve()
    if path.name != "canonical.json" or path.parent.parent.name != "canonical":
        raise DataContractError("EXPECTED_P2_CANONICAL_RUN_PATH")
    root = path.parent.parent.parent
    records = TypeAdapter(tuple[CanonicalEOD, ...]).validate_json(path.read_bytes())
    quarantine = TypeAdapter(tuple[QuarantineRecord, ...]).validate_json(
        (path.parent / "quarantine.json").read_bytes()
    )
    run = RunReport.model_validate_json((path.parent / "report.json").read_bytes())
    artifact_ids = (
        {run.artifact_id} | {r.artifact_id for r in records} | {q.artifact_id for q in quarantine}
    )
    if artifact_ids != {run.artifact_id}:
        raise DataContractError("P2_SINGLE_RUN_ARTIFACT_MISMATCH")
    manifest = RawManifest.model_validate_json(
        (root / "manifests" / (run.artifact_id + ".json")).read_bytes()
    )
    raw = RawLanding(root).read(manifest)
    selected_parser = parser or FixtureCSVParser()
    if selected_parser.version != manifest.versions.parser:
        raise DataContractError("P2_REPLAY_PARSER_VERSION_REQUIRED")
    parsed = selected_parser.parse(raw)
    replay_records, replay_quarantine = normalize(parsed, manifest)
    if records != replay_records or quarantine != replay_quarantine:
        raise DataContractError("P2_REPLAY_OUTPUT_MISMATCH")
    normalized = (path.parent / "normalized.json").read_bytes()
    rejected_rows = {q.source_row_number for q in quarantine}
    scopes: list[QuarantineScope] = []
    for row in parsed:
        fields = dict(row.fields)
        security = fields.get("security_id")
        session_text = fields.get("session_date", "")
        if (
            row.row_number not in rejected_rows
            or row.error
            or not security
            or security != security.strip()
            or len(security) > 256
        ):
            continue
        try:
            session = date.fromisoformat(session_text)
        except ValueError:
            continue
        if session.isoformat() != session_text:
            continue
        scopes.append(
            QuarantineScope(
                artifact_id=manifest.artifact_id,
                source_row_number=row.row_number,
                security_id=security,
                session_date=session,
                evidence_reference=f"P2_RAW_ROW:{manifest.artifact_id}:{row.row_number}",
            )
        )
    return ValidationInput(
        records=records,
        quarantine=quarantine,
        classification=run.classification,
        quarantine_scopes=tuple(scopes),
        artifacts=(
            ArtifactEvidence(
                manifest=manifest,
                observed_sha256=checksum(raw),
                observed_byte_size=len(raw),
                normalized_sha256=checksum(normalized),
                run=run,
            ),
        ),
    )
