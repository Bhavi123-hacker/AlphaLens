"""Read-only real research benchmark with separately isolated TEST_ONLY authentication."""

import argparse
import asyncio
import json
import platform
import secrets
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.main import create_app
from alphalens_api.operations.store import OperationsStore


async def measure(output: Path, samples: int) -> None:
    settings = Settings()
    root = Path(tempfile.mkdtemp(prefix="TEST_ONLY_benchmark_", dir=output.parent))
    settings.auth_root = root / "auth"
    settings.operations_root = root / "operations"
    auth = AuthStore(settings.auth_root)
    auth.initialize()
    secret = secrets.token_urlsafe(32)
    auth.bootstrap("benchmark_operator", secret)
    OperationsStore(settings.operations_root).initialize()
    app = create_app(settings)
    workloads = {
        "session": "/auth/session",
        "overview_status": "/system/status",
        "overview_freshness": "/system/data-freshness",
        "stock_search": "/stocks?q=RELIANCE&limit=20",
        "ohlcv": "/stocks/tejhq:isin:INE002A01018/history?limit=250",
        "indicators": "/stocks/tejhq:isin:INE002A01018/indicators?feature=sma_200&limit=250",
        "models": "/research/models?limit=20",
        "evaluation": "/research/evaluation",
        "backtests": "/research/backtests?limit=20",
        "portfolios": "/portfolios?limit=20",
        "paper_accounts": "/paper/accounts?limit=20",
        "alerts": "/alerts?limit=20",
        "unread": "/alerts/unread-count",
        "daily_runs": "/daily/runs?limit=20",
        "operations": "/operations/status",
    }
    results = {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 40000)),
        base_url="http://127.0.0.1:8017/api/v1",
    ) as client:
        started = time.perf_counter()
        login = await client.post(
            "/auth/login",
            json={"username": "benchmark_operator", "password": secret},
            headers={"Origin": "http://127.0.0.1:5173", "X-AlphaLens-Local": "p21"},
        )
        login.raise_for_status()
        results["login"] = {"elapsed_ms": (time.perf_counter() - started) * 1000}
        models = app.state.research.reports()
        model = next(
            m for m in models if m.get("fold_id") == "2022" and m.get("task") == "classification"
        )
        workloads["predictions"] = (
            f"/research/predictions?model_id={model['model_run_id']}"
            "&security_id=tejhq:isin:INE001A01036&limit=20"
        )
        for name, path in workloads.items():
            elapsed, statuses, payloads, cpu = [], [], [], []
            for _ in range(samples):
                started, cpu_start = time.perf_counter(), time.process_time()
                reply = await client.get(path)
                elapsed.append((time.perf_counter() - started) * 1000)
                cpu.append((time.process_time() - cpu_start) * 1000)
                statuses.append(reply.status_code)
                payloads.append(len(reply.content))
            warm = elapsed[1:]
            results[name] = {
                "path": path,
                "statuses": statuses,
                "cold_ms": elapsed[0],
                "warm_p50_ms": statistics.median(warm),
                "warm_p95_ms": sorted(warm)[int((len(warm) - 1) * 0.95)],
                "samples_ms": elapsed,
                "cpu_ms": cpu,
                "payload_bytes": payloads,
            }
    receipt = {
        "version": "p23.performance.v1",
        "measured_at": datetime.now(UTC).isoformat(),
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "cache_semantics": (
            "New application; checksum cache primed by model identity selection; OS cache not "
            "flushed. First per-workload and subsequent warm samples separately reported."
        ),
        "classification": "REAL_HISTORICAL_READS_WITH_ISOLATED_TEST_ONLY_AUTH",
        "limitations": (
            "ASGI transport excludes network/browser latency. Small-sample p95 is descriptive "
            "only. Unconfigured financial database remains 503."
        ),
        "results": results,
    }
    with output.open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, choices=range(4, 31), default=8)
    args = parser.parse_args()
    asyncio.run(measure(args.output, args.samples))
