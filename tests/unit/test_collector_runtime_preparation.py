"""TEST_ONLY destinations; no environment install or scheduled-task mutation."""

from pathlib import Path

import pytest
from scripts.prepare_nse_collector_runtime import fresh_destination


def test_fresh_private_environment_is_allowed_without_touching_shared(tmp_path: Path) -> None:
    private = tmp_path / ".local-data"
    private.mkdir()
    shared = tmp_path / ".venv"
    shared.mkdir()
    marker = shared / "TEST_ONLY_keep.txt"
    marker.write_text("TEST_ONLY_original")
    target = private / "TEST_ONLY_collector"
    assert fresh_destination(tmp_path, target) == target
    assert not target.exists()
    assert marker.read_text() == "TEST_ONLY_original"


@pytest.mark.parametrize("relative", [".venv", ".local-data", "other", "../outside"])
def test_existing_or_nonprivate_destination_is_rejected(tmp_path: Path, relative: str) -> None:
    (tmp_path / ".local-data").mkdir()
    with pytest.raises(ValueError, match="FRESH_PRIVATE"):
        fresh_destination(tmp_path, tmp_path / relative)


def test_existing_private_environment_is_preserved(tmp_path: Path) -> None:
    target = tmp_path / ".local-data" / "TEST_ONLY_app"
    target.mkdir(parents=True)
    marker = target / "TEST_ONLY_keep"
    marker.write_text("TEST_ONLY_app_still_running")
    with pytest.raises(ValueError, match="FRESH_PRIVATE"):
        fresh_destination(tmp_path, target)
    assert marker.read_text() == "TEST_ONLY_app_still_running"


def test_lexical_parent_escape_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".local-data").mkdir()
    with pytest.raises(ValueError, match="FRESH_PRIVATE"):
        fresh_destination(tmp_path, tmp_path / ".local-data" / ".." / "outside")
