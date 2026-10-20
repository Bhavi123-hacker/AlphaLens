"""Offline candidate manifest and capacity simulation; never activate or acquire."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import digest, encoded
from workers.nse_market import engine
from workers.providers import universe

from alphalens_api.auth.permissions import restrict


def capacity(
    stocks: int,
    *,
    max_stocks: int = 250,
    reserved_per_run: int = 600,
    daily_budget: int = 1800,
    slots: int = 3,
) -> dict[str, Any]:
    if any(
        type(x) is not int or x <= 0
        for x in (stocks, max_stocks, reserved_per_run, daily_budget, slots)
    ):
        raise ValueError("POSITIVE_INTEGER_CAPACITY_REQUIRED")
    batches = math.ceil(stocks / max_stocks)
    reservations = batches * reserved_per_run
    return {
        "stocks": stocks,
        "minimum_successful_batches": batches,
        "candle_gets_if_every_stock_missing": stocks,
        "action_gets_if_all_candles_valid": stocks,
        "stock_gets_if_all_valid": 2 * stocks,
        "reserved_capacity_required": reservations,
        "additional_daily_reserved_capacity_required": max(0, reservations - daily_budget),
        "additional_successful_slots_required": max(0, batches - slots),
        "same_session_full_coverage_supported": batches <= slots and reservations <= daily_budget,
        "stocks_per_day_upper_bound": min(slots, daily_budget // reserved_per_run) * max_stocks,
        "retries_included": False,
        "calendar_master_overhead": "ADDITIONAL_BOUNDED_REQUESTS_WITHIN_EACH_600_RESERVATION",
    }


def simulate_pending(stocks: int, slots: int, permanently_missing: int = 1) -> dict[str, int]:
    """TEST_ONLY oldest-missing-first queue, no invented source observations.

    Oldest missing instruments remain first on every run, matching daily selection.
    Successful hypothetical instruments are skipped on later simulated runs.
    """
    if not 0 <= permanently_missing <= stocks or stocks <= 0 or slots <= 0:
        raise ValueError("BOUNDED_SIMULATION_REQUIRED")
    pending = list(range(stocks))
    seen: set[int] = set()
    attempts = calls = 0
    for _ in range(slots):
        batch = pending[:250]
        seen.update(batch)
        attempts += len(batch)
        calls += sum(1 if key < permanently_missing else 2 for key in batch)
        pending = [key for key in pending if key not in batch or key < permanently_missing]
    return {
        "updated": stocks - len(pending),
        "pending": len(pending),
        "distinct_attempted": len(seen),
        "stock_attempts": attempts,
        "stock_gets_excluding_metadata": calls,
        "never_attempted": stocks - len(seen),
    }


def candidate_keys(existing: list[str], records: list[dict[str, Any]], target: int) -> list[str]:
    eligible = {r["instrument_key"]: r for r in records if r["eligible_common_equity"]}
    if len(set(existing)) != len(existing) or not set(existing) <= eligible.keys():
        raise ValueError("EXISTING_COHORT_MUST_REMAIN_UNIQUE_AND_CURRENTLY_ELIGIBLE")
    if not len(existing) <= target <= len(eligible):
        raise ValueError("AVAILABLE_TARGET_REQUIRED")
    ordered = sorted(eligible, key=lambda key: (eligible[key]["isin"], key))
    result = (
        sorted(existing)
        + [key for key in ordered if key not in set(existing)][: target - len(existing)]
    )
    if len({eligible[key]["isin"] for key in result}) != target:
        raise ValueError("DUPLICATE_ISIN_FORBIDDEN")
    return result


def prepare(repo: Path, output: Path) -> dict[str, Any]:
    root = repo / ".local-data/nse-market-expansion"
    universe_root = repo / ".local-data/nse-universe"
    output = output.resolve()
    proposal_root = (repo / ".local-data/nse-1000-readiness").resolve()
    if not output.is_relative_to(proposal_root):
        raise ValueError("ISOLATED_PRIVATE_OUTPUT_REQUIRED")
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("SYMLINK_OUTPUT_FORBIDDEN")
    master = universe.load(universe_root)
    plan = engine._pointed(root, "plan-latest.json")
    existing = [r["provider_key"] for r in plan["identities"]]
    keys = candidate_keys(existing, list(master.records), 1000)
    records = {r["instrument_key"]: r for r in master.records}
    saved = engine.workspace(root, repo / ".local-data/experimental-nse-v2")
    history = {r["key"]: r for r in saved["coverage"]["per_security"]}
    scores = {r["key"] for r in saved["candidates"]}
    manifest = {
        "version": "NSE_1000_OFFLINE_CANDIDATE_V1",
        "activation": "NOT_APPROVED_NOT_ACTIVATED",
        "selection": "PRESERVE_EXISTING_500_THEN_ISIN_ASCENDING_NO_RETURN_OR_SCORE_SELECTION",
        "master_snapshot_id": master.snapshot_id,
        "master_observed_at": master.observed_at.isoformat(),
        "master_raw_sha256": master.summary["raw_sha256"],
        "existing_plan_id": plan["plan_id"],
        "historical_membership": "CURRENT_FIXED_COHORT_ONLY",
        "securities": [
            {
                **records[key],
                "existing_approved_cohort": key in existing,
                "listing_status_evidence": (
                    "CURRENT_MASTER_ONLY_NOT_LISTING_DATE_OR_SUSPENSION_PROOF"
                ),
                "historical_data": history.get(key),
                "currently_scored": key in scores,
                "new_acquisition_authorized": False,
                "additional_data_readiness": "EXISTING_SAVED_EVIDENCE"
                if key in history
                else "NOT_QUERIED_NO_HISTORY_OR_ACTION_COMPATIBILITY_PROOF",
            }
            for key in keys
        ],
    }
    body = encoded(manifest)
    identifier = digest(body)
    output.mkdir(parents=True, exist_ok=True)
    restrict(output)
    target = output / (identifier + ".candidate.json")
    if target.exists():
        if target.read_bytes() != body:
            raise ValueError("OFFLINE_MANIFEST_CONFLICT")
    else:
        with target.open("xb") as stream:
            stream.write(body)
    restrict(target)
    daily_bytes = sum(
        p.stat().st_size for p in (root / "daily/2026-10-19").rglob("*") if p.is_file()
    )
    history_bytes = sum(p.stat().st_size for p in (root / "instruments").rglob("*") if p.is_file())
    result = {
        "as_of": datetime.now(UTC).isoformat(),
        "candidate_manifest": str(target.relative_to(repo)),
        "candidate_manifest_sha256": identifier,
        "current_master_common_equities": len(master.eligible),
        "candidate_count": len(keys),
        "existing_securities_preserved": len(existing),
        "additional_candidates": len(keys) - len(existing),
        "historically_observed_candidates": sum(k in history for k in keys),
        "currently_scored_candidates": sum(k in scores for k in keys),
        "series": dict(Counter(records[k]["instrument_type"] for k in keys)),
        "capacity_500": capacity(500),
        "capacity_1000": capacity(1000),
        "simulation_all_valid_four_slots": simulate_pending(1000, 4, 0),
        "simulation_one_oldest_pending_four_slots": simulate_pending(1000, 4, 1),
        "simulation_one_oldest_pending_five_slots": simulate_pending(1000, 5, 1),
        "bootstrap_new_500_logical_gets": {
            "candle_attempts": 500,
            "actions_if_all_nonempty": 500,
            "successful_stock_path_total": 1000,
            "overhead_and_retries_excluded": True,
        },
        "measured_existing_history_bytes": history_bytes,
        "measured_latest_daily_evidence_bytes": daily_bytes,
        "full_1000_daily_bytes_linear_estimate_not_guarantee": daily_bytes * 1000 / 499,
        "additional_500_daily_bytes_linear_estimate_not_guarantee": daily_bytes * 500 / 499,
        "new_source_requests": 0,
        "production_modified": False,
        "rights": "EXISTING_NARROW_PRIVATE_SCOPE_NOT_AN_AUTOMATIC_1000_STOCK_ACQUISITION_GRANT",
    }
    report = output / (identifier + ".readiness.json")
    # Only this isolated computed report is replaceable; candidate bytes are immutable.
    report.write_bytes(encoded(result))
    restrict(report)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path(".local-data/nse-1000-readiness"))
    args = parser.parse_args()
    print(json.dumps(prepare(Path(__file__).resolve().parents[1], args.output_root), indent=2))


if __name__ == "__main__":
    main()
