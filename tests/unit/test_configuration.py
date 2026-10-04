"""TEST-ONLY configuration, no credentials or external data."""

import pytest
from pydantic import ValidationError

from alphalens_api.core.config import Settings


def test_empty_url_means_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHALENS_DATABASE_URL", "")
    assert Settings().database_url is None


def test_secret_is_hidden() -> None:
    settings = Settings(database_url="postgresql://test_only:TEST_ONLY_VALUE@localhost/test_only")
    assert "TEST_ONLY_VALUE" not in repr(settings)


def test_reject_non_postgres_url() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="https://localhost/test_only")


def test_production_is_not_supported_in_foundation() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "production"})


def test_invalid_config_error_does_not_display_secret_input() -> None:
    with pytest.raises(ValidationError) as raised:
        Settings(database_url="https://test_only:TEST_ONLY_SECRET@localhost/test_only")
    assert "TEST_ONLY_SECRET" not in str(raised.value)
