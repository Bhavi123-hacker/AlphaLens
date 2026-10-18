"""TEST_ONLY account budgets; no credentials, prices or outbound requests."""

import json
from pathlib import Path

import pytest
from scripts.link_upstox_budget import link as migrate
from workers.providers.store import ProviderStore

from alphalens_api.auth.permissions import restrict
from alphalens_data.errors import DataContractError


def link(source: ProviderStore, target: Path) -> None:
    path = source.root / "upstox-shared-quota.json"
    path.write_text(json.dumps({"version": "provider.shared_quota.v1", "root": str(target)}))
    if __import__("os").name != "nt":
        path.chmod(0o600)
    restrict(source.root)


def test_independent_clients_share_reservations_retries_and_quota_exhaustion(
    tmp_path: Path,
) -> None:
    first, second = (
        ProviderStore(tmp_path / "TEST_ONLY_daily"),
        ProviderStore(tmp_path / "TEST_ONLY_view"),
    )
    first.initialize()
    second.initialize()
    link(second, first.root)
    at = 100000.0
    for index in range(50):
        client = first if index % 2 else second
        request = f"{index:064x}"
        assert client.reserve("upstox", request, 1, at)
        client.finish("upstox", request, 1, at, 200)
    with pytest.raises(DataContractError, match="QUOTA_EXHAUSTED"):
        second.reserve("upstox", "a" * 64, 1, at)
    assert second.status(at)["local_rolling_24h_attempts"]["upstox"] == 50
    assert second.status(at)["upstox_budget_shared"] is True
    assert second.reserve("upstox", "b" * 64, 1, at + 2)
    second.finish("upstox", "b" * 64, 1, at + 2, 429, 10)
    with pytest.raises(DataContractError, match="BACKOFF_GUARD"):
        first.reserve("upstox", "c" * 64, 1, at + 3)
    assert first.reserve("upstox", "b" * 64, 2, at + 12)


def test_chained_self_and_malformed_links_never_bypass_budget(tmp_path: Path) -> None:
    first, second = ProviderStore(tmp_path / "TEST_ONLY_A"), ProviderStore(tmp_path / "TEST_ONLY_B")
    first.initialize()
    second.initialize()
    link(first, first.root)
    with pytest.raises(DataContractError):
        first.reserve("upstox", "a" * 64, 1, 100000)
    link(first, second.root)
    link(second, first.root)
    with pytest.raises(DataContractError):
        first.reserve("upstox", "a" * 64, 1, 100000)


def test_idle_migration_appends_history_without_rewriting_source(tmp_path: Path) -> None:
    source, target = (
        ProviderStore(tmp_path / "TEST_ONLY_source"),
        ProviderStore(tmp_path / "TEST_ONLY_target"),
    )
    source.initialize()
    target.initialize()
    assert source.reserve("upstox", "a" * 64, 1, 100000)
    with pytest.raises(ValueError, match="MUST_BE_IDLE"):
        migrate(source.root, target.root)
    assert not (source.root / "upstox-shared-quota.json").exists()
    source.finish("upstox", "a" * 64, 1, 100000, 200)
    with source.connection(readonly=True) as connection:
        before = connection.execute("SELECT * FROM attempts").fetchall()
    result = migrate(source.root, target.root)
    assert result["copied_attempts"] == 1
    assert result["provider_GETs"] == 0
    with source.connection(readonly=True) as connection:
        assert connection.execute("SELECT * FROM attempts").fetchall() == before
    assert source.status(100001)["upstox_budget_shared"] is True
    with pytest.raises(ValueError, match="EXISTING_SHARED"):
        migrate(source.root, target.root)
