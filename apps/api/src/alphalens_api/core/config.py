"""Validated local configuration; secrets never appear in repr or error text."""

from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALPHALENS_", extra="forbid", hide_input_in_errors=True
    )

    environment: Literal["development", "test"] = "development"
    test_only_evidence: bool = False
    database_url: SecretStr | None = None
    research_data_root: Path | None = None
    research_run_root: Path | None = None
    research_report_root: Path | None = None
    catalog_path: Path | None = None
    port: int = Field(default=8000, ge=1024, le=65535)
    query_timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_concurrent_reads: int = Field(default=2, ge=1, le=8)
    max_ledger_records: int = Field(default=1000, ge=1, le=10000)
    max_response_bytes: int = Field(default=2_000_000, ge=1024, le=8_000_000)
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @model_validator(mode="after")
    def test_scope(self) -> Self:
        if self.test_only_evidence and self.environment != "test":
            raise ValueError("TEST_ONLY evidence requires the isolated test environment")
        return self

    @field_validator("cors_origins")
    @classmethod
    def local_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for origin in value:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Only explicit loopback frontend origins are permitted")
        return value

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
