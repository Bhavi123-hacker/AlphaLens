"""Build ignored P2/P3 evidence for the committed TEST_ONLY P4 scenarios.

This orchestrates existing ingestion/quality logic. It acquires no market data.
"""

import argparse
import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from alphalens_data.ingestion.contracts import ArtifactSpec
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.engine import validate
from alphalens_data.quality.files import load_run, local_output
from alphalens_data.universe.models import QualityEvidence, UniverseInput

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/p4"


class TestOnlyBytes:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def acquire(self) -> bytes:
        return self.payload


def build_fixture(root: Path) -> UniverseInput:
    root = root.resolve()
    data = UniverseInput.model_validate_json((FIXTURE / "TEST_ONLY.universe.json").read_bytes())
    evidence_bytes = (FIXTURE / "TEST_ONLY.evidence.txt").read_bytes()
    if any(
        f.provenance.artifact_sha256 != checksum(evidence_bytes)
        for f in (*data.identities, *data.memberships)
    ):
        raise ValueError("TEST_ONLY evidence checksum mismatch")
    grouped: dict[date, list[tuple[str, ...]]] = defaultdict(list)
    header: tuple[str, ...] = ()
    for row in FixtureCSVParser().parse((FIXTURE / "TEST_ONLY.prices.csv").read_bytes()):
        if row.error:
            raise ValueError("TEST_ONLY fixture parser failure")
        fields = dict(row.fields)
        grouped[date.fromisoformat(fields["session_date"])].append(row.original)
        header = tuple(fields)
    reports: list[QualityEvidence] = []
    for session, rows in sorted(grouped.items()):
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(header)
        writer.writerows(rows)
        landing = root / session.isoformat()
        pipeline = IngestionPipeline(
            RawLanding(landing), FileMetadataRepository(landing / "metadata"), FixtureCSVParser()
        )
        spec = ArtifactSpec.model_validate(
            {
                "source": "test-only",
                "dataset": "test-universe",
                "source_identifier": "TEST_ONLY constructed per-session P4 quality",
                "source_session_date": session,
                "original_filename": "TEST_ONLY.csv",
                "classification": "TEST_ONLY",
                "currency": "INR",
                "currency_evidence": "TEST_ONLY constructed units",
            }
        )
        result = pipeline.ingest(TestOnlyBytes(buffer.getvalue().encode()), spec)
        pipeline.replay(result.manifest.artifact_id)
        canonical = landing / "canonical" / result.report.run_id / "canonical.json"
        report = validate(load_run(canonical))
        publish(canonical.parent / "validation-report.json", report.to_bytes())
        # These knowledge times are explicitly constructed fixture evidence, not inferred
        # publication/availability of real P2 observations. Canonical P2 nulls stay null.
        reports.append(
            QualityEvidence(
                source=spec.source,
                session_date=session,
                report=report,
                report_sha256=checksum(report.to_bytes()),
                available_at=datetime(session.year, session.month, session.day, 11, tzinfo=UTC),
                ingested_at=result.manifest.acquired_at,
                evidence_reference=f"TEST_ONLY_P3_REPORT:{report.input_sha256}",
            )
        )
    combined = UniverseInput.model_validate({**data.model_dump(), "quality": tuple(reports)})
    publish(root / "universe-input.json", stable_json(combined.model_dump(mode="json")))
    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct TEST_ONLY P4 development evidence")
    parser.add_argument("--data-root", type=Path, default=Path("data/p4-test-only"))
    args = parser.parse_args()
    data = build_fixture(local_output(args.data_root))
    print(
        stable_json(
            {
                "classification": data.definition.classification,
                "quality_sessions": len(data.quality),
                "production_claims_permitted": False,
            }
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
