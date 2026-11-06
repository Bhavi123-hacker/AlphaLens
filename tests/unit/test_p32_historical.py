"""TEST_ONLY exact calendar, source identity and missingness exclusions."""

from datetime import date

from workers.personal.contracts import Profile
from workers.personal.historical import rank, reduce_partition


def test_historical_complete_windows_missingness_and_identity_changes() -> None:
    sessions = ["2024-01-02", "2024-01-03", "2024-01-04"]
    rows = []
    for key, values in (
        ("TEST_ONLY_A", ("100", "120", "110")),
        ("TEST_ONLY_B", ("100", None, "130")),
        ("TEST_ONLY_C", ("100", "101", "102")),
    ):
        for index, price in enumerate(values):
            if price is None:
                continue
            rows.append(
                {
                    "security_id": key,
                    "session_date": date.fromisoformat(sessions[index]),
                    "symbol": key,
                    "isin": "INE000000001"
                    if key != "TEST_ONLY_C" or index == 0
                    else "INE000000002",
                    "analytical_type": "RESEARCH_EQUITY_CANDIDATE",
                    "close": price,
                    "volume": 100,
                    "quality": "VALID",
                }
            )
    reduced = reduce_partition(rows, sessions, Profile())
    result = rank(reduced, "price_return", 10, False)
    assert result["observed_cohort"] == 3 and result["comparable_count"] == 1
    assert result["leaders"][0]["security_id"] == "TEST_ONLY_A"
    assert result["leaders"][0]["metrics"]["price_return_percent"] == 10
    assert len(result["excluded"]) == 2 and not result["full_nse_market"]


def test_risk_adjusted_is_price_diagnostic_not_sharpe_or_current_prediction() -> None:
    rows = [
        {
            "security_id": "TEST_ONLY_A",
            "metrics": {"mean_daily_return_over_volatility": 0.5},
            "preferences": {"state": "MATCHES_SUPPORTED_CONSTRAINTS"},
        }
    ]
    result = rank(rows, "risk_adjusted", 5, True)
    assert len(result["leaders"]) == 1 and "NOT_TOTAL_PROFIT" in result["interpretation"]
    assert result["strategy_tuning"] is False
