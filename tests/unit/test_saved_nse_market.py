"""TEST_ONLY financial display contracts; no market claims or network."""

import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.nse_market.saved_market import listing, project

AT = datetime(2026, 10, 24, 6, tzinfo=UTC)


def frame() -> dict[str, Any]:
    identities = [
        {
            "provider_key": f"NSE_EQ|INE{i:09}",
            "symbol": f"TEST_ONLY_{i}",
            "name": "TEST_ONLY company",
        }
        for i in range(3)
    ]
    rows = []
    for i, identity in enumerate(identities[:2]):
        for session, close in [("2026-10-19", "100"), ("2026-10-21", str(110 - 20 * i))]:
            rows.append(
                {
                    "key": identity["provider_key"],
                    "session": session,
                    "open": "100",
                    "high": "115",
                    "low": "85",
                    "close": close,
                    "volume": 123 + i,
                    "received_at": "2026-10-22T10:00:00+00:00",
                }
            )
    return {
        "dataset_id": "TEST_ONLY",
        "sessions": ["2026-10-19", "2026-10-21"],
        "rows": rows,
        "identities": identities,
        "source_observed_at": "2026-10-22T10:00:00Z",
        "price_basis": "TEST_ONLY",
    }


def test_exact_change_and_sign_filtered_leaders_without_padding() -> None:
    result = project(frame(), at=AT)
    up = listing(result, q="", order="gainers", limit=20)
    down = listing(result, q="", order="losers", limit=20)
    assert [row["symbol"] for row in up["rows"]] == ["TEST_ONLY_0"]
    assert [row["symbol"] for row in down["rows"]] == ["TEST_ONLY_1"]
    assert up["rows"][0]["change"] == "10"
    assert up["rows"][0]["change_percent"] == "10.0"
    assert down["rows"][0]["change_percent"] == "-10.0"
    assert result["configured_securities"] == 3
    assert result["latest_session_securities"] == 2
    assert result["provider_requests"] == 0


def test_missing_prior_slot_never_becomes_multi_session_daily_change() -> None:
    value = frame()
    value["sessions"].insert(1, "2026-10-20")
    result = project(value, at=AT)
    assert result["rows"][0]["previous_close"] is None
    assert result["rows"][0]["change_percent"] is None
    assert result["histories"]["NSE_EQ|INE000000000"][1]["close"] is None
    assert not listing(result, q="", order="gainers", limit=20)["rows"]


def test_stale_and_missing_prices_are_visible_but_never_leaders() -> None:
    value = frame()
    value["rows"] = [
        row
        for row in value["rows"]
        if row["key"] != "NSE_EQ|INE000000000" or row["session"] != "2026-10-21"
    ]
    result = project(value, at=AT)
    assert result["rows"][0]["freshness"] == "STALE"
    assert result["rows"][2]["freshness"] == "UNAVAILABLE"
    assert result["rows"][2]["close"] is None
    assert not listing(result, q="TEST_ONLY_0", order="volume", limit=20)["rows"]
    aged = project(value, at=datetime(2026, 11, 1, tzinfo=UTC))
    assert not listing(aged, q="", order="volume", limit=20)["rows"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("close", "NaN"),
        ("close", "-1"),
        ("low", "112"),
        ("volume", True),
        ("volume", -1),
        ("received_at", "2026-10-25T00:00:00+00:00"),
    ],
)
def test_invalid_source_fields_fail_closed(field: str, value: Any) -> None:
    data = frame()
    data["rows"][0][field] = value
    with pytest.raises(ValueError):
        project(data, at=AT)


def test_duplicate_source_and_future_session_fail_closed() -> None:
    data = frame()
    data["rows"].append(copy.deepcopy(data["rows"][0]))
    with pytest.raises(ValueError, match="DUPLICATE"):
        project(data, at=AT)
    with pytest.raises(ValueError, match="FUTURE"):
        project(frame(), at=datetime(2026, 10, 20, tzinfo=UTC))


def test_search_order_and_bound_are_deterministic() -> None:
    view = project(frame(), at=AT)
    result = listing(view, q="test_only", order="volume", limit=1)
    assert result["rows"][0]["symbol"] == "TEST_ONLY_1"
    assert result["total"] == 2
    with pytest.raises(ValueError):
        listing(view, q="", order="volume", limit=51)


def test_published_research_reads_never_rebuild_sources_and_detect_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from workers.nse_market import engine, saved_market

    root = tmp_path / "TEST_ONLY"
    root.mkdir()
    target = root / "view.json"
    engine._checked(
        target,
        {
            "dataset_id": "TEST_ONLY",
            "as_of": AT.isoformat(),
            "research_workspace": {"coverage": {"dataset_id": "TEST_ONLY"}, "candidates": []},
        },
    )
    engine._pointer(root, "market-view-latest.json", target)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("A saved GET must not rescan raw sources")

    monkeypatch.setattr(engine, "snapshot", forbidden)
    monkeypatch.setattr(engine, "_operations", lambda root: {"state": "TEST_ONLY"})
    result = saved_market.workspace(root)
    assert result is not None and result["operations"]["state"] == "TEST_ONLY"
    target.write_text("TEST_ONLY corrupt")
    with pytest.raises(ValueError, match="CHECKSUM"):
        saved_market.workspace(root)
