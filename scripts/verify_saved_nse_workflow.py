"""Read-only numerical replay of saved candles/models; never a new forecast."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import encoded, write_new
from workers.experimental_nse_v2 import models, pipeline
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES, build
from workers.nse_market import engine, forward_cohort

from alphalens_api import nse_evaluation


def numerical_replay(
    view: dict[str, Any], scores: dict[str, Any], model: dict[str, Any]
) -> dict[str, Any]:
    """Check only already-scored keys; this cannot recertify eligibility or clocks."""
    if (
        scores["model_id"] != model["model_id"]
        or scores["feature_version"] != model["feature_version"]
        or tuple(model["feature_names"]) != LOCAL_FEATURE_NAMES
        or view["provider_requests"] != 0
    ):
        raise ValueError("SAVED_MODEL_FEATURE_LINEAGE_MISMATCH")
    day = scores["observation_session"]
    candidates = scores["candidates"]
    if len({row["key"] for row in candidates}) != len(candidates):
        raise ValueError("UNIQUE_SAVED_CANDIDATES_REQUIRED")
    sessions = sorted(
        {
            row["session"]
            for rows in view["histories"].values()
            for row in rows
            if row["session"] <= day
        }
    )[-61:]
    if len(sessions) != 61 or sessions[-1] != day:
        raise ValueError("COMPLETE_BOUNDED_SAVED_SESSION_GRID_REQUIRED")
    selected = set(sessions)
    rows = []
    for candidate in candidates:
        if (
            candidate["session"] != day
            or candidate["source"] != "UPSTOX_OFFICIAL_HISTORICAL_CANDLES"
            or candidate["model_id"] != model["model_id"]
            or candidate["protocol_id"] != model["protocol_id"]
            or candidate["target_version"] != model["target_version"]
            or tuple(candidate["feature_names"]) != LOCAL_FEATURE_NAMES
        ):
            raise ValueError("SAVED_CANDIDATE_SOURCE_TARGET_LINEAGE_MISMATCH")
        for row in view["histories"].get(candidate["key"], []):
            if row["session"] in selected and all(
                row[field] is not None for field in ("open", "high", "low", "close", "volume")
            ):
                rows.append({**row, "key": candidate["key"], "symbol": candidate["symbol"]})
    features = build(rows, sessions, include_context=False)
    latest = {sample.key: sample for sample in features.samples if sample.session == day}
    failures = []
    max_vector_error = max_score_error = 0.0
    for candidate in candidates:
        sample = latest.get(candidate["key"])
        if sample is None:
            failures.append({"key": candidate["key"], "reason": "REPLAY_FEATURES_UNAVAILABLE"})
            continue
        vector = candidate["features"]
        if len(vector) != len(sample.vector):
            raise ValueError("SAVED_FEATURE_VECTOR_WIDTH_MISMATCH")
        vector_error = max(abs(a - b) for a, b in zip(sample.vector, vector, strict=True))
        value, _ = models.predict_vector(model, sample.vector)
        score_error = abs(value - candidate["score"])
        max_vector_error = max(max_vector_error, vector_error)
        max_score_error = max(max_score_error, score_error)
        if not math.isfinite(vector_error + score_error) or max(vector_error, score_error) > 1e-12:
            failures.append({"key": candidate["key"], "reason": "SAVED_NUMERICAL_REPLAY_MISMATCH"})
    eligible = []
    for candidate in candidates:
        sd = candidate["risk"]["return_daily_sd_20"]
        if type(sd) not in {int, float} or not math.isfinite(sd) or sd < 0:
            continue
        eligible.append({"key": candidate["key"], "value": candidate["score"] - sd})
    ranked = sorted(eligible, key=lambda row: (-row["value"], row["key"]))
    return {
        "state": "REPLAY_VERIFIED" if not failures else "REPLAY_MISMATCH",
        "observation_session": day,
        "session_slots": len(sessions),
        "saved_candidates": len(candidates),
        "regenerated_latest_vectors": len(latest),
        "maximum_feature_absolute_error": max_vector_error,
        "maximum_score_absolute_error": max_score_error,
        "tolerance": 1e-12,
        "failures": failures,
        "risk_ordering_policy": "model_score - daily_return_sd; weight 1 engineering assumption",
        "replayed_saved_top_n": {
            str(count): [row["key"] for row in ranked[:count]] for count in (5, 10, 20)
        },
    }


def verify(root: Path, v2_root: Path) -> dict[str, Any]:
    at = datetime.now(UTC)
    view = engine._pointed(root, "market-view-latest.json")
    scores = engine._pointed(root, "scores-latest.json")
    evaluation = pipeline.verified(v2_root / "price-only/evaluation.json")
    model = models.load_model(v2_root / "price-only/model.json", evaluation["model_sha256"])
    if model["model_id"] != evaluation["model_id"]:
        raise ValueError("PINNED_EVALUATION_MODEL_MISMATCH")
    result = numerical_replay(view, scores, model)
    selected = result["replayed_saved_top_n"]["20"]
    histories = [forward_cohort.stock_history(root, v2_root, key, limit=100) for key in selected]
    candidates = {row["key"]: row for row in scores["candidates"]}
    lineage_matches = 0
    for history in histories:
        candidate = candidates[history["key"]]
        if any(
            all(
                entry["forecast"].get(field) == candidate.get(field)
                for field in (
                    "model_id",
                    "key",
                    "session",
                    "target_version",
                    "source_sha256",
                    "feature_hash",
                    "score",
                )
            )
            for entry in history["rows"]
        ):
            lineage_matches += 1
    outcomes = nse_evaluation.read(root, v2_root, at=at)
    return {
        "classification": "SAVED_NUMERICAL_REPLAY_NOT_NEW_FORECAST_OR_ACCEPTANCE",
        "observed_at": at.isoformat(),
        "provider_requests": 0,
        "new_forecasts": 0,
        "outcome_writes": 0,
        "model_fits": 0,
        "accepted_rankings": 0,
        "source_view_sha256": hashlib.sha256(encoded(view)).hexdigest(),
        "score_snapshot_sha256": hashlib.sha256(encoded(scores)).hexdigest(),
        "model_sha256": evaluation["model_sha256"],
        "numerical_replay": result,
        "history": {
            "checked_top_securities": len(histories),
            "all_have_saved_history": all(row["unique_decisions"] > 0 for row in histories),
            "source_feature_target_lineage_matches": lineage_matches,
            "all_selected_lineage_matches": lineage_matches == len(histories),
            "matured_outcomes": sum(row["matured_outcomes"] for row in histories),
        },
        "outcome_evaluation": {key: value for key, value in outcomes.items() if key != "rows"},
        "limitations": [
            "Replays dated saved scores, never backdates a new decision clock.",
            "Numerical compatibility does not recertify action/calendar/current-source gates.",
            "The derived market view may omit original feature action exclusions.",
            "Raw source/feature/target matches are checked against saved Top-20 forecast bodies.",
            "Risk ordering is an unvalidated assumption, not an accepted recommendation.",
            "No live request, outcome reconciliation, forecast append or model fit occurred.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--v2-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    private_reports = args.v2_root.resolve().parent / "completion"
    if args.output.resolve().drive.casefold() != "d:" or not args.output.resolve().is_relative_to(
        private_reports
    ):
        raise ValueError("PRIVATE_D_DRIVE_REPORT_REQUIRED")
    report = verify(args.root, args.v2_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_new(args.output, encoded(report))
    print(json.dumps({"state": report["numerical_replay"]["state"], "output": str(args.output)}))
    if report["numerical_replay"]["state"] != "REPLAY_VERIFIED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
