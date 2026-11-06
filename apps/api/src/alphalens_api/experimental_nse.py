"""Private experimental research reads; never acquisition, training or accepted ranking writes."""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import JsonValue
from workers.personal.analytics import portfolio_review, preference_match
from workers.personal.contracts import Profile

from .core.domain_errors import APIError
from .personal import safe, store
from .routes import Research
from .schemas import Classification, Envelope
from .services import response

router = APIRouter(prefix="/api/v1/experimental-nse", tags=["private experimental NSE research"])


def personalized(data: dict[str, Any], request: Request) -> dict[str, Any]:
    """Apply only supported dated facts. Model inputs are never changed by preferences."""
    if request.app.state.settings.personal_root is None:
        data["personalization"] = "PERSONAL_WORKSPACE_NOT_CONFIGURED"
        return data
    owned = store(request)
    profile = Profile.model_validate(owned.profile()["value"])
    holdings: dict[str, list[dict[str, Any]]] = {}
    for record in owned.listing("portfolios"):
        review = portfolio_review(record["value"], profile, {})
        for holding in review["holdings"]:
            if float(holding["quantity"]) > 0:
                holdings.setdefault(holding["instrument_key"], []).append(
                    {
                        "portfolio": record["value"]["ledger"]["portfolio"]["portfolio_name"],
                        "quantity": holding["quantity"],
                        "remaining_cost_basis": holding["cost_basis_exact"],
                    }
                )
    watchlist_keys = {
        key for record in owned.listing("watchlists") for key in record["value"]["instrument_keys"]
    }
    for candidate in data.get("candidates", []):
        # Intraday-chain risk is not close-to-close drawdown or daily volatility.
        # Keep unavailable requested measures missing instead of substituting them.
        metrics = candidate.get("preference_metrics", {})
        candidate["preferences"] = preference_match(profile, metrics)
        candidate["held"] = candidate["key"] in holdings
        candidate["holdings"] = holdings.get(candidate["key"], [])
        candidate["watchlisted"] = candidate["key"] in watchlist_keys
        candidate["portfolio_implication"] = (
            "ALREADY_HELD_REVIEW_CONCENTRATION_WITH_DATED_PORTFOLIO_MARKS"
            if candidate["held"] and profile.consider_holdings
            else "NO_ALLOCATION_OR_TRADE_INSTRUCTION"
        )
    data["personalization"] = "SUPPORTED_CONSTRAINTS_ONLY_MODEL_ORDER_UNCHANGED"
    data["preference_horizon"] = profile.horizon
    return data


@router.get("/research")
def research_workspace(request: Request, service: Research) -> Envelope[JsonValue]:
    from workers.experimental_nse.workspace import read_workspace

    try:
        data = read_workspace(service.reader.settings.experimental_nse_root)
    except (OSError, ValueError, KeyError, TypeError):
        raise APIError(
            "EXPERIMENTAL_EVIDENCE_INVALID",
            "Experimental research evidence could not be verified. "
            "No substitute scores were created.",
            503,
        ) from None
    data = safe(lambda: personalized(data, request))
    return response(data, "PRIVATE_EXPERIMENTAL_NSE_RESEARCH").model_copy(
        update={
            "version": "alphalens.experimental_nse.workspace.v1",
            "classification": Classification(
                data_reality=(
                    "TEST_ONLY"
                    if service.reader.settings.test_only_evidence
                    else "REAL_PROVIDER_OBSERVATIONS_EXPERIMENTAL_RESEARCH"
                ),
                usage_classification="EXPERIMENTAL_UNVALIDATED_RESEARCH",
                final_vintage="RETROSPECTIVE_PROVIDER_RETRIEVAL_NOT_HISTORICAL_PIT",
                research_profile="ALPHALENS_EXPERIMENTAL_NSE_V1",
            ),
            "quality_status": "EXPERIMENTAL_NOT_INDEPENDENTLY_VALIDATED",
        }
    )
