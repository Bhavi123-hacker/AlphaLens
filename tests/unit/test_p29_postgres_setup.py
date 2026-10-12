"""Offline configuration safeguards; no real database/financial records created."""

import json
import secrets
from typing import Any
from urllib.parse import quote

import pytest
from scripts.build_p28_test_inputs import CredentialFixture

from alphalens_api.local import postgres


def test_existing_credential_is_preserved_before_any_database_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = CredentialFixture()
    fixture.CredWrite({"CredentialBlob": secrets.token_urlsafe(32)}, 0)
    monkeypatch.setattr(postgres, "credential_module", lambda: fixture)
    with pytest.raises(ValueError, match="PRESERVED"):
        postgres.bootstrap(5432, "TEST_ONLY", secrets.token_urlsafe(32))
    assert fixture.writes == 1


@pytest.mark.parametrize(
    "host,user,path",
    [
        ("remote.invalid", postgres.READER, postgres.DATABASE),
        ("127.0.0.1", "postgres", postgres.DATABASE),
        ("127.0.0.1", postgres.READER, "unrelated"),
    ],
)
def test_stored_uri_cannot_redirect_to_remote_or_privileged_database(
    monkeypatch: pytest.MonkeyPatch, host: str, user: str, path: str
) -> None:
    fixture = CredentialFixture()
    fixture.CredWrite(
        {
            "CredentialBlob": f"postgresql://{user}:{quote(secrets.token_urlsafe(32))}@{host}:5432/{path}"
        },
        0,
    )
    monkeypatch.setattr(postgres, "credential_module", lambda: fixture)
    with pytest.raises(ValueError, match="UNAVAILABLE"):
        postgres.reader_url()


def test_diagnostics_have_no_password_url_or_server_version_claim(tmp_path: Any) -> None:
    result = postgres.diagnose(65534, tmp_path)
    assert result["native17_tools_present"] is False
    assert result["automatic_installation"] is False
    assert result["server_version"] == "NOT_VERIFIED_WITHOUT_AUTHENTICATED_CONNECTION"
    assert "postgresql://" not in json.dumps(result)
