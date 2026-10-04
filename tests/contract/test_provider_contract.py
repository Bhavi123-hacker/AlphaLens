"""TEST-ONLY capability metadata is not vendor verification."""

import pytest
from pydantic import ValidationError

from alphalens_data.contracts import (
    Capability,
    CapabilityEvidence,
    CapabilityStatus,
    HistoryRequest,
    ProviderCapabilities,
)
from alphalens_data.errors import ProviderNotSelectedError
from alphalens_data.provider import MarketDataProvider
from alphalens_data.sample_ingestion import evaluate_price_sample


def test_missing_capability_is_unknown() -> None:
    capabilities = ProviderCapabilities(provider_id="TEST_ONLY")
    assert capabilities.status(Capability.HISTORICAL_MEMBERSHIP) == CapabilityStatus.UNKNOWN


def test_verified_support_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        CapabilityEvidence(
            capability=Capability.EOD_PRICES, status=CapabilityStatus.VERIFIED_SUPPORTED
        )


def test_interface_cannot_instantiate_as_provider() -> None:
    with pytest.raises(TypeError):
        MarketDataProvider()  # type: ignore[abstract]


def test_no_provider_does_not_generate_sample(history_request: HistoryRequest) -> None:
    with pytest.raises(ProviderNotSelectedError, match="PROVIDER_NOT_SELECTED"):
        evaluate_price_sample(None, history_request)
