"""P19 exclusive checkpoints and atomic, checksum-verified read publication."""

import json
import os
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise DataContractError("INVALID_DAILY_RUN_ID")
    return value


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, run_id: str, name: str) -> Path:
        if not re.fullmatch(r"[a-z][a-z0-9_-]*\.json", name):
            raise DataContractError("INVALID_DAILY_PRODUCT")
        path = (self.root / "runs" / identifier(run_id) / name).resolve()
        if not path.is_relative_to(self.root):
            raise DataContractError("DAILY_PATH_ESCAPES_ROOT")
        return path

    @contextmanager
    def lock(self) -> Iterator[None]:
        """Kernel lock: failed/terminated workers do not leave an unbreakable PID lock."""
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / "worker.lock"
        with lock.open("a+b") as stream:
            if lock.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl = import_module("fcntl")

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise DataContractError("DAILY_WORKER_BUSY") from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def write(self, run_id: str, name: str, value: dict[str, Any]) -> dict[str, str]:
        payload = stable_json(value)
        if len(payload) > 50_000_000:
            raise DataContractError("DAILY_PRODUCT_SIZE_LIMIT")
        publish(self.path(run_id, name), payload)
        return {"file": name, "sha256": checksum(payload)}

    def read(self, run_id: str, name: str) -> dict[str, Any]:
        path = self.path(run_id, name)
        if path.stat().st_size > 50_000_000:
            raise DataContractError("DAILY_PRODUCT_SIZE_LIMIT")
        value: dict[str, Any] = json.loads(path.read_bytes())
        return value

    def exists(self, run_id: str, name: str) -> bool:
        return self.path(run_id, name).is_file()

    def receipt(self, run_id: str) -> dict[str, Any]:
        result = self.read(run_id, "receipt.json")
        unsigned = {k: v for k, v in result.items() if k != "receipt_sha256"}
        if checksum(stable_json(unsigned)) != result.get("receipt_sha256"):
            raise DataContractError("DAILY_RECEIPT_CHECKSUM_MISMATCH")
        if result.get("run_id") != run_id or checksum(stable_json(result["identity"])) != run_id:
            raise DataContractError("DAILY_RECEIPT_IDENTITY_INVALID")
        for reference in result["products"].values():
            path = self.path(run_id, reference["file"])
            if (
                path.stat().st_size > 50_000_000
                or checksum(path.read_bytes()) != reference["sha256"]
            ):
                raise DataContractError("DAILY_PRODUCT_CHECKSUM_MISMATCH")
        return result

    def receipts(self) -> list[dict[str, Any]]:
        files = sorted((self.root / "runs").glob("*/receipt.json"))
        if len(files) > 1000:
            raise DataContractError("DAILY_RUN_INDEX_LIMIT_ARCHIVE_REQUIRED")
        started = time.monotonic()
        rows = []
        byte_budget = 0
        for file in files:
            byte_budget += file.stat().st_size
            if byte_budget > 50_000_000 or time.monotonic() - started > 10:
                raise DataContractError("DAILY_READ_BUDGET_EXCEEDED_ARCHIVE_REQUIRED")
            rows.append(self.receipt(file.parent.name))
        return sorted(rows, key=lambda r: (r["started_at"], r["run_id"]), reverse=True)

    def product(self, run_id: str, kind: str) -> dict[str, Any]:
        receipt = self.receipt(run_id)
        reference = receipt["products"].get(kind)
        if reference is None:
            raise DataContractError("DAILY_PRODUCT_UNAVAILABLE")
        return self.read(run_id, reference["file"])

    def checkpoints(self) -> list[dict[str, Any]]:
        """Operational evidence only; never exposes incomplete observation products."""
        files = sorted((self.root / "runs").glob("*/request.json"))
        if len(files) > 1000:
            raise DataContractError("DAILY_RUN_INDEX_LIMIT_ARCHIVE_REQUIRED")
        output = []
        for file in files:
            run_id = file.parent.name
            if self.exists(run_id, "receipt.json"):
                continue
            request = self.read(run_id, "request.json")
            if (
                checksum(
                    stable_json({k: v for k, v in request.items() if k != "source_received_at"})
                )
                != run_id
            ):
                raise DataContractError("DAILY_CHECKPOINT_IDENTITY_INVALID")
            retries = sorted(file.parent.glob("retry-*.json"))
            output.append(
                dict(
                    run_id=run_id,
                    session=request["session"],
                    mode=request["mode"],
                    state="RETRYABLE_FAILURE"
                    if retries
                    else "UNPUBLISHED_CHECKPOINT_RECOVERY_REQUIRED",
                    retry_count=len(retries),
                    products_visible=False,
                )
            )
        return output
