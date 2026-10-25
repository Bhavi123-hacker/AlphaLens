"""TEST_ONLY maturity explanations never infer unknown trading dates or returns."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from test_experimental_nse_v2_forward import KEY, SESSIONS, record, score, timing
from workers.nse_market import engine, model_review, outcomes

from alphalens_api import nse_evaluation


def decision() -> dict[str, Any]:
    return {
        **score(),
        "horizon": 5,
        "target_version": "prior-eod.next-open-to-fifth-close.price-return.v2",
        "source_observed_at": "2025-01-02T11:00:00+00:00",
        "inference_at": "2025-01-02T12:00:00+00:00",
        "recorded_at": "2025-01-02T12:00:00+00:00",
    }


def facts() -> dict[str, dict[str, Any]]:
    result = {day: timing(day) for day in SESSIONS}
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        result[previous]["next_verified_session"] = following
    return result


def context() -> dict[str, Any]:
    return {
        "state": "TEST_ONLY_PROJECTED_HISTORY",
        "histories": {
            KEY: {
                day: {"open": "100", "high": "110", "low": "90", "close": "105", "volume": 1}
                for day in SESSIONS
            }
        },
        "identities": {KEY: {"symbol": "RELIANCE"}},
        "actions": {
            KEY: {
                "state": "OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE",
                "hazard_dates": [],
                "complete": False,
            }
        },
    }


def test_complete_official_chain_defines_maturity_but_projection_is_not_outcome() -> None:
    result = outcomes.decision_evidence(
        decision(), at=datetime(2025, 1, 11, tzinfo=UTC), timings=facts(), context=context()
    )
    assert result["proven_required_future_sessions"] == list(SESSIONS[1:])
    assert result["expected_maturity_session"] == SESSIONS[-1]
    assert result["expected_maturity_at"] == timing(SESSIONS[-1])["close_at"]
    assert result["maturity_status"] == "AWAITING_QUALIFIED_OUTCOME_EVIDENCE"
    assert result["corporate_action_coverage_complete"] is False
    assert result["historical_identity_continuity_independently_verified"] is False
    assert all(
        row["saved_price_present"] and not row["raw_publication_receipt_verified_by_this_audit"]
        for row in result["target_observations"]
    )
    assert "QUALIFIED_APPEND_ONLY_OUTCOME_NOT_RECORDED" in result["missing_evidence"]


def test_unknown_next_session_never_becomes_guessed_weekday_maturity() -> None:
    partial = facts()
    partial[SESSIONS[3]].pop("next_verified_session")
    result = outcomes.decision_evidence(
        decision(), at=datetime(2025, 1, 11, tzinfo=UTC), timings=partial, context=context()
    )
    assert result["proven_required_future_sessions"] == list(SESSIONS[1:4])
    assert result["calendar_gap_after_session"] == SESSIONS[3]
    assert result["expected_maturity_session"] is result["expected_maturity_at"] is None
    assert result["maturity_status"] == "CALENDAR_MATURITY_UNKNOWN"


def test_future_entry_keeps_completed_calendar_and_missing_prices_separate() -> None:
    empty = context()
    empty["histories"] = {}
    empty["actions"] = {}
    empty["identities"] = {}
    result = outcomes.decision_evidence(
        decision(), at=datetime(2025, 1, 2, 13, tzinfo=UTC), timings=facts(), context=empty
    )
    assert result["maturity_status"] == "FUTURE_ENTRY_NOT_STARTED"
    assert (
        result["expected_maturity_session"] == SESSIONS[-1]
    )  # Official schedule can be known before future prices.
    assert "FUTURE_TARGET_SESSION_NOT_COMPLETED" in result["missing_evidence"]
    assert "REQUIRED_TARGET_PRICE_SLOTS_MISSING" in result["missing_evidence"]
    assert "ACTION_REFERENCE_UNAVAILABLE_OR_UNPARSED" in result["missing_evidence"]


def test_known_action_and_identity_mismatch_are_visible() -> None:
    evidence = context()
    evidence["actions"][KEY]["hazard_dates"] = [SESSIONS[2]]
    evidence["identities"][KEY]["symbol"] = "TEST_ONLY_CHANGED"
    result = outcomes.decision_evidence(
        decision(), at=datetime(2025, 1, 11, tzinfo=UTC), timings=facts(), context=evidence
    )
    assert result["known_action_exclusions"] == [SESSIONS[2]]
    assert result["identity_status"] == "CURRENT_SAVED_IDENTITY_DIFFERENT_OR_UNAVAILABLE"
    assert "KNOWN_TARGET_ACTION_EXCLUSION" in result["missing_evidence"]


def test_reader_can_export_complete_audit_and_zero_metrics_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, v2 = tmp_path / "TEST_ONLY_market", tmp_path / "TEST_ONLY_v2"
    record(v2 / "price-only", monkeypatch)
    result = nse_evaluation.read(root, v2, at=datetime(2025, 1, 3, tzinfo=UTC), row_limit=None)
    assert (
        result["measurement_status"] == result["confidence_interval_status"] == "NOT_YET_MEASURABLE"
    )
    assert result["top_n"]["measurement_status"] == "NOT_YET_MEASURABLE"
    assert result["rows_total"] == len(result["rows"]) == 1 and result["rows_truncated"] is False
    assert result["rows"][0]["horizon_sessions"] == 5
    assert result["rows"][0]["expected_maturity_at"] is None
    assert result["metrics"]["score"]["accuracy"] is result["confidence_intervals"] is None
    assert result["metrics"]["score"]["measurement_status"] == "NOT_YET_MEASURABLE"


def test_projection_context_never_uses_a_future_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "market-view-latest.json").write_text("TEST_ONLY_POINTER", encoding="utf-8")
    monkeypatch.setattr(engine, "_pointed", lambda root, name: {"as_of": "2025-01-10T00:00:00Z"})
    result = outcomes.audit_context(tmp_path, at=datetime(2025, 1, 3, tzinfo=UTC))
    assert result["state"] == "SAVED_MARKET_PROJECTION_AFTER_CUTOFF"
    assert result["histories"] == {}


def test_model_verdict_never_promotes_attractive_or_claimed_accepted_saved_metrics() -> None:
    result = model_review.candidate_verdict(
        integrity_valid=True, native_verdict="ACCEPTED", limitations=["EXTERNAL_REVIEW_ABSENT"]
    )
    assert result["verdict"] == "EXPERIMENTAL_INSUFFICIENT_EVIDENCE"
    assert result["independent_review_supplied_by_this_audit"] is False
    assert result["model_promoted_by_this_audit"] is result["accepted_publication"] is False
    blocked = model_review.candidate_verdict(
        integrity_valid=False, native_verdict=None, limitations=[]
    )
    assert blocked["verdict"] == "BLOCKED_DATA_QUALITY"


def test_model_evidence_rejects_checksum_corruption(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_model_evaluation.json"
    path.write_text('{"source":"TEST_ONLY"}', encoding="utf-8")
    path.with_suffix(".sha256").write_text("0" * 64, encoding="utf-8")
    with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
        model_review.evidence(path, relative_to=tmp_path)
