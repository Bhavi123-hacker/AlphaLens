"""TEST_ONLY manual lots prove cost concentration stays separate from model scores/valuation."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from workers.personal.contracts import ManualEntry
from workers.personal.store import PersonalStore

from alphalens_api import experimental_nse, experimental_nse_v2


def test_v2_explains_existing_cost_concentration_without_valuing_or_reordering_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = PersonalStore(tmp_path / "TEST_ONLY_owner", "TEST_ONLY_operator")
    owned.initialize()
    key = "NSE_EQ|INE000000001"
    portfolio = owned.create_portfolio("TEST_ONLY manual lots")
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
    monkeypatch.setattr(experimental_nse_v2, "store", lambda request: owned)
    request: Any = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(personal_root=owned.root))
        )
    )
    result = experimental_nse_v2.personalized_workspace(
        {
            "candidates": [
                {"key": key, "score": 0.4, "preference_metrics": {}},
                {"key": "NSE_EQ|INE000000002", "score": 0.3, "preference_metrics": {}},
            ]
        },
        request,
    )
    assert [row["score"] for row in result["candidates"]] == [0.4, 0.3]
    context = result["candidates"][0]["portfolio_context"][0]
    assert context["cost_allocation_percent"] == 100.0
    assert context["concentration_review"] is True
    assert context["allocation_basis"] == "REMAINING_FIFO_COST_NOT_MARKET_WEIGHT"
    assert "market_value" not in context and result["candidates"][1]["portfolio_context"] == []
