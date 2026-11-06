"""One explicit authenticated six-equity quote batch; retain only verification metadata."""

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from workers.providers.indicative import STATE, uncertain_quote
from workers.providers.store import ProviderStore
from workers.providers.upstox import UpstoxClient
from workers.providers.upstox_terminal import quote as validate_quote

from alphalens_api.local.cli import configured
from alphalens_data.providers.multi_contracts import Instrument

SYMBOLS = ("RELIANCE", "BAJFINANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fresh", action="store_true", help="One explicit GET, no cached quote reuse"
    )
    parser.add_argument("--include-indicative", action="store_true")
    args = parser.parse_args()
    if args.include_indicative and not args.fresh:
        raise ValueError("INDICATIVE_VERIFICATION_REQUIRES_ONE_FRESH_BATCH")
    if args.output.exists():
        raise ValueError("NEW_METADATA_RECEIPT_REQUIRED")
    repo = Path(__file__).resolve().parents[1]
    credentials = json.loads(
        (repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=90) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        credentials.clear()
        login.raise_for_status()
        keys = []
        instruments = []
        count = 0
        for symbol in SYMBOLS:
            response = client.get(
                "/api/v1/providers/upstox-private/instruments", params={"q": symbol}
            )
            response.raise_for_status()
            data = response.json()["data"]
            count = data["candidate_count"]
            matches = [i for i in data["instruments"] if i["symbol"] == symbol]
            if len(matches) != 1 or matches[0]["provider_key"] != "NSE_EQ|" + matches[0]["isin"]:
                raise ValueError("VERIFIED_EXACT_NSE_IDENTITY_REQUIRED")
            keys.append(matches[0]["provider_key"])
            instruments.append(Instrument.model_validate(matches[0]))
        if args.fresh:
            settings = configured(repo / ".local-data/p33-browser-runtime/operator-config.json")
            if settings.upstox_validation_root is None:
                raise ValueError("PROTECTED_PROVIDER_ROOT_REQUIRED")
            provider = UpstoxClient(
                ProviderStore(settings.upstox_validation_root),
                budget=1,
                retries=0,
                calibrate_quotes=True,
            )
            reply = provider.get("quote", keys=tuple(keys))
            observations: list[dict[str, Any]] = [
                {
                    "symbol": i.symbol,
                    "instrument_key": i.provider_key,
                    "quote": validate_quote(reply, i),
                }
                for i in instruments
            ]
            if args.include_indicative:
                for item, instrument in zip(observations, instruments, strict=True):
                    item["indicative_quote"] = uncertain_quote(reply, instrument, item["quote"])
            data = {
                "retained": False,
                "full_nse_coverage": False,
                "items": observations,
                "valid_quote_count": sum(
                    i["quote"]["state"] == "VALIDATED_SNAPSHOT" for i in observations
                ),
                "api_calls_this_request": provider.calls,
            }
        else:
            response = client.get(
                "/api/v1/providers/upstox-private/watchlist",
                params={"instrument_keys": ",".join(keys)},
            )
            response.raise_for_status()
            data = response.json()["data"]
        if data["retained"] or data["full_nse_coverage"] or len(data["items"]) != 6:
            raise ValueError("EXPLICIT_TRANSIENT_COHORT_REQUIRED")
        rows = []
        for item in data["items"]:
            quote = item["quote"]
            accepted = quote["state"] == "VALIDATED_SNAPSHOT"
            stamp = quote.get("snapshot_at", quote.get("reported_snapshot_at"))
            trade = quote.get("last_trade_at", quote.get("reported_last_trade_at"))
            receipt = quote["clock"]["local_received_at"]
            evidence = quote["clock"].get("calibration", {})
            receipt_bound = evidence.get("receipt_lower_at", receipt)
            chronology = bool(stamp and trade) and (
                datetime.fromisoformat(trade)
                <= datetime.fromisoformat(stamp)
                <= datetime.fromisoformat(receipt_bound)
            )
            correct_change = None
            if accepted:
                if not chronology:
                    raise ValueError("ACCEPTED_QUOTE_CHRONOLOGY_INVALID")
                previous = quote.get("previous_close")
                if previous is not None:
                    delta = Decimal(quote["ltp"]) - Decimal(previous)
                    correct_change = (
                        Decimal(quote["change"]) == delta
                        and Decimal(quote["change_percent"]) == delta / Decimal(previous) * 100
                    )
                    if not correct_change:
                        raise ValueError("DOCUMENTED_PREVIOUS_CLOSE_CHANGE_MISMATCH")
            elif "ltp" in quote:
                raise ValueError("REJECTED_QUOTE_MUST_NOT_EXPOSE_LTP")
            display = item.get("indicative_quote")
            display_metadata = None
            if display is not None:
                generated = datetime.fromisoformat(display["snapshot_at"])
                interval = display["clock"]["calibration"]
                bounds_valid = (
                    datetime.fromisoformat(interval["receipt_lower_at"])
                    < generated
                    <= datetime.fromisoformat(interval["receipt_upper_at"])
                )
                if (
                    not bounds_valid
                    or display["state"] != STATE
                    or display["financial_input_eligible"]
                    or display["strict_verified"]
                ):
                    raise ValueError("INDICATIVE_CLASSIFICATION_INVALID")
                previous = display["previous_close"]
                arithmetic = previous is not None and (
                    Decimal(display["change"]) == Decimal(display["ltp"]) - Decimal(previous)
                    and Decimal(display["change_percent"])
                    == (Decimal(display["ltp"]) - Decimal(previous)) / Decimal(previous) * 100
                )
                if previous is not None and not arithmetic:
                    raise ValueError("INDICATIVE_PREVIOUS_CLOSE_CHANGE_MISMATCH")
                display_metadata = {
                    "state": display["state"],
                    "display_only": True,
                    "strict_verified": False,
                    "financial_input_eligible": False,
                    "generation_inside_interval": bounds_valid,
                    "previous_close_change_correct": arithmetic,
                    "raw_provider_timestamp": display["raw_provider_timestamp"],
                    "raw_last_trade_time": display["raw_last_trade_time"],
                    "freshness": display["freshness"],
                    "timing_uncertainty_seconds": display["timing_uncertainty_seconds"],
                }
            rows.append(
                {
                    "symbol": item["symbol"],
                    "instrument_key": item["instrument_key"],
                    "quote_state": quote["state"],
                    "quote_generated_at": stamp,
                    "last_trade_at": trade,
                    "local_received_at": receipt,
                    "clock": quote["clock"],
                    "indicative_display": display_metadata,
                    "strict_chronology_passed": chronology,
                    "documented_previous_close_change_correct": correct_change,
                    "latest_eod_session": item.get("latest_session"),
                    "daily_candles_requested": False,
                    "market_values_retained": False,
                }
            )
        result = {
            "version": "p34.quote-verification.v1",
            "verified_at": datetime.now(UTC).isoformat(),
            "current_quotes": "PASSED"
            if all(r["quote_state"] == "VALIDATED_SNAPSHOT" for r in rows)
            else "NOT_ACCEPTED",
            "verified_current_identities": count,
            "queried_count": 6,
            "accepted_quote_count": data["valid_quote_count"],
            "indicative_quote_count": sum(r["indicative_display"] is not None for r in rows),
            "displayable_quote_count": sum(
                r["quote_state"] == "VALIDATED_SNAPSHOT" or r["indicative_display"] is not None
                for r in rows
            ),
            "quote_provider_gets": data["api_calls_this_request"],
            "search_http_requests": 6,
            "full_market_polling": False,
            "market_values_retained": False,
            "fresh_quote_requested": args.fresh,
            "items": rows,
        }
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P34_QUOTE_VERIFICATION_FAILED","sensitive_output":false}')
        raise SystemExit(1) from None
