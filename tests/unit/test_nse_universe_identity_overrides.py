"""TEST_ONLY saved common identities; no provider requests or real market prices."""

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest
from workers.providers import reference, universe, watchlist
from workers.providers import upstox_terminal as terminal
from workers.providers.upstox import Reply

from alphalens_api import providers
from alphalens_api.core.domain_errors import APIError
from alphalens_data.errors import DataContractError

AT = datetime(2026, 10, 17, 11, tzinfo=UTC)


def reply(*, at: datetime = AT, series: str = "BE") -> Reply:
    body = gzip.compress(
        json.dumps(
            [
                {
                    "segment": "NSE_EQ",
                    "exchange": "NSE",
                    "instrument_type": series,
                    "instrument_key": "NSE_EQ|INE002A01018",
                    "isin": "INE002A01018",
                    "trading_symbol": "TEST_ONLY",
                    "name": "TEST_ONLY company",
                    "security_type": "NORMAL",
                }
            ]
        ).encode()
    )
    return Reply(200, body, at, "ACCEPTED")


class Clock(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> Self:
        value = cls.fromisoformat(AT.isoformat())
        return value if tz is None else value.astimezone(tz)


class Client:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.calls = 0

    def get(self, operation: str, **_kwargs: Any) -> Reply:
        assert operation != "instruments", "Saved master must prevent a page-load master GET"
        self.calls += 1
        return Reply(503, b"", AT, "PROVIDER_OUTAGE")


def test_non_eq_requires_positive_common_master_and_fresh_override(tmp_path: Path) -> None:
    identities = universe.parse(reply()).eligible
    assert terminal.selected(identities, identities[0].provider_key) == identities[0]
    arbitrary = identities[0].model_copy(update={"identity_evidence": "TEST_ONLY_UNVERIFIED"})
    with pytest.raises(DataContractError, match="CURRENT_NSE_EQUITY_REQUIRED"):
        terminal.selected((arbitrary,), arbitrary.provider_key)
    for values, at, reason in [
        ((arbitrary,), AT, "VERIFIED_COMMON"),
        (identities, AT - timedelta(seconds=1), "FUTURE"),
        (identities, AT + timedelta(days=1, seconds=1), "STALE"),
        (identities + identities, AT, "VERIFIED_COMMON"),
    ]:
        with pytest.raises(DataContractError, match=reason):
            terminal.verified_override(values, at)
    result = terminal.search(tmp_path, "TEST_ONLY", at=AT, verified_instruments=identities)
    assert result["candidate_count"] == result["matched_count"] == 1
    assert result["instruments"][0]["instrument_type"] == "BE"
    assert result["market_prices_requested"] is False
    assert result["scope"] == "VERIFIED_CURRENT_ORDINARY_COMMON_EQUITIES_NOT_HISTORICAL_MEMBERSHIP"


def test_snapshot_and_watchlist_use_exact_saved_common_identity_without_master_get(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = universe.parse(reply()).eligible
    key = identities[0].provider_key
    monkeypatch.setattr(terminal, "UpstoxClient", Client)
    monkeypatch.setattr(watchlist, "UpstoxClient", Client)
    monkeypatch.setattr(watchlist, "datetime", Clock)
    snapshot = terminal.snapshot(tmp_path, keys=(key,), now=AT, verified_instruments=identities)
    assert snapshot["items"][0]["identity"]["instrument_type"] == "BE"
    assert snapshot["items"][0]["quote"]["state"] == "PROVIDER_OUTAGE"
    observed = watchlist.load(tmp_path, (key,), verified_instruments=identities)
    assert observed["items"][0]["identity"]["isin"] == identities[0].isin
    assert observed["valid_quote_count"] == 0


def test_non_eq_company_reference_uses_verified_identity_and_keeps_failed_source_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = universe.parse(reply()).eligible
    monkeypatch.setattr(reference, "datetime", Clock)
    monkeypatch.setattr(reference, "UpstoxClient", Client)
    data = reference.load(tmp_path, identities[0].provider_key, verified_instruments=identities)
    assert data["isin"] == identities[0].isin
    assert data["api_calls_this_request"] == 3
    assert data["retained"] is False
    assert all(row["state"] == "PROVIDER_OUTAGE" for row in data["observations"])
    renamed = identities[0].model_copy(update={"symbol": "TEST_ONLY_RENAMED"})
    refreshed = reference.load(tmp_path, renamed.provider_key, verified_instruments=(renamed,))
    assert refreshed["symbol"] == "TEST_ONLY_RENAMED"
    assert refreshed["api_calls_this_request"] == 3


def service(root: Path | None) -> Any:
    return SimpleNamespace(
        reader=SimpleNamespace(settings=SimpleNamespace(experimental_nse_v2_root=root))
    )


def test_api_derives_private_universe_without_new_setting_and_rejects_stale_or_future(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers, "datetime", Clock)
    assert providers.verified_instruments(service(None)) is None
    assert providers.verified_instruments(service(tmp_path / "v2")) is None
    root = tmp_path / "nse-universe"
    universe.save(root, reply())
    loaded = providers.verified_instruments(service(tmp_path / "v2"))
    assert loaded is not None and len(loaded) == 1
    universe.save(root, reply(at=AT + timedelta(seconds=1)))
    with pytest.raises(APIError) as future:
        providers.verified_instruments(service(tmp_path / "v2"))
    assert future.value.code == "UNIVERSE_FUTURE_OBSERVATION_REJECTED"
    other = tmp_path / "older"
    universe.save(other / "nse-universe", reply(at=AT - timedelta(days=2)))
    with pytest.raises(APIError) as stale:
        providers.verified_instruments(service(other / "v2"))
    assert stale.value.code == "UNIVERSE_STALE_REFRESH_REQUIRED"


def test_api_rejects_checksum_tampering_without_provider_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers, "datetime", Clock)
    root = tmp_path / "nse-universe"
    snap = universe.save(root, reply())
    raw = root / ("master-" + snap.summary["raw_sha256"] + ".json.gz")
    raw.write_bytes(b"TEST_ONLY_CORRUPTION")
    with pytest.raises(APIError) as rejected:
        providers.verified_instruments(service(tmp_path / "v2"))
    assert rejected.value.code == "UNIVERSE_SNAPSHOT_UNAVAILABLE"
