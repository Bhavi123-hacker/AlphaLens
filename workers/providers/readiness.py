"""Evidence-based comparison and rate-only capacity planning; never acquisition."""

from collections import deque
from datetime import date
from math import ceil
from typing import Any

from alphalens_data.providers.multi_adapters import RATES
from alphalens_data.providers.multi_contracts import ProviderName

PROFILES: tuple[dict[str, Any], ...] = (
    {
        "provider": "upstox",
        "name": "Upstox",
        "status": "ACCOUNT_PENDING",
        "authentication": "READ_ONLY_ANALYTICS_TOKEN_NOT_CONFIGURED",
        "account_status": "UNDER_REVIEW",
        "nse_support": "DOCUMENTED_NSE_EQ_NOT_TESTED",
        "historical_coverage": "Daily from Jan2000; max10-year request window",
        "free_conditions": (
            "Free Analytics Token; active eligible account required; no account action performed"
        ),
        "identity": (
            "NSE_EQ|ISIN current BOD master; series and historic eligibility require separate facts"
        ),
        "blocker": (
            "Account under review; token absent; "
            "data-use/adjustment/action/calendar evidence not verified"
        ),
        "reference": "https://upstox.com/developer/api-documentation/analytics-token/",
        "limits_reference": "https://upstox.com/developer/api-documentation/rate-limiting/",
    },
    {
        "provider": "indstocks",
        "name": "INDstocks",
        "status": "NOT_CONFIGURED",
        "authentication": "ACCESS_TOKEN_NOT_CONFIGURED",
        "account_status": "NOT_CONFIGURED",
        "nse_support": "DOCUMENTED_NSE_CASH_NOT_TESTED",
        "historical_coverage": "1day: one-year request window, total depth unverified",
        "free_conditions": (
            "Official FAQ free API; brokerage account and completed KYC; no minimum API balance"
        ),
        "identity": (
            "NSE_token, instrument master mapping required; no token-only canonical inference"
        ),
        "blocker": (
            "No account/token; retention/ML/display rights and "
            "action/adjustment evidence not verified"
        ),
        "reference": "https://api-docs.indstocks.com/faq/",
        "limits_reference": "https://api-docs.indstocks.com/conventions/",
    },
    {
        "provider": "angel-one",
        "name": "Angel One SmartAPI",
        "status": "SOURCE_NOT_CLEARED",
        "authentication": "NOT_CONFIGURED",
        "account_status": "NOT_CONFIGURED",
        "nse_support": "DOCUMENTED_NSE_NOT_TESTED",
        "historical_coverage": "Daily candles documented; actual depth/window not verified",
        "free_conditions": (
            "Official FAQ describes free API including historical; "
            "authenticated account entitlement required"
        ),
        "identity": "Exchange NSE plus instrument token; dated ISIN/series mapping required",
        "blocker": (
            "Docs authorization restriction; quote-rate descriptions "
            "conflict; auth and data-use rights unresolved"
        ),
        "reference": "https://smartapi.angelone.in/faq",
        "limits_reference": "https://smartapi.angelone.in/docs/RateLimit",
    },
    {
        "provider": "alpha-vantage",
        "name": "Alpha Vantage",
        "status": "SOURCE_NOT_CLEARED",
        "authentication": "LOCAL_CREDENTIAL_STATUS",
        "account_status": "API_KEY_ONLY",
        "nse_support": "NOT_ESTABLISHED_RELIANCE_BSE_ONLY",
        "historical_coverage": (
            "No authorized NSE OHLCV acquired; no accessible NSE sessions established"
        ),
        "free_conditions": (
            "Standard free25 requests/day; special educational exemption not assumed"
        ),
        "identity": "RELIANCE.BSE, India/Bombay; never substitute BSE for NSE",
        "blocker": (
            "One successful search, no NSE exchange proof; specific "
            "retention/ML/display scope not cleared"
        ),
        "reference": "https://www.alphavantage.co/documentation/",
        "limits_reference": "https://www.alphavantage.co/support/",
    },
    {
        "provider": "yahoo",
        "name": "Yahoo / yfinance",
        "status": "SOURCE_NOT_CLEARED",
        "authentication": "UNOFFICIAL_INTERFACE_DISABLED",
        "account_status": "NOT_CONFIGURED",
        "nse_support": "DOCUMENTED_NS_CONVENTION_NOT_ACQUIRED",
        "historical_coverage": "Wrapper history/download interfaces; no authorized price requests",
        "free_conditions": (
            "Open-source software is free; data rights and permitted automated quotas unverified"
        ),
        "identity": (
            ".NS and .BO preserved separately; suffix/company name is not "
            "authoritative ISIN evidence"
        ),
        "blocker": (
            "No Yahoo automation/retention approval; no cookie/crumb or anti-bot workaround allowed"
        ),
        "reference": "https://github.com/ranaroussi/yfinance",
        "limits_reference": "https://github.com/0xramm/Indian-Stock-Market-API",
    },
    {
        "provider": "tejhq",
        "name": "TejHQ",
        "status": "RESEARCH_ONLY",
        "authentication": "KEYLESS_METADATA_PRIOR_CHECK",
        "account_status": "NO_ACCOUNT",
        "nse_support": "PINNED_HISTORICAL_ARCHIVE_ONLY",
        "historical_coverage": "Preserved archive2010 through2026-10-06; no newly acquired session",
        "free_conditions": (
            "Publisher free raw-data claim; historical authorization does not clear ongoing source"
        ),
        "identity": (
            "Observed ISIN/symbol evidence; missing historical "
            "identity/action/calendar knowledge retained"
        ),
        "blocker": (
            "Ongoing upstream rights/revisions/identity/actions incomplete; "
            "advertised release is not acquired data"
        ),
        "reference": "https://tejhq.dev/docs",
        "limits_reference": "https://github.com/tejhq/tej-bazaar",
    },
)


def rate_only_seconds(calls: int, provider: ProviderName) -> float | None:
    """Lower bound for prepared requests, zero network latency, one bounded stream."""
    if calls < 1 or calls > 10000:
        return None
    rates = RATES[provider]
    if rates.get("second") is None:
        return None
    windows = [
        (period, limit)
        for name, period in (
            ("second", 1),
            ("minute", 60),
            ("half_hour", 1800),
            ("hour", 3600),
            ("day", 86400),
        )
        if (limit := rates.get(name)) is not None
    ]
    queues: dict[int, deque[float]] = {period: deque() for period, _ in windows}
    at = 0.0
    for _ in range(calls):
        while True:
            next_at = at
            for period, limit in windows:
                queue = queues[period]
                while queue and queue[0] <= at - period + 1e-8:
                    queue.popleft()
                if len(queue) >= limit:
                    next_at = max(next_at, queue[0] + period)
            if next_at == at:
                break
            at = next_at
        for queue in queues.values():
            queue.append(at)
        # Conservative pacing, not concurrent calls. This does not model network latency.
        at += 1 / float(rates["second"] or 1)
    return round(at, 3)


def comparison(
    *,
    archive_session: date | None = None,
    credential_present: bool = False,
    selected_provider: str | None = None,
    local_attempts: int | None = None,
) -> dict[str, Any]:
    providers = []
    for original in PROFILES:
        row = dict(original)
        provider: ProviderName = row["provider"]
        batch = RATES[provider].get("candle_batch")
        estimates = []
        for count in (50, 500, 2589):
            calls = ceil(count / batch) if batch else None
            estimates.append(
                {
                    "instruments": count,
                    "calls": calls,
                    "rate_only_minimum_seconds": rate_only_seconds(calls, provider)
                    if calls
                    else None,
                    "within_known_daily_quota": None
                    if not calls or not RATES[provider].get("day")
                    else calls <= int(RATES[provider]["day"] or 0),
                }
            )
        row.update(
            {
                "rates": RATES[provider],
                "daily_capacity": estimates,
                "last_verified_session": archive_session.isoformat()
                if archive_session and provider == "tejhq"
                else None,
                "latest_session_semantics": "FROZEN_ARCHIVE_NOT_LIVE"
                if provider == "tejhq"
                else "NO_NSE_SESSION_ACQUIRED",
                "publisher_advertised_session": "2026-10-09" if provider == "tejhq" else None,
                "latency_ms": None,
                "provider_remaining_daily_allowance": None,
                "local_rolling_24h_attempts": local_attempts
                if provider == "alpha-vantage"
                else None,
                "legal_permission": "NOT_VERIFIED_FOR_ONGOING_NSE_RETENTION_ML_PUBLIC_DISPLAY",
                "full_market_suitability": "CONDITIONAL_NOT_VERIFIED"
                if provider in {"upstox", "indstocks", "angel-one", "tejhq"}
                else "NOT_ESTABLISHED",
                "integration_readiness": "OFFLINE_PREPARED_LIVE_BLOCKED",
                "selected": selected_provider == provider,
                "collection_enabled": False,
                "credential_configured": credential_present
                if provider == "alpha-vantage"
                else False,
                "status_semantics": "HISTORICAL_ONLY_NOT_ONGOING_APPROVAL"
                if provider == "tejhq"
                else "NO_INGESTION_APPROVAL",
            }
        )
        if provider == "alpha-vantage":
            row["authentication"] = (
                "WINDOWS_CREDENTIAL_AVAILABLE_PRIOR_SEARCH_BSE_ONLY"
                if credential_present
                else "NOT_CONFIGURED_ON_THIS_HOST"
            )
        providers.append(row)
    return {
        "version": "p28.provider-readiness.v1",
        "providers": providers,
        "source_selected_for_live_ingestion": None,
        "collection_enabled": False,
        "scheduler_enabled": False,
        "capacity_scope": (
            "2589_IS_ARCHIVED_OBSERVED_RESEARCH_COHORT_NOT_VERIFIED_CURRENT_NSE_UNIVERSE"
        ),
        "capacity_interpretation": (
            "RATE_ONLY_THEORETICAL_ZERO_NETWORK_LATENCY_NOT_MEASURED_COVERAGE"
        ),
        "ml_readiness": {
            "feature_count": 38,
            "momentum_percentile_20": "COMPLETE_CONTEMPORANEOUS_PEERS_REQUIRED",
            "current_inference": "BLOCKED",
            "independent_model_acceptance": "NOT_PASSED",
            "shortlists": {"top5": "UNAVAILABLE", "top10": "UNAVAILABLE", "top20": "UNAVAILABLE"},
        },
        "recommendation": "UPSTOX_READ_ONLY_ANALYTICS_AFTER_ACCOUNT_AND_RIGHTS_CLEARANCE",
        "alternatives": "INDSTOCKS_CANDIDATE_WITH_BETTER_CANDLE_BATCHING_NOT_YET_CLEARED",
    }
