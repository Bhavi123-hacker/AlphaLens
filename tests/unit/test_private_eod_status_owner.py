"""TEST_ONLY explicit data-owner containment; no collection, scheduling or network."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from workers.providers.operations_status import status

from alphalens_api.auth.permissions import restrict


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    owner = tmp_path / "TEST_ONLY_owner"
    private = owner / ".local-data"
    folder = private / "p34-runtime"
    folder.mkdir(parents=True)
    restrict(private)
    restrict(folder)
    path = folder / "daily-config.json"
    path.write_text(
        json.dumps(
            {
                "pipeline_root": str(private / "p34-private-operational-test"),
                "access": {"provider": "upstox"},
                "calendar": {"sessions": []},
            }
        )
    )
    restrict(path)
    return owner, path


def test_explicit_owner_cannot_select_another_checkouts_configuration(tmp_path: Path) -> None:
    owner, config = fixture(tmp_path)
    with pytest.raises(ValueError, match="CONFIG_OWNER_MISMATCH"):
        status(config, owner_root=owner / "TEST_ONLY_other")


def test_explicit_owner_does_not_weaken_operational_store_containment(tmp_path: Path) -> None:
    owner, config = fixture(tmp_path)
    value = json.loads(config.read_bytes())
    value["pipeline_root"] = str(tmp_path / "TEST_ONLY_outside")
    config.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="SEPARATE_OWNED_PRIVATE_OPERATIONAL_ROOT_REQUIRED"):
        status(config, owner_root=owner)
    assert not (tmp_path / "TEST_ONLY_outside").exists()


def test_reparse_store_is_rejected_before_resolving_its_target(tmp_path: Path) -> None:
    owner, config = fixture(tmp_path)
    pipeline = Path(json.loads(config.read_bytes())["pipeline_root"])
    outside = tmp_path / "TEST_ONLY_outside"
    outside.mkdir()
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(pipeline), str(outside)],
            capture_output=True,
            check=True,
        )
    else:
        pipeline.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="REPARSE_REJECTED"):
            status(config, owner_root=owner)
        assert list(outside.iterdir()) == []
    finally:
        if sys.platform == "win32":
            pipeline.rmdir()
        else:
            pipeline.unlink()


def test_owner_acl_failure_is_not_treated_as_an_empty_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workers.providers import operations_status

    owner, config = fixture(tmp_path)

    def denied(*args: object, **kwargs: object) -> None:
        raise ValueError("AUTH_FILESYSTEM_PERMISSION_FAILED")

    monkeypatch.setattr(operations_status, "verify", denied)
    with pytest.raises(ValueError, match="FILESYSTEM_PERMISSION_FAILED"):
        status(config, owner_root=owner)


def test_other_reparse_attributes_are_rejected_before_config_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, config = fixture(tmp_path)
    original = Path.lstat

    def reparse(path: Path) -> object:
        metadata = original(path)
        if path == config:
            return SimpleNamespace(st_mode=metadata.st_mode, st_file_attributes=1024)
        return metadata

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ValueError, match="REPARSE_REJECTED"):
        status(config, owner_root=owner)
