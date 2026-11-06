"""Vanishing SQLite sidecars are distinct from permission failures on existing files."""

import secrets
from pathlib import Path
from typing import Any

import pytest

from alphalens_api.auth import store as module
from alphalens_api.auth.permissions import verify as original_verify
from alphalens_api.auth.store import AuthError, AuthStore


@pytest.mark.parametrize("vanishes", [True, False])
def test_sidecar_inspection_race_preserves_existing_acl_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vanishes: bool
) -> None:
    store = AuthStore(tmp_path / "auth")
    store.initialize()
    secret = secrets.token_urlsafe(32)
    store.bootstrap("test_operator", secret)
    raw, _ = store.login("test_operator", secret)
    sidecar = Path(str(store.path) + "-shm")
    sidecar.write_bytes(b"TEST_ONLY sidecar")

    def verify(path: Path, **kwargs: Any) -> None:
        if path == sidecar:
            if vanishes:
                path.unlink()
            raise ValueError("AUTH_FILESYSTEM_PERMISSION_FAILED")
        original_verify(path, **kwargs)

    monkeypatch.setattr(module, "verify", verify)
    if vanishes:
        assert store.session(raw)["role"] == "ADMIN"
    else:
        with pytest.raises(AuthError, match="AUTH_FILESYSTEM_PERMISSION_FAILED"):
            store.session(raw)
