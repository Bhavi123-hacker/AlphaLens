"""Authenticated read-only V2 research; isolated from accepted ranking publication."""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import JsonValue
from workers.personal.analytics import portfolio_review
from workers.personal.contracts import Profile

from .core.domain_errors import APIError
from .experimental_nse import personalized
from .personal import safe, store
from .routes import Research
from .schemas import Classification, Envelope
from .services import response

router = APIRouter(prefix="/api/v1/experimental-nse-v2", tags=["private V2 NSE research"])


def personalized_workspace(data: dict[str, Any], request: Request) -> dict[str, Any]:
    result = personalized(data, request)
    if request.app.state.settings.personal_root is None:
        return result
    owned = store(request)
    profile = Profile.model_validate(owned.profile()["value"])
    context: dict[str, list[dict[str, Any]]] = {}
    for record in owned.listing("portfolios"):
        review = portfolio_review(record["value"], profile, {})
        for holding in review["holdings"]:
            if holding["quantity"] == "0":
                continue
            context.setdefault(holding["instrument_key"], []).append(
                {
                    "portfolio_id": record["id"],
                    "portfolio_name": record["value"]["ledger"]["portfolio"]["portfolio_name"],
                    "cost_allocation_percent": holding["cost_allocation_percent"],
                    "allocation_basis": "REMAINING_FIFO_COST_NOT_MARKET_WEIGHT",
                    "user_concentration_limit_percent": float(
                        profile.maximum_stock_allocation_percent
                    ),
                    "concentration_review": "CONCENTRATION_RISK" in holding["diagnostics"],
                    "quantity": holding["quantity"],
                }
            )
    for candidate in result.get("candidates", []):
        candidate["portfolio_context"] = context.get(candidate["key"], [])
    return result


@router.get("/research")
def research_workspace(request: Request, service: Research) -> Envelope[JsonValue]:
    from workers.experimental_nse_v2.workspace import read_workspace

    try:
        data = read_workspace(service.reader.settings.experimental_nse_v2_root)
        if data.get("accepted_current_rankings") != 0:
            raise ValueError("EXPERIMENTAL_WORKSPACE_CANNOT_PUBLISH_ACCEPTED_RANKINGS")
    except (OSError, ValueError, KeyError, TypeError):
        raise APIError(
            "EXPERIMENTAL_V2_EVIDENCE_INVALID",
            "V2 research evidence could not be verified. No substitute scores were created.",
            503,
        ) from None
    data = safe(lambda: personalized_workspace(data, request))
    return response(data, "PRIVATE_EXPERIMENTAL_NSE_V2_RESEARCH").model_copy(
        update={
            "version": "alphalens.experimental_nse_v2.workspace.v1",
            "classification": Classification(
                data_reality=(
                    "TEST_ONLY"
                    if service.reader.settings.test_only_evidence
                    else "REAL_PROVIDER_OBSERVATIONS_EXPERIMENTAL_RESEARCH"
                ),
                usage_classification="EXPERIMENTAL_UNVALIDATED_RESEARCH",
                final_vintage="RETROSPECTIVE_PROVIDER_RETRIEVAL_NOT_HISTORICAL_PIT",
                research_profile="ALPHALENS_EXPERIMENTAL_NSE_V2",
            ),
            "quality_status": "EXPERIMENTAL_NOT_INDEPENDENTLY_VALIDATED",
        }
    )
