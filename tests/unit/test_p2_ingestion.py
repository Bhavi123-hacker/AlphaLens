"""Constructed TEST_ONLY data: infrastructure correctness, never market performance."""

import hashlib
import json
import logging
import stat
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.acquisition import LocalFileSource
from alphalens_data.ingestion.contracts import ArtifactSpec, Classification, Versions
from alphalens_data.ingestion.parsing import FixtureCSVParser, ParsedRow
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, publish

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/p2/TEST_ONLY.csv"
SPEC = FIXTURE.with_name("TEST_ONLY.spec.json")
HEADER = b"symbol,session_date,open,high,low,close,volume\n"
GOOD = b"TEST_ALPHA,2026-01-02,10.00,12.00,9.00,11.50,100\n"


class MemorySource:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def acquire(self) -> bytes:
        return self.payload


@pytest.fixture
def spec() -> ArtifactSpec:
    return ArtifactSpec.model_validate_json(SPEC.read_bytes())


@pytest.fixture
def pipeline(tmp_path: Path) -> IngestionPipeline:
    return IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path / "metadata"), FixtureCSVParser()
    )


def test_manifest_checksum_idempotency_and_raw_revision(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    first = pipeline.ingest(LocalFileSource(FIXTURE), spec)
    second = pipeline.ingest(LocalFileSource(FIXTURE), spec)
    assert not first.duplicate and second.duplicate
    assert first.manifest == second.manifest
    assert first.report == second.report
    manifest = first.manifest
    assert manifest.sha256 == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert manifest.byte_size == FIXTURE.stat().st_size
    assert "raw/test-fixture/eod-cash/2026/01/02/" in manifest.raw_path
    changed = pipeline.ingest(MemorySource(FIXTURE.read_bytes().replace(b"150", b"151")), spec)
    assert changed.manifest.artifact_id != manifest.artifact_id
    assert changed.manifest.prior_revision_ids == (manifest.artifact_id,)
    assert pipeline.landing.read(manifest) == FIXTURE.read_bytes()
    assert len(list((pipeline.landing.root / "manifests").glob("*.json"))) == 2
    with pytest.raises(DataContractError, match="IMMUTABLE_FILE_CONFLICT"):
        publish(pipeline.landing.resolve(manifest.raw_path), b"overwrite")


def test_replay_provenance_exact_parquet_and_missing_metadata(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    result = pipeline.ingest(LocalFileSource(FIXTURE), spec)
    replayed = pipeline.replay(result.manifest.artifact_id)
    assert replayed.records == result.records
    assert replayed.report == result.report
    assert [r.symbol for r in result.records] == ["TEST_ALPHA", "TEST_BETA"]
    parsed = FixtureCSVParser().parse(FIXTURE.read_bytes())
    for record in result.records:
        normalized = json.loads(
            (
                pipeline.landing.root / "canonical" / result.report.run_id / "normalized.json"
            ).read_bytes()
        )
        assert (
            next(r for r in normalized if r["normalized_record_id"] == record.normalized_record_id)[
                "artifact_id"
            ]
            == result.manifest.artifact_id
        )
        row = next(r for r in parsed if r.row_number == record.source_row_number)
        assert record.artifact_id == result.manifest.artifact_id
        assert record.raw_sha256 == result.manifest.sha256
        assert record.source == result.manifest.spec.source
        assert record.versions.parser == FixtureCSVParser.version
        assert (
            record.source_row_sha256
            == hashlib.sha256(
                json.dumps(
                    row.original, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ).hexdigest()
        )
        assert record.normalized_record_id != record.record_id
        assert record.classification == Classification.TEST_ONLY
        assert not record.production_claims_permitted
        assert record.isin is record.available_at is record.published_at is None
        assert record.session_close_at is record.adjustment_basis is None
        assert record.currency == "INR"
        assert record.identity_basis == "SOURCE_SCOPED_SYMBOL"
    table = pq.read_table(
        pipeline.landing.root / "canonical" / result.report.run_id / "canonical.parquet"
    )
    assert table.schema.metadata[b"classification"] == b"TEST_ONLY"
    assert table.to_pylist()[0]["close"] == result.records[0].close
    assert table.to_pylist()[0]["volume"] == 0


@pytest.mark.parametrize(
    ("row", "rule"),
    [
        (b"TEST_ALPHA,2026-01-02,10,9,8,11,1\n", "OHLC_HIGH_OPEN"),
        (b"TEST_ALPHA,2026-01-02,10,12,11,11,1\n", "OHLC_LOW_OPEN"),
        (b"TEST_ALPHA,2026-01-02,10,12,13,11,1\n", "OHLC_HIGH_LOW"),
        (b"TEST_ALPHA,2026-01-02,10,12,9,11,-1\n", "VOLUME"),
        (b"TEST_ALPHA,2026-01-02,10,12,9,11,1.5\n", "VOLUME"),
        (b"TEST_ALPHA,2026-01-02,bad,12,9,11,1\n", "NUMERIC_OPEN"),
        (b"TEST_ALPHA,2026-01-02,NaN,12,9,11,1\n", "NUMERIC_OPEN"),
        (b"TEST_ALPHA,2026-02-30,10,12,9,11,1\n", "SESSION_DATE"),
        (b"TEST_ALPHA,20260102,10,12,9,11,1\n", "SESSION_DATE"),
        (b",2026-01-02,10,12,9,11,1\n", "REQUIRED_IDENTIFIER"),
        (b"TEST_ALPHA,2026-01-02,10,12,9,11\n", "ROW_WIDTH_MISMATCH"),
        (b"TEST_ALPHA,2026-01-02,0.0000000000000000001,12,9,11,1\n", "NUMERIC_OPEN"),
        (b"TEST_ALPHA,2026-01-02,10,12,9,11,9223372036854775808\n", "VOLUME"),
    ],
)
def test_invalid_rows_are_preserved_and_replayed(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
    row: bytes,
    rule: str,
) -> None:
    result = pipeline.ingest(
        MemorySource(HEADER + row + GOOD.replace(b"TEST_ALPHA", b"TEST_GOOD")), spec
    )
    assert len(result.records) == 1
    assert result.report.status == "DEGRADED"
    assert result.report.quarantined_row_count == 1
    error = next(r for r in result.quarantine if r.validation_rule == rule)
    assert error.source_row_number == 2
    assert error.original_row == tuple(row.decode().strip().split(","))
    assert error.timestamp == result.manifest.acquired_at
    assert error.artifact_id == result.manifest.artifact_id
    assert error.reason
    assert pipeline.replay(result.manifest.artifact_id).quarantine == result.quarantine


def test_duplicate_group_quarantined_without_arbitrary_winner(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    result = pipeline.ingest(MemorySource(HEADER + GOOD + GOOD.replace(b"100", b"200")), spec)
    assert not result.records
    assert result.report.status == "UNAVAILABLE"
    assert result.report.quarantined_row_count == 2
    assert {q.validation_rule for q in result.quarantine} == {"DUPLICATE_SECURITY_SESSION_VERSION"}


@pytest.mark.parametrize(
    "payload", [b"", b"\xff", HEADER, b"symbol,open\nTEST,1\n", HEADER + b'"unterminated']
)
def test_malformed_artifacts_remain_in_raw_and_quarantine(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
    payload: bytes,
) -> None:
    result = pipeline.ingest(MemorySource(payload), spec)
    assert result.quarantine
    assert result.report.status == "UNAVAILABLE"
    assert pipeline.landing.read(result.manifest) == payload


def test_tampering_versions_and_classification_fail_closed(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    result = pipeline.ingest(MemorySource(HEADER + GOOD), spec)
    with pytest.raises(ValidationError, match="production capture is disabled"):
        ArtifactSpec.model_validate({**spec.model_dump(), "classification": "PRODUCTION"})
    with pytest.raises(ValidationError, match="rights"):
        ArtifactSpec.model_validate({**spec.model_dump(), "classification": "RESEARCH_FIXTURE"})
    with pytest.raises(DataContractError, match="DUPLICATE_METADATA_CONFLICT"):
        pipeline.ingest(
            MemorySource(HEADER + GOOD),
            spec.model_copy(update={"currency": None, "currency_evidence": None}),
        )
    pipeline.parser.version = "changed.parser.v2"  # replay must not silently change implementation
    with pytest.raises(DataContractError, match="REPLAY_VERSION_MISMATCH"):
        pipeline.replay(result.manifest.artifact_id)
    pipeline.parser.version = FixtureCSVParser.version
    raw_path = pipeline.landing.resolve(result.manifest.raw_path)
    raw_path.chmod(stat.S_IREAD | stat.S_IWRITE)
    raw_path.write_bytes(b"corrupt")
    with pytest.raises(DataContractError, match="CHECKSUM_OR_SIZE_MISMATCH"):
        pipeline.replay(result.manifest.artifact_id)


def test_source_and_parser_abstraction_and_unknown_currency(
    tmp_path: Path,
    spec: ArtifactSpec,
) -> None:
    class OtherParser:
        version = "other-format.v1"

        def parse(self, payload: bytes) -> tuple[ParsedRow, ...]:
            assert payload == b"TEST_ONLY:another-format"
            return FixtureCSVParser().parse(HEADER + GOOD)

    pipe = IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path / "state"), OtherParser()
    )
    other = spec.model_copy(update={"source": "other", "currency": None, "currency_evidence": None})
    result = pipe.ingest(MemorySource(b"TEST_ONLY:another-format"), other)
    assert result.records[0].currency is None
    assert result.records[0].source == "other"
    assert pipe.replay(result.manifest.artifact_id).records == result.records


def test_logs_contain_safe_structured_events(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="alphalens_data.ingestion")
    result = pipeline.ingest(LocalFileSource(FIXTURE), spec)
    pipeline.ingest(LocalFileSource(FIXTURE), spec)
    pipeline.replay(result.manifest.artifact_id)
    names = {json.loads(r.message)["event"] for r in caplog.records}
    assert {
        "ingestion_started",
        "artifact_acquired",
        "checksum_generated",
        "duplicate_detected",
        "parsing_complete",
        "normalization_complete",
        "replay_result",
    } <= names
    assert "TEST_ALPHA" not in caplog.text


def test_capture_lock_and_path_safety(pipeline: IngestionPipeline, spec: ArtifactSpec) -> None:
    with pipeline.landing.lock(), pytest.raises(DataContractError, match="CAPTURE_BUSY"):
        pipeline.landing.capture(HEADER + GOOD, spec, Versions(parser=FixtureCSVParser.version))
    with pytest.raises(DataContractError, match="ESCAPES_ROOT"):
        pipeline.landing.resolve("../escape")


def test_duplicate_across_recovered_landing_uses_first_capture_metadata(
    tmp_path: Path,
    spec: ArtifactSpec,
) -> None:
    repository = FileMetadataRepository(tmp_path / "metadata")
    first = IngestionPipeline(
        RawLanding(tmp_path / "first"), repository, FixtureCSVParser()
    ).ingest(LocalFileSource(FIXTURE), spec)
    recovered = IngestionPipeline(
        RawLanding(tmp_path / "recovered"), repository, FixtureCSVParser()
    )
    result = recovered.ingest(LocalFileSource(FIXTURE), spec)
    assert result.duplicate
    assert result.manifest == first.manifest
    assert result.report == first.report
    assert recovered.replay(result.manifest.artifact_id).records == first.records


def test_bad_duplicate_does_not_select_valid_sibling(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    result = pipeline.ingest(MemorySource(HEADER + GOOD + GOOD.replace(b"100", b"-1")), spec)
    assert not result.records
    assert result.report.quarantined_row_count == 2
    assert (
        sum(q.validation_rule == "DUPLICATE_SECURITY_SESSION_VERSION" for q in result.quarantine)
        == 2
    )
    assert any(q.validation_rule == "VOLUME" for q in result.quarantine)


def test_output_corruption_is_detected_by_replay(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    result = pipeline.ingest(LocalFileSource(FIXTURE), spec)
    path = pipeline.landing.root / "canonical" / result.report.run_id / "normalized.json"
    path.write_bytes(b"[]")
    with pytest.raises(DataContractError, match="REPLAY_OUTPUT_MISMATCH"):
        pipeline.replay(result.manifest.artifact_id)


def test_research_classification_and_currency_evidence(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    research = ArtifactSpec.model_validate(
        {
            **spec.model_dump(),
            "classification": "RESEARCH_FIXTURE",
            "rights_evidence": "TEST_ONLY acceptance reference",
        }
    )
    result = pipeline.ingest(MemorySource(HEADER + GOOD), research)
    assert result.records[0].classification == Classification.RESEARCH_FIXTURE
    assert not result.report.production_claims_permitted
    with pytest.raises(ValidationError, match="Currency"):
        ArtifactSpec.model_validate({**spec.model_dump(), "currency_evidence": None})
    with pytest.raises(ValidationError, match="request URL"):
        ArtifactSpec.model_validate(
            {**spec.model_dump(), "source_identifier": "https://invalid.test"}
        )


def test_optional_identifiers_are_preserved_without_fabrication(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    header = b"security_id,session_date,open,high,low,close,volume,isin,series\n"
    row = b"TEST_SECURITY,2026-01-02,1e1,12,9,11,0,TEST_ISIN,TEST_SERIES\n"
    result = pipeline.ingest(MemorySource(header + row), spec)
    record = result.records[0]
    assert record.security_id == "TEST_SECURITY"
    assert record.identity_basis == "SOURCE_SECURITY_ID"
    assert record.symbol is None
    assert record.isin == "TEST_ISIN"
    assert record.series == "TEST_SERIES"
    assert record.open == 10
    assert record.source_filename == spec.original_filename


def test_optional_identifier_errors_quarantine_instead_of_aborting(
    pipeline: IngestionPipeline,
    spec: ArtifactSpec,
) -> None:
    header = b"security_id,symbol,session_date,open,high,low,close,volume\n"
    row = b"TEST_ID, PADDED ,2026-01-02,10,12,9,11,0\n"
    result = pipeline.ingest(MemorySource(header + row), spec)
    assert result.report.status == "UNAVAILABLE"
    assert result.quarantine[0].validation_rule == "IDENTIFIER_FORMAT"
