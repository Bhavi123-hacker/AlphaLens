"""Tiered Provider Manager and Failover Mechanism for AlphaLens.

Provides reliable, zero-cost, multi-tier data acquisition:
- Tier 1: Primary Broker Provider (Upstox official API, token-authenticated, quota-governed)
- Tier 2: Secondary Exchange Archive (NSE/BSE Bhavcopy bulk files, verified checksums)
- Tier 3: Offline Research Replay (Deterministic local cache, zero network overhead)

Enforces strict provenance, rights governance, and exact session integrity:
- Returns distinct states: FRESH, HISTORICAL_REPLAY, VENDOR_PENDING, RIGHTS_BLOCKED, FAILED
- Never treats stale cached sessions as fresh acquisitions for newer target dates
- Preserves source lineage, rights, and quota constraints across all tiers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from workers.nse_market import bulk_eod

logger = logging.getLogger("alphalens.provider_manager")


class ProviderTier(StrEnum):
    TIER_1_UPSTOX = "TIER_1_UPSTOX_OFFICIAL"
    TIER_2_EXCHANGE_BULK = "TIER_2_EXCHANGE_BULK_BHAVCOPY"
    TIER_3_OFFLINE_CACHE = "TIER_3_OFFLINE_CACHE_REPLAY"


class AcquisitionState(StrEnum):
    FRESH = "FRESH"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    VENDOR_PENDING = "VENDOR_PENDING"
    RIGHTS_BLOCKED = "RIGHTS_BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class AcquisitionResult:
    instrument_key: str
    target_session: str
    observed_session: str | None
    state: AcquisitionState
    tier_used: ProviderTier | None
    candles_count: int
    success: bool
    fallback_invoked: bool
    error_message: str | None = None


class ProviderManager:
    def __init__(
        self,
        bulk_archive_dir: Path | None = None,
        bse_rights_cleared: bool = False,
    ) -> None:
        self.bulk_archive_dir = bulk_archive_dir
        self.bse_rights_cleared = bse_rights_cleared

    def acquire_eod_data(
        self,
        instrument_key: str,
        target_session: date,
        upstox_client: Any | None = None,
        cached_candles: list[dict[str, Any]] | None = None,
    ) -> AcquisitionResult:
        """Attempt multi-tier data retrieval with automated failover and rights enforcement."""
        target_str = str(target_session)

        # 0. Check Rights Boundary
        if instrument_key.startswith("BSE_EQ|") and not self.bse_rights_cleared:
            return AcquisitionResult(
                instrument_key=instrument_key,
                target_session=target_str,
                observed_session=None,
                state=AcquisitionState.RIGHTS_BLOCKED,
                tier_used=None,
                candles_count=0,
                success=False,
                fallback_invoked=False,
                error_message="BSE_COMMERCIAL_ARCHIVE_OR_DIRECT_FEED_RIGHTS_NOT_CLEARED",
            )

        # 1. Attempt Tier 1 (Upstox Live API)
        if upstox_client is not None:
            try:
                candles = upstox_client.get_daily_candles(instrument_key, target_session)
                if candles and any(str(c.get("session")) == target_str for c in candles):
                    return AcquisitionResult(
                        instrument_key=instrument_key,
                        target_session=target_str,
                        observed_session=target_str,
                        state=AcquisitionState.FRESH,
                        tier_used=ProviderTier.TIER_1_UPSTOX,
                        candles_count=len(candles),
                        success=True,
                        fallback_invoked=False,
                    )
            except Exception as e:
                logger.warning(
                    "Tier 1 Upstox acquisition failed for %s on %s: %s. Failing over to Tier 2...",
                    instrument_key,
                    target_session,
                    e,
                )

        # 2. Attempt Tier 2 (Exchange Bulk Bhavcopy)
        if self.bulk_archive_dir and self.bulk_archive_dir.exists():
            try:
                bulk_files = list(
                    self.bulk_archive_dir.glob(f"*{target_session.strftime('%Y%m%d')}*")
                )
                if bulk_files:
                    target_file = bulk_files[0]
                    _, csv_bytes, _, fmt = bulk_eod.extract_csv_payload(target_file)
                    if fmt == "NSE_UDIFF":
                        rows, _ = bulk_eod.parse_cm_udiff_rows(
                            csv_bytes, target_session, expected_exchange="NSE"
                        )
                    elif fmt == "BSE_UDIFF":
                        rows, _ = bulk_eod.parse_cm_udiff_rows(
                            csv_bytes, target_session, expected_exchange="BSE"
                        )
                    else:
                        rows, _ = bulk_eod.parse_bse_classic_rows(csv_bytes, target_session)

                    matching = []
                    for r in rows:
                        isin_code = str(r.get("ISIN") or r.get("ISIN_CODE") or "")
                        if isin_code and isin_code in instrument_key:
                            matching.append(r)
                    if matching:
                        return AcquisitionResult(
                            instrument_key=instrument_key,
                            target_session=target_str,
                            observed_session=target_str,
                            state=AcquisitionState.HISTORICAL_REPLAY,
                            tier_used=ProviderTier.TIER_2_EXCHANGE_BULK,
                            candles_count=len(matching),
                            success=True,
                            fallback_invoked=True,
                        )
            except Exception as e:
                logger.warning(
                    "Tier 2 Bulk Bhavcopy acquisition failed for %s: %s. Failing over to Tier 3...",
                    instrument_key,
                    e,
                )

        # 3. Attempt Tier 3 (Offline Cached Replay)
        # Never treat older cached candles as fresh acquisitions for target_session
        if cached_candles:
            exact_session_match = [c for c in cached_candles if str(c.get("session")) == target_str]
            if exact_session_match:
                return AcquisitionResult(
                    instrument_key=instrument_key,
                    target_session=target_str,
                    observed_session=target_str,
                    state=AcquisitionState.HISTORICAL_REPLAY,
                    tier_used=ProviderTier.TIER_3_OFFLINE_CACHE,
                    candles_count=len(exact_session_match),
                    success=True,
                    fallback_invoked=True,
                )

            # Check if cache has prior sessions; if so, target_session is pending publication
            prior_sessions = [
                str(c.get("session")) for c in cached_candles if str(c.get("session")) < target_str
            ]
            if prior_sessions:
                latest_prior = max(prior_sessions)
                return AcquisitionResult(
                    instrument_key=instrument_key,
                    target_session=target_str,
                    observed_session=latest_prior,
                    state=AcquisitionState.VENDOR_PENDING,
                    tier_used=ProviderTier.TIER_3_OFFLINE_CACHE,
                    candles_count=len(cached_candles),
                    success=False,
                    fallback_invoked=True,
                    error_message=(
                        f"VENDOR_PUBLICATION_PENDING: Target session {target_str} not in cache; "
                        f"latest observed session is {latest_prior}."
                    ),
                )

        return AcquisitionResult(
            instrument_key=instrument_key,
            target_session=target_str,
            observed_session=None,
            state=AcquisitionState.FAILED,
            tier_used=None,
            candles_count=0,
            success=False,
            fallback_invoked=True,
            error_message="ALL_ACQUISITION_TIERS_EXHAUSTED",
        )
