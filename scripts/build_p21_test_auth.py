"""Explicit TEST_ONLY authentication for preserved domain-contract integration tests."""

import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, Request, Response

from alphalens_api.auth.routes import COOKIE
from alphalens_api.auth.store import AuthStore


class AuthenticatedTransport(ASGITransport):
    """Inject a genuinely persisted test session, never a runtime bypass or fixed token."""

    def __init__(self, app: FastAPI, **kwargs: Any) -> None:
        root = Path(
            tempfile.mkdtemp(
                prefix="TEST_ONLY_auth_", dir=os.environ.get("ALPHALENS_TEST_TEMP_ROOT")
            )
        )
        app.state.settings.auth_root = root
        store = AuthStore(root)
        store.initialize()
        secret = secrets.token_urlsafe(24)
        store.bootstrap("test_operator", secret)
        self._session, identity = store.login("test_operator", secret)
        self._csrf = identity["csrf_token"]
        super().__init__(app=app, **kwargs)

    async def handle_async_request(self, request: Request) -> Response:
        request.headers.setdefault("Cookie", f"{COOKIE}={self._session}")
        request.headers.setdefault("X-CSRF-Token", self._csrf)
        return await super().handle_async_request(request)
