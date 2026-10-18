"""TEST_ONLY immutable SQLite history reader; no source, inference or new forecasts."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import digest
from workers.experimental_nse_v2 import forward
from workers.nse_market import forward_cohort

from alphalens_api.auth.permissions import restrict

KEY = "NSE_EQ|INE009A01021"


def ledger(folder: Path, *, future: bool = False, corrupt: bool = False) -> str:
    now = datetime.now(UTC)
    recorded = now + timedelta(days=1) if future else now - timedelta(days=8)
    forecast = {
        "model_id": "TEST_ONLY_MODEL",
        "key": KEY,
        "session": (recorded - timedelta(days=1)).date().isoformat(),
        "recorded_at": recorded.isoformat(),
        "source_observed_at": (recorded - timedelta(minutes=5)).isoformat(),
        "score": 0.6,
        "prospective_eligible": True,
    }
    identifier = forward._hash(forecast)
    with forward._connection(folder, write=True) as connection:
        connection.execute(
            "INSERT INTO experimental_forecasts VALUES(?,?,?,?,?,?)",
            (
                identifier,
                forecast["model_id"],
                KEY,
                forecast["session"],
                forecast["recorded_at"],
                forward._encode({**forecast, "score": 0.2} if corrupt else forecast),
            ),
        )
    return identifier


def outcome(
    folder: Path, identifier: str, revision: int, *, future: bool = False, value: str = "0.01"
) -> None:
    now = datetime.now(UTC)
    recorded = now + timedelta(days=1) if future else now - timedelta(minutes=1)
    body = {
        "forecast_id": identifier,
        "revision": revision,
        "recorded_at": recorded.isoformat(),
        "source_observed_at": (recorded - timedelta(minutes=5)).isoformat(),
        "target_session": (recorded - timedelta(days=1)).date().isoformat(),
        "status": "MATURED_PRICE_REFERENCE_RETURN",
        "target_return": value,
        "target": 1,
    }
    with forward._connection(folder, write=True) as connection:
        connection.execute(
            "INSERT INTO experimental_outcomes VALUES(?,?,?,?,?)",
            (forward._hash(body), identifier, revision, body["recorded_at"], forward._encode(body)),
        )


def paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root, v2 = tmp_path / "TEST_ONLY_expanded", tmp_path / "TEST_ONLY_v2"
    return (
        root,
        v2,
        v2 / "price-only",
        root / "expanded-forecasts" / digest(KEY.encode())[:2],
    )


def hashes(root: Path) -> dict[str, str]:
    return {str(path): digest(path.read_bytes()) for path in root.rglob("*") if path.is_file()}


def test_missing_security_history_never_creates_directories_or_database(tmp_path: Path) -> None:
    root, v2, _, _ = paths(tmp_path)
    value = forward_cohort.stock_history(root, v2, KEY)
    assert value["forecast_count"] == value["matured_outcomes"] == 0
    assert value["rows"] == [] and not root.exists() and not v2.exists()


def test_reader_retains_real_body_latest_revision_and_never_mutates_ledger(tmp_path: Path) -> None:
    root, v2, original, _ = paths(tmp_path)
    identifier = ledger(original)
    outcome(original, identifier, 1)
    outcome(original, identifier, 2)
    before = hashes(tmp_path)
    value = forward_cohort.stock_history(root, v2, KEY)
    assert value["forecast_count"] == value["matured_outcomes"] == 1
    assert value["original_forecasts"] == 1 and value["expanded_forecasts"] == 0
    assert value["rows"][0]["outcome"]["revision"] == 2
    assert value["rows"][0]["forecast"]["score"] == 0.6
    assert hashes(tmp_path) == before


def test_overlapping_decisions_count_once_but_both_stores_are_visible(tmp_path: Path) -> None:
    root, v2, original, expanded = paths(tmp_path)
    identifier = ledger(original)
    expanded.mkdir(parents=True)
    restrict(expanded)
    target = expanded / "experimental-v2-prospective.sqlite3"
    target.write_bytes((original / target.name).read_bytes())
    if os.name != "nt":
        target.chmod(0o600)
    outcome(original, identifier, 1)
    value = forward_cohort.stock_history(root, v2, KEY, limit=1)
    assert value["unique_decisions"] == value["forecast_count"] == 1
    assert value["original_forecasts"] == value["expanded_forecasts"] == 1
    assert value["raw_forecast_records"] == 2 and len(value["rows"]) == 1
    assert value["matured_outcomes"] == 1 and value["history_truncated"] is True


def test_future_forecasts_and_latest_future_outcomes_never_count_as_matured(tmp_path: Path) -> None:
    root, v2, original, expanded = paths(tmp_path)
    identifier = ledger(original)
    outcome(original, identifier, 1)
    outcome(original, identifier, 2, future=True)
    ledger(expanded, future=True)
    value = forward_cohort.stock_history(root, v2, KEY)
    assert value["forecast_count"] == value["pending_forecasts"] == 1
    assert value["matured_outcomes"] == 0 and value["rows"][0]["outcome"] is None
    assert value["future_forecast_records_ignored"] == value["future_outcome_records_ignored"] == 1


def test_disagreeing_store_outcomes_are_reported_without_inflating_maturity(tmp_path: Path) -> None:
    root, v2, original, expanded = paths(tmp_path)
    identifier = ledger(original)
    expanded.mkdir(parents=True)
    restrict(expanded)
    target = expanded / "experimental-v2-prospective.sqlite3"
    target.write_bytes((original / target.name).read_bytes())
    if os.name != "nt":
        target.chmod(0o600)
    outcome(original, identifier, 1)
    outcome(expanded, identifier, 1, value="0.02")
    value = forward_cohort.stock_history(root, v2, KEY)
    assert value["unique_decisions"] == value["overlapping_outcome_conflicts"] == 1
    assert value["matured_outcomes"] == 0 and value["pending_forecasts"] == 1


def test_tampered_body_cannot_be_read_as_verified_forecast(tmp_path: Path) -> None:
    root, v2, original, _ = paths(tmp_path)
    ledger(original, corrupt=True)
    with pytest.raises(ValueError, match="PROSPECTIVE_CHECKSUM_MISMATCH"):
        forward_cohort.stock_history(root, v2, KEY)


@pytest.mark.parametrize("limit", [0, 101, True, "50"])
def test_invalid_limits_are_rejected(tmp_path: Path, limit: Any) -> None:
    root, v2, _, _ = paths(tmp_path)
    with pytest.raises(ValueError, match="BOUNDED_SECURITY_HISTORY_LIMIT"):
        forward_cohort.stock_history(root, v2, KEY, limit=limit)
