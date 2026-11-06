"""Independent immutable actual-time forecasts, never original accepted ML records."""

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

from alphalens_api.auth.permissions import restrict, verify

from .features import FAMILY, FEATURE_NAMES, FEATURE_VERSION, HORIZON, TARGET_VERSION, candle

IST = ZoneInfo("Asia/Kolkata")
VERSION = "experimental.nse.prospective.v1"


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
    path = root / "experimental-prospective.sqlite3"
    if root.is_symlink() or path.is_symlink():
        raise ValueError("PROSPECTIVE_SYMLINK_FORBIDDEN")
    root.mkdir(parents=True, exist_ok=True)
    restrict(root)
    verify(root)
    if not path.exists():
        with sqlite3.connect(path) as initializing:
            schema = Path(__file__).resolve().parents[2] / "db/experimental-nse.sql"
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


def append_forecasts(
    root: Path,
    model_id: str,
    dataset_id: str,
    scores: Sequence[Mapping[str, Any]],
    source_observed_at: str | datetime,
) -> dict[str, Any]:
    """Record real runtime only. No supplied historical decision clock is accepted.

    Duplicate model/key/observation is an idempotent replay only if all immutable
    inputs agree. A changed model or source snapshot requires a new model/version;
    the old forecast is never replaced. This does not run retrospective evaluation.
    """
    model_id, dataset_id = _identifier(model_id), _identifier(dataset_id)
    now, observed = _utc_now(), _at(source_observed_at)
    if observed > now:
        raise ValueError("SOURCE_RETRIEVAL_AFTER_FORECAST")
    if len(scores) > 100:
        raise ValueError("PROSPECTIVE_COHORT_LIMIT")
    prepared = []
    for score in scores:
        if any(key in score for key in ("decision_at", "recorded_at", "forecast_at")):
            raise ValueError("CALLER_FORECAST_CLOCK_FORBIDDEN")
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
        if (
            not isinstance(vector, (list, tuple))
            or len(vector) != len(FEATURE_NAMES)
            or any(isinstance(v, bool) or not isinstance(v, (float, int)) for v in vector)
            or not all(math.isfinite(v) for v in vector)
        ):
            raise ValueError("COMPLETE_FINITE_FEATURE_VECTOR_REQUIRED")
        names = tuple(score.get("feature_names", FEATURE_NAMES))
        if (
            names != FEATURE_NAMES
            or score.get("feature_version", FEATURE_VERSION) != FEATURE_VERSION
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
        local_now = now.astimezone(IST)
        eligible = (day == local_now.date() and local_now.time() >= time(16)) or (
            day < local_now.date() and local_now.time() < time(9, 15)
        )
        baselines: dict[str, float | None] = {}
        for field in ("baseline_majority_score", "baseline_momentum_score"):
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
            "key": key,
            "symbol": symbol,
            "session": session,
            "score": float(value),
            "score_classification": "UNCALIBRATED_MODEL_SCORE",
            "vector": frozen_vector,
            "feature_names": list(names),
            "feature_version": FEATURE_VERSION,
            "feature_hash": vector_hash,
            "source": score.get("source", "UPSTOX_AUTHENTICATED_HISTORICAL_V3"),
            "source_sha256": score.get("source_sha256"),
            "source_observed_at": observed.isoformat(),
            "inference_at": inference_at.isoformat(),
            "recorded_at": now.isoformat(),
            "horizon": HORIZON,
            "target_version": TARGET_VERSION,
            "accepted_ml": False,
            "classification": "EXPERIMENTAL_UNVALIDATED_RESEARCH",
            "prospective_eligible": eligible,
            "prospective_eligibility_reason": (
                "BEFORE_FULL_TARGET_REGULAR_SESSION_OPEN_FUTURE_GRID_STILL_REQUIRED"
                if eligible
                else "FULL_FUTURE_SESSION_TARGET_NOT_PROVEN_AFTER_ACTUAL_DECISION"
            ),
            "regular_session_open_assumption": (
                "09:15 Asia/Kolkata; special sessions require separate review"
            ),
            **baselines,
        }
        prepared.append(body)
    inserted, replayed, identities = 0, 0, []
    with _connection(root, write=True) as connection:
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
    counts = {"inserted": 0, "replayed": 0, "pending": 0, "ineligible": 0, "corrections": 0}
    with _connection(root, write=True) as connection:
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
            if (
                required
                and datetime.combine(date.fromisoformat(required[0]), time(9, 15), IST) <= recorded
            ):
                counts["ineligible"] += 1
                continue
            if len(required) != HORIZON or any(
                (forecast["key"], session) not in observed for session in required
            ):
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
            exact = Fraction(1)
            inputs = []
            for item in selected:
                exact *= Fraction(item.close) / Fraction(item.open)
                inputs.append(
                    {"session": item.session, "open": str(item.open), "close": str(item.close)}
                )
            target_return = exact - 1
            inputs_hash = _hash(inputs)
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
                "forecast_id": row["id"],
                "revision": revision,
                "inputs": inputs,
                "inputs_hash": inputs_hash,
                "target_return": str(
                    Decimal(target_return.numerator) / Decimal(target_return.denominator)
                ),
                "target_return_numerator": str(target_return.numerator),
                "target_return_denominator": str(target_return.denominator),
                "target": int(target_return > 0),
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
    first = [body for body in checked if body["revision"] == 1]
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
            for field in ("baseline_majority_score", "baseline_momentum_score")
        },
        "by_target_month": {
            month: measurements(
                "score", [body for body in first if body["target_session"].startswith(month)]
            )
            for month in sorted({body["target_session"][:7] for body in first})
        },
    }
    return {
        "version": VERSION,
        "classification": "EXPERIMENTAL_UNVALIDATED_RESEARCH",
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
        "pending_outcome_count": eligible_count - len(first),
        "outcome_revision_count": len(checked),
        "correction_count": len(checked) - len(first),
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
            "Full daytime target must begin after the actual decision, before 09:15 regular open.",
            "Special-session open assumptions require separate review before prospective use.",
            "Observed cohort dates are not a certified complete NSE calendar.",
            "Scores are uncalibrated; outcomes are daytime movement, not economic profit.",
            "Metrics use first frozen outcomes; later source corrections are separate revisions.",
        ],
    }
