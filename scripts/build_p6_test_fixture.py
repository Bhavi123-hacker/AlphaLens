"""Constructed TEST_ONLY history, not real companies, exchange calendar or index data."""

import argparse
import csv
import io
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from scripts.build_p4_test_fixture import TestOnlyBytes

from alphalens_data.canonical.assembly import EvidenceAssembly, verify_local_batch
from alphalens_data.canonical.models import (
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
from alphalens_data.ingestion.contracts import ArtifactSpec, Classification
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.engine import validate
from alphalens_data.quality.files import local_output
from alphalens_data.universe.models import (
    FactProvenance,
    IdentityFact,
    MembershipFact,
    QualityEvidence,
    UniverseDefinition,
)

START = date(2024, 1, 1)


def day(index: int) -> date:
    return START + timedelta(days=index)


def instant(index: int, hour: int = 11) -> datetime:
    return datetime.combine(day(index), datetime.min.time(), UTC) + timedelta(hours=hour)


def build_history(
    root: Path,
    length: int = 70,
    overrides: dict[tuple[int, str], dict[str, str]] | None = None,
    revision: tuple[int, int, str] | None = None,
) -> tuple[CanonicalBatch, dict[str, str]]:
    assembly = EvidenceAssembly(root / "references", Classification.TEST_ONLY)
    revisions: list[Revision] = []
    marker = (
        b"TEST_ONLY authored synthetic calendar, prices, identities and basis; NOT NSE evidence"
    )
    captured = assembly.capture(marker, "TEST_ONLY.evidence.txt")

    def provenance(index: int, digest: str = captured.sha256) -> FactProvenance:
        return FactProvenance(
            source="test-only",
            artifact_reference="TEST_ONLY",
            artifact_sha256=digest,
            evidence_reference="TEST_ONLY explicit authored evidence",
            classification=Classification.TEST_ONLY,
            ingested_at=captured.acquired_at,
            available_at=instant(index),
            availability_basis="CONSERVATIVE_BOUND",
        )

    def append(record: Revision, raw: bytes | None = marker) -> None:
        revisions.append(record)
        # RawLanding scans a landing's manifests for revision lineage. Keep each
        # authored declaration in its own bounded landing; do not create a large
        # quadratic fixture landing or change P2/P5 behavior.
        assembly.root = root / "d" / str(len(revisions))
        assembly.reference(record, raw if raw != marker else None)
        if raw == marker:
            assembly.link_reference(record, captured, {"evidence_sha256": captured.sha256})

    securities = ("TEST:ALPHA", "TEST:BETA", "TEST:BENCHMARK", "TEST:NEW", "TEST:DEPART")
    for security in securities:
        first = 35 if security == "TEST:NEW" else 0
        fact = IdentityFact(
            fact_id=f"identity:{security}",
            revision_id="r1",
            security_id=security,
            effective_from=day(first),
            provenance=provenance(first),
            source_security_id=security,
            symbol=security.replace(":", "_"),
            series="EQ",
        )
        append(
            IdentityRevision(
                logical_record_id=fact.fact_id,
                revision_id="r1",
                revision_number=1,
                security_id=security,
                effective_from=fact.effective_from,
                provenance=fact.provenance,
                fact=fact,
            )
        )
        member = MembershipFact(
            fact_id=f"membership:{security}",
            revision_id="r1",
            security_id=security,
            effective_from=day(first),
            provenance=provenance(first),
            listing_status="LISTED",
            security_type="COMMON_EQUITY",
        )
        append(
            MembershipRevision(
                logical_record_id=member.fact_id,
                revision_id="r1",
                revision_number=1,
                security_id=security,
                effective_from=member.effective_from,
                provenance=member.provenance,
                fact=member,
            )
        )
        if security == "TEST:DEPART":
            closed = member.model_copy(
                update=dict(
                    revision_id="r2",
                    supersedes_revision_id="r1",
                    effective_to=day(55),
                    provenance=provenance(54),
                )
            )
            append(
                MembershipRevision(
                    logical_record_id=closed.fact_id,
                    revision_id="r2",
                    revision_number=2,
                    supersedes_revision_id="r1",
                    security_id=security,
                    effective_from=closed.effective_from,
                    effective_to=closed.effective_to,
                    provenance=closed.provenance,
                    fact=closed,
                )
            )
            departed = MembershipFact(
                fact_id=f"departure:{security}",
                revision_id="r1",
                security_id=security,
                effective_from=day(55),
                provenance=provenance(54),
                listing_status="DELISTED",
                security_type="COMMON_EQUITY",
            )
            append(
                MembershipRevision(
                    logical_record_id=departed.fact_id,
                    revision_id="r1",
                    revision_number=1,
                    security_id=security,
                    effective_from=departed.effective_from,
                    provenance=departed.provenance,
                    fact=departed,
                )
            )

    def prices(
        index: int,
        number: int = 1,
        known_index: int | None = None,
        revised_close: str | None = None,
    ) -> None:
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        fields = ("security_id", "session_date", "open", "high", "low", "close", "volume")
        writer.writerow(fields)
        for security in securities:
            if (security == "TEST:NEW" and index < 35) or (
                security == "TEST:DEPART" and index >= 55
            ):
                continue
            slope = 2 if security == "TEST:BETA" else 1
            close = 100 + slope * index
            row = dict(
                security_id=security,
                session_date=day(index).isoformat(),
                open=str(close - 1),
                high=str(close + 2),
                low=str(close - 2),
                close=str(close),
                volume=str(1000 + 10 * index),
            )
            row.update((overrides or {}).get((index, security), {}))
            if revised_close is not None and security == "TEST:ALPHA":
                row.update(close=revised_close, high=str(max(close + 2, int(revised_close) + 2)))
            writer.writerow([row[f] for f in fields])
        landing = root / f"prices-{index}-r{number}"
        pipeline = IngestionPipeline(
            RawLanding(landing), FileMetadataRepository(landing / "metadata"), FixtureCSVParser()
        )
        spec = ArtifactSpec(
            source="test-only",
            dataset="test-only-p6-history",
            source_identifier="TEST_ONLY",
            original_filename="TEST_ONLY.csv",
            source_session_date=day(index),
            classification=Classification.TEST_ONLY,
            currency="INR",
            currency_evidence="TEST_ONLY INR units",
        )
        result = pipeline.ingest(TestOnlyBytes(buffer.getvalue().encode()), spec)
        data = assembly.load_prices(landing / "canonical" / result.report.run_id / "canonical.json")
        report = validate(data)
        known = index if known_index is None else known_index
        qprov = provenance(known, checksum(report.to_bytes()))
        quality = QualityRevision(
            logical_record_id=f"quality:{index}",
            revision_id=f"r{number}",
            revision_number=number,
            supersedes_revision_id="r1" if number == 2 else None,
            security_id=None,
            effective_from=day(index),
            provenance=qprov,
            evidence=QualityEvidence(
                source="test-only",
                session_date=day(index),
                report=report,
                report_sha256=qprov.artifact_sha256,
                available_at=qprov.available_at,
                ingested_at=qprov.ingested_at,
                evidence_reference="TEST_ONLY P3 report",
            ),
        )
        append(quality, report.to_bytes())
        if number == 1:
            append(
                SessionRevision(
                    logical_record_id=f"session:{index}",
                    revision_id="r1",
                    revision_number=1,
                    security_id=None,
                    effective_from=day(index),
                    session_date=day(index),
                    status="VERIFIED_TRADING_SESSION",
                    calendar_evidence_reference="TEST_ONLY consecutive artificial sessions",
                    session_close_at=instant(index, 10),
                    provenance=provenance(index),
                )
            )
        for observed in data.records:
            record = PriceRevision(
                logical_record_id=f"bar:{observed.security_id}:{index}",
                revision_id=f"r{number}",
                revision_number=number,
                supersedes_revision_id="r1" if number == 2 else None,
                security_id=observed.security_id,
                effective_from=day(index),
                session_date=day(index),
                price_basis="RAW_UNADJUSTED",
                price_basis_evidence="TEST_ONLY explicitly unadjusted construction",
                currency="INR",
                session_close_at=instant(index, 10),
                quality_key=revision_key(quality),
                values=EODValues(
                    open=observed.open,
                    high=observed.high,
                    low=observed.low,
                    close=observed.close,
                    volume=observed.volume,
                ),
                provenance=provenance(known, result.manifest.sha256),
            )
            append(record, None)
            assembly.lineage.append(
                RecordLineage(
                    record_key=revision_key(record),
                    artifact_id=result.manifest.artifact_id,
                    normalized_record_id=observed.normalized_record_id,
                    source_record_id=observed.record_id,
                    evidence_reference="P2_VERIFIED_NORMALIZATION",
                )
            )
        for scope in data.quarantine_scopes:
            rejected = [
                q for q in data.quarantine if q.source_row_number == scope.source_row_number
            ]
            record = PriceRevision(
                logical_record_id=f"bar:{scope.security_id}:{index}",
                revision_id=f"r{number}",
                revision_number=number,
                supersedes_revision_id="r1" if number == 2 else None,
                security_id=scope.security_id,
                effective_from=day(index),
                session_date=day(index),
                price_basis="RAW_UNADJUSTED",
                price_basis_evidence="TEST_ONLY",
                currency="INR",
                session_close_at=instant(index, 10),
                values=None,
                quality_key=revision_key(quality),
                rejection_reason_codes=tuple(sorted({q.validation_rule for q in rejected})),
                provenance=provenance(known, result.manifest.sha256),
            )
            append(record, None)
            for q in rejected:
                assembly.lineage.append(
                    RecordLineage(
                        record_key=revision_key(record),
                        artifact_id=result.manifest.artifact_id,
                        quarantine_key=checksum(stable_json(q.model_dump(mode="json"))),
                        evidence_reference="TEST_ONLY rejected slot",
                    )
                )

    for index in range(length):
        prices(index)
    if revision:
        index, known_index, close = revision
        prices(index, 2, known_index, close)
    batch = CanonicalBatch(
        classification=Classification.TEST_ONLY,
        definition=UniverseDefinition(
            universe_id="TEST_DYNAMIC_CASH_UNIVERSE",
            classification=Classification.TEST_ONLY,
            evidence_scope="HISTORICAL_EVIDENCE",
            coverage_status="VERIFIED",
            coverage_reference="TEST_ONLY synthetic scope",
        ),
        securities=tuple(
            Security(security_id=s, classification=Classification.TEST_ONLY) for s in securities
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
        stable_json(dict(batch=batch.model_dump(mode="json"), artifact_roots=assembly.roots)),
    )
    publish(
        root / "feature-plan.json",
        stable_json(
            dict(
                history_start=START.isoformat(),
                decisions=[
                    dict(
                        session_date=day(i).isoformat(), knowledge_cutoff=instant(i, 12).isoformat()
                    )
                    for i in range(length)
                ],
                benchmark_security_id="TEST:BENCHMARK",
                benchmark_evidence_reference="TEST_ONLY synthetic benchmark, NOT NIFTY",
            )
        ),
    )
    return batch, assembly.roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct TEST_ONLY history; no real market data")
    parser.add_argument("--data-root", type=Path, default=Path("data/p6-test-only"))
    args = parser.parse_args()
    batch, _ = build_history(local_output(args.data_root))
    print(
        stable_json(
            dict(input_id=batch.input_id, classification=batch.classification, sessions=70)
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
