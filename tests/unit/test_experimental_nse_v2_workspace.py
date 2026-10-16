"""TEST_ONLY evidence boundary tests. No fixture is a genuine forecast."""

from pathlib import Path

import pytest
from workers.experimental_nse_v2.pipeline import verified, write_checked
from workers.experimental_nse_v2.workspace import read_workspace


def test_absent_workspace_is_explicit_and_never_publishes(tmp_path: Path) -> None:
    for root in (None, tmp_path):
        result = read_workspace(root)
        assert result["available"] is False
        assert result["candidates"] == []
        assert result["accepted_current_rankings"] == 0
        assert result["status"] == "EXPERIMENTAL_UNVALIDATED"


def test_checked_evidence_rejects_tamper_and_preserves_immutable_original(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.json"
    write_checked(path, {"classification": "TEST_ONLY", "scores": []})
    assert verified(path)["classification"] == "TEST_ONLY"
    with pytest.raises((ValueError, FileExistsError)):
        write_checked(path, {"classification": "TEST_ONLY", "scores": [1]})
    path.write_text("{}")
    with pytest.raises(ValueError, match="CHECKSUM"):
        verified(path)
