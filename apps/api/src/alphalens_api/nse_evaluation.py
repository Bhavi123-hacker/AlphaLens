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
from workers.nse_market import engine, forward_cohort
from workers.providers.upstox import Reply

from .auth.permissions import verify

FIELDS = (
    "score",
    "baseline_majority_score",
    "baseline_momentum_score",
    "baseline_mean_reversion_score",
    "baseline_risk_score",
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
    next_open = forecast.get("next_session_timing", {}).get("open_at")
    if (
        outcome.get("status") != "MATURED_PRICE_REFERENCE_RETURN"
        or outcome.get("forecast_id") != forward._hash(forecast)
        or forecast.get("prospective_eligible") is not True
        or not next_open
        or not forward._at(forecast["source_observed_at"])
        <= forward._at(forecast["inference_at"])
        <= forward._at(forecast["recorded_at"])
        < forward._at(next_open)
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
        if type(f.get(field)) in {float, int}
        and math.isfinite(f[field])
        and 0 <= f[field] <= 1
        and type(o.get("target")) is int
        and o["target"] in (0, 1)
    ]
    positive = sum(target for _, target in valid)
    negative = len(valid) - positive
    tp = sum(score >= 0.5 and target == 1 for score, target in valid)
    tn = sum(score < 0.5 and target == 0 for score, target in valid)
    fp, fn = negative - tn, positive - tp
    # Mann-Whitney score, with half credit for ties; O(n log n), no pair matrix.
    wins, earlier_negative = 0.0, 0
    score_groups: dict[float, list[int]] = {}
    for score, target in valid:
        score_groups.setdefault(score, []).append(target)
    for score in sorted(score_groups):
        targets = score_groups[score]
        p = sum(targets)
        n = len(targets) - p
        wins += p * (earlier_negative + n / 2)
        earlier_negative += n
    bins = []
    for index in range(10):
        selected = [(s, t) for s, t in valid if min(int(s * 10), 9) == index]
        bins.append(
            {
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "samples": len(selected),
                "mean_score": sum(s for s, _ in selected) / len(selected) if selected else None,
                "positive_fraction": sum(t for _, t in selected) / len(selected)
                if selected
                else None,
            }
        )
    return {
        "samples": len(valid),
        "excluded_invalid_or_missing": len(pairs) - len(valid),
        "positive_targets": positive,
        "negative_targets": negative,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accuracy": (tp + tn) / len(valid) if valid else None,
        "balanced_accuracy": (tp / positive + tn / negative) / 2 if positive and negative else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / positive if positive else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "roc_auc": wins / (positive * negative) if positive and negative else None,
        "brier_score": sum((score - target) ** 2 for score, target in valid) / len(valid)
        if valid
        else None,
        "score_bins": bins,
        "score_classification": "UNCALIBRATED_SCORE_DIAGNOSTIC_NOT_GAIN_PROBABILITY",
    }


def _baseline_comparisons(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    result = {}
    for field in FIELDS[1:]:
        matched = [
            (f, o)
            for f, o in pairs
            if all(
                type(f.get(name)) in {float, int} and math.isfinite(f[name]) and 0 <= f[name] <= 1
                for name in ("score", field)
            )
        ]
        candidate, baseline = _metrics(matched, "score"), _metrics(matched, field)
        result[field] = {
            "matched_samples": candidate["samples"],
            "excluded_missing_pairs": len(pairs) - candidate["samples"],
            "candidate": candidate,
            "baseline": baseline,
            "candidate_minus_baseline": {
                metric: candidate[metric] - baseline[metric]
                if candidate[metric] is not None and baseline[metric] is not None
                else None
                for metric in ("accuracy", "balanced_accuracy", "brier_score", "roc_auc")
            },
        }
    return result


def _selection_metrics(
    declaration: dict[str, Any], qualified: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Full original cohort or null; missing outcomes never change selections."""
    members = declaration["members"]
    indexed = {item["key"]: item for item in members}
    complete = bool(members) and all(item["forecast_id"] in qualified for item in members)
    selection: dict[str, Any] = {}
    for field, groups in declaration["frozen_selection"].items():
        selection[field] = {}
        for count in (5, 10, 20):
            keys = groups[str(count)]
            expected = [
                item["key"]
                for item in sorted(members, key=lambda item: (-item[field], item["key"]))[:count]
            ]
            if keys != expected:
                raise ValueError("FROZEN_GLOBAL_SELECTION_LINEAGE_MISMATCH")
            hits = (
                sum(qualified[indexed[key]["forecast_id"]]["target"] for key in keys)
                if complete
                else None
            )
            selection[field][str(count)] = {
                "selected_securities": len(keys),
                "qualified_selected_outcomes": sum(
                    indexed[key]["forecast_id"] in qualified for key in keys
                ),
                "hits": hits,
                "hit_rate": hits / len(keys) if hits is not None and keys else None,
            }
    return {
        "declaration_id": declaration["declaration_id"],
        "model_id": declaration["model_id"],
        "observation_session": declaration["observation_session"],
        "declared_securities": len(members),
        "qualified_outcomes": sum(item["forecast_id"] in qualified for item in members),
        "complete": complete,
        "equal_cohort_hit_rate": sum(qualified[item["forecast_id"]]["target"] for item in members)
        / len(members)
        if complete
        else None,
        "selections": selection,
    }


def _top_n(
    root: Path,
    forecasts: dict[str, dict[str, Any]],
    qualified: dict[str, dict[str, Any]],
    at: datetime,
) -> dict[str, Any]:
    results = []
    for path in sorted((root / "global-cohorts").glob("*.json")):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("PROSPECTIVE_SYMLINK_FORBIDDEN")
        declaration = engine._read(path)
        if forward._at(declaration["recorded_at"]) > at:
            continue
        if declaration["protocol_id"] != forward_cohort.protocol_id():
            raise ValueError("GLOBAL_DECLARATION_PROTOCOL_MISMATCH")
        members = declaration["members"]
        if not members or len({m["key"] for m in members}) != len(members):
            raise ValueError("GLOBAL_DECLARATION_UNIQUE_MEMBERS_REQUIRED")
        for member in members:
            f = forecasts.get(member["forecast_id"])
            if (
                f is None
                or f["model_id"] != declaration["model_id"]
                or f["key"] != member["key"]
                or f.get("prospective_eligible") is not True
                or f["session"] != declaration["observation_session"]
                or f["feature_hash"] != member["feature_hash"]
                or f["source_sha256"] != member["source_sha256"]
                or any(f.get(field) != member.get(field) for field in FIELDS)
                or f["recorded_at"] != member["original_forecast_recorded_at"]
                or f["next_session_timing"]["session"] != member["entry_session"]
                or forward._at(f["next_session_timing"]["open_at"])
                != forward._at(member["entry_open_at"])
                or forward._at(f["recorded_at"]) > forward._at(declaration["recorded_at"])
                or not forward._at(declaration["decision_clock"]["upper_at"])
                < forward._at(f["next_session_timing"]["open_at"])
                or not forward._at(declaration["recorded_at"])
                < forward._at(f["next_session_timing"]["open_at"])
            ):
                raise ValueError("GLOBAL_DECLARATION_FORECAST_LINEAGE_MISMATCH")
        results.append(_selection_metrics(declaration, qualified))
    return {
        "declarations": len(results),
        "complete_declarations": sum(r["complete"] for r in results),
        "results": results,
        "pooled_hit_rate": None,
        "basis": "ORIGINAL_FROZEN_GLOBAL_SELECTION_COMPLETE_COHORT_ONLY",
        "missing_evidence": []
        if any(r["complete"] for r in results)
        else ["COMPLETE_QUALIFIED_DECLARED_COHORT_OUTCOMES"],
        "independent_acceptance": False,
    }


def read(root: Path, v2_root: Path, *, at: datetime) -> dict[str, Any]:
    if at.utcoffset() is None or at > datetime.now(UTC):
        raise ValueError("NONFUTURE_AWARE_EVALUATION_CUTOFF_REQUIRED")
    stores = [v2_root / "price-only", *sorted((root / "expanded-forecasts").glob("*"))]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    raw_count, ignored_future = 0, 0
    all_forecasts: dict[str, dict[str, Any]] = {}
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
                all_forecasts[row["id"]] = f
                key = (f["model_id"], f["key"], f["session"])
                grouped.setdefault(key, []).append(
                    {"forecast": f, "outcome": outcomes.get(row["id"])}
                )
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    qualified: dict[str, dict[str, Any]] = {}
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
            scores = {
                (
                    *(e["forecast"].get(field) for field in FIELDS),
                    e["forecast"].get("feature_hash"),
                    e["forecast"].get("target_version"),
                )
                for e in entries
            }
            if len(signatures) > 1 or len(scores) > 1:
                reason = "OVERLAPPING_RECORD_CONFLICT"
            elif observed:
                o = observed[0]
                if o["status"] != "MATURED_PRICE_REFERENCE_RETURN":
                    reason = "EXCLUDED_OUTCOME"
                else:
                    matured = []
                    for e in entries:
                        own_outcome = e["outcome"]
                        if own_outcome is not None and _mature(
                            root, e["forecast"], own_outcome, at, calendar_cache, link_cache
                        ):
                            qualified[forward._hash(e["forecast"])] = own_outcome
                            matured.append(own_outcome)
                    if matured:
                        reason = "MATURED_VERIFIED_OUTCOME"
                        pairs.append((f, matured[0]))
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
                "baseline_comparisons": _baseline_comparisons(
                    [
                        (f, o)
                        for f, o in pairs
                        if (f["model_id"], f.get("target_version", "UNKNOWN")) == (model, target)
                    ]
                ),
            }
            for model, target in model_groups
        ],
        "baseline_comparisons": _baseline_comparisons(pairs if len(model_groups) <= 1 else []),
        "top_n": _top_n(root, all_forecasts, qualified, at),
        "metrics_basis": "UNIQUE_MATURED_DECISIONS_ONLY_FIXED_0_5_THRESHOLD",
        "evaluation_classification": "INTERIM_MATURED_SAMPLE_NOT_REGISTERED_GLOBAL_ACCEPTANCE",
        "independent_decision_dates": len({f["session"] for f, _ in pairs}),
        "independent_acceptance": False,
        "accepted_rankings": 0,
        "provider_requests": 0,
        "uncertainty": "SHARED_DATES_OVERLAPPING_TARGETS_REQUIRE_INDEPENDENT_PROTOCOL_REVIEW",
        "economic_edge": "NOT_ESTABLISHED",
    }
