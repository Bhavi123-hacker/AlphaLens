"""Bounded native-Parquet source profile; never infer historical knowledge clocks.

Only one yearly partition's duplicate keys are retained. Original bytes and P2
manifests are verified before reading; no rows are repaired, deleted or backfilled.
"""

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq
from scripts.acquire_tejhq_research import DATASET, REVISION, digest_file

REQUIRED = {"date", "symbol", "series", "isin", "name", "open", "high", "low", "close", "volume"}
SPECIAL_SESSIONS = tuple(
    date.fromisoformat(d)
    for d in (
        "2013-11-03",
        "2016-10-30",
        "2019-10-27",
        "2020-11-14",
        "2023-11-12",
    )
)
CALENDAR_SOURCES = [
    "https://nsearchives.nseindia.com/content/circulars/ISC59313.pdf",
    "https://nsearchives.nseindia.com/web/sites/default/files/inline-files/"
    "Market%20Pulse_November%202024_FINAL_3.pdf",
]


def identity(row: dict[str, Any]) -> str:
    """A source observation key, explicitly not a reconciled permanent P4 identity."""
    return (
        f"ISIN:{row['isin']}"
        if row["isin"]
        else f"UNRESOLVED_SYMBOL:{row['symbol']}:{row['series']}"
    )


def explicit_non_equity(name: str) -> str | None:
    """Positive name evidence for exclusion only; absence never proves common equity."""
    for kind, pattern in (
        ("ETF", r"\bETF\b|EXCHANGE TRADED FUND"),
        ("REIT", r"\bREIT\b|REAL ESTATE INVESTMENT TRUST"),
        ("INVIT", r"\bINVIT\b|INFRASTRUCTURE INVESTMENT TRUST"),
        ("PREFERENCE", r"PREFERENCE|PREF SHARES"),
        ("DEBT", r"DEBENTURE|\bBONDS?\b"),
    ):
        if re.search(pattern, name.upper()):
            return kind
    return None


def profile(root: Path, output: Path) -> dict[str, Any]:
    acquisition = json.loads((root / "acquisition-manifest.json").read_bytes())
    if acquisition["dataset_id"] != DATASET or acquisition["revision"] != REVISION:
        raise ValueError("PROFILE_SOURCE_REVISION_MISMATCH")
    counts: Counter[str] = Counter()
    rows_by_year: Counter[str] = Counter()
    series: Counter[str] = Counter()
    symbols: set[str] = set()
    isins: set[str] = set()
    sessions: set[date] = set()
    securities: dict[str, dict[str, Any]] = {}
    symbol_isins: dict[str, set[str]] = defaultdict(set)
    isin_symbols: dict[str, set[str]] = defaultdict(set)
    schema_reports = []
    year_reports = []
    excluded: dict[str, set[str]] = defaultdict(set)
    latest_keys: set[str] = set()
    latest: date | None = None
    symbol_session_duplicates = 0
    special_counts: Counter[date] = Counter()
    for receipt in acquisition["files"]:
        path = root / receipt["filename"]
        if path.stat().st_size != receipt["byte_size"] or digest_file(path) != receipt["sha256"]:
            raise ValueError("PROFILE_INPUT_CHECKSUM_MISMATCH")
        source = pq.ParquetFile(path)
        if not REQUIRED.issubset(source.schema_arrow.names):
            raise ValueError("SOURCE_SCHEMA_MISSING_REQUIRED_COLUMNS")
        schema_reports.append(
            {
                "filename": receipt["filename"],
                "rows": source.metadata.num_rows,
                "row_groups": source.metadata.num_row_groups,
                "columns": {f.name: str(f.type) for f in source.schema_arrow},
                "historical_clock_columns": [
                    n
                    for n in source.schema_arrow.names
                    if n in ("published_at", "available_at", "session_close_at")
                ],
            }
        )
        declared_year = Path(receipt["filename"]).stem[4:]
        # One year and two columns only; ParquetFile avoids hive 'year' type inference.
        symbol_dates = source.read(columns=["symbol", "date"])
        grouped = symbol_dates.group_by(["symbol", "date"]).aggregate([("symbol", "count")])
        ambiguous = grouped.filter(pc.greater(grouped["symbol_count"], 1))
        symbol_session_duplicates += sum(v - 1 for v in ambiguous["symbol_count"].to_pylist())
        seen: dict[tuple[str, date], tuple[Any, ...]] = {}
        file_keys: set[str] = set()
        local: Counter[str] = Counter()
        for batch in source.iter_batches(batch_size=16384):
            for row in batch.to_pylist():
                counts["raw_rows"] += 1
                d = row["date"]
                if d is None or not isinstance(d, date):
                    counts["null_or_invalid_date"] += 1
                    continue
                rows_by_year[str(d.year)] += 1
                if str(d.year) != declared_year:
                    counts["file_year_date_mismatch"] += 1
                sessions.add(d)
                if d in SPECIAL_SESSIONS:
                    special_counts[d] += 1
                key = identity(row)
                file_keys.add(key)
                symbol = row["symbol"]
                if symbol:
                    symbols.add(symbol)
                else:
                    counts["null_or_empty_symbol"] += 1
                series[str(row["series"])] += 1
                if row["isin"]:
                    isins.add(row["isin"])
                    symbol_isins[symbol].add(row["isin"])
                    isin_symbols[row["isin"]].add(symbol)
                    counts["isin_present_rows"] += 1
                else:
                    counts["isin_missing_rows"] += 1
                if not row["name"]:
                    counts["name_missing_rows"] += 1
                kind = explicit_non_equity(row["name"] or "")
                if kind:
                    excluded[kind].add(key)
                    counts["explicit_non_equity_name_rows"] += 1
                elif row["isin"] and re.fullmatch(r"INE[A-Z0-9]{5}10[0-9]{2}", row["isin"]):
                    # Format candidate only; no authoritative type declaration is supplied.
                    counts["candidate_equity_isin_pattern_rows"] += 1
                else:
                    counts["unresolved_type_rows"] += 1
                prices = [row[n] for n in ("open", "high", "low", "close")]
                for field, value in zip(("open", "high", "low", "close"), prices, strict=True):
                    if value is None:
                        counts[f"{field}_null"] += 1
                    elif not math.isfinite(value):
                        counts[f"{field}_nonfinite"] += 1
                    elif value < 0:
                        counts[f"{field}_negative"] += 1
                    elif value == 0:
                        counts[f"{field}_zero"] += 1
                if all(v is not None and math.isfinite(v) for v in prices):
                    o, h, low, c = prices
                    if h < max(o, c, low) or low > min(o, c):
                        counts["ohlc_consistency_violations"] += 1
                    if low > 0 and h / low > 1.5:
                        counts["high_low_ratio_above_p3_threshold"] += 1
                    previous = row.get("prev_close")
                    if previous is not None and previous > 0 and abs(c / previous - 1) > 0.5:
                        counts["extreme_source_prev_close_movements"] += 1
                volume = row["volume"]
                if volume is None:
                    counts["volume_null"] += 1
                elif volume < 0:
                    counts["volume_negative"] += 1
                elif volume == 0:
                    counts["volume_zero"] += 1
                fingerprint = (symbol, row["series"], *prices, volume)
                observed_key = (key, d)
                if observed_key in seen:
                    counts["duplicate_identity_session_rows"] += 1
                    local["duplicates"] += 1
                    if fingerprint != seen[observed_key]:
                        counts["conflicting_duplicate_rows"] += 1
                        local["conflicting_duplicates"] += 1
                    if symbol != seen[observed_key][0]:
                        counts["simultaneous_isin_symbol_conflict_rows"] += 1
                else:
                    seen[observed_key] = fingerprint
                    if key not in securities:
                        securities[key] = {"first": d, "last": d, "observed_sessions": 0}
                    s = securities[key]
                    s["first"] = min(s["first"], d)
                    s["last"] = max(s["last"], d)
                    s["observed_sessions"] += 1
                if latest is None or d > latest:
                    latest, latest_keys = d, {key}
                elif d == latest:
                    latest_keys.add(key)
        year_reports.append(
            {
                "year": declared_year,
                "rows": source.metadata.num_rows,
                "source_observation_keys": len(file_keys),
                **dict(local),
            }
        )
        print(json.dumps({"profiled": declared_year, "rows": source.metadata.num_rows}), flush=True)
    ordered_dates = sorted(sessions)
    ordinal = {d: i for i, d in enumerate(ordered_dates)}
    gap_counts: Counter[str] = Counter()
    for s in securities.values():
        missing = ordinal[s["last"]] - ordinal[s["first"]] + 1 - s["observed_sessions"]
        gap_counts["source_keys_with_internal_observed_session_gaps"] += missing > 0
        gap_counts["internal_observed_session_missing_slots"] += max(missing, 0)
    # Every requested defect field is explicit even when the measured count is zero.
    for field in (
        "duplicate_identity_session_rows",
        "conflicting_duplicate_rows",
        "simultaneous_isin_symbol_conflict_rows",
        "ohlc_consistency_violations",
        "volume_null",
        "volume_negative",
        "volume_zero",
        "file_year_date_mismatch",
        "extreme_source_prev_close_movements",
        "null_or_invalid_date",
    ):
        counts.setdefault(field, 0)
    for field in ("open", "high", "low", "close"):
        for suffix in ("null", "negative", "zero", "nonfinite"):
            counts.setdefault(f"{field}_{suffix}", 0)
    result = {
        "schema_version": "tejhq.raw-profile.v1",
        "status": "RAW_PROFILE_COMPLETE",
        "dataset_id": DATASET,
        "revision": REVISION,
        "data_reality": "REAL_MARKET_OBSERVATIONS",
        "usage_classification": "RESEARCH_ONLY",
        "production_market_data_use": "NOT_CLEARED",
        "production_claims_permitted": False,
        "file_count": len(acquisition["files"]),
        "total_bytes": acquisition["total_bytes"],
        "earliest_session": ordered_dates[0].isoformat(),
        "latest_session": ordered_dates[-1].isoformat(),
        "calendar_years": sorted(rows_by_year),
        "observed_trading_sessions": len(sessions),
        "calendar_status": "OBSERVED_SESSION_RESEARCH_EVIDENCE_NOT_AUTHORITATIVE_COMPLETENESS",
        "known_missing_session_checks": [
            {
                "session": d.isoformat(),
                "dataset_row_count": special_counts[d],
                "evidence": (
                    "NSE Market Pulse November 2024 CM Muhurat trading figure, printed page 86"
                ),
            }
            for d in SPECIAL_SESSIONS
            if ordered_dates[0] <= d <= ordered_dates[-1]
        ],
        "calendar_completeness": (
            "INCOMPLETE_VERIFIED_SPECIAL_SESSION_OMISSIONS"
            if any(
                d not in sessions and ordered_dates[0] <= d <= ordered_dates[-1]
                for d in SPECIAL_SESSIONS
            )
            else "NOT_ESTABLISHED"
        ),
        "calendar_verification_sources": CALENDAR_SOURCES,
        "weekend_observed_sessions": [d.isoformat() for d in ordered_dates if d.weekday() >= 5],
        "counts": dict(sorted(counts.items())),
        "rows_by_year": dict(sorted(rows_by_year.items())),
        "year_profiles": year_reports,
        "schemas": schema_reports,
        "distinct_symbols": len(symbols),
        "distinct_isins": len(isins),
        "series_rows": dict(series),
        "source_observation_keys": len(securities),
        "raw_symbol_session_duplicate_rows": symbol_session_duplicates,
        "stable_p4_security_count": None,
        "latest_session_observed_source_keys": len(latest_keys),
        "not_observed_on_latest_session_source_keys": len(securities.keys() - latest_keys),
        "confirmed_delisted_security_count": None,
        "symbols_with_multiple_isins": sum(len(v) > 1 for v in symbol_isins.values()),
        "isins_with_multiple_symbols": sum(len(v) > 1 for v in isin_symbols.values()),
        "explicit_non_equity_name_keys": {k: len(v) for k, v in sorted(excluded.items())},
        "authoritatively_classified_common_equities": 0,
        "asset_type_policy": "NO_EQ_SERIES_OR_ISIN_PATTERN_AUTOMATIC_UPGRADE",
        "missing_session_patterns": dict(gap_counts),
        "price_basis": "RAW_UNADJUSTED",
        "historical_price_availability": "UNAVAILABLE",
        "limitations": [
            "Publisher has already removed anomalous/zero-volume rows; lost-row counts unavailable",
            "Source observation keys are not reconciled P4 security identities",
            "Pre-2012 missing ISINs are not backfilled from later records",
            "Absence on latest session is not delisting; no corporate-chain merge inferred",
            "Missing dates are not asserted holidays or verified nontrading sessions",
            "ISIN code patterns are candidates, not evidence of COMMON_EQUITY eligibility",
            "Historical publication, availability, completion and vintage timestamps absent",
            "Float64 source precision retained; original exchange decimals unavailable",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incoming", type=Path, default=Path("data/incoming/tejhq") / REVISION)
    parser.add_argument("--output", type=Path, default=Path("docs/data/dataset-profile.json"))
    args = parser.parse_args()
    profile(args.incoming, args.output)


if __name__ == "__main__":
    main()
