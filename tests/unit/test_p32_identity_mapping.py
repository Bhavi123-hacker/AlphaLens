"""TEST_ONLY latest dated aliases; no name inference or ambiguous mapping."""

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from alphalens_api.providers import archive_identities


def test_batched_latest_identity_mapping_rejects_stale_and_ambiguous_aliases(
    tmp_path: Path,
) -> None:
    path = tmp_path / "TEST_ONLY_mapping.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            "CREATE TABLE securities(security_id TEXT,last_observed TEXT);"
            "CREATE TABLE aliases(security_id TEXT,isin TEXT,symbol TEXT,last_observed TEXT);"
        )
        connection.executemany(
            "INSERT INTO securities VALUES(?,?)",
            [(key, "2024-01-03") for key in ("A", "B", "C", "D")],
        )
        connection.executemany(
            "INSERT INTO aliases VALUES(?,?,?,?)",
            [
                ("A", "TEST_ONLY_ISIN_A", "TEST_ONLY_ALPHA", "2024-01-03"),
                ("A", "TEST_ONLY_OLD", "TEST_ONLY_ALPHA", "2024-01-02"),
                ("B", "TEST_ONLY_ISIN_B", "TEST_ONLY_BETA", "2024-01-03"),
                ("B", "TEST_ONLY_OTHER", "TEST_ONLY_BETA", "2024-01-03"),
                ("C", "TEST_ONLY_DUP", "TEST_ONLY_DUP", "2024-01-03"),
                ("D", "TEST_ONLY_DUP", "TEST_ONLY_DUP", "2024-01-03"),
            ],
        )

    def opened() -> sqlite3.Connection:
        result = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        result.row_factory = sqlite3.Row
        return result

    service: Any = SimpleNamespace(catalog=SimpleNamespace(connection=opened))
    identities = [
        {"isin": "TEST_ONLY_ISIN_A", "symbol": "TEST_ONLY_ALPHA"},
        {"isin": "TEST_ONLY_OLD", "symbol": "TEST_ONLY_ALPHA"},
        {"isin": "TEST_ONLY_ISIN_A", "symbol": "TEST_ONLY_WRONG"},
        {"isin": "TEST_ONLY_ISIN_B", "symbol": "TEST_ONLY_BETA"},
        {"isin": "TEST_ONLY_DUP", "symbol": "TEST_ONLY_DUP"},
    ]
    assert archive_identities(service, identities) == ["A", None, None, None, None]
    with pytest.raises(ValueError, match="PAGE_BOUND"):
        archive_identities(service, identities * 21)
