"""Authenticated, read-only provider comparison. No outbound market-data requests."""

import json
import os
import sqlite3
import time
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
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


@router.get("/upstox-private/reference")
def company_reference(
    service: Research, instrument_key: str = Query(pattern=r"^NSE_EQ\|[A-Z0-9]{12}$")
) -> Envelope[JsonValue]:
    from workers.providers.reference import load

    from alphalens_data.errors import DataContractError

    try:
        return private_response(
            load(private_root(service), instrument_key), "UPSTOX_EXPLICIT_CURRENT_REFERENCE"
        )
    except (DataContractError, ValueError, OSError, sqlite3.Error):
        raise APIError(
            "COMPANY_REFERENCE_UNAVAILABLE",
            "The bounded provider reference is unavailable; no archive or synthetic substitution.",
            503,
        ) from None


def private_root(service: Research) -> Path:
    settings = service.reader.settings
    if not settings.upstox_private_view or settings.upstox_validation_root is None:
        raise APIError(
            "PRIVATE_PROVIDER_VIEW_DISABLED", "Private Upstox observations are disabled.", 503
        )
    return settings.upstox_validation_root


def private_response(data: Any, source: str) -> Envelope[JsonValue]:
    return response(data, source).model_copy(
        update={
            "version": "p31.provider.v1",
            "classification": Classification(
                final_vintage=None,
                research_profile=None,
                usage_classification="PRIVATE_TRANSIENT_DESCRIPTIVE",
            ),
            "quality_status": "PROVIDER_BASIS_ACTIONS_AND_CALENDAR_UNVERIFIED",
        }
    )


def archive_identity(service: Research, identity: dict[str, Any]) -> str | None:
    """Positive dated catalog match on ISIN and symbol; never a name-only join."""
    return archive_identities(service, [identity])[0]


def archive_identities(service: Research, identities: list[dict[str, Any]]) -> list[str | None]:
    """One bounded read for a master page; ambiguous latest dated aliases fail closed."""
    if not identities:
        return []
    if len(identities) > 100:
        raise ValueError("ARCHIVE_IDENTITY_PAGE_BOUND")
    isins = tuple({i["isin"] for i in identities})
    with closing(service.catalog.connection()) as connection:
        rows = connection.execute(
            "SELECT DISTINCT s.security_id,a.isin,a.symbol FROM securities s "
            "JOIN aliases a ON a.security_id=s.security_id AND a.last_observed=s.last_observed "
            "WHERE a.isin IN (SELECT value FROM json_each(?)) AND NOT EXISTS "
            "(SELECT 1 FROM aliases other WHERE other.security_id=s.security_id "
            "AND other.last_observed=s.last_observed "
            "AND (other.isin IS NOT a.isin OR other.symbol IS NOT a.symbol))",
            (json.dumps(isins),),
        ).fetchall()
    matches: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        matches.setdefault((row["isin"], row["symbol"]), set()).add(row["security_id"])
    result = []
    for identity in identities:
        values = matches.get((identity["isin"], identity["symbol"]), set())
        result.append(next(iter(values)) if len(values) == 1 else None)
    return result


@router.get("/upstox-private/instruments")
def private_instruments(
    service: Research,
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
) -> Envelope[JsonValue]:
    from workers.providers.upstox_terminal import search

    root = private_root(service)
    try:
        data = search(root, q, limit=limit, offset=offset)
        matches = archive_identities(service, data["instruments"])
        for identity, canonical in zip(data["instruments"], matches, strict=True):
            identity["canonical_security_id"] = canonical
        return private_response(data, "UPSTOX_VERIFIED_CURRENT_MASTER_NOT_HISTORICAL_UNIVERSE")
    except (ValueError, OSError, sqlite3.Error):
        raise APIError(
            "PRIVATE_MASTER_UNAVAILABLE", "Current NSE instrument master is unavailable.", 503
        ) from None


@router.get("/upstox-private/watchlist")
def private_watchlist(
    service: Research, instrument_keys: str = Query(min_length=1, max_length=1500)
) -> Envelope[JsonValue]:
    from workers.providers.watchlist import load

    try:
        return private_response(
            load(private_root(service), tuple(instrument_keys.split(","))),
            "UPSTOX_BOUNDED_SELECTED_WATCHLIST_NOT_FULL_NSE",
        )
    except (ValueError, OSError, sqlite3.Error):
        raise APIError(
            "PRIVATE_WATCHLIST_UNAVAILABLE", "Verified selected watchlist unavailable.", 503
        ) from None


@router.get("/upstox-private/snapshot")
def private_snapshot(
    service: Research,
    instrument_keys: str = Query(default="", max_length=100),
    security_id: str | None = Query(default=None, max_length=256),
) -> Envelope[JsonValue]:
    from workers.providers.upstox_terminal import snapshot

    root = private_root(service)
    if bool(instrument_keys) == bool(security_id):
        raise APIError(
            "ONE_PRIVATE_IDENTITY_SELECTION_REQUIRED",
            "Choose current master instruments or one archive identity.",
            422,
        )
    aliases = None
    if security_id:
        aliases = service.catalog.security(security_id)["observed_identity_evidence"]
    try:
        data = snapshot(
            root, keys=tuple(instrument_keys.split(",")) if instrument_keys else (), aliases=aliases
        )
        for item in data["items"]:
            item["identity"] = {
                **item["identity"],
                "canonical_security_id": archive_identity(service, item["identity"]),
            }
        return private_response(data, "UPSTOX_PRIVATE_TRANSIENT_NOT_ARCHIVE_OR_MODEL_READY")
    except (ValueError, OSError, sqlite3.Error) as exc:
        # Only known identity contract reasons are surfaced, never provider errors.
        reason = str(exc)
        identity_reasons = {
            "CURRENT_AND_ARCHIVE_IDENTITY_DIFFER_CURRENT_MASTER_SELECTION_REQUIRED",
            "CURRENT_MASTER_IDENTITY_MISSING_OR_AMBIGUOUS",
            "CANONICAL_ISIN_AND_SYMBOL_REQUIRED",
            "CANONICAL_IDENTITY_AMBIGUOUS",
        }
        raise APIError(
            reason if reason in identity_reasons else "PRIVATE_PROVIDER_VIEW_UNAVAILABLE",
            "Verified provider observations are unavailable. "
            "Select an exact current-master identity if the archive identity differs.",
            503,
        ) from None


@router.get("/upstox-private/statistics")
def private_statistics(
    service: Research,
    instrument_key: str = Query(max_length=30),
    start: date | None = None,
    end: date | None = None,
) -> Envelope[JsonValue]:
    from workers.personal.analytics import observed
    from workers.providers.watchlist import cached

    if start and end and start > end:
        raise APIError("INVALID_DATE_WINDOW", "Start must precede end.", 422)
    item = cached(private_root(service), (instrument_key,)).get(instrument_key)
    if not item:
        raise APIError("PROVIDER_MEMORY_EXPIRED", "Explicitly load the selected stock again.", 503)
    rows = [
        r
        for r in item.get("rows", [])
        if (not start or r["session"] >= str(start)) and (not end or r["session"] <= str(end))
    ]
    return private_response(observed(rows), "UPSTOX_CACHED_OBSERVED_RAW_PRICE_STATISTICS")


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
