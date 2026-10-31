"""TEST_ONLY source-route lineage; no provider or genuine price inputs."""

from pathlib import Path

import pytest
from workers.experimental_nse.acquire import digest, initialize
from workers.nse_market import engine


@pytest.mark.parametrize("operation", ["candles", "intraday_candles", None])
def test_scoring_route_retains_exact_candle_provenance(
    tmp_path: Path, operation: str | None
) -> None:
    root = tmp_path / "TEST_ONLY"
    initialize(root)
    row = {"key": "NSE_EQ|INE002A01018", "session": "2025-01-03", "raw_sha256": "a" * 64}
    identity = {"isin": "INE002A01018"}
    folder = root / "daily" / row["session"] / identity["isin"]
    folder.mkdir(parents=True)
    receipt = {"raw_sha256": row["raw_sha256"]}
    if operation is not None:
        receipt["request"] = {"operation": operation, "instrument_key": row["key"]}  # type: ignore[assignment]
    engine._checked(folder / "response.json", receipt)
    result = engine._candle_operation(root, identity, row)
    assert result["operation"] == (operation or "NOT_RETAINED_IN_LEGACY_RECEIPT")
    assert result["raw_sha256"] == row["raw_sha256"]
    assert result["response_receipt_sha256"] == digest((folder / "response.json").read_bytes())


def test_scoring_route_rejects_a_different_response_body(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY"
    initialize(root)
    row = {"key": "NSE_EQ|INE002A01018", "session": "2025-01-03", "raw_sha256": "a" * 64}
    identity = {"isin": "INE002A01018"}
    folder = root / "daily" / row["session"] / identity["isin"]
    folder.mkdir(parents=True)
    engine._checked(folder / "response.json", {"raw_sha256": "b" * 64})
    with pytest.raises(ValueError, match="ROUTE_SOURCE_MISMATCH"):
        engine._candle_operation(root, identity, row)
