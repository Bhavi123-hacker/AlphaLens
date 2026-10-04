"""TEST-ONLY temporal boundaries; no real membership or session calendar implied."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from alphalens_data.contracts import PriceBar, UniverseMembership
from alphalens_data.errors import DataContractError
from alphalens_data.validation import eligible_at, member_at
from conftest import make_test_only_price, make_test_only_provenance


def test_no_future_availability_and_exact_boundary(price: PriceBar) -> None:
    at = datetime(2000, 1, 3, 11, tzinfo=UTC)
    assert not eligible_at(price, at - timedelta(microseconds=1))
    assert eligible_at(price, at)


def test_later_ingestion_is_not_live_knowledge(price: PriceBar) -> None:
    at = datetime(2000, 1, 3, 11, tzinfo=UTC)
    assert eligible_at(price, at, mode="historical")
    assert not eligible_at(price, at, mode="live")
    assert eligible_at(price, datetime(2000, 1, 10, tzinfo=UTC), mode="live")


def test_unknown_availability_is_ineligible() -> None:
    provenance = make_test_only_provenance(
        available_at=None, availability_basis="UNKNOWN", availability_evidence=None
    )
    assert not eligible_at(
        make_test_only_price(provenance=provenance), datetime(2000, 2, 1, tzinfo=UTC)
    )


def test_naive_decision_is_rejected(price: PriceBar) -> None:
    with pytest.raises(DataContractError, match="NAIVE_DECISION_TIMESTAMP"):
        eligible_at(price, datetime(2000, 1, 11))


def test_publication_must_precede_availability() -> None:
    with pytest.raises(ValidationError):
        make_test_only_provenance(published_at=datetime(2000, 1, 4, tzinfo=UTC))


def test_known_availability_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        make_test_only_provenance(availability_basis="UNKNOWN")


def test_membership_effective_interval_is_half_open() -> None:
    member = UniverseMembership(
        security_id="TEST_ONLY_SECURITY",
        provenance=make_test_only_provenance(),
        universe_id="NIFTY_500",
        effective_from=datetime(2000, 1, 4, tzinfo=UTC),
        effective_to=datetime(2000, 1, 6, tzinfo=UTC),
    )
    assert not member_at(member, datetime(2000, 1, 3, 12, tzinfo=UTC))
    assert member_at(member, datetime(2000, 1, 4, tzinfo=UTC))
    assert not member_at(member, datetime(2000, 1, 6, tzinfo=UTC))


def test_invalid_membership_interval_rejected() -> None:
    with pytest.raises(ValidationError):
        UniverseMembership(
            security_id="TEST_ONLY_SECURITY",
            provenance=make_test_only_provenance(),
            universe_id="NIFTY_500",
            effective_from=datetime(2000, 1, 4, tzinfo=UTC),
            effective_to=datetime(2000, 1, 4, tzinfo=UTC),
        )


def test_offset_equivalence_and_utc_canonicalization() -> None:
    provenance = make_test_only_provenance(
        available_at=datetime(2000, 1, 3, 16, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    )
    assert provenance.available_at == datetime(2000, 1, 3, 11, tzinfo=UTC)
    assert provenance.available_at is not None and provenance.available_at.tzinfo == UTC


def test_future_membership_announcement_cannot_be_current_member() -> None:
    membership = UniverseMembership(
        security_id="TEST_ONLY_SECURITY",
        provenance=make_test_only_provenance(),
        universe_id="NIFTY_500",
        effective_from=datetime(2000, 2, 1, tzinfo=UTC),
    )
    assert not member_at(membership, datetime(2000, 1, 15, tzinfo=UTC))
