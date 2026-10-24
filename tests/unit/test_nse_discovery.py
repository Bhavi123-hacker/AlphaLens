"""TEST_ONLY discovery/coverage contracts; no provider or real performance claims."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.nse_market import discovery
from workers.providers import universe

AT = datetime(2026, 10, 24, 18, 35, tzinfo=UTC)


def snapshot() -> universe.Snapshot:
    records = tuple(
        {
            "instrument_key": f"NSE_EQ|TEST_ONLY_{i}",
            "symbol": f"TEST_ONLY_{i}",
            "isin": f"TEST_ONLY_{i}",
            "name": "TEST_ONLY company",
            "eligible_common_equity": i < 5,
            "classification": "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"
            if i < 5
            else "FUND_OR_ETF_ISIN",
        }
        for i in range(6)
    )
    return universe.Snapshot(
        "0" * 64, AT - timedelta(days=2), (), records, {"exclusion_counts": {"FUND_OR_ETF_ISIN": 1}}
    )


def test_dated_discovery_never_promotes_provider_identity_or_future_master() -> None:
    source = snapshot()
    status = discovery.identity_status(source, at=AT)
    assert status["state"] == "STALE" and status["discovery_available"] is True
    assert status["current_identity_actions_available"] is False
    with pytest.raises(ValueError):
        discovery.identity_status(replace(source, observed_at=AT + timedelta(seconds=1)), at=AT)


def test_known_missing_and_unsupported_security_have_no_substitute_price_or_score() -> None:
    for index, state in [(0, "SUPPORTED_EQUITY_NO_SAVED_HISTORY"), (5, "UNSUPPORTED_INSTRUMENT")]:
        row = discovery.empty_security(snapshot().records[index])
        assert row["support_status"] == state
        assert row["close"] is row["volume"] is row["change"] is row["session"] is None
        assert "score" not in row


def test_independent_coverage_dates_deduplicated_exclusions_and_kolkata_freshness() -> None:
    source = snapshot()
    keys = [row["instrument_key"] for row in source.records]
    view: dict[str, Any] = {
        "rows": [
            {"key": keys[0], "close": "100", "session": "2026-10-24"},
            {"key": keys[1], "close": "50", "session": "2026-10-23"},
            {"key": keys[2], "close": None, "session": None},
        ],
        "latest_observed_session": "2026-10-24",
        "configured_securities": 3,
        "latest_session_securities": 1,
        "research_workspace": {
            "current_feature_date": "2026-10-24",
            "coverage": {"technical_feature_eligible_securities": 1},
            "scores": {"observation_session": "2026-10-17"},
            "candidates": [
                {"key": keys[0], "session": "2026-10-17", "risk": {"return_daily_sd_20": 0.1}},
                {"key": keys[1], "session": "2026-10-24", "risk": {"return_daily_sd_20": 0.2}},
            ],
            "technical_exclusions": [{"key": keys[0], "reason": "TEST_ONLY_MISSING"}] * 2,
        },
    }
    result = discovery.measure(source, view, at=AT)
    assert result["supported_equities"] == result["searchable_equities"] == 5
    assert result["available_saved_prices"] == 2 and result["latest_session_prices"] == 1
    assert result["saved_compatible_predictions"] == 2
    # At18:35UTC Kolkata is already25Oct:17Oct is8 days old, not7.
    assert result["dated_ranking_eligible_predictions"] == 1
    assert result["latest_session_predictions"] == 1
    assert result["top_n_returnable"] == {"5": 1, "10": 1, "20": 1}
    assert result["daily_update_success_rate"] is None
    assert result["latest_feature_exclusion_reasons"] == {"TEST_ONLY_MISSING": 1}
    assert result["exclusions"]["no_saved_price"] == 3
    assert result["ranking_security_cap"] is None


def test_identity_changes_keep_absence_separate_from_delisting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = snapshot()
    earlier = replace(
        source, snapshot_id="1" * 64, observed_at=source.observed_at - timedelta(days=1)
    )
    removed = replace(source, records=source.records[1:])
    for item in (earlier, removed):
        (tmp_path / f"snapshot-{item.snapshot_id}.json").touch()
    monkeypatch.setattr(
        universe,
        "load",
        lambda root, snapshot_id: earlier if snapshot_id == earlier.snapshot_id else removed,
    )
    result = discovery.identity_history(tmp_path, source.records[0]["instrument_key"])
    assert [row["presence"] for row in result["observations"]] == [
        "OBSERVED",
        "ABSENT_NOT_VERIFIED_DELISTING",
    ]
    assert result["absence_is_not_verified_delisting"] is True
    assert result["historical_membership_established"] is False


def test_corrupt_historical_master_is_counted_but_never_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = snapshot()
    (tmp_path / f"snapshot-{source.snapshot_id}.json").touch()
    (tmp_path / f"snapshot-{'f' * 64}.json").touch()

    def load(root: Path, *, snapshot_id: str) -> universe.Snapshot:
        if snapshot_id != source.snapshot_id:
            raise ValueError("TEST_ONLY_PRIVATE_DERIVATION_DETAIL")
        return source

    monkeypatch.setattr(universe, "load", load)
    result = discovery.identity_history(tmp_path, source.records[0]["instrument_key"])
    assert len(result["observations"]) == len(result["unverified_snapshots"]) == 1
    assert result["complete_snapshot_history"] is False
    assert "TEST_ONLY_PRIVATE_DERIVATION_DETAIL" not in str(result)
