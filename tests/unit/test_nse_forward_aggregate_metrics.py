"""TEST_ONLY aggregate math and immutable cohort denominators; no NSE results."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from test_experimental_nse_v2_forward import RECEIVED, mature, record, score
from test_nse_readonly_evaluation import context
from workers.experimental_nse_v2 import forward
from workers.nse_market import engine, forward_cohort

from alphalens_api import nse_evaluation as evaluation


def pairs(scores: list[float], targets: list[int]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [({"score": s}, {"target": t}) for s, t in zip(scores, targets, strict=True)]


def test_classification_confusion_denominators_and_auc_ties() -> None:
    value = evaluation._metrics(pairs([0.9, 0.6, 0.4, 0.4], [1, 0, 1, 0]), "score")
    assert value["samples"] == 4
    assert value["accuracy"] == value["balanced_accuracy"] == 0.5
    assert value["precision"] == value["recall"] == value["f1"] == 0.5
    assert value["roc_auc"] == 0.625
    assert value["brier_score"] == pytest.approx((0.01 + 0.36 + 0.36 + 0.16) / 4)
    assert sum(item["samples"] for item in value["score_bins"]) == 4


@pytest.mark.parametrize(
    ("scores", "targets", "precision", "recall", "f1"),
    [
        ([], [], None, None, None),
        ([0.1], [0], None, None, None),
        ([0.8], [0], 0, None, 0),
        ([0.1], [1], None, 0, 0),
        ([1.0], [1], 1, 1, 1),
    ],
)
def test_empty_single_class_and_undefined_metrics(
    scores: list[float],
    targets: list[int],
    precision: float | None,
    recall: float | None,
    f1: float | None,
) -> None:
    value = evaluation._metrics(pairs(scores, targets), "score")
    assert value["precision"] == precision
    assert value["recall"] == recall
    assert value["f1"] == f1
    assert value["roc_auc"] is value["balanced_accuracy"] is None
    if scores == [1.0]:
        assert value["score_bins"][-1]["samples"] == 1


def test_missing_invalid_scores_and_targets_are_excluded() -> None:
    invalid: list[tuple[dict[str, Any], dict[str, Any]]] = [
        ({"score": s}, {"target": 1}) for s in (True, float("nan"), float("inf"), -1, 2, None)
    ]
    invalid += [({"score": 0.5}, {"target": target}) for target in (True, None, 2, 1.0)]
    value = evaluation._metrics([*invalid, *pairs([0.5], [1])], "score")
    assert value["samples"] == 1
    assert value["excluded_invalid_or_missing"] == 10


def test_baseline_differences_use_identical_matched_samples() -> None:
    sample = pairs([0.9, 0.1, 0.9], [1, 0, 0])
    sample[0][0]["baseline_majority_score"] = 0.1
    sample[1][0]["baseline_majority_score"] = 0.1
    value = evaluation._baseline_comparisons(sample)["baseline_majority_score"]
    assert value["matched_samples"] == 2
    assert value["excluded_missing_pairs"] == 1
    assert value["candidate"]["accuracy"] == 1
    assert value["candidate_minus_baseline"]["accuracy"] == 0.5


def declaration() -> dict[str, Any]:
    members = [
        {"key": f"TEST_ONLY_{i:02d}", "forecast_id": f"TEST_ONLY_id{i}", "score": 1 - i / 100}
        for i in range(7)
    ]
    return {
        "members": members,
        "declaration_id": "TEST_ONLY",
        "model_id": "TEST_MODEL",
        "observation_session": "2025-01-02",
        "frozen_selection": {
            "score": {str(n): [m["key"] for m in members[:n]] for n in (5, 10, 20)}
        },
    }


def test_top_n_requires_whole_cohort_and_preserves_capped_denominators() -> None:
    frozen = declaration()
    qualified = {m["forecast_id"]: {"target": i % 2} for i, m in enumerate(frozen["members"])}
    pending = dict(qualified)
    pending.pop("TEST_ONLY_id6")  # Missing member outside Top5 still blocks all cohort statistics.
    value = evaluation._selection_metrics(frozen, pending)
    assert value["complete"] is False
    assert value["selections"]["score"]["5"]["qualified_selected_outcomes"] == 5
    assert value["selections"]["score"]["5"]["hit_rate"] is None
    complete = evaluation._selection_metrics(frozen, qualified)
    assert complete["complete"] is True
    assert complete["selections"]["score"]["5"]["hit_rate"] == 2 / 5
    assert complete["selections"]["score"]["20"]["selected_securities"] == 7
    assert complete["selections"]["score"]["20"]["hit_rate"] == 3 / 7
    assert complete["equal_cohort_hit_rate"] == 3 / 7


def test_frozen_selection_mismatch_fails_instead_of_reranking() -> None:
    frozen = declaration()
    frozen["frozen_selection"]["score"]["5"].reverse()
    with pytest.raises(ValueError, match="FROZEN_GLOBAL_SELECTION"):
        evaluation._selection_metrics(frozen, {})


def test_missing_global_declaration_is_readonly_and_not_reconstructed(tmp_path: Path) -> None:
    before = set(tmp_path.rglob("*"))
    result = evaluation._top_n(tmp_path, {}, {}, datetime(2025, 1, 3, tzinfo=UTC))
    assert result["declarations"] == result["complete_declarations"] == 0
    assert result["pooled_hit_rate"] is None
    assert result["missing_evidence"]
    assert set(tmp_path.rglob("*")) == before


def test_global_reader_validates_frozen_forecast_lineage_and_cutoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "global-cohorts"
    folder.mkdir()
    (folder / "TEST_ONLY.json").write_text("{}", encoding="utf-8")
    frozen = declaration()
    frozen.update(
        protocol_id="TEST_PROTOCOL",
        recorded_at="2025-01-02T13:00:00+00:00",
        decision_clock={"upper_at": "2025-01-02T13:01:00+00:00"},
    )
    forecasts = {}
    for member in frozen["members"]:
        member.update(
            original_forecast_recorded_at="2025-01-02T12:00:00+00:00",
            entry_session="2025-01-03",
            entry_open_at="2025-01-03T09:15:00+05:30",
            feature_hash="TEST_FEATURE",
            source_sha256="TEST_SOURCE",
        )
        forecasts[member["forecast_id"]] = {
            **member,
            "model_id": frozen["model_id"],
            "prospective_eligible": True,
            "session": frozen["observation_session"],
            "recorded_at": member["original_forecast_recorded_at"],
            "next_session_timing": {
                "session": member["entry_session"],
                "open_at": member["entry_open_at"],
            },
        }
    monkeypatch.setattr(engine, "_read", lambda p: frozen)
    monkeypatch.setattr(forward_cohort, "protocol_id", lambda: "TEST_PROTOCOL")
    result = evaluation._top_n(tmp_path, forecasts, {}, datetime(2025, 1, 3, tzinfo=UTC))
    assert result["declarations"] == 1
    assert result["results"][0]["complete"] is False
    earlier = evaluation._top_n(tmp_path, forecasts, {}, datetime(2025, 1, 2, tzinfo=UTC))
    assert earlier["declarations"] == 0
    frozen["members"][0]["source_sha256"] = "WRONG_TEST_SOURCE"
    with pytest.raises(ValueError, match="GLOBAL_DECLARATION_FORECAST_LINEAGE"):
        evaluation._top_n(tmp_path, forecasts, {}, datetime(2025, 1, 3, tzinfo=UTC))


def test_overlapping_outcome_is_bound_to_its_original_forecast_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, v2 = tmp_path / "TEST_ONLY_market", tmp_path / "TEST_ONLY_v2"
    record(v2 / "price-only", monkeypatch)
    shard = root / "expanded-forecasts/TEST_ONLY"
    monkeypatch.setattr(forward, "_utc_now", lambda: datetime(2025, 1, 2, 12, 1, tzinfo=UTC))
    forward.append_forecasts(shard, "TEST_MODEL", "TEST_DATA", "TEST_PROTOCOL", [score()], RECEIVED)
    mature(shard, monkeypatch)
    context(root, monkeypatch)
    result = evaluation.read(root, v2, at=datetime(2025, 1, 11, tzinfo=UTC))
    assert result["raw_forecast_records"] == 2
    assert result["unique_decisions"] == result["matured_outcomes"] == 1
    assert result["metrics"]["score"]["samples"] == 1


def test_maturity_rejects_a_rebound_outcome_identifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    mature(tmp_path, monkeypatch)
    with forward._connection(tmp_path) as conn:
        f = forward._verified(conn.execute("SELECT * FROM experimental_forecasts").fetchone())
        outcome = forward._verified(conn.execute("SELECT * FROM experimental_outcomes").fetchone())
    outcome["forecast_id"] = "TEST_ONLY_WRONG_FORECAST"
    assert (
        evaluation._mature(tmp_path, f, outcome, datetime(2025, 1, 11, tzinfo=UTC), {}, {}) is False
    )
