"""Authenticated read-only V2 research; isolated from accepted ranking publication."""

from fastapi import APIRouter, Request
from pydantic import JsonValue

from .core.domain_errors import APIError
from .experimental_nse import personalized
from .personal import safe
from .routes import Research
from .schemas import Classification, Envelope
from .services import response

router = APIRouter(prefix="/api/v1/experimental-nse-v2", tags=["private V2 NSE research"])


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
    data = safe(lambda: personalized(data, request))
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
