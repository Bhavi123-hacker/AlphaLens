"""TEST_ONLY experimental scores never substitute incompatible risk/preferences measures."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from workers.personal.contracts import ManualEntry
from workers.personal.store import PersonalStore

from alphalens_api import experimental_nse


def test_personalization_keeps_risk_unknown_and_model_scores_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = PersonalStore(tmp_path / "TEST_ONLY_owned", "TEST_ONLY_owner")
    owned.initialize()
    key = "NSE_EQ|INE000000001"
    portfolio = owned.create_portfolio("TEST_ONLY_manual")
    owned.record(
        portfolio["id"],
        ManualEntry(
            request_id=uuid4().hex,
            kind="OPENING_POSITION",
            instrument_key=key,
            session=date(2024, 1, 2),
            quantity="5",
            price="100",
            fees_known=True,
        ),
        {"provider_key": key, "symbol": "TEST_ONLY", "isin": "INE000000001"},
    )
    monkeypatch.setattr(experimental_nse, "store", lambda request: owned)
    request: Any = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(personal_root=owned.root))
        )
    )
    data = {
        "candidates": [
            {
                "key": key,
                "score": 0.6,
                "volatility_percent": 0.5,
                "drawdown_percent": -1,
                "preference_metrics": {"gross_price": 100, "volume": 100000},
            }
        ]
    }
    result = experimental_nse.personalized(data, request)["candidates"][0]
    assert result["score"] == 0.6
    assert result["held"] and result["holdings"][0]["quantity"] == "5"
    assert "maximum_drawdown_percent" in result["preferences"]["missing"]
    assert result["preferences"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["portfolio_implication"] == (
        "ALREADY_HELD_REVIEW_CONCENTRATION_WITH_DATED_PORTFOLIO_MARKS"
    )
