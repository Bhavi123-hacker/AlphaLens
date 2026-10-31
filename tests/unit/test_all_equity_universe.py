"""TEST_ONLY identity fixtures; no network, provider prices or real model outputs."""

from datetime import timedelta
from pathlib import Path

import pytest
from test_nse_universe import AT, isin, reply, row
from workers.nse_market import discovery
from workers.providers import equity_universe, universe
from workers.providers.upstox import Reply

from alphalens_data.errors import DataContractError


def bse() -> dict[str, object]:
    return {
        **row(),
        "segment": "BSE_EQ",
        "exchange": "BSE",
        "instrument_type": "A",
        "instrument_key": "BSE_EQ|INE002A01018",
        "security_type": None,
    }


def test_distinct_exchange_listing_same_company_and_no_bse_collection(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY"
    original = universe.save(root, reply([row()]))
    pointer = (root / "latest.json").read_bytes()
    expanded = universe.save(root, reply([row(), bse()], AT + timedelta(days=1)), expanded=True)
    assert (root / "latest.json").read_bytes() == pointer
    assert universe.load(root).snapshot_id == original.snapshot_id
    assert universe.load(root, expanded=True).snapshot_id == expanded.snapshot_id
    assert discovery.load_catalog(root).snapshot_id == expanded.snapshot_id
    assert len(expanded.records) == 2 and expanded.summary["unique_ordinary_company_isins"] == 1
    assert expanded.summary["eligible_by_exchange"] == {"NSE": 1, "BSE": 1}
    assert len(expanded.eligible) == 1 and expanded.eligible[0].exchange == "NSE"
    assert expanded.records[0]["instrument_key"] != expanded.records[1]["instrument_key"]
    assert expanded.summary["bse_ml_compatible"] is False
    assert (
        next(r for r in expanded.records if r["exchange"] == "BSE")["provider_status_available"]
        is False
    )


def test_other_categories_remain_visible_as_exclusions_not_ordinary_predictions() -> None:
    fund = {**bse(), "isin": isin("INF002A0101")}
    fund["instrument_key"] = "BSE_EQ|" + str(fund["isin"])
    debt = {**bse(), "isin": isin("INE002A0801"), "instrument_type": "F"}
    debt["instrument_key"] = "BSE_EQ|" + str(debt["isin"])
    derivative = {**row(), "segment": "NSE_FO", "instrument_type": "FUT"}
    index = {**row(), "segment": "NSE_INDEX", "instrument_type": "INDEX"}
    snapshot = universe.parse(reply([bse(), fund, debt, derivative, index]), expanded=True)
    assert snapshot.summary["all_bod_records"] == 5
    assert snapshot.summary["verified_eligible_common_equities"] == 1
    assert len(snapshot.records) == 3
    assert not snapshot.eligible  # NSE-only collector remains closed.
    excluded = [r for r in snapshot.records if not r["eligible_common_equity"]]
    assert {r["classification"] for r in excluded} == {
        "FUND_OR_ETF_ISIN",
        "UNVERIFIED_ORDINARY_EQUITY_ISIN_CLASS",
    }
    assert discovery.empty_security(snapshot.records[0])["close"] is None


def test_duplicate_symbols_do_not_hide_exchange_specific_keys_but_keys_fail_closed() -> None:
    other = {**bse(), "isin": "INE467B01029", "instrument_key": "BSE_EQ|INE467B01029"}
    snapshot = universe.parse(reply([bse(), other]), expanded=True)
    assert snapshot.summary["searchable_unique_instrument_keys"] == 2
    ambiguous = universe.parse(reply([bse(), bse()]), expanded=True)
    assert ambiguous.summary["searchable_unique_instrument_keys"] == 0
    assert (
        discovery.empty_security(ambiguous.records[0])["availability_state"]
        == "INSTRUMENT_IDENTITY_AMBIGUOUS"
    )


@pytest.mark.parametrize("expanded", [False, True])
def test_truncated_master_is_a_contract_rejection_not_an_uncaught_decompression_error(
    expanded: bool,
) -> None:
    raw = reply([row()])
    with pytest.raises(DataContractError, match="MALFORMED"):
        universe.parse(Reply(200, raw.body[:-4], AT, "ACCEPTED"), expanded=expanded)


@pytest.mark.parametrize("expanded", [False, True])
def test_corrupt_deflate_stream_is_a_contract_rejection(expanded: bool) -> None:
    raw = reply([row()])
    # Keep the gzip header and trailer but inject a reserved DEFLATE block type.
    corrupt = raw.body[:10] + bytes([(raw.body[10] & 0xF8) | 0x07]) + raw.body[11:]
    with pytest.raises(DataContractError, match="MALFORMED"):
        universe.parse(Reply(200, corrupt, AT, "ACCEPTED"), expanded=expanded)


@pytest.mark.parametrize("value", [[], {}])
def test_malformed_bse_category_fields_fail_closed(value: object) -> None:
    assert (
        equity_universe.classify({**bse(), "instrument_type": value})
        == "UNSUPPORTED_NON_COMMON_GROUP"
    )
    assert (
        equity_universe.classify({**bse(), "security_type": value})
        == "UNKNOWN_PROVIDER_SECURITY_STATUS"
    )
    snapshot = universe.parse(reply([bse(), {"segment": value}]), expanded=True)
    assert snapshot.summary["verified_eligible_common_equities"] == 1
    assert snapshot.summary["all_bod_records"] == 2
