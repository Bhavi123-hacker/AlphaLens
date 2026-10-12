"""Credential and quota tests use generated TEST_ONLY material; never real provider calls."""

import json
import secrets
from pathlib import Path
from typing import Any

import pytest

from alphalens_api import credentials


class MissingCredential(Exception):
    winerror = 1168


class CredentialFixture:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    def __init__(self) -> None:
        self.record: dict[str, Any] | None = None
        self.writes = 0

    def CredRead(self, target: str, kind: int) -> dict[str, Any]:
        if self.record is None:
            raise MissingCredential
        return {**self.record, "CredentialBlob": self.record["CredentialBlob"].encode("utf-16-le")}

    def CredWrite(self, record: dict[str, Any], flags: int) -> None:
        self.record = record
        self.writes += 1


def test_import_readback_replay_and_original_file_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = CredentialFixture()
    monkeypatch.setattr(credentials, "credential_module", lambda: fixture)
    secret = secrets.token_hex(8)
    path = tmp_path / "TEST_ONLY_input.txt"
    path.write_text(secret)
    report = credentials.import_key(path)
    assert report["readback_verified"] is True
    assert secret not in json.dumps(report)
    assert credentials.load_key() == secret
    credentials.import_key(path)
    assert fixture.writes == 1
    assert path.exists()
    path.write_text(secrets.token_hex(8))
    with pytest.raises(ValueError, match="PRESERVED"):
        credentials.import_key(path)
    assert fixture.writes == 1


def test_invalid_file_never_reaches_windows_store(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY_bad.txt"
    path.write_text("TEST_ONLY not a provider key")
    with pytest.raises(ValueError, match="INPUT_INVALID"):
        credentials.import_key(path)


def test_search_bse_not_nse_and_messages_are_redacted() -> None:
    secret = secrets.token_hex(8)
    payload = json.dumps(
        {
            "bestMatches": [
                {
                    "1. symbol": "RELIANCE.BSE",
                    "4. region": "India/Bombay",
                    "3. type": "Equity",
                    "8. currency": "INR",
                }
            ]
        }
    ).encode()
    result = credentials.classify_search(payload, secret)
    assert result["matches"][0]["exchange_evidence"] == "BSE_SYMBOL_NOT_NSE"
    assert result["nse_coverage"] == "NOT_ESTABLISHED"
    assert result["accessible_nse_sessions"] == []
    error = credentials.classify_search(json.dumps({"Error Message": secret}).encode(), secret)
    assert secret not in json.dumps(error)


def test_provider_echoed_secret_is_discarded() -> None:
    secret = secrets.token_hex(8)
    result = credentials.classify_search(
        json.dumps({"bestMatches": [{"1. symbol": secret}]}).encode(), secret
    )
    assert result["matches"] == []


def test_rolling_quota_counts_failed_attempts_and_never_exceeds_25(tmp_path: Path) -> None:
    for i in range(25):
        credentials.reserve_request(tmp_path, 100000 + i)
    with pytest.raises(ValueError, match="REQUEST_LIMIT"):
        credentials.reserve_request(tmp_path, 100100)
    credentials.reserve_request(tmp_path, 100000 + 86401)


def test_no_redirect_or_network_retry_after_probe_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    class FailedConnection:
        def __init__(self, host: str, timeout: int) -> None:
            calls.append(host)

        def request(self, *args: Any, **kwargs: Any) -> None:
            raise OSError("TEST_ONLY sensitive URL should not escape")

        def close(self) -> None:
            pass

    monkeypatch.setattr(credentials, "load_key", lambda: secrets.token_hex(8))
    monkeypatch.setattr(credentials, "state_root", lambda: tmp_path)
    monkeypatch.setattr(credentials, "HTTPSConnection", FailedConnection)
    with pytest.raises(ValueError, match="NO_AUTOMATIC_RETRY"):
        credentials.probe_search()
    assert calls == ["www.alphavantage.co"]
