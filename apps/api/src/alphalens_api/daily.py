"""Additive P19 persisted reads. Never invokes the worker, inference or training."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request
from pydantic import JsonValue

from alphalens_data.daily.providers import check_source
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError

from .core.domain_errors import APIError
from .schemas import Classification, Envelope, Error, Page
from .services import response

router = APIRouter(
    prefix="/api/v1/daily",
    tags=["daily research"],
    responses={503: {"model": Error}, 404: {"model": Error}, 422: {"model": Error}},
)
RunID = Annotated[str, Path(pattern="^[a-f0-9]{64}$")]


def records(request: Request) -> list[dict[str, Any]]:
    settings = request.app.state.settings
    if settings.daily_root is None:
        return []
    try:
        values = Store(settings.daily_root).receipts()
        if not settings.test_only_evidence and any(v["mode"] == "TEST_ONLY" for v in values):
            raise APIError(
                "TEST_ONLY_DAILY_EVIDENCE_BLOCKED",
                "Test evidence cannot be served as real research.",
            )
        return values
    except (DataContractError, OSError, ValueError, KeyError):
        raise APIError(
            "DAILY_EVIDENCE_INVALID", "Daily evidence is unavailable or failed verification."
        ) from None


def public(row: dict[str, Any]) -> dict[str, Any]:
    # The persisted request contains source filenames and local operational details.
    # Do not expose request identity, paths, raw manifests or serialized model objects.
    result = {
        k: row[k]
        for k in (
            "run_id",
            "mode",
            "session",
            "started_at",
            "completed_at",
            "source_received_at",
            "state",
            "counts",
            "reasons",
            "coverage_scope",
            "data_reality",
            "usage_classification",
            "final_vintage",
            "inference_status",
            "ranking_status",
            "signal_status",
            "production_ready",
        )
    }
    identity = row["identity"]
    result["lineage"] = dict(
        source=identity["provider"]["source"],
        source_revision=identity["provider"]["revision"],
        payload_sha256=identity["payload_sha256"],
        feature_registry_id=identity["feature_registry_id"],
        baseline_identity=identity["baseline_identity"],
        decision_policy_id=identity.get("decision_policy_id"),
        model_artifact_ids=[],
    )
    return result


def wrap(
    data: Any, row: dict[str, Any] | None = None, page: Page | None = None
) -> Envelope[JsonValue]:
    result = response(
        data,
        "P19_IMMUTABLE_RUN_RECEIPTS",
        row["run_id"] if row else None,
        as_of=date.fromisoformat(row["session"]) if row else None,
        page=page,
    )
    return result.model_copy(
        update={
            "version": "p19.api.v1",
            "classification": Classification(
                data_reality=row["data_reality"] if row else "REAL_MARKET_OBSERVATIONS",
                usage_classification=row["usage_classification"] if row else "RESEARCH_ONLY",
                final_vintage=row["final_vintage"] if row else None,
                research_profile=None,
            ),
        }
    )


@router.get("/status")
def status(request: Request) -> Envelope[JsonValue]:
    rows = records(request)
    real = [r for r in rows if r["mode"] == "DAILY"]
    completed = [r for r in real if r["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}]
    latest = real[0] if real else None
    return wrap(
        dict(
            configured=request.app.state.settings.daily_root is not None,
            pipeline_status=latest["state"] if latest else "NOT_RUN",
            live_data_activation="BLOCKED",
            scheduled_execution="DISABLED",
            latest_attempted_session=latest["session"] if latest else None,
            latest_successful_research_session=completed[0]["session"] if completed else None,
            last_source_receipt=completed[0]["source_received_at"] if completed else None,
            freshness="UNAVAILABLE",
            feature_readiness="UNAVAILABLE",
            inference_readiness="UNAVAILABLE",
            ranking_status="UNAVAILABLE",
            signal_status="UNAVAILABLE",
            provider=check_source(),
            historical_replay_count=sum(r["mode"] == "HISTORICAL_REPLAY" for r in rows),
            production_ready=False,
        )
    )


@router.get("/runs")
def runs(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> Envelope[JsonValue]:
    rows = records(request)
    return wrap(
        [public(r) for r in rows[offset : offset + limit]],
        row=rows[0] if rows else None,
        page=Page(limit=limit, offset=offset, has_more=len(rows) > offset + limit, total=len(rows)),
    )


@router.get("/checkpoints")
def checkpoints(request: Request) -> Envelope[JsonValue]:
    records(request)  # Apply classification and root validation first.
    root = request.app.state.settings.daily_root
    try:
        return wrap(Store(root).checkpoints() if root is not None else [])
    except (DataContractError, OSError, ValueError, KeyError):
        raise APIError(
            "DAILY_CHECKPOINT_INVALID", "Operational checkpoint verification failed."
        ) from None


@router.get("/runs/{run_id}")
def run(request: Request, run_id: RunID) -> Envelope[JsonValue]:
    row = next((r for r in records(request) if r["run_id"] == run_id), None)
    if row is None:
        raise APIError(
            "DAILY_RUN_NOT_FOUND", "No published daily receipt matches this identity.", 404
        )
    return wrap(public(row), row)


@router.get("/latest")
def latest(request: Request) -> Envelope[JsonValue]:
    rows = [
        r
        for r in records(request)
        if r["mode"] == "DAILY" and r["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    ]
    if not rows:
        raise APIError(
            "GENUINE_DAILY_OBSERVATION_UNAVAILABLE",
            "No verified new-session research snapshot is published.",
        )
    return wrap(public(rows[0]), rows[0])


@router.get("/data-quality")
def quality(
    request: Request, run_id: Annotated[str, Query(pattern="^[a-f0-9]{64}$")]
) -> Envelope[JsonValue]:
    run(request, run_id)
    root = request.app.state.settings.daily_root
    try:
        value = Store(root).product(run_id, "validation")
        # Safe report summary only; artifact manifests may contain local raw paths.
        return wrap(
            {k: value[k] for k in ("summary", "dataset_blocked")},
            next(r for r in records(request) if r["run_id"] == run_id),
        )
    except (DataContractError, OSError, KeyError):
        raise APIError(
            "DAILY_QUALITY_UNAVAILABLE", "No published validation summary exists for this run."
        ) from None


@router.get("/predictions")
@router.get("/rankings")
@router.get("/signals")
def withheld() -> Envelope[JsonValue]:
    raise APIError(
        "DAILY_EVIDENCE_GATE_NOT_MET",
        "Daily source/inference acceptance is blocked. No current ranking or signal is authorized.",
    )


@router.get("/runs/{run_id}/prices")
@router.get("/runs/{run_id}/features")
def observed_product(
    request: Request,
    run_id: RunID,
    security_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> Envelope[JsonValue]:
    row = next((r for r in records(request) if r["run_id"] == run_id), None)
    if row is None:
        raise APIError("DAILY_RUN_NOT_FOUND", "No published run matches this identity.", 404)
    kind = "canonical" if request.url.path.endswith("/prices") else "features"
    try:
        values = Store(request.app.state.settings.daily_root).product(run_id, kind)["rows"]
    except (OSError, DataContractError, KeyError):
        raise APIError(
            "DAILY_PRODUCT_UNAVAILABLE", "No accepted product exists for this run."
        ) from None
    if security_id:
        values = [v for v in values if v["security_id"] == security_id]
    return wrap(
        values[offset : offset + limit],
        row,
        Page(limit=limit, offset=offset, has_more=len(values) > offset + limit, total=len(values)),
    )
