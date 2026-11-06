"""Saved-prediction economic attribution and four registered sparse-entry policies.

No network, estimator loading, fitting, future forecasts or accepted publication.
All outputs remain known-period development price-reference research.
"""

from __future__ import annotations

import argparse
import math
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from workers.experimental_nse.acquire import digest, initialize
from workers.nse_market import engine

PROTOCOL = Path("docs/development/investment-frequency-v1-registered-protocol.md")
FAMILY = "ALPHALENS_INVESTMENT_FREQUENCY_V1"
MODELS = ("LSTM", "XGBOOST")
BASELINES = ("mean_reversion", "equal_cohort")
POLICIES = tuple((model, spacing) for model in MODELS for spacing in (10, 20))
COSTS = (25, 50, 100)
SEED = 1729


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Reject duplicates, missing outcomes, nonfinite scores and mixed clocks."""
    days: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        identity = (row["decision_session"], row["key"])
        decision, exit_day = (
            date.fromisoformat(row[name]) for name in ("decision_session", "target_session")
        )
        outcome = row["actual_price_component_return"]
        if (
            identity in seen
            or not row["key"].startswith("NSE_EQ|INE")
            or decision >= exit_day
            or not math.isfinite(outcome)
            or outcome <= -1
            or row["actual_positive"] != int(outcome > 0)
            or row["classification"] != "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE"
            or any(not math.isfinite(row["scores"][model]) for model in (*MODELS, "mean_reversion"))
        ):
            raise ValueError("ECONOMIC_SAVED_INPUT_REJECTED")
        seen.add(identity)
        days.setdefault(identity[0], []).append(row)
    if not days:
        raise ValueError("ECONOMIC_SAVED_INPUT_EMPTY")
    for cohort in days.values():
        if len({item["target_session"] for item in cohort}) != 1:
            raise ValueError("ECONOMIC_COMMON_TARGET_CLOCK_REQUIRED")
    return days


def references(
    days: dict[str, list[dict[str, Any]]], model: str, spacing: int
) -> list[dict[str, Any]]:
    """Same five-session holdings; explicit cash gaps, never extended labels."""
    if model not in (*MODELS, *BASELINES) or spacing not in (5, 10, 20):
        raise ValueError("REGISTERED_ECONOMIC_RULE_REQUIRED")
    selected_days = sorted(days)[::spacing]
    output: list[dict[str, Any]] = []
    previous: set[str] = set()
    previous_exit: str | None = None
    for day in selected_days:
        if previous_exit is not None and previous_exit > day:
            raise ValueError("ECONOMIC_REFERENCE_HORIZONS_OVERLAP")
        cohort = days[day]
        selected = (
            sorted(cohort, key=lambda row: row["key"])
            if model == "equal_cohort"
            else sorted(cohort, key=lambda row: (-row["scores"][model], row["key"]))[:5]
        )
        keys = {item["key"] for item in selected}
        output.append(
            {
                "decision_session": day,
                "exit_session": selected[0]["target_session"],
                "eligible_count": len(cohort),
                "selected_count": len(selected),
                "gross_return": math.fsum(
                    item["actual_price_component_return"] for item in selected
                )
                / len(selected),
                "membership_turnover": len(keys - previous) / len(keys),
                "equal_weight_concentration_hhi": 1 / len(keys),
            }
        )
        previous, previous_exit = keys, selected[0]["target_session"]
    return output


def compound(path: list[dict[str, Any]], cost_bps: int = 50) -> dict[str, Any]:
    """Endpoint wealth and exact telescoping log-cost attribution, not fills."""
    if cost_bps not in COSTS or not path:
        raise ValueError("REGISTERED_ECONOMIC_COST_AND_NONEMPTY_PATH_REQUIRED")
    gross = cost_only = net = peak = 1.0
    drawdown = 0.0
    years: dict[str, dict[str, Any]] = {}
    curve = []
    cost = cost_bps / 10000
    slippage = 10 / 10000
    for point in path:
        movement = point["gross_return"]
        if not math.isfinite(movement) or 1 + movement - cost - slippage <= 0:
            raise ValueError("ECONOMIC_REFERENCE_INSOLVENCY_OR_NONFINITE")
        gross *= 1 + movement
        cost_only *= 1 + movement - cost
        net *= 1 + movement - cost - slippage
        peak = max(peak, net)
        drawdown = min(drawdown, net / peak - 1)
        year = point["exit_session"][:4]
        period = years.setdefault(year, {"decisions": 0, "gross_wealth": 1.0, "net_wealth": 1.0})
        period["decisions"] += 1
        period["gross_wealth"] *= 1 + movement
        period["net_wealth"] *= 1 + movement - cost - slippage
        curve.append(
            {
                "session": point["exit_session"],
                "gross_equity": gross,
                "cost_only_equity": cost_only,
                "net_equity": net,
                "endpoint_drawdown": net / peak - 1,
            }
        )
    return {
        "round_trip_cost_bps": cost_bps,
        "slippage_bps_each_side": 5,
        "decision_count": len(path),
        "gross_compounded_reference_return": gross - 1,
        "net_compounded_reference_return": net - 1,
        "cost_only_compounded_reference_return": cost_only - 1,
        "gross_to_net_wealth_drag_percentage_points": (gross - net) * 100,
        "gross_log_wealth": math.log(gross),
        "cost_log_wealth_drag": math.log(gross) - math.log(cost_only),
        "slippage_log_wealth_drag": math.log(cost_only) - math.log(net),
        "net_log_wealth": math.log(net),
        "maximum_endpoint_drawdown": drawdown,
        "mean_membership_turnover": float(np.mean([p["membership_turnover"] for p in path])),
        "mean_equal_weight_concentration_hhi": float(
            np.mean([p["equal_weight_concentration_hhi"] for p in path])
        ),
        "losing_gross_references": sum(p["gross_return"] < 0 for p in path),
        "losing_net_references": sum(p["gross_return"] - cost - slippage < 0 for p in path),
        "calendar_years": {
            year: {
                "decisions": data["decisions"],
                "gross_return": data["gross_wealth"] - 1,
                "net_return": data["net_wealth"] - 1,
            }
            for year, data in sorted(years.items())
        },
        "curve": curve,
    }


def paired(path: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> dict[str, Any]:
    """Matched dates, shared cost, whole decision blocks; no independent claim."""
    if [p["decision_session"] for p in path] != [p["decision_session"] for p in baseline]:
        raise ValueError("ECONOMIC_PAIRED_DATES_REQUIRED")
    differences = np.array(
        [a["gross_return"] - b["gross_return"] for a, b in zip(path, baseline, strict=True)]
    )
    rng = np.random.default_rng(SEED)
    block = min(4, len(differences))
    bootstrap = []
    for _ in range(500):
        starts = rng.integers(0, len(differences) - block + 1, math.ceil(len(differences) / block))
        indices = np.concatenate([np.arange(start, start + block) for start in starts])[
            : len(differences)
        ]
        bootstrap.append(float(np.mean(differences[indices])))
    return {
        "mean_net_reference_return_difference": float(np.mean(differences)),
        "paired_mean_difference_95_interval": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
        "method": "PAIRED_FOUR_DECISION_MOVING_BLOCK_500_SEED1729",
        "costs_cancel_in_paired_mean_under_SAME_FULL_ROUND_TRIP_ASSUMPTION": True,
        "independent_confirmation": False,
        "multiple_comparison_adjustment": "NONE_EXPLORATORY_FOUR_POLICIES_TWO_COMPARATORS",
    }


def analyze(history: dict[str, Any], original: dict[str, Any]) -> dict[str, Any]:
    """Fixed audit and four policies. Caller must register protocol before running."""
    if (
        history["dataset_id"] != original["dataset_id"]
        or history["model_sha256"] != original["model_sha256"]
    ):
        raise ValueError("ECONOMIC_DATASET_MODEL_ALIGNMENT_REQUIRED")
    days = validate_rows(history["rows"])
    audit = {}
    for model in (*MODELS, *BASELINES):
        path = references(days, model, 5)
        summary = compound(path)
        old_strategy = "equal_cohort" if model == "equal_cohort" else "top5"
        old_model = "LSTM" if model == "equal_cohort" else model
        old = original["comparisons"][old_model]["economic_sensitivity"]["strategies"][
            old_strategy
        ]["scenarios"][1]
        for name in (
            "gross_compounded_reference_return",
            "net_compounded_reference_return",
            "maximum_endpoint_drawdown",
        ):
            if not math.isclose(summary[name], old[name], rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError("ORIGINAL_ECONOMIC_REPRODUCTION_FAILED")
        audit[model] = summary
    policies = []
    for model, spacing in POLICIES:
        path = references(days, model, spacing)
        comparisons = {}
        for baseline in BASELINES:
            reference = references(days, baseline, spacing)
            comparisons[baseline] = {
                "summary": compound(reference),
                "paired": paired(path, reference),
            }
        policies.append(
            {
                "policy_id": f"{model}_TOP5_FIVE_SESSION_HOLD_START_EVERY_{spacing}_DATES",
                "model": model,
                "decision_spacing": spacing,
                "holding_sessions": 5,
                "approximate_active_session_fraction": 5 / spacing,
                "cash_gap_return_assumption": 0,
                "scenarios": [compound(path, cost) for cost in COSTS],
                "comparisons": comparisons,
                "accepted": False,
            }
        )
    return {
        "family": FAMILY,
        "classification": "BACKTESTED_UNCONFIRMED",
        "evidence_state": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
        "historical_prediction_count": len(history["rows"]),
        "decision_dates": len(days),
        "security_count": len({r["key"] for r in history["rows"]}),
        "period": {"start": min(days), "end": max(days)},
        "original_result_reproduced": True,
        "original_five_date_attribution": audit,
        "policy_count": len(policies),
        "policies": policies,
        "edge_status": "NO_INDEPENDENTLY_DEMONSTRATED_EDGE",
        "new_model_fits": 0,
        "provider_requests": 0,
        "prospective_forecasts_created": 0,
        "accepted_rankings": 0,
        "limitations": [
            "Known-period current-fixed-cohort retrospective selection; survivorship limitation",
            "Final-vintage publication assumption, incomplete corporate-action history",
            "Price-component endpoints, no dividends or actual broker fills",
            "Endpoint drawdown excludes intervening mark-to-market losses",
            "Sparse five-session holdings with zero-return cash gaps, not10/20holding targets",
            "Full round trips charged even when consecutive selections contain same names",
            "No qualified independent NSE index, actual spreads, fill capacity or tax schedule",
            "Exploratory four-policy research with no untouched independent outcomes",
        ],
    }


def run(root: Path, source: Path) -> dict[str, Any]:
    initialize(root)
    if (root / "attempt.json").exists() or (root / "report.json").exists():
        raise ValueError("ECONOMIC_IMMUTABLE_ATTEMPT_EXISTS")
    protocol = digest(PROTOCOL.read_bytes())
    history_path, report_path = source / "historical-predictions.json", source / "report-final.json"
    history, original = engine._read(history_path), engine._read(report_path)
    sources = {path.name: digest(path.read_bytes()) for path in (history_path, report_path)}
    engine._checked(
        root / "attempt.json",
        {
            "family": FAMILY,
            "protocol_sha256": protocol,
            "inputs": sources,
            "started_at": datetime.now(UTC).isoformat(),
        },
    )
    result = analyze(history, original)
    result.update(
        {
            "inputs": sources,
            "protocol_sha256": protocol,
            "completed_at": datetime.now(UTC).isoformat(),
            "dataset_id": history["dataset_id"],
            "model_sha256": history["model_sha256"],
        }
    )
    if any(digest(path.read_bytes()) != sources[path.name] for path in (history_path, report_path)):
        raise ValueError("ECONOMIC_SOURCE_CHANGED_DURING_ANALYSIS")
    engine._checked(root / "report.json", result)
    return {
        "family": FAMILY,
        "policy_count": result["policy_count"],
        "source_requests": 0,
        "edge_status": result["edge_status"],
        "report_sha256": digest((root / "report.json").read_bytes()),
    }


def load(root: Path) -> dict[str, Any]:
    """Read a bounded pinned saved report; never recompute analysis on API GET."""
    path = root / "report.json"
    if path.stat().st_size > 1_000_000:
        raise ValueError("ECONOMIC_REPORT_SIZE_REJECTED")
    value, attempt = engine._read(path), engine._read(root / "attempt.json")
    if (
        value["family"] != FAMILY
        or value["protocol_sha256"] != digest(PROTOCOL.read_bytes())
        or value["protocol_sha256"] != attempt["protocol_sha256"]
        or value["inputs"] != attempt["inputs"]
        or value["policy_count"] != 4
        or value["new_model_fits"] != 0
        or value["provider_requests"] != 0
        or value["prospective_forecasts_created"] != 0
        or value["accepted_rankings"] != 0
        or value["edge_status"] != "NO_INDEPENDENTLY_DEMONSTRATED_EDGE"
        or [(p["model"], p["decision_spacing"]) for p in value["policies"]] != list(POLICIES)
        or any(
            p["holding_sessions"] != 5
            or p["accepted"]
            or [s["round_trip_cost_bps"] for s in p["scenarios"]] != list(COSTS)
            or set(p["comparisons"]) != set(BASELINES)
            or any(s["slippage_bps_each_side"] != 5 for s in p["scenarios"])
            for p in value["policies"]
        )
    ):
        raise ValueError("REGISTERED_ECONOMIC_SAVED_REPORT_REQUIRED")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    print(__import__("json").dumps(run(args.root, args.source), sort_keys=True))


if __name__ == "__main__":
    main()
