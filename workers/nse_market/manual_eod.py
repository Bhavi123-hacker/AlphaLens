"""Offline NSE CM UDiFF final-file adapter with explicit, hash-bound import approval.

The source remains exchange-reported unadjusted EOD. It is never relabelled as
Upstox, mixed into its adjusted history, or used by the pinned model implicitly.
No function in this module downloads market data.
"""

from __future__ import annotations

import csv
import io
import re
import stat
import zipfile
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from alphalens_data.daily.storage import Store
from workers.experimental_nse.acquire import digest, encoded, initialize, write_new
from workers.experimental_nse_v2.data import timing_fact
from workers.nse_market import engine
from workers.providers import universe
from workers.providers.upstox import Reply

SOURCE = "NSE_CM_UDIFF_FINAL_OPERATOR_DOWNLOAD"
BASIS = "NSE_EXCHANGE_REPORTED_UNADJUSTED_EOD"
SCHEMA = "alphalens.nse_manual_eod.v1"
MAX_COMPRESSED = 8_000_000
MAX_UNCOMPRESSED = 64_000_000
MAX_ROWS = 100_000
HEADERS = (
    "TradDt",
    "BizDt",
    "Sgmt",
    "Src",
    "FinInstrmTp",
    "FinInstrmId",
    "ISIN",
    "TckrSymb",
    "SctySrs",
    "XpryDt",
    "FininstrmActlXpryDt",
    "StrkPric",
    "OptnTp",
    "FinInstrmNm",
    "OpnPric",
    "HghPric",
    "LwPric",
    "ClsPric",
    "LastPric",
    "PrvsClsgPric",
    "UndrlygPric",
    "SttlmPric",
    "OpnIntrst",
    "ChngInOpnIntrst",
    "TtlTradgVol",
    "TtlTrfVal",
    "TtlNbOfTxsExctd",
    "SsnId",
    "NewBrdLotQty",
    "Rmks",
    "Rsvd1",
    "Rsvd2",
    "Rsvd3",
    "Rsvd4",
)
NAME = re.compile(r"BhavCopy_NSE_CM_0_0_0_([0-9]{8})_F_0000\.csv(?:\.zip)?\Z")
NUMBER = re.compile(r"[0-9]{1,19}(?:\.[0-9]{1,6})?\Z")


def checked_file(path: Path, maximum: int) -> bytes:
    """Reject reparse ancestors and nonregular sources before reading bytes."""
    path = path.absolute()
    _safe_destination(path)
    if not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError("MANUAL_EOD_FILE_SIZE_REJECTED")
    body = path.read_bytes()
    if len(body) > maximum:
        raise ValueError("MANUAL_EOD_FILE_SIZE_REJECTED")
    return body


def _safe_destination(path: Path) -> None:
    for item in (path.absolute(), *path.absolute().parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("MANUAL_EOD_REPARSE_PATH_REJECTED")


def _publish(path: Path, body: bytes) -> None:
    """A stopped write leaves only an ignored temporary file, never a partial record."""
    _safe_destination(path)
    temporary = path.with_name("t-" + uuid4().hex + ".tmp")
    write_new(temporary, body)
    temporary.replace(path)


def _publish_receipt(path: Path, receipt: dict[str, Any]) -> None:
    body = encoded(receipt)
    # This function runs under the source-store writer lock. An orphan sidecar
    # has no accepted receipt and may be completed on retry. Accepted records
    # are checked by the caller and are never replaced.
    sidecar = path.with_suffix(path.suffix + ".sha256")
    _publish(sidecar, digest(body).encode())
    _publish(path, body)


def _csv(path: Path) -> tuple[bytes, bytes, date]:
    match = NAME.fullmatch(path.name)
    if match is None:
        raise ValueError("MANUAL_EOD_OFFICIAL_FINAL_FILENAME_REQUIRED")
    session = datetime.strptime(match[1], "%Y%m%d").date()
    raw = checked_file(path, MAX_COMPRESSED if path.suffix == ".zip" else MAX_UNCOMPRESSED)
    if path.suffix != ".zip":
        return raw, raw, session
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) != 1:
                raise ValueError("MANUAL_EOD_SINGLE_CSV_REQUIRED")
            member = entries[0]
            if (
                member.filename != path.name.removesuffix(".zip")
                or "/" in member.filename
                or "\\" in member.filename
                or member.is_dir()
                or member.flag_bits & 1
                or stat.S_ISLNK(member.external_attr >> 16)
                or not 0 < member.file_size <= MAX_UNCOMPRESSED
                or member.compress_size > MAX_COMPRESSED
                or member.file_size > max(1, member.compress_size) * 500
            ):
                raise ValueError("MANUAL_EOD_ZIP_MEMBER_REJECTED")
            with archive.open(member) as stream:
                body = stream.read(MAX_UNCOMPRESSED + 1)
            if len(body) != member.file_size or len(body) > MAX_UNCOMPRESSED:
                raise ValueError("MANUAL_EOD_ZIP_SIZE_REJECTED")
            return raw, body, session
    except (zipfile.BadZipFile, OSError, RuntimeError):
        raise ValueError("MANUAL_EOD_ZIP_INVALID") from None


def _at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("MANUAL_EOD_AWARE_TIMESTAMP_REQUIRED")
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("MANUAL_EOD_AWARE_TIMESTAMP_REQUIRED")
    return result


def _decimal(value: str, *, positive: bool = True) -> Decimal:
    if NUMBER.fullmatch(value) is None:
        raise ValueError("INVALID_DECIMAL")
    result = Decimal(value)
    if not result.is_finite() or (result <= 0 if positive else result < 0):
        raise ValueError("INVALID_DECIMAL")
    return result


def _rows(body: bytes, session: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        text = body.decode("utf-8-sig")
        if "\x00" in text:
            raise ValueError("MANUAL_EOD_NUL_REJECTED")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError("MANUAL_EOD_EXACT_SCHEMA_REQUIRED")
        accepted: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ValueError("MANUAL_EOD_ROW_LIMIT")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("MANUAL_EOD_CSV_WIDTH_REJECTED")
            if row["TradDt"] != str(session) or row["BizDt"] != str(session):
                raise ValueError("MANUAL_EOD_FILENAME_SESSION_MISMATCH")
            if row["Sgmt"] != "CM" or row["Src"] != "NSE":
                raise ValueError("MANUAL_EOD_NSE_CASH_SOURCE_REQUIRED")
            isin, symbol, series = row["ISIN"], row["TckrSymb"], row["SctySrs"]
            reason = None
            if row["FinInstrmTp"] != "STK" or series not in universe.COMMON_SERIES:
                reason = "UNSUPPORTED_INSTRUMENT_OR_SERIES"
            elif not universe.valid_isin(isin) or not isin.startswith("INE") or isin[7:9] != "01":
                reason = "NOT_VERIFIED_ORDINARY_EQUITY_ISIN"
            elif re.fullmatch(r"[A-Z0-9&.\-]{1,32}", symbol) is None:
                reason = "INVALID_SYMBOL"
            elif any(row[key] for key in ("XpryDt", "FininstrmActlXpryDt", "StrkPric", "OptnTp")):
                reason = "DERIVATIVE_FIELDS_IN_CASH_RECORD"
            elif row["SsnId"] not in {"", "F1"}:
                reason = "MULTIPLE_OR_UNQUALIFIED_SESSION"
            elif row["Rmks"] or any(row[key] for key in ("Rsvd1", "Rsvd2", "Rsvd3", "Rsvd4")):
                reason = "REMARKS_OR_SCHEMA_EXTENSION_REQUIRES_REVIEW"
            if reason:
                exclusions.append({"line": number, "reason": reason})
                continue
            slot = isin, series
            if slot in seen:
                raise ValueError("MANUAL_EOD_DUPLICATE_IDENTITY_SERIES_CONFLICT")
            seen.add(slot)
            try:
                opened, high, low, close = (
                    _decimal(row[key]) for key in ("OpnPric", "HghPric", "LwPric", "ClsPric")
                )
                if low > min(opened, close) or high < max(opened, close) or low > high:
                    raise ValueError("INVALID_OHLC")
                volume = _decimal(row["TtlTradgVol"], positive=False)
                if volume != volume.to_integral_value() or volume >= 10**25:
                    raise ValueError("INVALID_VOLUME")
                if not row["FinInstrmId"].isdigit() or len(row["FinInstrmId"]) > 10:
                    raise ValueError("INVALID_EXCHANGE_TOKEN")
            except ValueError as exc:
                exclusions.append({"line": number, "reason": str(exc)})
                continue
            accepted.append(
                {
                    "key": "NSE_EQ|" + isin,
                    "symbol": symbol,
                    "isin": isin,
                    "exchange": "NSE",
                    "segment": "NSE_EQ",
                    "series": series,
                    "session": str(session),
                    "open": str(opened),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": int(volume),
                    "source": SOURCE,
                    "price_basis": BASIS,
                    "provider_candle_at": None,
                    "corporate_action_status": "UNQUALIFIED_FOR_ADJUSTED_MODEL",
                }
            )
        if not accepted:
            raise ValueError("MANUAL_EOD_NO_ACCEPTABLE_EQUITY_ROWS")
        return accepted, exclusions
    except (UnicodeError, csv.Error):
        raise ValueError("MANUAL_EOD_CSV_ENCODING_OR_SYNTAX_REJECTED") from None


def review(
    path: Path,
    provenance: dict[str, Any],
    master: universe.Snapshot,
    calendar_path: Path,
    *,
    at: datetime,
) -> dict[str, Any]:
    """Preview a local file; proof of source rights and import approval stay separate."""
    if at.utcoffset() is None:
        raise ValueError("MANUAL_EOD_AWARE_TIMESTAMP_REQUIRED")
    if master.observed_at.utcoffset() is None or master.observed_at > at:
        raise ValueError("MANUAL_EOD_MASTER_AFTER_REVIEW_REJECTED")
    raw, body, session = _csv(path)
    source_url = "https://nsearchives.nseindia.com/content/cm/" + path.name
    if provenance.get("source_url") != source_url or provenance.get("raw_sha256") != digest(raw):
        raise ValueError("MANUAL_EOD_OFFICIAL_PROVENANCE_HASH_REQUIRED")
    retrieved, published = (_at(provenance.get(key)) for key in ("retrieved_at", "published_at"))
    if (
        not isinstance(provenance.get("publication_reference"), str)
        or not provenance["publication_reference"]
    ):
        raise ValueError("MANUAL_EOD_PUBLICATION_EVIDENCE_REQUIRED")
    calendar = engine._read(calendar_path)
    calendar_raw = bytes.fromhex(calendar["raw_hex"])
    calendar_at = _at(calendar["received_at"])
    if digest(calendar_raw) != calendar["raw_sha256"] or calendar_at > at:
        raise ValueError("MANUAL_EOD_CALENDAR_CHECKSUM_OR_RECEIPT_REJECTED")
    timing = timing_fact(Reply(200, calendar_raw, calendar_at, "ACCEPTED"), session)
    if timing is None or not _at(timing["close_at"]) < published <= retrieved <= at:
        raise ValueError("MANUAL_EOD_COMPLETED_SESSION_PUBLICATION_REQUIRED")
    rows, exclusions = _rows(body, session)
    mapping: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in master.records:
        if row.get("exchange") == "NSE" and row.get("eligible_common_equity"):
            mapping.setdefault((row["isin"], row["symbol"], row["instrument_type"]), []).append(row)
    accepted = []
    for row in rows:
        matched = mapping.get((row["isin"], row["symbol"], row["series"]), [])
        if len(matched) != 1 or matched[0]["instrument_key"] != row["key"]:
            exclusions.append({"key": row["key"], "reason": "EXACT_NSE_MASTER_MAPPING_UNAVAILABLE"})
            continue
        accepted.append({**row, "received_at": retrieved.isoformat(), "raw_sha256": digest(raw)})
    if not accepted:
        raise ValueError("MANUAL_EOD_NO_UNAMBIGUOUS_MASTER_MATCHES")
    if len({row["key"] for row in accepted}) != len(accepted):
        raise ValueError("MANUAL_EOD_MULTIPLE_SERIES_KEY_AMBIGUITY")
    candidate = {
        "schema": SCHEMA,
        "source": SOURCE,
        "price_basis": BASIS,
        "session": str(session),
        "source_filename": path.name,
        "raw_sha256": digest(raw),
        "csv_sha256": digest(body),
        "provenance": provenance,
        "calendar": timing,
        "calendar_sha256": digest(calendar_path.read_bytes()),
        "master_id": master.snapshot_id,
        "master_observed_at": master.observed_at.isoformat(),
        "identity_scope": "DATED_CURRENT_MASTER_MATCH_NOT_HISTORICAL_MEMBERSHIP",
        "rows": sorted(accepted, key=lambda row: row["key"]),
        "exclusions": exclusions,
        "exclusion_counts": dict(Counter(row["reason"] for row in exclusions)),
        "rights_verified": False,
        "import_approved": False,
        "provider_requests": 0,
        "model_compatible": False,
        "ml_gate": "ADJUSTMENT_ACTION_AND_DOMAIN_QUALIFICATION_REQUIRED",
    }
    return {**candidate, "candidate_id": digest(encoded(candidate))}


def _candidate(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != SCHEMA
        or value.get("source") != SOURCE
        or value.get("price_basis") != BASIS
    ):
        raise ValueError("MANUAL_EOD_CANDIDATE_SCHEMA_REJECTED")
    original = {key: item for key, item in value.items() if key != "candidate_id"}
    if digest(encoded(original)) != value.get("candidate_id"):
        raise ValueError("MANUAL_EOD_CANDIDATE_CHECKSUM_REJECTED")
    if any(
        not isinstance(value.get(key), str) or re.fullmatch(r"[a-f0-9]{64}", value[key]) is None
        for key in ("candidate_id", "raw_sha256", "csv_sha256")
    ):
        raise ValueError("MANUAL_EOD_CANDIDATE_SOURCE_ID_REJECTED")
    rows = value.get("rows")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("MANUAL_EOD_CANDIDATE_ROWS_REJECTED")
    if len({row["key"] for row in rows}) != len(rows):
        raise ValueError("MANUAL_EOD_MULTIPLE_SERIES_KEY_AMBIGUITY")


def load(root: Path) -> list[dict[str, Any]]:
    """Read accepted imports with exact source provenance; no implicit model bridge."""
    _safe_destination(root)
    _safe_destination(root / "imports")
    _safe_destination(root / "raw")
    slots: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((root / "imports").glob("*.json")):
        _safe_destination(path)
        receipt = engine._read(path)
        candidate = receipt["candidate"]
        _candidate(candidate)
        raw = checked_file(root / "raw" / (candidate["raw_sha256"] + ".bin"), MAX_UNCOMPRESSED)
        if digest(raw) != candidate["raw_sha256"]:
            raise ValueError("MANUAL_EOD_RETAINED_SOURCE_CHECKSUM_REJECTED")
        for row in candidate["rows"]:
            slot = row["key"], row["session"]
            if slot in slots and slots[slot] != row:
                raise ValueError("MANUAL_EOD_SOURCE_SLOT_CONFLICT")
            slots[slot] = row
    return sorted(slots.values(), key=lambda row: (row["key"], row["session"]))


def import_candidate(
    root: Path,
    source_path: Path,
    candidate: dict[str, Any],
    approval: dict[str, Any],
    *,
    approved_candidate: str,
    at: datetime,
) -> dict[str, Any]:
    """Explicit CLI mutation, restricted to the exact reviewed raw-source namespace."""
    _candidate(candidate)
    _safe_destination(root)
    for name in ("imports", "raw", "control", "control/worker.lock"):
        _safe_destination(root / name)
    if (
        approved_candidate != candidate["candidate_id"]
        or approval.get("candidate_id") != approved_candidate
        or approval.get("source") != SOURCE
        or approval.get("raw_sha256") != candidate["raw_sha256"]
        or Path(approval.get("destination", "")).absolute() != root.absolute()
        or approval.get("session") != candidate["session"]
        or approval.get("instrument_keys") != [row["key"] for row in candidate["rows"]]
        or approval.get("mutation_scope")
        != "APPEND_NSE_MANUAL_EOD_SOURCE_ONLY_NO_MODEL_OR_PROVIDER_MUTATION"
        or not isinstance(approval.get("operator_approval_reference"), str)
        or not approval["operator_approval_reference"].strip()
        or approval.get("rights_scope") != "PRIVATE_RETENTION_AND_RESEARCH_OF_THIS_EXACT_NSE_SOURCE"
        or not _at(approval.get("approved_at")) <= at < _at(approval.get("expires_at"))
    ):
        raise ValueError("MANUAL_EOD_EXACT_OPERATOR_SCOPE_APPROVAL_REQUIRED")
    for name in ("rights_evidence", "publication_evidence"):
        evidence = approval.get(name, {})
        if (
            not isinstance(evidence, dict)
            or not isinstance(evidence.get("path"), str)
            or digest(checked_file(Path(evidence["path"]), MAX_COMPRESSED))
            != evidence.get("sha256")
        ):
            raise ValueError("MANUAL_EOD_HASH_BOUND_RIGHTS_AND_PUBLICATION_REQUIRED")
    raw, body, session = _csv(source_path)
    if (
        source_path.name != candidate["source_filename"]
        or str(session) != candidate["session"]
        or digest(raw) != candidate["raw_sha256"]
        or digest(body) != candidate["csv_sha256"]
    ):
        raise ValueError("MANUAL_EOD_REVIEWED_SOURCE_CHANGED")
    parsed, _ = _rows(body, session)
    parsed_by_key = {row["key"]: row for row in parsed}
    for row in candidate["rows"]:
        original = parsed_by_key.get(row["key"])
        if original is None or any(row.get(key) != value for key, value in original.items()):
            raise ValueError("MANUAL_EOD_NORMALIZED_SOURCE_MISMATCH")
    initialize(root)
    with Store(root / "control").lock():
        # Read existing records before any publication. A changed price requires a
        # separately reviewed revision, never overwrite or source priority rules.
        existing = {(row["key"], row["session"]): row for row in load(root)}
        for row in candidate["rows"]:
            prior = existing.get((row["key"], row["session"]))
            if prior is not None and prior != row:
                raise ValueError("MANUAL_EOD_SOURCE_SLOT_CONFLICT")
        imports, raws = root / "imports", root / "raw"
        imports.mkdir(exist_ok=True)
        raws.mkdir(exist_ok=True)
        target = imports / (approved_candidate + ".json")
        _safe_destination(target)
        _safe_destination(target.with_suffix(".json.sha256"))
        if target.exists():
            receipt = engine._read(target)
            if receipt["candidate"] != candidate:
                raise ValueError("MANUAL_EOD_REPLAY_CONFLICT")
            return {"state": "REPLAYED", "import_id": approved_candidate, "new_observations": 0}
        raw_path = raws / (candidate["raw_sha256"] + ".bin")
        _safe_destination(raw_path)
        if raw_path.exists():
            if raw_path.read_bytes() != raw:
                raise ValueError("MANUAL_EOD_RAW_HASH_CONFLICT")
        else:
            _publish(raw_path, raw)
        receipt = {
            "candidate": candidate,
            "approval": approval,
            "imported_at": at.isoformat(),
            "new_observations": sum(
                (row["key"], row["session"]) not in existing for row in candidate["rows"]
            ),
            "state": "ACCEPTED_SOURCE_ONLY",
            "model_compatible": False,
        }
        _publish_receipt(target, receipt)
        return {
            "state": receipt["state"],
            "import_id": approved_candidate,
            "new_observations": receipt["new_observations"],
            "model_compatible": False,
        }
