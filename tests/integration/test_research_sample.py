"""Real local CC BY research fixtures; no market data is embedded or downloaded by tests."""

import csv
import io
import json
from pathlib import Path

import pytest

from alphalens_data.normalization import checksum
from alphalens_data.providers.mendeley import (
    ResearchCatalog,
    parse_sample,
    read_artifact,
    source_row_bytes,
)
from alphalens_data.research_sample import replay
from alphalens_data.validation import eligible_at

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / ".local-data/p1/mendeley"
CATALOG = ROOT / "docs/data/research-sample-manifest.json"


@pytest.fixture(scope="module")
def catalog() -> ResearchCatalog:
    result = ResearchCatalog.model_validate_json(CATALOG.read_bytes())
    if not all((RAW / a.raw_relative_path).is_file() for a in result.artifacts):
        pytest.skip("Real research files absent: acquire pinned CC BY artifacts; no substitute")
    return result


def test_real_capture_replay_and_honest_missing_rows(catalog: ResearchCatalog) -> None:
    first, report = replay(catalog, RAW)
    second, second_report = replay(catalog, RAW)
    assert first == second
    assert report == second_report
    assert checksum(first) == report["normalized_sha256"] == report["replayed_sha256"]
    assert report["selected_source_rows"] == 300
    assert report["canonical_rows"] == 299
    assert report["unavailable_rows"] == 1
    assert report["observed_dates"] == 60
    assert report["production_data_clearance"] == "OPEN"
    by_symbol = {a["symbol"]: a for a in report["artifacts"]}
    assert by_symbol["3MINDIA.NS"]["missing_relative_to_observed_cohort"] == ["2024-03-15"]
    assert by_symbol["3MINDIA.NS"]["unavailable_rows"][0]["raw_row_number"] == 5403
    for symbol in ["ACI.NS", "360ONE.NS", "ABSLAMC.NS"]:
        assert by_symbol[symbol]["zero_volume_dates"] == ["2024-01-15"]
    normalized = json.loads(first)
    keys = [(r["bar"]["security_id"], r["bar"]["session_date"]) for r in normalized]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


def test_every_real_record_traces_to_original_input(catalog: ResearchCatalog) -> None:
    for artifact in catalog.artifacts:
        raw = read_artifact(RAW, artifact)
        source_rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
        parsed = parse_sample(raw, artifact, catalog.start_session, catalog.end_session)
        for row in parsed.rows:
            bar = row.bar
            source = tuple(source_rows[row.raw_row_number - 1])
            assert source == row.source_fields
            assert checksum(source_row_bytes(source)) == row.source_row_sha256
            assert row.raw_sha256 == artifact.sha256 == checksum(raw)
            assert row.raw_artifact_ref == artifact.raw_relative_path
            assert row.dataset_doi == artifact.doi
            assert row.dataset_version == artifact.version
            assert row.license == artifact.license
            assert row.contributors == artifact.contributors
            assert bar.provenance.origin == "REAL_RESEARCH_FIXTURE"
            assert str(row.raw_row_number) == bar.provenance.source_record_id.rsplit(":", 1)[1]
            assert bar.provenance.available_at is None
            assert bar.provenance.published_at is None
            assert bar.session_close_at is None
            assert bar.adjusted_close is None
            assert bar.adjustment_method_version is None
            assert not eligible_at(bar, artifact.acquired_at)
            assert bar.high >= max(bar.open, bar.close, bar.low)
            assert bar.low <= min(bar.open, bar.close, bar.high)
            assert bar.volume >= 0
        assert checksum(read_artifact(RAW, artifact)) == artifact.sha256
