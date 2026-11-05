"""AlphaLens One-Click Windows Startup Controller.

Idempotent, safe, headless/interactive startup controller:
1. Validates Python environment, version, and dependencies.
2. Performs database and repository integrity checks via alphalens_api.local.cli.
3. Checks if the API is already responding on port 8041.
4. If already running, reuses the process and opens the browser.
5. If stopped, spawns the local API daemon with redirected logging to D-drive.
6. Polls the health endpoint until ready, then launches the browser.
7. Never prints or logs secrets or credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Primary configurations in priority order
CONFIG_CANDIDATES = [
    Path("D:/al-research/p28-worktree/.local-data/private-v1-release/config-saved-refresh-20261102.json"),
    REPO_ROOT.parent / ".local-data" / "private-v1-release" / "config-saved-refresh-20261102.json",
    REPO_ROOT / ".local-data" / "private-v1-release" / "config-saved-refresh-20261102.json",
    Path("D:/al-research/p28-worktree/.local-data/private-v1-release/config.json"),
]

DEFAULT_LOG_PATH = Path("D:/al-research/p28-worktree/.local-data/alphalens_startup.log")


def resolve_config(explicit_path: Path | None = None) -> Path:
    """Locate the valid sealed AlphaLens local configuration file."""
    if explicit_path and explicit_path.is_file():
        return explicit_path
    for candidate in CONFIG_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not find a valid AlphaLens local configuration JSON file.")


def check_python_environment() -> None:
    """Ensure Python >= 3.11 and all required server packages exist."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        raise RuntimeError(f"Python >= 3.11 required; currently running {sys.version}")

    required_modules = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("joblib", "Joblib"),
        ("sklearn", "Scikit-Learn"),
        ("numpy", "NumPy"),
    ]
    missing = []
    for mod_name, label in required_modules:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(label)
    if missing:
        raise RuntimeError(f"Missing required packages in current virtualenv: {', '.join(missing)}")


def check_database_and_integrity(cfg_path: Path) -> dict[str, Any]:
    """Execute existing safe local integrity check without writing data."""
    from alphalens_api.local.cli import check, configured

    settings = configured(cfg_path)
    res = check(settings)
    if res.get("local_setup") != "PASSED":
        raise RuntimeError(f"Local environment check reported BLOCKED setup: {res}")
    return res


def is_api_responding(port: int = 8041, timeout_sec: float = 1.5) -> bool:
    """Check if the AlphaLens health endpoint responds HTTP 200."""
    url = f"http://127.0.0.1:{port}/api/v1/health/live"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaLens-Startup-Probe"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def start_api_daemon(cfg_path: Path, log_file_path: Path) -> subprocess.Popen[Any]:
    """Spawn the local API server process as a background task."""
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    out_fh = open(log_file_path, "a", encoding="utf-8")  # noqa: SIM115

    env = os.environ.copy()
    src = str(REPO_ROOT)
    src_paths = [
        src,
        f"{src}\\apps\\api\\src",
        f"{src}\\ml\\data\\src",
        f"{src}\\ml\\features\\src",
        f"{src}\\ml\\labels\\src",
        f"{src}\\ml\\training\\src",
        f"{src}\\ml\\evaluation\\src",
        f"{src}\\backtesting\\src",
        f"{src}\\decision\\src",
        f"{src}\\portfolio\\src",
    ]
    env["PYTHONPATH"] = ";".join(src_paths)
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "alphalens_api.local.cli",
        "--config",
        str(cfg_path),
        "start",
    ]

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=out_fh,
        stderr=out_fh,
        env=env,
        creationflags=flags,
    )
    return proc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start or verify local AlphaLens research platform.")
    parser.add_argument("--config", type=Path, default=None, help="Path to local configuration JSON.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser.")
    parser.add_argument("--timeout", type=int, default=25, help="Startup timeout in seconds.")
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH, help="Path for startup logs.")
    args = parser.parse_args(argv)

    print("================================================================================")
    print("               ALPHALENS — LOCAL RESEARCH PLATFORM LAUNCHER                     ")
    print("================================================================================")

    # 1. Environment & Dependency Check
    print("[1/5] Checking Python environment and dependencies...")
    try:
        check_python_environment()
        print(f"      Python {sys.version.split()[0]} confirmed with required packages.")
    except Exception as exc:
        print(f"[FATAL] Environment verification failed: {exc}", file=sys.stderr)
        return 1

    # 2. Configuration & Integrity Check
    print("[2/5] Locating configuration and checking system integrity...")
    try:
        cfg = resolve_config(args.config)
        print(f"      Using verified configuration: {cfg.name}")
        check_res = check_database_and_integrity(cfg)
        components = check_res.get("health", {}).get("components", {})
        pg_status = components.get("postgresql", {}).get("status", "UNKNOWN")
        cat_status = components.get("catalog", {}).get("status", "UNKNOWN")
        print(f"      Database: {pg_status} | Catalog: {cat_status} | Setup: PASSED")
    except Exception as exc:
        print(f"[FATAL] Database or configuration check failed: {exc}", file=sys.stderr)
        return 2

    target_port = 8041
    dashboard_url = f"http://127.0.0.1:{target_port}/nse-market"

    # 3. Check if already active
    print("[3/5] Probing port 8041 for active AlphaLens daemon...")
    if is_api_responding(port=target_port):
        print(f"[OK]  AlphaLens API is already active on http://127.0.0.1:{target_port}!")
        print("      Reusing existing verified instance (no duplicate process spawned).")
    else:
        print(f"[4/5] Starting local API server in background...")
        print(f"      Redirecting logs to: {args.log_path}")
        start_api_daemon(cfg, args.log_path)

        # 4. Wait for health check
        started = False
        start_t = time.time()
        print("      Waiting for server ready signal", end="", flush=True)
        while time.time() - start_t < args.timeout:
            print(".", end="", flush=True)
            time.sleep(1.0)
            if is_api_responding(port=target_port):
                started = True
                break
        print("")

        if not started:
            print(f"[FATAL] Server did not become healthy within {args.timeout}s.", file=sys.stderr)
            print(f"        Please inspect the log file: {args.log_path}", file=sys.stderr)
            return 3

        print(f"[SUCCESS] AlphaLens API successfully started on port {target_port}!")

    # 5. Browser Launch
    print(f"[5/5] Access URL: {dashboard_url}")
    if not args.no_browser:
        print("      Opening dashboard in default web browser...")
        webbrowser.open(dashboard_url)
    else:
        print("      (--no-browser specified; browser launch skipped).")

    print("================================================================================")
    print(" AlphaLens is operational. Use Ctrl+C or close window when done.                ")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
