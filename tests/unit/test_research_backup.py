"""TEST_ONLY backup boundaries and integrity, never real research evidence."""

import gzip
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from scripts import backup_research as bundle
from workers.experimental_nse.acquire import digest, encoded, initialize
from workers.experimental_nse_v2 import data, forward, models, pipeline
from workers.experimental_nse_v2.features import FEATURE_NAMES
from workers.nse_market import engine
from workers.providers import universe
from workers.providers.upstox import Reply

from alphalens_api.auth.permissions import restrict
from alphalens_data.daily.storage import Store


def test_destination_refuses_existing_or_external_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bundle, "REPO", tmp_path)
    initialize(tmp_path / ".local-data")
    existing = tmp_path / ".local-data/existing"
    initialize(existing)
    for path in (existing, tmp_path / "outside"):
        with pytest.raises(ValueError, match="NEW_PRIVATE_ISOLATED_DESTINATION_REQUIRED"):
            bundle.destination(path)
    assert not (tmp_path / "outside").exists()


def test_online_sqlite_copy_preserves_source_and_private_permissions(tmp_path: Path) -> None:
    restrict(tmp_path)
    source = tmp_path / "TEST_ONLY.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence(value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('TEST_ONLY')")
    before = digest(source.read_bytes())
    target = tmp_path / "private/saved.sqlite3"
    bundle.copy_file(source, target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT * FROM evidence").fetchall() == [("TEST_ONLY",)]
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert digest(source.read_bytes()) == before


def test_tampered_manifest_file_is_rejected_before_model_loading(tmp_path: Path) -> None:
    restrict(tmp_path)
    body = encoded({"files": {"payload.json": "0" * 64}, "v2_forecasts": 0})
    (tmp_path / "manifest.json").write_bytes(body)
    (tmp_path / "manifest.sha256").write_text(digest(body), encoding="ascii")
    (tmp_path / "payload.json").write_bytes(b"TEST_ONLY")
    (tmp_path / "payload.json").chmod(0o600)
    with pytest.raises(ValueError, match="RESEARCH_BUNDLE_FILE_HASH_REJECTED"):
        bundle.validate(tmp_path)


@pytest.mark.parametrize(
    "relative",
    [
        "/outside",
        "../outside",
        "v2/../outside",
        "v2\\..\\outside",
        "C:\\outside",
        "v2//file",
        "v2:stream/file",
    ],
)
def test_hosted_bundle_rejects_absolute_traversal_and_stream_paths(
    tmp_path: Path, relative: str
) -> None:
    restrict(tmp_path)
    body = encoded({"files": {relative: "0" * 64}, "v2_forecasts": 0})
    (tmp_path / "manifest.json").write_bytes(body)
    (tmp_path / "manifest.sha256").write_text(digest(body), encoding="ascii")
    with pytest.raises(ValueError, match="RESEARCH_BUNDLE_RELATIVE_PATH_REJECTED"):
        bundle.validate(tmp_path)


def _forecast(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now, received = datetime(2025, 1, 2, 12, tzinfo=UTC), datetime(2025, 1, 2, 11, tzinfo=UTC)
    monkeypatch.setattr(forward, "_utc_now", lambda: now)

    def timing(day: str) -> dict[str, Any]:
        return {
            "session": day,
            "open_at": day + "T09:15:00+05:30",
            "close_at": day + "T15:30:00+05:30",
            "source": "UPSTOX_OFFICIAL_MARKET_TIMINGS",
            "source_sha256": "a" * 64,
            "source_received_at": received.isoformat(),
            "previous_session": "2025-01-02",
            "intervening_dates_verified_closed": True,
        }

    forward.append_forecasts(
        root,
        "TEST_MODEL",
        "TEST_DATA",
        "TEST_PROTOCOL",
        [
            {
                "key": "NSE_EQ|INE002A01018",
                "symbol": "TEST_ONLY",
                "session": "2025-01-02",
                "score": 0.6,
                "vector": [0.01] * len(FEATURE_NAMES),
                "source": "TEST_ONLY_NOT_REAL_MARKET_DATA",
                "baseline_majority_score": 0.4,
                "baseline_momentum_score": 1.0,
                "session_timing": timing("2025-01-02"),
                "next_session_timing": timing("2025-01-03"),
            }
        ],
        received,
    )


def test_expanded_bundle_and_isolated_restore_preserve_source_hashes_models_and_forecast_shards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bundle, "REPO", tmp_path)
    private = tmp_path / ".local-data"
    initialize(private)
    v1, v2 = private / "TEST_ONLY_v1", private / "TEST_ONLY_v2"
    initialize(v1)
    initialize(v2)
    initialize(v2 / "price-only")
    (v1 / "TEST_ONLY-data.json").write_bytes(encoded({"source": "TEST_ONLY"}))
    _forecast(v2 / "price-only", monkeypatch)
    config = private / "p33-runtime"
    initialize(config)
    (config / "operator-config.json").write_bytes(
        encoded({"experimental_nse_root": str(v1), "experimental_nse_v2_root": str(v2)})
    )
    universe.save(
        private / "nse-universe",
        Reply(
            200,
            gzip.compress(
                encoded(
                    [
                        {
                            "segment": "NSE_EQ",
                            "exchange": "NSE",
                            "instrument_type": "EQ",
                            "security_type": "NORMAL",
                            "name": "TEST_ONLY COMPANY",
                            "trading_symbol": "TEST_ONLY",
                            "isin": "INE002A01018",
                            "instrument_key": "NSE_EQ|INE002A01018",
                        }
                    ]
                )
            ),
            datetime(2025, 1, 2, 12, tzinfo=UTC),
            "ACCEPTED",
        ),
    )
    expanded = private / "nse-market-expansion"
    initialize(expanded)
    initialize(expanded / "control")
    engine._checked(expanded / "TEST_ONLY-source.json", {"raw_sha256": "b" * 64})
    shard = expanded / "expanded-forecasts/TEST_ONLY-shard"
    _forecast(shard, monkeypatch)
    sequence = private / "sequence-benchmark-v1"
    initialize(sequence)
    engine._checked(
        sequence / "model.json", {"protocol_sha256": "a" * 64, "numeric_state": [0.1, 0.2]}
    )
    model_sha = digest((sequence / "model.json").read_bytes())
    engine._checked(
        sequence / "report.json",
        {
            "model_sha256": model_sha,
            "protocol_sha256": "a" * 64,
            "accepted_rankings": 0,
            "current_scores": [{"classification": "TEST_ONLY"}],
        },
    )
    engine._checked(
        sequence / "historical-predictions.json",
        {"model_sha256": model_sha, "rows": [{"classification": "TEST_ONLY"}]},
    )
    monkeypatch.setattr(data, "load_current", lambda root: {"rows": [{"source": "TEST_ONLY"}]})
    monkeypatch.setattr(pipeline, "verified", lambda path: {"model_sha256": "c" * 64})
    monkeypatch.setattr(models, "load_model", lambda path, sha: {"classification": "TEST_ONLY"})
    monkeypatch.setattr(
        engine,
        "workspace",
        lambda root, v2_root: {
            "coverage": {"observations": 1},
            "candidates": [{"classification": "TEST_ONLY"}],
        },
    )
    source_before = bundle._ledger(shard / "experimental-v2-prospective.sqlite3")
    with pytest.raises(ValueError, match="OUTSIDE_ACTIVE_ROOTS"):
        bundle.backup(v2 / "TEST_ONLY_recursive")
    assert not (v2 / "TEST_ONLY_recursive").exists()
    backup = private / "TEST_ONLY_bundle"
    saved = bundle.backup(backup)
    assert saved["expanded_evidence"]["expanded_forecasts"] == 1
    assert saved["expanded_evidence"]["sequence_model_sha256"] == model_sha
    manifest = json.loads((backup / "manifest.json").read_bytes())
    assert all("\\" not in name for name in manifest["files"])
    # A retained Windows-format manifest remains verifiable on a Linux host;
    # production manifests themselves are never migrated or rewritten.
    manifest["files"] = {name.replace("/", "\\"): sha for name, sha in manifest["files"].items()}
    legacy_body = encoded(manifest)
    (backup / "manifest.json").write_bytes(legacy_body)
    (backup / "manifest.sha256").write_text(digest(legacy_body), encoding="ascii")
    assert bundle.validate(backup) == saved
    with pytest.raises(ValueError, match="OUTSIDE_SOURCE_BUNDLE"):
        bundle.restore(backup, backup / "TEST_ONLY_recursive")
    restored = private / "TEST_ONLY_restore"
    actual = bundle.restore(backup, restored)
    assert actual["expanded_evidence"] == saved["expanded_evidence"]
    assert (
        bundle._ledger(
            restored
            / "nse-market-expansion/expanded-forecasts/TEST_ONLY-shard"
            / "experimental-v2-prospective.sqlite3"
        )
        == source_before
    )
    assert bundle._ledger(shard / "experimental-v2-prospective.sqlite3") == source_before
    assert (
        engine._read(restored / "nse-market-expansion/TEST_ONLY-source.json")["raw_sha256"]
        == "b" * 64
    )
    assert (restored / "sequence-benchmark-v1/model.json").read_bytes() == (
        sequence / "model.json"
    ).read_bytes()
    legacy = bundle.backup(private / "TEST_ONLY_legacy", include_expanded=False)
    assert legacy["expanded_evidence"] == {}
    assert not (private / "TEST_ONLY_legacy/nse-market-expansion").exists()
    with (
        Store(expanded / "control").lock(),
        pytest.raises(ValueError, match="DAILY_WORKER_BUSY"),
    ):
        bundle.backup(private / "TEST_ONLY_busy")
    assert not (private / "TEST_ONLY_busy/manifest.json").exists()
    original_copy = bundle.copy_file
    changed = v1 / "TEST_ONLY-data.json"

    def copy_and_change(source: Path, target: Path) -> None:
        original_copy(source, target)
        if source == changed:
            changed.write_bytes(encoded({"source": "TEST_ONLY_CONCURRENT_REVISION"}))

    monkeypatch.setattr(bundle, "copy_file", copy_and_change)
    with pytest.raises(ValueError, match="SOURCE_CHANGED_DURING_BACKUP"):
        bundle.backup(private / "TEST_ONLY_interrupted", include_expanded=False)
    assert not (private / "TEST_ONLY_interrupted/manifest.json").exists()


def test_online_backup_uses_committed_wal_snapshot_with_active_test_writer(tmp_path: Path) -> None:
    source = tmp_path / "TEST_ONLY-WAL.sqlite3"
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE evidence(value TEXT)")
        writer.execute("INSERT INTO evidence VALUES ('TEST_ONLY_COMMITTED')")
        writer.commit()
        writer.execute("INSERT INTO evidence VALUES ('TEST_ONLY_NOT_COMMITTED')")
        target = tmp_path / "isolated/TEST_ONLY-WAL.sqlite3"
        bundle.copy_file(source, target)
        with sqlite3.connect(target) as saved:
            assert saved.execute("SELECT value FROM evidence").fetchall() == [
                ("TEST_ONLY_COMMITTED",)
            ]
        writer.rollback()


def test_incomplete_sequence_artifacts_are_preserved_without_claiming_completed_model(
    tmp_path: Path,
) -> None:
    root = tmp_path / "sequence-benchmark-v1"
    initialize(root)
    engine._checked(root / "model.json", {"numeric_state": [0.1], "classification": "TEST_ONLY"})
    assert bundle._extended_evidence(tmp_path) == {
        "sequence_state": "INCOMPLETE_UNPUBLISHED_FILES_PRESERVED_ONLY"
    }
