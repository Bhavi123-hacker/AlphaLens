"""TEST_ONLY scanner rows exercise exact fixture review, never real credentials."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from scripts import verify_secret_history as gate


@pytest.fixture
def sample(monkeypatch: pytest.MonkeyPatch) -> tuple[list[Any], list[Any], dict[str, Any]]:
    raw = "TEST_ONLY_REVIEW_MARKER"
    blob = ("negative validation input: " + raw + "\n").encode()
    entry = {
        "detector": "TEST_ONLY_DETECTOR",
        "commit": "a" * 40,
        "file": "tests/TEST_ONLY.py",
        "scanner_line": 1,
        "source_line": 1,
        "match_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "source_blob_sha256": hashlib.sha256(blob).hexdigest(),
    }
    finding = {
        "Verified": False,
        "Raw": raw,
        "DetectorName": entry["detector"],
        "SourceMetadata": {
            "Data": {"Git": {"commit": entry["commit"], "file": entry["file"], "line": 1}}
        },
    }
    logs = [
        {
            "msg": "finished scanning",
            "level": "info-0",
            "trufflehog_version": gate.VERSION,
            "chunks": 12,
            "bytes": 500,
            "verified_secrets": 0,
            "unverified_secrets": 1,
        }
    ]
    manifest = {"schema": 1, "scanner_version": gate.VERSION, "fixtures": [entry]}
    monkeypatch.setattr(gate, "_git", lambda *args: blob)
    return [finding], logs, manifest


def test_exact_review_preserves_raw_failure_and_redacts_match(sample: tuple[Any, ...]) -> None:
    findings, logs, manifest = sample
    result = gate.review(findings, logs, 183, manifest, Path("."))
    assert result["state"] == "VERIFIED_COMPLETE"
    assert result["raw_scan_clean"] is False
    assert result["raw_scanner_exit"] == 183
    assert result["reviewed_fixture_findings"] == 1
    assert findings[0]["Raw"] not in str(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Raw", "TEST_ONLY_DIFFERENT_MARKER"),
        ("Verified", True),
        ("Verified", None),
        ("DetectorName", "OTHER_TEST_ONLY_DETECTOR"),
    ],
)
def test_changed_or_verified_finding_fails(
    sample: tuple[Any, ...],
    field: str,
    value: Any,
) -> None:
    findings, logs, manifest = sample
    findings[0][field] = value
    with pytest.raises(gate.ReviewError):
        gate.review(findings, logs, 183, manifest, Path("."))


@pytest.mark.parametrize(
    "field,value",
    [
        ("commit", "b" * 40),
        ("file", "other.py"),
        ("line", 2),
    ],
)
def test_other_location_is_never_accepted(
    sample: tuple[Any, ...],
    field: str,
    value: Any,
) -> None:
    findings, logs, manifest = sample
    findings[0]["SourceMetadata"]["Data"]["Git"][field] = value
    with pytest.raises(gate.ReviewError, match="UNREVIEWED"):
        gate.review(findings, logs, 183, manifest, Path("."))


@pytest.mark.parametrize("exit_code", [0, 1, 128])
def test_clean_or_failed_execution_is_not_complete_history_evidence(
    sample: tuple[Any, ...],
    exit_code: int,
) -> None:
    findings, logs, manifest = sample
    with pytest.raises(gate.ReviewError):
        gate.review(findings, logs, exit_code, manifest, Path("."))


@pytest.mark.parametrize("change", ["missing", "duplicate", "error", "version", "counts"])
def test_incomplete_error_and_inconsistent_summary_fail(
    sample: tuple[Any, ...],
    change: str,
) -> None:
    findings, logs, manifest = sample
    if change == "missing":
        logs.clear()
    elif change == "duplicate":
        logs.append(copy.deepcopy(logs[0]))
    elif change == "error":
        logs.append({"level": "error", "msg": "TEST_ONLY_SCAN_ERROR"})
    elif change == "version":
        logs[0]["trufflehog_version"] = "TEST_ONLY_OTHER_VERSION"
    else:
        logs[0]["unverified_secrets"] = 0
    with pytest.raises(gate.ReviewError):
        gate.review(findings, logs, 183, manifest, Path("."))


def test_source_context_change_blocks_fixture(
    sample: tuple[Any, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings, logs, manifest = sample
    monkeypatch.setattr(gate, "_git", lambda *args: b"TEST_ONLY_OTHER_CONTEXT")
    with pytest.raises(gate.ReviewError, match="SOURCE_BLOB"):
        gate.review(findings, logs, 183, manifest, Path("."))


def test_duplicate_finding_cannot_consume_another_reviewed_fixture(sample: tuple[Any, ...]) -> None:
    findings, logs, manifest = sample
    findings.append(copy.deepcopy(findings[0]))
    other = copy.deepcopy(manifest["fixtures"][0])
    other["file"] = "other.py"
    manifest["fixtures"].append(other)
    logs[0]["unverified_secrets"] = 2
    with pytest.raises(gate.ReviewError, match="DUPLICATE"):
        gate.review(findings, logs, 183, manifest, Path("."))


def test_cli_uses_full_history_without_scanner_exclusions(
    sample: tuple[Any, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    findings, logs, manifest = sample
    blob = ("negative validation input: " + str(findings[0]["Raw"]) + "\n").encode()
    repository = tmp_path / "TEST_ONLY_repository"
    repository.mkdir()
    scanner = tmp_path / "TEST_ONLY_scanner"
    scanner.write_bytes(b"TEST_ONLY_NOT_AN_EXECUTABLE")
    policy = tmp_path / "TEST_ONLY_manifest.json"
    policy.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(gate, "MANIFEST", policy)

    def git_reply(_repository: Path, *args: str) -> bytes:
        if args == ("rev-parse", "HEAD"):
            return b"a" * 40
        if args == ("rev-parse", "--is-shallow-repository"):
            return b"false"
        if args[:2] == ("rev-list", "--count"):
            return b"123"
        return blob

    monkeypatch.setattr(gate, "_git", git_reply)
    commands: list[list[str]] = []

    def scan(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        kwargs["stdout"].write((json.dumps(findings[0]) + "\n").encode())
        kwargs["stderr"].write((json.dumps(logs[0]) + "\n").encode())
        return subprocess.CompletedProcess(command, 183)

    monkeypatch.setattr(subprocess, "run", scan)
    output = tmp_path / "TEST_ONLY_receipt"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_secret_history",
            "--scanner",
            str(scanner),
            "--repository",
            str(repository),
            "--output-dir",
            str(output),
        ],
    )
    assert gate.main() == 0
    assert len(commands) == 1
    command = commands[0]
    assert "--fail" in command and "--fail-on-scan-errors" in command
    assert "--results=verified,unknown" in command
    assert command[command.index("--branch") + 1] == "a" * 40
    assert not any(
        argument.startswith(("--since", "--max-depth", "--exclude", "--no-verification"))
        for argument in command
    )
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["reachable_commits"] == 123
    assert receipt["raw_scanner_exit"] == 183
    assert findings[0]["Raw"] not in capsys.readouterr().out
