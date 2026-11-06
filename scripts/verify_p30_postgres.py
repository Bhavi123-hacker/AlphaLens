"""Owned local PG17 read-only checks and isolated empty financial backup restoration."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from psycopg import connect, sql
from psycopg.errors import InsufficientPrivilege, ReadOnlySqlTransaction
from scripts.setup_p30_postgres import ADMIN_TARGET, ROOT

from alphalens_api.credentials import credential_module
from alphalens_api.local.postgres import DATABASE, READER, reader_url

TABLES = ("accounts", "transactions", "paper_accounts", "paper_events")
RESTORE = "alphalens_p30_restore_test_only"


def main() -> None:
    module = credential_module()
    blob = module.CredRead(ADMIN_TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
    password = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
    arguments = dict(
        host="127.0.0.1",
        port=15430,
        user="alphalens_p30_admin",
        password=password,
        connect_timeout=3,
    )
    with connect(**arguments, dbname="postgres", autocommit=True) as admin:
        actual = admin.execute("SHOW data_directory").fetchone()[0]
        if (
            Path(actual).resolve() != (ROOT / "cluster").resolve()
            or admin.info.server_version // 10000 != 17
        ):
            raise ValueError("OWNED_POSTGRES17_REQUIRED")
        if admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (RESTORE,)).fetchone():
            raise ValueError("EXISTING_RESTORE_DATABASE_PRESERVED")
        with connect(reader_url(), connect_timeout=3) as reader:
            if reader.execute("SHOW transaction_read_only").fetchone() != ("on",):
                raise ValueError("READ_ONLY_TRANSACTION_REQUIRED")
            counts = {
                table: reader.execute(
                    sql.SQL("SELECT COUNT(*) FROM portfolio.{}").format(sql.Identifier(table))
                ).fetchone()[0]
                for table in TABLES
            }
            if any(counts.values()):
                raise ValueError("EMPTY_NEW_DATABASE_EXPECTATION_CHANGED_PRESERVE_RECORDS")
            if reader.execute("SELECT version FROM alphalens_local.setup_version").fetchone() != (
                "p29.local-postgres.v1",
            ):
                raise ValueError("MIGRATION_VERSION_REJECTED")
            for table in TABLES:
                if reader.execute(
                    "SELECT has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE')",
                    (READER, "portfolio." + table),
                ).fetchone()[0]:
                    raise ValueError("READER_WRITE_PRIVILEGE_REJECTED")
            try:
                reader.execute("CREATE TABLE alphalens_local.p30_forbidden_write(x INT)")
            except (InsufficientPrivilege, ReadOnlySqlTransaction):
                reader.rollback()
            else:
                reader.rollback()
                raise ValueError("READER_WRITE_GUARD_FAILED")
        backup = ROOT / "p30-empty-financial-backup.dump"
        if backup.exists():
            raise ValueError("EXISTING_BACKUP_PRESERVED")
        private_password = ROOT / "backup-passfile.private"
        if private_password.exists():
            raise ValueError("EXISTING_PRIVATE_PASSFILE_PRESERVED")
        private_password.write_text(
            f"127.0.0.1:15430:*:alphalens_p30_admin:{password}\n", encoding="utf-8"
        )
        environment = {**os.environ, "PGPASSFILE": str(private_password), "PGCONNECT_TIMEOUT": "3"}
        try:
            common = [
                "--host=127.0.0.1",
                "--port=15430",
                "--username=alphalens_p30_admin",
                "--no-password",
            ]
            with (ROOT / "backup-command.private").open("wb") as output:
                result = subprocess.run(
                    [
                        str(ROOT / "pgsql/bin/pg_dump.exe"),
                        *common,
                        "--format=custom",
                        "--no-owner",
                        "--no-acl",
                        "--file=" + str(backup),
                        DATABASE,
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    timeout=60,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode:
                    raise ValueError("OWNED_DATABASE_BACKUP_FAILED")
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(RESTORE)))
                result = subprocess.run(
                    [
                        str(ROOT / "pgsql/bin/pg_restore.exe"),
                        *common,
                        "--no-owner",
                        "--no-acl",
                        "--exit-on-error",
                        "--dbname=" + RESTORE,
                        str(backup),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    timeout=60,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode:
                    raise ValueError("ISOLATED_RESTORATION_FAILED")
        finally:
            private_password.unlink(missing_ok=True)
        with connect(**arguments, dbname=RESTORE) as restored:
            restored_counts = {
                table: restored.execute(
                    sql.SQL("SELECT COUNT(*) FROM portfolio.{}").format(sql.Identifier(table))
                ).fetchone()[0]
                for table in TABLES
            }
            if restored_counts != counts:
                raise ValueError("ISOLATED_RESTORATION_RECORD_MISMATCH")
            triggers = restored.execute(
                "SELECT COUNT(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN "
                "('portfolio_account_immutable','portfolio_transaction_immutable',"
                "'paper_account_immutable','paper_event_immutable')"
            ).fetchone()[0]
            if triggers != 4:
                raise ValueError("IMMUTABLE_FINANCIAL_TRIGGERS_MISSING")
    receipt = {
        "state": "PASSED",
        "server_version": "17.11",
        "read_only_role": True,
        "write_attempt_rejected": True,
        "migration_verified": True,
        "financial_record_counts": counts,
        "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "isolated_restoration": "PASSED",
        "immutable_triggers": triggers,
        "original_records_changed": False,
        "financial_fixtures_created": False,
    }
    (ROOT / "verification-receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps({"state": "POSTGRES_VERIFICATION_BLOCKED", "category": type(exc).__name__})
        )
        raise SystemExit(1) from None
