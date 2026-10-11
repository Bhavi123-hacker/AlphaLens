"""P20 local reads and explicitly enabled, origin-guarded notification projections."""

import json
import sqlite3
from typing import Annotated, Any, cast

from fastapi import APIRouter, Path, Query, Request
from pydantic import JsonValue, ValidationError
from workers.alerts.contracts import Category, Lifecycle, Preferences, Severity
from workers.alerts.store import AlertError, AlertStore

from .core.domain_errors import APIError
from .schemas import Classification, Envelope, Page
from .services import response

router = APIRouter(prefix="/api/v1/alerts", tags=["local notifications"])
AlertID = Annotated[str, Path(pattern="^[a-f0-9]{64}$")]


def configured_router(enable_writes: bool) -> APIRouter:
    selected = APIRouter()
    for route in router.routes:
        if enable_writes or "POST" not in getattr(route, "methods", set()):
            selected.routes.append(route)
    return selected


def store(request: Request) -> AlertStore:
    root = request.app.state.settings.alerts_root
    if root is None:
        raise APIError(
            "ALERT_STORE_UNAVAILABLE", "Configure and initialize the local P20 alert store."
        )
    return AlertStore(root)


def wrap(data: Any, page: Page | None = None, *, test_only: bool = False) -> Envelope[JsonValue]:
    result = response(data, "P20_DURABLE_OPERATIONAL_EVENTS", page=page)
    return result.model_copy(
        update={
            "version": "p20.api.v1",
            "classification": Classification(
                data_reality="TEST_ONLY" if test_only else "PERSISTED_OPERATIONAL_EVIDENCE",
                usage_classification="TEST_ONLY" if test_only else "RESEARCH_ONLY",
                final_vintage=None,
                research_profile=None,
            ),
        }
    )


def safe(call: Any) -> Any:
    try:
        return call()
    except AlertError as exc:
        code = str(exc)
        raise APIError(
            code,
            "Local alert evidence or state is unavailable.",
            404
            if code == "ALERT_NOT_FOUND"
            else 409
            if code == "INVALID_ALERT_TRANSITION"
            else 503,
        ) from None
    except (sqlite3.Error, OSError, ValueError, KeyError):
        raise APIError("ALERT_STORE_INVALID", "Local alert storage failed verification.") from None


async def mutation_body(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    if not settings.alert_mutations:
        raise APIError(
            "LOCAL_ALERT_MUTATIONS_DISABLED",
            "Use the local CLI or explicitly enable guarded alert controls.",
            403,
        )
    if (
        len(request.headers.getlist("origin")) != 1
        or request.headers.get("origin") not in settings.cors_origins
    ):
        raise APIError(
            "ALERT_WRITE_ORIGIN_REJECTED",
            "An explicit allowed local frontend origin is required.",
            403,
        )
    if (
        request.headers.getlist("x-alphalens-local") != ["p20"]
        or request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        raise APIError(
            "ALERT_WRITE_CONTEXT_REJECTED", "The local JSON notification context is required.", 403
        )
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 8192:
            raise APIError(
                "ALERT_WRITE_SIZE_LIMIT", "Notification control payload exceeds its bound.", 413
            )
    try:
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise APIError(
            "INVALID_REQUEST", "Notification controls require a JSON object.", 422
        ) from None


@router.get("")
def history(
    request: Request,
    category: Category | None = None,
    severity: Severity | None = None,
    lifecycle: Lifecycle | None = None,
    delivery: Annotated[
        str | None,
        Query(pattern="^(NOT_REQUESTED|PENDING|DELIVERED|FAILED|RETRY_PENDING|SUPPRESSED)$"),
    ] = None,
    search: Annotated[str, Query(max_length=100)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> Envelope[JsonValue]:
    rows, total = safe(
        lambda: store(request).listing(
            category=category,
            severity=severity,
            lifecycle=lifecycle,
            delivery=delivery,
            search=search,
            limit=limit,
            offset=offset,
            test_only=request.app.state.settings.test_only_evidence,
        )
    )
    return wrap(
        rows,
        Page(limit=limit, offset=offset, total=total, has_more=offset + limit < total),
        test_only=request.app.state.settings.test_only_evidence,
    )


@router.get("/unread-count")
def unread(request: Request) -> Envelope[JsonValue]:
    return wrap(
        {
            "count": safe(
                lambda: store(request).unread(
                    test_only=request.app.state.settings.test_only_evidence
                )
            )
        },
        test_only=request.app.state.settings.test_only_evidence,
    )


@router.get("/preferences")
def preferences(request: Request) -> Envelope[JsonValue]:
    value = safe(lambda: store(request).preferences())
    return wrap(
        dict(
            preferences=value.model_dump(mode="json"),
            mutations_enabled=request.app.state.settings.alert_mutations,
            channels={
                "IN_APP": "AVAILABLE",
                "EMAIL": "UNAVAILABLE_NO_AUTHORIZED_SMTP",
                "DESKTOP": "UNAVAILABLE_NOT_DELIVERY_TESTED",
            },
            stock_alerts="DISABLED_EVIDENCE_GATES_UNMET",
            scheduling="DISABLED",
        ),
        test_only=request.app.state.settings.test_only_evidence,
    )


@router.post("/preferences")
async def update_preferences(request: Request) -> Envelope[JsonValue]:
    body = await mutation_body(request)
    try:
        value = Preferences.model_validate(body)
    except ValidationError:
        raise APIError(
            "INVALID_REQUEST", "Notification preference validation failed.", 422
        ) from None
    safe(lambda: store(request).set_preferences(value))
    return preferences(request)


@router.get("/{alert_id}")
def detail(request: Request, alert_id: AlertID) -> Envelope[JsonValue]:
    return wrap(
        safe(
            lambda: store(request).get(
                alert_id, test_only=request.app.state.settings.test_only_evidence
            )
        ),
        test_only=request.app.state.settings.test_only_evidence,
    )


@router.post("/{alert_id}/state")
async def update_state(request: Request, alert_id: AlertID) -> Envelope[JsonValue]:
    body = await mutation_body(request)
    if (
        set(body) != {"state"}
        or not isinstance(body["state"], str)
        or body["state"] not in {"READ", "ACKNOWLEDGED", "RESOLVED"}
    ):
        raise APIError("INVALID_REQUEST", "Use READ, ACKNOWLEDGED or RESOLVED.", 422)
    # Classification and checksum verification precede projection mutation.
    safe(
        lambda: store(request).get(
            alert_id, test_only=request.app.state.settings.test_only_evidence
        )
    )
    target = cast(Lifecycle, body["state"])
    safe(lambda: store(request).transition(alert_id, target))
    return detail(request, alert_id)
