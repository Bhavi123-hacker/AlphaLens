"""Mandatory authentication and closed local security projection endpoints."""

import json
import re
import secrets
import sqlite3
from contextlib import suppress
from typing import Any, cast

from fastapi import APIRouter, Request, Response
from starlette.concurrency import run_in_threadpool

from alphalens_api.core.domain_errors import APIError

from .store import ABSOLUTE_SECONDS, AuthError, AuthStore

COOKIE = "alphalens_session"
PUBLIC = frozenset({"/api/v1/health/live", "/api/v1/health", "/api/v1/auth/login"})
router = APIRouter(prefix="/api/v1/auth", tags=["local account security"])


def store(request: Request) -> AuthStore:
    root = request.app.state.settings.auth_root
    if root is None:
        raise APIError(
            "AUTH_NOT_INITIALIZED", "Initialize the protected local operator store.", 503
        )
    return AuthStore(root)


def safe(call: Any) -> Any:
    try:
        return call()
    except AuthError as exc:
        code = str(exc)
        status = (
            429
            if code == "LOGIN_RATE_LIMITED"
            else 401
            if code in {"AUTHENTICATION_REQUIRED", "INVALID_CREDENTIALS"}
            else 404
            if code == "SESSION_NOT_FOUND"
            else 422
            if code
            in {"PASSWORD_POLICY_REJECTED", "PASSWORD_MUST_CHANGE", "USERNAME_POLICY_REJECTED"}
            else 503
        )
        message = (
            "Authentication failed."
            if status == 401
            else "Local security operation could not be completed."
        )
        raise APIError(code, message, status) from None
    except (sqlite3.Error, OSError, ValueError):
        raise APIError(
            "AUTH_STORE_UNAVAILABLE", "Local security storage is unavailable.", 503
        ) from None


def origin(request: Request) -> None:
    if (
        len(request.headers.getlist("origin")) != 1
        or request.headers.get("origin") not in request.app.state.settings.cors_origins
    ):
        raise APIError("AUTH_ORIGIN_REJECTED", "An approved local browser Origin is required.", 403)
    if (
        len(request.headers.getlist("content-type")) != 1
        or request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        raise APIError("AUTH_JSON_REQUIRED", "Use the local JSON security interface.", 403)


def authenticate(request: Request) -> None:
    if request.url.path in PUBLIC:
        return
    cookies = request.headers.getlist("cookie")
    # Duplicate session names or Cookie headers must not select ambiguous credentials.
    if (
        len(cookies) > 1
        or sum(part.strip().startswith(COOKIE + "=") for v in cookies for part in v.split(";")) != 1
    ):
        # Fixed 401 request-status logs remain available if the store is absent.
        with suppress(APIError, AuthError, sqlite3.Error, OSError):
            store(request).denied()
        raise APIError("AUTHENTICATION_REQUIRED", "Sign in to the local workspace.", 401)
    identity = safe(lambda: store(request).session(request.cookies.get(COOKIE)))
    request.state.operator = identity
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin(request)
        values = request.headers.getlist("x-csrf-token")
        if (
            len(values) != 1
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", values[0])
            or not secrets.compare_digest(values[0], identity["csrf_token"])
        ):
            raise APIError(
                "CSRF_REJECTED", "Refresh the authenticated session before this action.", 403
            )


async def body(request: Request, fields: set[str]) -> dict[str, str]:
    origin(request)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise APIError("AUTH_BODY_LIMIT", "Security payload exceeds its bound.", 413)
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        value = json.loads(data, object_pairs_hook=unique)
        if (
            not isinstance(value, dict)
            or set(value) != fields
            or any(
                not isinstance(v, str) or len(v) > 128 or len(v.encode("utf-8")) > 1024
                for v in value.values()
            )
        ):
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise APIError("INVALID_REQUEST", "Security input validation failed.", 422) from None


@router.post("/login")
async def login(request: Request, response: Response) -> dict[str, Any]:
    if request.headers.getlist("x-alphalens-local") != ["p21"]:
        raise APIError("LOGIN_CONTEXT_REQUIRED", "Use the local login interface.", 403)
    value = await body(request, {"username", "password"})
    raw, identity = await run_in_threadpool(
        lambda: safe(lambda: store(request).login(value["username"], value["password"]))
    )
    # A supplied session is never reused. Retire it only after successful credentials.
    previous = request.cookies.get(COOKIE)
    if previous:
        try:
            old = store(request).session(previous)
            store(request).revoke(old["account_id"], old["session_id"], event="SESSION_ROTATED")
        except (AuthError, sqlite3.Error, OSError):
            pass
    response.set_cookie(
        COOKIE,
        raw,
        max_age=ABSOLUTE_SECONDS,
        path="/api/v1",
        httponly=True,
        secure=request.app.state.settings.access_mode == "hosted_private",
        samesite="strict",
    )
    return cast(dict[str, Any], identity)


@router.get("/session")
def session(request: Request) -> dict[str, Any]:
    return dict(
        request.state.operator,
        scope="SINGLE_OPERATOR_WORKSPACE",
        transport="HTTPS_EDGE_PRIVATE_HOSTING"
        if request.app.state.settings.access_mode == "hosted_private"
        else "HTTP_LOOPBACK_NO_TLS",
    )


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    await body(request, set())
    value = request.state.operator
    safe(lambda: store(request).revoke(value["account_id"], value["session_id"], event="LOGOUT"))
    response.delete_cookie(
        COOKIE,
        path="/api/v1",
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.access_mode == "hosted_private",
    )
    return {"status": "LOGGED_OUT"}


@router.post("/password")
async def change_password(request: Request, response: Response) -> dict[str, str]:
    value = await body(request, {"current_password", "new_password"})
    await run_in_threadpool(
        lambda: safe(
            lambda: store(request).change_password(
                request.state.operator["account_id"],
                value["current_password"],
                value["new_password"],
            )
        )
    )
    response.delete_cookie(
        COOKIE,
        path="/api/v1",
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.access_mode == "hosted_private",
    )
    return {"status": "PASSWORD_CHANGED_ALL_SESSIONS_REVOKED"}


@router.get("/sessions")
def sessions(request: Request) -> dict[str, Any]:
    return {"sessions": safe(lambda: store(request).sessions(request.state.operator["account_id"]))}


@router.post("/sessions/revoke")
async def revoke(request: Request) -> dict[str, str]:
    value = await body(request, {"session_id"})
    safe(lambda: store(request).revoke(request.state.operator["account_id"], value["session_id"]))
    return {"status": "SESSION_REVOKED"}
