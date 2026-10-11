"""Bounded TEST_ONLY authentication/native smoke; never load models or market data."""

import importlib
import json
import os
import secrets
import shutil
import stat
import tempfile
from pathlib import Path

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.main import create_app
from alphalens_api.operations.recovery import backup, restore
from alphalens_api.operations.store import OperationsStore


def main() -> None:
    for module in (
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "lightgbm",
        "catboost",
        "xgboost",
        "workers.daily.engine",
        "workers.alerts.store",
        "workers.observability",
        "alphalens_api.local.cli",
    ):
        importlib.import_module(module)
    with tempfile.TemporaryDirectory(prefix="TEST_ONLY_p21_") as temporary:
        store = AuthStore(Path(temporary) / "auth")
        store.initialize()
        secret = secrets.token_urlsafe(32)
        store.bootstrap("test_operator", secret)
        raw, identity = store.login("test_operator", secret)
        if store.session(raw)["role"] != "ADMIN":
            raise RuntimeError("AUTH_SMOKE_FAILED")
        store.revoke(identity["account_id"])
        create_app(Settings(environment="test", auth_root=store.root))
        operations = OperationsStore(Path(temporary) / "operations")
        operations.initialize()
        settings = Settings(
            environment="test", auth_root=store.root, operations_root=operations.root
        )
        backup(settings, Path(temporary) / "backup")
        restored = restore(Path(temporary) / "backup", Path(temporary) / "restored")
        if not restored["restored"] or restored["auth_sessions"] != "REVOKED":
            raise RuntimeError("OPERATIONS_RECOVERY_SMOKE_FAILED")
        inventory = {
            name: {
                "present": bool(path := shutil.which(name)),
                "suid": bool(path and Path(path).stat().st_mode & stat.S_ISUID),
            }
            for name in ("mount", "umount", "nsenter", "infocmp", "perl", "systemd-homed")
        }
        result = {
            "authentication": "PASSED",
            "operations_backup_restore": "PASSED",
            "native_imports": "PASSED",
            "non_root": os.getuid() != 0,
            "binary_inventory": inventory,
            "archive_tar_files": sorted(
                str(p) for p in Path("/usr/share/perl").glob("*/Archive/Tar.pm")
            ),
        }
        if any(inventory[name]["suid"] for name in ("mount", "umount")):
            raise RuntimeError("UNNECESSARY_MOUNT_PRIVILEGE_PRESENT")
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
