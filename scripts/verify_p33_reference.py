"""Bounded actual new reference endpoints, retaining only status/field-presence receipts."""

import json
from pathlib import Path

import httpx


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    credentials = json.loads(
        (root / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=120) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        login.raise_for_status()
        search = client.get("/api/v1/providers/upstox-private/instruments", params={"q": "TCS"})
        search.raise_for_status()
        instruments = [i for i in search.json()["data"]["instruments"] if i["symbol"] == "TCS"]
        if len(instruments) != 1:
            raise ValueError("VERIFIED_TCS_REQUIRED")
        response = client.get(
            "/api/v1/providers/upstox-private/reference",
            params={"instrument_key": instruments[0]["provider_key"]},
        )
        response.raise_for_status()
        data = response.json()["data"]
        receipt = {
            "symbol": data["symbol"],
            "instrument_key": data["instrument_key"],
            "api_calls": data["api_calls_this_request"],
            "observations": [
                {
                    "kind": o["kind"],
                    "state": o["state"],
                    "received_at": o["received_at"],
                    "response_data_present": o["data"] is not None,
                    "provider_effective_at": o["provider_effective_at"],
                }
                for o in data["observations"]
            ],
            "historical_pit_eligible": data["historical_pit_eligible"],
            "action_coverage_complete": data["action_coverage_complete"],
            "provider_payloads_retained": False,
        }
        (root / ".local-data/p33-reference-verification.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"REFERENCE_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
