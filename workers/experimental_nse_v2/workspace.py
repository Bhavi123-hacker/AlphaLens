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


def research_evidence(row: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """Present exact saved feature values, without scoring again or inventing a company."""
    if (
        identity.get("provider_key") != row["key"]
        or identity.get("isin") != row["key"].removeprefix("NSE_EQ|")
        or identity.get("symbol") != row["symbol"]
        or identity.get("segment") != "NSE_EQ"
        or identity.get("exchange") != "NSE"
        or identity.get("instrument_type") != "EQ"
    ):
        raise ValueError("V2_COMPANY_INSTRUMENT_IDENTITY_MISMATCH")
    vector = dict(zip(row["feature_names"], row["features"], strict=True))
    fields = (
        ("price_return_5", "5 observed-session price return", "percent", 100),
        ("price_return_20", "20 observed-session price return", "percent", 100),
        ("price_return_60", "60 observed-session price return", "percent", 100),
        ("rsi_14", "Simple RSI over 14 changes", "RSI points", 1),
        ("ma_distance_20", "Distance from 20-close average", "percent", 100),
        ("macd_12_26_over_close", "MACD 12/26 divided by close", "ratio", 1),
    )
    return {
        "company_name": identity.get("name"),
        "identity": {
            key: identity.get(key)
            for key in (
                "provider_key",
                "isin",
                "exchange",
                "segment",
                "instrument_type",
                "observed_at",
                "identity_evidence",
                "revision_sha256",
            )
        },
        "company_name_basis": "CAPTURED_CURRENT_MASTER_NOT_HISTORICAL_NAME_MEMBERSHIP",
        "technical_evidence": [
            {"feature": name, "label": label, "value": vector[name] * scale, "unit": unit}
            for name, label, unit, scale in fields
            if name in vector
        ],
        "historical_evidence": {
            "observation_date": row["session"],
            "basis": "SAVED_TRAINING_COMPATIBLE_ADJUSTED_PRICE_FEATURES_NOT_TOTAL_RETURN",
            "maximum_lookback_observed_slots": 61,
            "maximum_observed_price_drawdown_percent": row["risk"]["historical_price_drawdown_60"]
            * 100,
        },
    }


def read_workspace(root: Path | None) -> dict[str, Any]:
    from .workflow import read_status

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
        "operations": read_status(root)
        if root is not None
        else {
            "state": "NO_SAVED_OPERATIONAL_RUN",
            "message": "No private V2 research workspace is configured.",
            "stages": [],
            "last_failure": None,
        },
    }
    if root is None or not (root / "evaluation.json").exists():
        return result
    verify(root)
    price_only = (root / "price-only/evaluation.json").exists()
    output = root / "price-only" if price_only else root
    report = verified(output / "evaluation.json")
    model = models.load_model(output / "model.json", report["model_sha256"])
    dataset = data.load_current(root)
    base_dataset_id = dataset.get(
        "base_dataset_id", dataset.get("parent_dataset_id", dataset["dataset_id"])
    )
    if (
        model["model_id"] != report["model_id"]
        or model["protocol_id"] != protocol_id(price_only)
        or model["dataset_id"] != base_dataset_id
    ):
        raise ValueError("V2_WORKSPACE_LINEAGE_MISMATCH")
    forecasts = summary(
        output,
        rows=dataset["rows"],
        sessions=dataset["sessions"],
        official_timings=data.collected_timings(root),
    )
    inference: dict[str, Any] = {"candidates": [], "exclusions": [], "gap": "NO_V2_INFERENCE_RUN"}
    pointer = output / "latest-inference.txt"
    if pointer.exists():
        if pointer.is_symlink():
            raise ValueError("V2_POINTER_SYMLINK_FORBIDDEN")
        name = pointer.read_text(encoding="utf-8")
        if not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z\.json", name):
            raise ValueError("V2_INFERENCE_PATH_REJECTED")
        inference = verified(output / "inference" / name)
        if inference["model_id"] != model["model_id"] or (
            inference["dataset_id"] != dataset["dataset_id"]
            and inference["dataset_id"] not in data.dataset_versions(root)
        ):
            raise ValueError("V2_INFERENCE_LINEAGE_MISMATCH")
    lookup = {(r["key"], r["session"]): r for r in dataset["rows"]}
    identities = {item["provider_key"]: item for item in dataset["identities"]}
    if len(identities) != len(dataset["identities"]):
        raise ValueError("V2_DUPLICATE_CURRENT_IDENTITY")
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    candidates = []
    for row in inference["candidates"]:
        if row["feature_names"] != model["feature_names"]:
            raise ValueError("V2_SAVED_FEATURE_ORDER_MISMATCH")
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
                **research_evidence(row, identities[row["key"]]),
                "observation_date": row["session"],
                "observation_age_days": age,
                "data_freshness": "STALE" if age > 7 else "DATED_PROVIDER_EOD",
                "collection_relation": (
                    "LATEST_COLLECTION_SNAPSHOT"
                    if inference["dataset_id"] == dataset["dataset_id"]
                    else "SAVED_FORECAST_INPUTS_PRESERVED_NEWER_COLLECTION_EXISTS"
                ),
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
            "inference_dataset_id": inference.get("dataset_id"),
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
            "latest_collection_date": latest,
            "latest_scored_date": max(
                (row["observation_date"] for row in candidates), default=None
            ),
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
                    "current_primary_inference": "NOT_PUBLISHED_BY_PRICE_ONLY_COMPANION",
                    "companion_current_scored_vectors": len(candidates),
                    "primary_context_required_fraction": 0.8,
                    "coverage_gap": "PRIMARY_CONTEXT_CONTRACT_AND_EVIDENCE_PRESERVED_SEPARATELY",
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
