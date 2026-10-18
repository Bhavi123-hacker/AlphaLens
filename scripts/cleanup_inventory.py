"""Inventory this worktree without following junctions; remove only reviewed caches.

No private storage, Git metadata, model, data, dependency or build deletion is supported.
Run inventory first, stop concurrent development checks, then pass its receipt to apply.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import stat
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CACHE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PROTECTED = {".local-data", ".git", ".venv", "node_modules"}


def reparse(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def allocation(path: Path, size: int) -> int:
    if os.name != "nt":
        return int(getattr(path.stat(), "st_blocks", (size + 511) // 512)) * 512

    class StandardInfo(ctypes.Structure):
        _fields_ = [
            ("allocation_size", ctypes.c_longlong),
            ("end_of_file", ctypes.c_longlong),
            ("links", ctypes.c_ulong),
            ("delete_pending", ctypes.c_ubyte),
            ("directory", ctypes.c_ubyte),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0, 7, None, 3, 128, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "File allocation handle unavailable")
    call = kernel.GetFileInformationByHandleEx
    call.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
    call.restype = ctypes.c_int
    close = kernel.CloseHandle
    close.argtypes = [ctypes.c_void_p]
    close.restype = ctypes.c_int
    info = StandardInfo()
    try:
        if not call(handle, 1, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError(ctypes.get_last_error(), "Allocated file size unavailable")
        return int(info.allocation_size)
    finally:
        close(handle)


def git_files(root: Path, *args: str) -> set[str]:
    reply = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", *args],
        check=True,
        capture_output=True,
    )
    return {item.decode("utf-8") for item in reply.stdout.split(b"\0") if item}


def category(relative: Path) -> str:
    parts = relative.parts
    if parts[0] == ".local-data":
        return "private/" + (parts[1] if len(parts) > 1 else "root")
    if any(part in CACHE_NAMES for part in parts[:-1]):
        return "disposable_python_caches"
    if any(part in {"test-results", "playwright-report"} for part in parts):
        return "generated_browser_outputs_retained"
    if any(part in {"dist", "build", ".next"} for part in parts[:-1]):
        return "generated_builds_retained"
    return "source_and_evidence/" + parts[0]


def inventory(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    tracked = git_files(root)
    ignored = git_files(root, "--others", "--ignored", "--exclude-standard")
    ignored_directories = {name.rstrip("/") for name in ignored if name.endswith("/")}
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"files": 0, "logical_bytes": 0, "allocated_bytes": 0}
    )
    links: list[dict[str, str]] = []
    caches: dict[str, dict[str, int]] = {}
    errors: list[dict[str, str]] = []

    def walk(folder: Path, cache: str | None = None) -> None:
        try:
            entries = list(folder.iterdir())
        except OSError as exc:
            errors.append(
                {"path": folder.relative_to(root).as_posix(), "error": type(exc).__name__}
            )
            return
        for path in entries:
            relative = path.relative_to(root)
            rel = relative.as_posix()
            try:
                if reparse(path):
                    links.append({"path": rel, "target": str(path.resolve())})
                    continue
                if path.is_dir():
                    next_cache = cache
                    if path.name in CACHE_NAMES and not any(
                        p.casefold() in PROTECTED for p in relative.parts
                    ):
                        next_cache = cache or rel
                        caches.setdefault(
                            next_cache, {"files": 0, "logical_bytes": 0, "allocated_bytes": 0}
                        )
                    walk(path, next_cache)
                    continue
                size = path.stat().st_size
                actual = allocation(path, size)
                is_ignored = rel in ignored or any(
                    parent.as_posix() in ignored_directories for parent in relative.parents
                )
                state = "tracked" if rel in tracked else "ignored" if is_ignored else "untracked"
                for key in ("TOTAL", "git/" + state, category(relative)):
                    totals[key]["files"] += 1
                    totals[key]["logical_bytes"] += size
                    totals[key]["allocated_bytes"] += actual
                if cache is not None:
                    caches[cache]["files"] += 1
                    caches[cache]["logical_bytes"] += size
                    caches[cache]["allocated_bytes"] += actual
            except OSError as exc:
                errors.append({"path": rel, "error": type(exc).__name__})

    walk(root)
    return {
        "schema": "alphalens.safe-cleanup.v1",
        "root": str(root),
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": "Worktree files only; reparse targets and external Git directory excluded",
        "totals": dict(sorted(totals.items())),
        "links_not_followed": links,
        "cache_candidates": caches,
        "errors": errors,
    }


def validate_cache(root: Path, relative: str, tracked: set[str]) -> Path:
    target = root / relative
    if target == root or not target.is_relative_to(root):
        raise ValueError("Target outside workspace")
    parts = target.relative_to(root).parts
    if any(part.casefold() in PROTECTED or part in {"..", "."} for part in parts):
        raise ValueError("Protected path")
    if target.name not in CACHE_NAMES:
        raise ValueError("Only named regenerable Python caches may be removed")
    for ancestor in (target, *target.parents):
        if ancestor == root:
            break
        if reparse(ancestor):
            raise ValueError("Reparse target refused")
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("Resolved target outside workspace")
    prefix = relative.replace("\\", "/").rstrip("/") + "/"
    if any(item.startswith(prefix) for item in tracked):
        raise ValueError("Cache contains tracked evidence")
    return resolved


def remove_cache(root: Path, target: Path) -> dict[str, int]:
    """Check every child before mutations; never follow or delete a reparse point."""
    files: list[Path] = []
    folders: list[Path] = []

    def inspect(path: Path) -> None:
        if reparse(path) or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("Unsafe cache child")
        if path.is_dir():
            folders.append(path)
            for child in path.iterdir():
                inspect(child)
        else:
            if target.name == "__pycache__" and path.suffix not in {".pyc", ".pyo"}:
                raise ValueError("Unexpected file in bytecode cache; retain for review")
            files.append(path)

    inspect(target)
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
        ]
        create.restype = ctypes.c_void_p
        close = kernel.CloseHandle
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        for path in files:
            handle = create(str(path), 0, 0, None, 3, 128, None)
            if handle == ctypes.c_void_p(-1).value:
                raise OSError(ctypes.get_last_error(), "Cache is in use; cleanup refused")
            close(handle)
    result = {"files": 0, "logical_bytes": 0, "allocated_bytes": 0}
    for path in files:
        if reparse(path) or not path.resolve(strict=True).is_relative_to(target):
            raise ValueError("Cache changed during removal")
        size = path.stat().st_size
        actual = allocation(path, size)
        path.unlink()
        result["files"] += 1
        result["logical_bytes"] += size
        result["allocated_bytes"] += actual
    for folder in reversed(folders):
        if reparse(folder) or not folder.resolve(strict=True).is_relative_to(target):
            raise ValueError("Cache changed during removal")
        folder.rmdir()
    return result


def apply(root: Path, receipt: dict[str, Any], *, quiet_confirmed: bool) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not quiet_confirmed:
        raise ValueError("Stop concurrent tests, formatters and type checks before cache cleanup")
    if receipt.get("schema") != "alphalens.safe-cleanup.v1" or receipt.get("root") != str(root):
        raise ValueError("Inventory does not match workspace")
    tracked = git_files(root)
    targets = [validate_cache(root, rel, tracked) for rel in receipt["cache_candidates"]]
    removed: dict[str, dict[str, int]] = {}
    for target in targets:
        removed[target.relative_to(root).as_posix()] = remove_cache(root, target)
    return {"removed": removed, "completed_at": datetime.now(UTC).isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply-inventory", type=Path)
    parser.add_argument("--development-checks-stopped", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output receipt must be a new file")
    if args.apply_inventory:
        receipt = json.loads(args.apply_inventory.read_text(encoding="utf-8"))
        result = apply(args.root, receipt, quiet_confirmed=args.development_checks_stopped)
    else:
        result = inventory(args.root)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(args.output), "completed": True}))


if __name__ == "__main__":
    main()
