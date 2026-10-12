"""Explicit local PostgreSQL17 bootstrap; no downloads, service changes or financial fixtures."""

import argparse
import getpass
import json
import secrets
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from psycopg import connect, sql

from alphalens_api.credentials import credential_module

TARGET = "AlphaLens/PostgreSQL/ResearchReadOnly"
DATABASE = "alphalens_research_local"
READER = "alphalens_research_reader"


def reader_url() -> str:
    try:
        module = credential_module()
        blob = module.CredRead(TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
        value = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        parsed = urlsplit(value)
        if (
            parsed.scheme != "postgresql"
            or parsed.hostname != "127.0.0.1"
            or parsed.username != READER
            or parsed.path != "/" + DATABASE
            or not parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
        return value
    except Exception:
        raise ValueError("PRIVATE_READ_ONLY_DATABASE_CREDENTIAL_UNAVAILABLE") from None


def absent_target(module: Any) -> None:
    try:
        module.CredRead(TARGET, module.CRED_TYPE_GENERIC)
    except Exception as exc:
        if getattr(exc, "winerror", None) == 1168:
            return
        raise ValueError("DATABASE_CREDENTIAL_STORE_UNAVAILABLE") from None
    raise ValueError("EXISTING_DATABASE_CREDENTIAL_PRESERVED")


def bootstrap(port: int, administrator: str, password: str) -> dict[str, Any]:
    """Only an explicitly NEW dedicated database and role. Existing objects are preserved."""
    module = credential_module()
    absent_target(module)
    if not 1024 <= port <= 65535 or not administrator or not password:
        raise ValueError("LOCAL_POSTGRES_PARAMETERS_INVALID")
    with connect(
        host="127.0.0.1",
        port=port,
        dbname="postgres",
        user=administrator,
        password=password,
        connect_timeout=3,
        autocommit=True,
    ) as admin:
        if admin.info.server_version // 10000 != 17:
            raise ValueError("POSTGRESQL17_REQUIRED")
        if (
            admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DATABASE,)).fetchone()
            or admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (READER,)).fetchone()
        ):
            raise ValueError("EXISTING_DATABASE_OR_ROLE_PRESERVED")
        # Do not expose new verifier or input credential through server statement/error logging.
        preload = admin.execute("SHOW shared_preload_libraries").fetchone()
        if preload is None or "pgaudit" in str(preload[0]):
            raise ValueError("SERVER_AUDIT_REVIEW_REQUIRED_BEFORE_CREDENTIAL_DDL")
        admin.execute("SET log_statement='none'")
        admin.execute("SET log_min_error_statement='panic'")
        readonly = secrets.token_urlsafe(48)
        verifier = admin.pgconn.encrypt_password(
            readonly.encode(), READER.encode(), b"scram-sha-256"
        ).decode()
        admin.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                "CONNECTION LIMIT 8 PASSWORD {}"
            ).format(sql.Identifier(READER), sql.Literal(verifier))
        )
        admin.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only=on").format(
                sql.Identifier(READER)
            )
        )
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE)))
        admin.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(DATABASE))
        )
        admin.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(DATABASE), sql.Identifier(READER)
            )
        )
    with connect(
        host="127.0.0.1",
        port=port,
        dbname=DATABASE,
        user=administrator,
        password=password,
        connect_timeout=3,
    ) as connection:
        root = Path(__file__).resolve().parents[5]
        for file in (
            "db/migrations/003_p15_portfolio.sql",
            "db/migrations/004_p16_paper.sql",
            "db/local/p29_schema.sql",
        ):
            connection.execute((root / file).read_text(encoding="utf-8"))
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA portfolio,alphalens_local TO {}").format(
                sql.Identifier(READER)
            )
        )
        connection.execute(
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA portfolio,alphalens_local TO {}").format(
                sql.Identifier(READER)
            )
        )
    uri = f"postgresql://{READER}:{quote(readonly, safe='')}@127.0.0.1:{port}/{DATABASE}"
    module.CredWrite(
        {
            "Type": module.CRED_TYPE_GENERIC,
            "TargetName": TARGET,
            "CredentialBlob": uri,
            "Persist": module.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": "AlphaLens local PostgreSQL read-only role; no financial evidence created",
        },
        0,
    )
    if reader_url() != uri:
        raise ValueError("DATABASE_CREDENTIAL_READBACK_FAILED")
    return {
        "state": "NEW_LOCAL_DATABASE_INITIALIZED",
        "version": 17,
        "credential_target": TARGET,
        "password_printed": False,
        "financial_records_created": 0,
        "access": "READ_ONLY_ROLE_AND_READ_ONLY_TRANSACTIONS",
    }


def diagnose(port: int, bin_root: Path | None) -> dict[str, Any]:
    with socket.socket() as probe:
        probe.settimeout(1)
        listening = probe.connect_ex(("127.0.0.1", port)) == 0
    tools = bin_root or Path("C:/Program Files/PostgreSQL/17/bin")
    return {
        "loopback_listener": listening,
        "port": port,
        "native17_tools_present": all(
            (tools / (name + ".exe")).is_file()
            for name in ("psql", "pg_ctl", "pg_dump", "pg_restore")
        ),
        "server_version": "NOT_VERIFIED_WITHOUT_AUTHENTICATED_CONNECTION",
        "automatic_installation": False,
        "financial_records_created": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("diagnose", "bootstrap", "check"))
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--bin", type=Path)
    parser.add_argument("--administrator", default="postgres")
    args = parser.parse_args()
    try:
        if args.command == "diagnose":
            result = diagnose(args.port, args.bin)
        elif args.command == "check":
            with connect(
                reader_url(),
                connect_timeout=3,
                options="-c default_transaction_read_only=on -c statement_timeout=3000",
            ) as connection:
                row = connection.execute(
                    "SELECT current_setting('server_version'),"
                    "current_setting('transaction_read_only'),"
                    "(SELECT COUNT(*) FROM portfolio.accounts)"
                ).fetchone()
                if row is None:
                    raise ValueError("POSTGRES_READINESS_UNAVAILABLE")
                result = {
                    "server_version": row[0],
                    "read_only": row[1],
                    "recorded_accounts": row[2],
                }
        else:
            if not sys.stdin.isatty():
                raise ValueError("LOCAL_INTERACTIVE_ADMIN_PROMPT_REQUIRED")
            result = bootstrap(
                args.port,
                args.administrator,
                getpass.getpass("Existing local PostgreSQL administrator password (hidden): "),
            )
        print(json.dumps(result))
        return 0
    except Exception:
        print(
            json.dumps(
                {
                    "state": "POSTGRES_OPERATION_REJECTED",
                    "guidance": (
                        "Check loopback PostgreSQL17, private credentials and new "
                        "database/role requirements. Existing data is preserved."
                    ),
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
