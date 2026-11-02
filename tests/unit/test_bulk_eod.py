"""Unit tests for bulk EOD adapters (BSE CM-UDiFF, BSE Classic Bhavcopy)
and corporate-action normalization.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from workers.nse_market.bulk_eod import (
    ADJUSTED_BASIS,
    BSE_CLASSIC_HEADERS,
    BSE_CLASSIC_SOURCE,
    BSE_UDIFF_SOURCE,
    BSE_UNADJUSTED_BASIS,
    UDIFF_HEADERS,
    CorporateAction,
    CorporateActionCoverage,
    extract_csv_payload,
    normalize_with_corporate_actions,
    parse_bse_classic_rows,
    parse_cm_udiff_rows,
    rows_to_chart_history,
)

ISIN_VALID = "INE002A01018"
ISIN_BSE_ONLY = "INE009A01021"


def create_bse_udiff_csv(
    session_str: str = "20261030",
    changes: dict[str, str] | None = None,
) -> bytes:
    row = dict.fromkeys(UDIFF_HEADERS, "")
    row.update(
        TradDt=f"{session_str[:4]}-{session_str[4:6]}-{session_str[6:]}",
        BizDt=f"{session_str[:4]}-{session_str[4:6]}-{session_str[6:]}",
        Sgmt="CM",
        Src="BSE",
        FinInstrmTp="STK",
        FinInstrmId="500325",
        ISIN=ISIN_VALID,
        TckrSymb="RELIANCE",
        SctySrs="A",
        FinInstrmNm="RELIANCE INDUSTRIES LTD",
        OpnPric="1400.00",
        HghPric="1420.00",
        LwPric="1390.00",
        ClsPric="1410.00",
        TtlTradgVol="50000",
        SsnId="F1",
    )
    if changes:
        row.update(changes)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=UDIFF_HEADERS)
    writer.writeheader()
    writer.writerow(row)
    return text.getvalue().encode()


def create_bse_classic_csv(
    changes: dict[str, str] | None = None,
) -> bytes:
    row = dict.fromkeys(BSE_CLASSIC_HEADERS, "")
    row.update(
        SC_CODE="500325",
        SC_NAME="RELIANCE IND",
        SC_GROUP="A",
        SC_TYPE="Q",
        OPEN="1400.00",
        HIGH="1420.00",
        LOW="1390.00",
        CLOSE="1410.00",
        LAST="1410.00",
        PREVCLOSE="1395.00",
        NO_TRADES="1200",
        NO_OF_SHRS="50000",
        NET_TURNOV="70500000",
        TDCLOIF="0",
        IND_SEC="",
        ISIN_CODE=ISIN_VALID,
    )
    if changes:
        row.update(changes)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=BSE_CLASSIC_HEADERS)
    writer.writeheader()
    writer.writerow(row)
    return text.getvalue().encode()


def test_extract_csv_payload_bse_udiff_zip(tmp_path: Path) -> None:
    csv_bytes = create_bse_udiff_csv("20261030") * 10
    zip_path = tmp_path / "BhavCopy_BSE_CM_0_0_0_20261030_F_0000.csv.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as arc:
        arc.writestr("BhavCopy_BSE_CM_0_0_0_20261030_F_0000.csv", csv_bytes)

    raw, body, session, fmt = extract_csv_payload(zip_path)
    assert fmt == "BSE_UDIFF"
    assert session == date(2026, 10, 30)
    assert body == csv_bytes
    assert len(raw) < len(body)


def test_extract_csv_payload_bse_classic_csv(tmp_path: Path) -> None:
    csv_bytes = create_bse_classic_csv()
    csv_path = tmp_path / "EQ301026.CSV"
    csv_path.write_bytes(csv_bytes)

    raw, body, session, fmt = extract_csv_payload(csv_path)
    assert fmt == "BSE_CLASSIC"
    assert session == date(2026, 10, 30)
    assert body == csv_bytes


def test_extract_csv_payload_unrecognized_filename(tmp_path: Path) -> None:
    path = tmp_path / "random_file.csv"
    path.write_bytes(b"data")
    with pytest.raises(ValueError, match="BULK_EOD_UNRECOGNIZED_OFFICIAL_FILENAME"):
        extract_csv_payload(path)


def test_parse_bse_cm_udiff_rows() -> None:
    session = date(2026, 10, 30)
    csv_bytes = create_bse_udiff_csv("20261030")
    accepted, exclusions = parse_cm_udiff_rows(csv_bytes, session, expected_exchange="BSE")

    assert len(accepted) == 1
    assert len(exclusions) == 0
    row = accepted[0]
    assert row["key"] == f"BSE_EQ|{ISIN_VALID}"
    assert row["exchange"] == "BSE"
    assert row["segment"] == "BSE_EQ"
    assert row["source"] == BSE_UDIFF_SOURCE
    assert row["price_basis"] == BSE_UNADJUSTED_BASIS
    assert row["close"] == "1410.00"
    assert row["volume"] == 50000
    assert row["model_compatible"] is False
    assert row["ml_gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"


def test_parse_bse_classic_rows() -> None:
    session = date(2026, 10, 30)
    csv_bytes = create_bse_classic_csv()
    accepted, exclusions = parse_bse_classic_rows(csv_bytes, session)

    assert len(accepted) == 1
    assert len(exclusions) == 0
    row = accepted[0]
    assert row["key"] == f"BSE_EQ|{ISIN_VALID}"
    assert row["exchange"] == "BSE"
    assert row["source"] == BSE_CLASSIC_SOURCE
    assert row["price_basis"] == BSE_UNADJUSTED_BASIS
    assert row["open"] == "1400.00"
    assert row["high"] == "1420.00"
    assert row["low"] == "1390.00"
    assert row["close"] == "1410.00"
    assert row["volume"] == 50000
    assert row["model_compatible"] is False
    assert row["ml_gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"


def test_parse_bse_classic_exclusions() -> None:
    session = date(2026, 10, 30)
    # Non-ordinary group (e.g. debt / preference 'F')
    # When all rows are excluded, it fails closed with BULK_EOD_NO_ACCEPTABLE_BSE_ROWS
    csv_bytes = create_bse_classic_csv({"SC_GROUP": "F"})
    with pytest.raises(ValueError, match="BULK_EOD_NO_ACCEPTABLE_BSE_ROWS"):
        parse_bse_classic_rows(csv_bytes, session)


def test_corporate_action_unverified_coverage_fails_closed() -> None:
    session = date(2026, 10, 15)
    as_of = date(2026, 10, 30)

    unadjusted_rows = [
        {
            "key": f"NSE_EQ|{ISIN_VALID}",
            "isin": ISIN_VALID,
            "exchange": "NSE",
            "series": "EQ",
            "session": str(session),
            "open": "2000.00",
            "high": "2100.00",
            "low": "1950.00",
            "close": "2050.00",
            "volume": 10000,
            "price_basis": "NSE_EXCHANGE_REPORTED_UNADJUSTED_EOD",
        }
    ]

    # Critical invariant: Empty action list with NO verified coverage must FAIL CLOSED
    norm_no_cov = normalize_with_corporate_actions(unadjusted_rows, [], coverage=None, as_of=as_of)
    assert len(norm_no_cov) == 1
    assert (
        norm_no_cov[0]["corporate_action_status"]
        == "UNVERIFIED_ACTION_COVERAGE_UNQUALIFIED_FOR_ADJUSTED_MODEL"
    )
    assert norm_no_cov[0]["model_compatible"] is False
    assert norm_no_cov[0]["ml_gate"] == "CORPORATE_ACTION_COVERAGE_NOT_VERIFIED"
    assert norm_no_cov[0]["adjustment_factor"] == "1"


def test_corporate_action_normalization_split_and_bonus() -> None:
    session = date(2026, 10, 15)
    as_of = date(2026, 10, 30)

    unadjusted_rows = [
        {
            "key": f"NSE_EQ|{ISIN_VALID}",
            "isin": ISIN_VALID,
            "exchange": "NSE",
            "series": "EQ",
            "session": str(session),
            "open": "2000.00",
            "high": "2100.00",
            "low": "1950.00",
            "close": "2050.00",
            "volume": 10000,
            "price_basis": "NSE_EXCHANGE_REPORTED_UNADJUSTED_EOD",
        },
        {
            "key": f"BSE_EQ|{ISIN_BSE_ONLY}",
            "isin": ISIN_BSE_ONLY,
            "exchange": "BSE",
            "series": "A",
            "session": str(session),
            "open": "500.00",
            "high": "520.00",
            "low": "490.00",
            "close": "510.00",
            "volume": 2000,
            "price_basis": "BSE_EXCHANGE_REPORTED_UNADJUSTED_EOD",
        },
    ]

    # Explicit verified coverage covering both ISINs through 2026-10-31
    coverage = CorporateActionCoverage(
        verified_coverage_as_of=date(2026, 10, 31),
        verified_isins=frozenset({ISIN_VALID, ISIN_BSE_ONLY}),
        coverage_evidence="TEST_ONLY_OFFICIAL_DISCLOSURE_RECEIPT",
        coverage_sha256="0" * 64,
    )

    # Split: 10 for 1 on 2026-10-20 -> factor 0.1
    actions = [
        CorporateAction(
            isin=ISIN_VALID,
            ex_date=date(2026, 10, 20),
            action_type="SPLIT",
            ratio_from=Decimal("10"),
            ratio_to=Decimal("1"),
            adjustment_factor=Decimal("0.1"),
        )
    ]

    norm = normalize_with_corporate_actions(
        unadjusted_rows, actions, coverage=coverage, as_of=as_of
    )
    assert len(norm) == 2

    nse_norm = next(r for r in norm if r["exchange"] == "NSE")
    assert nse_norm["corporate_action_status"] == "QUALIFIED_EXPLICIT_FACTOR_ADJUSTED"
    assert nse_norm["adjustment_factor"] == "0.1"
    assert nse_norm["open"] == "200.0000"
    assert nse_norm["high"] == "210.0000"
    assert nse_norm["low"] == "195.0000"
    assert nse_norm["close"] == "205.0000"
    assert nse_norm["raw_close"] == "2050.00"
    # Volume adjustment policy: raw volume 10,000 / 0.1 = 100,000 adjusted shares
    assert nse_norm["volume"] == 100000
    assert nse_norm["raw_volume"] == 10000
    assert nse_norm["price_basis"] == ADJUSTED_BASIS
    # NSE stock qualifies for ML once properly adjusted
    assert nse_norm["model_compatible"] is True
    assert nse_norm["ml_gate"] == "PASSED_FACTOR_ADJUSTMENT"

    bse_norm = next(r for r in norm if r["exchange"] == "BSE")
    assert (
        bse_norm["corporate_action_status"]
        == "QUALIFIED_NO_ACTIONS_VERIFIED_UNADJUSTED_EQUALS_ADJUSTED"
    )
    assert bse_norm["adjustment_factor"] == "1"
    assert bse_norm["close"] == "510.0000"
    assert bse_norm["volume"] == 2000
    # BSE stock is strictly forbidden from unverified model inference
    assert bse_norm["model_compatible"] is False
    assert bse_norm["ml_gate"] == "BSE_DOMAIN_MODEL_NOT_VALIDATED"


def test_rows_to_chart_history_integration() -> None:
    session = date(2026, 10, 30)
    rows = [
        {
            "key": f"NSE_EQ|{ISIN_VALID}",
            "session": str(session),
            "open": "200.0000",
            "high": "210.0000",
            "low": "195.0000",
            "close": "205.0000",
            "volume": 100000,
            "price_basis": ADJUSTED_BASIS,
            "corporate_action_status": "QUALIFIED_EXPLICIT_FACTOR_ADJUSTED",
        }
    ]
    histories = rows_to_chart_history(rows)
    assert f"NSE_EQ|{ISIN_VALID}" in histories
    candles = histories[f"NSE_EQ|{ISIN_VALID}"]
    assert len(candles) == 1
    candle = candles[0]
    assert candle["session"] == "2026-10-30"
    assert candle["close"] == 205.0
    assert candle["volume"] == 100000
    assert candle["price_basis"] == ADJUSTED_BASIS
