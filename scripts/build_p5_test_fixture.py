"""Construct TEST_ONLY P5 input from real P2/P3 processing and P4 fixtures."""

import argparse
import csv
import io
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.build_p4_test_fixture import FIXTURE, TestOnlyBytes, build_fixture

from alphalens_data.canonical.assembly import EvidenceAssembly, verify_local_batch
from alphalens_data.canonical.models import (
    ActionRevision,
    CanonicalBatch,
    EODValues,
    IdentityRevision,
    MembershipRevision,
    PriceRevision,
    QualityRevision,
    RecordLineage,
    Revision,
    Security,
    SessionRevision,
    revision_key,
)
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.engine import validate
from alphalens_data.quality.files import local_output
from alphalens_data.universe.models import FactProvenance, QualityEvidence


def at(session: date, hour: int = 11) -> datetime:
    return datetime(session.year, session.month, session.day, hour, tzinfo=UTC)


def build_fixture_p5(root: Path) -> tuple[CanonicalBatch, dict[str, str]]:
    root = root.resolve()
    universe = build_fixture(root / "market")
    assembly = EvidenceAssembly(root / "references", Classification.TEST_ONLY)
    revisions: list[Revision] = []
    marker = (FIXTURE / "TEST_ONLY.evidence.txt").read_bytes()
    for fact in (*universe.identities, *universe.memberships):
        values = dict(
            logical_record_id=fact.fact_id,
            revision_id=fact.revision_id,
            revision_number=2 if fact.supersedes_revision_id else 1,
            supersedes_revision_id=fact.supersedes_revision_id,
            security_id=fact.security_id,
            effective_from=fact.effective_from,
            effective_to=fact.effective_to,
            provenance=fact.provenance,
            fact=fact,
        )
        record = (
            IdentityRevision.model_validate(values)
            if fact in universe.identities
            else MembershipRevision.model_validate(values)
        )
        revisions.append(record)
        assembly.reference(record, marker)

    def add_run(path: Path, number: int) -> None:
        record: Revision
        data = assembly.load_prices(path)
        manifest = data.artifacts[0].manifest
        session = manifest.spec.source_session_date
        if session is None:
            raise ValueError("TEST_ONLY per-session input required")
        available = at(session) if number == 1 else at(date(2024, 1, 15))
        report = validate(data)
        evidence = QualityEvidence(
            source="test-only",
            session_date=session,
            report=report,
            report_sha256=checksum(report.to_bytes()),
            available_at=available,
            ingested_at=manifest.acquired_at,
            evidence_reference="TEST_ONLY authored report receipt",
        )
        quality = QualityRevision(
            logical_record_id=f"quality:{session}",
            revision_id=f"r{number}",
            revision_number=number,
            supersedes_revision_id="r1" if number == 2 else None,
            security_id=None,
            effective_from=session,
            provenance=FactProvenance(
                source="test-only",
                artifact_reference=evidence.evidence_reference,
                artifact_sha256=evidence.report_sha256,
                evidence_reference="TEST_ONLY declared quality availability",
                classification=Classification.TEST_ONLY,
                ingested_at=manifest.acquired_at,
                available_at=available,
                availability_basis="CONSERVATIVE_BOUND",
            ),
            evidence=evidence,
        )
        revisions.append(quality)
        assembly.reference(quality, report.to_bytes())
        if number == 1:
            calendar_bytes = stable_json(
                {
                    "TEST_ONLY": True,
                    "session_date": session.isoformat(),
                    "status": "UNKNOWN_SESSION_STATUS",
                    "close_at": at(session, 10).isoformat(),
                    "description": "Constructed fixture close; no real NSE calendar claim",
                }
            )
            calendar = assembly.capture(calendar_bytes, f"calendar-{session}.json")
            record = SessionRevision(
                logical_record_id=f"session:{session}",
                revision_id="r1",
                revision_number=1,
                security_id=None,
                effective_from=session,
                session_date=session,
                status="UNKNOWN_SESSION_STATUS",
                session_close_at=at(session, 10),
                provenance=FactProvenance(
                    source="test-only",
                    artifact_reference=calendar.artifact_id,
                    artifact_sha256=calendar.sha256,
                    evidence_reference="TEST_ONLY constructed session",
                    classification=Classification.TEST_ONLY,
                    ingested_at=calendar.acquired_at,
                    available_at=at(session),
                    availability_basis="CONSERVATIVE_BOUND",
                ),
            )
            revisions.append(record)
            assembly.reference(record, calendar_bytes)
        identities = {f.source_security_id: f.security_id for f in universe.identities}
        for observed in data.records:
            security = identities[observed.security_id]
            record = PriceRevision(
                logical_record_id=f"bar:{security}:{session}",
                revision_id=f"r{number}",
                revision_number=number,
                supersedes_revision_id="r1" if number == 2 else None,
                security_id=security,
                effective_from=session,
                session_date=session,
                price_basis="OBSERVED_UNKNOWN_BASIS",
                currency=observed.currency,
                session_close_at=at(session, 10),
                quality_key=revision_key(quality),
                values=EODValues(
                    open=observed.open,
                    high=observed.high,
                    low=observed.low,
                    close=observed.close,
                    volume=observed.volume,
                ),
                provenance=FactProvenance(
                    source=observed.source,
                    artifact_reference=manifest.artifact_id,
                    artifact_sha256=manifest.sha256,
                    evidence_reference="TEST_ONLY independently authored EOD availability",
                    classification=observed.classification,
                    ingested_at=observed.acquired_at,
                    available_at=available,
                    published_at=available,
                    availability_basis="VERIFIED_PUBLICATION",
                ),
            )
            revisions.append(record)
            assembly.reference(record)
            assembly.lineage.append(
                RecordLineage(
                    record_key=revision_key(record),
                    artifact_id=manifest.artifact_id,
                    normalized_record_id=observed.normalized_record_id,
                    source_record_id=observed.record_id,
                    evidence_reference="P2_VERIFIED_NORMALIZATION",
                )
            )
        for scope in data.quarantine_scopes:
            rejected = tuple(
                q for q in data.quarantine if q.source_row_number == scope.source_row_number
            )
            record = PriceRevision(
                logical_record_id=f"bar:{identities[scope.security_id]}:{session}",
                revision_id=f"r{number}",
                revision_number=number,
                supersedes_revision_id="r1" if number == 2 else None,
                security_id=identities[scope.security_id],
                effective_from=session,
                session_date=session,
                price_basis="OBSERVED_UNKNOWN_BASIS",
                currency=manifest.spec.currency,
                values=None,
                session_close_at=at(session, 10),
                quality_key=revision_key(quality),
                rejection_reason_codes=tuple(sorted({q.validation_rule for q in rejected})),
                provenance=FactProvenance(
                    source="test-only",
                    artifact_reference=manifest.artifact_id,
                    artifact_sha256=manifest.sha256,
                    evidence_reference=scope.evidence_reference,
                    classification=Classification.TEST_ONLY,
                    ingested_at=manifest.acquired_at,
                    available_at=available,
                    availability_basis="CONSERVATIVE_BOUND",
                ),
            )
            revisions.append(record)
            assembly.reference(record)
            for q in rejected:
                assembly.lineage.append(
                    RecordLineage(
                        record_key=revision_key(record),
                        artifact_id=manifest.artifact_id,
                        quarantine_key=checksum(stable_json(q.model_dump(mode="json"))),
                        evidence_reference=scope.evidence_reference,
                    )
                )

    for path in sorted((root / "market").glob("*/canonical/*/canonical.json")):
        add_run(path, 1)
    # Explicit correction to the Jan 10 source file, made knowable Jan 15.
    original = next((root / "market/2024-01-10/canonical").glob("*/canonical.json"))
    from alphalens_data.quality.files import load_run

    data = load_run(original)
    manifest = data.artifacts[0].manifest
    raw = RawLanding(root / "market/2024-01-10").read(manifest)
    rows = list(csv.reader(io.StringIO(raw.decode())))
    close_index = rows[0].index("close")
    security_index = rows[0].index("security_id")
    for row in rows[1:]:
        if row[security_index] == "TEST:A":
            row[close_index] = "101"
    buffer = io.StringIO(newline="")
    csv.writer(buffer).writerows(rows)
    pipeline = IngestionPipeline(
        RawLanding(root / "correction"),
        FileMetadataRepository(root / "correction/metadata"),
        FixtureCSVParser(),
    )
    result = pipeline.ingest(TestOnlyBytes(buffer.getvalue().encode()), manifest.spec)
    add_run(root / "correction/canonical" / result.report.run_id / "canonical.json", 2)
    action_bytes = stable_json(
        {
            "classification": "TEST_ONLY",
            "security_id": "TEST:D",
            "event_type": "SYMBOL_CHANGE",
            "effective_date": "2024-01-10",
            "available_at": "2024-01-09T00:00:00Z",
        }
    )
    action_manifest = assembly.capture(action_bytes, "symbol-change.json")
    action = ActionRevision(
        logical_record_id="action:D:symbol",
        revision_id="r1",
        revision_number=1,
        security_id="TEST:D",
        effective_from=date(2024, 1, 10),
        corporate_action_id="TEST_ONLY:D:symbol",
        event_type="SYMBOL_CHANGE",
        provenance=FactProvenance(
            source="test-only",
            artifact_reference=action_manifest.artifact_id,
            artifact_sha256=action_manifest.sha256,
            evidence_reference="TEST_ONLY symbol change evidence",
            classification=Classification.TEST_ONLY,
            ingested_at=action_manifest.acquired_at,
            published_at=at(date(2024, 1, 9), 0),
            available_at=at(date(2024, 1, 9), 0),
            availability_basis="VERIFIED_PUBLICATION",
        ),
    )
    revisions.append(action)
    assembly.reference(action, action_bytes)
    batch = CanonicalBatch(
        classification=Classification.TEST_ONLY,
        definition=universe.definition,
        securities=tuple(
            Security(security_id=s, classification=Classification.TEST_ONLY)
            for s in sorted({f.security_id for f in universe.identities})
        ),
        artifacts=tuple(assembly.artifacts.values()),
        runs=tuple(assembly.runs),
        normalized=tuple(assembly.normalized.values()),
        quarantine=tuple(assembly.quarantine.values()),
        revisions=tuple(revisions),
        lineage=tuple(assembly.lineage),
    )
    verify_local_batch(batch, assembly.roots)
    publish(
        root / "canonical-input.json",
        stable_json({"batch": batch.model_dump(mode="json"), "artifact_roots": assembly.roots}),
    )
    return batch, assembly.roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct TEST_ONLY P5 evidence; no market data")
    parser.add_argument("--data-root", type=Path, default=Path("data/p5-test-only"))
    args = parser.parse_args()
    batch, _ = build_fixture_p5(local_output(args.data_root))
    print(
        stable_json(
            {
                "input_id": batch.input_id,
                "classification": batch.classification,
                "records": len(batch.revisions),
            }
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
