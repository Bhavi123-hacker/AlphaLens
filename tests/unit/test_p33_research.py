"""TEST_ONLY descriptive rules and historical coverage never imply investment advice."""

from workers.personal.analytics import preference_match
from workers.personal.contracts import Profile
from workers.personal.historical import rank, reduce_partition


def test_supported_technical_filters_and_missing_dimensions() -> None:
    profile = Profile(
        minimum_momentum_percent="2",
        minimum_rsi="35",
        maximum_rsi="65",
        technical_condition="ABOVE_SMA20",
        maximum_daily_volatility_percent="3",
    )
    metrics = {
        "price_return_percent": 5,
        "rsi_14": 50,
        "sma_distance": 0.05,
        "maximum_drawdown_percent": -10,
        "daily_volatility_percent": 2,
    }
    assert preference_match(profile, metrics)["state"] == "MATCHES_SUPPORTED_CONSTRAINTS"
    assert preference_match(profile, {**metrics, "rsi_14": 80})["excluded"] == ["maximum_rsi"]
    missing = preference_match(profile, {**metrics, "rsi_14": None})
    assert missing["state"] == "INSUFFICIENT_EVIDENCE" and "minimum_rsi" in missing["missing"]
    assert "RISK_TOLERANCE_CATEGORY_CALIBRATION" in missing["unsupported"]


def test_current_provider_sector_is_explicit_and_never_backfilled() -> None:
    profile = Profile(preferred_sectors=["TEST_ONLY_TECH"])
    missing = preference_match(profile, {"maximum_drawdown_percent": -2})
    assert "VERIFIED_SECTORS" in missing["unsupported"]
    known = preference_match(
        profile, {"provider_current_sector": "TEST_ONLY_TECH", "maximum_drawdown_percent": -2}
    )
    assert "PREFERRED_PROVIDER_CURRENT_SECTOR" in known["matched"]
    assert "VERIFIED_SECTORS" not in known["unsupported"]
    excluded = preference_match(
        profile, {"provider_current_sector": "TEST_ONLY_OTHER", "maximum_drawdown_percent": -2}
    )
    assert excluded["state"] == "EXCLUDED_BY_SUPPORTED_CONSTRAINT"


def test_available_path_does_not_bridge_identity_or_missing_slots() -> None:
    sessions = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    rows = [
        {
            "security_id": "TEST_ONLY",
            "session_date": day,
            "symbol": "TEST_ONLY",
            "isin": None if n == 0 else "INE000000001",
            "analytical_type": "RESEARCH_EQUITY_CANDIDATE",
            "close": str(100 + n),
            "volume": 100,
            "quality": "VALID",
        }
        for n, day in enumerate(sessions)
        if n != 2
    ]
    strict = reduce_partition(rows, sessions, Profile())
    assert rank(strict, "price_return", 5, False)["comparable_count"] == 0
    available = reduce_partition(rows, sessions, Profile(), "available_window")
    leader = rank(available, "price_return", 5, False)["leaders"][0]
    assert leader["coverage"]["actual_start"] == sessions[3]
    assert leader["coverage"]["used_fraction"] == 0.4
    assert not leader["coverage"]["full_requested_path"]
    assert abs(leader["metrics"]["price_return_percent"] - 100 / 103) < 1e-12
    assert "NOT_FULL_PERIOD_RETURN" in leader["window_basis"]


def test_endpoint_movement_keeps_missing_path_risk_unavailable() -> None:
    sessions = ["2024-01-01", "2024-01-02", "2024-01-03"]
    rows = [
        {
            "security_id": "TEST_ONLY",
            "session_date": day,
            "symbol": "TEST_ONLY",
            "isin": "INE000000001",
            "analytical_type": "RESEARCH_EQUITY_CANDIDATE",
            "close": price,
            "volume": 10,
            "quality": "VALID",
        }
        for day, price in ((sessions[0], "100"), (sessions[-1], "120"))
    ]
    strict = rank(reduce_partition(rows, sessions, Profile()), "price_return", 5, False)
    endpoints = rank(
        reduce_partition(rows, sessions, Profile(), "observed_endpoints"), "price_return", 5, False
    )
    assert strict["comparable_count"] == 0 and endpoints["comparable_count"] == 1
    leader = endpoints["leaders"][0]
    assert leader["metrics"]["price_return_percent"] == 20
    assert leader["metrics"]["maximum_drawdown_percent"] is None
    assert leader["metrics"]["daily_volatility_percent"] is None
    assert leader["metrics"]["missing_count"] == 1
    assert not leader["coverage"]["full_requested_path"]


def test_unavailable_identity_never_becomes_available_window_eligible() -> None:
    sessions = ["2024-01-01", "2024-01-02"]
    rows = [
        {
            "security_id": "TEST_ONLY",
            "session_date": day,
            "symbol": "TEST_ONLY",
            "isin": None,
            "analytical_type": "RESEARCH_EQUITY_CANDIDATE",
            "close": "100",
            "volume": 10,
            "quality": "VALID",
        }
        for day in sessions
    ]
    result = rank(
        reduce_partition(rows, sessions, Profile(), "available_window"), "price_return", 5, False
    )
    assert result["comparable_count"] == 0
    assert result["coverage_counts"]["missing_dated_identity"] == 1
