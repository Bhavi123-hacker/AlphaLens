"""TEST-ONLY constructed edge cases. NOT market history or provider evidence."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from alphalens_data.contracts import HistoryRequest, PriceBar, Provenance


def make_test_only_provenance(**changes: object) -> Provenance:
    values: dict[str, object] = {
        "source_id": "TEST_ONLY",
        "source_record_id": "TEST_ONLY_BAR_1",
        "revision_id": "TEST_ONLY_REVISION_1",
        "ingested_at": datetime(2000, 1, 10, tzinfo=UTC),
        "published_at": datetime(2000, 1, 3, 10, tzinfo=UTC),
        "available_at": datetime(2000, 1, 3, 11, tzinfo=UTC),
        "availability_basis": "VERIFIED_PUBLICATION",
        "availability_evidence": "TEST-ONLY constructed eligibility fixture",
        "origin": "TEST_ONLY",
    }
    return Provenance.model_validate(values | changes)


def make_test_only_price(**changes: object) -> PriceBar:
    values: dict[str, object] = {
        "security_id": "TEST_ONLY_SECURITY",
        "provenance": make_test_only_provenance(),
        "session_date": date(2000, 1, 3),
        "session_close_at": datetime(2000, 1, 3, 10, tzinfo=UTC),
        "open": Decimal("10"),
        "high": Decimal("12"),
        "low": Decimal("9"),
        "close": Decimal("11"),
        "volume": 5,
    }
    return PriceBar.model_validate(values | changes)


@pytest.fixture
def price() -> PriceBar:
    return make_test_only_price()


@pytest.fixture
def history_request() -> HistoryRequest:
    return HistoryRequest(
        security_ids=("TEST_ONLY_SECURITY",),
        start_session=date(2000, 1, 3),
        end_session=date(2000, 1, 3),
        as_of=datetime(2000, 1, 11, tzinfo=UTC),
    )
