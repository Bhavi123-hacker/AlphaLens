"""Point-in-time, read-only display of frozen forecasts and qualified outcomes.

No initialization, reconciliation, inference, permissions writes or acquisition.
Overlapping original/expanded decisions are counted once for evaluation.
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import digest
from workers.experimental_nse_v2 import data, forward
from workers.nse_market import engine
from workers.providers.upstox import Reply

from .auth.permissions import verify

FIELDS = (
    "score",
    "baseline_majority_score",
    "baseline_momentum_score",
    "baseline_mean_reversion_score",
)


def _calendar(root: Path, day: str, at: datetime) -> dict[str, Any] | None:
    path = root / "calendar" / (day + ".json")
    if not path.exists():
        return None
    saved = engine._read(path)
    raw = bytes.fromhex(saved["raw_hex"])
    received = forward._at(saved["received_at"])
    if digest(raw) != saved["raw_sha256"] or received > at:
        return None
    return data.timing_fact(Reply(200, raw, received, "ACCEPTED"), date.fromisoformat(day))


def _mature(
    root: Path,
    forecast: dict[str, Any],
    outcome: dict[str, Any],
    at: datetime,
    calendar_cache: dict[str, Any],
    link_cache: dict[str, Any],
) -> bool:
    """Recheck decision chronology, five-session chain and price-component formula."""
    inputs = outcome.get("inputs", [])
    retrieved = forward._at(outcome["source_observed_at"])
    recorded = forward._at(outcome["recorded_at"])
    if (
        outcome.get("status") != "MATURED_PRICE_REFERENCE_RETURN"
        or outcome.get("known_action_exclusions")
        or not forward._at(forecast["recorded_at"]) < retrieved <= recorded <= at
        or len(inputs) != 5
        or outcome.get("target_version") != forecast.get("target_version")
        or outcome.get("inputs_hash")
        != forward._hash({"inputs": inputs, "known_action_exclusions": []})
    ):
        return False
    days = [item["session"] for item in inputs]
    if any(date.fromisoformat(day).isoformat() != day for day in [forecast["session"], *days]):
        return False
    if (
        sorted(set(days)) != days
        or days[0] != forecast["next_session_timing"]["session"]
        or days[0] != outcome.get("entry_session")
        or days[-1] != outcome.get("target_session")
        or days[-1] >= retrieved.astimezone(forward.IST).date().isoformat()
    ):
        return False
    previous = forecast["session"]
    for day in days:
        if day not in calendar_cache:
            calendar_cache[day] = _calendar(root, day, at)
        fact = calendar_cache[day]
        link_path = root / "session-links" / (previous + ".json")
        if fact is None or not link_path.exists():
            return False
        if previous not in link_cache:
            link_cache[previous] = engine._read(link_path)["next_session_timing"]
        following = link_cache[previous]
        if (
            following["session"] != day
            or following.get("previous_session") != previous
            or following.get("intervening_dates_verified_closed") is not True
            or forward._at(following["source_received_at"]) > retrieved
            or fact["source_sha256"] != following["source_sha256"]
            or forward._at(fact["close_at"]) >= retrieved
            or (
                previous == forecast["session"]
                and fact["open_at"] != forecast["next_session_timing"]["open_at"]
            )
        ):
            return False
        previous = day
    entry, exit_price = Fraction(inputs[0]["open"]), Fraction(inputs[-1]["close"])
    exact = Fraction(
        int(outcome["target_return_numerator"]), int(outcome["target_return_denominator"])
    )
    return (
        entry > 0
        and exit_price > 0
        and exact == exit_price / entry - 1
        and outcome.get("target") == int(exact > 0)
    )


def _metrics(pairs: list[tuple[dict[str, Any], dict[str, Any]]], field: str) -> dict[str, Any]:
    valid = [
        (f[field], o["target"])
        for f, o in pairs
        if type(f.get(field)) in {float, int} and math.isfinite(f[field]) and 0 <= f[field] <= 1
    ]
    positive = sum(target for _, target in valid)
    negative = len(valid) - positive
    tp = sum(score >= 0.5 and target == 1 for score, target in valid)
    tn = sum(score < 0.5 and target == 0 for score, target in valid)
    return {
        "samples": len(valid),
        "accuracy": (tp + tn) / len(valid) if valid else None,
        "balanced_accuracy": (tp / positive + tn / negative) / 2 if positive and negative else None,
        "brier_score": sum((score - target) ** 2 for score, target in valid) / len(valid)
        if valid
        else None,
    }


def read(root: Path, v2_root: Path, *, at: datetime) -> dict[str, Any]:
    if at.utcoffset() is None or at > datetime.now(UTC):
        raise ValueError("NONFUTURE_AWARE_EVALUATION_CUTOFF_REQUIRED")
    stores = [v2_root / "price-only", *sorted((root / "expanded-forecasts").glob("*"))]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    raw_count, ignored_future = 0, 0
    for folder in stores:
        path = folder / "experimental-v2-prospective.sqlite3"
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("PROSPECTIVE_SYMLINK_FORBIDDEN")
        if not path.exists():
            continue
        verify(folder)
        verify(path, directory=False)
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        ) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            outcomes: dict[str, dict[str, Any]] = {}
            for row in conn.execute("SELECT * FROM experimental_outcomes ORDER BY revision"):
                body = forward._verified(row)
                if forward._at(body["recorded_at"]) <= at:
                    outcomes[body["forecast_id"]] = body
            for row in conn.execute("SELECT * FROM experimental_forecasts"):
                f = forward._verified(row)
                if forward._at(f["recorded_at"]) > at:
                    ignored_future += 1
                    continue
                raw_count += 1
                key = (f["model_id"], f["key"], f["session"])
                grouped.setdefault(key, []).append(
                    {"forecast": f, "outcome": outcomes.get(row["id"])}
                )
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    # Scoped to this cutoff/read only; never hide later source revisions in a global cache.
    calendar_cache: dict[str, Any] = {}
    link_cache: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for key, entries in sorted(grouped.items()):
        f = min((e["forecast"] for e in entries), key=lambda f: f["recorded_at"])
        entry = f.get("next_session_timing") or {}
        opening = forward._at(entry["open_at"]) if entry.get("open_at") else None
        reason = "AWAITING_QUALIFIED_FIVE_SESSION_OUTCOME"
        if (
            f.get("prospective_eligible") is not True
            or opening is None
            or not forward._at(f["source_observed_at"])
            <= forward._at(f["inference_at"])
            <= forward._at(f["recorded_at"])
            < opening
        ):
            reason = "INELIGIBLE_FORECAST_CHRONOLOGY"
        elif opening > at:
            reason = "FUTURE_ENTRY_NOT_STARTED"
        else:
            observed = [e["outcome"] for e in entries if e["outcome"] is not None]
            signatures = {(o["status"], o.get("target_return"), o.get("target")) for o in observed}
            scores = {(e["forecast"]["score"], e["forecast"].get("feature_hash")) for e in entries}
            if len(signatures) > 1 or len(scores) > 1:
                reason = "OVERLAPPING_RECORD_CONFLICT"
            elif observed:
                o = observed[0]
                if o["status"] != "MATURED_PRICE_REFERENCE_RETURN":
                    reason = "EXCLUDED_OUTCOME"
                elif _mature(root, f, o, at, calendar_cache, link_cache):
                    reason = "MATURED_VERIFIED_OUTCOME"
                    pairs.append((f, o))
                else:
                    reason = "OUTCOME_EVIDENCE_NOT_QUALIFIED_AT_CUTOFF"
        reasons[reason] += 1
        rows.append(
            {
                "model_id": key[0],
                "key": key[1],
                "observation_session": key[2],
                "recorded_at": f["recorded_at"],
                "entry_at": entry.get("open_at"),
                "status": reason,
            }
        )
    model_groups = sorted({(f["model_id"], f.get("target_version", "UNKNOWN")) for f, _ in pairs})
    return {
        "as_of": at.isoformat(),
        "raw_forecast_records": raw_count,
        "unique_decisions": len(grouped),
        "overlapping_records": raw_count - len(grouped),
        "future_forecast_records_ignored": ignored_future,
        "matured_outcomes": len(pairs),
        "not_evaluated_decisions": len(grouped) - len(pairs),
        "status_counts": dict(reasons),
        "rows": rows[:100],
        "rows_total": len(rows),
        "metrics": {
            field: _metrics(pairs if len(model_groups) <= 1 else [], field) for field in FIELDS
        },
        "model_groups": [
            {
                "model_id": model,
                "target_version": target,
                "metrics": {
                    field: _metrics(
                        [
                            (f, o)
                            for f, o in pairs
                            if (f["model_id"], f.get("target_version", "UNKNOWN"))
                            == (model, target)
                        ],
                        field,
                    )
                    for field in FIELDS
                },
            }
            for model, target in model_groups
        ],
        "metrics_basis": "UNIQUE_MATURED_DECISIONS_ONLY_FIXED_0_5_THRESHOLD",
        "evaluation_classification": "INTERIM_MATURED_SAMPLE_NOT_REGISTERED_GLOBAL_ACCEPTANCE",
        "independent_decision_dates": len({f["session"] for f, _ in pairs}),
        "independent_acceptance": False,
        "accepted_rankings": 0,
        "provider_requests": 0,
        "uncertainty": "SHARED_DATES_OVERLAPPING_TARGETS_REQUIRE_INDEPENDENT_PROTOCOL_REVIEW",
        "economic_edge": "NOT_ESTABLISHED",
    }
