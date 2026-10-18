"""Dated current NSE common-equity identities; never historical membership or prices.

Explicit refresh is the only network operation. Search and loading only inspect
checksum-verified private snapshots. A master disappearance is not a delisting.
"""

import gzip
import hashlib
import io
import json
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_contracts import Instrument

from .store import ProviderStore
from .upstox import MASTER_HOST, MASTER_PATH, Reply, UpstoxClient

VERSION = "upstox.current-nse-common-equity.v1"
COMMON_SERIES = frozenset({"EQ", "BE", "BZ", "SM", "ST", "SZ"})
SECURITY_TYPES = frozenset({"NORMAL", "SME", "PCA", "IPO", "RELIST"})
CLASSIFICATION_EVIDENCE = {
    "series": "https://www.nseindia.com/static/market-data/legend-of-series",
    "isin": "https://nsdl.co.in/downloadables/Core%20Services.pdf",
    "master": "https://upstox.com/developer/api-documentation/instruments/",
    "status": "https://upstox.com/developer/api-documentation/appendix/equity-security-type/",
}


def _encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _path(root: Path, name: str) -> Path:
    path = root / name
    if root.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise DataContractError("UNIVERSE_PRIVATE_PATH_REQUIRED")
    return path


def _write(path: Path, body: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(body)
    if __import__("os").name != "nt":
        path.chmod(0o600)


def valid_isin(isin: str) -> bool:
    """ISO-6166 check digit, with expanded alphabetic characters and Luhn sum."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in isin)
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char) * (2 if index % 2 else 1)
        total += value // 10 + value % 10
    return total % 10 == 0


def classification(row: dict[str, Any]) -> str:
    """Fail closed for funds, nonordinary rights, unsupported or unknown series."""
    if row.get("segment") != "NSE_EQ" or row.get("exchange") != "NSE":
        return "NOT_NSE_CASH_SEGMENT"
    isin = row.get("isin")
    if not isinstance(isin, str) or not valid_isin(isin):
        return "INVALID_ISIN_CHECKSUM_OR_FORMAT"
    if row.get("instrument_key") != "NSE_EQ|" + isin:
        return "INSTRUMENT_KEY_ISIN_MISMATCH"
    if not isinstance(row.get("trading_symbol"), str) or not 1 <= len(row["trading_symbol"]) <= 64:
        return "MISSING_OR_INVALID_SYMBOL"
    if not isinstance(row.get("name"), str) or not 1 <= len(row["name"]) <= 256:
        return "MISSING_OR_INVALID_COMPANY_NAME"
    if (
        not isinstance(row.get("instrument_type"), str)
        or row["instrument_type"] not in COMMON_SERIES
    ):
        return "UNSUPPORTED_NON_COMMON_SERIES"
    if isin.startswith("INF"):
        return "FUND_OR_ETF_ISIN"
    if isin.startswith("IN9"):
        return "DIFFERENT_EQUITY_RIGHTS_NOT_ORDINARY"
    if not isin.startswith("INE") or isin[7:9] != "01":
        return "UNVERIFIED_ORDINARY_EQUITY_ISIN_CLASS"
    if not isinstance(row.get("security_type"), str) or row["security_type"] not in SECURITY_TYPES:
        return "UNKNOWN_PROVIDER_SECURITY_STATUS"
    return "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"


def is_ordinary_instrument(instrument: Instrument) -> bool:
    """Identity predicate for an already positively verified master selection.

    This does not upgrade quote timestamps, source permission or ML eligibility.
    Provider status was checked when constructing the verified snapshot.
    """
    return (
        instrument.provider == "upstox"
        and instrument.exchange == "NSE"
        and instrument.segment == "NSE_EQ"
        and instrument.instrument_type in COMMON_SERIES
        and instrument.isin is not None
        and instrument.isin.startswith("INE")
        and instrument.isin[7:9] == "01"
        and valid_isin(instrument.isin)
        and instrument.provider_key == "NSE_EQ|" + instrument.isin
        and instrument.identity_evidence == "UPSTOX_CURRENT_BOD_PLUS_NSE_SERIES_AND_NSDL_ISIN_CLASS"
    )


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    observed_at: datetime
    eligible: tuple[Instrument, ...]
    records: tuple[dict[str, Any], ...]
    summary: dict[str, Any]


def parse(reply: Reply) -> Snapshot:
    if reply.state != "ACCEPTED" or reply.status != 200 or reply.received_at.utcoffset() is None:
        raise DataContractError("UNIVERSE_MASTER_UNAVAILABLE_OR_UNDATED")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(reply.body)) as stream:
            body = stream.read(128_000_001)
        if len(body) > 128_000_000:
            raise ValueError
        native = json.loads(body)
        if not isinstance(native, list) or not all(isinstance(row, dict) for row in native):
            raise ValueError
    except (OSError, ValueError):
        raise DataContractError("UNIVERSE_MASTER_MALFORMED") from None
    raw_sha = _sha(reply.body)
    cash = [row for row in native if row.get("segment") == "NSE_EQ"]
    if any(
        not isinstance(row.get("instrument_key"), str)
        or not isinstance(row.get("trading_symbol"), str)
        for row in cash
    ):
        raise DataContractError("UNIVERSE_MASTER_IDENTITY_FIELDS_MALFORMED")
    key_counts = Counter(row.get("instrument_key") for row in cash)
    # A warrant/debt can share a company symbol with ordinary equity. Only
    # ambiguity *within* the eligible ordinary class blocks symbol selection.
    symbol_counts = Counter(
        row.get("trading_symbol")
        for row in cash
        if classification(row) == "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"
    )
    records: list[dict[str, Any]] = []
    eligible: list[Instrument] = []
    for row in cash:
        reason = classification(row)
        if key_counts[row.get("instrument_key")] != 1:
            reason = "DUPLICATE_OR_AMBIGUOUS_INSTRUMENT_KEY"
        elif (
            reason == "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY"
            and symbol_counts[row.get("trading_symbol")] != 1
        ):
            reason = "DUPLICATE_OR_AMBIGUOUS_SYMBOL"
        record = {
            "instrument_key": row.get("instrument_key"),
            "isin": row.get("isin"),
            "symbol": row.get("trading_symbol"),
            "name": row.get("name"),
            "exchange": row.get("exchange"),
            "segment": row.get("segment"),
            "instrument_type": row.get("instrument_type"),
            "security_type": row.get("security_type"),
            "lot_size": row.get("lot_size"),
            "classification": reason,
            "eligible_common_equity": reason == "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITY",
        }
        records.append(record)
        if record["eligible_common_equity"]:
            eligible.append(
                Instrument(
                    provider="upstox",
                    provider_key=row["instrument_key"],
                    exchange="NSE",
                    segment="NSE_EQ",
                    symbol=row["trading_symbol"],
                    isin=row["isin"],
                    name=row["name"],
                    instrument_type=row["instrument_type"],
                    series=row["instrument_type"],
                    observed_at=reply.received_at,
                    identity_evidence="UPSTOX_CURRENT_BOD_PLUS_NSE_SERIES_AND_NSDL_ISIN_CLASS",
                    revision_sha256=raw_sha,
                )
            )
    records.sort(key=lambda row: (str(row["symbol"]), str(row["instrument_key"])))
    eligible.sort(key=lambda item: (item.symbol, item.provider_key))
    summary = {
        "schema": VERSION,
        "source": f"https://{MASTER_HOST}{MASTER_PATH}",
        "raw_sha256": raw_sha,
        "observed_at": reply.received_at.isoformat(),
        "all_nse_master_rows": len(native),
        "discoverable_nse_cash_identities": len(cash),
        "discoverable_nse_eq_type_eq": sum(row.get("instrument_type") == "EQ" for row in cash),
        "verified_eligible_common_equities": len(eligible),
        "eligible_by_series": dict(
            sorted(Counter(item.instrument_type for item in eligible).items())
        ),
        "exclusion_counts": dict(
            sorted(
                Counter(
                    row["classification"] for row in records if not row["eligible_common_equity"]
                ).items()
            )
        ),
        "classification_evidence": CLASSIFICATION_EVIDENCE,
        "historical_membership_established": False,
        "provider_accessible_stocks": None,
        "validated_historical_stocks": None,
        "technical_feature_eligible_stocks": None,
        "experimental_ml_eligible_stocks": None,
        "independently_accepted_ml_stocks": 0,
        "coverage_note": (
            "Identity discovery only; source access, observed history and model eligibility "
            "require separate evidence."
        ),
    }
    snapshot_id = _sha(_encoded({"summary": summary, "records": records}))
    return Snapshot(snapshot_id, reply.received_at, tuple(eligible), tuple(records), summary)


def save(root: Path, reply: Reply) -> Snapshot:
    """Retain an explicitly retrieved master; original receipt time is immutable."""
    snapshot = parse(reply)
    if not root.exists():
        root.mkdir(parents=True)
        restrict(root)
    verify(root)
    pointer_path = _path(root, "latest.json")
    if pointer_path.exists() and load(root).observed_at > snapshot.observed_at:
        raise DataContractError("UNIVERSE_CURRENT_POINTER_CANNOT_MOVE_BACKWARD")
    raw_name = "master-" + snapshot.summary["raw_sha256"] + ".json.gz"
    raw = _path(root, raw_name)
    if not raw.exists():
        _write(raw, reply.body)
    elif _sha(raw.read_bytes()) != snapshot.summary["raw_sha256"]:
        raise DataContractError("UNIVERSE_MASTER_CHECKSUM_MISMATCH")
    document = _encoded(
        {"id": snapshot.snapshot_id, "summary": snapshot.summary, "records": snapshot.records}
    )
    filename = "snapshot-" + snapshot.snapshot_id + ".json"
    path = _path(root, filename)
    if not path.exists():
        _write(path, document)
    elif path.read_bytes() != document:
        raise DataContractError("UNIVERSE_SNAPSHOT_CONFLICT")
    pointer = _encoded({"file": filename, "sha256": _sha(document)})
    temporary = _path(root, "pointer-" + uuid.uuid4().hex + ".tmp")
    _write(temporary, pointer)
    temporary.replace(pointer_path)
    return snapshot


def refresh(root: Path, provider_root: Path, *, client: UpstoxClient | None = None) -> Snapshot:
    """One explicit master GET, no quotes, historical candles or automatic timer."""
    selected = client or UpstoxClient(ProviderStore(provider_root), budget=1, retries=0)
    return save(root, selected.get("instruments"))


def load(root: Path, *, snapshot_id: str | None = None) -> Snapshot:
    verify(root)
    if snapshot_id is None:
        pointer = json.loads(_path(root, "latest.json").read_bytes())
        filename = pointer["file"]
        if not isinstance(filename, str) or not re.fullmatch(
            r"snapshot-[a-f0-9]{64}\.json", filename
        ):
            raise DataContractError("UNIVERSE_POINTER_INVALID")
    else:
        if not re.fullmatch(r"[a-f0-9]{64}", snapshot_id):
            raise DataContractError("UNIVERSE_SNAPSHOT_ID_INVALID")
        filename = "snapshot-" + snapshot_id + ".json"
        pointer = None
    body = _path(root, filename).read_bytes()
    if pointer is not None and _sha(body) != pointer["sha256"]:
        raise DataContractError("UNIVERSE_SNAPSHOT_CHECKSUM_MISMATCH")
    document = json.loads(body)
    summary = document["summary"]
    raw_sha = summary["raw_sha256"]
    if not isinstance(raw_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", raw_sha):
        raise DataContractError("UNIVERSE_RAW_HASH_INVALID")
    raw = _path(root, "master-" + raw_sha + ".json.gz").read_bytes()
    if _sha(raw) != raw_sha:
        raise DataContractError("UNIVERSE_MASTER_CHECKSUM_MISMATCH")
    snapshot = parse(Reply(200, raw, datetime.fromisoformat(summary["observed_at"]), "ACCEPTED"))
    if (
        snapshot.snapshot_id != document["id"]
        or filename != "snapshot-" + snapshot.snapshot_id + ".json"
        or body
        != _encoded(
            {"id": snapshot.snapshot_id, "summary": snapshot.summary, "records": snapshot.records}
        )
    ):
        raise DataContractError("UNIVERSE_SNAPSHOT_DERIVATION_MISMATCH")
    return snapshot


def fresh(root: Path, *, at: datetime | None = None) -> Snapshot:
    """Current private identity use requires a dated master at most 24 hours old."""
    now = at or datetime.now(UTC)
    if now.utcoffset() is None:
        raise DataContractError("UNIVERSE_AWARE_CURRENT_CLOCK_REQUIRED")
    snapshot = load(root)
    age = (now - snapshot.observed_at).total_seconds()
    if age < 0:
        raise DataContractError("UNIVERSE_FUTURE_OBSERVATION_REJECTED")
    if age > 86400:
        raise DataContractError("UNIVERSE_STALE_REFRESH_REQUIRED")
    return snapshot


def search(
    root: Path, query: str = "", *, page: int = 1, page_size: int = 50, eligible_only: bool = True
) -> dict[str, Any]:
    if (
        type(page) is not int
        or type(page_size) is not int
        or not 1 <= page <= 10000
        or not 1 <= page_size <= 100
        or not isinstance(query, str)
        or len(query) > 128
    ):
        raise DataContractError("UNIVERSE_SEARCH_BOUNDS_REQUIRED")
    snapshot = load(root)
    term = query.strip().casefold()
    records = [
        row
        for row in snapshot.records
        if (not eligible_only or row["eligible_common_equity"])
        and (
            not term
            or any(
                term in str(row[field]).casefold()
                for field in ("name", "symbol", "isin", "instrument_key")
            )
        )
    ]
    return {
        "snapshot_id": snapshot.snapshot_id,
        "observed_at": snapshot.observed_at.isoformat(),
        "total": len(records),
        "page": page,
        "page_size": page_size,
        "rows": records[(page - 1) * page_size : page * page_size],
        "summary": snapshot.summary,
        "provider_requests": 0,
    }


def changes(previous: Snapshot, current: Snapshot) -> dict[str, Any]:
    if current.observed_at <= previous.observed_at:
        raise DataContractError("UNIVERSE_CHANGES_REQUIRE_LATER_OBSERVATION")
    before = {row["instrument_key"]: row for row in previous.records}
    after = {row["instrument_key"]: row for row in current.records}
    return {
        "previous_snapshot": previous.snapshot_id,
        "current_snapshot": current.snapshot_id,
        "added_current_identities": sorted(after.keys() - before.keys()),
        "absent_from_current_master": sorted(before.keys() - after.keys()),
        "changed": [
            {"instrument_key": key, "before": before[key], "after": after[key]}
            for key in sorted(before.keys() & after.keys())
            if before[key] != after[key]
        ],
        "absence_is_not_verified_delisting": True,
        "historical_membership_established": False,
    }


def main() -> None:
    """Explicit identity maintenance; refreshing sends exactly one master GET."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("status", "search", "refresh"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--provider-root", type=Path)
    parser.add_argument("--query", default="")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=50)
    args = parser.parse_args()
    if args.operation == "refresh":
        if args.provider_root is None:
            parser.error("refresh requires the protected provider root")
        snapshot = refresh(args.root, args.provider_root)
        result = {
            "snapshot_id": snapshot.snapshot_id,
            "summary": snapshot.summary,
            "provider_requests": 1,
        }
    elif args.operation == "search":
        fresh(args.root)
        result = search(args.root, args.query, page=args.page, page_size=args.page_size)
    else:
        snapshot = load(args.root)
        age = (datetime.now(UTC) - snapshot.observed_at).total_seconds()
        result = {
            "snapshot_id": snapshot.snapshot_id,
            "summary": snapshot.summary,
            "identity_usable_now": 0 <= age <= 86400,
            "provider_requests": 0,
        }
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError):
        print('{"state":"FAILED","code":"NSE_IDENTITY_OPERATION_FAILED"}')
        raise SystemExit(1) from None
