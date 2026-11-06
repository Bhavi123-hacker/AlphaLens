"""Explicit bounded live verification, sanitized receipts only, no price retention."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from workers.providers.store import ProviderStore
from workers.providers.upstox import KEY, UpstoxClient, instrument_master

from alphalens_data.providers.multi_adapters import parse_daily


def main() -> None:
    root = Path(__file__).resolve().parents[1] / ".local-data/p30-upstox-validation"
    store = ProviderStore(root)
    client = UpstoxClient(store, budget=3)
    reply = client.get("instruments")
    instruments, summary = instrument_master(reply)
    identity = next(i for i in instruments if i.provider_key == KEY)
    # Current instrument metadata only, supported by the official download mechanism.
    # Never historical membership or a retained price body.
    metadata_path = root / (
        "master-identity-" + reply.received_at.strftime("%Y%m%dT%H%M%S%f") + ".json"
    )
    metadata_path.write_text(identity.model_dump_json(), encoding="utf-8")
    category_file = root.parent / "p30-token-category.json"
    category = (
        json.loads(category_file.read_bytes())
        if category_file.exists()
        else {"category": "UNDETERMINED"}
    )
    from zoneinfo import ZoneInfo

    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    candle = client.get("candles", start=today - timedelta(days=14), end=today - timedelta(days=1))
    receipt = {
        **summary,
        "schema": "p30.upstox.validation.v1",
        "category": category["category"],
        "category_evidence": "LOCAL_OPERATOR_NOT_SERVER_SCOPE_PROOF",
        "authentication": candle.state,
        "credential_readback": True,
        "verified_at": datetime.now(UTC).isoformat(),
        "requests": [
            {"operation": "instruments", "state": "ACCEPTED", "http_status": reply.status},
            {"operation": "candles", "state": candle.state, "http_status": candle.status},
        ],
        "instrument_key": KEY,
        "exchange": "NSE",
        "segment": "NSE_EQ",
        "market_payloads_retained": False,
        "collection_enabled": False,
        "scheduler_enabled": False,
    }
    if candle.state == "ACCEPTED":
        identity = next(i for i in instruments if i.provider_key == KEY)
        rows = parse_daily(candle.body, identity, candle.received_at)
        receipt.update(
            {
                "valid_candles": len(rows),
                "sessions": [str(r.session) for r in rows],
                "latest_provider_daily_session": str(rows[-1].session) if rows else None,
                "price_basis": "UNKNOWN",
                "publication_time": None,
                "ohlcv_schema": "VALID_DECIMAL_OHLC_INTEGER_VOLUME",
                "timezone": "Asia/Kolkata",
                "official_final_close": "NOT_ESTABLISHED",
                "eligible_denominator": 1,
                "instruments_queried": 1,
                "successful_instruments": int(bool(rows)),
                "quarantined": 0,
            }
        )
    quote = client.get("quote")
    q = {"operation": "quote", "http_status": quote.status, "state": quote.state}
    if quote.state == "ACCEPTED":
        payload = json.loads(quote.body)
        values = list(payload.get("data", {}).values())
        if len(values) != 1 or values[0].get("instrument_token") != KEY:
            q["state"] = "IDENTITY_REJECTED"
        else:
            raw_stamp = values[0].get("timestamp")
            stamp = datetime.fromisoformat(raw_stamp) if isinstance(raw_stamp, str) else None
            q["snapshot_timestamp"] = stamp.isoformat() if stamp else None
            q["receipt_timestamp"] = quote.received_at.isoformat()
            q["state"] = (
                "VALIDATED_SNAPSHOT"
                if stamp and stamp.tzinfo and stamp <= quote.received_at
                else "QUOTE_TIME_REJECTED"
            )
            q["is_final_eod_close"] = False
    receipt["requests"].append(q)
    receipt["authenticated_calls_this_check"] = client.calls - 1
    receipt["static_calls_this_check"] = 1
    output = root / ("validation-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json")
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import re

        reason = str(exc) if re.fullmatch(r"[A-Z_]{5,100}", str(exc)) else "DETAILS_REDACTED"
        print(
            json.dumps(
                {
                    "state": "LIVE_VERIFICATION_REJECTED",
                    "error_category": type(exc).__name__,
                    "reason": reason,
                    "secret_output": False,
                }
            )
        )
        raise SystemExit(1) from None
