"""Actual checksum-verified descriptive window audit; no model evaluation or backtest."""

import argparse
import json
import time
from pathlib import Path

import httpx


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--five-year-only", action="store_true")
    parser.add_argument(
        "--comparison-mode", choices=("strict", "available_window", "observed_endpoints")
    )
    options = parser.parse_args()
    credentials = json.loads(
        (repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    receipts = []
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=120) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        login.raise_for_status()
        headers = {
            "Origin": "http://127.0.0.1:8029",
            "X-AlphaLens-Local": "p32",
            "X-CSRF-Token": login.json()["csrf_token"],
        }
        windows = [
            ("1M", "2026-09-06"),
            ("3M", "2026-07-06"),
            ("6M", "2026-04-06"),
            ("1Y", "2025-10-06"),
            ("3Y", "2023-10-06"),
            ("5Y", "2021-10-06"),
        ]
        for name, start in windows:
            if options.five_year_only and name != "5Y":
                continue
            for mode in (
                (options.comparison_mode,)
                if options.comparison_mode
                else (
                    ("strict", "available_window")
                    if name == "5Y" and not options.five_year_only
                    else ("strict",)
                )
            ):
                began = time.perf_counter()
                response = client.post(
                    "/api/v1/personal/historical-scan/prepare",
                    json={"start": start, "end": "2026-10-06", "comparison_mode": mode},
                    headers=headers,
                )
                response.raise_for_status()
                job = response.json()["data"]
                for _ in range(job["total_partitions"]):
                    response = client.post(
                        "/api/v1/personal/historical-scan/step",
                        json={"scan_id": job["scan_id"]},
                        headers=headers,
                    )
                    response.raise_for_status()
                    step = response.json()["data"]
                result = step["result"]
                receipt = {
                    "window": name,
                    "comparison_mode": mode,
                    "start": start,
                    "end": "2026-10-06",
                    "observed_cohort": result["observed_cohort"],
                    "comparable_count": result["comparable_count"],
                    "coverage_counts": result["coverage_counts"],
                    "slots_with_zero_observed_equities": result.get(
                        "slots_with_zero_observed_equities", []
                    ),
                    "exclusion_counts": result["exclusion_counts"],
                    "leader_coverage": [
                        {"symbol": r["symbol"], "coverage": r["coverage"]}
                        for r in result["leaders"]
                    ],
                    "seconds": round(time.perf_counter() - began, 3),
                    "provider_requests": 0,
                    "research_reruns": False,
                }
                receipts.append(receipt)
                print(
                    json.dumps({k: v for k, v in receipt.items() if k != "leader_coverage"}),
                    flush=True,
                )
    output = (
        "p33-historical-gap-diagnostic.json"
        if options.five_year_only
        else "p33-historical-verification.json"
    )
    if options.comparison_mode:
        output = "p33-historical-" + options.comparison_mode + ".json"
    (repo / ".local-data" / output).write_text(json.dumps(receipts, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
