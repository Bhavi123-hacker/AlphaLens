"""Provider-neutral boundary. No default provider, web scraper or synthetic fallback."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from alphalens_data.contracts import (
    CorporateAction,
    FundamentalRecord,
    HistoryRequest,
    PriceBar,
    ProviderCapabilities,
    Record,
    UniverseMembership,
    UniverseRequest,
)


@dataclass(frozen=True)
class CapturedBatch[T: Record]:
    """One bounded, fully paginated response; no URLs, auth headers or credentials.

    Adapter owns vendor parsing and pagination. raw_payload is exactly the received
    data payload, not HTTP headers. Adapters must reject credential-bearing payloads.
    Retention rights are checked before raw_payload can be persisted.
    """

    provider_id: str
    records: tuple[T, ...]
    raw_payload: bytes
    complete: bool


class MarketDataProvider(ABC):
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return scoped evidence; unspecified support is UNKNOWN."""

    @abstractmethod
    def get_prices(self, request: HistoryRequest) -> CapturedBatch[PriceBar]:
        """Return complete EOD history, retaining revisions and availability."""

    @abstractmethod
    def get_fundamentals(self, request: HistoryRequest) -> CapturedBatch[FundamentalRecord]:
        """Never replace as-of fundamentals with current/restated values."""

    @abstractmethod
    def get_corporate_actions(self, request: HistoryRequest) -> CapturedBatch[CorporateAction]:
        """Return dated/revisioned events without inventing adjustment factors."""

    @abstractmethod
    def get_universe(self, request: UniverseRequest) -> CapturedBatch[UniverseMembership]:
        """Historical membership only; today's constituents are not a fallback."""
