"""TEST_ONLY native inactive-wrapper failure paths; never starts a collector."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows cmd wrapper")
@pytest.mark.parametrize("arguments", [[], ["TEST_ONLY_missing.json"], ["TEST_ONLY.json", "extra"]])
def test_inactive_watchlist_wrapper_fails_before_any_provider_or_clock_access(
    arguments: list[str],
) -> None:
    repo = Path(__file__).resolve().parents[2]
    wrapper = repo / "scripts/windows/p30-daily-update-patched.cmd"
    result = subprocess.run(
        [
            str(Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe"),
            "/d",
            "/c",
            str(wrapper),
            *arguments,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stdout or "configuration is missing" in result.stdout
