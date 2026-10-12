"""Future read-only provider interface. No acquisition or credential handling here."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol


@dataclass(frozen=True)
class ProviderGate:
    configured: bool = False
    rights_cleared: bool = False
    technically_verified: bool = False
    account_status: Literal["NOT_CONFIGURED", "UNDER_REVIEW", "INACTIVE", "ACTIVE"] = (
        "NOT_CONFIGURED"
    )

    @property
    def reason(self) -> str:
        if not self.configured:
            return "PROVIDER_NOT_CONFIGURED"
        if self.account_status != "ACTIVE":
            return "ACCOUNT_" + self.account_status
        if not self.rights_cleared:
            return "PROVIDER_RIGHTS_NOT_CLEARED"
        if not self.technically_verified:
            return "PROVIDER_TECHNICAL_EVIDENCE_MISSING"
        return "OPERATOR_ACTIVATION_NOT_AUTHORIZED"


@dataclass(frozen=True)
class UnavailableCapability:
    capability: str
    reason: str
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    publication_time: datetime | None = None
    retrieval_time: datetime | None = None


@dataclass(frozen=True)
class EvidencedQuote:
    """Future compatible payload, never populated by the disabled adapter."""

    instrument_id: str
    provider_revision: str
    payload_sha256: str
    last_price: Decimal
    event_time: datetime
    received_at: datetime
    publication_time: datetime | None
    classification: Literal["RESEARCH_ONLY"] = "RESEARCH_ONLY"


class ReadOnlyProvider(Protocol):
    """Future adapters must return evidenced typed results, never invented quotes."""

    def quote(self, instrument: str) -> EvidencedQuote | UnavailableCapability: ...
    def ltp(self, instrument: str) -> EvidencedQuote | UnavailableCapability: ...
    def ohlc(self, instrument: str) -> UnavailableCapability: ...
    def market_status(self) -> UnavailableCapability: ...
    def instrument_lookup(self, query: str) -> UnavailableCapability: ...
    def option_chain(self, instrument: str) -> UnavailableCapability: ...


class DisabledProvider:
    def __init__(self, gate: ProviderGate | None = None) -> None:
        self.gate = gate or ProviderGate()

    def quote(self, instrument: str) -> UnavailableCapability:
        return UnavailableCapability("quote", self.gate.reason)

    def ltp(self, instrument: str) -> UnavailableCapability:
        return UnavailableCapability("ltp", self.gate.reason)

    def ohlc(self, instrument: str) -> UnavailableCapability:
        return UnavailableCapability("ohlc", self.gate.reason)

    def market_status(self) -> UnavailableCapability:
        return UnavailableCapability("market_status", self.gate.reason)

    def instrument_lookup(self, query: str) -> UnavailableCapability:
        return UnavailableCapability("instrument_lookup", self.gate.reason)

    def option_chain(self, instrument: str) -> UnavailableCapability:
        return UnavailableCapability("option_chain", self.gate.reason)
