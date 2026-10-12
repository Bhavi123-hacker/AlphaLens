"""Offline TEST_ONLY adapter contracts. No broker/Yahoo/Alpha Vantage requests."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from scripts.build_p28_test_inputs import AT, DAY, instrument, payload
from workers.providers.store import ProviderStore

from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_adapters import (
    DisabledAdapter,
    p2_rows,
    parse_daily,
    upstox_instruments,
)
from alphalens_data.providers.multi_contracts import Access, Candle
from alphalens_data.providers.test_bundle import parse_bundle


@pytest.mark.parametrize("provider", ["upstox", "indstocks", "angel-one"])
def test_native_daily_schema_exact_decimals_and_clocks(provider: Any) -> None:
    rows = parse_daily(payload(provider), instrument(provider), AT, "TEST_ONLY")
    assert rows[0].session == DAY
    assert rows[0].open == Decimal("100.123456789")
    assert rows[0].publication_time is None
    assert rows[0].source_revision is None
    assert rows[0].price_basis == "UNKNOWN"
    assert rows[0].classification == "TEST_ONLY"
    with pytest.raises(DataContractError, match="RAW_PRICE"):
        p2_rows(rows)


def test_upstox_master_does_not_infer_equity_series_or_historic_membership() -> None:
    body = json.dumps(
        [
            {
                "exchange": "NSE",
                "segment": "NSE_EQ",
                "instrument_type": "EQ",
                "instrument_key": "NSE_EQ|INE000A00001",
                "isin": "INE000A00001",
                "trading_symbol": "TEST_ONLY",
                "name": "TEST_ONLY COMPANY",
            }
        ]
    ).encode()
    row = upstox_instruments(body, AT)[0]
    assert row.series is None
    assert row.canonical_security_id is None
    assert row.identity_semantics == "CURRENT_MASTER_NOT_HISTORICAL_MEMBERSHIP"
    assert row.revision_sha256 == checksum(body)


@pytest.mark.parametrize(
    "provider,key",
    [
        ("upstox", "BSE_EQ|INE000A00001"),
        ("yahoo", "TEST_ONLY.BO"),
        ("alpha-vantage", "RELIANCE.BSE"),
    ],
)
def test_exchange_identity_cannot_be_replaced_by_company_name(provider: Any, key: str) -> None:
    with pytest.raises(ValidationError):
        instrument(provider, provider_key=key)


def test_indstocks_missing_requested_key_is_not_complete_release() -> None:
    with pytest.raises(DataContractError, match="EXPECTED_INSTRUMENT_MISSING"):
        parse_daily(b'{"success":true,"data":{}}', instrument("indstocks"), AT, "TEST_ONLY")


def test_duplicate_candle_session_is_rejected() -> None:
    body = json.loads(payload("upstox"))
    body["data"]["candles"] *= 2
    with pytest.raises(DataContractError, match="DUPLICATE"):
        parse_daily(json.dumps(body).encode(), instrument(), AT, "TEST_ONLY")


@pytest.mark.parametrize("replacement", [True, "1.5", -1])
def test_volume_does_not_silently_round_or_accept_bool(replacement: Any) -> None:
    body = json.loads(payload("upstox"))
    body["data"]["candles"][0][5] = replacement
    with pytest.raises((DataContractError, ValidationError)):
        parse_daily(json.dumps(body).encode(), instrument(), AT, "TEST_ONLY")


def test_provider_timestamp_requires_timezone_and_past_receipt() -> None:
    body = json.loads(payload("upstox"))
    body["data"]["candles"][0][0] = "2026-10-09T00:00:00"
    with pytest.raises(DataContractError, match="TIMEZONE_UNKNOWN"):
        parse_daily(json.dumps(body).encode(), instrument(), AT, "TEST_ONLY")
    body["data"]["candles"][0][0] = "2026-10-12T00:00:00+05:30"
    with pytest.raises(DataContractError, match="FUTURE"):
        parse_daily(json.dumps(body).encode(), instrument(), AT, "TEST_ONLY")


@pytest.mark.parametrize(
    "provider", ["upstox", "indstocks", "angel-one", "alpha-vantage", "yahoo", "tejhq"]
)
def test_every_runtime_adapter_stays_disabled_even_with_permission_flags(provider: Any) -> None:
    access = Access(
        provider=provider,
        account_status="ACTIVE",
        credential_configured=True,
        automation_permitted=True,
        retention_permitted=True,
        research_permitted=True,
        permission_reference="TEST_ONLY",
        nse_verified=True,
        token_kind="READ_ONLY_ANALYTICS",
        operator_activation=True,
    )
    adapter = DisabledAdapter(provider, access)
    assert adapter.get_daily_ohlcv((instrument(provider),), DAY, DAY).state == "BLOCKED"
    assert adapter.get_latest_quote((instrument(provider),)).state == "BLOCKED"
    assert adapter.get_corporate_actions(instrument(provider)).state == "UNAVAILABLE"
    assert adapter.get_provider_health(AT)["collection_enabled"] is False


def test_under_review_and_expired_token_reasons_remain_distinct() -> None:
    access = Access(
        provider="upstox", account_status="UNDER_REVIEW", token_expires_at=AT - timedelta(seconds=1)
    )
    assert "ACCOUNT_UNDER_REVIEW" in access.blockers(AT)
    assert "TOKEN_EXPIRED" in access.blockers(AT)
    assert "READ_ONLY_ANALYTICS_TOKEN_REQUIRED" in access.blockers(AT)


@pytest.mark.parametrize("provider", ["upstox", "indstocks", "angel-one"])
def test_read_only_request_plans_contain_no_credentials_or_trading_operations(
    provider: Any,
) -> None:
    plan = DisabledAdapter(provider).plan_daily((instrument(provider),), DAY, DAY)
    assert plan.operation == "daily_ohlcv"
    assert plan.enabled is False
    assert plan.contains_credentials is False
    assert "order" not in plan.path
    if provider == "indstocks":
        assert int(plan.parameters["end_time"]) - int(plan.parameters["start_time"]) == 86400000
    if provider == "upstox":
        assert "NSE_EQ%7C" in plan.path


def test_test_bundle_preserves_native_bytes_and_blocks_real_identity_injection() -> None:
    native = payload("upstox")
    value: dict[str, Any] = {
        "version": "p28.test-provider.v1",
        "classification": "TEST_ONLY",
        "price_basis": "RAW_UNADJUSTED",
        "provider": "upstox",
        "native_payload_hex": native.hex(),
        "native_payload_sha256": checksum(native),
        "instruments": [instrument().model_dump(mode="json")],
    }
    raw, rows, names, lineage = parse_bundle(json.dumps(value).encode(), "upstox", DAY, AT)
    assert raw == native and len(rows) == 1
    assert dict(rows[0].fields)["open"] == "100.123456789"
    assert lineage["native_payload_sha256"] == checksum(native)
    value["instruments"][0]["canonical_security_id"] = "tejhq:isin:INE002A01018"
    with pytest.raises(DataContractError):
        parse_bundle(json.dumps(value).encode(), "upstox", DAY, AT)


@pytest.fixture
def store(tmp_path: Path) -> ProviderStore:
    result = ProviderStore(tmp_path / "TEST_ONLY_provider_state")
    result.initialize()
    return result


def test_store_restarts_selection_disabled_and_refuses_destructive_initialization(
    store: ProviderStore,
) -> None:
    store.select("upstox", 100000)
    assert ProviderStore(store.root).status(100000)["selected_provider"] == "upstox"
    assert store.status(100000)["collection_enabled"] is False
    with pytest.raises(DataContractError, match="NEW_PROVIDER"):
        store.initialize()


def test_concurrent_reservation_is_idempotent_and_pending_survives_restart(
    store: ProviderStore,
) -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.reserve("upstox", "a" * 64, 1, 100000), range(4)))
    assert results.count(True) == 1
    assert ProviderStore(store.root).status(100000)["pending_attempts"] == 1


def test_rate_limit_retry_after_and_bounded_attempts(store: ProviderStore) -> None:
    assert store.reserve("indstocks", "a" * 64, 1, 100000)
    store.finish("indstocks", "a" * 64, 1, 100001, 429, 600)
    with pytest.raises(DataContractError, match="BACKOFF"):
        store.reserve("indstocks", "a" * 64, 2, 100100)
    assert store.reserve("indstocks", "a" * 64, 2, 100601)
    store.finish("indstocks", "a" * 64, 2, 100602, 503)
    assert store.reserve("indstocks", "a" * 64, 3, 100606)
    store.finish("indstocks", "a" * 64, 3, 100607, 503)
    with pytest.raises(DataContractError, match="RETRY_EXCEEDED"):
        store.reserve("indstocks", "a" * 64, 4, 100620)


def test_quota_includes_failed_calls_auth_is_not_retryable(store: ProviderStore) -> None:
    for i in range(5):
        request = checksum(str(i).encode())
        store.reserve("indstocks", request, 1, 100000 + i / 10)
        store.finish("indstocks", request, 1, 100000 + i / 10, 401)
    with pytest.raises(DataContractError, match="QUOTA"):
        store.reserve("indstocks", "b" * 64, 1, 100000.5)
    with pytest.raises(DataContractError, match="RETRY_NOT_ELIGIBLE"):
        store.reserve("indstocks", checksum(b"0"), 2, 100010)


def test_invalid_ohlc_never_enters_candle_contract() -> None:
    rows = parse_daily(payload("upstox"), instrument(), AT, "TEST_ONLY")
    with pytest.raises(ValidationError, match="OHLC_RANGE"):
        Candle.model_validate({**rows[0].model_dump(), "high": Decimal("98")})
