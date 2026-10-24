"""Scan complete reachable Git history, then review only exact registered fixtures.

No scanner exclusions, verification changes, or ignored findings are used. The
raw scanner exit remains in the receipt. Output containing matches stays in the
private output directory; only fingerprints and disposition metadata are printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VERSION = "3.93.8"
MANIFEST = Path("docs/security/reviewed-secret-fixtures-v1.json")


class ReviewError(ValueError):
    """A fixed error code, never scanner input or a matched value."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repository: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True, check=False)
    if result.returncode:
        raise ReviewError("GIT_EVIDENCE_UNAVAILABLE")
    return result.stdout


def review(
    findings: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    raw_exit: int,
    manifest: dict[str, Any],
    repository: Path,
) -> dict[str, Any]:
    """Fail closed on changed matches, verified results, source drift or scan errors."""
    if manifest.get("schema") != 1 or manifest.get("scanner_version") != VERSION:
        raise ReviewError("FIXTURE_POLICY_VERSION_REJECTED")
    entries = manifest.get("fixtures")
    if not isinstance(entries, list) or not entries:
        raise ReviewError("FIXTURE_POLICY_REQUIRED")
    finished = [row for row in logs if row.get("msg") == "finished scanning"]
    if len(finished) != 1 or any(
        str(row.get("level", "")).lower() in {"error", "fatal", "panic"} for row in logs
    ):
        raise ReviewError("SCAN_INCOMPLETE_OR_ERROR")
    summary = finished[0]
    if (
        summary.get("trufflehog_version") != VERSION
        or not isinstance(summary.get("chunks"), int)
        or summary["chunks"] <= 0
        or not isinstance(summary.get("bytes"), int)
        or summary["bytes"] <= 0
        or summary.get("verified_secrets") != 0
        or summary.get("unverified_secrets") != len(findings)
        or raw_exit != 183
        or len(findings) != len(entries)
    ):
        raise ReviewError("SCAN_COUNTS_VERSION_OR_EXIT_REJECTED")
    accepted = []
    used: set[int] = set()
    for finding in findings:
        if finding.get("Verified") is not False:
            raise ReviewError("VERIFIED_OR_MALFORMED_FINDING_REJECTED")
        raw = finding.get("Raw")
        if not isinstance(raw, str) or not raw:
            raise ReviewError("FINDING_MATCH_REQUIRED")
        try:
            metadata = finding["SourceMetadata"]["Data"]["Git"]
            identity = (
                finding["DetectorName"],
                metadata["commit"],
                metadata["file"],
                metadata["line"],
                _sha(raw.encode()),
            )
        except (KeyError, TypeError) as exc:
            raise ReviewError("FINDING_METADATA_REJECTED") from exc
        candidates = [
            (index, entry)
            for index, entry in enumerate(entries)
            if identity
            == (
                entry["detector"],
                entry["commit"],
                entry["file"],
                entry["scanner_line"],
                entry["match_sha256"],
            )
        ]
        if len(candidates) != 1 or candidates[0][0] in used:
            raise ReviewError("UNREVIEWED_OR_DUPLICATE_FINDING")
        index, entry = candidates[0]
        # Immutable committed context, not a mutable file with the same name.
        blob = _git(repository, "show", f"{entry['commit']}:{entry['file']}")
        if _sha(blob) != entry["source_blob_sha256"]:
            raise ReviewError("REVIEWED_SOURCE_BLOB_CHANGED")
        lines = blob.decode("utf-8").splitlines()
        source_line = entry["source_line"]
        if not isinstance(source_line, int) or not 1 <= source_line <= len(lines):
            raise ReviewError("REVIEWED_SOURCE_LINE_REJECTED")
        if entry.get("source_line_sha256"):
            if _sha(lines[source_line - 1].encode()) != entry["source_line_sha256"]:
                raise ReviewError("REVIEWED_SOURCE_LINE_CHANGED")
        elif raw not in lines[source_line - 1]:
            raise ReviewError("REVIEWED_SOURCE_MATCH_CHANGED")
        used.add(index)
        accepted.append(
            {
                key: entry[key]
                for key in ("detector", "commit", "file", "scanner_line", "match_sha256")
            }
        )
    return {
        "state": "VERIFIED_COMPLETE",
        "method": "FULL_HISTORY_RAW_SCAN_AND_EXACT_SOURCE_REVIEW",
        "raw_scanner_exit": raw_exit,
        "raw_scan_clean": False,
        "verified_secrets": 0,
        "reviewed_fixture_findings": len(accepted),
        "unexpected_findings": 0,
        "chunks": summary["chunks"],
        "bytes": summary["bytes"],
        "scanner_version": VERSION,
        "fixtures": sorted(accepted, key=lambda row: row["file"]),
    }


def _json_lines(path: Path) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (ValueError, UnicodeError) as exc:
        raise ReviewError("SCANNER_JSON_REJECTED") from exc
    if any(not isinstance(row, dict) for row in rows):
        raise ReviewError("SCANNER_JSON_REJECTED")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    repository = args.repository.resolve(strict=True)
    repo_root = Path(__file__).resolve().parents[1]
    manifest_bytes = (repo_root / MANIFEST).read_bytes()
    scanner = args.scanner.resolve(strict=True)
    head = _git(repository, "rev-parse", "HEAD").decode().strip()
    shallow = _git(repository, "rev-parse", "--is-shallow-repository").decode().strip()
    if shallow != "false":
        raise ReviewError("FULL_GIT_HISTORY_REQUIRED")
    # Scan from the parent to avoid Windows drive URI duplication. TruffleHog
    # makes its own isolated clone; no trusted-local-config bypass is enabled.
    command = [
        str(scanner),
        "git",
        f"file://{repository.name}",
        "--branch",
        head,
        "--no-update",
        "--json",
        "--fail",
        "--fail-on-scan-errors",
        "--results=verified,unknown",
        "--concurrency=4",
    ]
    temp = output / "temp"
    temp.mkdir(mode=0o700)
    environment = dict(os.environ, TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp))
    with (
        (output / "findings.private.jsonl").open("xb") as findings_stream,
        (output / "scanner.private.jsonl").open("xb") as log_stream,
    ):
        result = subprocess.run(
            command,
            cwd=repository.parent,
            env=environment,
            stdout=findings_stream,
            stderr=log_stream,
            check=False,
        )
    receipt: dict[str, Any] = {
        "state": "BLOCKED_SECURITY",
        "raw_scanner_exit": result.returncode,
    }
    try:
        receipt = review(
            _json_lines(output / "findings.private.jsonl"),
            _json_lines(output / "scanner.private.jsonl"),
            result.returncode,
            json.loads(manifest_bytes),
            repository,
        )
    except ReviewError as exc:
        receipt["reason"] = str(exc)
    receipt.update(
        verified_at=datetime.now(UTC).isoformat(),
        head=head,
        reachable_commits=int(_git(repository, "rev-list", "--count", head)),
        scope="ALL_REACHABLE_HISTORY_NO_SINCE_OR_DEPTH_LIMIT",
        manifest_sha256=_sha(manifest_bytes),
        scanner_binary_sha256=_sha(scanner.read_bytes()),
    )
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0 if receipt["state"] == "VERIFIED_COMPLETE" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewError, OSError, ValueError):
        # Do not leak subprocess output, matched values or arbitrary exceptions.
        print(json.dumps({"state": "BLOCKED_SECURITY", "reason": "SCAN_EXECUTION_REJECTED"}))
        raise SystemExit(1) from None
