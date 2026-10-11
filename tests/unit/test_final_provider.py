"""TEST_ONLY publication metadata; no price downloader or source permission waiver."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from alphalens_data.daily import providers
from alphalens_data.errors import DataContractError


def payload(**changes: Any) -> bytes:
    value = dict(
        trading_date="2026-10-09",
        stage="derived",
        prices_published_at="2026-10-09T20:39:58Z",
        derived_published_at="2026-10-09T20:50:01Z",
        generated_at="2026-10-09T20:50:01Z",
    )
    return json.dumps(value | changes).encode()


def test_publication_is_reported_metadata_not_ingestion() -> None:
    result = providers.publication_status(payload(), datetime(2026, 10, 11, tzinfo=UTC))
    assert result["advertised_session"] == "2026-10-09"
    assert result["exchange_publication_at"] is None
    assert result["live_data_activation"] == "BLOCKED"
    assert result["price_download_attempted"] is False
    assert providers.assessment().allowed("DAILY") is False


@pytest.mark.parametrize(
    "changes",
    [
        {"stage": "complete_universe"},
        {"trading_date": "not-a-date"},
        {"generated_at": "2026-10-09T20:50:01"},
        {"generated_at": "2026-10-09T19:00:00Z"},
        {"derived_published_at": None},
        {"trading_date": "2026-12-01"},
        {"generated_at": "2026-12-01T20:50:01Z"},
    ],
)
def test_bad_or_future_metadata_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(DataContractError):
        providers.publication_status(payload(**changes), datetime(2026, 10, 11, tzinfo=UTC))


@pytest.mark.parametrize("code", [200, 302, 401, 403, 429, 503])
def test_fixed_status_request_never_fetches_prices_or_retries(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    calls: list[tuple[str, str]] = []

    class Connection:
        status = code

        def __init__(self, host: str, timeout: int) -> None:
            assert host == "api.tejhq.dev" and timeout == 10

        def request(self, method: str, path: str) -> None:
            calls.append((method, path))

        def getresponse(self) -> "Connection":
            return self

        def read(self, count: int) -> bytes:
            assert count == 10001 and code == 200
            return payload()

        def close(self) -> None:
            pass

    monkeypatch.setattr(providers, "HTTPSConnection", Connection)
    result = providers.check_publication()
    assert calls == [("GET", "/v1/status")]
    assert result["live_data_activation"] == "BLOCKED"
    assert result["price_download_attempted"] is False


def test_size_and_aware_clock_limits() -> None:
    with pytest.raises(DataContractError):
        providers.publication_status(b"x" * 10001, datetime.now(UTC))
    with pytest.raises(DataContractError):
        providers.publication_status(payload(), datetime(2026, 10, 11))
