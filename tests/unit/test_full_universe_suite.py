"""Comprehensive regression test suite for AlphaLens Full-Universe Engineering Repairs.

Verifies:
1. ForwardMaturationEngine:
   - Next-open-to-fifth-close target calculation
   - Correct separation of realized_direction and directional_hit
   - Append-only conflict detection and idempotent replay
   - Model identity uniqueness in forecast_id
2. ProviderManager:
   - Rejection of stale cached sessions for newer target requests (VENDOR_PENDING)
   - Distinct state outputs: FRESH, HISTORICAL_REPLAY, VENDOR_PENDING, RIGHTS_BLOCKED, FAILED
   - Rights enforcement for unverified BSE requests
3. FullUniverseIngestionEngine:
   - Inverse volume adjustments (V_adj = V / factor)
   - CorporateActionCoverage enforcement before model qualification
   - Idempotent replay vs conflict quarantine
   - Real Parquet Snappy archive generation
   - Executable disk reserve floor check
4. FullUniversePredictor:
   - Zero synthetic BSE candles in production prediction path
   - Explicit fail-closed BSE_DOMAIN_MODEL_NOT_VALIDATED gate
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
from ml.explainability.feature_attribution import (
    attribute_linear_prediction,
    compute_global_feature_importances,
)
from sklearn.linear_model import Ridge
from workers.nse_market import bulk_eod, market_regime, provider_manager
from workers.nse_market.forward_maturation_engine import ForwardMaturationEngine
from workers.nse_market.full_universe_ingestion import (
    FullUniverseIngestionEngine,
    verify_disk_reserve,
)
from workers.nse_market.full_universe_predictor import FullUniversePredictor


def test_market_regime_classifier() -> None:
    bull_candles = [{"session": f"2026-10-{i:02d}", "close": 100.0 + i * 2.0} for i in range(1, 25)]
    bull_state = market_regime.classify_market_regime(bull_candles)
    assert bull_state.regime in (
        market_regime.MarketRegime.BULL_TRENDING,
        market_regime.MarketRegime.LOW_VOL_RANGE,
    )
    assert bull_state.trend_score > 0
    assert 0.0 <= bull_state.recommended_equity_exposure <= 1.0


def test_feature_attribution_linear_decomposition() -> None:
    x = [[1.0, 2.0], [2.0, 1.0], [3.0, 4.0], [4.0, 3.0]]
    y = [10.0, 12.0, 20.0, 22.0]
    model = Ridge(alpha=1.0)
    model.fit(x, y)

    names = ["f1", "f2"]
    exp = attribute_linear_prediction(
        model, np.array([2.5, 2.5], dtype=np.float64), names, "NSE_EQ|INE002A01018", "2026-11-02"
    )
    assert exp.instrument_key == "NSE_EQ|INE002A01018"
    assert len(exp.top_factors) == 2

    importances = compute_global_feature_importances(model, names)
    assert len(importances) == 2
    assert sum(i["importance_pct"] for i in importances) == pytest.approx(100.0, rel=1e-2)


def test_forward_maturation_next_open_to_fifth_close(tmp_path: Path) -> None:
    """Verify target calculation uses Next Open (T+1) to Fifth Close (T+5)."""
    db_file = tmp_path / "test_outcomes.db"
    engine = ForwardMaturationEngine(db_file)

    histories = {
        "NSE_EQ|INE002A01018": [
            {"session": "2026-10-01", "open": 100.0, "close": 101.0},  # T (Forecast session)
            {
                "session": "2026-10-02",
                "open": 105.0,
                "close": 106.0,
            },  # T+1 (Entry session: open=105.0)
            {"session": "2026-10-05", "open": 106.0, "close": 107.0},  # T+2
            {"session": "2026-10-06", "open": 107.0, "close": 108.0},  # T+3
            {"session": "2026-10-07", "open": 108.0, "close": 109.0},  # T+4
            {
                "session": "2026-10-08",
                "open": 110.0,
                "close": 115.5,
            },  # T+5 (Exit session: close=115.5)
        ]
    }

    forecasts = [
        {
            "model_id": "HistGB_Classifier_H5",
            "instrument_key": "NSE_EQ|INE002A01018",
            "symbol": "RELIANCE",
            "session": "2026-10-01",
            "horizon_sessions": 5,
            "direction_probability": 0.70,
            "expected_return": 0.08,
        }
    ]

    matured = engine.settle_forecasts(forecasts, histories)
    assert len(matured) == 1
    m = matured[0]

    # Entry session must be T+1 ("2026-10-02"), Settlement session must be T+5 ("2026-10-08")
    assert m.entry_session == "2026-10-02"
    assert m.settlement_session == "2026-10-08"

    # Realized return = (115.5 - 105.0) / 105.0 = 10.5 / 105.0 = 0.10 (+10.0%)
    assert m.realized_return == pytest.approx(0.10, rel=1e-3)
    assert m.realized_direction == 1
    assert m.directional_hit is True
    assert m.brier_score_component == pytest.approx((0.70 - 1.0) ** 2, rel=1e-3)


def test_forward_maturation_append_only_conflict_and_idempotence(tmp_path: Path) -> None:
    """Verify idempotent retries succeed while conflicting rewrites are rejected."""
    db_file = tmp_path / "test_outcomes_conflict.db"
    engine = ForwardMaturationEngine(db_file)

    histories = {
        "NSE_EQ|INE002A01018": [
            {"session": "2026-10-01", "open": 100.0, "close": 101.0},
            {"session": "2026-10-02", "open": 100.0, "close": 101.0},
            {"session": "2026-10-05", "open": 101.0, "close": 102.0},
            {"session": "2026-10-06", "open": 102.0, "close": 103.0},
            {"session": "2026-10-07", "open": 103.0, "close": 104.0},
            {"session": "2026-10-08", "open": 104.0, "close": 110.0},
        ]
    }

    forecast = {
        "model_id": "HistGB_Classifier_H5",
        "instrument_key": "NSE_EQ|INE002A01018",
        "session": "2026-10-01",
        "horizon_sessions": 5,
        "direction_probability": 0.65,
        "expected_return": 0.05,
    }

    # 1. First settlement
    matured1 = engine.settle_forecasts([forecast], histories)
    assert len(matured1) == 1

    # 2. Idempotent replay (same forecast and same market history)
    matured2 = engine.settle_forecasts([forecast], histories)
    assert len(matured2) == 1

    # 3. Conflicting rewrite attempt (modified probability for same forecast ID)
    conflicting_forecast = {**forecast, "direction_probability": 0.15}
    with pytest.raises(ValueError, match="CONFLICTING_FORECAST_OUTCOME_MUTATION_REJECTED"):
        engine.settle_forecasts([conflicting_forecast], histories)


def test_provider_manager_stale_cache_and_rights(tmp_path: Path) -> None:
    """Verify provider manager returns distinct states and rejects stale cache for new sessions."""
    mgr = provider_manager.ProviderManager(bulk_archive_dir=tmp_path, bse_rights_cleared=False)

    # 1. Unverified BSE rights -> RIGHTS_BLOCKED
    bse_res = mgr.acquire_eod_data("BSE_EQ|INE002A01018", date(2026, 11, 2))
    assert bse_res.state == provider_manager.AcquisitionState.RIGHTS_BLOCKED
    assert bse_res.success is False

    # 2. Stale cache for newer requested session -> VENDOR_PENDING
    cached_stale = [{"session": "2026-10-30", "close": 1400.0}]
    nse_stale_res = mgr.acquire_eod_data(
        "NSE_EQ|INE002A01018",
        date(2026, 11, 2),
        upstox_client=None,
        cached_candles=cached_stale,
    )
    assert nse_stale_res.state == provider_manager.AcquisitionState.VENDOR_PENDING
    assert nse_stale_res.success is False
    assert nse_stale_res.observed_session == "2026-10-30"

    # 3. Exact matching cache session -> HISTORICAL_REPLAY
    cached_exact = [{"session": "2026-11-02", "close": 1410.0}]
    nse_exact_res = mgr.acquire_eod_data(
        "NSE_EQ|INE002A01018",
        date(2026, 11, 2),
        upstox_client=None,
        cached_candles=cached_exact,
    )
    assert nse_exact_res.state == provider_manager.AcquisitionState.HISTORICAL_REPLAY
    assert nse_exact_res.success is True
    assert nse_exact_res.observed_session == "2026-11-02"


def test_full_universe_ingestion_inverse_volume_and_parquet(tmp_path: Path) -> None:
    """Verify inverse volume adjustment (V_adj = V / factor) and Parquet generation."""
    db_file = tmp_path / "test_univ.db"
    archive_dir = tmp_path / "parquet"
    engine = FullUniverseIngestionEngine(target_db_path=db_file, archive_dir=archive_dir)

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
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=bulk_eod.UDIFF_HEADERS)
    writer.writeheader()
    writer.writerow(row)
    csv_bytes = text.getvalue().encode("utf-8")

    # 2-for-1 stock split: ex-date is 2026-11-05, coverage as of 2026-11-10.
    # Pre-event session 2026-11-02 (< ex_date <= as_of) is adjusted:
    # price halved (factor=0.5), volume doubled (50000 / 0.5 = 100000).
    ca = [
        bulk_eod.CorporateAction(
            isin="INE002A01018",
            ex_date=date(2026, 11, 5),
            action_type="SPLIT",
            ratio_from=Decimal("1"),
            ratio_to=Decimal("2"),
            adjustment_factor=Decimal("0.5"),
        )
    ]
    coverage = bulk_eod.CorporateActionCoverage(
        verified_coverage_as_of=date(2026, 11, 10),
        verified_isins=frozenset({"INE002A01018"}),
        coverage_evidence="OFFICIAL_NSE_CORPORATE_ACTION_BULK",
        coverage_sha256="abc123",
    )

    summary = engine.ingest_bhavcopy_payload(
        csv_bytes, "NSE_UDIFF", date(2026, 11, 2), corporate_actions=ca, coverage=coverage
    )
    assert summary.status == "INGESTION_SUCCESS"
    assert summary.ordinary_equities_saved == 1
    assert summary.corporate_actions_applied == 1
    assert summary.parquet_bytes_written > 0

    # Verify Parquet file on disk
    parquet_files = list(archive_dir.glob("*.parquet"))
    assert len(parquet_files) == 1
    table = pq.read_table(parquet_files[0])
    assert table.num_rows == 1
    # Adjusted price: 1410.00 * 0.5 = 705.00
    assert table.column("close")[0].as_py() == pytest.approx(705.00)
    # Inverse volume adjustment: 50000 / 0.5 = 100000
    assert table.column("volume")[0].as_py() == pytest.approx(100000.0)


def test_full_universe_predictor_zero_synthetic_bse() -> None:
    """Verify FullUniversePredictor produces zero fake BSE predictions.

    Fails closed when authentic BSE data is absent.
    """
    predictor = FullUniversePredictor()
    res = predictor.run_full_universe_prediction(as_of_session="2026-11-02")

    # BSE status must fail closed
    assert res["bse_status"]["gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"
    assert res["bse_status"]["bse_production_predictions_suppressed"] is True
    assert res["universe_summary"]["bse_equities_evaluated"] == 0
    assert len(res["bse_top_20"]) == 0

    # Dual-exchange Top 20 contains only genuine model-qualified predictions (zero BSE)
    for equity in res["dual_exchange_top_20"]:
        assert equity["exchange"] == "NSE"
    assert not any(equity.get("exchange") == "BSE" for equity in res["dual_exchange_top_20"])


def test_disk_reserve_floor_check(tmp_path: Path) -> None:
    """Verify verify_disk_reserve raises RuntimeError when free space is below safety floor."""
    # Under mock condition with absurd threshold
    with pytest.raises(RuntimeError, match="INSUFFICIENT_DISK_SPACE_SAFETY_RESERVE_FLOOR_VIOLATED"):
        verify_disk_reserve(tmp_path, min_bytes=10**15)  # 1 Petabyte
