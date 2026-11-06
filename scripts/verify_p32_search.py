"""Bounded actual identity pagination benchmark; no market observations requested."""

import json
import statistics
import time
from pathlib import Path

import httpx


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    credentials = json.loads(
        (repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=40) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        credentials.clear()
        login.raise_for_status()
        endpoint = "/api/v1/providers/upstox-private/instruments"
        first = client.get(endpoint, params={"q": "", "limit": 100})
        first.raise_for_status()
        count = first.json()["data"]["candidate_count"]
        keys = {i["provider_key"] for i in first.json()["data"]["instruments"]}
        timings, sizes = [], []
        started = time.perf_counter()
        for offset in range(100, count, 100):
            began = time.perf_counter()
            result = client.get(endpoint, params={"q": "", "limit": 100, "offset": offset})
            result.raise_for_status()
            timings.append(time.perf_counter() - began)
            sizes.append(len(result.content))
            keys.update(i["provider_key"] for i in result.json()["data"]["instruments"])
        if len(keys) != count or not 1000 < count <= 10000:
            raise ValueError("ACTUAL_CURRENT_IDENTITY_PAGINATION_REQUIRED")
        receipt = {
            "state": "PASSED",
            "verified_current_identities": count,
            "page_size": 100,
            "timed_http_pages": len(timings),
            "median_page_ms": round(statistics.median(timings) * 1000, 3),
            "maximum_page_ms": round(max(timings) * 1000, 3),
            "total_timed_seconds": round(time.perf_counter() - started, 3),
            "maximum_response_bytes": max(sizes),
            "market_observation_requests": 0,
            "full_market_polling": False,
            "interpretation": "WARM_CURRENT_IDENTITY_INDEX_NOT_PRICE_ENTITLEMENT_OR_ML_UNIVERSE",
        }
        (repo / ".local-data/p32-search-verification.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P32_SEARCH_CHECK_FAILED","sensitive_output":false}')
        raise SystemExit(1) from None
