"""Process health is distinct from database readiness and market-data availability."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from alphalens_api.core.config import Settings
from alphalens_api.core.errors import error_response

router = APIRouter(prefix="/api/v1/health", tags=["health"])


async def check_database(url: str) -> bool:
    # Psycopg async connections reject Windows' default ProactorEventLoop.
    # A bounded synchronous probe in a worker thread keeps the API loop unblocked.
    import asyncio

    return await asyncio.to_thread(_check_database_sync, url)


def _check_database_sync(url: str) -> bool:
    try:
        from psycopg import connect

        with connect(url, connect_timeout=3, options="-c statement_timeout=3000") as conn:
            return conn.execute("SELECT 1").fetchone() == (1,)
    except (ImportError, OSError):
        return False
    except Exception:
        # Never leak a driver exception (it can contain connection credentials).
        return False


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive", "scope": "foundation_only"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    if settings.database_url is None:
        return error_response(
            request, "DATABASE_NOT_CONFIGURED", "Database readiness is not configured.", 503
        )
    if not await check_database(settings.database_url.get_secret_value()):
        return error_response(request, "DATABASE_UNAVAILABLE", "Database is unavailable.", 503)
    return JSONResponse({"status": "ready", "scope": "foundation_only", "database": "reachable"})
