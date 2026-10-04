"""TEST-ONLY deterministic records; vendor-specific parsing awaits provider approval."""

from decimal import Decimal

import pytest

from alphalens_data.contracts import PriceBar
from alphalens_data.errors import DataContractError
from alphalens_data.normalization import canonical_bytes
from conftest import make_test_only_price, make_test_only_provenance


def test_revisions_preserved_and_input_order_irrelevant(price: PriceBar) -> None:
    revised = make_test_only_price(
        provenance=make_test_only_provenance(revision_id="TEST_ONLY_REVISION_2"),
        close=Decimal("10"),
    )
    forward = canonical_bytes([price, revised])
    assert forward == canonical_bytes([revised, price])
    assert b"TEST_ONLY_REVISION_1" in forward and b"TEST_ONLY_REVISION_2" in forward


def test_exact_duplicate_deduplicated(price: PriceBar) -> None:
    assert canonical_bytes([price, price]) == canonical_bytes([price])


def test_conflicting_duplicate_revision_rejected(price: PriceBar) -> None:
    with pytest.raises(DataContractError, match="CONFLICTING_DUPLICATE_REVISION"):
        canonical_bytes([price, make_test_only_price(close=Decimal("10"))])
