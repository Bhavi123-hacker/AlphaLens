"""Thin GET-only routers. Synchronous persisted I/O runs in FastAPI's worker pool."""

from datetime import date
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import JsonValue

from .core.domain_errors import APIError
from .portfolio_reads import PortfolioReads
from .schemas import Envelope, Error, Horizon, PredictionPoint, PricePoint
from .services import ResearchService, response

router = APIRouter(
    prefix="/api/v1",
    responses={
        403: {"model": Error},
        404: {"model": Error},
        413: {"model": Error},
        422: {"model": Error},
        503: {"model": Error},
        429: {"model": Error},
        504: {"model": Error},
        500: {"model": Error},
    },
)
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0, le=10000)]
Identity = Annotated[str, Query(min_length=1, max_length=200)]
ModelID = Annotated[str, Query(pattern="^[0-9a-f]{64}$")]
RecordPath = Annotated[str, Path(min_length=1, max_length=200)]
HashPath = Annotated[str, Path(pattern="^[0-9a-f]{64}$")]
Phase = Literal["development", "2025", "2026"]


def research(request: Request) -> ResearchService:
    return cast(ResearchService, request.app.state.research)


def portfolios(request: Request) -> PortfolioReads:
    return cast(PortfolioReads, request.app.state.portfolios)


Research = Annotated[ResearchService, Depends(research)]
Portfolios = Annotated[PortfolioReads, Depends(portfolios)]


def dates(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise APIError("INVALID_DATE_RANGE", "Start date must precede end date.", 422)


def freshness(service: ResearchService) -> Envelope[JsonValue]:
    root = service.reader.settings.research_data_root
    if root is None:
        return response(
            {"freshness": "UNAVAILABLE", "live_data": "UNAVAILABLE"},
            "UNCONFIGURED",
            status="UNAVAILABLE",
            reasons=("DATASET_NOT_CONFIGURED",),
        )
    manifest = service.reader.manifest("canonical-manifest.json")
    calendar = service.reader.calendar()
    observed = [
        s["session_date"]
        for s in calendar["sessions"]
        if s["price_status"] == "SOURCE_ROWS_PRESENT"
    ]
    latest = date.fromisoformat(max(observed)) if observed else None
    return response(
        {
            "last_evidenced_market_session": latest,
            "freshness": "STALE" if latest and latest < date.today() else "HISTORICAL_EOD",
            "live_data": "UNAVAILABLE",
            "calendar_completeness": calendar["completeness"],
        },
        "P5_RESEARCH_OBSERVED_SESSION_CALENDAR",
        manifest["dataset_id"],
        as_of=latest,
        reasons=("ARCHIVE_NOT_LIVE", "ASSUMED_AVAILABILITY_NOT_EXCHANGE_PUBLICATION"),
    )


@router.get("/health", tags=["system"])
def health() -> Envelope[JsonValue]:
    return response(
        {
            "backend": "ALIVE",
            "application_version": "0.1.0",
            "api_version": "p17.api.v1",
            "production_ready": False,
        },
        "PROCESS_LIVENESS",
    )


@router.get("/system/data-freshness", tags=["system"])
def data_freshness(service: Research) -> Envelope[JsonValue]:
    return freshness(service)


@router.get("/system/status", tags=["system"])
def system_status(service: Research) -> Envelope[JsonValue]:
    settings = service.reader.settings
    components: dict[str, JsonValue] = {}
    for name, operation in (
        ("stock_catalog", lambda: service.catalog.search("", 1, 0)),
        ("stored_features", lambda: service.reader.manifest("supervised-manifest.json")),
        ("research_reports", lambda: service.reader.report("ml/real-model-runs.json")),
        (
            "backtest_reports",
            lambda: service.reader.report("backtesting/real-research-economic-audit.json"),
        ),
    ):
        try:
            operation()
            components[name] = {"status": "AVAILABLE"}
        except APIError as exc:
            components[name] = {"status": "UNAVAILABLE", "reason": exc.code}
    components["database"] = PortfolioReads(settings).readiness()
    root = settings.research_run_root
    components["run_artifact_sources"] = {
        "status": "AVAILABLE"
        if root and (root / "p9/oos").is_dir() and (root / "p10").is_dir()
        else "UNAVAILABLE",
        "verification": "PER_REQUEST_SHA256_AND_LINEAGE",
    }
    components["current_rank_risk_signal_explanations"] = {
        "status": "UNAVAILABLE",
        "reason": "NO_PERSISTED_REAL_CURRENT_SESSION_OUTPUTS",
    }
    components["production"] = {
        "status": "BLOCKED",
        "reasons": [
            "P21_AUTHORIZATION_NOT_IMPLEMENTED",
            "PRODUCTION_DATA_NOT_CLEARED",
            "UNRESOLVED_ECONOMIC_EVIDENCE",
            "44_HIGH_OS_SECURITY_FINDINGS_AT_APPROVED_BASELINE",
        ],
    }
    return response(
        {
            "backend": "LOCAL_RESEARCH_ONLY",
            "components": components,
            "model_loading": "DISABLED",
            "training_execution": "DISABLED",
            "paper_execution": "DISABLED",
            "production_ready": False,
        },
        "LOCAL_READ_ADAPTERS",
    )


@router.get(
    "/ready",
    tags=["system"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue]}},
)
def ready(service: Research) -> JSONResponse:
    status = system_status(service)
    if not isinstance(status.data, dict) or not isinstance(status.data["components"], dict):
        raise APIError("STATUS_INVALID", "Component readiness could not be established.")
    components = status.data["components"]
    required = (
        "stock_catalog",
        "stored_features",
        "research_reports",
        "backtest_reports",
        "run_artifact_sources",
        "database",
    )
    healthy = True
    for key in required:
        component = components[key]
        if not isinstance(component, dict) or component.get("status") not in (
            "AVAILABLE",
            "REACHABLE",
        ):
            healthy = False
    result = response(
        {"research_read_ready": healthy, "production_ready": False, "components": components},
        "RESEARCH_READINESS",
        status="AVAILABLE" if healthy else "UNAVAILABLE",
        reasons=() if healthy else ("REQUIRED_READ_COMPONENT_UNAVAILABLE",),
    )
    return JSONResponse(result.model_dump(mode="json"), status_code=200 if healthy else 503)


@router.get("/stocks", tags=["stocks"])
def stocks(
    service: Research,
    q: Annotated[str, Query(max_length=100)] = "",
    limit: Limit = 100,
    offset: Offset = 0,
) -> Envelope[JsonValue]:
    return service.stocks(q, limit, offset)


@router.get("/stocks/{security_id}", tags=["stocks"])
def stock(security_id: RecordPath, service: Research) -> Envelope[JsonValue]:
    return service.stock(security_id)


@router.get("/stocks/{security_id}/history", tags=["stocks"])
def history(
    security_id: RecordPath,
    service: Research,
    start: date | None = None,
    end: date | None = None,
    limit: Limit = 250,
    offset: Offset = 0,
) -> Envelope[list[PricePoint]]:
    dates(start, end)
    return service.history(security_id, start, end, limit, offset)


@router.get("/stocks/{security_id}/indicators", tags=["stocks"])
def indicators(
    security_id: RecordPath,
    service: Research,
    feature: Identity,
    start: date | None = None,
    end: date | None = None,
    limit: Limit = 250,
    offset: Offset = 0,
) -> Envelope[JsonValue]:
    dates(start, end)
    return service.indicators(security_id, feature, start, end, limit, offset)


@router.get("/research/models", tags=["research"])
def models(
    service: Research,
    horizon: Horizon | None = None,
    phase: Phase | None = None,
    limit: Limit = 25,
    offset: Offset = 0,
) -> Envelope[JsonValue]:
    return service.models(None, horizon, phase, limit, offset)


@router.get("/research/models/{model_id}", tags=["research"])
def model(model_id: HashPath, service: Research) -> Envelope[JsonValue]:
    return service.models(model_id, None, None, 1, 0)


@router.get("/research/evaluation", tags=["research"])
def evaluation(service: Research) -> Envelope[JsonValue]:
    return service.evaluation()


@router.get("/research/predictions", tags=["research"])
def predictions(
    service: Research,
    model_id: ModelID,
    security_id: Identity,
    start: date | None = None,
    end: date | None = None,
    limit: Limit = 250,
    offset: Offset = 0,
) -> Envelope[list[PredictionPoint]]:
    dates(start, end)
    return service.predictions(model_id, security_id, start, end, limit, offset)


@router.get("/research/backtests", tags=["backtests"])
def backtests(
    service: Research,
    horizon: Horizon | None = None,
    phase: Phase | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> Envelope[JsonValue]:
    return service.backtests(None, horizon, phase, limit, offset)


@router.get("/research/backtests/{backtest_id}", tags=["backtests"])
def backtest(backtest_id: HashPath, service: Research) -> Envelope[JsonValue]:
    return service.backtests(backtest_id, None, None, 1, 0)


@router.get("/research/backtests/{backtest_id}/performance", tags=["backtests"])
def backtest_performance(
    backtest_id: HashPath,
    service: Research,
    start: date | None = None,
    end: date | None = None,
    limit: Limit = 250,
    offset: Offset = 0,
) -> Envelope[JsonValue]:
    dates(start, end)
    return service.backtest_performance(backtest_id, limit, offset, start, end)


@router.get(
    "/opportunities",
    tags=["decision-evidence"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue]}},
)
@router.get(
    "/rankings",
    tags=["decision-evidence"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue]}},
)
@router.get(
    "/signals",
    tags=["decision-evidence"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue]}},
)
def unavailable_decisions() -> JSONResponse:
    result = response(
        None,
        "P11_P14_PERSISTED_REAL_OUTPUTS",
        status="UNAVAILABLE",
        reasons=(
            "NO_PERSISTED_REAL_CURRENT_SESSION_OUTPUTS",
            "RESEARCH_METRICS_ARE_NOT_LIVE_SIGNALS",
            "P11_P14_CALIBRATION_UNCHANGED",
        ),
    )
    return JSONResponse(result.model_dump(mode="json"), status_code=503)


@router.get(
    "/signals/{security_id}",
    tags=["decision-evidence"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue] | Error}},
)
@router.get(
    "/explanations/{security_id}",
    tags=["decision-evidence"],
    response_model=Envelope[JsonValue],
    responses={503: {"model": Envelope[JsonValue] | Error}},
)
def unavailable_security_decisions(security_id: RecordPath, service: Research) -> JSONResponse:
    service.catalog.security(security_id)
    return unavailable_decisions()


@router.get("/portfolios", tags=["portfolio"])
def portfolio_accounts(
    service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.accounts(False, limit, offset)


@router.get("/portfolios/{portfolio_id}", tags=["portfolio"])
def portfolio_metadata(portfolio_id: RecordPath, service: Portfolios) -> Envelope[JsonValue]:
    return service.portfolio(portfolio_id, "metadata", 100, 0)


@router.get("/portfolios/{portfolio_id}/holdings", tags=["portfolio"])
def portfolio_holdings(
    portfolio_id: RecordPath, service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.portfolio(portfolio_id, "holdings", limit, offset)


@router.get("/portfolios/{portfolio_id}/transactions", tags=["portfolio"])
def portfolio_transactions(
    portfolio_id: RecordPath, service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.portfolio(portfolio_id, "transactions", limit, offset)


@router.get("/portfolios/{portfolio_id}/performance", tags=["portfolio"])
def portfolio_performance(portfolio_id: RecordPath, service: Portfolios) -> Envelope[JsonValue]:
    return service.portfolio(portfolio_id, "performance", 100, 0)


@router.get("/paper/accounts", tags=["paper"])
def paper_accounts(
    service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.accounts(True, limit, offset)


@router.get("/paper/accounts/{account_id}", tags=["paper"])
def paper_metadata(account_id: RecordPath, service: Portfolios) -> Envelope[JsonValue]:
    return service.paper(account_id, "metadata", 100, 0)


@router.get("/paper/accounts/{account_id}/orders", tags=["paper"])
def paper_orders(
    account_id: RecordPath, service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.paper(account_id, "orders", limit, offset)


@router.get("/paper/accounts/{account_id}/trades", tags=["paper"])
def paper_trades(
    account_id: RecordPath, service: Portfolios, limit: Limit = 100, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.paper(account_id, "trades", limit, offset)


@router.get("/paper/accounts/{account_id}/performance", tags=["paper"])
def paper_performance(
    account_id: RecordPath, service: Portfolios, limit: Limit = 250, offset: Offset = 0
) -> Envelope[JsonValue]:
    return service.paper(account_id, "performance", limit, offset)
