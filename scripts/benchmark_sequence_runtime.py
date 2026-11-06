"""Explicit saved-data benchmark, no training or forecast publication.

Run with project-python, or the existing optional PyTorch environment. Repeated
inputs measure throughput only and are never presented as new securities/scores.
"""

from __future__ import annotations

import json
import statistics
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from threadpoolctl import threadpool_limits
from workers.experimental_nse.acquire import digest, initialize
from workers.experimental_nse_v2.features import build
from workers.nse_market import engine, sequence, sequence_runtime


def saved_inputs(repo: Path) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    root = repo / ".local-data/sequence-benchmark-v1"
    model, report = engine._read(root / "model.json"), engine._read(root / "report-final.json")
    model_hash = digest((root / "model.json").read_bytes())
    if report["model_sha256"] != model_hash:
        raise ValueError("PINNED_SEQUENCE_REPORT_MODEL_REQUIRED")
    saved = report["current_scores"]
    sessions = {item["session"] for item in saved}
    if len(sessions) != 1 or not saved:
        raise ValueError("SAVED_SINGLE_SESSION_SEQUENCE_COHORT_REQUIRED")
    session = next(iter(sessions))
    frame = engine.snapshot(repo / ".local-data/nse-market-expansion")
    days = [day for day in frame["sessions"] if day <= session][-80:]
    keys, selected = {item["key"] for item in saved}, set(days)
    rows = [r for r in frame["rows"] if r["key"] in keys and r["session"] in selected]
    features = build(rows, days, frame["quality"]["excluded_sessions"], include_context=False)
    items = [x for x in sequence.sequences(features.samples, days) if x.sample.session == session]
    expected = {item["key"]: item for item in saved}
    if {item.sample.key for item in items} != keys:
        raise ValueError("SAVED_SEQUENCE_INPUT_COHORT_NO_LONGER_COMPLETE")
    values = sequence._array(items)
    scores = sequence.predict(model, values)
    error = max(
        abs(float(score) - expected[item.sample.key]["score"])
        for item, score in zip(items, scores, strict=True)
    )
    if error > 1e-12:
        raise ValueError("SAVED_SEQUENCE_REPRODUCTION_FAILED")
    return (
        model,
        values,
        {
            "model_sha256": model_hash,
            "feature_version": sequence.VERSION,
            "dataset_id": report["dataset_id"],
            "observation_session": session,
            "real_unique_input_securities": len(items),
            "saved_score_max_absolute_error": error,
            "input_sha256": digest(values.tobytes()),
        },
    )


def measure(model: dict[str, Any], values: Any) -> dict[str, Any]:
    results = []
    capabilities = sequence_runtime.capability()
    # Deliberately small fixed budget, two BLAS threads, five measured trials after warmup.
    with threadpool_limits(limits=2):
        for count in (len(values), 500, 1000):
            matrix = np.tile(values, (int(np.ceil(count / len(values))), 1, 1))[:count]
            reference = sequence.predict(model, matrix)
            for name, batch, device in (
                ("CPU_REFERENCE", count, "cpu"),
                ("CPU_BATCHED", 128, "cpu"),
                ("AUTO_BATCHED", 128, "auto"),
            ):
                trials, info, error = [], {}, 0.0
                for trial in range(6):
                    start = time.perf_counter()
                    if name == "CPU_REFERENCE":
                        output = sequence.predict(model, matrix)
                        info = {"completed_device": "cpu", "fallback_reason": None}
                    else:
                        output, info = sequence_runtime.predict(
                            model, matrix, batch_size=batch, device=device
                        )
                    elapsed = time.perf_counter() - start
                    error = max(error, float(np.max(np.abs(output - reference))))
                    if trial:
                        trials.append(elapsed)
                if error > 1e-10:
                    raise ValueError("BENCHMARK_MODEL_PARITY_FAILED")
                median = statistics.median(trials)
                results.append(
                    {
                        "method": name,
                        "sequences": count,
                        "trials": trials,
                        "median_seconds": median,
                        "sequences_per_second": count / median,
                        "maximum_absolute_error": error,
                        "completed_device": info["completed_device"],
                        "fallback_reason": info["fallback_reason"],
                        "repeated_input_stress_test": count != len(values),
                    }
                )
    measured_gpu = next(
        (
            row
            for row in results
            if row["method"] == "AUTO_BATCHED"
            and row["sequences"] == len(values)
            and row["completed_device"] in {"cuda", "xpu"}
            and row["fallback_reason"] is None
        ),
        None,
    )
    return {
        "capability": capabilities,
        "measurements": results,
        "gpu_speedup": results[0]["median_seconds"] / measured_gpu["median_seconds"]
        if measured_gpu
        else None,
        "thread_limit": 2,
        "training_performed": False,
        "forecasts_written": 0,
        "provider_requests": 0,
    }


def _require_idle() -> None:
    from alphalens_api.nse_monitoring import windows_observation

    observed = windows_observation({}, at=datetime.now(UTC))
    if (
        observed.get("live_query_state") != "AVAILABLE"
        or observed.get("state") != "Ready"
        or (datetime.fromisoformat(observed["next_run_at"]) - datetime.now(UTC)).total_seconds()
        < 300
    ):
        raise ValueError("BENCHMARK_REQUIRES_VERIFIED_IDLE_TASK_AND_FIVE_MINUTE_WINDOW")


def main() -> None:
    repo = Path.cwd()
    _require_idle()
    started = datetime.now(UTC)
    print(
        json.dumps({"stage": "VALIDATING_SAVED_SEQUENCE_INPUTS", "at": started.isoformat()}),
        flush=True,
    )
    model, values, lineage = saved_inputs(repo)
    _require_idle()  # Source verification can be slow; do not infer over a newly started task.
    print(
        json.dumps({"stage": "BENCHMARKING_REPLAY", "at": datetime.now(UTC).isoformat()}),
        flush=True,
    )
    result = {
        "version": "sequence-runtime-benchmark.v1",
        "started_at": started.isoformat(),
        "lineage": lineage,
        **measure(model, values),
        "completed_at": datetime.now(UTC).isoformat(),
        "scope": "SAVED_SEQUENCE_MODEL_REPLAY_NOT_CURRENT_FORECASTS",
    }
    root = repo / ".local-data/sequence-runtime"
    initialize(root)
    runs = root / "benchmarks"
    initialize(runs)
    path = runs / (uuid.uuid4().hex + ".json")
    engine._checked(path, result)
    engine._pointer(root, "benchmark-latest.json", path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
