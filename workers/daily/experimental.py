"""Explicit private experimental scoring of a complete, reviewed current feature bundle.

This module has no API publication, scheduler, fitting, ranking, alert or ledger writes.
Only trusted local evidence is supported; evidence references require operator review.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.daily.providers import BASELINE
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_contracts import Access, Instrument

from .features import definitions
from .inference import input_compatibility, load, predict, verify_model

CLASSIFICATION = "EXPERIMENTAL_UNVALIDATED_RESEARCH"
REQUIRED_REVIEWS = (
    "source_compatibility",
    "corporate_actions",
    "session_calendar",
    "dated_peer_universe",
)


def preflight(report: dict[str, Any], bundle: dict[str, Any], access: Access) -> dict[str, Any]:
    """No model loading until all numerical, temporal and reviewed source inputs pass."""
    reasons = []
    decision = datetime.fromisoformat(bundle["decision_at"])
    receipt = datetime.fromisoformat(bundle["received_at"])
    session = date.fromisoformat(bundle["session"])
    try:
        instrument = Instrument.model_validate(bundle.get("instrument", {}))
        if (
            instrument.provider != "upstox"
            or instrument.exchange != "NSE"
            or instrument.segment != "NSE_EQ"
            or instrument.instrument_type != "EQ"
            or not instrument.isin
            or instrument.provider_key != "NSE_EQ|" + instrument.isin
            or instrument.observed_at > receipt
        ):
            raise ValueError
    except ValueError:
        reasons.append("VERIFIED_EXACT_CURRENT_NSE_EQ_IDENTITY_REQUIRED")
    if decision.tzinfo is None or receipt.tzinfo is None:
        raise DataContractError("AWARE_EXPERIMENTAL_CLOCKS_REQUIRED")
    if access.provider != "upstox" or access.blockers(decision):
        reasons.append("AUTHORIZED_PRIVATE_SOURCE_REQUIRED")
    if not access.retention_permitted or not access.research_permitted:
        reasons.append("PRIVATE_RETAINED_RESEARCH_PERMISSION_REQUIRED")
    if (
        receipt > decision
        or session <= date(2026, 10, 6)
        or decision.astimezone(ZoneInfo("Asia/Kolkata")).date() <= session
    ):
        reasons.append("NEW_SESSION_KNOWN_AT_CHRONOLOGY_REQUIRED")
    if bundle.get("price_basis") in {None, "UNKNOWN"}:
        reasons.append("REVIEWED_SOURCE_COMPATIBLE_PRICE_BASIS_REQUIRED")
    reviews = bundle.get("reviews", {})
    for name in REQUIRED_REVIEWS:
        review = reviews.get(name, {})
        if not review.get("reference") or review.get("bundle_sha256") != checksum(
            stable_json({k: v for k, v in bundle.items() if k != "reviews"})
        ):
            reasons.append("REVIEW_REQUIRED_" + name.upper())
    columns = tuple(report["model_identity"]["feature_columns"])
    expected = tuple(d.feature_name for d in definitions(session, decision))
    if columns != expected or len(columns) != 38:
        reasons.append("EXACT_38_FEATURE_ORDER_REQUIRED")
    values = bundle.get("features", {})
    if set(values) != set(columns):
        reasons.append("EXACT_FEATURE_NAMES_REQUIRED")
    compatible = input_compatibility(columns, values)
    reasons.extend(compatible["reasons"])
    for name in columns:
        observed = values.get(name, {}).get("available_at")
        try:
            available = datetime.fromisoformat(observed)
            if available.tzinfo is None or available > decision:
                raise ValueError
        except (ValueError, TypeError):
            reasons.append("FEATURE_AVAILABILITY_REQUIRED_" + name)
    return {
        "classification": CLASSIFICATION,
        "eligible_for_experimental_scoring": not reasons,
        "reasons": sorted(set(reasons)),
        "missing_features": compatible["excluded"],
        "values": compatible["values"] if not reasons else None,
        "accepted_model": False,
        "accepted_rankings": False,
    }


def score(
    root: Path, report: dict[str, Any], bundle: dict[str, Any], access: Access
) -> dict[str, Any]:
    checked = preflight(report, bundle, access)
    if not checked["eligible_for_experimental_scoring"]:
        return {**checked, "state": "INPUT_EVIDENCE_INCOMPLETE", "predictions_generated": 0}
    from workers.providers.daily_clock import guard

    from .compatibility import audit

    clock = guard()
    if datetime.fromisoformat(bundle["decision_at"]) > datetime.fromisoformat(clock["lower_at"]):
        raise DataContractError("EXPERIMENTAL_DECISION_NOT_YET_INDEPENDENTLY_OBSERVED")

    pinned = audit(root)
    if not any(
        c["model_run_id"] == report["model_run_id"] and c["model_sha256"] == report["model_sha256"]
        for c in pinned["candidates"]
    ):
        raise DataContractError("FROZEN_EXPERIMENTAL_CANDIDATE_REQUIRED")
    path = verify_model(root / "p9", report, BASELINE)
    model = load(path, report["model_sha256"], authorized_experimental=True)
    columns = tuple(report["model_identity"]["feature_columns"])
    result = predict(
        model,
        checked["values"],
        columns,
        columns,
        session=date.fromisoformat(bundle["session"]),
        decision_time=datetime.fromisoformat(bundle["decision_at"]),
        receipt_time=datetime.fromisoformat(bundle["received_at"]),
        training_cutoff=datetime.fromisoformat(
            report["model_identity"]["configuration"]["training_cutoff"]
        ),
        archive_end=date(2026, 10, 6),
        authorized_experimental=True,
    )
    return {
        **checked,
        "values": None,
        "state": "UNVALIDATED_EXPLORATORY_RESULT",
        "model_sha256": report["model_sha256"],
        "instrument_key": bundle["instrument"]["provider_key"],
        "symbol": bundle["instrument"]["symbol"],
        "session": bundle["session"],
        "result": result,
        "predictions_generated": 1,
        "financial_action_authorized": False,
        "personalized_advice": False,
    }
