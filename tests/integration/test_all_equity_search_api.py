"""TEST_ONLY exhaustive identity contract; no provider requests or real forecasts."""

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.build_p17_test_evidence import build
from scripts.build_p21_test_auth import AuthenticatedTransport
from test_nse_universe import isin, reply, row
from test_saved_nse_market_api import saved_view
from workers.nse_market import discovery
from workers.providers import universe

from alphalens_api import nse_saved
from alphalens_api.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_every_listing_opens_and_search_filters_paginate_without_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows: list[dict[str, Any]] = []
    for number in range(55):
        code = isin(f"INE{number:03}A0101")
        native = row(f"TEST_ONLY_{number:03}", code=code)
        rows.extend(
            [
                native,
                {
                    **native,
                    "segment": "BSE_EQ",
                    "exchange": "BSE",
                    "instrument_key": "BSE_EQ|" + code,
                    "instrument_type": "A",
                    "security_type": None,
                },
            ]
        )
    snapshot = universe.parse(reply(rows), expanded=True)
    assert snapshot.summary["verified_eligible_common_equities"] == 110
    app = create_app(
        build(tmp_path / "TEST_ONLY").model_copy(
            update={"experimental_nse_v2_root": tmp_path / "TEST_ONLY_v2"}
        )
    )
    monkeypatch.setattr(discovery, "load_catalog", lambda root: snapshot)
    monkeypatch.setattr(nse_saved, "_view", lambda service: saved_view())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/v1/nse-market/universe")).status_code == 401
    async with AsyncClient(
        transport=AuthenticatedTransport(app=app), base_url="http://testserver"
    ) as client:
        found: list[str] = []
        for page in range(1, 7):
            response = await client.get(
                "/api/v1/nse-market/universe", params={"page": page, "page_size": 20}
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["total"] == 110 and data["provider_requests"] == 0
            found.extend(r["instrument_key"] for r in data["rows"])
        assert len(set(found)) == 110
        for key in found:
            response = await client.get("/api/v1/nse-market/saved-history", params={"key": key})
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["rows"] == [] and data["provider_requests"] == 0
            assert data["security"]["availability_state"] == "HISTORY_NOT_COLLECTED"
            assert data["security"]["close"] is None
            if key.startswith("BSE"):
                assert data["security"]["ml_status"] == "MODEL_NOT_VALIDATED_FOR_THIS_SEGMENT"
        for exchange in ("NSE", "BSE"):
            response = await client.get(
                "/api/v1/nse-market/universe", params={"exchange": exchange, "page_size": 100}
            )
            assert response.json()["data"]["total"] == 55
            assert all(r["exchange"] == exchange for r in response.json()["data"]["rows"])
        for query, count in (
            (rows[0]["isin"].lower(), 2),
            (rows[0]["instrument_key"].lower(), 1),
            ("test_only_000", 2),
            ("company", 110),
        ):
            response = await client.get("/api/v1/nse-market/universe", params={"q": query})
            assert response.json()["data"]["total"] == count
        assert (await client.get("/api/v1/nse-market/universe?exchange=UNKNOWN")).status_code == 422
        assert (await client.get("/api/v1/nse-market/universe?page_size=101")).status_code == 422
