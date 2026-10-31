"""TEST_ONLY storage roots; never inspect or mutate operational private state."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.private_storage_inventory import scan


def test_hardlinks_are_one_physical_file(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    root.mkdir()
    source = root / "first.bin"
    source.write_bytes(b"TEST_ONLY" * 2048)
    os.link(source, root / "second.bin")
    result = scan([root])
    total = result["totals"]["TOTAL"]
    assert total["files"] == 2
    assert total["logical_bytes"] == source.stat().st_size * 2
    assert total["hardlink_aliases"] == 1
    assert total["unique_allocated_bytes"] > 0
    assert not result["errors"]


def test_reparse_target_is_not_followed(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "child").mkdir()
    (outside / "valuable.txt").write_text("TEST_ONLY retained")
    link = root / "linked"
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            check=True,
            capture_output=True,
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        result = scan([root])
        assert result["totals"].get("TOTAL", {}).get("files", 0) == 0
        assert len(result["reparse_points_not_followed"]) == 1
        with pytest.raises(ValueError, match="reparse"):
            scan([link])
        with pytest.raises(ValueError, match="reparse"):
            scan([link / "child"])
        assert (outside / "valuable.txt").read_text() == "TEST_ONLY retained"
    finally:
        if sys.platform == "win32":
            link.rmdir()
        else:
            link.unlink()


def test_overlapping_roots_refused(tmp_path: Path) -> None:
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(ValueError, match="Overlapping"):
        scan([tmp_path, child])
