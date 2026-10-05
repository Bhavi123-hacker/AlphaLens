"""Parser protocol and a documented fixture CSV adapter; no vendor assumptions."""

import csv
import io
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    original: tuple[str, ...]
    fields: tuple[tuple[str, str], ...]
    error: str | None = None


class EODParser(Protocol):
    version: str

    def parse(self, payload: bytes) -> tuple[ParsedRow, ...]: ...


class FixtureCSVParser:
    """TEST_ONLY interchange: exact named columns, UTF-8, ISO dates and decimals.

    Optional fields: security_id, symbol, isin, series, source_row_identifier.
    Additional columns stay in original rows and raw bytes, never fabricated fields.
    """

    version = "fixture.csv.v1"

    def parse(self, payload: bytes) -> tuple[ParsedRow, ...]:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            return (ParsedRow(0, (), (), "INVALID_UTF8"),)
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        result: list[ParsedRow] = []
        try:
            header = tuple(next(reader))
            required = {"session_date", "open", "high", "low", "close", "volume"}
            if (
                len(header) != len(set(header))
                or not required.issubset(header)
                or not {"symbol", "security_id"}.intersection(header)
            ):
                return (ParsedRow(1, header, (), "INVALID_HEADER"),)
            for index, row in enumerate(reader, start=2):
                original = tuple(row)
                if len(row) != len(header):
                    result.append(ParsedRow(index, original, (), "ROW_WIDTH_MISMATCH"))
                else:
                    result.append(ParsedRow(index, original, tuple(zip(header, row, strict=True))))
        except StopIteration:
            return (ParsedRow(0, (), (), "EMPTY_ARTIFACT"),)
        except csv.Error:
            # Remaining undecodable CSV stays in the immutable raw artifact.
            result.append(ParsedRow(reader.line_num, (), (), "MALFORMED_CSV"))
        return tuple(result) if result else (ParsedRow(1, header, (), "NO_DATA_ROWS"),)
