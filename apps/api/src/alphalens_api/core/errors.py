"""Stable safe errors; no raw validation or exception details."""

from fastapi import Request
from fastapi.responses import JSONResponse


def error_response(request: Request, code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error_code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
