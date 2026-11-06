"""TEST_ONLY saved processing receipts and target/session distinction."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import initialize
from workers.nse_market import engine

from alphalens_api import nse_monitoring


def test_collection_target_is_not_old_retained_history(tmp_path: Path) -> None:
    data: dict[str, Any] = {
        "operations": {"collection": {"session": "2026-10-21"}},
        "coverage": {
            "end": "2026-10-19",
            "configured_securities": 500,
            "per_security": [{"key": str(i), "last": "2026-10-19"} for i in range(499)],
        },
    }
    nse_monitoring.enrich(data, tmp_path / "market", at=datetime.now(UTC))
    operations = data["operations"]
    assert operations["session_status"]["updated_or_already_verified"] == 499
    assert operations["target_session_status"]["updated_or_already_verified"] == 0
    assert operations["target_session_status"]["pending_securities"] == 500
    assert operations["processing"]["state"] == "NOT_BENCHMARKED"


def test_saved_benchmark_is_checked_and_never_executes_inference(tmp_path: Path) -> None:
    folder = tmp_path / "sequence-runtime"
    initialize(folder)
    now = datetime.now(UTC)
    saved = {
        "version": "sequence-runtime-benchmark.v1",
        "started_at": (now - timedelta(seconds=3)).isoformat(),
        "completed_at": (now - timedelta(seconds=1)).isoformat(),
        "provider_requests": 0,
        "forecasts_written": 0,
        "training_performed": False,
        "capability": {"torch_version": None, "cuda_available": False, "xpu_available": False},
        "lineage": {"real_unique_input_securities": 2},
        "gpu_speedup": None,
        "measurements": [
            {
                "method": "CPU_BATCHED",
                "completed_device": "cpu",
                "sequences": 2,
                "median_seconds": 0.01,
                "sequences_per_second": 200,
                "repeated_input_stress_test": False,
                "fallback_reason": None,
            }
        ],
    }
    path = folder / "test-only.json"
    engine._checked(path, saved)
    engine._pointer(folder, "benchmark-latest.json", path)
    result = nse_monitoring.processing_evidence(tmp_path / "market", at=now)
    assert result["state"] == "SAVED_BENCHMARK_NOT_PRODUCTION_EXECUTION"
    assert result["gpu_speedup"] is None and result["provider_requests"] == 0
    assert (
        nse_monitoring.processing_evidence(tmp_path / "market", at=now - timedelta(days=1))["state"]
        == "SAVED_BENCHMARK_UNAVAILABLE_OR_INVALID"
    )
    path.write_text("{}")
    assert (
        nse_monitoring.processing_evidence(tmp_path / "market", at=now)["state"]
        == "SAVED_BENCHMARK_UNAVAILABLE_OR_INVALID"
    )
