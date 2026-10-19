"""Authenticated saved-only current-universe coverage and experimental research.

Default GET requests never acquire market data, fit/load estimators or append forecasts.
The explicit universe refresh parameter performs one budgeted identity-master GET.
The existing accepted ranking publisher is not used by this separate workspace.
"""

import math
import re
import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from pydantic import JsonValue
from workers.experimental_nse.acquire import digest
from workers.experimental_nse_v2.features import LOCAL_FEATURE_NAMES
from workers.nse_market import economic_research, engine, forward_cohort, stock_metrics
from workers.personal import research_sizing
from workers.providers import universe
from workers.providers.store import ProviderStore

from .core.domain_errors import APIError
from .experimental_nse_v2 import personalized_workspace
from .personal import safe
from .routes import Research
from .schemas import Classification, Envelope
from .services import response

router = APIRouter(prefix="/api/v1/nse-market", tags=["private observed NSE cohort"])
Page = Annotated[int, Query(ge=1, le=10000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str, Query(max_length=128)]


def _roots(service: Research) -> tuple[Path, Path, Path] | None:
    selected = service.reader.settings.experimental_nse_v2_root
    if selected is None:
        return None
    return selected.parent / "nse-market-expansion", selected, selected.parent / "nse-universe"


def _error() -> APIError:
    return APIError(
        "NSE_MARKET_SAVED_EVIDENCE_INVALID",
        "Saved NSE research or current identity evidence could not be verified. "
        "Refresh through the explicit private collection workflow; no substitute data was created.",
        503,
    )


def _envelope(data: dict[str, Any], service: Research) -> Envelope[JsonValue]:
    return response(data, "PRIVATE_OBSERVED_NSE_COHORT_RESEARCH").model_copy(
        update={
            "version": "alphalens.nse_market.workspace.v1",
            "classification": Classification(
                data_reality=(
                    "TEST_ONLY"
                    if service.reader.settings.test_only_evidence
                    else "REAL_PROVIDER_OBSERVATIONS_EXPERIMENTAL_RESEARCH"
                ),
                usage_classification="EXPERIMENTAL_UNVALIDATED_RESEARCH",
                final_vintage="RETROSPECTIVE_PROVIDER_RETRIEVAL_NOT_HISTORICAL_PIT",
                research_profile="ALPHALENS_EXPANDED_NSE_RESEARCH_V1",
            ),
            "quality_status": "OBSERVED_COHORT_NOT_FULL_MARKET_OR_INDEPENDENTLY_VALIDATED",
        }
    )


def _counts(data: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
    coverage = data.get("coverage", {})
    scores = data.get("scores") or {}
    return {
        "discoverable_nse_identities": summary.get("discoverable_nse_cash_identities")
        if summary
        else None,
        "discoverable_eq_series_identities": summary.get("discoverable_nse_eq_type_eq")
        if summary
        else None,
        "verified_eligible_common_equities": summary.get("verified_eligible_common_equities")
        if summary
        else None,
        "configured_securities": coverage.get("configured_securities", 0),
        "provider_queried_stocks": coverage.get("provider_queried_securities"),
        "provider_accessible_stocks": coverage.get("provider_accessible_securities"),
        "validated_historical_stocks": coverage.get("validated_historical_securities", 0),
        "genuine_candles": coverage.get("observations", 0),
        "sufficient_technical_features": coverage.get("technical_feature_eligible_securities"),
        "experimental_ml_eligible_stocks": coverage.get(
            "experimental_scored_securities", scores.get("scored_securities", 0)
        ),
        "independently_accepted_ml_stocks": 0,
    }


def _candidate(row: dict[str, Any]) -> dict[str, Any]:
    identity = row["identity"]
    if (
        row.get("source") != "UPSTOX_OFFICIAL_HISTORICAL_CANDLES"
        or identity["provider_key"] != row["key"]
        or identity["symbol"] != row["symbol"]
        or identity["isin"] != row["key"].removeprefix("NSE_EQ|")
        or identity["segment"] != "NSE_EQ"
        or identity["exchange"] != "NSE"
        or identity["instrument_type"] not in universe.COMMON_SERIES
        or tuple(row["feature_names"]) != LOCAL_FEATURE_NAMES
        or len(row["features"]) != len(LOCAL_FEATURE_NAMES)
    ):
        raise ValueError("NSE_RESEARCH_IDENTITY_OR_FEATURE_CONTRACT_MISMATCH")
    vector = dict(zip(row["feature_names"], row["features"], strict=True))
    if any(
        type(value) not in {int, float} or not math.isfinite(value) for value in vector.values()
    ):
        raise ValueError("NSE_RESEARCH_NONFINITE_FEATURE")
    score = row["score"]
    if type(score) not in {int, float} or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("NSE_RESEARCH_INVALID_SCORE")
    now = datetime.now(UTC)
    age = (
        now.astimezone(ZoneInfo("Asia/Kolkata")).date() - date.fromisoformat(row["session"])
    ).days
    inferred = datetime.fromisoformat(row["inference_at"])
    if age < 0 or inferred.utcoffset() is None or inferred > now:
        raise ValueError("NSE_RESEARCH_FUTURE_OBSERVATION_OR_INFERENCE")
    risk = row["risk"]
    volatility = risk["return_daily_sd_20"] * 100
    drawdown = risk["historical_price_drawdown_60"] * 100
    fields = (
        ("price_return_5", "5 observed-session price return", "percent", 100),
        ("price_return_20", "20 observed-session price return", "percent", 100),
        ("price_return_60", "60 observed-session price return", "percent", 100),
        ("rsi_14", "Simple RSI over 14 changes", "RSI points", 1),
        ("ma_distance_20", "Distance from 20-close average", "percent", 100),
        ("macd_12_26_over_close", "MACD 12/26 divided by close", "ratio", 1),
    )
    return {
        **row,
        "company_name": identity["name"],
        "company_name_basis": "CAPTURED_CURRENT_MASTER_NOT_HISTORICAL_NAME_MEMBERSHIP",
        "observation_date": row["session"],
        "observation_age_days": age,
        "data_freshness": "STALE" if age > 7 else "DATED_PROVIDER_EOD",
        "volatility_percent": volatility,
        "drawdown_percent": drawdown,
        "risk_kind": "ADJUSTED_PRICE_DAILY_RISK_NOT_TOTAL_RETURN",
        "preference_metrics": {
            "gross_price": float(row["observed_price"]),
            "volume": risk["volume"],
            "daily_volatility_percent": volatility,
            "maximum_drawdown_percent": drawdown,
            "price_return_percent": vector["price_return_20"] * 100,
            "rsi_14": vector["rsi_14"],
            "sma_distance": vector["ma_distance_20"],
            "macd": vector["macd_12_26_over_close"],
        },
        "preference_metric_basis": (
            "DATED_20_SESSION_PRICE_MOMENTUM_VOLATILITY_60_SESSION_DRAWDOWN_SIMPLE_RSI14"
        ),
        "technical_evidence": [
            {"feature": name, "label": label, "value": vector[name] * scale, "unit": unit}
            for name, label, unit, scale in fields
        ],
        "historical_evidence": {
            "observation_date": row["session"],
            "basis": "SAVED_TRAINING_COMPATIBLE_ADJUSTED_PRICE_FEATURES_NOT_TOTAL_RETURN",
            "maximum_lookback_observed_slots": 61,
            "maximum_observed_price_drawdown_percent": drawdown,
        },
    }


def _bounded(data: dict[str, Any], page: int, page_size: int) -> dict[str, Any]:
    """Bound duplicate/nested per-security arrays as well as the visible ranking."""
    result = dict(data)
    result["coverage"] = dict(data.get("coverage", {}))
    coverage = result["coverage"]
    full_rows = coverage.get("per_security")
    if isinstance(full_rows, list) and isinstance(coverage.get("end"), str):
        verified = len({row["key"] for row in full_rows if row.get("last") == coverage["end"]})
        configured = coverage.get("configured_securities", len(full_rows))
        coverage["latest_session_coverage"] = {
            "session": coverage["end"],
            "verified_securities": verified,
            "configured_securities": configured,
            "pending_securities": configured - verified,
            "basis": "FULL_CONFIGURED_COHORT_BEFORE_PAGINATION",
        }
    offset = (page - 1) * page_size
    for name in ("per_security", "not_observed", "technical_exclusions"):
        rows = result["coverage"].get(name)
        if isinstance(rows, list):
            result["coverage"][name + "_total"] = len(rows)
            result["coverage"][name] = rows[offset : offset + page_size]
    if isinstance(result.get("technical_exclusions"), list):
        result["technical_exclusions_total"] = len(result["technical_exclusions"])
        result["technical_exclusions"] = result["technical_exclusions"][offset : offset + page_size]
    if isinstance(data.get("scores"), dict):
        scores = {key: value for key, value in data["scores"].items() if key != "candidates"}
        exclusions = scores.get("exclusions", [])
        scores["exclusions_total"] = len(exclusions)
        scores["exclusions"] = exclusions[offset : offset + page_size]
        evaluation = scores.get("original_evaluation", {})
        scores["original_evaluation"] = {
            key: evaluation[key]
            for key in (
                "model_id",
                "selected_algorithm",
                "candidate_summary",
                "baseline_summary",
                "evidence_conclusion",
                "feature_version",
                "target_version",
                "selection_rule",
                "independent_acceptance",
                "future_independent_confirmation_required",
            )
            if key in evaluation
        }
        result["scores"] = scores
    return result


def _read(service: Research) -> dict[str, Any]:
    roots = _roots(service)
    if roots is None:
        data: dict[str, Any] = {"state": "NOT_CONFIGURED", "candidates": []}
        summary = None
    else:
        root, v2_root, universe_root = roots
        try:
            data = engine.workspace(root, v2_root)
            if data.get("accepted_current_rankings") != 0:
                raise ValueError("EXPERIMENTAL_COHORT_CANNOT_PUBLISH_ACCEPTED_RANKINGS")
            summary = universe.fresh(universe_root).summary
            data["universe"] = summary
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            raise _error() from None
    data["counts"] = _counts(data, summary)
    operations = data.setdefault("operations", {})
    provider_root = service.reader.settings.providers_root
    try:
        operations["shared_provider_usage"] = (
            ProviderStore(provider_root).upstox_day_usage(datetime.now(UTC))
            if provider_root is not None
            else {"state": "NOT_CONFIGURED", "provider_requests": 0}
        )
    except (OSError, ValueError, sqlite3.Error):
        operations["shared_provider_usage"] = {"state": "UNAVAILABLE", "provider_requests": 0}
    data["accepted_current_rankings"] = 0
    data["provider_requests"] = 0
    data["edge_status"] = "NO_DEMONSTRATED_EDGE"
    data["automatic_acquisition_enabled"] = (
        data.get("operations", {}).get("scheduler", {}).get("state")
        == "REGISTERED_ENABLED_LAST_VERIFIED"
    )
    return data


@router.get("/research")
def research(
    request: Request,
    service: Research,
    page: Page = 1,
    page_size: PageSize = 20,
    matches_only: bool = False,
    horizon: Annotated[int, Query(ge=5, le=20)] = 5,
) -> Envelope[JsonValue]:
    if horizon not in (5, 10, 20):
        raise APIError("UNSUPPORTED_RESEARCH_HORIZON", "Choose 5, 10 or 20 sessions.", 422)
    data = _read(service)
    try:
        data["candidates"] = [_candidate(row) for row in data.get("candidates", [])]
        saved = _sequence(service)
        sequence_scores = (
            {row["key"]: row for row in saved[1]["current_scores"]} if saved is not None else {}
        )
        for row in data["candidates"]:
            sequence_row = sequence_scores.get(row["key"])
            row["current_lstm"] = (
                sequence_row
                if sequence_row is not None and sequence_row["session"] == row["session"]
                else None
            )
            vector = dict(zip(row["feature_names"], row["features"], strict=True))
            why = [
                "Complete ordered 16-feature vector from qualified dated provider observations",
                "Ranked by actual saved five-session model score"
                if horizon == 5
                else "Ordered by observed daily volatility, not a prediction for this horizon",
            ]
            if vector["price_return_20"] > 0:
                why.append("Positive observed 20-session adjusted-price momentum")
            if vector["ma_distance_20"] > 0:
                why.append("Observed close above its 20-close average")
            row["evidence"] = {
                "classification": "EXPERIMENTAL_ML"
                if horizon == 5
                else "TECHNICAL_RESEARCH_CANDIDATE",
                "ml_horizon_sessions": 5,
                "why": why,
                "risks": [
                    "No demonstrated predictive or net economic edge",
                    "Classification scores are uncalibrated and are not probabilities of profit",
                    "Historical cohort membership and publication vintages are incomplete",
                    *(
                        ["Dated observation exceeds the seven-day freshness limit"]
                        if row["data_freshness"] == "STALE"
                        else []
                    ),
                    *(
                        ["Unvalidated extrapolation outside the original training cohort"]
                        if row.get("applicability")
                        == "OUT_OF_TRAINING_COHORT_EXTRAPOLATION_UNVALIDATED"
                        else []
                    ),
                ],
                "missing": [
                    *row.get("missing_evidence", []),
                    *(
                        []
                        if row["current_lstm"]
                        else ["No complete compatible saved LSTM score for this security"]
                    ),
                    *(
                        []
                        if horizon == 5
                        else [f"No trained {horizon}-session forecast is published"]
                    ),
                    "Verified market-capacity, bid/ask spread and dividend-inclusive total return",
                ],
            }
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        raise _error() from None
    data = safe(lambda: personalized_workspace(data, request))
    candidates = data["candidates"]
    if horizon != 5:
        candidates = sorted(candidates, key=lambda row: (row["volatility_percent"], row["key"]))
    unfiltered = len(candidates)
    if matches_only:
        candidates = [
            row
            for row in candidates
            if row.get("preferences", {}).get("state") == "MATCHES_SUPPORTED_CONSTRAINTS"
        ]
    data = _bounded(data, page, page_size)
    offset = (page - 1) * page_size
    data.update(
        candidates=candidates[offset : offset + page_size],
        total=len(candidates),
        unfiltered_total=unfiltered,
        page=page,
        page_size=page_size,
        matches_only=matches_only,
        research_horizon_sessions=horizon,
        ranking_basis="EXPERIMENTAL_FIVE_SESSION_MODEL_SCORE"
        if horizon == 5
        else "DESCRIPTIVE_LOW_DAILY_VOLATILITY_NOT_HORIZON_FORECAST",
        ml_horizon_supported=horizon == 5,
    )
    return _envelope(data, service)


@router.get("/economic-research")
def economic_evidence(service: Research) -> Envelope[JsonValue]:
    """Read registered saved-policy evidence; never execute experiments from a page load."""
    roots = _roots(service)
    if roots is None:
        return _envelope({"state": "NOT_CONFIGURED", "provider_requests": 0}, service)
    try:
        root = roots[1].parent / "investment-evidence-research"
        if not (root / "report.json").exists():
            return _envelope({"state": "NOT_YET_AVAILABLE", "provider_requests": 0}, service)
        return _envelope(economic_research.load(root), service)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        raise _error() from None


@router.get("/status")
def status(service: Research) -> Envelope[JsonValue]:
    data = _bounded(_read(service), 1, 20)
    data["candidates"] = []
    return _envelope(data, service)


@router.get("/universe")
def current_universe(
    service: Research,
    q: Search = "",
    page: Page = 1,
    page_size: PageSize = 50,
    refresh: bool = False,
) -> Envelope[JsonValue]:
    roots = _roots(service)
    if roots is None:
        raise _error()
    try:
        if refresh:
            from .providers import private_root

            snapshot = universe.refresh(roots[2], private_root(service))
        else:
            snapshot = universe.fresh(roots[2])
        term = q.strip().casefold()
        rows = [
            row
            for row in snapshot.records
            if row["eligible_common_equity"]
            and (
                not term
                or any(
                    term in str(row[field]).casefold()
                    for field in ("name", "symbol", "isin", "instrument_key")
                )
            )
        ]
        offset = (page - 1) * page_size
        data = {
            "snapshot_id": snapshot.snapshot_id,
            "observed_at": snapshot.observed_at.isoformat(),
            "summary": snapshot.summary,
            "total": len(rows),
            "rows": [
                {**row, "series": row.get("instrument_type")}
                for row in rows[offset : offset + page_size]
            ],
            "page": page,
            "page_size": page_size,
            "provider_requests": 1 if refresh else 0,
            "historical_membership_established": False,
        }
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        raise _error() from None
    return _envelope(data, service)


def _sequence_score(row: dict[str, Any], model_sha: str, now: datetime) -> None:
    """Validate saved decision-time evidence without loading an estimator."""
    key, symbol = row["key"], row["symbol"]
    session = date.fromisoformat(row["session"])
    inferred = datetime.fromisoformat(row["inference_at"])
    observed = datetime.fromisoformat(row["source_observed_at"])
    score = row["score"]
    if (
        not isinstance(key, str)
        or not re.fullmatch(r"NSE_EQ\|INE[A-Z0-9]{8}[0-9]", key)
        or not universe.valid_isin(key.removeprefix("NSE_EQ|"))
        or not isinstance(symbol, str)
        or not 1 <= len(symbol) <= 64
        or row["model_sha256"] != model_sha
        or row["classification"] != "EXPERIMENTAL_ML"
        or row["calibration_status"] != "NOT_ESTABLISHED"
        or row["forecast_created"] is not False
        or inferred.utcoffset() is None
        or observed.utcoffset() is None
        or observed > inferred
        or inferred > now
        or session > observed.astimezone(ZoneInfo("Asia/Kolkata")).date()
        or type(score) not in {int, float}
        or not math.isfinite(score)
        or not 0 <= score <= 1
    ):
        raise ValueError("SAVED_SEQUENCE_SCORE_CHRONOLOGY_OR_CONTRACT_INVALID")


def _sequence(service: Research) -> tuple[Path, dict[str, Any]] | None:
    roots = _roots(service)
    if roots is None:
        return None
    root = roots[1].parent / "sequence-benchmark-v1"
    if not (root / "report.json").exists():
        return None
    report_path = root / "report-final.json"
    if not report_path.exists():
        report_path = root / "report.json"
    report = engine._read(report_path)
    if report_path.name == "report-final.json":
        from workers.nse_market.sequence_review import validate_correction

        original = engine._read(root / "report.json")
        validate_correction(original, report)
        if report["original_report_sha256"] != digest((root / "report.json").read_bytes()):
            raise ValueError("SEQUENCE_ENGINEERING_CORRECTION_LINEAGE_INVALID")
    model = engine._read(root / "model.json")
    completed = datetime.fromisoformat(report["completed_at"])
    if (
        report["family"] != "ALPHALENS_SEQUENCE_BENCHMARK_V1"
        or report["feature_version"] != "nse.price-state.sequence20x8.v1"
        or report["state"] != "EXPERIMENTAL_UNVALIDATED"
        or report["accepted_rankings"] != 0
        or report["prospective_forecasts"] != 0
        or report["matured_prospective_outcomes"] != 0
        or report["model_sha256"] != digest((root / "model.json").read_bytes())
        or report["protocol_sha256"] != model["protocol_sha256"]
        or completed.utcoffset() is None
        or completed > datetime.now(UTC)
        or not isinstance(report["current_scores"], list)
        or len(report["current_scores"]) > 10000
    ):
        raise ValueError("SAVED_SEQUENCE_EVIDENCE_MISMATCH")
    keys = set()
    for row in report["current_scores"]:
        _sequence_score(row, report["model_sha256"], completed)
        if row["key"] in keys:
            raise ValueError("SAVED_SEQUENCE_DUPLICATE_SCORE_IDENTITY")
        keys.add(row["key"])
    return root, report


@router.get("/sequence")
def sequence_research(service: Research) -> Envelope[JsonValue]:
    try:
        saved = _sequence(service)
        if saved is None:
            return _envelope({"state": "NOT_YET_AVAILABLE", "accepted_rankings": 0}, service)
        _, report = saved
        comparisons = {}
        for name, result in report["comparisons"].items():
            comparisons[name] = {
                key: value for key, value in result.items() if key != "economic_sensitivity"
            }
            # Same experiment, same target and dates. Expose saved reference
            # economics without duplicating every security decision or curve.
            top = result.get("economic_sensitivity", {}).get("strategies", {}).get("top5", {})
            comparisons[name]["top5_reference"] = {
                key: top[key]
                for key in ("decision_count", "mean_membership_turnover")
                if key in top
            }
            comparisons[name]["top5_reference"]["scenarios"] = [
                {key: value for key, value in scenario.items() if key != "curve"}
                for scenario in top.get("scenarios", [])
            ]
        lstm = report["comparisons"]["LSTM"]["economic_sensitivity"]
        data = {
            **{
                key: value
                for key, value in report.items()
                if key not in {"comparisons", "current_scores"}
            },
            "comparisons": comparisons,
            "current_scored_count": len(report["current_scores"]),
            "current_scores": report["current_scores"][:20],
            "economic_sensitivity": {
                **lstm,
                "strategies": {
                    key: {name: value for name, value in result.items() if name != "decisions"}
                    for key, result in lstm["strategies"].items()
                },
            },
            "provider_requests": 0,
        }
        return _envelope(data, service)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        raise _error() from None


@router.get("/stock-research")
def stock_research(
    service: Research,
    key: Annotated[str, Query(pattern=r"^NSE_EQ\|[A-Z0-9]{12}$")],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Envelope[JsonValue]:
    """Dated saved scores/outcomes only; classifier scores never become target prices."""
    try:
        workspace = _read(service)
        current = next((row for row in workspace.get("candidates", []) if row["key"] == key), None)
        if current is not None:
            current = _candidate(current)
        saved = _sequence(service)
        roots = _roots(service)
        prospective = (
            forward_cohort.stock_history(roots[0], roots[1], key, limit)
            if roots is not None
            else {"forecast_count": 0, "matured_outcomes": 0, "rows": []}
        )
        lstm, history = None, []
        if saved is not None:
            root, report = saved
            lstm = next((row for row in report["current_scores"] if row["key"] == key), None)
            records = engine._read(root / "historical-predictions.json")
            if records["model_sha256"] != report["model_sha256"]:
                raise ValueError("HISTORICAL_SEQUENCE_MODEL_MISMATCH")
            history = [row for row in records["rows"] if row["key"] == key][-limit:]
            for row in history:
                decision = date.fromisoformat(row["decision_session"])
                target = date.fromisoformat(row["target_session"])
                actual = row["actual_price_component_return"]
                if (
                    row["classification"] != "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE"
                    or not decision < target <= datetime.now(UTC).date()
                    or type(actual) not in {int, float}
                    or not math.isfinite(actual)
                    or type(row["actual_positive"]) is not int
                    or row["actual_positive"] not in {0, 1}
                    or any(
                        type(score) not in {int, float}
                        or not math.isfinite(score)
                        or not 0 <= score <= 1
                        for score in row["scores"].values()
                    )
                ):
                    raise ValueError("HISTORICAL_SEQUENCE_OUTCOME_CONTRACT_INVALID")
        return _envelope(
            {
                "state": "AVAILABLE"
                if current is not None or lstm is not None
                else "NO_COMPLETE_COMPATIBLE_SAVED_INPUTS",
                "key": key,
                "v2": current,
                "lstm": lstm,
                "historical_comparisons": history,
                "historical_metrics": stock_metrics.comparison(history),
                "historical_classification": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
                "target": "NEXT_OBSERVED_OPEN_TO_FIFTH_OBSERVED_CLOSE_PRICE_COMPONENT",
                "calibration_status": "NOT_ESTABLISHED",
                "prospective_outcomes": prospective["matured_outcomes"],
                "prospective_history": prospective,
                "accepted_rankings": 0,
                "provider_requests": 0,
                "missing_evidence": [
                    "Future matured observations and independent acceptance",
                    "Complete historical publication, actions and membership",
                    "Verified executions and full economic outcomes",
                ],
            },
            service,
        )
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        raise _error() from None


@router.get("/position-scenario")
def position_scenario(
    service: Research,
    key: Annotated[str, Query(pattern=r"^NSE_EQ\|[A-Z0-9]{12}$")],
    budget: Annotated[Decimal, Query(gt=0, le=1000000000)],
    loss_budget: Annotated[Decimal, Query(gt=0, le=1000000000)],
    assumed_stop_percent: Annotated[Decimal, Query(gt=0, le=100)],
    round_trip_cost_bps: Annotated[Decimal, Query(ge=0, le=10000)],
) -> Envelope[JsonValue]:
    """User-declared dated-price scenario; no order, cash claim or portfolio write."""

    def calculate() -> dict[str, Any]:
        data = _read(service)
        row = next((item for item in data.get("candidates", []) if item["key"] == key), None)
        if row is None:
            raise ValueError("COMPATIBLE_DATED_PRICE_REFERENCE_REQUIRED")
        verified = _candidate(row)
        if verified["observation_age_days"] > 7:
            raise ValueError("STALE_SCENARIO_REFERENCE_REJECTED")
        result = research_sizing.calculate(
            observed_price=Decimal(verified["observed_price"]),
            budget=budget,
            loss_budget=loss_budget,
            assumed_stop_percent=assumed_stop_percent,
            round_trip_cost_bps=round_trip_cost_bps,
            observation_date=date.fromisoformat(verified["session"]),
            source=verified["source"],
            as_of=datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date(),
        )
        result.update(key=key, provider_requests=0, model_score_used_for_sizing=False)
        return result

    return _envelope(safe(calculate), service)
