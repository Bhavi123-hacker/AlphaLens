"""Dated cash-market discovery only. Never authorizes collection or BSE inference.

Version two is opt-in so original immutable NSE snapshot derivations stay exact.
The complete official master is retained privately; derivatives are counted, not
promoted into equity search. An absent BSE status stays explicitly unknown.
"""

import gzip
import io
import json
import zlib
from collections import Counter
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.errors import DataContractError

from . import universe
from .upstox import Reply

VERSION = "upstox.current-cash-equity.v2"
SOURCE = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
# BSE groups are classifications, not a representation of NSE security series.
BSE_ORDINARY_GROUPS = frozenset({"A", "B", "X", "XT", "T", "M", "MT", "Z", "ZP", "P", "TS", "MS"})


def classify(row: dict[str, Any]) -> str:
    if row.get("segment") == "NSE_EQ":
        return universe.classification(row)
    if row.get("segment") != "BSE_EQ" or row.get("exchange") != "BSE":
        return "NON_CASH_SEGMENT"
    isin = row.get("isin")
    if not isinstance(isin, str) or not universe.valid_isin(isin):
        return "INVALID_ISIN_CHECKSUM_OR_FORMAT"
    if row.get("instrument_key") != "BSE_EQ|" + isin:
        return "INSTRUMENT_KEY_ISIN_MISMATCH"
    if not isinstance(row.get("trading_symbol"), str) or not 1 <= len(row["trading_symbol"]) <= 64:
        return "MISSING_OR_INVALID_SYMBOL"
    if not isinstance(row.get("name"), str) or not 1 <= len(row["name"]) <= 256:
        return "MISSING_OR_INVALID_COMPANY_NAME"
    if isin.startswith("INF"):
        return "FUND_OR_ETF_ISIN"
    if isin.startswith("IN9"):
        return "DIFFERENT_EQUITY_RIGHTS_NOT_ORDINARY"
    if not isin.startswith("INE") or isin[7:9] != "01":
        return "UNVERIFIED_ORDINARY_EQUITY_ISIN_CLASS"
    if (
        not isinstance(row.get("instrument_type"), str)
        or row["instrument_type"] not in BSE_ORDINARY_GROUPS
    ):
        return "UNSUPPORTED_NON_COMMON_GROUP"
    if row.get("security_type") is not None and (
        not isinstance(row["security_type"], str)
        or row["security_type"] not in universe.SECURITY_TYPES
    ):
        return "UNKNOWN_PROVIDER_SECURITY_STATUS"
    return "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"


def parse_all(reply: Reply) -> universe.Snapshot:
    if reply.state != "ACCEPTED" or reply.status != 200 or reply.received_at.utcoffset() is None:
        raise DataContractError("UNIVERSE_MASTER_UNAVAILABLE_OR_UNDATED")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(reply.body)) as stream:
            body = stream.read(128_000_001)
        native = json.loads(body)
        if (
            len(body) > 128_000_000
            or not isinstance(native, list)
            or not all(isinstance(row, dict) for row in native)
        ):
            raise ValueError
    except (OSError, ValueError, EOFError, zlib.error):
        raise DataContractError("UNIVERSE_MASTER_MALFORMED") from None
    raw_sha = universe._sha(reply.body)
    cash = [row for row in native if row.get("segment") in ("NSE_EQ", "BSE_EQ")]
    if any(
        not isinstance(row.get("instrument_key"), str)
        or not isinstance(row.get("trading_symbol"), str)
        for row in cash
    ):
        raise DataContractError("UNIVERSE_MASTER_IDENTITY_FIELDS_MALFORMED")
    keys = Counter(row["instrument_key"] for row in cash)
    records = []
    for row in cash:
        reason = classify(row)
        if keys[row["instrument_key"]] != 1:
            reason = "DUPLICATE_OR_AMBIGUOUS_INSTRUMENT_KEY"
        eligible = reason == "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"
        records.append(
            {
                "instrument_key": row["instrument_key"],
                "isin": row.get("isin"),
                "symbol": row["trading_symbol"],
                "name": row.get("name"),
                "exchange": row.get("exchange"),
                "segment": row.get("segment"),
                "instrument_type": row.get("instrument_type"),
                "security_type": row.get("security_type"),
                "lot_size": row.get("lot_size"),
                "trading_status": "PRESENT_IN_DATED_BOD_NOT_SUSPENSION_VERIFIED",
                "provider_status_available": row.get("security_type") is not None,
                "source_date": reply.received_at.astimezone(ZoneInfo("Asia/Kolkata"))
                .date()
                .isoformat(),
                "source_date_basis": "MASTER_RECEIPT_DATE_NOT_VERIFIED_PROVIDER_PUBLICATION_DATE",
                "master_sha256": raw_sha,
                "classification": reason,
                "eligible_common_equity": eligible,
                "model_segment_status": "NSE_MODEL_REQUIRES_COMPATIBLE_SAVED_FEATURES"
                if row.get("segment") == "NSE_EQ"
                else "MODEL_NOT_VALIDATED_FOR_THIS_SEGMENT",
            }
        )
    records.sort(key=lambda row: (str(row["symbol"]).casefold(), str(row["instrument_key"])))
    ordinary = [row for row in records if row["eligible_common_equity"]]
    # Only NSE identities can enter the existing collection selector. Its strict
    # duplicate-symbol and series/status rules are preserved by the v1 parser.
    nse_reply = Reply(
        200,
        gzip.compress(
            json.dumps([row for row in native if row.get("segment") == "NSE_EQ"]).encode(), mtime=0
        ),
        reply.received_at,
        "ACCEPTED",
    )
    nse = universe.parse(nse_reply)
    nse_eligible = tuple(
        item.model_copy(update={"revision_sha256": raw_sha}) for item in nse.eligible
    )
    summary = {
        "schema": VERSION,
        "source": SOURCE,
        "raw_sha256": raw_sha,
        "observed_at": reply.received_at.isoformat(),
        "all_bod_records": len(native),
        "all_nse_master_rows": sum(row.get("exchange") == "NSE" for row in native),
        "discoverable_nse_cash_identities": sum(row["segment"] == "NSE_EQ" for row in records),
        "discoverable_bse_cash_identities": sum(row["segment"] == "BSE_EQ" for row in records),
        "discoverable_nse_eq_type_eq": sum(
            row["segment"] == "NSE_EQ" and row["instrument_type"] == "EQ" for row in records
        ),
        "verified_eligible_common_equities": len(ordinary),
        "searchable_unique_instrument_keys": len({row["instrument_key"] for row in ordinary}),
        "unique_ordinary_company_isins": len({row["isin"] for row in ordinary}),
        "eligible_by_exchange": dict(sorted(Counter(row["exchange"] for row in ordinary).items())),
        "all_records_by_segment": dict(
            sorted(Counter(str(row.get("segment")) for row in native).items())
        ),
        "exclusion_counts": dict(
            sorted(
                Counter(
                    row["classification"] for row in records if not row["eligible_common_equity"]
                ).items()
            )
        ),
        "historical_membership_established": False,
        "independently_accepted_ml_stocks": 0,
        "bse_ml_compatible": False,
        "classification_evidence": universe.CLASSIFICATION_EVIDENCE,
        "coverage_note": (
            "Identity discovery only; BSE is not admitted to NSE collection or model inference. "
            "BOD presence does not prove suspension status, data rights "
            "or provider candle availability."
        ),
    }
    snapshot_id = universe._sha(universe._encoded({"summary": summary, "records": records}))
    return universe.Snapshot(snapshot_id, reply.received_at, nse_eligible, tuple(records), summary)
