"""Validated local configuration; secrets never appear in repr or error text."""

import re
from ipaddress import ip_address
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
    access_mode: Literal["loopback", "hosted_private"] = "loopback"
    public_origin: str | None = None
    allowed_hosts: tuple[str, ...] = ()
    hosted_data_root: Path | None = None
    hosted_bind_host: str | None = None
    test_only_evidence: bool = False
    database_url: SecretStr | None = None
    database_credential_target: Literal["AlphaLens/PostgreSQL/ResearchReadOnly"] | None = None
    research_data_root: Path | None = None
    research_run_root: Path | None = None
    research_report_root: Path | None = None
    catalog_path: Path | None = None
    daily_root: Path | None = None
    alerts_root: Path | None = None
    auth_root: Path | None = None
    operations_root: Path | None = None
    providers_root: Path | None = None
    upstox_validation_root: Path | None = None
    upstox_private_view: bool = False
    private_eod_config: Path | None = None
    experimental_nse_root: Path | None = None
    experimental_nse_v2_root: Path | None = None
    frontend_root: Path | None = None
    alert_mutations: bool = False
    personal_root: Path | None = None
    personal_mutations: bool = False
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
        if self.access_mode == "loopback":
            if self.public_origin or self.allowed_hosts or self.hosted_bind_host:
                raise ValueError("Hosted settings require explicit hosted_private access mode")
            if any(
                urlsplit(value).hostname not in {"localhost", "127.0.0.1", "::1"}
                for value in self.cors_origins
            ):
                raise ValueError("Only explicit loopback frontend origins are permitted")
        else:
            if not self.hosted_bind_host or not ip_address(self.hosted_bind_host).is_unspecified:
                raise ValueError("Hosted private access requires an explicit platform bind address")
            parsed = urlsplit(self.public_origin or "")
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.netloc != parsed.hostname
                or self.cors_origins != (self.public_origin,)
            ):
                raise ValueError("Hosted private access requires one exact HTTPS browser origin")
            if (
                not 1 <= len(self.allowed_hosts) <= 4
                or len(set(self.allowed_hosts)) != len(self.allowed_hosts)
                or parsed.hostname not in self.allowed_hosts
                or any(
                    not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host)
                    or ".." in host
                    for host in self.allowed_hosts
                )
            ):
                raise ValueError("Hosted private access requires explicit non-wildcard hostnames")
            if (
                self.hosted_data_root is None
                or self.auth_root is None
                or self.operations_root is None
            ):
                raise ValueError(
                    "Hosted private access requires persistent data, auth and operations roots"
                )
            if self.frontend_root is None:
                raise ValueError("Hosted private access requires the compiled same-origin frontend")
            if self.database_credential_target is not None or self.private_eod_config is not None:
                raise ValueError(
                    "Hosted private access cannot activate Windows credentials or collectors"
                )
        return self

    @field_validator("cors_origins")
    @classmethod
    def local_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for origin in value:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
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
