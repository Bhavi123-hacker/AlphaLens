"""Bulk EOD market data ingestion adapters and corporate-action aware normalization.

Supports:
1. NSE CM-UDiFF Bhavcopy (CSV/ZIP)
2. BSE CM-UDiFF Bhavcopy (CSV/ZIP)
3. BSE Classic Equity Bhavcopy (CSV/ZIP)

Provides explicit corporate-action normalization to safely bridge raw exchange-reported
unadjusted prices (NSE/BSE Bhavcopies) with split/bonus-adjusted price series required
by ML feature extraction, enforcing domain isolation (BSE domain validation required).
"""

from __future__ import annotations

import csv
import io
import re
import stat
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from workers.providers import universe

# Provenance Sources
NSE_UDIFF_SOURCE = "NSE_CM_UDIFF_FINAL_OPERATOR_DOWNLOAD"
BSE_UDIFF_SOURCE = "BSE_CM_UDIFF_FINAL_OPERATOR_DOWNLOAD"
BSE_CLASSIC_SOURCE = "BSE_EQUITY_BHAVCOPY_FINAL_OPERATOR_DOWNLOAD"

# Price Bases
NSE_UNADJUSTED_BASIS = "NSE_EXCHANGE_REPORTED_UNADJUSTED_EOD"
BSE_UNADJUSTED_BASIS = "BSE_EXCHANGE_REPORTED_UNADJUSTED_EOD"
ADJUSTED_BASIS = "CORPORATE_ACTION_EXPLICIT_FACTOR_ADJUSTED_EOD"

# Schemas
SCHEMA_V1 = "alphalens.bulk_eod.v1"

# Bounded File Limits
MAX_COMPRESSED = 8_000_000
MAX_UNCOMPRESSED = 64_000_000
MAX_ROWS = 100_000

# Regular Expressions
NAME_NSE_UDIFF = re.compile(r"BhavCopy_NSE_CM_0_0_0_([0-9]{8})_F_0000\.csv(?:\.zip)?\Z")
NAME_BSE_UDIFF = re.compile(r"BhavCopy_BSE_CM_0_0_0_([0-9]{8})_F_0000\.csv(?:\.zip)?\Z")
NAME_BSE_CLASSIC = re.compile(r"(?:EQ_ISINCODE_|EQ)([0-9]{6})\.CSV(?:\.ZIP)?\Z", re.IGNORECASE)
NUMBER = re.compile(r"[0-9]{1,19}(?:\.[0-9]{1,6})?\Z")

# Column Headers
UDIFF_HEADERS = (
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

BSE_CLASSIC_HEADERS = (
    "SC_CODE",
    "SC_NAME",
    "SC_GROUP",
    "SC_TYPE",
    "OPEN",
    "HIGH",
    "LOW",
    "CLOSE",
    "LAST",
    "PREVCLOSE",
    "NO_TRADES",
    "NO_OF_SHRS",
    "NET_TURNOV",
    "TDCLOIF",
    "IND_SEC",
    "ISIN_CODE",
)

# Ordinary Equity BSE Groups
COMMON_BSE_GROUPS = frozenset({"A", "B", "T", "X", "XT", "M", "MT", "Z", "ZP", "P", "TS", "MS"})


@dataclass(frozen=True)
class CorporateAction:
    isin: str
    ex_date: date
    action_type: str  # "SPLIT", "BONUS", "RIGHTS"
    ratio_from: Decimal
    ratio_to: Decimal
    adjustment_factor: Decimal


@dataclass(frozen=True)
class CorporateActionCoverage:
    """Explicit cryptographic and calendar proof of verified corporate action records.

    An empty action list alone does not establish no-action status unless coverage
    is affirmatively verified for the target ISINs up to the evaluation date.
    """

    verified_coverage_as_of: date
    verified_isins: frozenset[str]
    coverage_evidence: str
    coverage_sha256: str


def _safe_destination(path: Path) -> None:
    for item in (path.absolute(), *path.absolute().parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("BULK_EOD_REPARSE_PATH_REJECTED")


def checked_file(path: Path, maximum: int) -> bytes:
    path = path.absolute()
    _safe_destination(path)
    if not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError("BULK_EOD_FILE_SIZE_REJECTED")
    body = path.read_bytes()
    if len(body) > maximum:
        raise ValueError("BULK_EOD_FILE_SIZE_REJECTED")
    return body


def _at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("BULK_EOD_AWARE_TIMESTAMP_REQUIRED")
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("BULK_EOD_AWARE_TIMESTAMP_REQUIRED")
    return result


def _decimal(value: str, *, positive: bool = True) -> Decimal:
    if NUMBER.fullmatch(value.strip()) is None:
        raise ValueError("INVALID_DECIMAL")
    result = Decimal(value.strip())
    if not result.is_finite() or (result <= 0 if positive else result < 0):
        raise ValueError("INVALID_DECIMAL")
    return result


def extract_csv_payload(path: Path) -> tuple[bytes, bytes, date, str]:
    """Identify file type, validate name/compression, and extract raw and uncompressed CSV bytes.

    Returns:
        tuple[raw_bytes, csv_bytes, session_date, format_type]
        where format_type is one of: 'NSE_UDIFF', 'BSE_UDIFF', 'BSE_CLASSIC'
    """
    filename = path.name
    nse_match = NAME_NSE_UDIFF.fullmatch(filename)
    bse_udiff_match = NAME_BSE_UDIFF.fullmatch(filename)
    bse_classic_match = NAME_BSE_CLASSIC.fullmatch(filename)

    if nse_match:
        format_type = "NSE_UDIFF"
        session = datetime.strptime(nse_match[1], "%Y%m%d").date()
    elif bse_udiff_match:
        format_type = "BSE_UDIFF"
        session = datetime.strptime(bse_udiff_match[1], "%Y%m%d").date()
    elif bse_classic_match:
        format_type = "BSE_CLASSIC"
        # Format DDMMYY
        session = datetime.strptime(bse_classic_match[1], "%d%m%y").date()
    else:
        raise ValueError("BULK_EOD_UNRECOGNIZED_OFFICIAL_FILENAME")

    raw = checked_file(path, MAX_COMPRESSED if path.suffix.lower() == ".zip" else MAX_UNCOMPRESSED)
    if path.suffix.lower() != ".zip":
        return raw, raw, session, format_type

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) != 1:
                raise ValueError("BULK_EOD_SINGLE_CSV_REQUIRED")
            member = entries[0]
            expected_unzipped = path.name[:-4] if path.name.lower().endswith(".zip") else path.name
            if (
                member.filename.lower() != expected_unzipped.lower()
                or "/" in member.filename
                or "\\" in member.filename
                or member.is_dir()
                or member.flag_bits & 1
                or stat.S_ISLNK(member.external_attr >> 16)
                or not 0 < member.file_size <= MAX_UNCOMPRESSED
                or member.compress_size > MAX_COMPRESSED
                or member.file_size > max(1, member.compress_size) * 500
            ):
                raise ValueError("BULK_EOD_ZIP_MEMBER_REJECTED")
            with archive.open(member) as stream:
                body = stream.read(MAX_UNCOMPRESSED + 1)
            if len(body) != member.file_size or len(body) > MAX_UNCOMPRESSED:
                raise ValueError("BULK_EOD_ZIP_SIZE_REJECTED")
            return raw, body, session, format_type
    except (zipfile.BadZipFile, OSError, RuntimeError):
        raise ValueError("BULK_EOD_ZIP_INVALID") from None


def parse_bse_classic_rows(
    body: bytes, session: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse classic BSE equity Bhavcopy (SC_CODE, SC_NAME, SC_GROUP, ..., ISIN_CODE)."""
    try:
        text = body.decode("utf-8-sig")
        if "\x00" in text:
            raise ValueError("BULK_EOD_NUL_REJECTED")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if tuple(reader.fieldnames or ()) != BSE_CLASSIC_HEADERS:
            raise ValueError("BULK_EOD_BSE_CLASSIC_EXACT_SCHEMA_REQUIRED")

        accepted: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        seen: set[str] = set()

        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ValueError("BULK_EOD_ROW_LIMIT")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("BULK_EOD_CSV_WIDTH_REJECTED")

            sc_code = row["SC_CODE"].strip()
            group = row["SC_GROUP"].strip()
            isin = row["ISIN_CODE"].strip()
            name = row["SC_NAME"].strip()

            reason = None
            if group not in COMMON_BSE_GROUPS:
                reason = "UNSUPPORTED_BSE_GROUP"
            elif not universe.valid_isin(isin) or not isin.startswith("INE") or isin[7:9] != "01":
                reason = "NOT_VERIFIED_ORDINARY_EQUITY_ISIN"
            elif not sc_code.isdigit() or len(sc_code) != 6:
                reason = "INVALID_BSE_SC_CODE"

            if reason:
                exclusions.append({"line": number, "reason": reason})
                continue

            if isin in seen:
                raise ValueError("BULK_EOD_DUPLICATE_BSE_ISIN_CONFLICT")
            seen.add(isin)

            try:
                opened, high, low, close = (
                    _decimal(row[key]) for key in ("OPEN", "HIGH", "LOW", "CLOSE")
                )
                if low > min(opened, close) or high < max(opened, close) or low > high:
                    raise ValueError("INVALID_OHLC")
                volume = _decimal(row["NO_OF_SHRS"], positive=False)
                if volume != volume.to_integral_value() or volume >= 10**25:
                    raise ValueError("INVALID_VOLUME")
            except ValueError as exc:
                exclusions.append({"line": number, "reason": str(exc)})
                continue

            accepted.append(
                {
                    "key": "BSE_EQ|" + isin,
                    "symbol": name,
                    "isin": isin,
                    "exchange": "BSE",
                    "segment": "BSE_EQ",
                    "series": group,
                    "session": str(session),
                    "open": str(opened),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": int(volume),
                    "source": BSE_CLASSIC_SOURCE,
                    "price_basis": BSE_UNADJUSTED_BASIS,
                    "provider_candle_at": None,
                    "corporate_action_status": "UNQUALIFIED_FOR_ADJUSTED_MODEL",
                    "model_compatible": False,
                    "ml_gate": "BSE_DOMAIN_MODEL_NOT_VALIDATED",
                }
            )

        if not accepted:
            raise ValueError("BULK_EOD_NO_ACCEPTABLE_BSE_ROWS")
        return accepted, exclusions
    except (UnicodeError, csv.Error):
        raise ValueError("BULK_EOD_CSV_ENCODING_OR_SYNTAX_REJECTED") from None


def parse_cm_udiff_rows(
    body: bytes, session: date, *, expected_exchange: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse standardized CM UDiFF format for either NSE or BSE."""
    if expected_exchange not in {"NSE", "BSE"}:
        raise ValueError("EXPECTED_EXCHANGE_MUST_BE_NSE_OR_BSE")

    source = NSE_UDIFF_SOURCE if expected_exchange == "NSE" else BSE_UDIFF_SOURCE
    basis = NSE_UNADJUSTED_BASIS if expected_exchange == "NSE" else BSE_UNADJUSTED_BASIS

    try:
        text = body.decode("utf-8-sig")
        if "\x00" in text:
            raise ValueError("BULK_EOD_NUL_REJECTED")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if tuple(reader.fieldnames or ()) != UDIFF_HEADERS:
            raise ValueError("BULK_EOD_UDIFF_EXACT_SCHEMA_REQUIRED")

        accepted: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ValueError("BULK_EOD_ROW_LIMIT")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("BULK_EOD_CSV_WIDTH_REJECTED")
            if row["TradDt"] != str(session) or row["BizDt"] != str(session):
                raise ValueError("BULK_EOD_FILENAME_SESSION_MISMATCH")
            if row["Sgmt"] != "CM" or row["Src"] != expected_exchange:
                raise ValueError(f"BULK_EOD_{expected_exchange}_CASH_SOURCE_REQUIRED")

            isin, symbol, series = row["ISIN"], row["TckrSymb"], row["SctySrs"]
            reason = None

            if row["FinInstrmTp"] != "STK":
                reason = "UNSUPPORTED_INSTRUMENT_TYPE"
            elif expected_exchange == "NSE" and series not in universe.COMMON_SERIES:
                reason = "UNSUPPORTED_NSE_SERIES"
            elif expected_exchange == "BSE" and series not in COMMON_BSE_GROUPS:
                reason = "UNSUPPORTED_BSE_GROUP"
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
                raise ValueError("BULK_EOD_DUPLICATE_IDENTITY_SERIES_CONFLICT")
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

            segment = f"{expected_exchange}_EQ"
            accepted.append(
                {
                    "key": f"{segment}|{isin}",
                    "symbol": symbol,
                    "isin": isin,
                    "exchange": expected_exchange,
                    "segment": segment,
                    "series": series,
                    "session": str(session),
                    "open": str(opened),
                    "high": str(high),
                    "low": str(low),
                    "close": str(close),
                    "volume": int(volume),
                    "source": source,
                    "price_basis": basis,
                    "provider_candle_at": None,
                    "corporate_action_status": "UNQUALIFIED_FOR_ADJUSTED_MODEL",
                    "model_compatible": False,
                    "ml_gate": (
                        "ADJUSTMENT_ACTION_AND_DOMAIN_QUALIFICATION_REQUIRED"
                        if expected_exchange == "NSE"
                        else "BSE_DOMAIN_MODEL_NOT_VALIDATED"
                    ),
                }
            )

        if not accepted:
            raise ValueError(f"BULK_EOD_NO_ACCEPTABLE_{expected_exchange}_ROWS")
        return accepted, exclusions
    except (UnicodeError, csv.Error):
        raise ValueError("BULK_EOD_CSV_ENCODING_OR_SYNTAX_REJECTED") from None


def normalize_with_corporate_actions(
    unadjusted_rows: list[dict[str, Any]],
    corporate_actions: list[CorporateAction],
    coverage: CorporateActionCoverage | None = None,
    *,
    as_of: date,
) -> list[dict[str, Any]]:
    """Normalize raw unadjusted exchange prices using explicit corporate action adjustment factors.

    Transforms exchange unadjusted series into mathematically consistent series compatible
    with Upstox Historical V3 split/bonus adjustments.

    CRITICAL INVARIANT:
    An empty corporate action list does NOT establish absence of actions unless affirmatively
    proven by a verified CorporateActionCoverage certificate covering the target ISINs.
    If coverage is missing, unverified, or expired relative to as_of, the rows remain
    UNVERIFIED_ACTION_COVERAGE_UNQUALIFIED_FOR_ADJUSTED_MODEL and model_compatible=False.
    """
    actions_by_isin: dict[str, list[CorporateAction]] = {}
    for ca in corporate_actions:
        actions_by_isin.setdefault(ca.isin, []).append(ca)

    normalized: list[dict[str, Any]] = []
    for row in unadjusted_rows:
        isin = row["isin"]
        session = date.fromisoformat(row["session"])

        # Check explicit verified corporate action coverage
        is_covered = (
            coverage is not None
            and as_of <= coverage.verified_coverage_as_of
            and isin in coverage.verified_isins
        )

        if not is_covered:
            # Cannot assume absence of corporate actions; fail closed
            unverified_status = "UNVERIFIED_ACTION_COVERAGE_UNQUALIFIED_FOR_ADJUSTED_MODEL"
            norm_row = {
                **row,
                "raw_close": row["close"],
                "raw_volume": row["volume"],
                "adjustment_factor": "1",
                "corporate_action_status": unverified_status,
                "corporate_actions_applied": 0,
                "model_compatible": False,
                "ml_gate": "CORPORATE_ACTION_COVERAGE_NOT_VERIFIED",
            }
            normalized.append(norm_row)
            continue

        relevant_actions = [
            ca for ca in actions_by_isin.get(isin, []) if session < ca.ex_date <= as_of
        ]

        factor = Decimal("1.0")
        for ca in relevant_actions:
            factor *= ca.adjustment_factor

        opened = Decimal(row["open"]) * factor
        high = Decimal(row["high"]) * factor
        low = Decimal(row["low"]) * factor
        close = Decimal(row["close"]) * factor

        # Volume adjustment policy: inverse of price factor
        # When price splits by 10 (factor 0.1), equivalent volume is multiplied by 10
        raw_vol = Decimal(row["volume"])
        adj_vol = int(round(raw_vol / factor))

        is_nse = row["exchange"] == "NSE"
        is_nse_common = is_nse and row.get("series") in universe.COMMON_SERIES

        if len(relevant_actions) == 0:
            ca_status = "QUALIFIED_NO_ACTIONS_VERIFIED_UNADJUSTED_EQUALS_ADJUSTED"
        else:
            ca_status = "QUALIFIED_EXPLICIT_FACTOR_ADJUSTED"

        norm_row = {
            **row,
            "open": str(round(opened, 4)),
            "high": str(round(high, 4)),
            "low": str(round(low, 4)),
            "close": str(round(close, 4)),
            "volume": adj_vol,
            "raw_close": row["close"],
            "raw_volume": row["volume"],
            "adjustment_factor": str(factor.normalize()),
            "price_basis": ADJUSTED_BASIS,
            "corporate_action_status": ca_status,
            "corporate_actions_applied": len(relevant_actions),
            # BSE equities remain model_compatible=False until dedicated BSE domain model is trained
            "model_compatible": is_nse_common,
            "ml_gate": (
                "PASSED_FACTOR_ADJUSTMENT"
                if is_nse_common
                else (
                    "BSE_DOMAIN_MODEL_NOT_VALIDATED" if is_nse is False else "SERIES_INCOMPATIBLE"
                )
            ),
        }
        normalized.append(norm_row)

    return normalized


def rows_to_chart_history(
    normalized_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group normalized rows into chart-compatible OHLCV candles indexed by instrument key.

    Provides safe, offline source-to-persistence-to-chart verification without external calls.
    """
    histories: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(normalized_rows, key=lambda r: (r["key"], r["session"])):
        candle = {
            "session": row["session"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"]),
            "price_basis": row["price_basis"],
            "corporate_action_status": row.get("corporate_action_status"),
        }
        histories.setdefault(row["key"], []).append(candle)
    return histories
