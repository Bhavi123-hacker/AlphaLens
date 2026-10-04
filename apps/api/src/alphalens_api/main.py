"""Local health service. Does not implement P17 or expose product data."""

from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from alphalens_api.core.config import Settings
from alphalens_api.core.errors import error_response
from alphalens_api.core.logging import configure_logging
from alphalens_api.health import router


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
    app = FastAPI(title="AlphaLens foundation", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings or Settings()
    app.include_router(router)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    app.add_middleware(RequestContextMiddleware)

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
