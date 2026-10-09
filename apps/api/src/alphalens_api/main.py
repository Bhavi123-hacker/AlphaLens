"""P17 loopback-only research read service; production deployment remains blocked."""

from ipaddress import ip_address
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from alphalens_api.core.config import Settings
from alphalens_api.core.domain_errors import APIError
from alphalens_api.core.errors import error_response
from alphalens_api.core.logging import configure_logging
from alphalens_api.health import router
from alphalens_api.portfolio_reads import PortfolioReads
from alphalens_api.routes import router as api_router
from alphalens_api.services import ResearchService


class LocalOnlyMiddleware:
    """No authentication substitute: reject non-loopback peers and foreign browser origins."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        try:
            local = client is not None and ip_address(client[0]).is_loopback
        except ValueError:
            local = (
                self.settings.environment == "test"
                and client is not None
                and client[0] == "testclient"
            )
        origins = [v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"origin"]
        if (
            not local
            or len(origins) > 1
            or (origins and origins[0] not in self.settings.cors_origins)
        ):
            await JSONResponse(
                {
                    "error_code": "LOCAL_ACCESS_ONLY",
                    "message": "Only configured local research access is permitted.",
                    "request_id": scope.get("state", {}).get("request_id", ""),
                },
                status_code=403,
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)


class ResponseLimitMiddleware:
    """Bound serialized JSON responses before their original headers or body are sent."""

    def __init__(self, app: ASGIApp, maximum: int) -> None:
        self.app, self.maximum = app, maximum

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        rejected = False

        async def bounded_send(message: Message) -> None:
            nonlocal rejected
            if message["type"] == "http.response.start":
                lengths = [int(v) for k, v in message.get("headers", []) if k == b"content-length"]
                if lengths and lengths[0] > self.maximum:
                    rejected = True
                    await JSONResponse(
                        {
                            "error_code": "RESPONSE_LIMIT",
                            "message": (
                                "Response exceeds the configured size limit; narrow the query."
                            ),
                            "request_id": scope.get("state", {}).get("request_id", ""),
                        },
                        status_code=413,
                    )(scope, receive, send)
            if not rejected:
                await send(message)

        await self.app(scope, receive, bounded_send)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = configure_logging()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Generate our own correlation ID; do not trust caller-supplied arbitrary text.
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        status_code = 500

        async def safe_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode("ascii")),
                        (b"x-content-type-options", b"nosniff"),
                        (b"cache-control", b"no-store"),
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, safe_send)
        self.logger.info(
            "request.completed", extra={"request_id": request_id, "status_code": status_code}
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings()
    app = FastAPI(
        title="AlphaLens research-only read API",
        version="p17.api.v1",
        description="Local decision support. RESEARCH_ONLY, NOT PRODUCTION PIT. "
        "No training, execution, production forecasts or real trading.",
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.state.settings = configured
    app.state.research = ResearchService(configured)
    app.state.portfolios = PortfolioReads(configured)
    app.include_router(router)
    app.include_router(api_router)

    @app.get("/docs", include_in_schema=False)
    def docs() -> RedirectResponse:
        # Offline contract access; no CDN-hosted Swagger assets or JavaScript dependency.
        return RedirectResponse("/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(configured.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]"]
        + (["testserver"] if configured.environment == "test" else []),
    )
    app.add_middleware(LocalOnlyMiddleware, settings=configured)
    app.add_middleware(ResponseLimitMiddleware, maximum=configured.max_response_bytes)
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(APIError)
    async def domain_error(request: Request, exc: APIError) -> JSONResponse:
        return error_response(request, exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(request, "INVALID_REQUEST", "Request validation failed.", 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_REJECTED"
        return error_response(request, code, "Request could not be served.", exc.status_code)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> Response:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        # Middleware cannot amend the outer server-error response headers.
        response = error_response(request, "INTERNAL_ERROR", "Request could not be served.", 500)
        response.headers["X-Request-ID"] = str(UUID(request_id))
        response.headers["Cache-Control"] = "no-store"
        configure_logging().error("request.failed", extra={"request_id": request_id})
        return response

    return app


app = create_app()
