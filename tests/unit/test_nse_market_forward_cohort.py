"""TEST_ONLY global forward declarations, future guards and complete-cohort metrics."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import initialize
from workers.nse_market import engine, forward_cohort


def fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, dict[str, Any]]]:
    root = tmp_path / "TEST_ONLY_private_forward"
    initialize(root)
    now = datetime.now(UTC)
    candidates = []
    forecasts = {}
    for index, score in enumerate((0.9, 0.7, 0.1)):
        key = f"NSE_EQ|INE{index:09d}"
        row = {
            "key": key,
            "symbol": f"TEST_ONLY_{index}",
            "model_id": "a" * 64,
            "session": str((now - timedelta(days=1)).date()),
            "score": score,
            "baseline_majority_score": 0.6,
            "baseline_momentum_score": (0.2, 0.1, 0.9)[index],
            "baseline_mean_reversion_score": (0.8, 0.9, 0.1)[index],
            "baseline_risk_score": 0.6,
            "source_observed_at": (now - timedelta(minutes=10)).isoformat(),
            "inference_at": (now - timedelta(minutes=5)).isoformat(),
            "entry_open_at": (now + timedelta(days=2)).isoformat(),
            "entry_session": str((now + timedelta(days=2)).date()),
            "feature_hash": str(index) * 64,
            "source_sha256": "b" * 64,
            "applicability": "TEST_ONLY_NOT_A_REAL_NSE_FORECAST",
        }
        candidates.append(row)
        forecasts[str(index)] = {
            **row,
            "recorded_at": now.isoformat(),
            "prospective_eligible": True,
        }
    folder = root / "scores"
    folder.mkdir()
    path = folder / "TEST_ONLY.json"
    engine._checked(
        path,
        {
            "model_id": "a" * 64,
            "model_sha256": "e" * 64,
            "dataset_id": "c" * 64,
            "feature_version": "TEST_ONLY",
            "observation_session": candidates[0]["session"],
            "candidates": candidates,
        },
    )
    engine._pointer(root, "scores-latest.json", path)
    monkeypatch.setattr(
        forward_cohort, "guard", lambda: {"upper_at": now.isoformat(), "lower_at": now.isoformat()}
    )
    outcomes: dict[str, dict[str, Any]] = {}
    monkeypatch.setattr(forward_cohort, "_forecasts", lambda unused: (forecasts, outcomes))
    return root, outcomes


def test_declaration_has_actual_clock_capped_global_top_lists_and_frozen_baselines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = fixture(tmp_path, monkeypatch)
    before = datetime.now(UTC)
    value = forward_cohort.freeze_current(root)
    assert before <= datetime.fromisoformat(value["recorded_at"]) <= datetime.now(UTC)
    assert len(value["members"]) == 3 and value["accepted_ml"] is False
    assert all(len(value["frozen_selection"]["score"][str(n)]) == 3 for n in (5, 10, 20))
    assert value["frozen_selection"]["score"]["5"][0] == "NSE_EQ|INE000000000"
    assert value["frozen_selection"]["baseline_momentum_score"]["5"][0] == "NSE_EQ|INE000000002"
    repeat = forward_cohort.freeze_current(root)
    assert repeat["replayed"] is True and repeat["recorded_at"] == value["recorded_at"]
    assert len(list((root / "global-cohorts").glob("*.json"))) == 1


def test_pending_outcomes_never_become_global_performance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, outcomes = fixture(tmp_path, monkeypatch)
    declaration = forward_cohort.freeze_current(root)
    result = forward_cohort.evaluate(declaration, outcomes)
    assert result["pending_outcomes"] == 3 and result["matured_outcomes"] == 0
    assert result["global_metrics"] is None and result["selection_returns"] is None
    assert forward_cohort.summary(root)["shard_rank_metrics_averaged"] is False


def test_complete_cohort_metrics_use_exact_members_and_cost_assumption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, outcomes = fixture(tmp_path, monkeypatch)
    declaration = forward_cohort.freeze_current(root)
    for index, ret in enumerate((0.1, -0.02, 0.05)):
        outcomes[str(index)] = {
            "status": "MATURED_PRICE_REFERENCE_RETURN",
            "target": int(ret > 0),
            "target_return": str(ret),
            "revision": 1,
        }
    result = forward_cohort.evaluate(declaration, outcomes)
    assert result["matured_outcomes"] == 3
    assert result["global_metrics"]["score"]["balanced_accuracy"] == pytest.approx(0.25)
    assert result["global_metrics"]["baseline_momentum_score"][
        "balanced_accuracy"
    ] == pytest.approx(0.75)
    expected = (0.1 - 0.02 + 0.05) / 3
    assert result["selection_returns"]["score"]["20"][
        "gross_price_component_return"
    ] == pytest.approx(expected)
    assert result["selection_returns"]["score"]["20"]["assumed_net_return"] == pytest.approx(
        expected - 0.0035
    )
    assert result["selection_returns"]["score"]["20"]["actual_realized_profit"] is False
    assert result["accepted_ml"] is False


def test_missing_or_excluded_selected_member_does_not_get_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, outcomes = fixture(tmp_path, monkeypatch)
    declaration = forward_cohort.freeze_current(root)
    outcomes["0"] = {
        "status": "MATURED_PRICE_REFERENCE_RETURN",
        "target": 1,
        "target_return": "0.1",
    }
    outcomes["1"] = {"status": "UNSCORABLE_KNOWN_ACTION"}
    result = forward_cohort.evaluate(declaration, outcomes)
    assert (
        result["matured_outcomes"] == 1
        and result["excluded_outcomes"] == 1
        and result["pending_outcomes"] == 1
    )
    assert result["global_metrics"] is None and result["selection_returns"] is None


def test_result_revisions_append_and_do_not_rewrite_pending_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, outcomes = fixture(tmp_path, monkeypatch)
    declaration = forward_cohort.freeze_current(root)
    directory = root / "global-results" / declaration["declaration_id"]
    previous = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    assert forward_cohort.reconcile(root)["global_result_versions_replayed"] == 1
    outcomes["0"] = {
        "status": "MATURED_PRICE_REFERENCE_RETURN",
        "target": 1,
        "target_return": "0.1",
        "revision": 1,
    }
    assert forward_cohort.reconcile(root)["global_result_versions_written"] == 1
    assert all((directory / name).read_bytes() == value for name, value in previous.items())
    assert len(list(directory.glob("*.json"))) == 2


def test_protocol_changes_refuse_new_declarations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(forward_cohort, "PROTOCOL_SHA256", "f" * 64)
    with pytest.raises(ValueError, match="REGISTERED_PROTOCOL_CHANGED"):
        forward_cohort.freeze_current(root)
