"""Disposable real PostgreSQL verification; secrets never printed or passed as arguments.

Uses a dedicated compose project and loopback port 55432. Removes only its own
containers/network/volume. Does not touch the normal development database.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "verification-local/p5-compose.yaml"
CONFIG = """services:
  postgres:
    image: postgres:17-bookworm
    environment:
      POSTGRES_USER: test_only
      POSTGRES_DB: test_only
      POSTGRES_PASSWORD: ${ALPHALENS_P5_TEST_PASSWORD:?required}
    ports: ["127.0.0.1:55432:5432"]
    volumes: ["p5_test_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_only -d test_only"]
      interval: 2s
      timeout: 3s
      retries: 20
volumes:
  p5_test_data:
"""


def main() -> int:
    COMPOSE.parent.mkdir(exist_ok=True)
    COMPOSE.write_text(CONFIG, encoding="utf-8")
    environment = os.environ.copy()
    environment["ALPHALENS_P5_TEST_PASSWORD"] = secrets.token_hex(24)
    environment["ALPHALENS_TEST_DATABASE_URL"] = (
        "postgresql://test_only:"
        + environment["ALPHALENS_P5_TEST_PASSWORD"]
        + "@127.0.0.1:55432/test_only"
    )
    command = ["docker", "compose", "-f", str(COMPOSE), "-p", "alphalens-p5-verification"]
    try:
        subprocess.run(
            command + ["up", "-d", "--wait", "--wait-timeout", "90"],
            env=environment,
            cwd=ROOT,
            check=True,
            timeout=300,
        )
        tests = subprocess.run(
            [sys.executable, "-m", "pytest", "-W", "error", "-ra", "--tb=short"],
            env=environment,
            cwd=ROOT,
            check=False,
            timeout=2400,
        )
        if tests.returncode:
            return tests.returncode
        smoke = subprocess.run(
            [
                sys.executable,
                "-m",
                "alphalens_data.ingestion.cli",
                "tests/fixtures/p2/TEST_ONLY.csv",
                "--spec",
                "tests/fixtures/p2/TEST_ONLY.spec.json",
                "--data-root",
                "data/p2-postgres-smoke/" + secrets.token_hex(4),
                "--postgres",
            ],
            env=environment,
            cwd=ROOT,
            check=False,
            timeout=60,
        ).returncode
        if smoke:
            return smoke
        with psycopg.connect(
            environment["ALPHALENS_TEST_DATABASE_URL"], connect_timeout=3
        ) as connection:
            for migration in sorted((ROOT / "db/migrations").glob("*.sql")):
                connection.execute(migration.read_text())
        environment["ALPHALENS_DATABASE_URL"] = environment["ALPHALENS_TEST_DATABASE_URL"]
        local_root = Path("data/p5-postgres-smoke") / secrets.token_hex(4)
        prepared = subprocess.run(
            [sys.executable, "-m", "scripts.build_p5_test_fixture", "--data-root", str(local_root)],
            env=environment,
            cwd=ROOT,
            check=False,
            timeout=60,
        )
        if prepared.returncode:
            return prepared.returncode
        build = [
            sys.executable,
            "-m",
            "alphalens_data.canonical.cli",
            str(local_root / "canonical-input.json"),
            "--knowledge-cutoff",
            "2024-01-20T12:00:00Z",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-20",
            "--output",
            str(local_root / "snapshots"),
            "--postgres",
        ]
        for _ in range(2):
            result = subprocess.run(build, env=environment, cwd=ROOT, check=False, timeout=60)
            if result.returncode:
                return result.returncode
        return 0
    finally:
        subprocess.run(
            command + ["down", "--volumes"], env=environment, cwd=ROOT, check=True, timeout=60
        )


if __name__ == "__main__":
    raise SystemExit(main())
