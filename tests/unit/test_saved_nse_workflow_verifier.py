"""TEST_ONLY replay corruption checks; no live source or model training."""

import copy
from datetime import date, timedelta
from typing import Any

import pytest
from scripts.verify_saved_nse_workflow import numerical_replay
from workers.experimental_nse_v2 import models
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, build


def fixture(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], ...]:
    rows = []
    sessions = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(61)]
    histories: dict[str, list[dict[str, Any]]] = {}
    for key, symbol in (
        ("NSE_EQ|INE000000002", "TEST_ONLY_B"),
        ("NSE_EQ|INE000000001", "TEST_ONLY_A"),
    ):
        histories[key] = []
        for index, session in enumerate(sessions):
            row = {
                "session": session,
                "open": str(100 + index),
                "high": str(103 + index),
                "low": str(99 + index),
                "close": str(101 + index),
                "volume": 1000,
            }
            histories[key].append(row)
            rows.append({**row, "key": key, "symbol": symbol})
    monkeypatch.setattr(models, "predict_vector", lambda model, vector: (0.6, []))
    model = {
        "model_id": "TEST_ONLY_MODEL",
        "protocol_id": "TEST_ONLY_PROTOCOL",
        "feature_version": "TEST_ONLY_FEATURE_VERSION",
        "target_version": "TEST_ONLY_TARGET_VERSION",
        "feature_names": list(LOCAL_FEATURE_NAMES),
    }
    samples = build(rows, sessions, include_context=False).samples
    candidates = [
        {
            **model,
            "key": sample.key,
            "symbol": sample.symbol,
            "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
            "session": sample.session,
            "features": list(sample.vector),
            "score": 0.6,
            "risk": sample.risk,
        }
        for sample in samples
    ]
    scores = {**model, "observation_session": sessions[-1], "candidates": candidates}
    view = {"provider_requests": 0, "histories": histories}
    return view, scores, model


def test_replay_checks_real_feature_math_and_deterministic_risk_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, scores, model = fixture(monkeypatch)
    before = copy.deepcopy((view, scores, model))
    report = numerical_replay(view, scores, model)
    assert report["state"] == "REPLAY_VERIFIED"
    assert report["maximum_feature_absolute_error"] == 0
    assert report["maximum_score_absolute_error"] == 0
    assert report["session_slots"] == 61
    assert all(
        keys == ["NSE_EQ|INE000000001", "NSE_EQ|INE000000002"]
        for keys in report["replayed_saved_top_n"].values()
    )
    assert (view, scores, model) == before


def test_replay_detects_changed_candle_missing_slot_and_changed_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, scores, model = fixture(monkeypatch)
    view["histories"]["NSE_EQ|INE000000001"][-1]["close"] = "162"
    report = numerical_replay(view, scores, model)
    assert report["state"] == "REPLAY_MISMATCH"
    assert report["failures"] == [
        {"key": "NSE_EQ|INE000000001", "reason": "SAVED_NUMERICAL_REPLAY_MISMATCH"}
    ]
    view, scores, model = fixture(monkeypatch)
    view["histories"]["NSE_EQ|INE000000001"][-2]["close"] = None
    assert numerical_replay(view, scores, model)["failures"] == [
        {"key": "NSE_EQ|INE000000001", "reason": "REPLAY_FEATURES_UNAVAILABLE"}
    ]
    view, scores, model = fixture(monkeypatch)
    scores["candidates"][0]["score"] = 0.7
    assert numerical_replay(view, scores, model)["maximum_score_absolute_error"] > 0.09


def test_replay_rejects_wrong_source_or_target_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    view, scores, model = fixture(monkeypatch)
    scores["candidates"][0]["target_version"] = "TEST_ONLY_INCOMPATIBLE"
    with pytest.raises(ValueError, match="SOURCE_TARGET_LINEAGE"):
        numerical_replay(view, scores, model)
