"""Bounded, offline Mendeley CSV research-fixture adapter; never a live/PIT provider."""

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from alphalens_data.contracts import Contract, NonEmpty, PriceBar, Provenance
from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum

HEADER = ("", "open", "high", "low", "close", "adjclose", "volume", "ticker")
PARSER_VERSION = "mendeley.csv.v1"
NORMALIZATION_VERSION = "p1.research.v1"
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ResearchArtifact(Contract):
    repository: Literal["Mendeley Data"]
    dataset_id: NonEmpty
    doi: NonEmpty
    version: Literal[1]
    title: NonEmpty
    contributors: tuple[NonEmpty, ...]
    license: Literal["CC-BY-4.0"]
    license_url: NonEmpty
    dataset_published_date: date
    stated_purpose: str
    documented_date_coverage: None = None
    upstream_source: None = None
    research_fixture_use: Literal["ACCEPTED_WITH_RESIDUAL_RISK"]
    production_market_data_use: Literal["NOT_CLEARED"]
    source_url: NonEmpty
    download_url: str
    file_id: NonEmpty
    original_filename: NonEmpty
    symbol: NonEmpty
    acquired_at: AwareDatetime
    byte_size: Annotated[int, Field(gt=0, le=2_000_000)]
    sha256: Hash
    repository_sha256: Hash
    raw_relative_path: NonEmpty
    parsing_version: Literal["mendeley.csv.v1"]
    normalization_version: Literal["p1.research.v1"]
    acquisition_method: str
    origin: Literal["REAL_RESEARCH_FIXTURE", "TEST_ONLY"] = "REAL_RESEARCH_FIXTURE"
    currency: Literal["INR"]
    currency_basis: NonEmpty


class ResearchCatalog(Contract):
    scope: Literal["RESEARCH_FIXTURE_DATASET"]
    start_session: date
    end_session: date
    artifacts: Annotated[tuple[ResearchArtifact, ...], Field(min_length=1, max_length=20)]


class ResearchRow(Contract):
    bar: PriceBar
    symbol: NonEmpty
    dataset_doi: NonEmpty
    dataset_version: Literal[1]
    license: Literal["CC-BY-4.0"]
    contributors: tuple[NonEmpty, ...]
    raw_artifact_ref: NonEmpty
    raw_sha256: Hash
    raw_row_number: Annotated[int, Field(ge=2)]
    source_row_sha256: Hash
    source_fields: tuple[str, ...]
    price_basis: Literal["UNKNOWN"] = "UNKNOWN"
    scope: Literal["RESEARCH_FIXTURE_DATASET"] = "RESEARCH_FIXTURE_DATASET"


class UnavailableRow(Contract):
    raw_row_number: int
    session_date: date
    missing_fields: tuple[str, ...]
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"


@dataclass(frozen=True)
class ParsedSample:
    rows: tuple[ResearchRow, ...]
    unavailable: tuple[UnavailableRow, ...]
    source_row_count: int
    selected_row_count: int
    first_source_date: date
    last_source_date: date
    input_ordered: bool
    observed_dates: tuple[date, ...]


def read_artifact(root: Path, artifact: ResearchArtifact) -> bytes:
    path = (root / artifact.raw_relative_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise DataContractError("ARTIFACT_PATH_ESCAPES_ROOT")
    payload = path.read_bytes()
    if (
        len(payload) != artifact.byte_size
        or checksum(payload) != artifact.sha256
        or artifact.sha256 != artifact.repository_sha256
    ):
        raise DataContractError("RAW_ARTIFACT_CHECKSUM_OR_SIZE_MISMATCH")
    return payload


def source_row_bytes(fields: tuple[str, ...]) -> bytes:
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _session(value: str) -> date:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DataContractError("MALFORMED_SESSION_DATE") from exc


def _number(value: str) -> Decimal:
    try:
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
            raise InvalidOperation
        number = Decimal(value)
        if not number.is_finite():
            raise InvalidOperation
        return number
    except InvalidOperation as exc:
        raise DataContractError("MALFORMED_NUMERIC_VALUE") from exc


def parse_sample(
    payload: bytes, artifact: ResearchArtifact, start: date, end: date
) -> ParsedSample:
    """Validate bounded rows; enumerate explicit missing rows without filling them.

    Dates are scanned across the file to select/describe coverage. Financial values
    outside the requested window are not normalized or certified. Duplicate sessions
    fail closed. Missing required values produce an explicit unavailable observation.
    """
    if start > end or (end - start).days > 120:
        raise DataContractError("INVALID_OR_UNBOUNDED_RESEARCH_WINDOW")
    if len(payload) != artifact.byte_size or checksum(payload) != artifact.sha256:
        raise DataContractError("RAW_ARTIFACT_CHECKSUM_OR_SIZE_MISMATCH")
    reader = csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True)
    if tuple(next(reader, ())) != HEADER:
        raise DataContractError("UNRECOGNIZED_MENDELEY_CSV_HEADER")
    dates: list[date] = []
    observed: list[date] = []
    seen: set[date] = set()
    rows: list[ResearchRow] = []
    unavailable: list[UnavailableRow] = []
    for source in reader:
        line = reader.line_num
        fields = tuple(source)
        if len(fields) != len(HEADER):
            raise DataContractError("MALFORMED_CSV_ROW")
        session = _session(fields[0])
        dates.append(session)
        if not start <= session <= end:
            continue
        if session in seen:
            raise DataContractError("DUPLICATE_SECURITY_SESSION")
        seen.add(session)
        observed.append(session)
        if fields[7] != artifact.symbol:
            raise DataContractError("SOURCE_SYMBOL_MISMATCH")
        required = (1, 2, 3, 4, 6)
        missing = tuple(HEADER[i] for i in required if not fields[i].strip())
        if missing:
            unavailable.append(
                UnavailableRow(raw_row_number=line, session_date=session, missing_fields=missing)
            )
            continue
        numbers = [_number(fields[i]) for i in required]
        volume = numbers[-1]
        if volume < 0 or volume != volume.to_integral_value():
            raise DataContractError("INVALID_VOLUME")
        # adjclose is retained verbatim but cannot be promoted without methodology.
        if fields[5] and _number(fields[5]) <= 0:
            raise DataContractError("INVALID_SOURCE_ADJUSTED_CLOSE")
        provenance = Provenance(
            source_id="mendeley_research_fixture",
            source_record_id=f"{artifact.doi}:{artifact.file_id}:row:{line}",
            revision_id=f"{artifact.doi}:sha256:{artifact.sha256}",
            ingested_at=artifact.acquired_at,
            origin=artifact.origin,
            schema_version="p1.v2",
        )
        bar = PriceBar(
            security_id=f"mendeley:{artifact.dataset_id}:v{artifact.version}:{artifact.symbol}",
            currency=artifact.currency,
            provenance=provenance,
            session_date=session,
            session_close_at=None,
            open=numbers[0],
            high=numbers[1],
            low=numbers[2],
            close=numbers[3],
            volume=int(volume),
        )
        rows.append(
            ResearchRow(
                bar=bar,
                symbol=artifact.symbol,
                dataset_doi=artifact.doi,
                dataset_version=artifact.version,
                license=artifact.license,
                contributors=artifact.contributors,
                raw_artifact_ref=artifact.raw_relative_path,
                raw_sha256=artifact.sha256,
                raw_row_number=line,
                source_row_sha256=checksum(source_row_bytes(fields)),
                source_fields=fields,
            )
        )
    if not dates or not observed or not rows:
        raise DataContractError("EMPTY_RESEARCH_SAMPLE")
    return ParsedSample(
        rows=tuple(sorted(rows, key=lambda row: row.bar.session_date)),
        unavailable=tuple(sorted(unavailable, key=lambda row: row.session_date)),
        source_row_count=len(dates),
        selected_row_count=len(observed),
        first_source_date=min(dates),
        last_source_date=max(dates),
        input_ordered=observed == sorted(observed),
        observed_dates=tuple(sorted(observed)),
    )


def research_bytes(rows: tuple[ResearchRow, ...]) -> bytes:
    ordered = sorted(rows, key=lambda row: (row.bar.security_id, row.bar.session_date))
    keys = [(row.bar.security_id, row.bar.session_date) for row in ordered]
    if len(keys) != len(set(keys)):
        raise DataContractError("DUPLICATE_SECURITY_SESSION")
    return json.dumps(
        [row.model_dump(mode="json") for row in ordered],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
