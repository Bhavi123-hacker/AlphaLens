"""TEST_ONLY constructed CSV edge cases; never historical market data/performance."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from alphalens_data.providers.mendeley import ResearchArtifact, parse_sample, read_artifact
from conftest import make_test_only_price, make_test_only_provenance

START = date(2000, 1, 3)
END = date(2000, 1, 4)
HEADER = ",open,high,low,close,adjclose,volume,ticker\r\n"
TEST_ONLY_ROW = "2000-01-03,10,12,9,11,10,5,TEST_ONLY.NS\r\n"


def make_test_only_artifact(payload: bytes) -> ResearchArtifact:
    # Metadata skeleton only; every constructed input is explicitly TEST_ONLY.
    catalog = Path(__file__).resolve().parents[2] / "docs/data/research-sample-manifest.json"
    data = json.loads(catalog.read_text(encoding="utf-8"))["artifacts"][0]
    data.update(
        dataset_id="TEST_ONLY",
        doi="TEST_ONLY_DOI",
        title="TEST_ONLY constructed fixture",
        symbol="TEST_ONLY.NS",
        raw_relative_path="TEST_ONLY.csv",
        original_filename="TEST_ONLY.csv",
        byte_size=len(payload),
        sha256=checksum(payload),
        repository_sha256=checksum(payload),
        origin="TEST_ONLY",
    )
    return ResearchArtifact.model_validate(data)


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("2000-01-03", "2000-02-30", "MALFORMED_SESSION_DATE"),
        ("2000-01-03", "03/01/2000", "MALFORMED_SESSION_DATE"),
        (",10,12", ",NaN,12", "MALFORMED_NUMERIC_VALUE"),
        (",10,12", ",bad,12", "MALFORMED_NUMERIC_VALUE"),
        (",10,12", ",1_0,12", "MALFORMED_NUMERIC_VALUE"),
        (",10,12", ",13,12", "OHLC outside"),
        (",9,11", ",13,11", "OHLC outside"),
        (",5,TEST_ONLY", ",-1,TEST_ONLY", "INVALID_VOLUME"),
        (",5,TEST_ONLY", ",1.5,TEST_ONLY", "INVALID_VOLUME"),
        ("TEST_ONLY.NS", "TEST_ONLY_WRONG.NS", "SOURCE_SYMBOL_MISMATCH"),
    ],
)
def test_reject_invalid_test_only_input(old: str, new: str, error: str) -> None:
    payload = (HEADER + TEST_ONLY_ROW.replace(old, new)).encode()
    with pytest.raises((DataContractError, ValidationError), match=error):
        parse_sample(payload, make_test_only_artifact(payload), START, END)


def test_duplicate_sessions_fail_instead_of_silently_disappearing() -> None:
    payload = (HEADER + TEST_ONLY_ROW * 2).encode()
    with pytest.raises(DataContractError, match="DUPLICATE_SECURITY_SESSION"):
        parse_sample(payload, make_test_only_artifact(payload), START, END)


def test_missing_values_are_explicit_and_order_is_chronological() -> None:
    missing = "2000-01-04,,,,,,,TEST_ONLY.NS\r\n"
    payload = (HEADER + missing + TEST_ONLY_ROW).encode()
    result = parse_sample(payload, make_test_only_artifact(payload), START, END)
    assert not result.input_ordered
    assert len(result.rows) == len(result.unavailable) == 1
    assert result.unavailable[0].session_date == END
    assert result.unavailable[0].state == "UNAVAILABLE"
    assert result.rows[0].bar.provenance.origin == "TEST_ONLY"


def test_raw_tampering_and_path_escape_are_rejected(tmp_path: Path) -> None:
    payload = (HEADER + TEST_ONLY_ROW).encode()
    artifact = make_test_only_artifact(payload)
    (tmp_path / "TEST_ONLY.csv").write_bytes(payload + b"\n")
    with pytest.raises(DataContractError, match="CHECKSUM_OR_SIZE"):
        read_artifact(tmp_path, artifact)
    escaped = artifact.model_copy(update={"raw_relative_path": "../TEST_ONLY.csv"})
    with pytest.raises(DataContractError, match="ESCAPES_ROOT"):
        read_artifact(tmp_path, escaped)


def test_null_close_requires_new_version_and_cannot_claim_known_availability() -> None:
    with pytest.raises(ValidationError, match="requires p1.v2"):
        make_test_only_price(session_close_at=None)
    with pytest.raises(ValidationError, match="requires evidenced session close"):
        make_test_only_price(
            session_close_at=None,
            provenance=make_test_only_provenance(schema_version="p1.v2"),
        )
    provenance = make_test_only_provenance(
        schema_version="p1.v2",
        available_at=None,
        published_at=None,
        availability_basis="UNKNOWN",
        availability_evidence=None,
        ingested_at=datetime(2000, 1, 4, tzinfo=UTC),
    )
    result = make_test_only_price(session_close_at=None, provenance=provenance)
    assert result.session_close_at is None
    with pytest.raises(ValidationError, match="after acquisition"):
        make_test_only_price(
            session_close_at=None, session_date=date(2000, 1, 5), provenance=provenance
        )
