"""TEST_ONLY broad-universe detail contracts and receipt-derived workload estimates."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import encoded
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, TARGET_VERSION
from workers.nse_market.operational_coverage import detail_contracts, durations, storage
from workers.providers import universe

AT = datetime(2026, 10, 25, 8, tzinfo=UTC)


def sources() -> tuple[universe.Snapshot, dict[str, Any]]:
    records = tuple(
        {
            "instrument_key": f"NSE_EQ|INE{index:09}",
            "isin": f"INE{index:09}",
            "name": f"TEST_ONLY company {index}",
            "symbol": f"TEST_ONLY_{index}",
            "eligible_common_equity": True,
            "classification": "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY",
        }
        for index in range(3207)
    )
    master = universe.Snapshot("0" * 64, AT - timedelta(days=1), (), records, {})
    first = records[0]
    key = first["instrument_key"]
    view = {
        "rows": [
            {
                "key": key,
                "session": "2026-10-23",
                "close": "100",
                "freshness": "DATED_COMPLETED_SESSION",
            }
        ],
        "histories": {key: [{"session": "2026-10-23", "close": "100"}]},
        "research_workspace": {
            "candidates": [
                {
                    "key": key,
                    "identity": {
                        "provider_key": key,
                        "isin": first["isin"],
                        "symbol": first["symbol"],
                    },
                    "symbol": first["symbol"],
                    "inference_at": (AT - timedelta(hours=1)).isoformat(),
                    "session": "2026-10-23",
                    "features": [0.1] * 16,
                    "feature_names": list(LOCAL_FEATURE_NAMES),
                    "score": 0.61,
                    "target_version": TARGET_VERSION,
                    "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
                }
            ]
        },
    }
    return master, view


def test_every_supported_identity_has_an_explicit_detail_contract_without_http() -> None:
    master, view = sources()
    result = detail_contracts(master, view, at=AT)
    assert result["supported_detail_contracts"] == 3207
    assert result["priced_chart_contracts"] == result["compatible_saved_predictions"] == 1
    assert len(result["per_security"]) == 3207
    assert result["risk_missing_reasons"]["NO_SAVED_PRICES"] == 3206
    assert result["model_observation_sessions"] == {"2026-10-23": 1}
    assert result["accepted_models"] == result["http_requests"] == result["provider_requests"] == 0


def test_detail_audit_rejects_price_chart_mismatch_and_incomplete_identity() -> None:
    master, view = sources()
    view["histories"] = {}
    with pytest.raises(ValueError, match="LINEAGE"):
        detail_contracts(master, view, at=AT)
    master, view = sources()
    broken = {**master.records[-1], "name": None}
    with pytest.raises(ValueError, match="IDENTITY"):
        detail_contracts(replace(master, records=(*master.records[:-1], broken)), view, at=AT)
    master, view = sources()
    view["rows"].append(view["rows"][0])
    with pytest.raises(ValueError, match="DUPLICATE"):
        detail_contracts(master, view, at=AT)


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", float("nan")),
        ("score", True),
        ("features", [0.1] * 15),
        ("target_version", "TEST_ONLY_WRONG_HORIZON"),
    ],
)
def test_incompatible_predictions_never_count_as_universe_coverage(field: str, value: Any) -> None:
    master, view = sources()
    view["research_workspace"]["candidates"][0][field] = value
    with pytest.raises(ValueError, match="PREDICTION_CONTRACT"):
        detail_contracts(master, view, at=AT)


def test_duration_estimate_retains_partial_runs_and_excludes_zero_gets_or_incomplete_jobs() -> None:
    records = [
        {
            "run_id": "TEST_ONLY_A",
            "started_at": "2026-10-24T10:00:00+00:00",
            "completed_at": "2026-10-24T10:02:00+00:00",
            "state": "PARTIAL_OR_PUBLICATION_PENDING",
            "source_requests_last_run": 60,
        },
        {
            "run_id": "TEST_ONLY_B",
            "started_at": "2026-10-24T10:00:00+00:00",
            "completed_at": "2026-10-24T10:04:00+00:00",
            "state": "FAILED",
            "source_requests_last_run": 60,
        },
        {"run_id": "TEST_ONLY_ZERO", "source_requests_last_run": 0},
        {"run_id": "TEST_ONLY_INTERRUPTED", "source_requests_last_run": 60},
    ]
    result = durations([*records, records[0]], calls=100)
    assert result["qualified_receipts"] == 2
    assert result["projected_active_seconds"] == {"min": 200, "median": 300, "max": 400}
    assert "NOT_NETWORK_BENCHMARK" in result["method"]
    assert durations(records[2:], calls=100)["projected_active_seconds"] is None
    assert (
        durations(records, calls=100, at=datetime(2026, 10, 24, 9, tzinfo=UTC))[
            "qualified_receipts"
        ]
        == 0
    )
    with pytest.raises(ValueError, match="NONNEGATIVE"):
        durations(records, calls=-1)


def test_storage_sizes_pinned_payload_without_following_a_changed_publication_pointer(
    tmp_path: Path,
) -> None:
    root = tmp_path / "TEST_ONLY"
    for part in ("daily", "instruments", "market-views"):
        (root / part).mkdir(parents=True)
    view = {
        "latest_observed_session": "2026-10-23",
        "configured_securities": 1,
        "dataset_id": "TEST_ONLY_PINNED_PROJECTION",
    }
    result = storage(root, view, equities=3207)
    assert result["current_saved_projection_bytes"] == len(encoded(view))
    assert result["whole_universe_projection_bytes_linear_scenario"] == len(encoded(view)) * 3207
    assert result["daily_retained_source_bytes_scenario"] is None
    assert result["all_existing_daily_evidence_bytes"] == 0
    assert not (root / "market-view-latest.json").exists()


def test_explicit_interruption_is_visible_both_in_all_run_and_separate_scenarios() -> None:
    result = durations(
        [
            {
                "run_id": "TEST_ONLY_COMPLETED",
                "source_requests_last_run": 100,
                "started_at": "2026-10-24T10:00:00+00:00",
                "completed_at": "2026-10-24T10:02:00+00:00",
                "state": "PARTIAL_OR_PUBLICATION_PENDING",
            },
            {
                "run_id": "TEST_ONLY_INTERRUPTED",
                "source_requests_last_run": 5,
                "started_at": "2026-10-24T10:00:00+00:00",
                "completed_at": "2026-10-24T10:05:00+00:00",
                "state": "INTERRUPTED_FOR_SCALABILITY_FIX",
            },
        ],
        calls=100,
    )
    assert result["qualified_receipts"] == 2
    assert (
        result["explicitly_interrupted_receipts"] == result["ordinary_completed_job_receipts"] == 1
    )
    assert result["projected_active_seconds"]["max"] == 6000
    assert result["ordinary_completed_job_seconds_scenario"]["max"] == 120
