"""TEST_ONLY synthetic bytes/bars for public acquisition and fail-closed adapters.

No test output is real TejHQ history or a market-performance claim.
"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.acquire_tejhq_research import acquire_one
from scripts.ingest_tejhq_research import previous_context

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import ArtifactSpec, Classification, Versions
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.storage import RawLanding, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.tejhq import iter_batches, parse_batch
from alphalens_data.quality.engine import validate
from alphalens_data.quality.models import ArtifactEvidence, ValidationInput
from alphalens_data.universe.models import UniverseDefinition


def synthetic_row(day: int = 4, isin: str | None = None) -> dict[str, Any]:
    return {
        "date": date(2010, 1, day),
        "symbol": "TEST_ONLY",
        "series": "EQ",
        "isin": isin,
        "name": "TEST_ONLY constructed company",
        "open": 10.1,
        "high": 11.0,
        "low": 9.0,
        "close": 10.2,
        "volume": 100,
    }


def synthetic_manifest(tmp_path: Path) -> tuple[RawLanding, Any]:
    landing = RawLanding(tmp_path / "raw")
    spec = ArtifactSpec(
        source="tejhq",
        dataset="test-only-adapter",
        source_identifier="TEST_ONLY",
        original_filename="TEST_ONLY.parquet",
        classification=Classification.TEST_ONLY,
    )
    manifest, _ = landing.capture(
        b"TEST_ONLY immutable bytes", spec, Versions(parser="tejhq.parquet.v1")
    )
    return landing, manifest


def test_research_only_requires_rights_and_never_clears_production() -> None:
    base = {
        "source": "tejhq",
        "dataset": "test-only-contract",
        "source_identifier": "TEST_ONLY",
        "original_filename": "TEST_ONLY",
        "classification": "RESEARCH_ONLY",
    }
    with pytest.raises(ValueError, match="rights"):
        ArtifactSpec.model_validate(base)
    spec = ArtifactSpec.model_validate(base | {"rights_evidence": "TEST_ONLY authorization"})
    assert spec.classification == Classification.RESEARCH_ONLY
    universe = UniverseDefinition(
        universe_id="RESEARCH_DYNAMIC_NSE_CASH",
        classification=Classification.RESEARCH_ONLY,
        evidence_scope="HISTORICAL_EVIDENCE",
        coverage_status="UNKNOWN",
        coverage_reference="TEST_ONLY classification propagation test, not historical evidence",
    )
    assert universe.coverage_status == "UNKNOWN"
    assert universe.classification == Classification.RESEARCH_ONLY
    with pytest.raises(ValueError, match="production capture"):
        ArtifactSpec.model_validate(base | {"classification": "PRODUCTION"})


def test_public_download_exact_bytes_p2_capture_and_restart(tmp_path: Path) -> None:
    payload = b"TEST_ONLY mock publisher-native bytes, NOT market data"
    expected = {
        "path": "nse/year=2010/nse_2010.parquet",
        "byte_size": len(payload),
        "publisher_lfs_sha256": hashlib.sha256(payload).hexdigest(),
    }
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = 200
    response.read.side_effect = [payload, b""]
    landing = RawLanding(tmp_path / "raw")
    with patch("urllib.request.urlopen", return_value=response) as network:
        first = acquire_one(expected, tmp_path / "incoming", landing)
        second = acquire_one(expected, tmp_path / "incoming", landing)
        assert network.call_count == 1
    assert first == second
    assert first["sha256"] == expected["publisher_lfs_sha256"]
    assert first["auto_converted"] is False
    assert first["split"] is None
    assert (tmp_path / "incoming" / str(expected["path"])).read_bytes() == payload


def test_corrupt_public_download_cannot_enter_raw_storage(tmp_path: Path) -> None:
    expected = {
        "path": "nse/year=2010/nse_2010.parquet",
        "byte_size": 3,
        "publisher_lfs_sha256": hashlib.sha256(b"one").hexdigest(),
    }
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = 200
    response.read.side_effect = [b"two", b""]
    landing = RawLanding(tmp_path / "raw")
    with (
        patch("urllib.request.urlopen", return_value=response),
        pytest.raises(ValueError, match="CHECKSUM_OR_SIZE"),
    ):
        acquire_one(expected, tmp_path / "incoming", landing)
    assert not list((tmp_path / "raw").rglob("payload"))


def test_unexpected_exchange_or_revision_path_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="UNEXPECTED"):
        acquire_one({"path": "bse/year=2010/bse_2010.parquet"}, tmp_path, RawLanding(tmp_path))


def test_parquet_batches_keep_offsets_values_and_unknown_identity(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.parquet"
    pq.write_table(pa.Table.from_pylist([synthetic_row(4), synthetic_row(5)]), path)
    batches = list(iter_batches(path, batch_size=1))
    assert [b[0].row_number for b in batches] == [2, 3]
    assert dict(batches[0][0].fields)["open"] == "10.1"
    assert dict(batches[0][0].fields)["isin"] == ""
    assert dict(batches[0][0].fields)["security_id"] == ""
    assert list(iter_batches(path, batch_size=2))[0] == batches[0] + batches[1]


def test_missing_source_columns_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_missing.parquet"
    pq.write_table(pa.Table.from_pylist([{"date": date(2010, 1, 4)}]), path)
    with pytest.raises(DataContractError, match="SCHEMA"):
        list(iter_batches(path))


def test_identity_shards_preserve_every_original_row_and_offset(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_shards.parquet"
    rows = [synthetic_row(4), synthetic_row(5, "TEST_ONLY_ISIN"), synthetic_row(6)]
    pq.write_table(pa.Table.from_pylist(rows), path)
    expected = [r for batch in iter_batches(path, batch_size=1) for r in batch]
    partitioned = [
        r
        for i in range(4)
        for batch in iter_batches(path, batch_size=2, shards=4, shard_index=i)
        for r in batch
    ]
    assert sorted(partitioned, key=lambda r: r.row_number) == expected
    assert len({r.row_number for r in partitioned}) == len(rows)
    with pytest.raises(ValueError, match="INVALID_IDENTITY_SHARD"):
        list(iter_batches(path, shards=4, shard_index=4))


def test_explicit_global_duplicate_index_quarantines_both_members(tmp_path: Path) -> None:
    _, manifest = synthetic_manifest(tmp_path)
    row = synthetic_row()
    key = "tejhq:symbol:TEST_ONLY:EQ"
    rows = parse_batch([row, row], 2, {(key, row["date"])})
    records, quarantined = normalize(rows, manifest)
    assert not records
    assert len(quarantined) == 2
    assert {q.validation_rule for q in quarantined} == {"DUPLICATE_SECURITY_SESSION_VERSION"}


def test_normalization_and_p3_do_not_invent_historical_clocks(tmp_path: Path) -> None:
    _, manifest = synthetic_manifest(tmp_path)
    records, _ = normalize(parse_batch([synthetic_row()], 2), manifest)
    assert records[0].open.as_tuple().exponent == -1
    assert records[0].available_at is None
    assert records[0].session_close_at is None
    assert records[0].identity_basis == "SOURCE_SCOPED_SYMBOL"
    report = validate(
        ValidationInput(
            records=records,
            artifacts=(
                ArtifactEvidence(
                    manifest=manifest,
                    observed_sha256=manifest.sha256,
                    observed_byte_size=manifest.byte_size,
                    normalized_sha256=checksum(
                        stable_json(
                            [r.model_dump(mode="json", exclude={"record_id"}) for r in records]
                        )
                    ),
                ),
            ),
            classification=Classification.TEST_ONLY,
        )
    )
    assert report.session_calendar_status == "UNAVAILABLE"
    assert "UNIVERSE_READINESS" in {i.rule_id for i in report.issues}
    assert report.production_claims_permitted is False


def test_repeated_price_context_survives_more_than_four_sessions(tmp_path: Path) -> None:
    _, manifest = synthetic_manifest(tmp_path)
    records, _ = normalize(parse_batch([synthetic_row(d) for d in range(4, 11)], 2), manifest)
    assert len(previous_context(list(records))) == 7


def test_original_raw_corruption_is_detected(tmp_path: Path) -> None:
    landing, manifest = synthetic_manifest(tmp_path)
    path = landing.resolve(manifest.raw_path)
    path.chmod(0o600)
    path.write_bytes(b"TEST_ONLY corrupt bytes")
    with pytest.raises(DataContractError, match="CHECKSUM_OR_SIZE"):
        landing.read(manifest)
