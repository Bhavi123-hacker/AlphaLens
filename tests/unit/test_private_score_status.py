"""TEST_ONLY source/entry clock distinctions; no market prediction or performance."""

from datetime import UTC, datetime, timedelta

import pytest
from test_nse_market_api import data_fixture

from alphalens_api.nse_market import _candidate


def test_recent_source_does_not_redate_passed_entry_or_old_snapshot() -> None:
    row = data_fixture()["candidates"][0]
    row["entry_open_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert _candidate(row, latest_snapshot=True)["score_status"] == "SAVED_HISTORICAL_SCORE"
    row["entry_open_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    assert _candidate(row)["score_status"] == "SAVED_HISTORICAL_SCORE"
    assert (
        _candidate(row, latest_snapshot=True)["score_status"] == "FRESH_ELIGIBLE_EXPERIMENTAL_SCORE"
    )
    row["current_score_matches_frozen_vector"] = False
    assert _candidate(row, latest_snapshot=True)["score_status"] == "SAVED_HISTORICAL_SCORE"


def test_qualified_next_session_timing_can_support_future_entry_but_never_acceptance() -> None:
    row = data_fixture()["candidates"][0]
    row["next_session_timing"] = {"open_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}
    output = _candidate(row, latest_snapshot=True)
    assert output["prospective_entry_eligible"] is True
    assert output["forward_outcome_status"] == "FORWARD_OUTCOME_PENDING"
    assert output["independent_acceptance_status"] == "INDEPENDENT_ACCEPTANCE_PENDING"
    assert output["research_status"] == "EXPERIMENTAL_RESEARCH"


def test_corrupt_next_session_timing_fails_closed() -> None:
    row = data_fixture()["candidates"][0]
    row["next_session_timing"] = "TEST_ONLY_CORRUPT"
    with pytest.raises(ValueError, match="TIMING_INVALID"):
        _candidate(row, latest_snapshot=True)
