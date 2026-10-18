"""TEST_ONLY master fixtures. No genuine provider observations or network calls."""

import copy
import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.providers import universe
from workers.providers.upstox import Reply

from alphalens_data.errors import DataContractError

AT = datetime(2026, 10, 17, 11, tzinfo=UTC)


def isin(prefix: str) -> str:
    return next(
        prefix + str(digit) for digit in range(10) if universe.valid_isin(prefix + str(digit))
    )


def row(
    symbol: str = "TEST_ONLY", *, code: str = "INE002A01018", series: str = "EQ"
) -> dict[str, Any]:
    return {
        "segment": "NSE_EQ",
        "exchange": "NSE",
        "isin": code,
        "instrument_key": "NSE_EQ|" + code,
        "name": "TEST_ONLY COMPANY",
        "trading_symbol": symbol,
        "instrument_type": series,
        "security_type": "NORMAL",
        "lot_size": 1,
    }


def reply(rows: list[Any], at: datetime = AT) -> Reply:
    return Reply(200, gzip.compress(json.dumps(rows).encode()), at, "ACCEPTED")


def test_common_equity_excludes_funds_differential_rights_debt_and_unknown_status() -> None:
    fund = row("TEST_ONLY_FUND", code=isin("INF002A0101"))
    rights = row("TEST_ONLY_RIGHTS", code=isin("IN9002A0101"))
    debt = row("TEST_ONLY_DEBT", code=isin("INE002A0801"), series="N1")
    unknown = row("TEST_ONLY_UNKNOWN", code="INE467B01029")
    unknown["security_type"] = "FUTURE_UNKNOWN"
    parsed = universe.parse(reply([row(), fund, rights, debt, unknown]))
    assert len(parsed.eligible) == 1
    assert parsed.summary["discoverable_nse_eq_type_eq"] == 4
    assert parsed.summary["exclusion_counts"] == {
        "FUND_OR_ETF_ISIN": 1,
        "DIFFERENT_EQUITY_RIGHTS_NOT_ORDINARY": 1,
        "UNSUPPORTED_NON_COMMON_SERIES": 1,
        "UNKNOWN_PROVIDER_SECURITY_STATUS": 1,
    }
    assert parsed.summary["provider_accessible_stocks"] is None
    assert parsed.summary["historical_membership_established"] is False
    assert parsed.summary["independently_accepted_ml_stocks"] == 0


@pytest.mark.parametrize("series", sorted(universe.COMMON_SERIES))
def test_official_fully_paid_common_series_are_searchable_with_exact_identity(series: str) -> None:
    parsed = universe.parse(reply([row(series=series)]))
    identity = parsed.eligible[0]
    assert identity.instrument_type == identity.series == series
    assert identity.provider_key == "NSE_EQ|" + str(identity.isin)
    assert universe.is_ordinary_instrument(identity)
    assert identity.observed_at == AT
    assert identity.identity_semantics == "CURRENT_MASTER_NOT_HISTORICAL_MEMBERSHIP"


def test_same_company_noncommon_symbol_does_not_hide_exact_common_identity() -> None:
    debt = row(code=isin("INE002A0801"), series="D1")
    parsed = universe.parse(reply([row(), debt]))
    assert len(parsed.eligible) == 1
    assert len(parsed.records) == 2


def test_duplicate_keys_and_ambiguous_common_symbols_fail_closed() -> None:
    original = row()
    assert not universe.parse(reply([original, original])).eligible
    other = row(code="INE467B01029")
    ambiguous = universe.parse(reply([original, other]))
    assert not ambiguous.eligible
    assert ambiguous.summary["exclusion_counts"] == {"DUPLICATE_OR_AMBIGUOUS_SYMBOL": 2}


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"instrument_key": "NSE_EQ|INE467B01029"}, "INSTRUMENT_KEY_ISIN_MISMATCH"),
        ({"isin": "INE002A01019"}, "INVALID_ISIN_CHECKSUM_OR_FORMAT"),
        ({"name": ""}, "MISSING_OR_INVALID_COMPANY_NAME"),
        ({"instrument_type": "RR"}, "UNSUPPORTED_NON_COMMON_SERIES"),
    ],
)
def test_invalid_or_unsupported_identity_never_enters_common_universe(
    change: dict[str, Any], reason: str
) -> None:
    assert universe.classification({**row(), **change}) == reason


def test_snapshot_roundtrip_pagination_no_network_and_history_changes(tmp_path: Path) -> None:
    root = tmp_path / "private-universe"
    first = universe.save(root, reply([row("TEST_ONLY_A")]))
    assert universe.load(root).snapshot_id == first.snapshot_id
    assert universe.load(root, snapshot_id=first.snapshot_id).snapshot_id == first.snapshot_id
    search = universe.search(root, "company", page_size=1)
    assert search["total"] == 1 and search["provider_requests"] == 0
    assert universe.search(root, "MISSING")["rows"] == []
    renamed = row("TEST_ONLY_RENAMED")
    new = row("TEST_ONLY_NEW", code="INE467B01029")
    second = universe.save(root, reply([renamed, new], AT + timedelta(days=1)))
    delta = universe.changes(first, second)
    assert len(delta["changed"]) == len(delta["added_current_identities"]) == 1
    assert delta["absence_is_not_verified_delisting"] is True
    third = universe.save(root, reply([renamed], AT + timedelta(days=2)))
    assert universe.changes(second, third)["absent_from_current_master"] == [new["instrument_key"]]
    with pytest.raises(DataContractError, match="CANNOT_MOVE_BACKWARD"):
        universe.save(root, reply([row("TEST_ONLY_A")]))


def test_raw_and_derived_snapshot_tampering_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "private-universe"
    snap = universe.save(root, reply([row()]))
    path = root / ("snapshot-" + snap.snapshot_id + ".json")
    original = path.read_bytes()
    document = json.loads(original)
    document["summary"]["verified_eligible_common_equities"] = 999999
    path.write_text(json.dumps(document))
    with pytest.raises(DataContractError, match="CHECKSUM"):
        universe.load(root)
    with pytest.raises(DataContractError, match="DERIVATION"):
        universe.load(root, snapshot_id=snap.snapshot_id)
    path.write_bytes(original)
    raw = root / ("master-" + snap.summary["raw_sha256"] + ".json.gz")
    raw.write_bytes(raw.read_bytes() + b"TEST_ONLY_TAMPER")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        universe.load(root)


@pytest.mark.parametrize("page,size", [(0, 50), (1, 101), (True, 50), (1, False)])
def test_search_bounds_reject_unbounded_requests(tmp_path: Path, page: int, size: int) -> None:
    with pytest.raises(DataContractError, match="BOUNDS"):
        universe.search(tmp_path, page=page, page_size=size)


def test_naive_malformed_and_wrong_shape_master_rejection() -> None:
    with pytest.raises(DataContractError, match="UNDATED"):
        universe.parse(reply([row()], AT.replace(tzinfo=None)))
    with pytest.raises(DataContractError, match="MALFORMED"):
        universe.parse(Reply(200, b"TEST_ONLY_INVALID_GZIP", AT, "ACCEPTED"))
    with pytest.raises(DataContractError, match="MALFORMED"):
        universe.parse(reply([None]))
    invalid = copy.deepcopy(row())
    invalid["instrument_key"] = []
    with pytest.raises(DataContractError, match="IDENTITY_FIELDS_MALFORMED"):
        universe.parse(reply([invalid]))
