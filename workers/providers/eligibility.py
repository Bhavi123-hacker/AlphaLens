"""Coverage diagnostics reuse frozen input compatibility; never grant model acceptance."""

from datetime import date, datetime
from typing import Any

from pydantic import AwareDatetime

from alphalens_data.contracts import Contract
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Hash
from alphalens_data.providers.multi_contracts import Candle, ProviderName
from workers.daily.inference import input_compatibility


class PeerScope(Contract):
    session: date
    provider: ProviderName
    expected_isins: tuple[str, ...]
    membership_sha256: Hash
    membership_available_at: AwareDatetime
    semantics: str = "CONTEMPORANEOUS_EXPECTED_SCOPE_NOT_CURRENT_MASTER_BACKFILL"


def assess(
    scope: PeerScope,
    candles: tuple[Candle, ...],
    cutoff: datetime,
    columns: tuple[str, ...],
    features: dict[str, Any],
) -> dict[str, Any]:
    if cutoff.tzinfo is None:
        raise DataContractError("AWARE_PEER_CUTOFF_REQUIRED")
    reasons = []
    if cutoff.tzinfo is None or scope.membership_available_at > cutoff:
        reasons.append("CONTEMPORANEOUS_PEER_MEMBERSHIP_UNAVAILABLE")
    expected = set(scope.expected_isins)
    if not expected or len(expected) != len(scope.expected_isins):
        reasons.append("PEER_DENOMINATOR_INVALID")
    observed = set()
    for candle in candles:
        isin = candle.instrument.isin
        if (
            candle.provider != scope.provider
            or candle.session != scope.session
            or candle.received_at > cutoff
            or not isin
            or isin in observed
        ):
            reasons.append("PEER_SESSION_IDENTITY_OR_CHRONOLOGY_INVALID")
        elif (
            candle.price_basis != "RAW_UNADJUSTED"
            or not candle.instrument.series
            or candle.action_status == "UNAVAILABLE"
        ):
            reasons.append("PEER_PRICE_BASIS_SERIES_OR_ACTIONS_UNAVAILABLE")
        if isin:
            observed.add(isin)
    missing, extra = sorted(expected - observed), sorted(observed - expected)
    if missing or extra:
        reasons.append("INCOMPLETE_OR_DIFFERENT_PEER_UNIVERSE")
    if len(columns) != 38 or "momentum_percentile_20" not in columns:
        reasons.append("FROZEN_38_FEATURE_CONTRACT_REQUIRED")
    compatibility = input_compatibility(columns, features)
    reasons.extend(compatibility["reasons"])
    return {
        "expected": len(expected),
        "observed": len(observed),
        "missing_isins": missing,
        "unexpected_isins": extra,
        "coverage_complete": not missing and not extra and bool(expected),
        "feature_compatibility": compatibility,
        "evidence_blockers": sorted(set(reasons)),
        "current_inference": "UNAVAILABLE",
        "ranking": "UNAVAILABLE",
        "policy_blockers": [
            "NO_CLEARED_LIVE_SOURCE",
            "INDEPENDENT_MODEL_ACCEPTANCE_NOT_PASSED",
            "UNATTENDED_ACTIVATION_DISABLED",
        ],
        "membership_sha256": scope.membership_sha256,
        "momentum_percentile_20": "NO_RECOMPUTATION_OR_SCOPE_UPGRADE",
    }
