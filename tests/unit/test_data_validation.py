"""TEST-ONLY constructed invalid bars/filings, never historical market records."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from alphalens_data.contracts import FundamentalRecord, PriceBar
from conftest import make_test_only_price, make_test_only_provenance


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open", Decimal("0")),
        ("close", Decimal("NaN")),
        ("low", Decimal("13")),
        ("high", Decimal("10")),
        ("volume", -1),
        ("volume", 1.5),
        ("volume", True),
        ("currency", "USD"),
        ("interval", "1m"),
        ("adjusted_close", Decimal("5")),
        ("turnover", Decimal("-1")),
    ],
)
def test_reject_invalid_bar(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        make_test_only_price(**{field: value})


def test_reject_naive_session_timestamp() -> None:
    with pytest.raises(ValidationError):
        make_test_only_price(session_close_at=datetime(2000, 1, 3, 10))


def test_reject_future_session_close() -> None:
    with pytest.raises(ValidationError):
        make_test_only_price(session_close_at=datetime(2000, 1, 3, 12, tzinfo=UTC))


def test_publication_and_revision_are_not_period_end() -> None:
    record = FundamentalRecord.model_validate(
        {
            "security_id": "TEST_ONLY_SECURITY",
            "provenance": make_test_only_provenance(),
            "period_end": "1999-12-31",
            "values": [{"name": "eps", "value": None, "unit": "INR/share"}],
        }
    )
    assert record.values[0].value is None
    assert record.provenance.published_at is not None
    assert record.provenance.revision_id == "TEST_ONLY_REVISION_1"


def test_extra_vendor_fields_rejected(price: PriceBar) -> None:
    with pytest.raises(ValidationError):
        PriceBar.model_validate(price.model_dump() | {"vendor_token": "TEST_ONLY"})
