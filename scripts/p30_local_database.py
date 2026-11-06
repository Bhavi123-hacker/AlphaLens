"""Start/stop only the checksum-reviewed P30-owned PostgreSQL cluster, never a service."""

import argparse
import hashlib
import json
import socket
from pathlib import Path

from psycopg import connect
from scripts.setup_p30_postgres import ADMIN_TARGET, ROOT, run

from alphalens_api.auth.permissions import verify
from alphalens_api.credentials import credential_module


def owned_identity() -> None:
    module = credential_module()
    blob = module.CredRead(ADMIN_TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
    password = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
    with connect(
        host="127.0.0.1",
        port=15430,
        user="alphalens_p30_admin",
        password=password,
        dbname="postgres",
        connect_timeout=3,
    ) as connection:
        location = connection.execute("SHOW data_directory").fetchone()[0]
        if (
            Path(location).resolve() != (ROOT / "cluster").resolve()
            or connection.info.server_version // 10000 != 17
        ):
            raise ValueError("OWNED_CLUSTER_IDENTITY_REQUIRED")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "stop", "status"))
    args = parser.parse_args()
    verify(ROOT)
    manifest = json.loads((ROOT / "binary-manifest.json").read_bytes())
    pinned = {r["file"]: r["sha256"] for r in manifest["files"]}
    for name in ("pgsql/bin/postgres.exe", "pgsql/bin/pg_ctl.exe"):
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != pinned[name]:
            raise ValueError("REVIEWED_DATABASE_BINARY_CHANGED")
    with socket.socket() as probe:
        probe.settimeout(1)
        listening = probe.connect_ex(("127.0.0.1", 15430)) == 0
    if listening:
        owned_identity()
    if args.command == "start" and not listening:
        run(
            [
                str(ROOT / "pgsql/bin/pg_ctl.exe"),
                "start",
                "-w",
                "-D",
                str(ROOT / "cluster"),
                "-l",
                str(ROOT / "postgres.log"),
            ]
        )
        owned_identity()
        listening = True
    elif args.command == "stop" and listening:
        run(
            [
                str(ROOT / "pgsql/bin/pg_ctl.exe"),
                "stop",
                "-m",
                "smart",
                "-w",
                "-D",
                str(ROOT / "cluster"),
            ]
        )
        listening = False
    print(
        json.dumps(
            {
                "owned_postgres_running": listening,
                "port": 15430,
                "scope": "P30_OWNED_CLUSTER_ONLY",
                "windows_service_changed": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps({"state": "OWNED_DATABASE_ACTION_REJECTED", "category": type(exc).__name__})
        )
        raise SystemExit(1) from None
