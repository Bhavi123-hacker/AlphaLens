"""Disposable CI PostgreSQL17 role/schema verification; never real financial evidence."""

import os
import secrets
from urllib.parse import unquote, urlsplit

import pytest
from psycopg import connect, sql
from psycopg.errors import InsufficientPrivilege, ReadOnlySqlTransaction
from scripts.build_p28_test_inputs import CredentialFixture

from alphalens_api.local import postgres

pytestmark = pytest.mark.database


def test_readonly_bootstrap_new_database_and_preserved_existing_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uri = os.environ.get("ALPHALENS_TEST_DATABASE_URL")
    if not uri:
        pytest.skip("No isolated PostgreSQL17 test connection available")
    parsed = urlsplit(uri)
    if parsed.hostname not in {"localhost", "127.0.0.1"} or not (
        parsed.path.lstrip("/").startswith("test_only")
    ):
        pytest.skip("Explicit disposable TEST_ONLY localhost database required")
    fixture = CredentialFixture()
    monkeypatch.setattr(postgres, "credential_module", lambda: fixture)
    created = False
    try:
        result = postgres.bootstrap(
            parsed.port or 5432, unquote(parsed.username or ""), unquote(parsed.password or "")
        )
        created = True
        assert result["financial_records_created"] == 0
        with connect(postgres.reader_url()) as reader:
            assert reader.execute("SHOW transaction_read_only").fetchone() == ("on",)
            assert reader.execute("SELECT COUNT(*) FROM portfolio.accounts").fetchone() == (0,)
            assert reader.execute(
                "SELECT version FROM alphalens_local.setup_version"
            ).fetchone() == ("p29.local-postgres.v1",)
            with pytest.raises((InsufficientPrivilege, ReadOnlySqlTransaction)):
                reader.execute("CREATE TABLE portfolio.TEST_ONLY_forbidden_write(x INT)")
        with pytest.raises(ValueError, match="PRESERVED"):
            postgres.bootstrap(parsed.port or 5432, "TEST_ONLY", secrets.token_urlsafe(32))
    finally:
        if created:
            # Only the new empty database/role in this guarded disposable CI instance.
            with connect(uri, autocommit=True) as admin:
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(postgres.DATABASE)))
                admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(postgres.READER)))
