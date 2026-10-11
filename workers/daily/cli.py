"""Offline-first worker commands. No schedule registration or training entry point."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from alphalens_data.daily.contracts import Request
from alphalens_data.daily.providers import check_publication, check_source
from alphalens_data.daily.storage import Store, identifier
from alphalens_data.errors import DataContractError
from alphalens_data.normalization import checksum
from workers.observability import completed

from .engine import Worker


def approved_hashes(manifest: Path | None) -> frozenset[str]:
    if manifest is None:
        return frozenset()
    payload = manifest.read_bytes()
    if checksum(payload) != "30071821607336c6193f88efa873b21be789c8fa33c5b3eb805450ccdecd05d4":
        raise DataContractError("APPROVED_MANIFEST_CHECKSUM_MISMATCH")
    value = json.loads(payload)
    # Only the repository's previously approved, pinned archive. Caller cannot
    # authorize a new revision by adding a provider status flag.
    from alphalens_data.daily.providers import PINNED_REVISION

    if PINNED_REVISION not in json.dumps(value):
        raise DataContractError("APPROVED_ARCHIVE_REVISION_REQUIRED")
    return frozenset(v["sha256"] for v in value["files"] if v["filename"].startswith("nse/"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P19 local research worker; live activation blocked"
    )
    parser.add_argument(
        "command",
        choices=("status", "check-source", "dry-run", "run-once", "replay", "verify", "resume"),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--approved-manifest", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--network-metadata", action="store_true")
    parser.add_argument("--network-publication-status", action="store_true")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    result: Any = None
    store = Store(args.root)
    try:
        if args.command == "check-source":
            result = check_source(network=args.network_metadata)
            if args.network_publication_status:
                result["publication_check"] = check_publication()
        elif args.command == "status":
            result = dict(
                live_data_activation="BLOCKED",
                scheduled_execution="DISABLED",
                runs=store.receipts(),
            )
        elif args.command == "verify":
            result = store.receipt(identifier(args.run_id)) if args.run_id else store.receipts()
        else:
            if args.command == "resume":
                run_id = identifier(args.run_id or "")
                request = Request.model_validate(store.read(run_id, "request.json"))
                if request.run_id != run_id:
                    raise DataContractError(
                        "CHECKPOINT_VERSION_UNSUPPORTED_READ_ONLY_VERIFY_AVAILABLE"
                    )
                history = store.read(run_id, "context.json")["rows"]
            else:
                if args.request is None:
                    parser.error("--request is required")
                request = Request.model_validate(json.loads(args.request.read_bytes()))
                history = json.loads(args.context.read_bytes())["rows"] if args.context else []
            if args.command == "dry-run":
                result = dict(
                    run_id=request.run_id,
                    mode=request.mode,
                    session=request.session.isoformat(),
                    calendar_status=request.calendar.status(
                        request.session, request.source_received_at
                    ),
                    provider_allowed=request.provider.allowed(request.mode),
                    mutations=False,
                    live_data_activation="BLOCKED",
                )
            else:
                if args.command == "run-once" and request.mode != "DAILY":
                    raise DataContractError("RUN_ONCE_REQUIRES_DAILY_MODE_USE_REPLAY")
                if args.command == "replay" and request.mode == "DAILY":
                    raise DataContractError("REPLAY_REQUIRES_EXPLICIT_REPLAY_MODE")
                worker = Worker(args.root, approved_hashes(args.approved_manifest))
                result = worker.run(request, args.payload, history)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        if isinstance(result, dict) and result.get("state") in {
            "BLOCKED_SOURCE",
            "BLOCKED_EVIDENCE",
        }:
            return 2
        if isinstance(result, dict) and result.get("state") == "FAILED":
            return 1
        return 0
    except KeyboardInterrupt:
        print('{"state":"INTERRUPTED","checkpoint":"RETAINED_RESUME_SAME_REQUEST"}')
        return 130
    except (DataContractError, OSError, ValueError, KeyError):
        # Exception strings may contain paths or provider payloads; never log them.
        print('{"state":"FAILED_OR_RETRYABLE","reason":"CHECK_INPUT_AND_LOCAL_EVIDENCE"}')
        return 1
    finally:
        state = result.get("state") if isinstance(result, dict) else None
        completed(
            "daily",
            args.command,
            started,
            500
            if result is None or state == "FAILED"
            else 503
            if state in {"BLOCKED_SOURCE", "BLOCKED_EVIDENCE"}
            else 200,
            result.get("run_id") if isinstance(result, dict) else args.run_id,
        )


if __name__ == "__main__":
    sys.exit(main())
