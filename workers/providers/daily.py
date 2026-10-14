"""Bounded source-gated Upstox acquisition into the existing P19 worker."""

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.daily.contracts import Calendar, Provider, Request
from alphalens_data.daily.providers import BASELINE
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_contracts import Access, Instrument
from workers.daily.engine import Worker
from workers.daily.features import definitions

from .store import ProviderStore
from .upstox import KEY, UpstoxClient


def run(
    access: Access,
    calendar: Calendar,
    provider_root: Path,
    pipeline_root: Path,
    *,
    at: datetime | None = None,
    budget: int = 3,
) -> dict[str, Any]:
    now = at or datetime.now(UTC)
    blockers = access.blockers(now)
    if access.provider != "upstox" or blockers:
        return {
            "state": "BLOCKED_SOURCE",
            "blockers": list(blockers),
            "api_calls": 0,
            "scheduler_enabled": False,
        }
    if not 1 <= budget <= 3:
        raise DataContractError("DAILY_CONSERVATIVE_BUDGET_REQUIRED")
    # Only an explicitly separate operational root may be supplied by the caller.
    if pipeline_root.resolve() == provider_root.resolve():
        raise DataContractError("SEPARATE_OPERATIONAL_ROOT_REQUIRED")
    verify(provider_root)
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    sessions = [
        s
        for s in calendar.sessions
        if today - timedelta(days=30) <= s.session < today
        and s.session > date(2026, 10, 6)
        and s.known_at <= now
        and s.status == "TRADING"
        and s.evidence_type == "OFFICIAL_VERIFIED_SESSION"
    ]
    if not sessions:
        return {
            "state": "BLOCKED_EVIDENCE",
            "blockers": ["KNOWN_PAST_OFFICIAL_SESSION_REQUIRED"],
            "api_calls": 0,
            "scheduler_enabled": False,
        }
    if not pipeline_root.exists():
        pipeline_root.mkdir(parents=True)
        restrict(pipeline_root)
    verify(pipeline_root)
    identity_files = sorted(provider_root.glob("master-identity-*.json"))
    if not identity_files or identity_files[-1].stat().st_size > 8192:
        raise DataContractError("VERIFIED_CURRENT_MASTER_IDENTITY_REQUIRED")
    instrument = Instrument.model_validate_json(identity_files[-1].read_bytes())
    if instrument.provider_key != KEY or instrument.observed_at > now:
        raise DataContractError("BOUNDED_RELIANCE_IDENTITY_REQUIRED")
    client = UpstoxClient(ProviderStore(provider_root), budget=budget)
    results = []
    worker = Worker(pipeline_root)
    for item in sessions:
        capture = pipeline_root / "captures" / (str(item.session) + ".json")
        if not capture.exists():
            if client.calls >= budget:
                break
            reply = client.get("candles", start=item.session, end=item.session)
            if reply.state != "ACCEPTED":
                results.append({"session": str(item.session), "state": reply.state})
                break
            envelope = {
                "version": "p30.upstox.operational-release.v1",
                "instrument": instrument.model_dump(mode="json"),
                "received_at": reply.received_at.isoformat(),
                "response": reply.body.decode("utf-8"),
            }
            # First actual capture survives interruption; never overwrite a revision.
            publish(capture, stable_json(envelope))
        if capture.stat().st_size > 2_000_000:
            raise DataContractError("DAILY_CAPTURE_SIZE_LIMIT")
        envelope = json.loads(capture.read_bytes())
        received = datetime.fromisoformat(envelope["received_at"])
        req = Request(
            mode="DAILY",
            session=item.session,
            source_received_at=received,
            provider=Provider(
                source="upstox",
                dataset="private-operational-eod",
                revision="p30.upstox.operational-release.v1",
                status="SOURCE_APPROVED_FOR_RESEARCH",
                automation_permitted=access.automation_permitted,
                retention_permitted=access.retention_permitted,
                research_permitted=access.research_permitted,
                evidence_reference="P30_OPERATOR_VERIFIED_SOURCE_USAGE_CONTRACT",
            ),
            calendar=calendar,
            baseline_identity=BASELINE,
            source_filename="upstox-session.json",
            expected_security_ids=(KEY,),
            feature_registry_id=checksum(
                stable_json(
                    [d.model_dump(mode="json") for d in definitions(item.session, received)]
                )
            ),
            payload_sha256=checksum(capture.read_bytes()),
        )
        receipt = worker.run(req, capture)
        results.append(
            {
                "session": str(item.session),
                "state": receipt["state"],
                "run_id": receipt["run_id"],
                "counts": receipt["counts"],
                "reasons": receipt["reasons"],
            }
        )
    return {
        "state": "BOUNDED_SESSIONS_PROCESSED",
        "api_calls": client.calls,
        "sessions": results,
        "coverage": "ONE_VERIFIED_PROVIDER_KEY_NOT_FULL_NSE",
        "current_inference": "UNAVAILABLE",
        "scheduler_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.config.stat().st_size > 100000:
            raise ValueError
        config = json.loads(args.config.read_bytes())
        repo = Path(__file__).resolve().parents[2]
        result = run(
            Access.model_validate(config["access"]),
            Calendar.model_validate(config["calendar"]),
            repo / ".local-data/p30-upstox-validation",
            repo / ".local-data/p30-operational-data",
        )
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, DataContractError):
        print(json.dumps({"state": "DAILY_INPUT_OR_PROVIDER_REJECTED", "scheduler_enabled": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
