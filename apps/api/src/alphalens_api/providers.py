"""Authenticated, read-only provider comparison. No outbound market-data requests."""

import os
import sqlite3
import time
from contextlib import closing
from datetime import date
from pathlib import Path

from fastapi import APIRouter
from pydantic import JsonValue
from workers.providers.readiness import comparison
from workers.providers.store import ProviderStore
from workers.providers.validation import status as upstox_status

from alphalens_api.auth.permissions import verify
from alphalens_api.core.domain_errors import APIError
from alphalens_api.credentials import credential_present
from alphalens_api.routes import Research
from alphalens_api.schemas import Classification, Envelope
from alphalens_api.services import response

router = APIRouter(prefix="/api/v1/providers", tags=["provider-readiness"])


@router.get("/upstox-validation")
def upstox_validation(service: Research) -> Envelope[JsonValue]:
    data = upstox_status(service.reader.settings.upstox_validation_root)
    return response(data, "SANITIZED_BOUNDED_LIVE_VALIDATION_NOT_PRICE_REDISTRIBUTION")


@router.get("/upstox-private/reliance")
def upstox_private_reliance(service: Research) -> Envelope[JsonValue]:
    settings = service.reader.settings
    if not settings.upstox_private_view or settings.upstox_validation_root is None:
        raise APIError(
            "PRIVATE_PROVIDER_VIEW_DISABLED",
            "Explicit local private provider view is disabled.",
            503,
        )
    from workers.providers.private_view import view

    try:
        data = view(settings.upstox_validation_root, model_root=settings.research_run_root)
        return response(data, "UPSTOX_PRIVATE_TRANSIENT_DESCRIPTIVE_NOT_RETAINED_OR_MODEL_READY")
    except (ValueError, OSError, sqlite3.Error):
        raise APIError(
            "PRIVATE_PROVIDER_VIEW_UNAVAILABLE",
            "Verified private provider view is unavailable.",
            503,
        ) from None


def alpha_attempts() -> int | None:
    """Read the existing diagnostic ledger; never create/reset it or reserve another call."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return None
    root = Path(base) / "AlphaLens/provider-state"
    path = root / "alpha-vantage-requests.sqlite3"
    if not path.is_file():
        return None
    try:
        verify(root)
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM attempts WHERE at>?", (time.time() - 86400,)
                ).fetchone()[0]
            )
    except (OSError, ValueError, sqlite3.Error):
        return None


@router.get("/comparison")
def provider_comparison(service: Research) -> Envelope[JsonValue]:
    settings = service.reader.settings
    try:
        sessions = service.reader.calendar()["sessions"]
        archive = max(date.fromisoformat(row["session_date"]) for row in sessions)
    except (ValueError, KeyError, APIError):
        archive = None
    selected = None
    state = "NOT_CONFIGURED"
    if settings.providers_root:
        try:
            selected = ProviderStore(settings.providers_root).status(time.time())[
                "selected_provider"
            ]
            state = "AVAILABLE_ACQUISITION_DISABLED"
        except (ValueError, OSError, sqlite3.Error):
            state = "UNAVAILABLE"
    data = comparison(
        archive_session=archive,
        credential_present=credential_present() if settings.environment != "test" else False,
        selected_provider=selected,
        local_attempts=alpha_attempts() if settings.environment != "test" else None,
    )
    data["operational_store"] = state
    verified = upstox_status(settings.upstox_validation_root)
    data["upstox_validation"] = verified
    for provider in data["providers"]:
        if provider["provider"] == "upstox" and verified["authentication"] == "ACCEPTED":
            provider.update(
                {
                    "status": "AUTHENTICATED_USAGE_NOT_CLEARED",
                    "authentication": "GENUINE_READ_ONLY_GET_ACCEPTED",
                    "credential_configured": verified["credential_readback"],
                    "account_status": "MARKET_DATA_ACCESS_ACCEPTED_OTHER_STATUS_NOT_VERIFIED",
                    "nse_support": "NSE_IDENTITY_AND_CANDLES_VERIFIED"
                    if verified["nse_identity_verified"] and verified["valid_candles"]
                    else "HTTP_ACCESS_ACCEPTED_IDENTITY_OR_SCHEMA_PENDING",
                    "blocker": (
                        "Retention, automation, ML analysis, adjustment/action/publication "
                        "and independent model evidence remain unverified"
                    ),
                }
            )
    result = response(data, "PRIMARY_DOCUMENTATION_AND_PRIOR_SANITIZED_CHECKS_NOT_LIVE_QUOTES")
    return result.model_copy(
        update={
            "classification": Classification(
                data_reality="PROVIDER_DOCUMENTATION_NOT_MARKET_OBSERVATIONS",
                final_vintage=None,
                research_profile=None,
            )
        }
    )
