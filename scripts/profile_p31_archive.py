"""Profile unchanged archival read gates. Counts/timing only, never price output."""

import json
import time
from pathlib import Path
from typing import Any

import alphalens_api.intelligence as intelligence
from alphalens_api.core.domain_errors import APIError
from alphalens_api.local.cli import configured
from alphalens_api.services import ResearchService


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    service = ResearchService(
        configured(repo / ".local-data/p31-browser-runtime/operator-config.json")
    )
    counters = {
        "verify_calls": 0,
        "verify_seconds": 0.0,
        "scan_calls": 0,
        "scan_seconds": 0.0,
        "returned_rows": 0,
    }
    verify = service.reader.verify
    scan = intelligence.snapshot_rows
    scans = []

    def measured_verify(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return verify(*args, **kwargs)
        finally:
            counters["verify_calls"] += 1
            counters["verify_seconds"] += time.perf_counter() - start

    def measured_scan(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = scan(*args, **kwargs)
            counters["returned_rows"] += len(result[0])
            return result
        finally:
            counters["scan_calls"] += 1
            elapsed = time.perf_counter() - start
            counters["scan_seconds"] += elapsed
            scans.append(
                {
                    "partition": str(
                        Path(args[0]).relative_to(service.reader.settings.research_data_root)
                    ),
                    "seconds": elapsed,
                }
            )

    service.reader.verify = measured_verify  # type: ignore[method-assign]
    intelligence.snapshot_rows = measured_scan
    started = time.perf_counter()
    try:
        service.intelligence_window.read(None, 2)
        state = "PASSED"
    except APIError as exc:
        state = exc.code
    receipt = {
        "state": state,
        "seconds": time.perf_counter() - started,
        **counters,
        "gates_unchanged": True,
        "price_values_output": False,
        "slowest_scans": sorted(scans, key=lambda row: row["seconds"], reverse=True)[:8],
    }
    (repo / ".local-data/p31-archive-profile.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
