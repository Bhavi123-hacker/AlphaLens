"""TEST_ONLY deterministic SQLite sidecar races and fail-closed permission checks."""

import importlib
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from alphalens_api.auth import permissions
from alphalens_api.operations import store as module
from alphalens_api.operations.store import OperationsStore


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
@pytest.mark.parametrize("error", [FileNotFoundError, ValueError])
@pytest.mark.parametrize("vanishes", [True, False])
def test_optional_sidecar_race_does_not_bypass_existing_file_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    error: type[Exception],
    vanishes: bool,
) -> None:
    store = OperationsStore(tmp_path / "ops")
    store.initialize()
    sidecar = Path(str(store.path) + suffix)
    sidecar.write_bytes(b"TEST_ONLY inspection race; never opened as SQLite data")
    checked = []

    def verify(path: Path, **kwargs: Any) -> None:
        checked.append(path)
        if path == sidecar:
            if vanishes:
                path.unlink()
            raise error("AUTH_FILESYSTEM_PERMISSION_FAILED")
        permissions.verify(path, **kwargs)

    monkeypatch.setattr(module, "verify", verify)
    if vanishes:
        with store.connection() as connection:
            assert connection.execute("SELECT count(*) FROM probes").fetchone()[0] == 0
    else:
        with pytest.raises(error, match="FILESYSTEM_PERMISSION_FAILED"), store.connection():
            pytest.fail("Existing unverified sidecar must not permit a connection")
    assert store.root in checked and store.path in checked and sidecar in checked


@pytest.mark.parametrize("target", ["directory", "database"])
@pytest.mark.parametrize("error", [FileNotFoundError, ValueError, PermissionError])
def test_required_paths_never_use_optional_sidecar_exception_handling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    error: type[Exception],
) -> None:
    store = OperationsStore(tmp_path / "ops")
    store.initialize()
    required = store.root if target == "directory" else store.path

    def verify(path: Path, **kwargs: Any) -> None:
        if path == required:
            raise error("TEST_ONLY_REQUIRED_PATH_REJECTED")
        permissions.verify(path, **kwargs)

    monkeypatch.setattr(module, "verify", verify)
    with pytest.raises(error, match="REQUIRED_PATH_REJECTED"), store.connection():
        pytest.fail("Required paths must always pass verification")


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
def test_existing_insecure_sidecar_is_rejected(tmp_path: Path, suffix: str) -> None:
    store = OperationsStore(tmp_path / "ops")
    store.initialize()
    sidecar = Path(str(store.path) + suffix)
    sidecar.touch(mode=0o600)
    if os.name == "nt":
        security = importlib.import_module("win32security")
        descriptor = security.GetNamedSecurityInfo(
            str(sidecar), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION
        )
        acl = descriptor.GetSecurityDescriptorDacl()
        acl.AddAccessAllowedAce(
            security.ACL_REVISION, 0x1F01FF, security.CreateWellKnownSid(security.WinWorldSid, None)
        )
        security.SetNamedSecurityInfo(
            str(sidecar),
            security.SE_FILE_OBJECT,
            security.DACL_SECURITY_INFORMATION,
            None,
            None,
            acl,
            None,
        )
    else:
        sidecar.chmod(0o644)
    with pytest.raises(ValueError, match="FILESYSTEM_PERMISSION_FAILED"), store.connection():
        pytest.fail("Insecure existing sidecar must never be opened")


@pytest.mark.parametrize("mode,owner", [(0o600, 123), (0o644, 123), (0o600, 456)])
def test_posix_mode_and_owner_use_one_metadata_snapshot(
    monkeypatch: pytest.MonkeyPatch, mode: int, owner: int
) -> None:
    # Exercise POSIX semantics on both CI/Linux and the Windows development host.
    monkeypatch.setattr(permissions, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(permissions, "os", SimpleNamespace(geteuid=lambda: 123))
    path = Mock(spec=Path)
    path.stat.return_value = SimpleNamespace(st_mode=mode, st_uid=owner)
    if mode == 0o600 and owner == 123:
        permissions.verify(path)
    else:
        with pytest.raises(ValueError, match="FILESYSTEM_PERMISSION_FAILED"):
            permissions.verify(path)
    path.stat.assert_called_once_with()
