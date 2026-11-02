"""Unit tests for AlphaLens Full-Universe Ingestion, Modeling, and Delivery Suite.

Verifies:
1. Market Regime Classifier (Bull, Bear, High-Vol Choppy, Range)
2. Mathematical Feature Attribution & Linear Decomposition
3. Forward Outcome Maturation Engine & Audit Ledger
4. Multi-Tier Provider Manager & Failover
5. Full-Universe Bulk Ingestion & Corporate Actions Adjustment
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
from ml.explainability.feature_attribution import (
    attribute_linear_prediction,
    compute_global_feature_importances,
)
from sklearn.linear_model import Ridge
from workers.nse_market import bulk_eod, market_regime, provider_manager
from workers.nse_market.forward_maturation_engine import ForwardMaturationEngine
from workers.nse_market.full_universe_ingestion import FullUniverseIngestionEngine


def test_market_regime_classifier() -> None:
    # 1. Trending Bull candles
    bull_candles = [{"session": f"2026-10-{i:02d}", "close": 100.0 + i * 2.0} for i in range(1, 25)]
    bull_state = market_regime.classify_market_regime(bull_candles)
    assert bull_state.regime in (
        market_regime.MarketRegime.BULL_TRENDING,
        market_regime.MarketRegime.LOW_VOL_RANGE,
    )
    assert bull_state.trend_score > 0
    assert 0.0 <= bull_state.recommended_equity_exposure <= 1.0

    # 2. Bear Trending candles
    bear_candles = [{"session": f"2026-10-{i:02d}", "close": 200.0 - i * 3.0} for i in range(1, 25)]
    bear_state = market_regime.classify_market_regime(bear_candles)
    assert bear_state.regime in (
        market_regime.MarketRegime.BEAR_TRENDING,
        market_regime.MarketRegime.HIGH_VOL_CHOPPY,
    )
    assert bear_state.trend_score < 0


def test_feature_attribution_linear_decomposition() -> None:
    # Fit simple ridge model
    np.random.seed(42)
    x = np.random.randn(50, 4)
    y = 0.5 * x[:, 0] - 0.3 * x[:, 1] + 0.1 * x[:, 2]
    model = Ridge(alpha=1.0)
    model.fit(x, y)

    names = ["f1", "f2", "f3", "f4"]
    test_vec = np.array([1.5, -1.0, 0.5, 0.0])
    exp = attribute_linear_prediction(model, test_vec, names, "NSE_EQ|INE002A01018", "2026-11-02")
    assert exp.instrument_key == "NSE_EQ|INE002A01018"
    assert exp.session == "2026-11-02"
    assert len(exp.top_factors) == 4
    assert exp.explanation_method == "EXACT_LINEAR_COEFFICIENT_DECOMPOSITION"

    importances = compute_global_feature_importances(model, names)
    assert len(importances) == 4
    assert sum(i["importance_pct"] for i in importances) == pytest.approx(100.0, rel=1e-2)


def test_forward_maturation_engine(tmp_path: Path) -> None:
    db_file = tmp_path / "test_outcomes.db"
    engine = ForwardMaturationEngine(db_file)

    histories = {
        "NSE_EQ|INE002A01018": [
            {"session": "2026-10-01", "close": 100.0},
            {"session": "2026-10-02", "close": 102.0},
            {"session": "2026-10-05", "close": 105.0},
            {"session": "2026-10-06", "close": 108.0},
            {"session": "2026-10-07", "close": 110.0},
            {"session": "2026-10-08", "close": 112.0},
        ]
    }

    forecasts = [
        {
            "instrument_key": "NSE_EQ|INE002A01018",
            "session": "2026-10-01",
            "horizon_sessions": 5,
            "direction_probability": 0.75,
            "expected_return": 0.08,
        }
    ]

    matured = engine.settle_forecasts(forecasts, histories)
    assert len(matured) == 1
    m = matured[0]
    assert m.forecast_session == "2026-10-01"
    assert m.settlement_session == "2026-10-08"
    assert m.realized_return == pytest.approx(0.12, rel=1e-3)
    assert m.realized_direction == 1
    assert m.directional_hit is True

    summary = engine.generate_audit_summary()
    assert summary["status"] == "AUDIT_RECORDS_SETTLED"
    assert summary["total_matured_forecasts"] == 1
    assert summary["summary_by_horizon"]["H_5"]["directional_hit_rate"] == 1.0


def test_provider_manager_failover(tmp_path: Path) -> None:
    mgr = provider_manager.ProviderManager(bulk_archive_dir=tmp_path)
    cached = [{"session": "2026-11-02", "close": 500.0}]

    res = mgr.acquire_eod_data(
        "NSE_EQ|INE002A01018",
        date(2026, 11, 2),
        upstox_client=None,
        cached_candles=cached,
    )
    assert res.success is True
    assert res.fallback_invoked is True
    assert res.tier_used == provider_manager.ProviderTier.TIER_3_OFFLINE_CACHE


def test_full_universe_ingestion_and_corporate_actions(tmp_path: Path) -> None:
    db_file = tmp_path / "test_univ.db"
    engine = FullUniverseIngestionEngine(target_db_path=db_file)

    # Create synthetic UDiff CSV
    row = dict.fromkeys(bulk_eod.UDIFF_HEADERS, "")
    row.update(
        TradDt="2026-11-02",
        BizDt="2026-11-02",
        Sgmt="CM",
        Src="NSE",
        FinInstrmTp="STK",
        FinInstrmId="500325",
        ISIN="INE002A01018",
        TckrSymb="RELIANCE",
        SctySrs="EQ",
        FinInstrmNm="RELIANCE INDUSTRIES LTD",
        OpnPric="1400.00",
        HghPric="1420.00",
        LwPric="1390.00",
        ClsPric="1410.00",
        TtlTradgVol="50000",
        SsnId="F1",
    )
    import csv
    import io

    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=bulk_eod.UDIFF_HEADERS)
    writer.writeheader()
    writer.writerow(row)
    csv_text = text.getvalue().encode("utf-8")

    ca = [
        bulk_eod.CorporateAction(
            isin="INE002A01018",
            ex_date=date(2026, 11, 1),
            action_type="SPLIT",
            ratio_from=Decimal("1"),
            ratio_to=Decimal("2"),
            adjustment_factor=Decimal("0.5"),
        )
    ]

    summary = engine.ingest_bhavcopy_payload(
        csv_text, "NSE_UDIFF", date(2026, 11, 2), corporate_actions=ca
    )
    assert summary.status == "INGESTION_SUCCESS"
    assert summary.ordinary_equities_saved == 1
    assert summary.corporate_actions_applied == 1
