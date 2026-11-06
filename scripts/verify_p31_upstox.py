"""Seven-GET maximum genuine selected-cohort validation; no prices retained/logged."""

import json
from datetime import UTC, datetime
from pathlib import Path

from workers.providers.store import ProviderStore
from workers.providers.upstox import UpstoxClient
from workers.providers.upstox_terminal import master, snapshot


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    root = repo / ".local-data/p30-upstox-validation"
    client = UpstoxClient(ProviderStore(root), budget=1)
    instruments = master(root, client, datetime.now(UTC))
    names = ("BAJFINANCE", "RELIANCE", "TCS")
    selected = []
    for name in names:
        matches = [i for i in instruments if i.symbol == name]
        if len(matches) != 1:
            raise ValueError("EXACT_CURRENT_MASTER_SYMBOL_REQUIRED")
        selected.append(matches[0])
    result = snapshot(root, keys=tuple(i.provider_key for i in selected))
    receipt = {
        "schema": "p31.selected-cohort.verification.v1",
        "verified_at": datetime.now(UTC).isoformat(),
        "total_gets": client.calls + result["api_calls_this_request"],
        "market_payloads_retained": False,
        "retained_ingestion": False,
        "historical_archive_joined": False,
        "items": [],
    }
    for item in result["items"]:
        q, sessions = item["quote"], item["session_ohlc"]
        receipt["items"].append(
            {
                "symbol": item["symbol"],
                "isin": item["identity"]["isin"],
                "instrument_key": item["instrument_key"],
                "master_observed_at": item["identity"]["observed_at"],
                "state": item["state"],
                "latest_daily_session": item["latest_session"],
                "candle_count": len(item["rows"]),
                "quote_state": q["state"],
                "quote_snapshot_at": q.get("snapshot_at"),
                "quote_reported_snapshot_at": q.get("reported_snapshot_at"),
                "last_trade_at": q.get("last_trade_at"),
                "quote_freshness": q.get("freshness"),
                "clock": q["clock"],
                "previous_close_supplied": q.get("previous_close") is not None,
                "change_basis": q.get("change_basis"),
                "ohlc_state": sessions["state"],
                "ohlc_current_session": sessions["current"]["session"]
                if sessions["current"]
                else None,
                "ohlc_previous_session": sessions["previous"]["session"]
                if sessions["previous"]
                else None,
                "market": item["market"],
                "current_session_status": item["current_session_status"],
                "price_basis": "UNKNOWN",
                "corporate_actions": "UNVERIFIED",
            }
        )
    output = repo / ".local-data/p31-live-verification.json"
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P31_LIVE_CHECK_UNAVAILABLE","sensitive_output":false}')
        raise SystemExit(1) from None
