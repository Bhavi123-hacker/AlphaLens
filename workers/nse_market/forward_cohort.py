"""Immutable global cohort selection and genuine outcome aggregation across shards."""

from __future__ import annotations

import math
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scipy.stats import spearmanr

from alphalens_api.auth.permissions import verify
from workers.experimental_nse.acquire import digest, encoded, initialize, private_path
from workers.experimental_nse_v2 import forward
from workers.nse_market import engine
from workers.providers.daily_clock import guard

PROTOCOL = (
    Path(__file__).resolve().parents[2] / "docs/development/nse-expanded-forward-protocol-v1.md"
)
# The exact digest is populated when registering this new protocol before use.
PROTOCOL_SHA256 = "73c7f89c38b2e5cfd06b605a8ecc627a1739bf37a1a090dd1369f70b5801b6d4"
BASELINES = (
    "score",
    "baseline_majority_score",
    "baseline_momentum_score",
    "baseline_mean_reversion_score",
    "baseline_risk_score",
)


def stock_history(root: Path, v2_root: Path, key: str, limit: int = 50) -> dict[str, Any]:
    """Read existing security ledgers only; never initialize a missing database.

    Original and expanded forecasts may overlap. Aggregate counts use unique
    model/key/observation decisions, while rows retain each store's exact record.
    This reader neither reconciles outcomes nor creates prospective evidence.
    """
    if not re.fullmatch(r"NSE_EQ\|INE[A-Z0-9]{9}", key):
        raise ValueError("EXACT_NSE_COMMON_EQUITY_KEY_REQUIRED")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("BOUNDED_SECURITY_HISTORY_LIMIT_REQUIRED")
    now = datetime.now(UTC)
    stores = (
        ("original", v2_root / "price-only"),
        ("expanded", root / "expanded-forecasts" / digest(key.encode())[:2]),
    )
    entries: list[dict[str, Any]] = []
    counts = {"original": 0, "expanded": 0}
    future_forecasts, future_outcomes = 0, 0
    decisions: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for store, folder in stores:
        path = folder / "experimental-v2-prospective.sqlite3"
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("PROSPECTIVE_SYMLINK_FORBIDDEN")
        if not path.exists():
            continue
        verify(folder)
        verify(path, directory=False)
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            # A stable read transaction keeps forecast and outcome revisions aligned.
            connection.execute("BEGIN")
            for row in connection.execute(
                "SELECT * FROM experimental_forecasts WHERE instrument_key=? "
                "ORDER BY recorded_at DESC,id",
                (key,),
            ):
                forecast = forward._verified(row)
                recorded = forward._at(forecast["recorded_at"])
                if recorded > now or forward._at(forecast["source_observed_at"]) > recorded:
                    future_forecasts += 1
                    continue
                outcome_row = connection.execute(
                    "SELECT * FROM experimental_outcomes WHERE forecast_id=? "
                    "ORDER BY revision DESC LIMIT 1",
                    (row["id"],),
                ).fetchone()
                outcome = forward._verified(outcome_row) if outcome_row else None
                if outcome is not None and (
                    forward._at(outcome["recorded_at"]) > now
                    or forward._at(outcome["source_observed_at"]) > now
                    or forward._at(outcome["source_observed_at"])
                    > forward._at(outcome["recorded_at"])
                    or forward._at(outcome["recorded_at"]) < recorded
                    or (
                        forecast.get("next_session_timing") is not None
                        and forward._at(forecast["next_session_timing"]["open_at"]) > now
                    )
                    or outcome["target_session"]
                    >= forward._at(outcome["source_observed_at"])
                    .astimezone(forward.IST)
                    .date()
                    .isoformat()
                ):
                    future_outcomes += 1
                    outcome = None
                entry = {
                    "store": store,
                    "forecast_id": row["id"],
                    "forecast": forecast,
                    "outcome": outcome,
                }
                entries.append(entry)
                counts[store] += 1
                decision = (forecast["model_id"], forecast["key"], forecast["session"])
                decisions.setdefault(decision, []).append(entry)
        finally:
            connection.close()
    matured, pending, excluded, conflicts = 0, 0, 0, 0
    for group in decisions.values():
        outcomes = [
            item["outcome"]
            for item in group
            if item["outcome"] is not None and item["forecast"].get("prospective_eligible") is True
        ]
        signatures = {
            (outcome["status"], outcome.get("target_return"), outcome.get("target"))
            for outcome in outcomes
        }
        if len(signatures) > 1:
            conflicts += 1
            pending += 1
        elif outcomes and outcomes[0]["status"] == "MATURED_PRICE_REFERENCE_RETURN":
            matured += 1
        elif outcomes:
            excluded += 1
        else:
            pending += 1
    entries.sort(
        key=lambda item: (item["forecast"]["recorded_at"], item["forecast_id"]), reverse=True
    )
    return {
        "key": key,
        "classification": "EXISTING_IMMUTABLE_EXPERIMENTAL_FORECAST_HISTORY",
        "forecast_count": len(decisions),
        "unique_decisions": len(decisions),
        "raw_forecast_records": len(entries),
        "matured_outcomes": matured,
        "pending_forecasts": pending,
        "excluded_outcomes": excluded,
        "overlapping_outcome_conflicts": conflicts,
        "original_forecasts": counts["original"],
        "expanded_forecasts": counts["expanded"],
        "future_forecast_records_ignored": future_forecasts,
        "future_outcome_records_ignored": future_outcomes,
        "rows": entries[:limit],
        "history_limit": limit,
        "history_truncated": len(entries) > limit,
        "accepted_ml": False,
    }


def protocol_id() -> str:
    actual = digest(PROTOCOL.read_bytes())
    if actual != PROTOCOL_SHA256:
        raise ValueError("EXPANDED_FORWARD_REGISTERED_PROTOCOL_CHANGED")
    return actual


def _forecasts(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    forecasts: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}
    for folder in sorted(private_path(root, "expanded-forecasts").glob("*")):
        if not (folder / "experimental-v2-prospective.sqlite3").exists():
            continue
        with forward._connection(folder) as connection:
            for row in connection.execute("SELECT * FROM experimental_forecasts"):
                body = forward._verified(row)
                forecasts[row["id"]] = body
            for row in connection.execute("SELECT * FROM experimental_outcomes ORDER BY revision"):
                body = forward._verified(row)
                outcomes[body["forecast_id"]] = body
    return forecasts, outcomes


def freeze_current(root: Path) -> dict[str, Any]:
    """No inference, acquisition, retrospective clock or original forecast update."""
    initialize(root)
    protocol = protocol_id()
    scores = engine._pointed(root, "scores-latest.json")
    snapshot_sha = digest(encoded(scores))
    folder = private_path(root, "global-cohorts")
    folder.mkdir(exist_ok=True)
    identity = digest(encoded({"protocol_id": protocol, "score_snapshot_sha256": snapshot_sha}))
    path = folder / (identity + ".json")
    if path.exists():
        return {**engine._read(path), "replayed": True}
    clock = guard()
    now = datetime.now(UTC)
    forecasts, _ = _forecasts(root)
    indexed = {
        (value["model_id"], value["key"], value["session"]): (key, value)
        for key, value in forecasts.items()
    }
    members = []
    for score in scores["candidates"]:
        if datetime.fromisoformat(score["entry_open_at"]) <= datetime.fromisoformat(
            clock["upper_at"]
        ):
            raise ValueError("EXPANDED_GLOBAL_DECLARATION_MUST_PRECEDE_FUTURE_ENTRY")
        if (
            not datetime.fromisoformat(score["source_observed_at"])
            <= datetime.fromisoformat(score["inference_at"])
            <= now
        ):
            raise ValueError("EXPANDED_GLOBAL_SCORE_CHRONOLOGY_REJECTED")
        located = indexed.get((score["model_id"], score["key"], score["session"]))
        if located is None:
            raise ValueError("IMMUTABLE_SECURITY_FORECAST_REQUIRED_BEFORE_GLOBAL_DECLARATION")
        forecast_id, forecast = located
        if (
            not forecast["prospective_eligible"]
            or forecast["feature_hash"] != score["feature_hash"]
            or forecast["source_sha256"] != score["source_sha256"]
        ):
            raise ValueError("GLOBAL_DECLARATION_FROZEN_SECURITY_INPUT_MISMATCH")
        member = {name: score[name] for name in BASELINES}
        if any(
            not isinstance(member[name], (int, float))
            or not math.isfinite(member[name])
            or not 0 <= member[name] <= 1
            for name in BASELINES
        ):
            raise ValueError("COMPLETE_FINITE_FROZEN_BASELINE_SCORES_REQUIRED")
        members.append(
            {
                **member,
                "key": score["key"],
                "symbol": score["symbol"],
                "feature_hash": score["feature_hash"],
                "source_sha256": score["source_sha256"],
                "forecast_id": forecast_id,
                "original_forecast_recorded_at": forecast["recorded_at"],
                "entry_session": score["entry_session"],
                "entry_open_at": score["entry_open_at"],
                "applicability": score["applicability"],
            }
        )
    if not members or len({item["key"] for item in members}) != len(members):
        raise ValueError("NONEMPTY_UNIQUE_ACTUAL_SCORED_GLOBAL_COHORT_REQUIRED")
    selection = {
        name: {
            str(count): [
                item["key"]
                for item in sorted(members, key=lambda item: (-item[name], item["key"]))[:count]
            ]
            for count in (5, 10, 20)
        }
        for name in BASELINES
    }
    value = {
        "declaration_id": identity,
        "protocol_id": protocol,
        "model_id": scores["model_id"],
        "model_sha256": scores["model_sha256"],
        "dataset_id": scores["dataset_id"],
        "feature_version": scores["feature_version"],
        "score_snapshot_sha256": snapshot_sha,
        "recorded_at": now.isoformat(),
        "decision_clock": clock,
        "observation_session": scores["observation_session"],
        "members": members,
        "frozen_selection": selection,
        "classification": "EXPERIMENTAL_UNVALIDATED",
        "accepted_ml": False,
        "independent_acceptance": False,
        "assumed_round_trip_and_slippage_cost": 0.0035,
    }
    engine._checked(path, value)
    engine._pointer(root, "global-cohort-latest.json", path)
    reconcile(root)
    return value


def _metrics(
    members: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]], field: str
) -> dict[str, Any]:
    targets = [int(outcomes[item["forecast_id"]]["target"]) for item in members]
    probabilities = [float(item[field]) for item in members]
    positive, negative = sum(targets), len(targets) - sum(targets)
    balanced = (
        (
            (
                sum(
                    score >= 0.5 and target == 1
                    for score, target in zip(probabilities, targets, strict=True)
                )
                / positive
                + sum(
                    score < 0.5 and target == 0
                    for score, target in zip(probabilities, targets, strict=True)
                )
                / negative
            )
            / 2
        )
        if positive and negative
        else None
    )
    returns = [float(outcomes[item["forecast_id"]]["target_return"]) for item in members]
    correlation = (
        float(spearmanr(probabilities, returns).statistic)
        if len(set(probabilities)) > 1 and len(set(returns)) > 1
        else None
    )
    return {
        "balanced_accuracy": balanced,
        "brier_score": sum(
            (score - target) ** 2 for score, target in zip(probabilities, targets, strict=True)
        )
        / len(targets),
        "rank_information_coefficient": correlation
        if correlation is None or math.isfinite(correlation)
        else None,
    }


def evaluate(declaration: dict[str, Any], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    members = declaration["members"]
    eligible = [
        item
        for item in members
        if outcomes.get(item["forecast_id"], {}).get("status") == "MATURED_PRICE_REFERENCE_RETURN"
    ]
    excluded = [
        item
        for item in members
        if item["forecast_id"] in outcomes
        and outcomes[item["forecast_id"]]["status"] != "MATURED_PRICE_REFERENCE_RETURN"
    ]
    result: dict[str, Any] = {
        "declaration_id": declaration["declaration_id"],
        "declared_securities": len(members),
        "matured_outcomes": len(eligible),
        "pending_outcomes": len(members) - len(eligible) - len(excluded),
        "excluded_outcomes": len(excluded),
        "global_metrics": None,
        "selection_returns": None,
        "status": "PENDING_COMPLETE_DECLARED_COHORT_OUTCOMES",
        "accepted_ml": False,
    }
    if len(eligible) != len(members):
        return result
    indexed = {item["key"]: item for item in members}
    full_return = sum(
        float(outcomes[item["forecast_id"]]["target_return"]) for item in members
    ) / len(members)
    selected: dict[str, dict[str, dict[str, Any]]] = {}
    for name, groups in declaration["frozen_selection"].items():
        selected[name] = {}
        for count, keys in groups.items():
            gross = sum(
                float(outcomes[indexed[key]["forecast_id"]]["target_return"]) for key in keys
            ) / len(keys)
            selected[name][count] = {
                "securities": len(keys),
                "gross_price_component_return": gross,
                "assumed_net_return": gross - declaration["assumed_round_trip_and_slippage_cost"],
                "equal_weight_declared_cohort_return": full_return,
                "gross_excess_vs_declared_cohort": gross - full_return,
                "actual_realized_profit": False,
            }
    result.update(
        status="COMPLETE_REFERENCE_PRICE_RESEARCH_NOT_INDEPENDENT_ACCEPTANCE",
        global_metrics={name: _metrics(members, outcomes, name) for name in BASELINES},
        selection_returns=selected,
    )
    return result


def summary(root: Path) -> dict[str, Any]:
    forecasts, outcomes = _forecasts(root)
    declarations = [
        engine._read(path) for path in sorted(private_path(root, "global-cohorts").glob("*.json"))
    ]
    for declaration in declarations:
        if declaration["protocol_id"] != protocol_id() or any(
            item["forecast_id"] not in forecasts for item in declaration["members"]
        ):
            raise ValueError("EXPANDED_GLOBAL_COHORT_PROTOCOL_OR_FORECAST_LINEAGE_REJECTED")
    results = [evaluate(declaration, outcomes) for declaration in declarations]
    return {
        "declarations": len(declarations),
        "unique_security_forecasts": len(forecasts),
        "matured_security_outcomes": sum(
            item["status"] == "MATURED_PRICE_REFERENCE_RETURN" for item in outcomes.values()
        ),
        "complete_global_declarations": sum(item["global_metrics"] is not None for item in results),
        "results": results,
        "accepted_current_rankings": 0,
        "independent_acceptance": False,
        "shard_rank_metrics_averaged": False,
    }


def reconcile(root: Path) -> dict[str, int]:
    """Append result revisions bound to exact immutable outcome versions."""
    _, outcomes = _forecasts(root)
    added, replayed = 0, 0
    for path in sorted(private_path(root, "global-cohorts").glob("*.json")):
        declaration = engine._read(path)
        if declaration["protocol_id"] != protocol_id():
            raise ValueError("EXPANDED_GLOBAL_REGISTERED_PROTOCOL_MISMATCH")
        inputs = {
            item["forecast_id"]: digest(encoded(outcomes[item["forecast_id"]]))
            for item in declaration["members"]
            if item["forecast_id"] in outcomes
        }
        identifier = digest(
            encoded({"declaration_id": declaration["declaration_id"], "outcome_inputs": inputs})
        )
        directory = private_path(root, "global-results", declaration["declaration_id"])
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (identifier + ".json")
        if target.exists():
            engine._read(target)
            replayed += 1
            continue
        value = {
            "result_id": identifier,
            "computed_at": datetime.now(UTC).isoformat(),
            "outcome_inputs": inputs,
            "result": evaluate(declaration, outcomes),
        }
        engine._checked(target, value)
        added += 1
    return {"global_result_versions_written": added, "global_result_versions_replayed": replayed}
