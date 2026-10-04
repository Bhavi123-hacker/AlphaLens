"""TEST-ONLY opt-in real PostgreSQL check; no schema or financial records created."""

import asyncio
import os

import pytest

from alphalens_api.health import check_database


@pytest.mark.database
def test_real_postgres_connectivity() -> None:
    url = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL not configured: ALPHALENS_TEST_DATABASE_URL absent")
    assert asyncio.run(check_database(url)), "PostgreSQL connectivity failed (details redacted)"
