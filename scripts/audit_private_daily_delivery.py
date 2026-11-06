"""Read-only, compact daily-source/ML evidence report. No provider or clock calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def risk_ranked(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exact unfiltered five-session API/UI weight-one engineering ordering."""
    eligible = [
        row
        for row in candidates
        if isinstance(row.get("risk"), dict)
        and type(row["risk"].get("return_daily_sd_20")) in {int, float}
        and math.isfinite(row["risk"]["return_daily_sd_20"])
        and row["risk"]["return_daily_sd_20"] >= 0
    ]
    return sorted(
        eligible, key=lambda row: (-(row["score"] - row["risk"]["return_daily_sd_20"]), row["key"])
    )


def audit(root: Path, v2_root: Path | None = None) -> dict[str, Any]:
    def read(path: Path) -> dict[str, Any]:
        body = path.read_bytes()
        sidecar = path.with_suffix(path.suffix + ".sha256")
        if path.parent != root and not sidecar.exists():
            raise ValueError("DAILY_AUDIT_CHECKSUM_REQUIRED")
        if sidecar.exists() and sidecar.read_text().strip() != hashlib.sha256(body).hexdigest():
            raise ValueError("DAILY_AUDIT_CHECKSUM_REJECTED")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("DAILY_AUDIT_OBJECT_REQUIRED")
        return value

    def pointed(name: str) -> tuple[Path, dict[str, Any]]:
        path = (root / read(root / name)["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("DAILY_AUDIT_POINTER_ESCAPE_REJECTED")
        return path, read(path)

    summaries: list[dict[str, Any]] = []
    for path in sorted((root / "operational" / "runs").glob("*.done.json")):
        row = read(path)
        if row["started_at"] < "2026-10-26":
            continue
        outcome = row.get("outcome", {})
        summaries.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                **{
                    key: row.get(key)
                    for key in (
                        "run_id",
                        "launch_id",
                        "started_at",
                        "completed_at",
                        "state",
                        "error_code",
                        "source_requests_last_run",
                        "reserved_request_ceiling",
                        "worker_pid",
                        "scheduled",
                    )
                },
                "outcome": {
                    key: outcome.get(key)
                    for key in (
                        "session",
                        "new_daily_observations",
                        "accepted_session_securities",
                        "pending_securities",
                        "failures",
                        "dataset_id",
                        "market_view",
                        "scoring",
                        "reconciliation",
                    )
                },
            }
        )
    summaries.sort(key=lambda row: row["started_at"])
    launches = {row["launch_id"] for row in summaries}
    lifecycle = []
    for path in sorted((root / "operational" / "diagnostics").glob("*.json")):
        row = read(path)
        if row.get("launch_id") in launches:
            lifecycle.append(row)
    lifecycle.sort(key=lambda row: row["at"])
    score_path, scores = pointed("scores-latest.json")
    view_path, view = pointed("market-view-latest.json")
    candidates = scores.get("candidates", [])
    ranked = sorted(candidates, key=lambda row: (-float(row["score"]), row["key"]))
    ranking: dict[str, Any] = {
        "state": "PASS"
        if ranked == candidates and len({row["key"] for row in candidates}) == len(candidates)
        else "FAIL",
        "latest_observation_session": scores.get("observation_session"),
        "unique_instruments": len({row["key"] for row in candidates}),
        "top5_prefix_top10": ranked[:5] == ranked[:10][:5],
        "top10_prefix_top20": ranked[:10] == ranked[:20][:10],
        "method": "EXISTING_DESCENDING_MODEL_SCORE_STABLE_INSTRUMENT_KEY_TIEBREAK",
    }
    ui_ranked = risk_ranked(candidates)
    ranking["ui_risk_adjusted"] = {
        "method": "model_score - daily_return_sd; weight=1; stable instrument key tie break",
        "eligible_candidates": len(ui_ranked),
        "top5_prefix_top10": ui_ranked[:5] == ui_ranked[:10][:5],
        "top10_prefix_top20": ui_ranked[:10] == ui_ranked[:20][:10],
        "status": "ENGINEERING_ASSUMPTION_NOT_VALIDATED_EDGE",
    }
    older = []
    for path in (root / "scores").glob("*.json"):
        row = read(path)
        if row.get("observation_session", "") < scores.get("observation_session", ""):
            older.append(row)
    if older:
        prior = max(older, key=lambda row: (row["observation_session"], row["generated_at"]))
        before = [row["key"] for row in prior["candidates"][:20]]
        after = [row["key"] for row in ranked[:20]]
        ranking.update(
            prior_observation_session=prior["observation_session"],
            prior_scored_securities=len(prior["candidates"]),
            top20_positions_changed=sum(
                left != right for left, right in zip(before, after, strict=False)
            ),
            top20_snapshot_changed=before != after,
            top20_before_sha256=hashlib.sha256(json.dumps(before).encode()).hexdigest(),
            top20_after_sha256=hashlib.sha256(json.dumps(after).encode()).hexdigest(),
        )
        risk_before = [row["key"] for row in risk_ranked(prior["candidates"])[:20]]
        risk_after = [row["key"] for row in ui_ranked[:20]]
        ranking["ui_risk_adjusted"].update(
            top20_positions_changed=sum(
                left != right for left, right in zip(risk_before, risk_after, strict=False)
            ),
            top20_snapshot_changed=risk_before != risk_after,
            top20_before_sha256=hashlib.sha256(json.dumps(risk_before).encode()).hexdigest(),
            top20_after_sha256=hashlib.sha256(json.dumps(risk_after).encode()).hexdigest(),
        )
    sessions = {}
    requests: Counter[str] = Counter()
    for folder in sorted((root / "daily").iterdir()):
        if not folder.is_dir():
            continue
        records = list(folder.glob("*/record.json"))
        sessions[folder.name] = len(records)
        for path in folder.glob("*/response.json"):
            row = read(path)
            context = row.get("request_context", row.get("request", {})) or {}
            requests[str(context.get("operation", "NOT_RETAINED"))] += 1
    totals: Counter[str] = Counter()
    forecast_sessions: Counter[str] = Counter()
    decision_ids = set()
    for path in sorted((root / "expanded-forecasts").glob("*/experimental-v2-prospective.sqlite3")):
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM experimental_forecasts").fetchall()
            totals["forecast_records"] += len(rows)
            for row in rows:
                values = json.loads(row["body"])
                canonical = json.dumps(
                    values, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
                if hashlib.sha256(canonical).hexdigest() != row["id"]:
                    raise ValueError("DAILY_AUDIT_FORECAST_CHECKSUM_REJECTED")
                forecast_sessions[str(values.get("session", "UNKNOWN"))] += 1
                decision_ids.add((values.get("model_id"), values.get("key"), values.get("session")))
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "experimental_outcomes" in tables:
                totals["outcome_records"] += connection.execute(
                    "SELECT count(*) FROM experimental_outcomes"
                ).fetchone()[0]
    result = {
        "schema": "alphalens.private-daily-audit.v1",
        "audit_at": datetime.now(UTC).isoformat(),
        "provider_requests_by_this_audit": 0,
        "source_mutations_by_this_audit": 0,
        "scheduled_runs": summaries,
        "lifecycle": lifecycle,
        "accepted_daily_record_counts": sessions,
        "retained_response_operations": dict(requests),
        "ranking_replay": ranking,
        "latest_scores": {
            "path": str(score_path.relative_to(root)),
            "sha256": hashlib.sha256(score_path.read_bytes()).hexdigest(),
            "keys": sorted(scores),
            **{
                key: value
                for key, value in scores.items()
                if key
                in (
                    "dataset_id",
                    "model_id",
                    "model_sha256",
                    "generated_at",
                    "observation_session",
                    "source",
                    "forecast_horizon",
                    "classification",
                    "edge_status",
                    "new_forecasts",
                    "existing_forecasts_preserved",
                    "scored_securities",
                    "accepted_current_rankings",
                )
            },
            "score_count": len(scores.get("candidates", [])),
            "score_sessions": dict(
                Counter(str(row.get("session")) for row in scores.get("candidates", []))
            ),
        },
        "market_view": {
            "path": str(view_path.relative_to(root)),
            "sha256": hashlib.sha256(view_path.read_bytes()).hexdigest(),
            **{
                key: value
                for key, value in view.items()
                if key
                in (
                    "dataset_id",
                    "generated_at",
                    "latest_observed_session",
                    "source",
                    "state",
                )
            },
            "row_count": len(view.get("rows", [])),
            "history_count": len(view.get("histories", {})),
        },
        "ledger_totals": dict(totals),
        "unique_decisions": len(decision_ids),
        "forecast_sessions": dict(forecast_sessions),
    }
    if v2_root is not None:
        from workers.experimental_nse_v2 import models
        from workers.nse_market import engine

        model = models.load_model(v2_root / "price-only" / "model.json", scores["model_sha256"])
        frame = engine.snapshot(root)
        if frame["dataset_id"] != scores["dataset_id"]:
            raise ValueError("DAILY_AUDIT_LATEST_SOURCE_SCORE_DATASET_MISMATCH")
        _, _, features = engine._latest_features(frame)
        eligible = {
            sample.key: sample
            for sample in features.samples
            if sample.session == scores["observation_session"]
        }
        exact = 0
        for candidate in scores["candidates"]:
            sample = eligible[candidate["key"]]
            if list(sample.vector) != candidate["vector"]:
                raise ValueError("DAILY_AUDIT_FEATURE_REPLAY_MISMATCH")
            first, _ = models.predict_vector(model, sample.vector)
            second, _ = models.predict_vector(model, sample.vector)
            if first != second or first != candidate["score"]:
                raise ValueError("DAILY_AUDIT_MODEL_REPLAY_MISMATCH")
            exact += 1
        result["model_replay"] = {
            "state": "PASS",
            "exact_feature_vectors": exact,
            "exact_model_scores_twice": exact,
            "source_rows": len(frame["rows"]),
            "feature_names": model["feature_names"],
            "model_id": model["model_id"],
            "dataset_id": frame["dataset_id"],
            "forecast_writes": 0,
            "clock_source_calls": 0,
        }
    result["completed_at"] = datetime.now(UTC).isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--v2-root", type=Path)
    args = parser.parse_args()
    if args.output and (
        args.output.exists()
        or args.output.resolve().is_relative_to(args.root.resolve())
        or (args.v2_root and args.output.resolve().is_relative_to(args.v2_root.resolve()))
    ):
        raise ValueError("FRESH_AUDIT_OUTPUT_OUTSIDE_SOURCE_STORES_REQUIRED")
    result = audit(args.root, args.v2_root)
    body = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(body + "\n")
    print(body)


if __name__ == "__main__":
    main()
