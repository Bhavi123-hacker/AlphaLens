"""Validated local configuration; secrets never appear in repr or error text."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALPHALENS_", extra="forbid", hide_input_in_errors=True
    )

    environment: Literal["development", "test"] = "development"
    database_url: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            parsed = urlsplit(value.get_secret_value())
            if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
                raise ValueError("A PostgreSQL URL is required")
        return value
