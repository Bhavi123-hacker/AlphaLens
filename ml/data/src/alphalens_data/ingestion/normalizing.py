"""Strict decimal normalization and row accounting; invalid evidence is quarantined."""

import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from alphalens_data.ingestion.contracts import CanonicalEOD, QuarantineRecord, RawManifest
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum


def decimal_value(value: str) -> Decimal:
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        raise ValueError("Expected a finite decimal with no separators")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("Malformed decimal") from None
    if not number.is_finite():
        raise ValueError("Non-finite decimal")
    # Exact decimal128(38,18) output; reject rather than round/truncate.
    _, digits, exponent = number.as_tuple()
    if not isinstance(exponent, int) or exponent < -18 or len(digits) + exponent > 20:
        raise ValueError("Decimal exceeds exact canonical storage precision")
    if number <= 0:
        raise ValueError("OHLC price must be positive")
    return number


def normalize(
    rows: tuple[ParsedRow, ...], manifest: RawManifest
) -> tuple[tuple[CanonicalEOD, ...], tuple[QuarantineRecord, ...]]:
    accepted: list[CanonicalEOD] = []
    errors: list[QuarantineRecord] = []
    identified: dict[int, tuple[str, date, str]] = {}

    def reject(row: ParsedRow, rule: str, reason: str) -> None:
        errors.append(
            QuarantineRecord(
                artifact_id=manifest.artifact_id,
                raw_sha256=manifest.sha256,
                versions=manifest.versions,
                classification=manifest.spec.classification,
                source_row_number=row.row_number,
                original_row=row.original,
                validation_rule=rule,
                reason=reason,
                timestamp=manifest.acquired_at,
            )
        )

    for row in rows:
        if row.error:
            reject(row, row.error, "Parser rejected the source row; raw bytes remain preserved")
            continue
        fields = dict(row.fields)
        required = {"session_date", "open", "high", "low", "close", "volume"}
        if len(fields) != len(row.fields) or not required.issubset(fields):
            reject(
                row, "REQUIRED_FIELDS", "Parser must supply unique canonical minimum field names"
            )
            continue
        # Whitespace in required values is malformed, not silently stripped.
        security = fields.get("security_id") or fields.get("symbol")
        if not security or security != security.strip():
            reject(row, "REQUIRED_IDENTIFIER", "Non-empty, unpadded security_id or symbol required")
            continue
        series = fields.get("series") or None
        identifier_names = {"security_id", "symbol", "isin", "series", "source_row_identifier"}
        if any(
            value and (value != value.strip() or len(value) > 256)
            for name, value in fields.items()
            if name in identifier_names
        ):
            reject(
                row, "IDENTIFIER_FORMAT", "Identifiers must be unpadded and at most 256 characters"
            )
            continue
        security_id = (
            security
            if fields.get("security_id")
            else (
                f"{manifest.spec.source}:symbol:{quote(security, safe='')}:"
                f"{quote(series or '', safe='')}"
            )
        )
        try:
            value = fields["session_date"]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            session = date.fromisoformat(value)
        except ValueError:
            reject(row, "SESSION_DATE", "Expected a real calendar date in YYYY-MM-DD format")
            continue
        if session > manifest.acquired_at.date():
            reject(row, "SESSION_AFTER_ACQUISITION", "Completed EOD session is in the future")
            continue
        if len(security_id) > 256:
            reject(row, "IDENTIFIER_FORMAT", "Source-scoped identifier exceeds schema length")
            continue
        identified[row.row_number] = (security_id, session, manifest.artifact_id)
        values: dict[str, Decimal] = {}
        for name in ("open", "high", "low", "close"):
            try:
                values[name] = decimal_value(fields[name])
            except ValueError as exc:
                reject(row, "NUMERIC_" + name.upper(), str(exc))
        try:
            if not re.fullmatch(r"[+-]?\d+", fields["volume"]):
                raise ValueError("Volume must be an integer")
            volume = int(fields["volume"])
            if not 0 <= volume <= 2**63 - 1:
                raise ValueError("Volume must be non-negative and fit int64")
        except ValueError as exc:
            reject(row, "VOLUME", str(exc))
            continue
        if len(values) != 4:
            continue
        failed = False
        for lhs, operator, rhs in (
            ("high", ">=", "open"),
            ("high", ">=", "close"),
            ("high", ">=", "low"),
            ("low", "<=", "open"),
            ("low", "<=", "close"),
        ):
            valid = values[lhs] >= values[rhs] if operator == ">=" else values[lhs] <= values[rhs]
            if not valid:
                reject(row, f"OHLC_{lhs.upper()}_{rhs.upper()}", f"Required {lhs} {operator} {rhs}")
                failed = True
        if failed:
            continue
        row_hash = checksum(stable_json(row.original))
        normalized_id = checksum(
            stable_json(
                [
                    manifest.artifact_id,
                    row.row_number,
                    row_hash,
                    manifest.versions.model_dump(),
                ]
            )
        )
        accepted.append(
            CanonicalEOD(
                record_id=checksum(stable_json([normalized_id, "canonical"])),
                normalized_record_id=normalized_id,
                artifact_id=manifest.artifact_id,
                raw_sha256=manifest.sha256,
                source=manifest.spec.source,
                source_version=manifest.artifact_id,
                versions=manifest.versions,
                classification=manifest.spec.classification,
                security_id=security_id,
                identity_basis="SOURCE_SECURITY_ID"
                if fields.get("security_id")
                else "SOURCE_SCOPED_SYMBOL",
                symbol=fields.get("symbol") or None,
                isin=fields.get("isin") or None,
                series=series,
                source_row_identifier=fields.get("source_row_identifier") or str(row.row_number),
                source_filename=manifest.spec.original_filename,
                source_row_number=row.row_number,
                source_row_sha256=row_hash,
                session_date=session,
                open=values["open"],
                high=values["high"],
                low=values["low"],
                close=values["close"],
                volume=volume,
                currency=manifest.spec.currency,
                acquired_at=manifest.acquired_at,
            )
        )
    counts = Counter(identified.values())
    original_by_number = {r.row_number: r for r in rows}
    canonical: list[CanonicalEOD] = []
    for row_number, key in identified.items():
        if counts[key] > 1:
            reject(
                original_by_number[row_number],
                "DUPLICATE_SECURITY_SESSION_VERSION",
                "All members of an ambiguous duplicate group are quarantined",
            )
    for record in accepted:
        if counts[(record.security_id, record.session_date, record.source_version)] == 1:
            canonical.append(record)
    canonical.sort(key=lambda r: (r.security_id, r.session_date, r.source_row_number))
    errors.sort(key=lambda r: (r.source_row_number, r.validation_rule))
    return tuple(canonical), tuple(errors)
