"""Read-only verified V2 workspace. No provider requests, fitting or acceptance writes."""

import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_api.auth.permissions import verify

from . import acceptance, data, models
from .forward import summary
from .pipeline import protocol_id, verified


def read_workspace(root: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "alphalens.experimental_nse_v2.workspace.v1",
        "family": data.FAMILY,
        "status": "EXPERIMENTAL_UNVALIDATED",
        "available": False,
        "model": None,
        "dataset": None,
        "evaluation": None,
        "candidates": [],
        "exclusions": ["NO_VERIFIED_V2_MODEL_RUN"],
        "prospective": {"forecasts": 0, "outcomes": 0, "metrics": None, "status": "NO_FORECASTS"},
        "accepted_current_rankings": 0,
    }
    if root is None or not (root / "evaluation.json").exists():
        return result
    verify(root)
    price_only = (root / "price-only/evaluation.json").exists()
    output = root / "price-only" if price_only else root
    report = verified(output / "evaluation.json")
    model = models.load_model(output / "model.json", report["model_sha256"])
    dataset = data.load_current(root)
    if (
        model["model_id"] != report["model_id"]
        or model["protocol_id"] != protocol_id(price_only)
        or model["dataset_id"] != data.load(root)["dataset_id"]
    ):
        raise ValueError("V2_WORKSPACE_LINEAGE_MISMATCH")
    forecasts = summary(output)
    inference: dict[str, Any] = {"candidates": [], "exclusions": [], "gap": "NO_V2_INFERENCE_RUN"}
    pointer = output / "latest-inference.txt"
    if pointer.exists():
        if pointer.is_symlink():
            raise ValueError("V2_POINTER_SYMLINK_FORBIDDEN")
        name = pointer.read_text(encoding="utf-8")
        if not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z\.json", name):
            raise ValueError("V2_INFERENCE_PATH_REJECTED")
        inference = verified(output / "inference" / name)
        if (
            inference["model_id"] != model["model_id"]
            or inference["dataset_id"] != dataset["dataset_id"]
        ):
            raise ValueError("V2_INFERENCE_LINEAGE_MISMATCH")
    lookup = {(r["key"], r["session"]): r for r in dataset["rows"]}
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    candidates = []
    for row in inference["candidates"]:
        actual = lookup[(row["key"], row["session"])]
        if actual["symbol"] != row["symbol"] or actual["close"] != row["observed_price"]:
            raise ValueError("V2_STOCK_CHART_IDENTITY_PRICE_MISMATCH")
        if abs(models.predict_vector(model, row["features"])[0] - row["score"]) > 1e-12:
            raise ValueError("V2_SAVED_MODEL_SCORE_MISMATCH")
        age = (today - date.fromisoformat(row["session"])).days
        if age < 0 or datetime.fromisoformat(row["inference_at"]) > datetime.now(UTC):
            raise ValueError("V2_FUTURE_OBSERVATION_REJECTED")
        risk = row["risk"]
        candidates.append(
            {
                **row,
                "observation_date": row["session"],
                "observation_age_days": age,
                "data_freshness": "STALE" if age > 7 else "DATED_PROVIDER_EOD",
                "risk_kind": "ADJUSTED_PRICE_DAILY_RISK_NOT_TOTAL_RETURN",
                "volatility_percent": risk["return_daily_sd_20"] * 100,
                "drawdown_percent": risk["historical_price_drawdown_60"] * 100,
                "preference_metrics": {
                    "gross_price": float(row["observed_price"]),
                    "volume": risk["volume"],
                    "daily_volatility_percent": risk["return_daily_sd_20"] * 100,
                    "maximum_drawdown_percent": risk["historical_price_drawdown_60"] * 100,
                    "price_return_percent": row["features"][2] * 100,
                    "rsi_14": row["features"][8],
                    "sma_distance": row["features"][6],
                    "macd": row["features"][9],
                },
                "preference_metric_basis": (
                    "DATED_20_SESSION_PRICE_MOMENTUM_VOLATILITY_60_SESSION_DRAWDOWN_SIMPLE_RSI14"
                ),
                "forecast_timing": (
                    "ACTUAL_INFERENCE_BEFORE_VERIFIED_NEXT_SESSION_OPEN"
                    if row.get("eligible_for_prospective")
                    else "TIMING_INELIGIBLE_RESEARCH_SCORE"
                ),
                "preference_matches": [],
                "exclusions": [],
                "held": False,
            }
        )
    comparisons = [
        {"algorithm": key, "metrics": value} for key, value in report["candidate_summary"].items()
    ]
    comparisons += [
        {"algorithm": "BASELINE_" + key, "metrics": value}
        for key, value in report["baseline_summary"].items()
    ]
    bundle = acceptance.evidence_bundle(
        model["model_id"], dataset["dataset_id"], protocol_id(price_only), forecasts
    )
    latest = dataset["sessions"][-1]
    return {
        **result,
        "status": "PROSPECTIVE_EVALUATION_IN_PROGRESS"
        if forecasts.get("eligible_forecasts", 0)
        else "BACKTESTED_NOT_PROSPECTIVELY_ACCEPTED",
        "available": True,
        "model": {
            "id": model["model_id"],
            "algorithm": model["algorithm"],
            "feature_version": model["feature_version"],
            "features": model["feature_names"],
            "trained_at": model["trained_at"],
            "inference_at": inference.get("generated_at"),
            "decision_clock": inference.get("decision_clock"),
            "horizon": "5 subsequent observed sessions; next open to fifth close",
            "target_definition": (
                "Split/bonus-adjusted price return C[t+5]/O[t+1]-1; excludes dividends; "
                "conditional reference prices, not execution profit"
            ),
            "calibration_status": "NOT_ESTABLISHED_UNCALIBRATED_SCORE",
        },
        "dataset": {
            "id": dataset["dataset_id"],
            "training_dataset_id": model["dataset_id"],
            "observations": len(dataset["rows"]),
            "securities": len(dataset["identities"]),
            "sessions": len(dataset["sessions"]),
            "start": dataset["sessions"][0],
            "end": latest,
            "source": "UPSTOX_OFFICIAL_AUTHENTICATED_DAILY_CANDLES",
            "price_basis": data.BASIS,
            "permission_reference": dataset["permission_reference"],
            "quality": dataset["quality"],
            "action_coverage": "REFERENCE_RESPONSES_NOT_EXHAUSTIVE",
            "membership": "CURRENT_FIXED_COHORT_NOT_HISTORICAL_UNIVERSE",
            "publication_finality": dataset.get(
                "current_finality", "HISTORICAL_FINAL_VINTAGE_NOT_PIT"
            ),
            "provider_requests_from_page": 0,
            "source_observed_at": dataset["source_observed_at"],
            "collection_clock": dataset.get("current_clock", dataset["clock"]),
        },
        "evaluation": {
            **report,
            "comparisons": comparisons,
            "edge_status": report["evidence_conclusion"],
            "preserved_primary_experiment": (
                {
                    "feature_version": verified(root / "evaluation.json")["feature_version"],
                    "selected_algorithm": verified(root / "evaluation.json")["selected_algorithm"],
                    "current_eligible_vectors": 0,
                    "coverage_gap": "31_ACTION_SAFE_STOCKS_BELOW_40_REQUIRED_CONTEXT_MEMBERS",
                }
                if price_only
                else None
            ),
        },
        "candidates": candidates,
        "exclusions": [r for r in inference["exclusions"] if r.get("session") == latest]
        + ([inference["gap"]] if inference.get("gap") else []),
        "prospective": forecasts,
        "acceptance": acceptance.readiness(bundle),
        "read_at": datetime.now(UTC).isoformat(),
    }
