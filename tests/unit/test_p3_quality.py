"""Constructed TEST_ONLY quality cases are not market evidence or performance."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.acquisition import LocalFileSource
from alphalens_data.ingestion.contracts import ArtifactSpec, CanonicalEOD, Classification
from alphalens_data.ingestion.parsing import FixtureCSVParser
from alphalens_data.ingestion.pipeline import IngestionPipeline
from alphalens_data.ingestion.repository import FileMetadataRepository
from alphalens_data.ingestion.storage import RawLanding, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.quality.engine import validate
from alphalens_data.quality.files import load_run
from alphalens_data.quality.models import (
    ActionEvidence,
    ArtifactEvidence,
    QualityPolicy,
    QualityStatus,
    ReferenceSession,
    TemporalEvidence,
    ValidationInput,
    ValidationSeverity,
)

FIXTURE = Path("tests/fixtures/p3")


@pytest.fixture
def quality_input(tmp_path: Path) -> ValidationInput:
    pipeline = IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path), FixtureCSVParser()
    )
    result = pipeline.ingest(
        LocalFileSource(FIXTURE / "TEST_ONLY.csv"),
        ArtifactSpec.model_validate_json((FIXTURE / "TEST_ONLY.spec.json").read_bytes()),
    )
    assert pipeline.replay(result.manifest.artifact_id)
    return load_run(tmp_path / "canonical" / result.report.run_id / "canonical.json")


def replace_records(data: ValidationInput, records: tuple[CanonicalEOD, ...]) -> ValidationInput:
    """Constructed mutations isolate semantic rules from the separately tested hash gate."""
    evidence = data.artifacts[0].model_copy(
        update={
            "normalized_sha256": checksum(
                stable_json([r.model_dump(mode="json", exclude={"record_id"}) for r in records])
            ),
            "run": None,
        }
    )
    return data.model_copy(update={"records": records, "artifacts": (evidence,)})


def rule_ids(data: ValidationInput) -> set[str]:
    return {i.rule_id for i in validate(data).issues}


def test_summary_and_replay(quality_input: ValidationInput) -> None:
    report = validate(quality_input)
    assert report.to_bytes() == validate(quality_input).to_bytes()
    assert report.status == QualityStatus.DEGRADED
    assert report.summary.record_count == report.summary.valid_record_count == 5
    assert report.summary.unique_security_count == 2
    assert report.summary.zero_volume_count == 1
    assert report.summary.candidate_gap_count == 1
    assert report.summary.confirmed_missing_session_count == 0
    assert report.summary.provenance_complete_count == 5
    assert report.summary.provenance_missing_count == 0
    assert report.summary.valid_record_ratio == 1
    assert report.session_calendar_status == "UNAVAILABLE"
    assert report.universe_input_status == "UNAVAILABLE"
    assert report.summary.price_anomaly_count == 1
    assert report.summary.first_session == date(2024, 1, 1)
    assert report.summary.last_session == date(2024, 1, 4)
    assert tuple(i.rule_id for i in report.issues) == tuple(
        sorted(i.rule_id for i in report.issues)
    )
    issue = next(i for i in report.issues if i.rule_id == "EXTREME_RETURN")
    assert issue.severity == ValidationSeverity.WARNING
    assert issue.action_status == "ACTION_DATA_UNAVAILABLE"
    assert issue.artifact_id and issue.source and issue.record_ids and issue.normalized_record_ids
    assert issue.original_row_numbers == (4,)


@pytest.mark.parametrize(
    ("change", "rule"),
    [
        ({"open": Decimal("0")}, "P2_NUMERIC_OPEN"),
        ({"close": Decimal("-1")}, "P2_NUMERIC_CLOSE"),
        ({"high": Decimal("99")}, "P2_OHLC_HIGH_OPEN"),
        ({"close": Decimal("120")}, "P2_OHLC_HIGH_CLOSE"),
        ({"low": Decimal("120")}, "P2_OHLC_HIGH_LOW"),
        ({"low": Decimal("101")}, "P2_OHLC_LOW_OPEN"),
        ({"close": Decimal("80")}, "P2_OHLC_LOW_CLOSE"),
        ({"volume": -1}, "P2_VOLUME"),
        ({"security_id": " BAD "}, "P2_REQUIRED_IDENTIFIER"),
        ({"session_date": date(2099, 1, 1)}, "FUTURE_SESSION"),
    ],
)
def test_reuses_p2_hard_invariants(
    quality_input: ValidationInput,
    change: dict[str, Any],
    rule: str,
) -> None:
    r = quality_input.records[0].model_copy(update=change)
    data = replace_records(quality_input, (r,) + quality_input.records[1:])
    report = validate(data)
    assert rule in {i.rule_id for i in report.issues}
    assert report.status == QualityStatus.REJECTED
    assert any(s.status == QualityStatus.REJECTED for s in report.sessions)


def test_duplicates_and_conflicting_revisions(quality_input: ValidationInput) -> None:
    r = quality_input.records[0]
    data = replace_records(quality_input, quality_input.records + (r,))
    assert "DUPLICATE_SECURITY_SESSION" in rule_ids(data)
    assert validate(data).summary.duplicate_count == 1
    changed = r.model_copy(update={"close": Decimal("101")})
    data = replace_records(quality_input, quality_input.records + (changed,))
    assert "CONFLICTING_REVISION" in rule_ids(data)
    # No duplicate winner, no silent filtering.
    assert validate(data).summary.valid_record_count == 4
    assert len(data.records) == 6


def test_chronology_and_original_input_hash(quality_input: ValidationInput) -> None:
    data = replace_records(quality_input, tuple(reversed(quality_input.records)))
    assert "UNSORTED_SESSIONS" in rule_ids(data)
    assert validate(data).input_sha256 != validate(quality_input).input_sha256
    assert validate(data).to_bytes() == validate(data).to_bytes()


def test_calendar_does_not_invent_missing_sessions(quality_input: ValidationInput) -> None:
    assert "CONFIRMED_MISSING_SESSION" not in rule_ids(quality_input)
    ref = ReferenceSession(
        security_id="TEST:A",
        session_date=date(2024, 1, 3),
        status="NON_TRADING",
        evidence_reference="TEST_ONLY holiday",
    )
    data = quality_input.model_copy(update={"reference_sessions": (ref,)})
    assert "NON_TRADING_SESSION" in rule_ids(data)
    assert validate(data).summary.confirmed_missing_session_count == 0
    trading = ref.model_copy(update={"status": "TRADING"})
    data = data.model_copy(update={"reference_sessions": (trading,)})
    report = validate(data)
    assert report.summary.confirmed_missing_session_count == 1
    assert report.session_calendar_status == "PARTIALLY_VERIFIED"
    assert report.status == QualityStatus.REJECTED
    assert not report.dataset_blocked
    assert (
        next(s for s in report.sessions if s.session_date == date(2024, 1, 3)).status == "REJECTED"
    )


@pytest.mark.parametrize(
    "status",
    [
        "KNOWN_CORPORATE_ACTION",
        "POSSIBLE_CORPORATE_ACTION",
        "NO_ACTION_EVIDENCE",
    ],
)
def test_action_evidence_never_adjusts_prices(quality_input: ValidationInput, status: str) -> None:
    action = ActionEvidence.model_validate(
        {
            "security_id": "TEST:A",
            "session_date": "2024-01-04",
            "status": status,
            "evidence_reference": "TEST_ONLY action",
        }
    )
    data = quality_input.model_copy(update={"action_evidence": (action,)})
    issue = next(i for i in validate(data).issues if i.rule_id == "EXTREME_RETURN")
    assert issue.action_status == status
    assert issue.severity == "WARNING"
    assert data.records[2].close == Decimal("202")


def test_configured_anomalies(quality_input: ValidationInput) -> None:
    policy = QualityPolicy(
        absolute_return=Decimal("2"),
        volume_multiple=Decimal("30"),
        repeated_ohlc_sessions=2,
        high_low_ratio=Decimal("1.01"),
    )
    data = quality_input.model_copy(update={"policy": policy})
    rules = rule_ids(data)
    assert "EXTREME_RETURN" not in rules
    assert "VOLUME_SPIKE" not in rules
    assert {"REPEATED_OHLC", "EXTREME_RANGE", "ZERO_VOLUME"} <= rules


@pytest.mark.parametrize("field", ["isin", "symbol"])
def test_simultaneous_identifier_conflict(quality_input: ValidationInput, field: str) -> None:
    r = quality_input.records[3].model_copy(
        update={field: getattr(quality_input.records[0], field)}
    )
    data = replace_records(
        quality_input, quality_input.records[:3] + (r,) + quality_input.records[4:]
    )
    report = validate(data)
    assert "IDENTIFIER_CONFLICT" in {i.rule_id for i in report.issues}
    assert report.summary.valid_record_count == 3


def test_provenance_gaps_and_checksums(quality_input: ValidationInput) -> None:
    r = quality_input.records[0].model_copy(update={"normalized_record_id": "0" * 64})
    data = replace_records(quality_input, (r,) + quality_input.records[1:])
    assert validate(data).summary.provenance_missing_count == 1
    assert "PROVENANCE" in rule_ids(data)
    evidence = quality_input.artifacts[0].model_copy(update={"observed_sha256": "0" * 64})
    data = quality_input.model_copy(update={"artifacts": (evidence,)})
    assert validate(data).dataset_blocked
    assert "CHECKSUM" in rule_ids(data)
    assert validate(data).summary.provenance_missing_count == 5
    missing = ArtifactEvidence(manifest=evidence.manifest)
    data = data.model_copy(update={"artifacts": (missing,)})
    assert validate(data).summary.provenance_complete_count == 0


def test_metadata_versions_range_and_classification(quality_input: ValidationInput) -> None:
    r = quality_input.records[0].model_copy(update={"source": "wrong-source"})
    assert "METADATA" in rule_ids(replace_records(quality_input, (r,) + quality_input.records[1:]))
    r = quality_input.records[0].model_copy(
        update={"classification": Classification.RESEARCH_FIXTURE}
    )
    assert "CLASSIFICATION" in rule_ids(
        replace_records(quality_input, (r,) + quality_input.records[1:])
    )
    data = quality_input.model_copy(
        update={"start_session": date(2024, 2, 1), "end_session": date(2024, 1, 1)}
    )
    assert {"DATE_RANGE", "OUTSIDE_DATE_RANGE"} <= rule_ids(data)
    assert validate(data).dataset_blocked
    assert "EMPTY_DATASET" in rule_ids(ValidationInput())


def test_duplicate_artifact_content(quality_input: ValidationInput) -> None:
    evidence = quality_input.artifacts[0]
    other = evidence.model_copy(
        update={
            "manifest": evidence.manifest.model_copy(
                update={
                    "artifact_id": "a" * 64,
                }
            ),
            "normalized_sha256": checksum(stable_json([])),
            "run": None,
        }
    )
    data = quality_input.model_copy(update={"artifacts": (evidence, other)})
    assert "DUPLICATE_ARTIFACT_CONTENT" in rule_ids(data)


def test_known_temporal_evidence_and_use_before_available(quality_input: ValidationInput) -> None:
    r = quality_input.records[0]
    evidence = TemporalEvidence(
        record_id=r.record_id,
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        published_at=datetime(2024, 1, 3, tzinfo=UTC),
        effective_from=date(2024, 1, 3),
        effective_to=date(2024, 1, 2),
        evidence_reference="TEST_ONLY impossible times",
    )
    data = quality_input.model_copy(
        update={"temporal_evidence": (evidence,), "decision_time": datetime(2024, 1, 1, tzinfo=UTC)}
    )
    assert {"TEMPORAL_INVERSION", "USE_BEFORE_AVAILABLE"} <= rule_ids(data)
    data = data.model_copy(update={"temporal_evidence": (evidence, evidence)})
    assert "REFERENCE_CONFLICT" in rule_ids(data)


def test_valid_gate_requires_evidenced_readiness(quality_input: ValidationInput) -> None:
    r = quality_input.records[0]
    data = replace_records(quality_input, (r,))
    evidence = TemporalEvidence(
        record_id=r.record_id,
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        evidence_reference="TEST_ONLY bar availability",
    )
    data = data.model_copy(update={"temporal_evidence": (evidence,)})
    assert validate(data).status == "VALID"
    assert validate(data).universe_input_status == "PARTIALLY_VERIFIED"


def test_p2_quarantine_consumed_without_filtering(tmp_path: Path) -> None:
    source = tmp_path / "TEST_ONLY_bad.csv"
    source.write_text(
        "symbol,session_date,open,high,low,close,volume\n"
        "TEST,2024-01-01,100,110,90,100,100\n"
        "TEST,not-a-date,100,110,90,100,100\n",
        encoding="utf-8",
    )
    pipeline = IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path), FixtureCSVParser()
    )
    result = pipeline.ingest(
        LocalFileSource(source),
        ArtifactSpec.model_validate_json((FIXTURE / "TEST_ONLY.spec.json").read_bytes()),
    )
    data = load_run(tmp_path / "canonical" / result.report.run_id / "canonical.json")
    report = validate(data)
    assert report.summary.quarantined_record_count == 1
    assert report.summary.record_count == 1
    assert {"PARTIAL_POPULATION", "P2_SESSION_DATE"} <= rule_ids(data)
    assert report.status == "REJECTED"
    assert report.to_bytes() == validate(data).to_bytes()


def test_canonical_values_cannot_disagree_with_raw_replay(tmp_path: Path) -> None:
    pipeline = IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path), FixtureCSVParser()
    )
    result = pipeline.ingest(
        LocalFileSource(FIXTURE / "TEST_ONLY.csv"),
        ArtifactSpec.model_validate_json((FIXTURE / "TEST_ONLY.spec.json").read_bytes()),
    )
    canonical = tmp_path / "canonical" / result.report.run_id / "canonical.json"
    payload = canonical.read_bytes().replace(b'"close":"202"', b'"close":"201"')
    canonical.write_bytes(payload)
    with pytest.raises(DataContractError, match="P2_REPLAY_OUTPUT_MISMATCH"):
        load_run(canonical)


def test_missing_columns_quarantine_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "TEST_ONLY_missing.csv"
    source.write_text("symbol,session_date\nTEST,2024-01-01\n", encoding="utf-8")
    pipeline = IngestionPipeline(
        RawLanding(tmp_path), FileMetadataRepository(tmp_path), FixtureCSVParser()
    )
    result = pipeline.ingest(
        LocalFileSource(source),
        ArtifactSpec.model_validate_json((FIXTURE / "TEST_ONLY.spec.json").read_bytes()),
    )
    data = load_run(tmp_path / "canonical" / result.report.run_id / "canonical.json")
    report = validate(data)
    assert report.status == "REJECTED"
    assert {"EMPTY_DATASET", "P2_INVALID_HEADER"} <= rule_ids(data)


def test_cli_replay_and_malformed_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from alphalens_data.quality.cli import main

    root = tmp_path / "data" / "TEST_ONLY"
    spec = ArtifactSpec.model_validate_json((FIXTURE / "TEST_ONLY.spec.json").read_bytes())
    pipeline = IngestionPipeline(
        RawLanding(root), FileMetadataRepository(root / "metadata"), FixtureCSVParser()
    )
    result = pipeline.ingest(LocalFileSource(FIXTURE / "TEST_ONLY.csv"), spec)
    canonical = root / "canonical" / result.report.run_id / "canonical.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["alphalens-validate", str(canonical)])
    assert main() == 0
    report_path = canonical.parent / "validation-report.json"
    original = report_path.read_bytes()
    assert main() == 0
    assert report_path.read_bytes() == original
    canonical.write_text('[{"bad":"TEST_ONLY malformed canonical metadata"}]', encoding="utf-8")
    failure_path = root / "invalid-report.json"
    monkeypatch.setattr(
        "sys.argv", ["alphalens-validate", str(canonical), "--output", str(failure_path)]
    )
    assert main() == 2
    assert b'"severity":"FATAL"' in failure_path.read_bytes()
    assert "TEST_ONLY malformed canonical metadata" not in capsys.readouterr().out
