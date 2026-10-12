"""Closed event vocabulary; notification text never comes from untrusted payloads."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from alphalens_data.contracts import Contract
from alphalens_data.daily.contracts import Provider, Session
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum

Category = Literal[
    "DATA_SOURCE", "PIPELINE", "ML_RESEARCH", "PORTFOLIO", "PAPER_TRADING", "STOCK_SIGNAL"
]
Severity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
Lifecycle = Literal["NEW", "READ", "ACKNOWLEDGED", "RESOLVED"]
Safe = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.: -]{1,200}$")]
Reason = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,99}$")]

# Code -> category, severity, title, safe explanation. Signals have no enabled code.
TEMPLATES: dict[str, tuple[Category, Severity, str, str]] = {
    "PROSPECTIVE_EVALUATED": (
        "ML_RESEARCH",
        "INFO",
        "Prospective evaluation recorded",
        "Immutable forecast evidence has a recorded raw-price horizon outcome. "
        "This does not establish economic performance, model acceptance or a stock signal.",
    ),
    "OPERATION_FAILURE": (
        "PIPELINE",
        "ERROR",
        "Local component needs attention",
        "Repeated recorded checks found a local service, storage or security failure. "
        "Review Data Health.",
    ),
    "SOURCE_BLOCKED": (
        "DATA_SOURCE",
        "WARNING",
        "Daily source is blocked",
        "The saved daily attempt cannot acquire permitted observations.",
    ),
    "SOURCE_UNAVAILABLE": (
        "DATA_SOURCE",
        "ERROR",
        "Source check unavailable",
        "A recorded source metadata check exhausted its bounded attempts.",
    ),
    "SOURCE_REVISION": (
        "DATA_SOURCE",
        "WARNING",
        "Upstream revision changed",
        "Public source metadata changed. This does not grant acquisition permission.",
    ),
    "DATA_MISSING": (
        "DATA_SOURCE",
        "WARNING",
        "Source observations missing",
        "Missing expected observations are recorded. Exchange-wide completeness is not inferred.",
    ),
    "DATA_REJECTED": (
        "DATA_SOURCE",
        "ERROR",
        "Data quality rejected observations",
        "Existing validation rejected or quarantined source records.",
    ),
    "IDENTITY_CONFLICT": (
        "DATA_SOURCE",
        "WARNING",
        "Instrument identity unresolved",
        "The persisted observation has unknown or unusable identity evidence.",
    ),
    "DATA_VALIDATED": (
        "DATA_SOURCE",
        "INFO",
        "Research data validated",
        "A separately classified research receipt records accepted observations.",
    ),
    "SESSION_DELAYED": (
        "DATA_SOURCE",
        "WARNING",
        "Expected session data delayed",
        "Verified trading-session and release-window evidence supports a pending observation.",
    ),
    "PIPELINE_STARTED": (
        "PIPELINE",
        "INFO",
        "Research processing started",
        "An immutable worker start checkpoint is recorded.",
    ),
    "PIPELINE_COMPLETED": (
        "PIPELINE",
        "INFO",
        "Research snapshot published",
        "Verified publication is complete; historical replay is not a new market session.",
    ),
    "PIPELINE_WARNINGS": (
        "PIPELINE",
        "WARNING",
        "Research run has warnings",
        "The published receipt retains partial coverage and evidence limitations.",
    ),
    "PIPELINE_FAILED": (
        "PIPELINE",
        "ERROR",
        "Research processing failed",
        "A persisted failure receipt requires operator review.",
    ),
    "RETRY_LIMIT": (
        "PIPELINE",
        "ERROR",
        "Research retry limit exceeded",
        "The existing bounded retry policy was exhausted.",
    ),
    "PUBLICATION_INCOMPLETE": (
        "PIPELINE",
        "WARNING",
        "Research publication incomplete",
        "No complete receipt is visible. A worker may still be active; inspect before recovery.",
    ),
    "WORKER_LOCK": (
        "PIPELINE",
        "WARNING",
        "Worker lock conflict",
        "A durable operational event records duplicate-worker protection.",
    ),
    "RECOVERED": (
        "PIPELINE",
        "INFO",
        "Interrupted research run recovered",
        "A complete receipt follows retained retry checkpoints.",
    ),
    "INTEGRITY_FAILURE": (
        "PIPELINE",
        "CRITICAL",
        "Research integrity check failed",
        "Stored evidence failed validation. Products withheld; exception text excluded.",
    ),
    "INFERENCE_BLOCKED": (
        "ML_RESEARCH",
        "WARNING",
        "Experimental inference unavailable",
        "Source, feature or model acceptance is insufficient. No forecast or recommendation.",
    ),
    "MODEL_MISSING": (
        "ML_RESEARCH",
        "ERROR",
        "Model artifact unavailable",
        "A verified gate event records missing trusted model evidence.",
    ),
    "FEATURE_SCHEMA": (
        "ML_RESEARCH",
        "ERROR",
        "Feature schema incompatible",
        "The recorded model compatibility gate rejected feature schema or order.",
    ),
    "FEATURE_HISTORY": (
        "ML_RESEARCH",
        "WARNING",
        "Feature history insufficient",
        "Stored features retain missing warm-up or required reference history.",
    ),
    "POLICY_REJECTED": (
        "ML_RESEARCH",
        "WARNING",
        "Research policy gate withheld outputs",
        "Unchanged risk, ranking and signal evidence gates remain unsatisfied.",
    ),
    "PREDICTION_AVAILABLE": (
        "ML_RESEARCH",
        "INFO",
        "Experimental research forecast recorded",
        "A verified later-session experimental forecast is available; it is not a trading signal.",
    ),
    "PAPER_ORDER": (
        "PAPER_TRADING",
        "INFO",
        "Recorded paper order changed",
        "An existing simulated order-state event was recovered. No new order was executed.",
    ),
    "PAPER_FILL": (
        "PAPER_TRADING",
        "INFO",
        "Recorded paper fill",
        "An existing simulated fill was recovered. Amounts and account details are omitted.",
    ),
    "PAPER_FAILURE": (
        "PAPER_TRADING",
        "ERROR",
        "Recorded paper processing issue",
        "Existing simulated event evidence records a rejected or unresolved execution.",
    ),
    "VALUATION_UNRESOLVED": (
        "PORTFOLIO",
        "WARNING",
        "Portfolio valuation unavailable",
        "A holding has no verified persisted valuation. Research prices are not substituted.",
    ),
    "HOLDING_QUALITY": (
        "PORTFOLIO",
        "WARNING",
        "Holding evidence has quality warnings",
        "An existing valuation report retains unresolved or degraded observations.",
    ),
}


class Event(Contract):
    version: Literal["p20.event.v1"] = "p20.event.v1"
    code: str
    component: Literal["P19", "P15", "P16", "P22"]
    evidence_ref: Safe
    evidence_sha256: Annotated[str, Field(pattern="^[a-f0-9]{64}$")]
    event_at: AwareDatetime
    time_basis: Literal["PERSISTED_EVENT_TIME", "DETECTOR_OBSERVATION_TIME"]
    run_id: Annotated[str, Field(pattern="^[a-f0-9]{64}$")] | None = None
    security_id: Safe | None = None
    session: date | None = None
    classification: Literal[
        "RESEARCH_ONLY",
        "TEST_ONLY",
        "PAPER",
        "TEST_ONLY_PAPER",
        "USER_RECORDED",
        "UNVERIFIED_OPERATIONAL_EVIDENCE",
    ]
    final_vintage: Literal["FINAL_VINTAGE_RESEARCH_ASSUMPTION"] | None = None
    mode: Literal["DAILY", "HISTORICAL_REPLAY", "TEST_ONLY", "RECORDED"]
    reasons: tuple[Reason, ...] = Field(default=(), max_length=40)
    group: Safe
    identity: Safe

    @model_validator(mode="after")
    def gated(self) -> Self:
        if self.code not in TEMPLATES:
            raise ValueError("UNSUPPORTED_OR_DISABLED_ALERT_TYPE")
        if self.code == "PREDICTION_AVAILABLE":
            raise ValueError("EXPERIMENTAL_INFERENCE_ACTIVATION_NOT_VERIFIED")
        if self.mode == "TEST_ONLY" and self.classification != "TEST_ONLY":
            raise ValueError("TEST_ONLY_CLASSIFICATION_REQUIRED")
        return self

    @property
    def event_key(self) -> str:
        return checksum(
            stable_json([self.component, self.code, self.identity, self.classification])
        )

    @property
    def alert_id(self) -> str:
        return checksum(stable_json(["p20.alert.v1", self.event_key]))


class Preferences(Contract):
    version: Literal["p20.preferences.v1"] = "p20.preferences.v1"
    categories: tuple[Category, ...] = (
        "DATA_SOURCE",
        "PIPELINE",
        "ML_RESEARCH",
        "PORTFOLIO",
        "PAPER_TRADING",
    )
    include_info: bool = False
    quiet_enabled: bool = False
    quiet_start: Annotated[str, Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")] = "22:00"
    quiet_end: Annotated[str, Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")] = "07:00"
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    cooldown_seconds: int = Field(default=3600, ge=0, le=86400)
    maximum_attempts: int = Field(default=3, ge=1, le=5)
    retention_days: int = Field(default=90, ge=7, le=365)
    email: Literal[False] = False
    desktop: Literal[False] = False

    @model_validator(mode="after")
    def disabled(self) -> Self:
        if "STOCK_SIGNAL" in self.categories or len(set(self.categories)) != len(self.categories):
            raise ValueError("SIGNAL_CHANNEL_DISABLED_OR_DUPLICATE_CATEGORY")
        if self.quiet_enabled and self.quiet_start == self.quiet_end:
            raise ValueError("QUIET_INTERVAL_MUST_HAVE_DISTINCT_BOUNDARIES")
        return self


class FreshnessEvidence(Contract):
    """Operator-reviewed scoped release evidence, not a weekday-derived calendar."""

    version: Literal["p20.freshness.v1"] = "p20.freshness.v1"
    provider: Provider
    session: Session
    release_window_known_at: AwareDatetime
    expected_available_at: AwareDatetime
    release_evidence_ref: Safe
    classification: Literal["RESEARCH_ONLY", "TEST_ONLY"]

    @model_validator(mode="after")
    def clocks(self) -> Self:
        if self.release_window_known_at > self.expected_available_at:
            raise ValueError("RELEASE_WINDOW_KNOWLEDGE_MUST_PRECEDE_EXPECTATION")
        if self.classification == "TEST_ONLY" and self.session.evidence_type != "TEST_ONLY":
            raise ValueError("TEST_ONLY_SESSION_REQUIRED")
        if (
            self.classification == "RESEARCH_ONLY"
            and self.session.evidence_type != "OFFICIAL_VERIFIED_SESSION"
        ):
            raise ValueError("OFFICIAL_SESSION_REQUIRED_FOR_MISSING_SESSION_ALERT")
        return self
