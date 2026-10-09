"""Read-only evidence audit of frozen research backtests; never fit or simulate."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds
import pyarrow.parquet as pq

from alphalens_data.ingestion.storage import stable_json

VERSION = "p10.frozen_evidence_audit.v1"
PRICE_COLUMNS = [
    "security_id",
    "session_date",
    "canonical_record_id",
    "p2_security_id",
    "symbol",
    "isin",
    "identity_basis",
    "quality",
    "economic_action",
    "raw_sha256",
    "source_row_number",
]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def trade_evidence(
    trade: dict[str, Any],
    sessions: list[str],
    prices: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare stored lifecycle with source flags, including temporary missing marks.

    Exits precede EOD marking. Action flags precede exits. After a permanent
    unresolved event the frozen engine stops economic reconciliation; later
    prices cannot repair it. This reproduces checks, not prices/cash/trading.
    """
    active = [d for d in sessions if trade["entry_session"] <= d]
    marks: set[str] = set()
    events: list[tuple[str, str]] = []
    expected = "OPEN"
    unresolved = False
    for day in active:
        row = prices.get(day)
        if row and row["economic_action"]:
            events.append(("RAW_ACTION_AFTER_UNRESOLVED" if unresolved else "RAW_ACTION", day))
            marks.update(d for d in active if d >= day)
            expected = "UNRESOLVED_RAW_ECONOMIC_ACTION"
            unresolved = True
        if unresolved:
            continue
        if day == trade["planned_exit_session"]:
            if not row or row["quality"] == "REJECTED":
                events.append(("MISSING_EXIT" if not row else "REJECTED_EXIT", day))
                marks.update(d for d in active if d >= day)
                expected = "UNRESOLVED_MISSING_EXIT"
                unresolved = True
            else:
                expected = "CLOSED"
                break
            continue
        if not row or row["quality"] == "REJECTED":
            events.append(("MISSING_MARK" if not row else "REJECTED_MARK", day))
            marks.add(day)
    return {
        "events": events,
        "unknown_sessions": sorted(marks),
        "expected_status": expected,
        "status_matches": expected == trade["status"],
    }


def gap_classification(
    session: dict[str, Any], entry: dict[str, Any], alternatives: list[dict[str, Any]]
) -> str:
    if session["price_status"] == "PRICE_OBSERVATION_MISSING":
        return "VERIFIED_SESSION_SOURCE_PRICE_MISSING"
    same_source = [r for r in alternatives if r["p2_security_id"] == entry["p2_security_id"]]
    if same_source:
        return "SOURCE_ID_PRESENT_UNDER_DIFFERENT_RESEARCH_ID"
    if alternatives:
        return "SAME_SYMBOL_OTHER_ID_AMBIGUOUS_NOT_MERGED"
    return "NO_CANONICAL_OBSERVATION_NO_TERMINAL_VALUE_EVIDENCE"


def check_output(output: Path, roots: list[Path]) -> None:
    target = output.resolve()
    if any(target == r.resolve() or target.is_relative_to(r.resolve()) for r in roots):
        raise ValueError("AUDIT_OUTPUT_MUST_NOT_OVERWRITE_FROZEN_INPUTS")


def enrich_source_gaps(result: dict[str, Any], acquisition: Path, incoming: Path) -> dict[str, Any]:
    """Verify actual archive absence separately from an internal identity lookup miss."""
    manifest = json.loads(acquisition.read_bytes())
    gaps = [e for e in result["events"] if e["kind"].startswith("MISSING")]
    by_symbol: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_isin: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    wanted_symbols = {(e["symbol_at_entry"], e["session"]) for e in gaps}
    wanted_isins = {(e["isin_at_entry"], e["session"]) for e in gaps if e["isin_at_entry"]}
    verified_files = []
    for receipt in manifest["files"]:
        if not receipt["filename"].startswith("nse/"):
            continue
        path = incoming / manifest["revision"] / receipt["filename"]
        if digest(path) != receipt["sha256"]:
            raise ValueError("SOURCE_PRICE_CHECKSUM_MISMATCH")
        verified_files.append({k: receipt[k] for k in ("filename", "sha256")})
        offset = 0
        for batch in pq.ParquetFile(path).iter_batches(
            columns=["date", "symbol", "isin", "series", "open", "close"]
        ):
            for ordinal, row in enumerate(batch.to_pylist(), offset):
                day = row["date"].isoformat()
                symbol_key, isin_key = (row["symbol"], day), (row["isin"], day)
                if symbol_key not in wanted_symbols and isin_key not in wanted_isins:
                    continue
                evidence = {
                    "file": receipt["filename"],
                    "sha256": receipt["sha256"],
                    "source_row_number": ordinal,
                    "symbol": row["symbol"],
                    "isin": row["isin"],
                    "series": row["series"],
                    "open_close_present": row["open"] is not None and row["close"] is not None,
                }
                if symbol_key in wanted_symbols:
                    by_symbol[symbol_key].append(evidence)
                if isin_key in wanted_isins:
                    by_isin[isin_key].append(evidence)
            offset += batch.num_rows
    for event in gaps:
        symbol_rows = by_symbol[(event["symbol_at_entry"], event["session"])]
        isin_rows = by_isin[(event["isin_at_entry"], event["session"])]
        event["original_source_rows"] = symbol_rows
        event["original_source_isin_rows"] = isin_rows
        event["source_gap_status"] = (
            "SOURCE_OBSERVATION_PRESENT_IDENTITY_RECONCILIATION_REQUIRED"
            if symbol_rows or isin_rows
            else "SOURCE_OBSERVATION_ABSENT"
        )
    result["verified_original_price_files"] = verified_files
    result["missing_event_source_status_counts"] = dict(
        sorted(Counter(e["source_gap_status"] for e in gaps).items())
    )
    return result


def audit(run_root: Path, data_root: Path, acquisition: Path, incoming: Path) -> dict[str, Any]:
    input_stats = {
        str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in run_root.rglob("*") if p.is_file()
    }
    # Hash every completed model/OOS/backtest/lock artifact once. A post-audit stat
    # check detects writes during this read-only process without rescanning rows.
    preservation = [
        {
            "path": str(Path(p).relative_to(run_root)).replace("\\", "/"),
            "bytes": size,
            "sha256": digest(Path(p)),
        }
        for p, (size, _) in sorted(input_stats.items())
    ]
    print(f"Preserved fingerprint: {len(preservation)} artifacts", flush=True)
    runs: dict[str, dict[str, Any]] = {}
    trades: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    equities: dict[str, list[dict[str, Any]]] = {}
    evidence_hashes: dict[str, dict[str, str]] = {}
    for phase in ("development", "2025", "2026"):
        for summary in json.loads((run_root / f"{phase}-backtests.json").read_bytes())["backtests"]:
            bid = summary["backtest_id"]
            if bid in runs:
                raise ValueError("DUPLICATE_BACKTEST_ID")
            folder = run_root / "p10" / bid
            stored = json.loads((folder / "summary.json").read_bytes())
            if stored != {k: v for k, v in summary.items() if k != "phase"}:
                raise ValueError("BACKTEST_INDEX_SUMMARY_MISMATCH")
            runs[bid] = summary
            equities[bid] = pq.read_table(folder / "equity.parquet").to_pylist()
            evidence_hashes[bid] = {
                n: digest(folder / n)
                for n in ("summary.json", "trades.parquet", "equity.parquet")
                if (folder / n).exists()
            }
            trade_rows = (
                pq.read_table(folder / "trades.parquet").to_pylist()
                if (folder / "trades.parquet").exists()
                else []
            )
            if len(trade_rows) != summary["trade_count"]:
                raise ValueError("STORED_TRADE_COUNT_MISMATCH")
            for trade in trade_rows:
                trades[trade["security_id"]].append((bid, trade))
    calendar = json.loads((data_root / "research-calendar.json").read_bytes())
    calendar_by_day = {r["session_date"]: r for r in calendar["sessions"]}
    canonical = json.loads((data_root / "canonical-manifest.json").read_bytes())
    manifest = json.loads(acquisition.read_bytes())
    actions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for receipt in manifest["files"]:
        if not receipt["filename"].startswith("actions/"):
            continue
        path = incoming / manifest["revision"] / receipt["filename"]
        if digest(path) != receipt["sha256"]:
            raise ValueError("SOURCE_ACTION_CHECKSUM_MISMATCH")
        for ordinal, row in enumerate(pq.read_table(path).to_pylist()):
            if row["type"] not in {"agm", "buyback"}:
                actions[(row["symbol"], row["ex_date"].isoformat())].append(
                    {
                        "file": receipt["filename"],
                        "sha256": receipt["sha256"],
                        "source_row_number": ordinal,
                        "type": row["type"],
                        "isin": row["isin"],
                        "cash_amount_present": row["cash_amount"] is not None,
                        "ratio_present": row["ratio_num"] is not None
                        and row["ratio_den"] is not None,
                    }
                )
    unknown: dict[str, set[str]] = defaultdict(set)
    run_events: dict[str, set[str]] = defaultdict(set)
    events: dict[str, dict[str, Any]] = {}
    inconsistencies: list[dict[str, Any]] = []
    trade_status: Counter[str] = Counter()
    by_bucket: dict[int, list[str]] = defaultdict(list)
    for security in trades:
        by_bucket[int(hashlib.sha256(security.encode()).hexdigest()[:8], 16) % 64].append(security)
    for receipt in canonical["identity"]["files"]:
        path = data_root / receipt["path"]
        if digest(path) != receipt["sha256"]:
            raise ValueError("CANONICAL_CHECKSUM_MISMATCH")
        bucket = int(path.stem.split("-")[-1])
        securities = by_bucket.get(bucket, [])
        table = ds.dataset(path, format="parquet").to_table(
            columns=PRICE_COLUMNS, filter=ds.field("security_id").isin(securities)
        )
        prices: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in table.to_pylist():
            prices[row["security_id"]][row["session_date"].isoformat()] = row
        for security in securities:
            for bid, trade in trades[security]:
                days = [r["session"] for r in equities[bid]]
                result = trade_evidence(trade, days, prices[security])
                trade_status[trade["status"]] += 1
                if not result["status_matches"]:
                    inconsistencies.append(
                        {
                            "backtest_id": bid,
                            "trade_id": trade["trade_id"],
                            "check": "TRADE_STATUS",
                            "expected": result["expected_status"],
                        }
                    )
                unknown[bid].update(result["unknown_sessions"])
                entry = prices[security].get(trade["entry_session"])
                if entry is None:
                    raise ValueError("STORED_FILL_WITHOUT_CANONICAL_ENTRY")
                for kind, day in result["events"]:
                    # Cost scenarios/models may repeat one causal source event.
                    eid = hashlib.sha256(stable_json([security, day, kind])).hexdigest()
                    run_events[bid].add(eid)
                    if eid in events:
                        events[eid]["trade_occurrences"] += 1
                        continue
                    row = prices[security].get(day)
                    event: dict[str, Any] = {
                        "event_id": eid,
                        "kind": kind,
                        "security_id": security,
                        "session": day,
                        "symbol_at_entry": entry["symbol"],
                        "p2_security_id_at_entry": entry["p2_security_id"],
                        "isin_at_entry": entry["isin"],
                        "identity_basis": entry["identity_basis"],
                        "entry_record_id": entry["canonical_record_id"],
                        "trade_occurrences": 1,
                        "calendar_evidence": calendar_by_day[day]["evidence"],
                    }
                    if row:
                        event.update(
                            canonical_record_id=row["canonical_record_id"],
                            raw_sha256=row["raw_sha256"],
                            source_row_number=row["source_row_number"],
                            quality=row["quality"],
                        )
                    if kind.startswith("RAW_ACTION"):
                        matched = actions.get((row["symbol"], day), []) if row else []
                        event["action_evidence"] = matched
                        event["cause"] = "RAW_ACTION_UNRECONCILED_ECONOMIC_ENTITLEMENT"
                        event["action_isin_conflict"] = any(
                            a["isin"] and row and row["isin"] and a["isin"] != row["isin"]
                            for a in matched
                        )
                        if not matched:
                            inconsistencies.append(
                                {"event_id": eid, "check": "ACTION_SOURCE_MISSING"}
                            )
                    elif kind.startswith("REJECTED"):
                        event["cause"] = "QUALITY_REJECTED_PRICE"
                    else:
                        event["cause"] = "PENDING_GAP_CLASSIFICATION"
                    events[eid] = event
        print(f"Canonical evidence bucket {bucket:02d} checked", flush=True)
    # Examine only actually missing keys; alternatives are evidence, not permission
    # to merge identities or rewrite a frozen execution/valuation.
    gaps = [e for e in events.values() if e["cause"] == "PENDING_GAP_CLASSIFICATION"]
    wanted = {(e["symbol_at_entry"], e["session"]) for e in gaps}
    alternatives: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    if wanted:
        table = ds.dataset(data_root / "canonical", format="parquet").to_table(
            columns=PRICE_COLUMNS,
            filter=ds.field("symbol").isin(sorted({s for s, _ in wanted}))
            & ds.field("session_date").isin(sorted({date.fromisoformat(d) for _, d in wanted})),
        )
        for row in table.to_pylist():
            key = row["symbol"], row["session_date"].isoformat()
            if key in wanted:
                alternatives[key].append(row)
    for event in gaps:
        matches = alternatives[(event["symbol_at_entry"], event["session"])]
        event["cause"] = gap_classification(
            calendar_by_day[event["session"]],
            {"p2_security_id": event["p2_security_id_at_entry"]},
            matches,
        )
        event["alternative_records"] = [
            {
                k: r[k]
                for k in ("security_id", "canonical_record_id", "p2_security_id", "isin", "quality")
            }
            for r in sorted(matches, key=lambda x: x["canonical_record_id"])
        ]
    audited_runs = []
    for bid, summary in sorted(runs.items()):
        actual_unknown = {r["session"] for r in equities[bid] if r["portfolio_value"] is None}
        if actual_unknown != unknown[bid]:
            inconsistencies.append(
                {
                    "backtest_id": bid,
                    "check": "UNKNOWN_EQUITY_SESSIONS",
                    "missing_explanation": sorted(actual_unknown - unknown[bid]),
                    "unexpected_explanation": sorted(unknown[bid] - actual_unknown),
                }
            )
        expected_status = (
            "UNRESOLVED_ECONOMIC_OUTCOMES" if actual_unknown else "RESEARCH_RAW_PRICE_DIAGNOSTIC"
        )
        if expected_status != summary["status"]:
            inconsistencies.append({"backtest_id": bid, "check": "SUMMARY_STATUS"})
        refs = sorted(run_events[bid])
        audited_runs.append(
            {
                "backtest_id": bid,
                "phase": summary["phase"],
                "task": summary["task"],
                "horizon": summary["horizon"],
                "model_family": summary["model_family"],
                "selection_rule": summary["selection_rule"],
                "cost_scenario": summary["cost_scenario"],
                "status": summary["status"],
                "unresolved_trade_count": summary["unresolved_trade_count"],
                "unknown_valuation_sessions": len(actual_unknown),
                "first_unknown_session": min(actual_unknown) if actual_unknown else None,
                "cause_counts": dict(sorted(Counter(events[e]["cause"] for e in refs).items())),
                "event_ids": refs,
                "stored_evidence_sha256": evidence_hashes[bid],
            }
        )
    after_stats = {
        str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in run_root.rglob("*") if p.is_file()
    }
    if after_stats != input_stats:
        raise ValueError("FROZEN_ARTIFACT_CHANGED_DURING_READ_ONLY_AUDIT")
    return {
        "schema_version": VERSION,
        "baseline_commit": "8507f7fd5457fe5e53e016c2cd7b8f14e6b6e430",
        **{
            k: canonical["identity"][k]
            for k in (
                "data_reality",
                "usage_classification",
                "final_vintage",
                "production_market_data_use",
            )
        },
        "benchmark": "UNAVAILABLE",
        "canonical_dataset_id": canonical["dataset_id"],
        "artifact_inventory_sha256": hashlib.sha256(stable_json(preservation)).hexdigest(),
        "preserved_file_count": len(preservation),
        "preserved_bytes": sum(p["bytes"] for p in preservation),
        "artifact_inventory": preservation,
        "preservation_check": (
            "ALL_CONTENT_HASHED_BEFORE_AUDIT_ALL_SIZES_MTIMES_PATHS_UNCHANGED_AFTER"
        ),
        "audit_status": "CONSISTENT_WITH_FROZEN_ENGINE"
        if not inconsistencies
        else "INCONSISTENCIES_FOUND",
        "backtest_status_counts": dict(sorted(Counter(r["status"] for r in audited_runs).items())),
        "trade_status_counts": dict(sorted(trade_status.items())),
        "unique_event_causes": dict(sorted(Counter(e["cause"] for e in events.values()).items())),
        "runs_with_cause": dict(
            sorted(Counter(c for r in audited_runs for c in r["cause_counts"]).items())
        ),
        "action_type_unique_events": dict(
            sorted(
                Counter(
                    t
                    for e in events.values()
                    for t in {a["type"] for a in e.get("action_evidence", [])}
                ).items()
            )
        ),
        "inconsistencies": inconsistencies,
        "runs": audited_runs,
        "events": sorted(events.values(), key=lambda e: e["event_id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--enrich-existing",
        type=Path,
        help="Reuse completed read-only audit; check original-price gaps only",
    )
    args = parser.parse_args()
    incoming = Path("data/incoming/tejhq")
    check_output(args.output, [args.run_root, args.data_root, incoming])
    acquisition = Path("docs/data/tejhq-acquisition-manifest.json")
    result = (
        json.loads(args.enrich_existing.read_bytes())
        if args.enrich_existing
        else audit(args.run_root, args.data_root, acquisition, incoming)
    )
    result = enrich_source_gaps(result, acquisition, incoming)
    events = {e["event_id"]: e for e in result["events"]}
    partition: Counter[str] = Counter()
    for run in result["runs"]:
        if run["status"] != "UNRESOLVED_ECONOMIC_OUTCOMES":
            continue
        kinds = [events[e]["kind"] for e in run["event_ids"]]
        has_action = any(k.startswith("RAW_ACTION") for k in kinds)
        has_gap = any(k.startswith("MISSING") for k in kinds)
        partition[
            "ACTION_AND_GAP"
            if has_action and has_gap
            else "ACTION_ONLY"
            if has_action
            else "GAP_ONLY"
        ] += 1
    result["unresolved_run_partition"] = dict(sorted(partition.items()))
    plan = json.loads(Path("docs/ml/research-training-plan.json").read_bytes())
    expected = dict(plan["code_hashes"])
    expected["uv.lock"] = plan["dependency_lock_sha256"]
    if any(digest(Path(p)) != sha for p, sha in expected.items()):
        raise ValueError("FROZEN_RESEARCH_PROTOCOL_CHANGED")
    result["frozen_protocol_hashes"] = expected
    result["auditor_sha256"] = digest(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(stable_json(result))
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "audit_status",
                    "backtest_status_counts",
                    "trade_status_counts",
                    "unique_event_causes",
                    "runs_with_cause",
                    "action_type_unique_events",
                    "preserved_file_count",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
