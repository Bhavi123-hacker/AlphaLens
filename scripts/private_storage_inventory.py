"""Read-only Windows storage accounting for explicitly selected AlphaLens roots.

Never follows reparse points. Counts hard-linked file allocation once globally;
logical sizes remain directory-entry totals. No deletion capability is provided.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.cleanup_inventory import allocation


def scan(roots: list[Path]) -> dict[str, Any]:
    canonical: list[Path] = []
    for root in roots:
        if not root.exists():
            raise ValueError("Explicit inventory root is missing")
        for ancestor in (root.absolute(), *root.absolute().parents):
            info = ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
                raise ValueError("Inventory root ancestors must not be reparse points")
        resolved = root.resolve(strict=True)
        if any(
            resolved.is_relative_to(other) or other.is_relative_to(resolved) for other in canonical
        ):
            raise ValueError("Overlapping inventory roots refused")
        canonical.append(resolved)
    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "files": 0,
            "logical_bytes": 0,
            "unique_allocated_bytes": 0,
            "hardlink_aliases": 0,
            "latest_modification_ns": 0,
        }
    )
    seen: set[tuple[int, int]] = set()
    links: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    file_systems = {str(p.anchor): shutil.disk_usage(p.anchor)._asdict() for p in canonical}

    def visit(folder: Path, root: Path) -> None:
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if (
                            stat.S_ISLNK(info.st_mode)
                            or getattr(info, "st_file_attributes", 0) & 1024
                        ):
                            links.append({"path": str(path), "action": "NOT_FOLLOWED"})
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            visit(path, root)
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        relative = path.relative_to(root)
                        depth = 3 if relative.parts[0] in {"p28-worktree", ".local-data"} else 1
                        group = str(
                            root.joinpath(*relative.parts[: min(depth, len(relative.parts) - 1)])
                        )
                        # Windows DirEntry.stat caches zero st_ino/st_dev. Path.stat
                        # obtains the actual volume/file identity for hardlinks.
                        identity_info = path.stat(follow_symlinks=False)
                        identity = (identity_info.st_dev, identity_info.st_ino)
                        alias = identity in seen
                        actual = 0 if alias else allocation(path, info.st_size)
                        seen.add(identity)
                        for label in ("TOTAL", "ROOT " + str(root), group):
                            row = totals[label]
                            row["files"] += 1
                            row["logical_bytes"] += info.st_size
                            row["unique_allocated_bytes"] += actual
                            row["hardlink_aliases"] += int(alias)
                            row["latest_modification_ns"] = max(
                                row["latest_modification_ns"], info.st_mtime_ns
                            )
                    except OSError as exc:
                        errors.append({"path": str(path), "error": type(exc).__name__})
        except OSError as exc:
            errors.append({"path": str(folder), "error": type(exc).__name__})

    for root in canonical:
        visit(root, root)
    return {
        "schema": "alphalens.private-storage-inventory.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "roots": list(map(str, canonical)),
        "volume_usage_before": file_systems,
        "totals": dict(sorted(totals.items())),
        "reparse_points_not_followed": links,
        "errors": errors,
        "accounting": (
            "FileStandardInfo allocation; hardlinks once by volume/file identity; "
            "excludes directory/MFT metadata; VHDX file allocation only; "
            "no virtual capacity addition"
        ),
        "mutations": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Existing receipt preserved")
    result = scan(args.root)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(args.output),
                "totals": result["totals"]["TOTAL"],
                "errors": len(result["errors"]),
            }
        )
    )


if __name__ == "__main__":
    main()
