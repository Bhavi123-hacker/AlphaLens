"""Explicit TEST_ONLY vendor bundle for exercising the original P19 worker offline."""

from datetime import date, datetime
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.normalization import checksum

from .multi_adapters import RATES, decoded, p2_rows, parse_daily
from .multi_contracts import Instrument


def parse_bundle(
    payload: bytes, provider: str, session: date, received_at: datetime
) -> tuple[bytes, tuple[ParsedRow, ...], dict[int, str], dict[str, Any]]:
    bundle = decoded(payload)
    if (
        bundle.get("version") != "p28.test-provider.v1"
        or bundle.get("classification") != "TEST_ONLY"
        or bundle.get("provider") != provider
        or bundle.get("price_basis") != "RAW_UNADJUSTED"
        or provider not in {"upstox", "indstocks", "angel-one"}
    ):
        raise DataContractError("TEST_ONLY_VENDOR_BUNDLE_REQUIRED")
    try:
        body = bytes.fromhex(bundle["native_payload_hex"])
        if checksum(body) != bundle["native_payload_sha256"]:
            raise ValueError
        instruments = tuple(Instrument.model_validate(r) for r in bundle["instruments"])
        if not instruments or len(instruments) > (
            RATES[instruments[0].provider]["candle_batch"] or 0
        ):
            raise ValueError
        result: list[ParsedRow] = []
        names: dict[int, str] = {}
        for instrument in instruments:
            if (
                instrument.provider != provider
                or instrument.exchange != "NSE"
                or not instrument.series
                or not instrument.canonical_security_id
                or not instrument.canonical_security_id.startswith("TEST_ONLY:")
            ):
                raise ValueError
            candles = tuple(
                c.model_copy(
                    update={"price_basis": "RAW_UNADJUSTED", "action_status": "TEST_ONLY_VERIFIED"}
                )
                for c in parse_daily(body, instrument, received_at, "TEST_ONLY")
                if c.session == session
            )
            for row in p2_rows(candles):
                number = len(result) + 2
                result.append(ParsedRow(number, row.original, row.fields, row.error))
                names[number] = instrument.name or "TEST_ONLY COMPANY"
        identities = [dict(r.fields)["security_id"] for r in result]
        if len(identities) != len(set(identities)):
            raise ValueError
        return (
            body,
            tuple(result),
            names,
            {
                "classification": "TEST_ONLY",
                "adapter_version": "p28.offline-adapters.v1",
                "native_payload_sha256": checksum(body),
                "bundle_sha256": checksum(payload),
                "instrument_revisions": sorted({i.revision_sha256 for i in instruments}),
                "publication_time": None,
                "price_basis": "TEST_ONLY_EXPLICIT_RAW_UNADJUSTED",
                "exchange": "NSE",
                "live_activation": "BLOCKED",
            },
        )
    except (ValueError, KeyError, TypeError):
        raise DataContractError("TEST_ONLY_PROVIDER_BUNDLE_INVALID") from None
