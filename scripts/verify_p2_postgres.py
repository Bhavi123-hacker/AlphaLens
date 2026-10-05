"""Disposable real PostgreSQL verification; secrets never printed or passed as arguments.

Uses a dedicated compose project and loopback port 55432. Removes only its own
containers/network/volume. Does not touch the normal development database.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "verification-local/p2-compose.yaml"
CONFIG = """services:
  postgres:
    image: postgres:17-bookworm
    environment:
      POSTGRES_USER: test_only
      POSTGRES_DB: test_only
      POSTGRES_PASSWORD: ${ALPHALENS_P2_TEST_PASSWORD:?required}
    ports: ["127.0.0.1:55432:5432"]
    volumes: ["p2_test_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_only -d test_only"]
      interval: 2s
      timeout: 3s
      retries: 20
volumes:
  p2_test_data:
"""


def main() -> int:
    COMPOSE.parent.mkdir(exist_ok=True)
    COMPOSE.write_text(CONFIG, encoding="utf-8")
    environment = os.environ.copy()
    environment["ALPHALENS_P2_TEST_PASSWORD"] = secrets.token_hex(24)
    environment["ALPHALENS_TEST_DATABASE_URL"] = (
        "postgresql://test_only:"
        + environment["ALPHALENS_P2_TEST_PASSWORD"]
        + "@127.0.0.1:55432/test_only"
    )
    command = ["docker", "compose", "-f", str(COMPOSE), "-p", "alphalens-p2-verification"]
    try:
        subprocess.run(
            command + ["up", "-d", "--wait", "--wait-timeout", "90"],
            env=environment,
            cwd=ROOT,
            check=True,
            timeout=120,
        )
        tests = subprocess.run(
            [sys.executable, "-m", "pytest", "-W", "error", "-ra", "--tb=short"],
            env=environment,
            cwd=ROOT,
            check=False,
            timeout=120,
        )
        if tests.returncode:
            return tests.returncode
        return subprocess.run(
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
    finally:
        subprocess.run(
            command + ["down", "--volumes"], env=environment, cwd=ROOT, check=True, timeout=60
        )


if __name__ == "__main__":
    raise SystemExit(main())
