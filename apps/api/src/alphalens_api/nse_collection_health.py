"""Authenticated read-only derived collection monitoring; no history replay on GET."""

import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import JsonValue
from workers.nse_market import collection_alerts, operational_health

from .core.domain_errors import APIError
from .nse_market import _envelope, _roots
from .routes import Research
from .schemas import Envelope

router = APIRouter(prefix="/api/v1/nse-market", tags=["private collection monitoring"])


@router.get("/collection-health")
def health(
    service: Research,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[JsonValue]:
    roots = _roots(service)
    if roots is None:
        raise APIError(
            "COLLECTION_HEALTH_NOT_CONFIGURED", "Collection monitoring is unavailable.", 503
        )
    try:
        data = collection_alerts.load(roots[0])
        if data:
            read_at = datetime.fromisoformat(data["read_at"])
            age = (datetime.now(UTC) - read_at).total_seconds()
            if read_at.utcoffset() is None or age < 0:
                raise ValueError("COLLECTION_HEALTH_TIME_REJECTED")
            data["snapshot_age_seconds"] = age
            data["snapshot_stale"] = age > 86400
        data["local_alerts"] = collection_alerts.listing(
            roots[0], limit=limit, test_only=service.reader.settings.test_only_evidence
        )
        data["provider_requests"] = 0
        data["outbound_delivery"] = False
        data["operational_readiness"] = operational_health.load(roots[0], at=datetime.now(UTC))
        return _envelope(data, service)
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error):
        raise APIError(
            "COLLECTION_HEALTH_EVIDENCE_INVALID",
            "Saved collection monitoring could not be verified.",
            503,
        ) from None
