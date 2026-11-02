"""Unit tests for AlphaLens universe coverage tracker and 4-tier pipeline invariants."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from workers.nse_market.universe_coverage_tracker import (
    APPROVED_BUDGET_CONSTRAINT,
    SCHEMA,
    compute_universe_coverage,
    format_coverage_summary,
)


@pytest.fixture
def valid_mock_coverage() -> dict:
    return {
        "searchable": {
            "total_listings": 8169,
            "nse_listings": 3214,
            "bse_listings": 4955,
            "unique_company_isins": 5664,
            "catalog_snapshot_file": "snapshot-test.json",
            "status": "INDEXED_FROM_OFFICIAL_BOD_METADATA",
        },
        "daily_store": {
            "total_cohort_stocks": 500,
            "active_session_received": 497,
            "pending_vendor_publication": 3,
            "pending_vendor_keys": (
                "NSE_EQ|INE023A01030",
                "NSE_EQ|INE029L01018",
                "NSE_EQ|INE077P01034",
            ),
            "total_candles_retained": 450970,
            "latest_observed_session": "2026-10-30",
            "status": "BOUNDED_COHORT_DAILY_STORE",
        },
        "features": {
            "evaluated_stocks": 307,
            "excluded_stocks": 193,
            "feature_dimension": 16,
            "observation_session": "2026-10-30",
            "bse_evaluated": 0,
            "status": "V2_FEATURE_PIPELINE_VALIDATED",
        },
        "forecast_ledger": {
            "session_forecasts": 307,
            "total_immutable_records": 1561,
            "database_count": 190,
            "historical_pinned_forecasts": 1254,
            "observation_session": "2026-10-30",
            "bse_forecasts": 0,
            "status": "IMMUTABLE_DURABLE_LEDGER",
        },
    }


def test_coverage_tracker_deterministic_invariants(valid_mock_coverage: dict) -> None:
    at = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    report = compute_universe_coverage(Path("."), at=at, mock_data=valid_mock_coverage)

    assert report.schema == SCHEMA
    assert report.budget_constraint == APPROVED_BUDGET_CONSTRAINT
    assert "1,800 GETs/day" in report.budget_note
    assert report.invariants_passed is True
    assert len(report.invariant_violations) == 0

    # Searchable tier checks
    assert report.searchable.total_listings == 8169
    assert report.searchable.nse_listings == 3214
    assert report.searchable.bse_listings == 4955
    assert report.searchable.unique_company_isins == 5664

    # Daily store tier checks
    assert report.daily_store.total_cohort_stocks == 500
    assert report.daily_store.active_session_received == 497
    assert report.daily_store.pending_vendor_publication == 3

    # Features tier checks
    assert report.features.evaluated_stocks == 307
    assert report.features.excluded_stocks == 193
    assert report.features.bse_evaluated == 0

    # Forecast tier checks
    assert report.forecast_ledger.session_forecasts == 307
    assert report.forecast_ledger.total_immutable_records == 1561
    assert report.forecast_ledger.bse_forecasts == 0


def test_coverage_tracker_flags_searchable_mismatch(valid_mock_coverage: dict) -> None:
    valid_mock_coverage["searchable"]["total_listings"] = 8000  # != 3214 + 4955 (8169)
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    assert report.invariants_passed is False
    assert any("Searchable total" in v for v in report.invariant_violations)


def test_coverage_tracker_flags_unauthorized_bse_inference(valid_mock_coverage: dict) -> None:
    valid_mock_coverage["features"]["bse_evaluated"] = 10
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    assert report.invariants_passed is False
    assert any("BSE features evaluated" in v for v in report.invariant_violations)


def test_coverage_tracker_flags_cohort_feature_sum_mismatch(valid_mock_coverage: dict) -> None:
    valid_mock_coverage["features"]["excluded_stocks"] = 100  # 307 + 100 = 407 != 500
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    assert report.invariants_passed is False
    assert any("Feature evaluation sum" in v for v in report.invariant_violations)


def test_coverage_tracker_flags_forecast_ledger_mismatch(valid_mock_coverage: dict) -> None:
    valid_mock_coverage["forecast_ledger"]["total_immutable_records"] = 2000  # != 307 + 1254 (1561)
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    assert report.invariants_passed is False
    assert any("Forecast ledger total" in v for v in report.invariant_violations)


def test_coverage_summary_format(valid_mock_coverage: dict) -> None:
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    summary = format_coverage_summary(report)
    assert "# AlphaLens Universe & Pipeline Coverage Summary" in summary
    assert "8,169" in summary
    assert "3,214 NSE" in summary
    assert "4,955 BSE" in summary
    assert "500" in summary
    assert "307" in summary
    assert "1,561" in summary
    assert "1,800 GETs/day" in summary


def test_coverage_report_json_serializable(valid_mock_coverage: dict) -> None:
    report = compute_universe_coverage(Path("."), mock_data=valid_mock_coverage)
    d = report.to_dict()
    encoded = json.dumps(d)
    assert isinstance(encoded, str)
    decoded = json.loads(encoded)
    assert decoded["searchable"]["total_listings"] == 8169
