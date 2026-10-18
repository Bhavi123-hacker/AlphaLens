"""Immutable global cohort selection and genuine outcome aggregation across shards."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scipy.stats import spearmanr

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
