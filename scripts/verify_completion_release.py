"""Run software tests against a new disposable TEST_ONLY PostgreSQL cluster.

No production migration, provider acquisition, cleanup or service modification.
The cluster and logs remain in a fresh private directory for inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("tests", nargs="*", default=["tests"])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to((repo / ".local-data").resolve()) or output.exists():
        raise ValueError("FRESH_PRIVATE_RELEASE_DIRECTORY_REQUIRED")
    output.mkdir(parents=True)
    pg_root = repo / ".local-data/p30-postgres"
    manifest = json.loads((pg_root / "binary-manifest.json").read_bytes())
    for entry in manifest["files"]:
        path = (pg_root / entry["file"]).resolve(strict=True)
        if not path.is_relative_to(pg_root.resolve()):
            raise ValueError("POSTGRES_BINARY_PATH_REJECTED")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != entry["sha256"]:
                raise ValueError("POSTGRES_BINARY_HASH_MISMATCH")
    bins = pg_root / "pgsql/bin"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    password = secrets.token_urlsafe(32)
    password_file = output / "TEST_ONLY_password"
    from alphalens_api.auth.permissions import restrict

    restrict(output)
    password_file.write_text(password, encoding="ascii")
    restrict(password_file)
    cluster = output / "TEST_ONLY_cluster"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started = False
    result: dict[str, object] = {
        "started_at": datetime.now(UTC).isoformat(),
        "production_cluster_used": False,
        "provider_requests": 0,
        "postgres_port": port,
        "tests": args.tests,
    }

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        kwargs.setdefault("stdout", subprocess.DEVNULL)
        kwargs.setdefault("stderr", subprocess.STDOUT)
        return subprocess.run(command, cwd=repo, creationflags=flags, **kwargs)  # type: ignore[call-overload,no-any-return]

    try:
        with (output / "postgres-init.log").open("xb") as log:
            run(
                [
                    str(bins / "initdb.exe"),
                    "-D",
                    str(cluster),
                    "-U",
                    "test_only",
                    "--pwfile",
                    str(password_file),
                    "--auth=scram-sha-256",
                    "--encoding=UTF8",
                    "--locale=C",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        password_file.unlink()
        run(
            [
                str(bins / "pg_ctl.exe"),
                "-D",
                str(cluster),
                "-l",
                str(output / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -c shared_buffers=64MB -c max_connections=30",
                "-w",
                "start",
            ],
            check=True,
        )
        started = True
        import psycopg

        with psycopg.connect(
            host="127.0.0.1",
            port=port,
            user="test_only",
            password=password,
            dbname="postgres",
            autocommit=True,
        ) as connection:
            connection.execute("CREATE DATABASE test_only")
        env = os.environ.copy()
        env.update(
            ALPHALENS_TEST_DATABASE_URL=f"postgresql://test_only:{password}@127.0.0.1:{port}/test_only",
            ALPHALENS_TEST_TEMP_ROOT="D:/al-tests",
            PYTHONUTF8="1",
            TEMP="D:/AlphaLensStorage/Temp/Development",
            TMP="D:/AlphaLensStorage/Temp/Development",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
        )
        with (output / "pytest.log").open("xb") as log:
            completed = run(
                [sys.executable, "-m", "pytest", "-W", "error", "-ra", "--tb=short", *args.tests],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        result["test_exit_code"] = completed.returncode
        return completed.returncode
    finally:
        if password_file.exists():
            password_file.unlink()
        if started:
            stopped = run(
                [str(bins / "pg_ctl.exe"), "-D", str(cluster), "-m", "fast", "-w", "stop"]
            )
            result["postgres_stop_exit_code"] = stopped.returncode
        result["completed_at"] = datetime.now(UTC).isoformat()
        (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))


if __name__ == "__main__":
    raise SystemExit(main())
