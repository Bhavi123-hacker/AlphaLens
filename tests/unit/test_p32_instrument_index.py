"""TEST_ONLY realistic identity counts; no market data or provider requests."""

import time
from datetime import UTC, datetime

import pytest
from workers.providers.search_index import InstrumentIndex
from workers.providers.watchlist import plan

from alphalens_data.providers.multi_contracts import Instrument


def test_thousands_of_current_identities_indexed_paginated_and_ranked() -> None:
    instruments = tuple(
        Instrument(
            provider="upstox",
            provider_key=f"NSE_EQ|INE{i:09d}",
            symbol=f"TEST_ONLY_{i:04d}",
            isin=f"INE{i:09d}",
            name=f"TEST_ONLY Corporation {i}",
            exchange="NSE",
            segment="NSE_EQ",
            instrument_type="EQ",
            observed_at=datetime.now(UTC),
            identity_evidence="TEST_ONLY_CONSTRUCTED_MASTER",
            revision_sha256="a" * 64,
        )
        for i in range(5000)
    )
    started = time.perf_counter()
    indexed = InstrumentIndex(instruments)
    build_seconds = time.perf_counter() - started
    pages = [indexed.search("", 100, offset)[0] for offset in range(0, 5000, 100)]
    assert len({i.provider_key for page in pages for i in page}) == 5000
    assert indexed.search("TEST_ONLY_1234", 20, 0)[0][0].symbol == "TEST_ONLY_1234"
    assert indexed.search("NSE_EQ|INE000001234", 20, 0)[0][0].isin == "INE000001234"
    assert indexed.search("Corporation 1234", 20, 0)[1] == 1
    assert indexed.search("BSE_EQ", 20, 0)[1] == 0
    assert build_seconds < 10


def test_quote_planner_uses_documented_capacity_and_bounded_local_scope() -> None:
    keys = tuple(f"NSE_EQ|INE{i:09d}" for i in range(50))
    result = plan(keys)
    assert result["documented_quote_batch_limit"] == 500 and result["quote_batches"] == 1
    assert result["maximum_provider_gets"] == 2 and result["historical_series_requests"] == 0
    with pytest.raises(ValueError):
        plan((*keys, "NSE_EQ|INE000000050"))
    with pytest.raises(ValueError):
        plan((keys[0], keys[0]))
