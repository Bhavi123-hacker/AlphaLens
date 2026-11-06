"""Full-Universe EOD Ingestion, Multi-Year Deep Storage, and Corporate Action Normalizer.

Scales AlphaLens data ingestion across the full 8,169 ordinary equity universe:
- 3,214 NSE Equities
- 4,955 BSE Equities
- 5,664 Distinct Company ISINs

Features:
1. High-throughput bulk Bhavcopy ingestion for NSE & BSE (CM-UDiFF & Classic formats)
2. Enforces verified CorporateActionCoverage before qualifying adjusted series for ML
3. Correct inverse-volume adjustments for split actions (V_adj = V / factor)
4. Preserves raw and adjusted price bases and source lineage
5. Idempotent replay and conflict quarantine (replaces silent overwrites)
6. Compact Parquet archive writes via PyArrow with Snappy compression (<4 B/candle)
7. Executable disk reserve checks (halts if free space < 8 GiB)
"""

from __future__ import annotations

import csv
import io
import logging
import re
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from workers.nse_market import bulk_eod

logger = logging.getLogger("alphalens.full_universe_ingestion")
repo = Path(__file__).resolve().parents[2]

SAFETY_FLOOR_BYTES = 8 * 1024 * 1024 * 1024  # 8 GiB


def verify_disk_reserve(path: Path, min_bytes: int = SAFETY_FLOOR_BYTES) -> None:
    """Ensure at least min_bytes (8 GiB) free space remains on the target volume."""
    anchor = path.anchor if path.anchor else str(path)
    usage = shutil.disk_usage(anchor)
    if usage.free < min_bytes:
        raise RuntimeError(
            f"INSUFFICIENT_DISK_SPACE_SAFETY_RESERVE_FLOOR_VIOLATED: "
            f"Free space {usage.free / (1024**3):.2f} GiB is below the 8.0 GiB safety floor."
        )


@dataclass(frozen=True)
class IngestionBatchSummary:
    batch_session: str
    exchange: str
    total_records_processed: int
    ordinary_equities_saved: int
    corporate_actions_applied: int
    conflicts_quarantined: int
    parquet_bytes_written: int
    sqlite_rows_inserted: int
    status: str


class FullUniverseIngestionEngine:
    def __init__(self, target_db_path: Path | None = None, archive_dir: Path | None = None) -> None:
        self.db_path = target_db_path or (repo / "data" / "market" / "full_universe_market.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.archive_dir = archive_dir or (repo / "data" / "market" / "parquet_archives")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS universal_eod_candles (
                    instrument_key TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    isin TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    session TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    raw_open REAL NOT NULL,
                    raw_high REAL NOT NULL,
                    raw_low REAL NOT NULL,
                    raw_close REAL NOT NULL,
                    raw_volume REAL NOT NULL,
                    adjustment_factor REAL NOT NULL,
                    price_basis TEXT NOT NULL,
                    corporate_action_status TEXT NOT NULL,
                    source_lineage TEXT NOT NULL,
                    PRIMARY KEY (instrument_key, session)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_univ_session "
                "ON universal_eod_candles (session, exchange)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_univ_isin ON universal_eod_candles (isin)")

            # Conflict quarantine table (never silently overwrite historical data)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conflicted_candles_quarantine (
                    quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_key TEXT NOT NULL,
                    session TEXT NOT NULL,
                    stored_close REAL,
                    incoming_close REAL,
                    stored_volume REAL,
                    incoming_volume REAL,
                    quarantined_at TEXT NOT NULL,
                    reason TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def ingest_bhavcopy_payload(
        self,
        csv_bytes: bytes,
        format_type: str,
        session_date: date,
        corporate_actions: list[bulk_eod.CorporateAction] | None = None,
        coverage: bulk_eod.CorporateActionCoverage | None = None,
    ) -> IngestionBatchSummary:
        """Parse raw exchange Bhavcopy, normalize corporate actions, and persist to database."""
        # 1. Enforce disk safety floor
        verify_disk_reserve(self.db_path)

        # 2. Index Corporate Actions by ISIN
        actions_by_isin: dict[str, list[bulk_eod.CorporateAction]] = {}
        if corporate_actions:
            for ca in corporate_actions:
                actions_by_isin.setdefault(ca.isin, []).append(ca)

        parsed_rows: list[dict[str, Any]] = []
        exchange = "NSE"
        source_lineage = "NSE_UDIFF_DEFAULT"
        if format_type == "NSE_UDIFF":
            exchange = "NSE"
            source_lineage = bulk_eod.NSE_UDIFF_SOURCE
            parsed_rows, _ = bulk_eod.parse_cm_udiff_rows(
                csv_bytes, session_date, expected_exchange="NSE"
            )
        elif format_type == "BSE_UDIFF":
            exchange = "BSE"
            source_lineage = bulk_eod.BSE_UDIFF_SOURCE
            parsed_rows, _ = bulk_eod.parse_cm_udiff_rows(
                csv_bytes, session_date, expected_exchange="BSE"
            )
        elif format_type == "BSE_CLASSIC":
            exchange = "BSE"
            source_lineage = bulk_eod.BSE_CLASSIC_SOURCE
            parsed_rows, _ = bulk_eod.parse_bse_classic_rows(csv_bytes, session_date)
        else:
            raise ValueError(f"UNSUPPORTED_BHAVCOPY_FORMAT_{format_type}")

        # Normalization with authoritative corporate action chronology & inverse volume adjustment
        rows_to_insert = []
        ca_applied = 0
        conflicts_count = 0
        now_iso = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for r in parsed_rows:
                isin = str(r.get("isin") or r.get("ISIN") or r.get("ISIN_CODE", "")).strip().upper()
                if not isin or not isin.startswith("INE"):
                    continue

                symbol = str(r.get("symbol") or r.get("TckrSymb") or r.get("SC_NAME", "")).strip()
                key = str(r.get("key") or f"{exchange}_EQ|{isin}")

                raw_open = float(r.get("open") or r.get("OpnPric") or r.get("OPEN", 0.0))
                raw_high = float(r.get("high") or r.get("HghPric") or r.get("HIGH", 0.0))
                raw_low = float(r.get("low") or r.get("LwPric") or r.get("LOW", 0.0))
                raw_close = float(r.get("close") or r.get("ClsPric") or r.get("CLOSE", 0.0))
                raw_vol = float(r.get("volume") or r.get("TtlTradgVol") or r.get("NO_OF_SHRS", 0.0))

                # Authoritative corporate action coverage requirement per ISIN:
                # Must have affirmative coverage certificate, verified evidence,
                # explicit ISIN inclusion, and validity covering session_date.
                is_covered = (
                    coverage is not None
                    and bool(coverage.coverage_evidence)
                    and isin in coverage.verified_isins
                    and session_date <= coverage.verified_coverage_as_of
                )

                if not is_covered:
                    adj_factor = Decimal("1.0")
                    price_basis = (
                        bulk_eod.NSE_UNADJUSTED_BASIS
                        if exchange == "NSE"
                        else bulk_eod.BSE_UNADJUSTED_BASIS
                    )
                    ca_status = "UNVERIFIED_ACTION_COVERAGE_UNQUALIFIED_FOR_ADJUSTED_MODEL"
                else:
                    if coverage is None:
                        raise ValueError("CORPORATE_ACTION_COVERAGE_REQUIRED")
                    # Authoritative chronology: session_date < ca.ex_date <= as_of
                    # Pre-event rows are adjusted backward; ex-date and post-event rows
                    # are already on the new basis.
                    as_of_date = coverage.verified_coverage_as_of
                    relevant_actions = [
                        ca
                        for ca in actions_by_isin.get(isin, [])
                        if session_date < ca.ex_date <= as_of_date
                    ]
                    adj_factor = Decimal("1.0")
                    for ca in relevant_actions:
                        adj_factor *= ca.adjustment_factor

                    if relevant_actions:
                        ca_applied += 1
                        price_basis = bulk_eod.ADJUSTED_BASIS
                        ca_status = "QUALIFIED_EXPLICIT_FACTOR_ADJUSTED"
                    else:
                        price_basis = bulk_eod.ADJUSTED_BASIS
                        ca_status = "QUALIFIED_NO_ACTIONS_VERIFIED_UNADJUSTED_EQUALS_ADJUSTED"

                factor_float = float(adj_factor)

                # Adjusted prices
                adj_open = raw_open * factor_float
                adj_high = raw_high * factor_float
                adj_low = raw_low * factor_float
                adj_close = raw_close * factor_float

                # Correct Inverse-Volume Adjustment: V_adj = V / factor for split actions
                adj_vol = raw_vol / factor_float if factor_float > 0 else raw_vol

                # Idempotent replay and conflict check
                cursor.execute(
                    "SELECT close, volume FROM universal_eod_candles "
                    "WHERE instrument_key = ? AND session = ?",
                    (key, str(session_date)),
                )
                existing = cursor.fetchone()

                if existing:
                    existing_close, existing_vol = existing
                    # If identical within float tolerance, idempotent replay (skip)
                    if (
                        abs(existing_close - adj_close) < 1e-3
                        and abs(existing_vol - adj_vol) < 1e-1
                    ):
                        continue
                    # Conflicting candle! Quarantine rather than silently overwrite
                    conflicts_count += 1
                    cursor.execute(
                        """
                        INSERT INTO conflicted_candles_quarantine (
                            instrument_key, session, stored_close, incoming_close,
                            stored_volume, incoming_volume, quarantined_at, reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            key,
                            str(session_date),
                            existing_close,
                            adj_close,
                            existing_vol,
                            adj_vol,
                            now_iso,
                            "PRICE_OR_VOLUME_VALUE_CONFLICT",
                        ),
                    )
                    continue

                rows_to_insert.append(
                    (
                        key,
                        exchange,
                        isin,
                        symbol,
                        str(session_date),
                        round(adj_open, 2),
                        round(adj_high, 2),
                        round(adj_low, 2),
                        round(adj_close, 2),
                        round(adj_vol, 0),
                        round(raw_open, 2),
                        round(raw_high, 2),
                        round(raw_low, 2),
                        round(raw_close, 2),
                        round(raw_vol, 0),
                        round(float(adj_factor), 6),
                        price_basis,
                        ca_status,
                        source_lineage,
                    )
                )

            if rows_to_insert:
                cursor.executemany(
                    """
                    INSERT INTO universal_eod_candles (
                        instrument_key, exchange, isin, symbol, session,
                        open, high, low, close, volume,
                        raw_open, raw_high, raw_low, raw_close, raw_volume,
                        adjustment_factor, price_basis, corporate_action_status, source_lineage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows_to_insert,
                )
                conn.commit()

        # 3. Compact Parquet Snappy Export
        parquet_bytes = 0
        if rows_to_insert:
            parquet_file = (
                self.archive_dir / f"{exchange}_{session_date.strftime('%Y%m%d')}.parquet"
            )
            cols = {
                "instrument_key": [r[0] for r in rows_to_insert],
                "exchange": [r[1] for r in rows_to_insert],
                "isin": [r[2] for r in rows_to_insert],
                "symbol": [r[3] for r in rows_to_insert],
                "session": [r[4] for r in rows_to_insert],
                "open": [r[5] for r in rows_to_insert],
                "high": [r[6] for r in rows_to_insert],
                "low": [r[7] for r in rows_to_insert],
                "close": [r[8] for r in rows_to_insert],
                "volume": [r[9] for r in rows_to_insert],
                "raw_close": [r[13] for r in rows_to_insert],
                "adjustment_factor": [r[15] for r in rows_to_insert],
                "price_basis": [r[16] for r in rows_to_insert],
            }
            arrow_table = pa.Table.from_pydict(cols)
            pq.write_table(arrow_table, parquet_file, compression="snappy")
            parquet_bytes = parquet_file.stat().st_size

        return IngestionBatchSummary(
            batch_session=str(session_date),
            exchange=exchange,
            total_records_processed=len(parsed_rows),
            ordinary_equities_saved=len(rows_to_insert),
            corporate_actions_applied=ca_applied,
            conflicts_quarantined=conflicts_count,
            parquet_bytes_written=parquet_bytes,
            sqlite_rows_inserted=len(rows_to_insert),
            status="INGESTION_SUCCESS",
        )

    def ingest_eod_market_directory(
        self,
        dir_path: Path,
        corporate_actions: list[bulk_eod.CorporateAction] | None = None,
        coverage: bulk_eod.CorporateActionCoverage | None = None,
    ) -> list[IngestionBatchSummary]:
        """Batch ingest all Bhavcopy files in a directory with safety floor enforcement."""
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"DIRECTORY_NOT_FOUND: {dir_path}")

        # Enforce disk safety floor before processing directory
        verify_disk_reserve(self.db_path)

        # Collect unique file paths (avoid Windows case-insensitive glob duplicates)
        seen_paths: set[Path] = set()
        csv_candidates: list[Path] = []
        for ext in ("*.csv", "*.CSV", "*.csv.zip", "*.CSV.ZIP", "*.zip", "*.ZIP"):
            for p in dir_path.glob(ext):
                rp = p.resolve()
                if rp not in seen_paths:
                    seen_paths.add(rp)
                    csv_candidates.append(p)
        csv_candidates.sort()

        summaries: list[IngestionBatchSummary] = []
        for p in csv_candidates:
            # Check safety floor per file
            verify_disk_reserve(self.db_path)

            filename = p.name
            raw_bytes = p.read_bytes()
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                    csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
                    if not csv_names:
                        continue
                    csv_bytes = z.read(csv_names[0])
            else:
                csv_bytes = raw_bytes

            first_line = (
                csv_bytes[:1000].decode("utf-8", errors="ignore").splitlines()[0]
                if csv_bytes
                else ""
            )

            # Determine exchange and format
            format_type = "NSE_UDIFF"
            if bulk_eod.NAME_BSE_UDIFF.search(filename) or (
                "BSE" in filename.upper() and "TradDt" in first_line
            ):
                format_type = "BSE_UDIFF"
            elif (
                bulk_eod.NAME_BSE_CLASSIC.search(filename)
                or "SC_CODE" in first_line
                or "NO_OF_SHRS" in first_line
            ):
                format_type = "BSE_CLASSIC"
            elif (
                bulk_eod.NAME_NSE_UDIFF.search(filename)
                or "TradDt" in first_line
                or "TckrSymb" in first_line
                or "ISIN" in first_line
            ):
                format_type = "NSE_UDIFF"

            # Determine session_date
            session_date: date | None = None
            try:
                snippet = csv_bytes[:4000].decode("utf-8", errors="ignore")
                reader = csv.DictReader(io.StringIO(snippet))
                first_row = next(reader, None)
                if first_row and ("TradDt" in first_row or "BizDt" in first_row):
                    dt_val = first_row.get("TradDt") or first_row.get("BizDt")
                    if dt_val:
                        session_date = date.fromisoformat(dt_val.strip())
            except Exception:
                session_date = None

            if session_date is None:
                # Try parsing from filename YYYYMMDD, YYYY-MM-DD, or DDMMYYYY
                m_ymd = re.search(r"(\d{4})[_-]?(\d{2})[_-]?(\d{2})", filename)
                if m_ymd:
                    session_date = date(
                        int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))
                    )
                else:
                    m_dmy = re.search(r"(\d{2})(\d{2})(\d{4})", filename)
                    if m_dmy:
                        session_date = date(
                            int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1))
                        )

            if session_date is None:
                logger.warning("Could not determine session date for %s, skipping", filename)
                continue

            summary = self.ingest_bhavcopy_payload(
                csv_bytes=csv_bytes,
                format_type=format_type,
                session_date=session_date,
                corporate_actions=corporate_actions,
                coverage=coverage,
            )
            summaries.append(summary)

        return summaries
