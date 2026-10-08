"""TEST_ONLY invented execution scenarios; never TejHQ/real-market results."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from alphalens_backtesting.contracts import scenarios
from alphalens_backtesting.research import ResearchPrices, digest_file, run_research
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchProfile, calendar, lineage


class TestOnlyPrices(ResearchPrices):
    __test__ = False

    def __init__(self, missing: bool = False, action: bool = False) -> None:
        self.sessions = calendar(
            {date(2023, 11, 10), date(2023, 11, 13), date(2023, 11, 14)}, ResearchProfile()
        )
        self.dataset_id = checksum(b"TEST_ONLY_PRICE_FIXTURE")
        self.oos_cache_key = None
        self.oos_cache = None
        self.missing = missing
        self.action = action

    def get(self, security: str, day: Any) -> dict[str, Any] | None:
        if self.missing and day == date(2023, 11, 12):
            return None
        return dict(
            open=Decimal("10"),
            close=Decimal("11"),
            quality="VALID",
            economic_action=self.action and day == date(2023, 11, 12),
            canonical_record_id=checksum(f"TEST_ONLY:{security}:{day}".encode()),
        )


def reports(
    root: Path, prices: TestOnlyPrices, decision: datetime | None = None, target: str = "0.1"
) -> list[dict[str, Any]]:
    source = date(2023, 11, 10)
    run = checksum(b"TEST_ONLY_MODEL")
    rows = [
        dict(
            security_id="TEST_ONLY_A",
            session_date=source,
            decision_time=decision or prices.sessions.availability(source),
            prediction_id=checksum(b"TEST_ONLY_PREDICTION"),
            score=0.7,
            canonical_record_id=checksum(b"TEST_ONLY_FEATURE_SOURCE"),
            actual_forward_return=target,
        )
    ]
    schema = pa.schema(
        [
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("decision_time", pa.timestamp("us", tz="UTC")),
            ("prediction_id", pa.string()),
            ("score", pa.float64()),
            ("canonical_record_id", pa.string()),
            ("actual_forward_return", pa.string()),
        ],
        metadata={
            b"role": b"FOLD_TEST",
            b"model_run_id": run.encode(),
            b"research_lineage": stable_json(lineage(prices.sessions.profile)),
        },
    )
    path = root / "TEST_ONLY-oos.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    return [
        dict(
            task="classification",
            horizon=1,
            model_family="logistic",
            research_profile_id=prices.sessions.profile.profile_id,
            model_run_id=run,
            oos_file=path.name,
            oos_sha256=digest_file(path),
            fold=dict(test_end="2023-11-13"),
        )
    ]


def test_same_session_close_decision_cannot_fill(tmp_path: Path) -> None:
    prices = TestOnlyPrices()
    r = reports(tmp_path, prices, datetime(2023, 11, 10, 16, tzinfo=ZoneInfo("Asia/Kolkata")))
    with pytest.raises(ValueError, match="NOT_PROVEN_BEFORE_OPEN_STAGE"):
        run_research(r, tmp_path, prices, scenarios()[0], "TOP_K", tmp_path / "bt")


def test_missing_muhurat_open_no_fill_no_fake_price(tmp_path: Path) -> None:
    prices = TestOnlyPrices(missing=True)
    result = run_research(
        reports(tmp_path, prices), tmp_path, prices, scenarios()[0], "TOP_K", tmp_path / "bt"
    )
    assert result["trade_count"] == 0
    assert result["skipped"]["NO_FILL_MISSING_OR_REJECTED_OPEN"] == 1
    assert result["minimum_cash"] == "100000"


def test_known_raw_action_keeps_economics_unresolved_without_retroactive_order_block(
    tmp_path: Path,
) -> None:
    prices = TestOnlyPrices(action=True)
    result = run_research(
        reports(tmp_path, prices), tmp_path, prices, scenarios()[0], "TOP_K", tmp_path / "bt"
    )
    assert result["trade_count"] == 1 and result["unresolved_trade_count"] == 1
    assert result["total_return"] is None and result["maximum_drawdown"] is None
    assert result["final_vintage"] == "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
    assert Decimal(result["minimum_cash"]) >= 0


def test_future_outcome_never_changes_selection_or_simulated_fill(tmp_path: Path) -> None:
    prices = TestOnlyPrices()
    first = run_research(
        reports(tmp_path, prices, target="0.1"),
        tmp_path,
        prices,
        scenarios()[0],
        "TOP_K",
        tmp_path / "bt",
    )
    second = run_research(
        reports(tmp_path, prices, target="-0.9"),
        tmp_path,
        prices,
        scenarios()[0],
        "TOP_K",
        tmp_path / "bt",
    )
    assert first["trade_count"] == second["trade_count"] == 1
    assert first["total_return"] == second["total_return"]
    assert first["fees"] == second["fees"]
