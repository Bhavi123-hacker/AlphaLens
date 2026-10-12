"""Capacity numbers are plans, never claims of NSE coverage or provider permission."""

import getpass
import json
import secrets
from datetime import timedelta

import pytest
from scripts.build_p28_test_inputs import AT, DAY, instrument, payload
from workers.providers import credentials
from workers.providers.cli import main
from workers.providers.eligibility import PeerScope, assess
from workers.providers.readiness import comparison, rate_only_seconds

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import parse_daily


def test_capacity_estimates_include_upstox_half_hour_and_indstocks_batching() -> None:
    rows = {p["provider"]: p for p in comparison()["providers"]}
    assert rows["upstox"]["daily_capacity"][1]["calls"] == 500
    assert rows["indstocks"]["daily_capacity"][1]["calls"] == 100
    assert rows["upstox"]["daily_capacity"][2]["rate_only_minimum_seconds"] >= 1800
    assert rows["alpha-vantage"]["daily_capacity"][0]["within_known_daily_quota"] is False
    assert rate_only_seconds(50, "yahoo") is None
    assert all(p["collection_enabled"] is False for p in rows.values())


@pytest.mark.parametrize(
    "body",
    [
        b'{"status":"success"}',
        b'{"status":"success","data":null}',
        b'{"status":"success","data":{"candles":[["secret",1,2,1,1,1]]}}',
    ],
)
def test_malformed_bodies_produce_safe_reason_not_raw_message(body: bytes) -> None:
    with pytest.raises(DataContractError) as error:
        parse_daily(body, instrument(), AT)
    assert "secret" not in str(error.value)


def test_peer_missing_scope_is_not_neutral_feature() -> None:
    candles = parse_daily(payload("upstox"), instrument(), AT, "TEST_ONLY")
    scope = PeerScope(
        session=DAY,
        provider="upstox",
        expected_isins=("INE000A00001", "INE000A01002"),
        membership_sha256="a" * 64,
        membership_available_at=AT,
    )
    result = assess(scope, candles, AT, ("momentum_percentile_20",), {})
    assert result["coverage_complete"] is False
    assert result["missing_isins"] == ["INE000A01002"]
    assert result["current_inference"] == "UNAVAILABLE"
    assert "FROZEN_38_FEATURE_CONTRACT_REQUIRED" in result["evidence_blockers"]
    assert result["feature_compatibility"]["values"] is None
    future = scope.model_copy(update={"membership_available_at": AT + timedelta(days=1)})
    assert (
        "CONTEMPORANEOUS_PEER_MEMBERSHIP_UNAVAILABLE"
        in assess(future, candles, AT, (), {})["evidence_blockers"]
    )


def test_cli_comparison_and_rejection_never_have_enable_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["comparison"]) == 0
    assert json.loads(capsys.readouterr().out)["collection_enabled"] is False
    with pytest.raises(SystemExit):
        main(["enable"])


def test_future_analytics_import_redacted_idempotent_and_no_scope_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.build_p28_test_inputs import CredentialFixture

    fixture = CredentialFixture()
    secret = secrets.token_urlsafe(40)
    monkeypatch.setattr(getpass, "getpass", lambda _: secret)
    monkeypatch.setattr(credentials, "credential_module", lambda: fixture)
    result = credentials.import_analytics()
    assert result["readback_verified"] is True and result["collection_enabled"] is False
    assert "NOT_SERVER_VERIFIED" in result["scope_evidence"]
    assert secret not in json.dumps(result)
    credentials.import_analytics()
    assert fixture.writes == 1
    monkeypatch.setattr(getpass, "getpass", lambda _: secrets.token_urlsafe(40))
    with pytest.raises(ValueError, match="PRESERVED"):
        credentials.import_analytics()
    assert fixture.writes == 1
