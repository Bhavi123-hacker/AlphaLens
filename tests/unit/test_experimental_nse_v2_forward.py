"""TEST_ONLY data verifies financial/clock invariants, never actual NSE evidence."""

import json
import sqlite3
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse_v2 import acceptance, forward
from workers.experimental_nse_v2.features import FEATURE_NAMES

KEY = "NSE_EQ|INE002A01018"
NOW = datetime(2025, 1, 2, 12, tzinfo=UTC)
RECEIVED = datetime(2025, 1, 2, 11, tzinfo=UTC)
SESSIONS = ("2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09")


def timing(day: str) -> dict[str, Any]:
    return {
        "session": day,
        "open_at": day + "T09:15:00+05:30",
        "close_at": day + "T15:30:00+05:30",
        "source": "UPSTOX_OFFICIAL_MARKET_TIMINGS",
        "source_sha256": "a" * 64,
        "source_received_at": RECEIVED.isoformat(),
        "previous_session": SESSIONS[0],
        "intervening_dates_verified_closed": True,
    }


def score(**updates: Any) -> dict[str, Any]:
    return {
        "key": KEY,
        "symbol": "RELIANCE",
        "session": SESSIONS[0],
        "score": 0.6,
        "vector": [0.01] * len(FEATURE_NAMES),
        "source": "TEST_ONLY_NOT_REAL_MARKET_DATA",
        "baseline_majority_score": 0.4,
        "baseline_momentum_score": 1.0,
        "session_timing": timing(SESSIONS[0]),
        "next_session_timing": timing(SESSIONS[1]),
        **updates,
    }


def record(root: Path, monkeypatch: pytest.MonkeyPatch, **updates: Any) -> dict[str, Any]:
    monkeypatch.setattr(forward, "_utc_now", lambda: NOW)
    return forward.append_forecasts(
        root, "TEST_MODEL", "TEST_DATA", "TEST_PROTOCOL", [score(**updates)], RECEIVED
    )


def rows() -> list[dict[str, Any]]:
    return [
        {
            "key": KEY,
            "symbol": "RELIANCE",
            "session": day,
            "open": str(100 + index),
            "high": "120",
            "low": "90",
            "close": str(101 + index),
            "volume": 10,
        }
        for index, day in enumerate(SESSIONS[1:])
    ]


def mature(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    observations: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, int]:
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 10, 12, tzinfo=UTC))
    kwargs.setdefault("require_official_sessions", False)  # Explicit TEST_ONLY fixture adapter.
    return forward.reconcile(
        root,
        observations if observations is not None else rows(),
        SESSIONS,
        datetime(2025, 1, 10, 11, tzinfo=UTC),
        **kwargs,
    )


def test_holding_return_uses_one_later_open_and_final_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    result = mature(tmp_path, monkeypatch)
    assert result["inserted"] == 1
    with sqlite3.connect(tmp_path / "experimental-v2-prospective.sqlite3") as db:
        body = json.loads(db.execute("SELECT body FROM experimental_outcomes").fetchone()[0])
    exact = Fraction(int(body["target_return_numerator"]), int(body["target_return_denominator"]))
    assert exact == Fraction(105, 100) - 1
    assert exact != (Fraction(101, 100) ** 5 - 1)
    assert body["entry_session"] == SESSIONS[1]
    assert body["economic_profitability_verified"] is False


def test_zero_outcomes_show_five_future_sessions_without_fabricated_rejections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record(tmp_path, monkeypatch)
    status = forward.summary(tmp_path)
    assert status["lifecycle"]["pending"] == 1
    assert status["lifecycle"]["rejected"] is None
    assert status["pending_forecasts"][0]["observed_sessions"] == 0
    assert status["pending_forecasts"][0]["remaining_sessions"] == 5
    assert status["metrics"]["ranking_and_reference_costs"]["available"] is False


def test_pending_progress_distinguishes_missing_published_bar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record(tmp_path, monkeypatch)
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 10, 12, tzinfo=UTC))
    facts = {day: timing(day) for day in SESSIONS}
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        facts[previous]["next_verified_session"] = following
    observations = [
        {**row, "received_at": "2025-01-10T11:00:00+00:00"}
        for row in rows()
        if row["session"] != SESSIONS[3]
    ]
    status = forward.summary(tmp_path, rows=observations, sessions=SESSIONS, official_timings=facts)
    progress = status["pending_forecasts"][0]
    assert progress["observed_sessions"] == 4
    assert progress["remaining_sessions"] == 1
    assert progress["missing_sessions"] == [SESSIONS[3]]
    assert status["lifecycle"]["missing"] == 1


def test_pinned_review_id_alone_never_reports_imported_approval() -> None:
    bundle = acceptance.evidence_bundle("model", "dataset", "protocol", {})
    result = acceptance.readiness(bundle, verified_review_id="manually_supplied_green_flag")
    assert result["independent_review"] == "PENDING_EXTERNAL_REVIEW"
    assert result["independent_review_id"] is None
    assert result["unverified_review_id_ignored"] is True
    assert result["accepted_top_5_10_20"] is False


def test_acceptance_rejects_rehashed_lowered_criteria() -> None:
    bundle = acceptance.evidence_bundle("model", "dataset", "protocol", {})
    bundle["criteria"] = {**acceptance.CRITERIA, "eligible_outcomes": 0}
    body = {key: value for key, value in bundle.items() if key != "bundle_id"}
    bundle["bundle_id"] = acceptance._hash(body)
    with pytest.raises(ValueError, match="REGISTERED_ACCEPTANCE_CRITERIA"):
        acceptance.readiness(bundle)


def test_maturity_rejects_revised_frozen_entry_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record(tmp_path, monkeypatch)
    facts = {day: timing(day) for day in SESSIONS}
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        facts[previous]["next_verified_session"] = following
    facts[SESSIONS[1]]["open_at"] = SESSIONS[1] + "T09:16:00+05:30"
    with pytest.raises(ValueError, match="FROZEN_ENTRY_TIMING_REVISION"):
        mature(tmp_path, monkeypatch, official_timings=facts, require_official_sessions=True)


def test_complete_frozen_cohort_required_for_reference_costs() -> None:
    keys = [KEY, "NSE_EQ|INE009A01021"]
    cohort = forward._hash(sorted(keys))
    forecasts = {
        str(index): {
            "model_id": "TEST_ONLY",
            "session": SESSIONS[0],
            "key": key,
            "frozen_scored_cohort_sha256": cohort,
            "prospective_eligible": True,
            "score": 0.4 + index * 0.2,
            "frozen_selection_ranks": {"score": index + 1},
        }
        for index, key in enumerate(keys)
    }
    outcomes = [
        {
            "forecast_id": str(index),
            "target_return": str(0.1 - index * 0.05),
            "entry_session": SESSIONS[1],
            "target_session": SESSIONS[-1],
        }
        for index in range(2)
    ]
    missing = forward._ranking_statistics(forecasts, outcomes[:1])
    assert missing["available"] is False
    assert missing["incomplete_or_excluded_cohorts"] == 1
    complete = forward._ranking_statistics(forecasts, outcomes)
    assert complete["complete_frozen_cohorts"] == 1
    scenario = next(
        item
        for item in complete["by_model"]["TEST_ONLY"]["reference_cost_scenarios"]
        if item["selection"] == "score_top20"
        and item["round_trip_cost_bps_assumption"] == 25
        and item["slippage_bps_each_side_assumption"] == 5
    )
    assert scenario["selected_security_count_range"] == [2, 2]
    assert scenario["gross_price_reference_return"] == pytest.approx(0.075)
    assert scenario["net_price_reference_return"] == pytest.approx(0.0715)
    assert complete["profitability_verified"] is False


def test_mixed_frozen_models_cannot_satisfy_single_model_acceptance() -> None:
    bundle = acceptance.evidence_bundle(
        "first",
        "dataset",
        "protocol",
        {
            "model_ids": ["first", "second"],
            "protocol_ids": ["protocol"],
        },
    )
    result = acceptance.readiness(bundle)
    assert result["research_requirements"]["single_frozen_model_and_protocol"] is False
    assert result["independent_acceptance"] is False


def test_pinned_external_review_path_is_only_software_evidence(
    tmp_path: Path,
) -> None:
    """TEST_ONLY trust fixture; this does not approve genuine AlphaLens research."""
    import hashlib

    forward.summary(tmp_path)
    bundle = acceptance.evidence_bundle(
        "fixture",
        "fixture",
        "fixture",
        {
            "last_forecast_recorded_at": "2025-01-02T12:00:00+00:00",
        },
    )
    document = tmp_path / "fixture-review.txt"
    document.write_text("TEST_ONLY software validation, not independent model acceptance.")
    checksum = hashlib.sha256(document.read_bytes()).hexdigest()
    registry = {
        "reviewers": {
            "fixture-human": {
                "operator_verified_external_identity": True,
                "independence_evidence_sha256": "a" * 64,
                "approved_bundle_id": bundle["bundle_id"],
                "review_document_sha256": checksum,
                "review_document": document.name,
            }
        }
    }
    trust = tmp_path / "independent-review-trust.json"
    trust.write_text(json.dumps(registry))
    for path in (document, trust):
        path.chmod(0o600)
    review = {
        "bundle_id": bundle["bundle_id"],
        "reviewer_id": "fixture-human",
        "reviewed_at": "2025-01-03T12:00:00+00:00",
        "independence_statement": "TEST_ONLY isolated software fixture",
        "review_document_sha256": checksum,
        "decision": "APPROVE_RESEARCH_EVIDENCE",
    }
    result = acceptance.readiness(bundle, review_root=tmp_path, review=review)
    assert result["independent_review"] == "EVIDENCE_IMPORTED"
    assert result["independent_acceptance"] is False
    assert result["accepted_top_5_10_20"] is False
    with pytest.raises(ValueError, match="PRECEDES_EVIDENCE"):
        acceptance.import_review(
            tmp_path, bundle, {**review, "reviewed_at": "2025-01-01T12:00:00+00:00"}
        )
    registry["reviewers"]["fixture-human"]["operator_verified_external_identity"] = "green"
    trust.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="PINNED_INDEPENDENT_REVIEW"):
        acceptance.import_review(tmp_path, bundle, review)


def test_operational_maturity_requires_dated_official_session_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    result = mature(tmp_path, monkeypatch, require_official_sessions=True)
    assert result["pending"] == 1
    assert result["inserted"] == 0
    facts = {day: timing(day) for day in SESSIONS}
    for prior, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        facts[prior]["next_verified_session"] = following
    incomplete = {day: dict(value) for day, value in facts.items()}
    incomplete[SESSIONS[1]]["next_verified_session"] = SESSIONS[3]
    assert (
        mature(tmp_path, monkeypatch, require_official_sessions=True, official_timings=incomplete)[
            "pending"
        ]
        == 1
    )
    result = mature(tmp_path, monkeypatch, require_official_sessions=True, official_timings=facts)
    assert result["inserted"] == 1


def test_companion_forecast_requires_exact_sixteen_feature_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = record(
        tmp_path,
        monkeypatch,
        feature_version="nse.adjusted-price-only.16.v2",
        feature_names=list(FEATURE_NAMES[:16]),
        vector=[0.01] * 16,
    )
    assert result["inserted"] == 1
    mature(tmp_path, monkeypatch)
    metrics = forward.summary(tmp_path)["metrics"]
    assert metrics["missing_registered_cohort_regime_outcomes"] == 1
    assert metrics["positive_cross_regime_stability"] is False
    with pytest.raises(ValueError, match="FEATURE"):
        record(
            tmp_path / "bad",
            monkeypatch,
            feature_version="nse.adjusted-price-only.16.v2",
            feature_names=list(reversed(FEATURE_NAMES[:16])),
            vector=[0.01] * 16,
        )


@pytest.mark.parametrize(
    "entry",
    [
        {"entry_session": "2025-01-06"},
        {"entry_open_at": "2025-01-03T09:16:00+05:30"},
    ],
)
def test_scorer_entry_must_match_frozen_official_next_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="ENTRY_TIMING_LINEAGE_MISMATCH"):
        record(tmp_path, monkeypatch, **entry)
    assert forward.summary(tmp_path)["forecasts"] == 0


def test_scorer_timing_ineligible_flag_cannot_be_promoted_by_calendar_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record(
        tmp_path,
        monkeypatch,
        eligible_for_prospective=False,
        entry_session=SESSIONS[1],
        entry_open_at=timing(SESSIONS[1])["open_at"],
    )
    status = forward.summary(tmp_path)
    assert status["eligible_forecasts"] == 0
    assert status["research_only_forecast_count"] == 1
    assert mature(tmp_path, monkeypatch)["ineligible"] == 1


def test_known_action_resolves_pending_into_unscorable_without_fake_maturity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record(tmp_path, monkeypatch)
    mature(tmp_path, monkeypatch, excluded_sessions={KEY: [SESSIONS[3]]})
    status = forward.summary(tmp_path)
    assert status["outcomes"] == 0
    assert status["pending_outcome_count"] == 0
    assert status["unscorable_outcome_count"] == 1
    assert status["outstanding_forecasts"] == []


def test_frozen_actual_clock_and_idempotent_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    assert record(tmp_path, monkeypatch)["replayed"] == 1
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 3, 6, tzinfo=UTC))
    assert (
        forward.append_forecasts(
            tmp_path, "TEST_MODEL", "TEST_DATA", "TEST_PROTOCOL", [score()], RECEIVED
        )["replayed"]
        == 1
    )
    with sqlite3.connect(tmp_path / "experimental-v2-prospective.sqlite3") as db:
        body = json.loads(db.execute("SELECT body FROM experimental_forecasts").fetchone()[0])
        assert body["recorded_at"] == NOW.isoformat()
        assert body["prospective_eligible"] is True
        assert body["protocol_id"] == "TEST_PROTOCOL"
        for query in (
            "DELETE FROM experimental_forecasts",
            "UPDATE experimental_forecasts SET body='{}'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_FORECAST"):
                db.execute(query)


@pytest.mark.parametrize("field", ["decision_at", "recorded_at", "forecast_at"])
def test_backdating_forbidden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    with pytest.raises(ValueError, match="CALLER_FORECAST_CLOCK_FORBIDDEN"):
        record(tmp_path, monkeypatch, **{field: RECEIVED.isoformat()})


@pytest.mark.parametrize(
    "updates,error",
    [
        ({"vector": []}, "COMPLETE_FINITE"),
        ({"vector": [float("nan")] * len(FEATURE_NAMES)}, "COMPLETE_FINITE"),
        ({"score": float("nan")}, "FINITE_UNCALIBRATED"),
        ({"feature_hash": "b" * 64}, "FEATURE_HASH"),
        ({"session": "2030-01-01"}, "OBSERVATION_AFTER_SOURCE"),
        ({"inference_at": "2030-01-01T00:00:00Z"}, "INFERENCE_SOURCE"),
        ({"feature_names": list(reversed(FEATURE_NAMES))}, "FEATURE_CONTRACT"),
        ({"model_id": "DIFFERENT_MODEL"}, "FROZEN_FORECAST_LINEAGE"),
        ({"protocol_id": "DIFFERENT_PROTOCOL"}, "FROZEN_FORECAST_LINEAGE"),
    ],
)
def test_invalid_features_or_future_input_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, updates: dict[str, Any], error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        record(tmp_path, monkeypatch, **updates)


def test_missing_timing_is_visible_research_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch, next_session_timing=None)
    assert forward.summary(tmp_path)["eligible_forecasts"] == 0
    assert mature(tmp_path, monkeypatch)["ineligible"] == 1


def test_elapsed_first_session_cannot_be_shifted_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = timing(SESSIONS[1])
    evidence["open_at"] = SESSIONS[0] + "T09:15:00+05:30"
    with pytest.raises(ValueError, match="CONTRADICTORY_SESSION_TIMING"):
        record(tmp_path, monkeypatch, next_session_timing=evidence)
    evidence = timing(SESSIONS[1])
    evidence["intervening_dates_verified_closed"] = False
    record(tmp_path, monkeypatch, next_session_timing=evidence)
    assert forward.summary(tmp_path)["eligible_forecasts"] == 0


def test_missing_future_slot_remains_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    assert mature(tmp_path, monkeypatch, rows()[:-1])["pending"] == 1
    assert forward.summary(tmp_path)["outcomes"] == 0


def test_correction_and_later_action_append_without_rewriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    assert mature(tmp_path, monkeypatch)["inserted"] == 1
    assert mature(tmp_path, monkeypatch)["replayed"] == 1
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 11, 12, tzinfo=UTC))
    result = forward.reconcile(
        tmp_path,
        rows(),
        SESSIONS,
        datetime(2025, 1, 11, 11, tzinfo=UTC),
        {KEY: [SESSIONS[-1]]},
        require_official_sessions=False,  # Explicit TEST_ONLY revision fixture.
    )
    assert result["corrections"] == result["unscorable"] == 1
    summary = forward.summary(tmp_path)
    assert summary["outcome_revision_count"] == 2
    assert summary["outcomes"] == 0 and summary["unscorable_outcome_count"] == 1
    with (
        sqlite3.connect(tmp_path / "experimental-v2-prospective.sqlite3") as db,
        pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_OUTCOME"),
    ):
        db.execute("DELETE FROM experimental_outcomes")


def test_changed_score_cannot_replace_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="IMMUTABLE_FORECAST_REPLAY_CONFLICT"):
        record(tmp_path, monkeypatch, score=0.7)


def test_no_outcomes_cannot_claim_edge_or_acceptance(tmp_path: Path) -> None:
    prospective = forward.summary(tmp_path)
    result = acceptance.readiness(acceptance.evidence_bundle("m", "d", "p", prospective))
    assert result["predictive_edge"] == "NO_DEMONSTRATED_EDGE"
    assert result["economic_edge"] == "PENDING"
    assert result["independent_acceptance"] is result["accepted_top_5_10_20"] is False
    assert prospective["metrics"]["mean_date_rank_ic"] is None


def test_review_without_external_trust_or_forged_document_fails(tmp_path: Path) -> None:
    bundle = acceptance.evidence_bundle("m", "d", "p", {})
    with pytest.raises(ValueError, match="EXTERNAL_REVIEWER_NOT_CONFIGURED"):
        acceptance.import_review(tmp_path, bundle, {"decision": "APPROVE_RESEARCH_EVIDENCE"})
    forward.summary(tmp_path)
    registry = {
        "reviewers": {
            "external": {
                "operator_verified_external_identity": True,
                "independence_evidence_sha256": "a" * 64,
                "approved_bundle_id": bundle["bundle_id"],
                "review_document_sha256": "b" * 64,
                "review_document": "review.txt",
            }
        }
    }
    (tmp_path / "independent-review-trust.json").write_text(json.dumps(registry))
    (tmp_path / "review.txt").write_text("TEST_ONLY forged review")
    for path in (tmp_path / "independent-review-trust.json", tmp_path / "review.txt"):
        path.chmod(0o600)
    review = {
        "reviewer_id": "external",
        "bundle_id": bundle["bundle_id"],
        "independence_statement": "TEST_ONLY reviewer fixture",
        "review_document_sha256": "b" * 64,
        "decision": "APPROVE_RESEARCH_EVIDENCE",
    }
    with pytest.raises(ValueError, match="DOCUMENT_HASH_MISMATCH"):
        acceptance.import_review(tmp_path, bundle, review)


def test_trust_cannot_be_codex_or_test_reviewer(tmp_path: Path) -> None:
    bundle = acceptance.evidence_bundle("m", "d", "p", {})
    forward.summary(tmp_path)
    (tmp_path / "independent-review-trust.json").write_text('{"reviewers":{}}')
    (tmp_path / "independent-review-trust.json").chmod(0o600)
    with pytest.raises(ValueError, match="INDEPENDENT_EXTERNAL_HUMAN"):
        acceptance.import_review(tmp_path, bundle, {"reviewer_id": "CODEX_SELF_APPROVAL"})


def test_bundle_tampering_cannot_reuse_review(tmp_path: Path) -> None:
    bundle = acceptance.evidence_bundle("m", "d", "p", {})
    bundle["dataset_id"] = "different"
    with pytest.raises(ValueError, match="BUNDLE_HASH_MISMATCH"):
        acceptance.import_review(tmp_path, bundle, {})


def test_runtime_clock_cannot_move_before_frozen_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 2, 11, 30, tzinfo=UTC))
    with pytest.raises(ValueError, match="CLOCK_ROLLBACK"):
        forward.append_forecasts(
            tmp_path, "TEST_MODEL", "TEST_DATA", "TEST_PROTOCOL", [score()], RECEIVED
        )


def test_block_uncertainty_retains_shared_dates_and_frozen_baselines() -> None:
    forecasts: dict[str, Any] = {}
    outcomes = []
    for day in range(20):
        for member in range(6):
            identifier = f"TEST_ONLY_{day}_{member}"
            positive = member >= 3
            forecasts[identifier] = {
                "session": f"2025-01-{day + 1:02}",
                "recorded_at": f"2025-01-{day + 1:02}T12:00:00+00:00",
                "vector": [0.1] * len(FEATURE_NAMES),
                "score": 0.9 if positive else 0.1,
                "baseline_majority_score": 0.0,
                "baseline_mean_reversion_score": float(not positive),
                "baseline_momentum_score": float(not positive),
            }
            outcomes.append(
                {
                    "forecast_id": identifier,
                    "target": int(positive),
                    "target_return": str(member - 2),
                }
            )
    evidence = forward._uncertainty(forecasts, outcomes)
    assert evidence["rank_ic_dates"] == 20
    assert evidence["date_block_bootstrap_improvement_intervals"]["baseline_momentum_score"] == [
        1.0,
        1.0,
    ]
    assert evidence["date_block_bootstrap_improvement_intervals"]["baseline_majority_score"] == [
        0.5,
        0.5,
    ]
    assert evidence["positive_cross_regime_stability"] is False
