"""Bounded read-only HTTP diagnostics, not a model fit/evaluation/backtest rerun."""

import json
import time
from pathlib import Path

import httpx


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    secret = json.loads((repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes())
    receipt = []
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=40) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=secret,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        if login.status_code != 200:
            raise ValueError("ISOLATED_DIAGNOSTIC_LOGIN_REQUIRED")
        for route in (
            "/intelligence/regime?sessions=2",
            "/intelligence/drift?sessions=2",
            "/visual/market?limit=5",
        ):
            started = time.perf_counter()
            reply = client.get("/api/v1" + route)
            body = reply.json()
            receipt.append(
                {
                    "route": route,
                    "status": reply.status_code,
                    "seconds": round(time.perf_counter() - started, 3),
                    "error_code": body.get("error_code"),
                    "source": body.get("source"),
                    "bytes": len(reply.content),
                    "projection_seconds": body.get("data", {}).get("projection_seconds")
                    if isinstance(body.get("data"), dict)
                    else None,
                }
            )
        client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Origin": "http://127.0.0.1:8029", "X-CSRF-Token": login.json()["csrf_token"]},
        )
    (repo / ".local-data/p31-archive-read-latency.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
