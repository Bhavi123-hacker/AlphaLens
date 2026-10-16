"""V2 immutable actual-time holding-price forecasts, isolated from V1 and accepted ML."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from scipy.stats import spearmanr
from workers.experimental_nse.features import candle

from alphalens_api.auth.permissions import restrict, verify

from .features import FAMILY, FEATURE_NAMES, FEATURE_VERSION, HORIZON, TARGET_VERSION

IST = ZoneInfo("Asia/Kolkata")
VERSION = "experimental.nse.prospective.v2"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return sha256(_encode(value).encode()).hexdigest()


def _at(value: str | datetime) -> datetime:
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(result, datetime) or result.tzinfo is None:
        raise ValueError("AWARE_SOURCE_RETRIEVAL_TIME_REQUIRED")
    return result.astimezone(UTC)


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value):
        raise ValueError("EXPERIMENT_ID_REQUIRED")
    return value


@contextmanager
def _connection(root: Path, *, write: bool = False) -> Iterator[sqlite3.Connection]:
    """Only this dedicated child ledger is written; protect every open."""
    path = root / "experimental-v2-prospective.sqlite3"
    if root.is_symlink() or path.is_symlink():
        raise ValueError("PROSPECTIVE_SYMLINK_FORBIDDEN")
    root.mkdir(parents=True, exist_ok=True)
    restrict(root)
    verify(root)
    if not path.exists():
        with sqlite3.connect(path) as initializing:
            schema = Path(__file__).resolve().parents[2] / "db/experimental-nse-v2.sql"
            initializing.executescript(schema.read_text(encoding="utf-8"))
        if os.name != "nt":
            path.chmod(0o600)
    if path.resolve().parent != root.resolve():
        raise ValueError("PROSPECTIVE_PATH_ESCAPE")
    verify(path, directory=False)
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE" if write else "PRAGMA query_only=ON")
        yield connection
        if write:
            connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _verified(row: sqlite3.Row) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(row["body"])
    if _hash(body) != row["id"]:
        raise ValueError("PROSPECTIVE_CHECKSUM_MISMATCH")
    if body.get("recorded_at") != row["recorded_at"]:
        raise ValueError("PROSPECTIVE_INDEX_MISMATCH")
    columns = set(row.keys())
    if "model_id" in columns and (
        body.get("model_id") != row["model_id"]
        or body.get("key") != row["instrument_key"]
        or body.get("session") != row["observation_session"]
    ):
        raise ValueError("PROSPECTIVE_INDEX_MISMATCH")
    if "revision" in columns and (
        body.get("revision") != row["revision"] or body.get("forecast_id") != row["forecast_id"]
    ):
        raise ValueError("PROSPECTIVE_INDEX_MISMATCH")
    return body


def _eligible_timing(
    session: str, timing: Any, following: Any, observed: datetime, now: datetime
) -> tuple[bool, str]:
    """Require dated evidence; no regular-open or weekday assumptions."""
    if not isinstance(timing, dict) or not isinstance(following, dict):
        return False, "DATED_OBSERVATION_AND_NEXT_SESSION_TIMING_REQUIRED"
    for evidence in (timing, following):
        if evidence.get("source") != "UPSTOX_OFFICIAL_MARKET_TIMINGS" or not re.fullmatch(
            r"[0-9a-f]{64}", str(evidence.get("source_sha256", ""))
        ):
            return False, "OFFICIAL_TIMING_LINEAGE_REQUIRED"
        opening, closing = _at(evidence["open_at"]), _at(evidence["close_at"])
        if (
            opening >= closing
            or opening.astimezone(IST).date().isoformat() != evidence.get("session")
            or closing.astimezone(IST).date().isoformat() != evidence.get("session")
        ):
            raise ValueError("CONTRADICTORY_SESSION_TIMING")
        if _at(evidence["source_received_at"]) > now:
            raise ValueError("TIMING_SOURCE_AFTER_FORECAST")
    if timing["session"] != session or _at(timing["close_at"]) > observed:
        return False, "PUBLISHED_COMPLETED_OBSERVATION_SESSION_REQUIRED"
    if following["session"] <= session or _at(following["open_at"]) <= now:
        return False, "FULL_FUTURE_TARGET_ENTRY_ALREADY_ELAPSED"
    if (
        following.get("previous_session") != session
        or following.get("intervening_dates_verified_closed") is not True
    ):
        return False, "CONSECUTIVE_NEXT_SESSION_EVIDENCE_REQUIRED"
    return True, "DATED_NEXT_ENTRY_OPEN_AFTER_ACTUAL_FORECAST"


def append_forecasts(
    root: Path,
    model_id: str,
    dataset_id: str,
    protocol_id: str,
    scores: Sequence[Mapping[str, Any]],
    source_observed_at: str | datetime,
) -> dict[str, Any]:
    """Record real runtime only. No supplied historical decision clock is accepted.

    Duplicate model/key/observation is an idempotent replay only if all immutable
    inputs agree. A changed model or source snapshot requires a new model/version;
    the old forecast is never replaced. This does not run retrospective evaluation.
    """
    model_id, dataset_id = _identifier(model_id), _identifier(dataset_id)
    protocol_id = _identifier(protocol_id)
    now, observed = _utc_now(), _at(source_observed_at)
    if observed > now:
        raise ValueError("SOURCE_RETRIEVAL_AFTER_FORECAST")
    if len(scores) > 100:
        raise ValueError("PROSPECTIVE_COHORT_LIMIT")
    if len({score.get("key") for score in scores}) != len(scores):
        raise ValueError("UNIQUE_PROSPECTIVE_COHORT_REQUIRED")
    prepared = []
    for score in scores:
        if any(key in score for key in ("decision_at", "recorded_at", "forecast_at")):
            raise ValueError("CALLER_FORECAST_CLOCK_FORBIDDEN")
        for field, expected in (
            ("model_id", model_id),
            ("dataset_id", dataset_id),
            ("protocol_id", protocol_id),
            ("target_version", TARGET_VERSION),
            ("horizon_observed_sessions", HORIZON),
        ):
            if field in score and score[field] != expected:
                raise ValueError("FROZEN_FORECAST_LINEAGE_MISMATCH")
        key, symbol, session = score.get("key"), score.get("symbol"), score.get("session")
        if not isinstance(key, str) or not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", key):
            raise ValueError("EXACT_NSE_KEY_REQUIRED")
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9&_.-]{1,40}", symbol):
            raise ValueError("EXACT_NSE_SYMBOL_REQUIRED")
        if not isinstance(session, str):
            raise ValueError("ISO_SESSION_REQUIRED")
        day = date.fromisoformat(session)
        if day.isoformat() != session or day > observed.astimezone(IST).date():
            raise ValueError("OBSERVATION_AFTER_SOURCE_RETRIEVAL")
        if day == observed.astimezone(IST).date() and observed.astimezone(IST).time() < time(16):
            raise ValueError("SAME_DAY_EOD_COMPLETENESS_UNPROVEN")
        vector = score.get("vector")
        feature_version = score.get("feature_version", FEATURE_VERSION)
        expected_names = (
            FEATURE_NAMES[:16]
            if feature_version == "nse.adjusted-price-only.16.v2"
            else FEATURE_NAMES
        )
        if (
            not isinstance(vector, (list, tuple))
            or len(vector) != len(expected_names)
            or any(isinstance(v, bool) or not isinstance(v, (float, int)) for v in vector)
            or not all(math.isfinite(v) for v in vector)
        ):
            raise ValueError("COMPLETE_FINITE_FEATURE_VECTOR_REQUIRED")
        names = tuple(score.get("feature_names", expected_names))
        if names != expected_names or feature_version not in (
            FEATURE_VERSION,
            "nse.adjusted-price-only.16.v2",
        ):
            raise ValueError("PROSPECTIVE_FEATURE_CONTRACT_MISMATCH")
        value = score.get("score")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= 1:
            raise ValueError("FINITE_UNCALIBRATED_SCORE_REQUIRED")
        frozen_vector = [float(v) for v in vector]
        vector_hash = _hash(frozen_vector)
        if score.get("feature_hash", vector_hash) != vector_hash:
            raise ValueError("PROSPECTIVE_FEATURE_HASH_MISMATCH")
        inference_at = _at(score.get("inference_at", now))
        if not observed <= inference_at <= now:
            raise ValueError("INFERENCE_SOURCE_OR_RUNTIME_CHRONOLOGY_REJECTED")
        if (now - inference_at).total_seconds() > 60:
            raise ValueError("ACTUAL_CURRENT_INFERENCE_TIMESTAMP_REQUIRED")
        timing, following = score.get("session_timing"), score.get("next_session_timing")
        eligible, eligibility_reason = _eligible_timing(session, timing, following, observed, now)
        if isinstance(following, dict) and (
            ("entry_session" in score and score["entry_session"] != following.get("session"))
            or (
                "entry_open_at" in score
                and _at(score["entry_open_at"]) != _at(following["open_at"])
            )
        ):
            raise ValueError("FORECAST_ENTRY_TIMING_LINEAGE_MISMATCH")
        if score.get("eligible_for_prospective") is False:
            eligible, eligibility_reason = False, "SCORER_MARKED_TIMING_INELIGIBLE"
        baselines: dict[str, float | None] = {}
        for field in (
            "baseline_majority_score",
            "baseline_momentum_score",
            "baseline_mean_reversion_score",
            "baseline_risk_score",
        ):
            baseline = score.get(field)
            if baseline is not None and (
                isinstance(baseline, bool)
                or not isinstance(baseline, (float, int))
                or not 0 <= baseline <= 1
            ):
                raise ValueError("FINITE_PREDECLARED_BASELINE_SCORE_REQUIRED")
            baselines[field] = float(baseline) if baseline is not None else None
        body = {
            "version": VERSION,
            "family": FAMILY,
            "model_id": model_id,
            "dataset_id": dataset_id,
            "protocol_id": protocol_id,
            "key": key,
            "symbol": symbol,
            "session": session,
            "score": float(value),
            "score_classification": "UNCALIBRATED_MODEL_SCORE",
            "vector": frozen_vector,
            "feature_names": list(names),
            "feature_version": feature_version,
            "feature_hash": vector_hash,
            "source": score.get("source", "UPSTOX_AUTHENTICATED_HISTORICAL_V3"),
            "source_sha256": score.get("source_sha256"),
            "source_observed_at": observed.isoformat(),
            "decision_clock": score.get("decision_clock"),
            "inference_at": inference_at.isoformat(),
            "recorded_at": now.isoformat(),
            "horizon": HORIZON,
            "target_version": TARGET_VERSION,
            "accepted_ml": False,
            "classification": "EXPERIMENTAL_UNVALIDATED_RESEARCH",
            "prospective_eligible": eligible,
            "prospective_eligibility_reason": eligibility_reason,
            "session_timing": timing,
            "next_session_timing": following,
            "price_basis": "PROVIDER_STAFF_CONFIRMED_SPLIT_BONUS_ADJUSTED_NOT_DIVIDEND",
            "complete_action_coverage": False,
            "frozen_scored_cohort_sha256": _hash(sorted(item["key"] for item in scores)),
            **baselines,
        }
        prepared.append(body)
    rank_fields = (
        "score",
        "baseline_majority_score",
        "baseline_momentum_score",
        "baseline_mean_reversion_score",
        "baseline_risk_score",
    )
    for body in prepared:
        body["frozen_selection_ranks"] = {}
    for field in rank_fields:
        ordered = sorted(
            (body for body in prepared if body.get(field) is not None),
            key=lambda body: (-float(body[field]), body["key"]),
        )
        for rank, body in enumerate(ordered, 1):
            body["frozen_selection_ranks"][field] = rank
    inserted, replayed, identities = 0, 0, []
    with _connection(root, write=True) as connection:
        latest_clock = connection.execute(
            "SELECT MAX(recorded_at) FROM experimental_forecasts"
        ).fetchone()[0]
        if latest_clock and _at(latest_clock) > now:
            raise ValueError("PROSPECTIVE_LEDGER_CLOCK_ROLLBACK")
        for body in prepared:
            previous = connection.execute(
                "SELECT * FROM experimental_forecasts WHERE model_id=? "
                "AND instrument_key=? AND observation_session=?",
                (model_id, body["key"], body["session"]),
            ).fetchone()
            if previous:
                original = _verified(previous)
                comparison = dict(body)
                comparison["recorded_at"] = original["recorded_at"]
                comparison["prospective_eligible"] = original["prospective_eligible"]
                comparison["prospective_eligibility_reason"] = original[
                    "prospective_eligibility_reason"
                ]
                for optional_field in (
                    "inference_at",
                    "regular_session_open_assumption",
                    "baseline_majority_score",
                    "baseline_momentum_score",
                ):
                    if optional_field not in original:
                        comparison.pop(optional_field, None)
                if "inference_at" in original:
                    comparison["inference_at"] = original["inference_at"]
                if comparison != original:
                    raise ValueError("IMMUTABLE_FORECAST_REPLAY_CONFLICT")
                identities.append(previous["id"])
                replayed += 1
                continue
            identity = _hash(body)
            connection.execute(
                "INSERT INTO experimental_forecasts VALUES (?,?,?,?,?,?)",
                (
                    identity,
                    model_id,
                    body["key"],
                    body["session"],
                    body["recorded_at"],
                    _encode(body),
                ),
            )
            identities.append(identity)
            inserted += 1
    return {"inserted": inserted, "replayed": replayed, "forecast_ids": identities}


def reconcile(
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    sessions: Sequence[str],
    source_observed_at: str | datetime,
    excluded_sessions: Mapping[str, Sequence[str]] | None = None,
    *,
    official_timings: Mapping[str, Mapping[str, Any]] | None = None,
    require_official_sessions: bool = False,
) -> dict[str, int]:
    """Freeze actual newly observed future outcomes; corrections append revisions.

    Require the next-five observational grid and first target session opening
    after the actual forecast. Mid-session forecasts cannot retrospectively
    qualify an already-started full open-to-close target. No calendar is fabricated.
    """
    now, retrieved = _utc_now(), _at(source_observed_at)
    if retrieved > now:
        raise ValueError("OUTCOME_SOURCE_RETRIEVAL_IN_FUTURE")
    reference = tuple(sessions)
    if tuple(sorted(set(reference))) != reference:
        raise ValueError("SORTED_UNIQUE_REFERENCE_SESSIONS_REQUIRED")
    for session in reference:
        if date.fromisoformat(session).isoformat() != session:
            raise ValueError("ISO_REFERENCE_SESSION_REQUIRED")
    observed = {}
    for row in rows:
        observation = candle(row)
        identity = (observation.key, observation.session)
        if identity in observed:
            raise ValueError("DUPLICATE_OUTCOME_OBSERVATION")
        if date.fromisoformat(observation.session) >= retrieved.astimezone(IST).date():
            raise ValueError("OUTCOME_COMPLETE_PAST_SESSION_REQUIRED")
        observed[identity] = observation
    counts = {
        "inserted": 0,
        "replayed": 0,
        "pending": 0,
        "ineligible": 0,
        "corrections": 0,
        "unscorable": 0,
    }
    with _connection(root, write=True) as connection:
        latest_clock = connection.execute(
            "SELECT MAX(recorded_at) FROM experimental_outcomes"
        ).fetchone()[0]
        if latest_clock and _at(latest_clock) > now:
            raise ValueError("PROSPECTIVE_LEDGER_CLOCK_ROLLBACK")
        forecasts = connection.execute(
            "SELECT * FROM experimental_forecasts ORDER BY id"
        ).fetchall()
        for row in forecasts:
            forecast = _verified(row)
            recorded = _at(forecast["recorded_at"])
            if not forecast["prospective_eligible"]:
                counts["ineligible"] += 1
                continue
            if retrieved <= recorded or forecast["session"] not in reference:
                counts["pending"] += 1
                continue
            start = reference.index(forecast["session"]) + 1
            required = reference[start : start + HORIZON]
            if required and required[0] != forecast["next_session_timing"]["session"]:
                counts["ineligible"] += 1
                continue
            if len(required) != HORIZON or any(
                (forecast["key"], session) not in observed for session in required
            ):
                counts["pending"] += 1
                continue
            if require_official_sessions and any(
                not (official_timings or {}).get(session)
                or (official_timings or {})[session].get("session") != session
                or (official_timings or {})[session].get("source")
                != "UPSTOX_OFFICIAL_MARKET_TIMINGS"
                or not (official_timings or {})[session].get("source_sha256")
                or _at((official_timings or {})[session]["close_at"]) >= retrieved
                for session in required
            ):
                counts["pending"] += 1
                continue
            if require_official_sessions and any(
                (official_timings or {}).get(previous, {}).get("next_verified_session") != following
                for previous, following in zip(
                    (forecast["session"], *required[:-1]), required, strict=True
                )
            ):
                # The observed-date union cannot hide an entirely uncollected market session.
                counts["pending"] += 1
                continue
            sequence = (forecast["session"], *required)
            if any(
                (date.fromisoformat(b) - date.fromisoformat(a)).days > 7
                for a, b in zip(sequence, sequence[1:], strict=False)
            ):
                counts["ineligible"] += 1
                continue
            selected = [observed[(forecast["key"], session)] for session in required]
            if any(item.symbol != forecast["symbol"] for item in selected):
                raise ValueError("OUTCOME_FORECAST_IDENTITY_MISMATCH")
            inputs = [
                {"session": item.session, "open": str(item.open), "close": str(item.close)}
                for item in selected
            ]
            hazards = sorted(
                set(required) & set((excluded_sessions or {}).get(forecast["key"], ()))
            )
            inputs_hash = _hash({"inputs": inputs, "known_action_exclusions": hazards})
            target_return = Fraction(selected[-1].close) / Fraction(selected[0].open) - 1
            previous = connection.execute(
                "SELECT * FROM experimental_outcomes WHERE forecast_id=? "
                "ORDER BY revision DESC LIMIT 1",
                (row["id"],),
            ).fetchone()
            previous_body = _verified(previous) if previous else None
            if previous_body and previous_body["inputs_hash"] == inputs_hash:
                counts["replayed"] += 1
                continue
            if previous_body and retrieved <= _at(previous_body["source_observed_at"]):
                raise ValueError("CORRECTION_REQUIRES_NEWER_SOURCE_RETRIEVAL")
            revision = previous["revision"] + 1 if previous else 1
            body = {
                "version": VERSION,
                "status": "UNSCORABLE_KNOWN_ACTION"
                if hazards
                else "MATURED_PRICE_REFERENCE_RETURN",
                "known_action_exclusions": hazards,
                "entry_session": required[0],
                "entry_reference": str(selected[0].open),
                "exit_reference": str(selected[-1].close),
                "reference_fill_only": True,
                "forecast_id": row["id"],
                "revision": revision,
                "inputs": inputs,
                "inputs_hash": inputs_hash,
                "target_return": str(
                    Decimal(target_return.numerator) / Decimal(target_return.denominator)
                ),
                "target_return_numerator": str(target_return.numerator),
                "target_return_denominator": str(target_return.denominator),
                "target": None if hazards else int(target_return > 0),
                "target_session": required[-1],
                "target_version": TARGET_VERSION,
                "source_observed_at": retrieved.isoformat(),
                "recorded_at": now.isoformat(),
                "economic_profitability_verified": False,
            }
            connection.execute(
                "INSERT INTO experimental_outcomes VALUES (?,?,?,?,?)",
                (_hash(body), row["id"], revision, now.isoformat(), _encode(body)),
            )
            counts["inserted"] += 1
            counts["unscorable"] += int(bool(hazards))
            counts["corrections"] += int(previous is not None)
    return counts


def summary(root: Path) -> dict[str, Any]:
    """First frozen outcomes drive metrics; later correction counts remain visible."""
    with _connection(root) as connection:
        forecasts = {
            row["id"]: _verified(row)
            for row in connection.execute("SELECT * FROM experimental_forecasts ORDER BY id")
        }
        outcomes = connection.execute(
            "SELECT * FROM experimental_outcomes ORDER BY forecast_id,revision"
        ).fetchall()
        checked = [_verified(row) for row in outcomes]
    latest = {body["forecast_id"]: body for body in checked}
    first = [body for body in latest.values() if body["status"] == "MATURED_PRICE_REFERENCE_RETURN"]
    positive = [body for body in first if body["target"] == 1]
    negative = [body for body in first if body["target"] == 0]

    def accuracy(group: list[dict[str, Any]]) -> float | None:
        if not group:
            return None
        return sum(
            int((forecasts[body["forecast_id"]]["score"] >= 0.5) == bool(body["target"]))
            for body in group
        ) / len(group)

    positive_accuracy, negative_accuracy = accuracy(positive), accuracy(negative)
    balanced = (
        (positive_accuracy + negative_accuracy) / 2
        if positive_accuracy is not None and negative_accuracy is not None
        else None
    )
    eligible_count = sum(int(body["prospective_eligible"]) for body in forecasts.values())

    def measurements(field: str, group: list[dict[str, Any]]) -> dict[str, Any]:
        paired = [
            (float(forecasts[body["forecast_id"]][field]), body["target"])
            for body in group
            if forecasts[body["forecast_id"]].get(field) is not None
        ]
        tp = sum(int(value >= 0.5 and target == 1) for value, target in paired)
        tn = sum(int(value < 0.5 and target == 0) for value, target in paired)
        positives = sum(target for _, target in paired)
        negatives = len(paired) - positives
        predicted_positive = sum(int(value >= 0.5) for value, _ in paired)
        return {
            "count": len(paired),
            "accuracy": (tp + tn) / len(paired) if paired else None,
            "balanced_accuracy": (tp / positives + tn / negatives) / 2
            if positives and negatives
            else None,
            "precision": tp / predicted_positive if predicted_positive else None,
            "recall": tp / positives if positives else None,
            "brier": sum((value - target) ** 2 for value, target in paired) / len(paired)
            if paired
            else None,
        }

    metrics = {
        **measurements("score", first),
        "baselines": {
            field: measurements(field, first)
            for field in (
                "baseline_majority_score",
                "baseline_momentum_score",
                "baseline_mean_reversion_score",
                "baseline_risk_score",
            )
        },
        "by_target_month": {
            month: measurements(
                "score", [body for body in first if body["target_session"].startswith(month)]
            )
            for month in sorted({body["target_session"][:7] for body in first})
        },
    }
    metrics.update(_uncertainty(forecasts, first))
    return {
        "version": VERSION,
        "classification": "PROSPECTIVE_EVALUATION_IN_PROGRESS"
        if eligible_count
        else "BACKTESTED_NOT_PROSPECTIVELY_ACCEPTED",
        "forecast_count": len(forecasts),
        "prospective_eligible_forecast_count": eligible_count,
        "research_only_forecast_count": sum(
            int(not body["prospective_eligible"]) for body in forecasts.values()
        ),
        "legacy_missing_baseline_count": sum(
            int(
                body.get("baseline_majority_score") is None
                or body.get("baseline_momentum_score") is None
            )
            for body in forecasts.values()
        ),
        "matured_outcome_count": len(first),
        "pending_outcome_count": eligible_count - len(latest),
        "recorded_eligible_decision_dates": len(
            {
                _at(body["recorded_at"]).astimezone(IST).date().isoformat()
                for body in forecasts.values()
                if body["prospective_eligible"]
            }
        ),
        "outstanding_forecasts": [
            {
                "key": body["key"],
                "symbol": body["symbol"],
                "observation_session": body["session"],
                "recorded_at": body["recorded_at"],
                "first_required_session": body["next_session_timing"]["session"],
                "first_required_open_at": body["next_session_timing"]["open_at"],
                "required_subsequent_eligible_sessions": HORIZON,
                "remaining_evidence": "FIVE_FUTURE_PRICE_SLOTS_AND_OFFICIAL_TIMINGS",
                "earliest_review_condition": "AFTER_FIFTH_ELIGIBLE_SESSION_PUBLICATION",
            }
            for identity, body in forecasts.items()
            if body["prospective_eligible"] and identity not in latest
        ],
        "outcome_revision_count": len(checked),
        "correction_count": len(checked) - len(latest),
        "unscorable_outcome_count": sum(
            int(body["status"] != "MATURED_PRICE_REFERENCE_RETURN") for body in latest.values()
        ),
        "future_decision_dates": len(
            {
                _at(forecasts[body["forecast_id"]]["recorded_at"])
                .astimezone(IST)
                .date()
                .isoformat()
                for body in first
            }
        ),
        "securities_with_outcomes": len({forecasts[body["forecast_id"]]["key"] for body in first}),
        "outcome_quarters": len(
            {
                (body["target_session"][:4], (int(body["target_session"][5:7]) - 1) // 3)
                for body in first
            }
        ),
        "balanced_accuracy": balanced,
        "accuracy": accuracy(first),
        "independent_acceptance": False,
        "forecasts": len(forecasts),
        "outcomes": len(first),
        "eligible_forecasts": eligible_count,
        "metrics": metrics,
        "status": (
            "ACTIVE_WAITING_FOR_MATURED_OUTCOMES"
            if eligible_count
            else "READY_NO_FULL_SESSION_PROSPECTIVE_FORECASTS"
        ),
        "limitations": [
            "Actual runtime forecasts; no retrospective rows qualify as prospective.",
            "Later entry must match frozen verified timing and precede the complete target.",
            "Dated official timing is required; weekdays and regular hours are not inferred.",
            "Observed cohort dates are not a certified complete NSE calendar.",
            "Uncalibrated adjusted price appreciation is not dividend-inclusive profit.",
            "Metrics use latest revisions; immutable originals and corrections remain visible.",
        ],
    }


def _uncertainty(
    forecasts: Mapping[str, Mapping[str, Any]], outcomes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Moving blocks retain shared dates and short serial dependence; no iid rows."""

    def balanced(items: Sequence[Mapping[str, Any]], field: str) -> float | None:
        positive = [item for item in items if item["target"] == 1]
        negative = [item for item in items if item["target"] == 0]
        if (
            not positive
            or not negative
            or any(forecasts[item["forecast_id"]].get(field) is None for item in items)
        ):
            return None
        return (
            sum(int(forecasts[item["forecast_id"]][field] >= 0.5) for item in positive)
            / len(positive)
            + sum(int(forecasts[item["forecast_id"]][field] < 0.5) for item in negative)
            / len(negative)
        ) / 2

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in outcomes:
        grouped.setdefault(
            _at(forecasts[item["forecast_id"]]["recorded_at"]).astimezone(IST).date().isoformat(),
            [],
        ).append(item)
    dates = sorted(grouped)
    intervals: dict[str, list[float] | None] = {}
    for field in (
        "baseline_majority_score",
        "baseline_momentum_score",
        "baseline_mean_reversion_score",
    ):
        values = []
        generator = np.random.default_rng(42)
        if len(dates) >= 20:
            for _ in range(1000):
                selected: list[str] = []
                while len(selected) < len(dates):
                    start = int(generator.integers(len(dates) - min(20, len(dates)) + 1))
                    selected.extend(dates[start : start + 20])
                items = [item for day in selected[: len(dates)] for item in grouped[day]]
                candidate, baseline = balanced(items, "score"), balanced(items, field)
                if candidate is not None and baseline is not None:
                    values.append(candidate - baseline)
        values.sort()
        intervals[field] = (
            [
                values[int((0.05 / (2 * 3)) * len(values))],
                values[int((1 - 0.05 / (2 * 3)) * len(values))],
            ]
            if values
            else None
        )
    correlations = []
    for items in grouped.values():
        scores = [forecasts[item["forecast_id"]]["score"] for item in items]
        returns = [float(item["target_return"]) for item in items]
        if len(items) >= 5 and len(set(scores)) > 1 and len(set(returns)) > 1:
            correlations.append(float(spearmanr(scores, returns).statistic))
    regimes: dict[str, list[Mapping[str, Any]]] = {
        "UP_COHORT_MOMENTUM_20": [],
        "NONPOSITIVE_COHORT_MOMENTUM_20": [],
    }
    missing_regime = 0
    for item in outcomes:
        vector = forecasts[item["forecast_id"]]["vector"]
        if len(vector) != len(FEATURE_NAMES):
            missing_regime += 1
            continue
        feature = vector[17]
        regimes[
            "UP_COHORT_MOMENTUM_20" if feature > 0 else "NONPOSITIVE_COHORT_MOMENTUM_20"
        ].append(item)
    stability = {}
    for name, items in regimes.items():
        candidate = balanced(items, "score")
        baselines = [
            balanced(items, field)
            for field in (
                "baseline_majority_score",
                "baseline_momentum_score",
                "baseline_mean_reversion_score",
            )
        ]
        regime_dates = {
            _at(forecasts[item["forecast_id"]]["recorded_at"]).astimezone(IST).date().isoformat()
            for item in items
        }
        stability[name] = {
            "dates": len(regime_dates),
            "outcomes": len(items),
            "positive_both_baseline_improvements": len(regime_dates) >= 20
            and candidate is not None
            and all(value is not None and candidate > value for value in baselines),
        }
    return {
        "date_block_bootstrap_improvement_intervals": intervals,
        "bootstrap_block_dates": 20,
        "bootstrap_draws": 1000,
        "bootstrap_seed": 42,
        "simultaneous_baseline_comparisons": 3,
        "family_confidence": 0.95,
        "mean_date_rank_ic": sum(correlations) / len(correlations) if correlations else None,
        "rank_ic_dates": len(correlations),
        "by_market_regime": stability,
        "missing_registered_cohort_regime_outcomes": missing_regime,
        "positive_cross_regime_stability": missing_regime == 0
        and all(item["positive_both_baseline_improvements"] for item in stability.values()),
        "calibration_independently_reviewed": False,
        "limitations": (
            "Date blocks preserve overlap; intervals do not cure cohort/action/vintage bias."
        ),
    }
