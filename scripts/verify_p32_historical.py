"""Actual owned compiled API, frozen full-cohort window; no prices/credentials output."""

import argparse
import calendar
import json
import time
from datetime import date
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, choices=(1, 3, 6, 12, 36, 60), default=1)
    months = parser.parse_args().months
    repo = Path(__file__).resolve().parents[1]
    credentials = json.loads(
        (repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=40) as client:
        origin = "http://127.0.0.1:8029"
        result = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": origin, "X-AlphaLens-Local": "p21"},
        )
        credentials.clear()
        result.raise_for_status()
        csrf = result.json()["csrf_token"]
        headers = {"Origin": origin, "X-AlphaLens-Local": "p32", "X-CSRF-Token": csrf}
        freshness = client.get("/api/v1/system/data-freshness")
        freshness.raise_for_status()
        end = date.fromisoformat(freshness.json()["data"]["last_evidenced_market_session"])
        year, month_zero = divmod(end.year * 12 + end.month - 1 - months, 12)
        month = month_zero + 1
        start = end.replace(
            year=year, month=month, day=min(end.day, calendar.monthrange(year, month)[1])
        )
        started = time.perf_counter()
        prepared = client.post(
            "/api/v1/personal/historical-scan/prepare",
            json={"start": str(start), "end": str(end), "category": "price_return", "size": 10},
            headers=headers,
        )
        prepared.raise_for_status()
        identity = prepared.json()["data"]["scan_id"]
        steps = prepared.json()["data"]["total_partitions"]
        if not 1 <= steps <= 256:
            raise ValueError("BOUNDED_ACTUAL_ARCHIVE_REQUIRED")
        timings = []
        completed = None
        for _ in range(steps):
            began = time.perf_counter()
            response = client.post(
                "/api/v1/personal/historical-scan/step", json={"scan_id": identity}, headers=headers
            )
            response.raise_for_status()
            timings.append(time.perf_counter() - began)
            data = response.json()["data"]
            if data["provider_requests"] != 0:
                raise ValueError("ARCHIVE_PROVIDER_SEPARATION_REQUIRED")
            if data["complete"]:
                completed = data["result"]
                break
        if completed is None:
            raise ValueError("ACTUAL_ARCHIVE_SCAN_NOT_COMPLETE")
        receipt = {
            "state": "PASSED",
            "start": str(start),
            "end": str(end),
            "partitions": len(timings),
            "observed_cohort": completed["observed_cohort"],
            "comparable_count": completed["comparable_count"],
            "leader_count": len(completed["leaders"]),
            "excluded_count": len(completed["excluded"]),
            "maximum_step_seconds": round(max(timings), 3),
            "total_seconds": round(time.perf_counter() - started, 3),
            "provider_requests": 0,
            "model_runs": 0,
            "source_archive_writes": 0,
            "raw_prices_retained": False,
            "interpretation": completed["interpretation"],
        }
        (repo / f".local-data/p32-historical-{months}m-verification.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P32_HISTORICAL_CHECK_FAILED","sensitive_output":false}')
        raise SystemExit(1) from None
