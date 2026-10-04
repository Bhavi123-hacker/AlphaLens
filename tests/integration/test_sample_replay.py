"""TEST-ONLY bounded replay. Does NOT establish real provider capability or P1 completion."""

from datetime import UTC, datetime

import pytest

from alphalens_data.contracts import (
    Capability,
    CapabilityEvidence,
    CapabilityStatus,
    CorporateAction,
    FundamentalRecord,
    HistoryRequest,
    PriceBar,
    ProviderCapabilities,
    UniverseMembership,
    UniverseRequest,
)
from alphalens_data.errors import DataContractError
from alphalens_data.provider import CapturedBatch, MarketDataProvider
from alphalens_data.sample_ingestion import evaluate_price_sample


class FixtureProvider(MarketDataProvider):
    """TEST-ONLY double. Never register or use this class in application code."""

    def __init__(self, price: PriceBar, *, complete: bool = True, verified: bool = True) -> None:
        self.price = price
        self.complete = complete
        self.verified = verified

    def get_capabilities(self) -> ProviderCapabilities:
        evidence = tuple(
            CapabilityEvidence(
                capability=capability,
                status=CapabilityStatus.VERIFIED_SUPPORTED,
                evidence_reference="TEST-ONLY constructed metadata, NOT vendor evidence",
                verified_at=datetime(2000, 1, 11, tzinfo=UTC),
                scope="TEST-ONLY fixture",
            )
            for capability in (Capability.EOD_PRICES, Capability.LICENSED_SAMPLE_USE)
        )
        return ProviderCapabilities(
            provider_id="TEST_ONLY", evidence=evidence if self.verified else ()
        )

    def get_prices(self, request: HistoryRequest) -> CapturedBatch[PriceBar]:
        return CapturedBatch(
            "TEST_ONLY", (self.price,), b"TEST-ONLY constructed payload", self.complete
        )

    def get_fundamentals(self, request: HistoryRequest) -> CapturedBatch[FundamentalRecord]:
        raise DataContractError("TEST_ONLY_UNSUPPORTED")

    def get_corporate_actions(self, request: HistoryRequest) -> CapturedBatch[CorporateAction]:
        raise DataContractError("TEST_ONLY_UNSUPPORTED")

    def get_universe(self, request: UniverseRequest) -> CapturedBatch[UniverseMembership]:
        raise DataContractError("TEST_ONLY_UNSUPPORTED")


def test_replay_preserves_origin_and_is_deterministic(
    price: PriceBar, history_request: HistoryRequest
) -> None:
    provider = FixtureProvider(price)
    first = evaluate_price_sample(provider, history_request, origin="TEST_ONLY")
    second = evaluate_price_sample(provider, history_request, origin="TEST_ONLY")
    assert first == second
    assert first.manifest.origin == "TEST_ONLY"
    assert first.manifest.record_count == 1
    assert b"TEST_ONLY" in first.normalized_payload
    assert first.manifest.evidence_scope == "BOUNDED_PRICE_SAMPLE_NOT_FULL_P1_ACCEPTANCE"


def test_test_fixture_cannot_be_real_evidence(
    price: PriceBar, history_request: HistoryRequest
) -> None:
    with pytest.raises(DataContractError, match="SAMPLE_ORIGIN_MISMATCH"):
        evaluate_price_sample(FixtureProvider(price), history_request)


def test_unknown_capability_does_not_trigger_download(
    price: PriceBar, history_request: HistoryRequest
) -> None:
    with pytest.raises(DataContractError, match="EOD_PRICES_UNKNOWN"):
        evaluate_price_sample(
            FixtureProvider(price, verified=False), history_request, origin="TEST_ONLY"
        )


def test_incomplete_page_chain_is_rejected(
    price: PriceBar, history_request: HistoryRequest
) -> None:
    with pytest.raises(DataContractError, match="INCOMPLETE_PROVIDER_BATCH"):
        evaluate_price_sample(
            FixtureProvider(price, complete=False), history_request, origin="TEST_ONLY"
        )
