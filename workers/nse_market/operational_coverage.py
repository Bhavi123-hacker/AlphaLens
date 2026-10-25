"""Read-only saved-universe contracts and measured capacity/storage scenarios.

No transport, model fitting, forecast writes, scheduler or environment changes.
Storage and duration extrapolations are workload estimates, never benchmarks or
evidence that missing instruments will return data or produce eligible forecasts.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.experimental_nse.acquire import digest, encoded, private_path
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, TARGET_VERSION
from workers.providers import universe

from . import discovery, engine
from .coverage_plan import RESERVED_PER_DAY, RESERVED_PER_RUN, RUNS_PER_DAY, STOCKS_PER_RUN


def detail_contracts(
    master: universe.Snapshot, view: dict[str, Any], *, at: datetime
) -> dict[str, Any]:
    """Join every supported identity once; never replay thousands of HTTP reads."""
    discovery.identity_status(master, at=at)
    identities = {
        row["instrument_key"]: row for row in master.records if row["eligible_common_equity"]
    }
    prices = {row["key"]: row for row in view["rows"]}
    candidates = {
        row["key"]: row for row in (view.get("research_workspace") or {}).get("candidates", [])
    }
    if len(prices) != len(view["rows"]) or len(candidates) != len(
        (view.get("research_workspace") or {}).get("candidates", [])
    ):
        raise ValueError("DUPLICATE_SAVED_UNIVERSE_SECURITY_REJECTED")
    exclusions: dict[str, list[str]] = {}
    for item in (view.get("research_workspace") or {}).get("technical_exclusions", []):
        exclusions.setdefault(item["key"], []).append(item["reason"])
    model_dates: Counter[str] = Counter()
    for key, row in candidates.items():
        identity = row["identity"]
        recorded = datetime.fromisoformat(row["inference_at"])
        vector = row["features"]
        score = row["score"]
        if (
            tuple(row["feature_names"]) != LOCAL_FEATURE_NAMES
            or len(vector) != len(LOCAL_FEATURE_NAMES)
            or any(type(value) not in {int, float} or not math.isfinite(value) for value in vector)
            or type(score) not in {int, float}
            or not math.isfinite(score)
            or not 0 <= score <= 1
            or recorded.utcoffset() is None
            or recorded > at
            or row["session"] > at.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
            or row["target_version"] != TARGET_VERSION
            or row["source"] != "UPSTOX_OFFICIAL_HISTORICAL_CANDLES"
            or identity["provider_key"] != key
            or identity["isin"] != key.removeprefix("NSE_EQ|")
            or identity["symbol"] != row["symbol"]
        ):
            raise ValueError("SAVED_UNIVERSE_PREDICTION_CONTRACT_REJECTED")
        model_dates[row["session"]] += 1
    details = []
    for key, identity in sorted(identities.items()):
        if (
            not identity.get("name")
            or not identity.get("symbol")
            or key != "NSE_EQ|" + identity["isin"]
        ):
            raise ValueError("SUPPORTED_DETAIL_IDENTITY_INCOMPLETE")
        price = prices.get(key)
        history = view["histories"].get(key, [])
        has_price = price is not None and price["close"] is not None
        actual = [row for row in history if row["close"] is not None]
        if (
            has_price
            and price is not None
            and (
                not actual
                or actual[-1]["session"] != price["session"]
                or actual[-1]["close"] != price["close"]
            )
        ):
            raise ValueError("SAVED_DETAIL_PRICE_CHART_LINEAGE_MISMATCH")
        if price is None:
            price = discovery.empty_security(identity)
        risk = discovery.descriptive_risk(history, exclusions.get(key, []))
        details.append(
            {
                "key": key,
                "symbol": identity["symbol"],
                "has_saved_price_and_chart": has_price,
                "price_session": price["session"],
                "freshness": price["freshness"],
                "risk_state": risk["state"],
                "risk_observation_session": risk["observation_session"],
                "risk_missing_reason": risk["reason"],
                "saved_model_observation_session": candidates.get(key, {}).get("session"),
                "ml_missing_reasons": (
                    sorted(set(exclusions.get(key, [])))
                    or ["NO_COMPATIBLE_SAVED_FEATURE_VECTOR" if has_price else "NO_SAVED_HISTORY"]
                )
                if key not in candidates
                else [],
                "history_surface": "EXISTING_READ_ONLY_FORECAST_READER_OR_EXPLICIT_EMPTY_HISTORY",
            }
        )
    return {
        "status": "VERIFIED_COMPLETE",
        "supported_detail_contracts": len(details),
        "priced_chart_contracts": sum(row["has_saved_price_and_chart"] for row in details),
        "risk_states": dict(Counter(row["risk_state"] for row in details)),
        "risk_missing_reasons": dict(
            Counter(row["risk_missing_reason"] for row in details if row["risk_missing_reason"])
        ),
        "compatible_saved_predictions": len(candidates.keys() & identities.keys()),
        "model_observation_sessions": dict(sorted(model_dates.items())),
        "accepted_models": 0,
        "http_requests": 0,
        "provider_requests": 0,
        "method": (
            "LINEAR_INDEX_JOIN_OF_VERIFIED_SAVED_EVIDENCE_NOT_LIVE_HTTP_OR_INDEPENDENT_MODEL_ACCEPTANCE"
        ),
        "per_security": details,
    }


def durations(
    records: list[dict[str, Any]], *, calls: int, at: datetime | None = None
) -> dict[str, Any]:
    if type(calls) is not int or calls < 0:
        raise ValueError("NONNEGATIVE_PROPOSED_GET_COUNT_REQUIRED")
    samples = []
    seen = set()
    for row in records:
        if row.get("run_id") in seen:
            continue
        count = row.get("source_requests_last_run")
        if type(count) is not int or count <= 0 or not row.get("completed_at"):
            continue
        first, last = (
            datetime.fromisoformat(row["started_at"]),
            datetime.fromisoformat(row["completed_at"]),
        )
        if (
            first.utcoffset() is None
            or last.utcoffset() is None
            or last <= first
            or (at is not None and last > at)
        ):
            continue
        seen.add(row.get("run_id"))
        samples.append(
            {
                "run_id": row["run_id"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "state": row["state"],
                "actual_gets": count,
                "whole_job_seconds": (last - first).total_seconds(),
                "accepted_new_observations": (row.get("outcome") or {}).get(
                    "new_daily_observations"
                ),
            }
        )
    rates = [row["whole_job_seconds"] / row["actual_gets"] for row in samples]
    ordinary = [
        row["whole_job_seconds"] / row["actual_gets"]
        for row in samples
        if not str(row["state"]).startswith("INTERRUPTED")
    ]
    return {
        "status": "VERIFIED_COMPLETE" if rates else "BLOCKED_EXTERNAL_DATA",
        "qualified_receipts": len(samples),
        "receipts": samples,
        "proposed_gets": calls,
        "projected_active_seconds": {
            "min": min(rates) * calls,
            "median": statistics.median(rates) * calls,
            "max": max(rates) * calls,
        }
        if rates
        else None,
        "ordinary_completed_job_receipts": len(ordinary),
        "ordinary_completed_job_seconds_scenario": _range(ordinary, calls),
        "explicitly_interrupted_receipts": len(rates) - len(ordinary),
        "method": "WHOLE_JOB_WALL_TIME_PER_ACTUAL_GET_WORKLOAD_ESTIMATE_NOT_NETWORK_BENCHMARK",
        "limitations": [
            "Includes clock, source, validation, inference and persistence overhead",
            "Partial and failed-response runs remain in the samples",
            "Projection does not establish complete collection, timing SLA or a speedup",
            "Inter-run cooldown, overnight cadence and approvals are additional",
        ],
    }


def tree_bytes(root: Path) -> int:
    if root.is_symlink() or root.is_junction():
        raise ValueError("STORAGE_REPARSE_POINT_REJECTED")
    total = 0
    for entry in root.iterdir():
        if entry.is_symlink() or entry.is_junction():
            raise ValueError("STORAGE_REPARSE_POINT_REJECTED")
        total += tree_bytes(entry) if entry.is_dir() else entry.stat().st_size
    return total


def _range(values: list[float], multiplier: int) -> dict[str, float] | None:
    return (
        {
            "min": min(values) * multiplier,
            "median": statistics.median(values) * multiplier,
            "max": max(values) * multiplier,
        }
        if values
        else None
    )


def storage(root: Path, view: dict[str, Any], *, equities: int) -> dict[str, Any]:
    session = view["latest_observed_session"]
    daily_samples = []
    day = private_path(root, "daily", session)
    if day.exists():
        for path in day.glob("INE*/record.json"):
            record = engine._read(path)
            if record["response_sha256"] != digest(
                (path.parent / "response.json").read_bytes()
            ) or record["actions_sha256"] != digest((path.parent / "actions.json").read_bytes()):
                raise ValueError("STORAGE_SAMPLE_RECEIPT_LINEAGE_REJECTED")
            daily_samples.append(float(tree_bytes(path.parent)))
    historical_samples = []
    for path in private_path(root, "instruments").glob("INE*/normalization.json"):
        manifest = engine._read(path)
        count = manifest["observations"]
        if type(count) is not int or count <= 0:
            continue
        data_bytes = sum(
            (path.parent / name).stat().st_size for name in ("candles.json", "normalized.json.gz")
        )
        fixed_bytes = tree_bytes(path.parent) - data_bytes
        historical_samples.append(fixed_bytes + data_bytes * 61 / count)
    # Size the already verified pinned projection, avoiding a second pointer read
    # that could race a genuine append-only publication.
    projection_bytes = len(encoded(view))
    configured = view["configured_securities"]
    return {
        "status": "VERIFIED_COMPLETE",
        "latest_session": session,
        "measured_daily_security_folders": len(daily_samples),
        "daily_retained_source_bytes_scenario": _range(daily_samples, equities),
        "measured_historical_security_folders": len(historical_samples),
        "historical_61_slot_source_bytes_scenario": _range(historical_samples, equities),
        "current_saved_projection_bytes": projection_bytes,
        "whole_universe_projection_bytes_linear_scenario": projection_bytes * equities / configured
        if configured
        else None,
        "all_existing_daily_evidence_bytes": tree_bytes(private_path(root, "daily")),
        "all_existing_history_evidence_bytes": tree_bytes(private_path(root, "instruments")),
        "all_existing_immutable_market_views_bytes": tree_bytes(private_path(root, "market-views")),
        "limitations": [
            "Ranges are extrema and median of genuine payload samples, not confidence bounds",
            (
                "Daily folder sizes include retained attempts and "
                "source/checksum/normalization records"
            ),
            (
                "Historical scenario prorates observed data bytes plus "
                "per-security fixed evidence to61 slots"
            ),
            "61 genuine slots are not guaranteed for new listings or missing instruments",
            (
                "Forecast/outcome ledgers, PostgreSQL, models, backups and frozen "
                "research are additional"
            ),
            (
                "Immutable projections multiply by successful publications; no "
                "automatic pruning is authorized"
            ),
        ],
    }


def report(root: Path, universe_root: Path, *, at: datetime) -> dict[str, Any]:
    master = universe.load(universe_root)
    view = engine._pointed(root, "market-view-latest.json")
    counts = discovery.measure(master, view, at=at)
    n = counts["supported_equities"]
    batches = math.ceil(n / STOCKS_PER_RUN)
    jobs = []
    for path in private_path(root, "operational", "runs").glob("*.done.json"):
        jobs.append(engine._read(path))
    return {
        "as_of": at.isoformat(),
        "master_snapshot_id": master.snapshot_id,
        "dataset_id": view["dataset_id"],
        "coverage": counts,
        "detail_contracts": detail_contracts(master, view, at=at),
        "capacity": {
            "full_universe_batches": batches,
            "daily_reserved_gets_required": batches * RESERVED_PER_RUN,
            "currently_approved_daily_reserved_gets": RESERVED_PER_DAY,
            "minimum_capacity_days": math.ceil(batches / RUNS_PER_DAY),
            "successful_stock_gets_if_all_valid": 2 * n,
            "additional_metadata_gets_conservative_ceiling": 71 * batches,
            "success_path_gets_with_metadata_ceiling": 2 * n + 71 * batches,
            "historical_bootstrap_stock_gets_lower_bound": 2
            * (n - counts["available_saved_prices"]),
            "daily_rotation_is_not_full_daily_coverage": True,
            "activation_status": "BLOCKED_APPROVAL",
        },
        "duration": durations(jobs, calls=2 * n, at=at),
        "storage": storage(root, view, equities=n),
        "actual_provider_requests": 0,
        "new_forecasts": 0,
        "protected_data_modified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--universe-root", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.root, args.universe_root, at=datetime.now(UTC))
    result["detail_contracts"].pop("per_security")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
