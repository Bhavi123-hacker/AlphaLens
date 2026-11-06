"""P19-owned versioned provider observations; no historical canonical promotion."""

import json
from collections.abc import Callable
from typing import Any

from alphalens_data.daily.contracts import Request
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Instrument


def stage(
    request: Request, payload: bytes, store: Store, check: Callable[[str], None]
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    """Called only after existing source rights/calendar/checksum gates in Worker.

    The envelope contains one original official candle response and its current
    instrument identity. Unknown basis, actions and publication remain unknown.
    These observations cannot enter frozen P5/P6 research or the model pipeline.
    """
    if len(payload) > 2_000_000:
        raise DataContractError("OPERATIONAL_RELEASE_SIZE_LIMIT")
    envelope = json.loads(payload)
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"version", "instrument", "received_at", "response"}
        or envelope["version"] != "p30.upstox.operational-release.v1"
    ):
        raise DataContractError("OPERATIONAL_RELEASE_SCHEMA_REJECTED")
    instrument = Instrument.model_validate(envelope["instrument"])
    if (
        instrument.provider != "upstox"
        or instrument.exchange != "NSE"
        or instrument.canonical_security_id is not None
        or envelope["received_at"] != request.source_received_at.isoformat()
        or not isinstance(envelope["response"], str)
    ):
        raise DataContractError("OPERATIONAL_RELEASE_IDENTITY_OR_CLOCK_REJECTED")
    native = envelope["response"].encode("utf-8")
    candles = parse_daily(native, instrument, request.source_received_at)
    if any(c.session != request.session for c in candles) or len(candles) > 1:
        raise DataContractError("OPERATIONAL_RELEASE_SINGLE_SESSION_REQUIRED")
    if request.expected_security_ids and request.expected_security_ids != (
        instrument.provider_key,
    ):
        raise DataContractError("OPERATIONAL_EXPECTED_PROVIDER_KEY_MISMATCH")
    rows = []
    for candle in candles:
        item = candle.model_dump(mode="json")
        # Economic identity excludes retrieval time: repeated receipt does not
        # invent a new price. A changed OHLCV has a different observation identity.
        item["observation_id"] = checksum(
            stable_json(
                {
                    "key": instrument.provider_key,
                    "session": str(candle.session),
                    "ohlcv": [
                        str(candle.open),
                        str(candle.high),
                        str(candle.low),
                        str(candle.close),
                        candle.volume,
                    ],
                    "price_basis": candle.price_basis,
                }
            )
        )
        rows.append(item)
    products = {
        "provider_observations": store.write(
            request.run_id,
            "provider-observations.json",
            {
                "version": "p30.upstox.observations.v1",
                "rows": rows,
                "native_response": envelope["response"],
                "native_response_sha256": checksum(native),
                "coverage": {"expected": 1, "observed": len(rows), "scope": "ONE_PROVIDER_KEY"},
                "identity_semantics": "CURRENT_MASTER_NOT_HISTORICAL_MEMBERSHIP",
                "canonical_join_permitted": False,
                "feature_eligibility": False,
            },
        )
    }
    check("provider_observations")
    reasons = [
        "PRICE_BASIS_ACTION_AND_PUBLICATION_EVIDENCE_UNAVAILABLE",
        "DATED_COMMON_EQUITY_AND_PEER_UNIVERSE_UNAVAILABLE",
        "CURRENT_MODEL_ACCEPTANCE_NOT_PASSED",
        "PROVIDER_OBSERVATIONS_NOT_FROZEN_RESEARCH_CANONICAL",
    ]
    if not rows:
        reasons.append("MISSING_SOURCE_OBSERVATION")
    check("before_publish")
    return (
        products,
        reasons,
        {"observations": len(rows), "missing": int(not rows), "feature_rows": 0, "predictions": 0},
    )
