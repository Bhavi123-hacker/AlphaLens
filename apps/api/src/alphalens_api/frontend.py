"""Compiled public application shell only; private data always stays behind API auth."""

import re
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from .core.config import Settings

PAGES = frozenset(
    {
        "",
        ".",
        "login",
        "market",
        "heatmap",
        "screener",
        "compare",
        "analysis",
        "research",
        "experimental-ai",
        "intelligence",
        "opportunities",
        "portfolios",
        "my-portfolio",
        "preferences",
        "watchlists",
        "journal",
        "copilot",
        "research-alerts",
        "decision-desk",
        "paper",
        "backtests",
        "data-health",
        "notifications",
        "settings",
    }
)
ASSET = re.compile(r"assets/[A-Za-z0-9_.-]+\.(?:js|css|woff2?|svg|png|ico)$")
SHELL_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)


def validate(settings: Settings) -> Path:
    root = settings.frontend_root
    if root is None or not root.is_dir() or not (root / "index.html").is_file():
        raise ValueError("COMPILED_FRONTEND_NOT_INSTALLED")
    root = root.resolve()
    for private in (
        settings.auth_root,
        settings.alerts_root,
        settings.operations_root,
        settings.providers_root,
        settings.daily_root,
        settings.research_data_root,
        settings.research_run_root,
        settings.research_report_root,
        settings.personal_root,
        settings.experimental_nse_root,
    ):
        if private and (
            root.is_relative_to(private.resolve()) or private.resolve().is_relative_to(root)
        ):
            raise ValueError("FRONTEND_PRIVATE_STORAGE_OVERLAP")
    if (root / "index.html").stat().st_size > 100_000:
        raise ValueError("FRONTEND_SHELL_SIZE_INVALID")
    shell = (root / "index.html").read_text(encoding="utf-8")
    if not re.search(r'<script[^>]+src="/assets/[A-Za-z0-9_.-]+\.js"', shell):
        raise ValueError("FRONTEND_COMPILED_ENTRY_REQUIRED")
    return root


class LocalFrontend(StaticFiles):
    def __init__(self, settings: Settings) -> None:
        super().__init__(directory=validate(settings), follow_symlink=False)

    async def get_response(self, path: str, scope: Scope) -> Response:
        path = path.replace("\\", "/")
        if scope["method"] not in {"GET", "HEAD"}:
            raise HTTPException(405)
        if path in PAGES or re.fullmatch(r"stocks/[^/]{1,200}", path):
            path = "index.html"
        elif path != "third-party-notices.txt" and not ASSET.fullmatch(path):
            # Unknown API routes and private/dot files never fall back to HTML.
            raise HTTPException(404)
        response = await super().get_response(path, scope)
        response.headers["Content-Security-Policy"] = SHELL_CSP
        return response
