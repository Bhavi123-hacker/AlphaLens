"""Bounded source-gated Upstox acquisition into the existing P19 worker."""

import argparse
import json
import re
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.daily.contracts import Calendar, Provider, Request, Session
from alphalens_data.daily.providers import BASELINE
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Access, Instrument
from workers.daily.engine import Worker
from workers.daily.features import definitions

from .calendar import nse_timing
from .store import ProviderStore
from .upstox import KEY, UpstoxClient


def configured_pipeline(config: dict[str, Any], repo: Path) -> Path:
    """Explicit local CLI configuration only; separate owned operational namespace."""
    legacy = repo / ".local-data/p30-operational-data"
    value = config.get("pipeline_root")
    if value is None:
        return legacy
    if not isinstance(value, str):
        raise DataContractError("PRIVATE_OPERATIONAL_ROOT_REQUIRED")
    path = Path(value).resolve()
    if path == legacy.resolve():
        return path
    if path.parent != (repo / ".local-data").resolve() or not re.fullmatch(
        r"p\d+-private-operational-[a-z0-9-]{1,64}", path.name
    ):
        raise DataContractError("SEPARATE_OWNED_PRIVATE_OPERATIONAL_ROOT_REQUIRED")
    return path


def run(
    access: Access,
    calendar: Calendar,
    provider_root: Path,
    pipeline_root: Path,
    *,
    at: datetime | None = None,
    budget: int = 3,
    instrument_key: str = KEY,
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
    if access.permission_reference is None:
        raise DataContractError("SOURCE_PERMISSION_REFERENCE_REQUIRED")
    if not 1 <= budget <= 3:
        raise DataContractError("DAILY_CONSERVATIVE_BUDGET_REQUIRED")
    if not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", instrument_key):
        raise DataContractError("EXACT_NSE_EQ_KEY_REQUIRED")
    # Only an explicitly separate operational root may be supplied by the caller.
    if pipeline_root.resolve() == provider_root.resolve():
        raise DataContractError("SEPARATE_OPERATIONAL_ROOT_REQUIRED")
    if instrument_key != KEY:
        pipeline_root = pipeline_root / (
            "instrument-" + sha256(instrument_key.encode()).hexdigest()[:16]
        )
    verify(provider_root)
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    if not pipeline_root.exists():
        pipeline_root.mkdir(parents=True)
        restrict(pipeline_root)
    verify(pipeline_root)
    known = {s.session: s for s in calendar.sessions}
    pinned = sorted((pipeline_root / "captures").glob("*-session.json"))
    if len(pinned) > 1000:
        raise DataContractError("DAILY_CALENDAR_ARCHIVE_REQUIRED")
    for path in pinned:
        if path.stat().st_size > 8192:
            raise DataContractError("DAILY_SESSION_METADATA_SIZE_LIMIT")
        fact = Session.model_validate_json(path.read_bytes())
        if today - timedelta(days=30) <= fact.session < today:
            known[fact.session] = fact
    client = UpstoxClient(ProviderStore(provider_root), budget=budget)
    previous = today - timedelta(days=1)
    if previous not in known:
        timing = client.get("timings", end=previous)
        try:
            if nse_timing(timing, previous)["session_elapsed"]:
                now = max(now, timing.received_at)
                fact = Session(
                    session=previous,
                    status="TRADING",
                    known_at=timing.received_at,
                    evidence_reference="UPSTOX_OFFICIAL_MARKET_TIMING",
                    evidence_type="OFFICIAL_VERIFIED_SESSION",
                )
                known[previous] = fact
                publish(
                    pipeline_root / "captures" / (str(previous) + "-session.json"),
                    stable_json(fact.model_dump(mode="json")),
                )
        except (ValueError, KeyError, TypeError):
            pass  # Unknown/non-returned dates are never inferred as trading.
    sessions = [
        s
        for s in sorted(known.values(), key=lambda s: s.session)
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
            "api_calls": client.calls,
            "scheduler_enabled": False,
        }
    identity_files = sorted(provider_root.glob("master-identity-*.json"))
    if not identity_files or identity_files[-1].stat().st_size > 8192:
        raise DataContractError("VERIFIED_CURRENT_MASTER_IDENTITY_REQUIRED")
    if len(identity_files) > 500:
        raise DataContractError("BOUNDED_MASTER_IDENTITY_FILES_REQUIRED")
    identities = [
        Instrument.model_validate_json(p.read_bytes())
        for p in identity_files
        if p.stat().st_size <= 8192
    ]
    matches = [
        i
        for i in identities
        if i.provider_key == instrument_key
        and i.observed_at <= now
        and i.exchange == "NSE"
        and i.segment == "NSE_EQ"
    ]
    if not matches:
        raise DataContractError("VERIFIED_CURRENT_MASTER_IDENTITY_REQUIRED")
    instrument = max(matches, key=lambda i: i.observed_at)
    if instrument_key != KEY and instrument.instrument_type != "EQ":
        raise DataContractError("VERIFIED_CURRENT_EQ_TYPE_REQUIRED")
    results = []
    worker = Worker(pipeline_root)
    for item in sessions:
        capture = pipeline_root / "captures" / (str(item.session) + ".json")
        fact_path = pipeline_root / "captures" / (str(item.session) + "-session.json")
        if not fact_path.exists():
            publish(fact_path, stable_json(item.model_dump(mode="json")))
        pinned_fact = Session.model_validate_json(fact_path.read_bytes())
        if not capture.exists():
            if client.calls >= budget:
                break
            reply = client.get("candles", key=instrument_key, start=item.session, end=item.session)
            if reply.state != "ACCEPTED":
                results.append({"session": str(item.session), "state": reply.state})
                break
            observed = parse_daily(reply.body, instrument, reply.received_at)
            if not observed:
                # An empty pre-publication response must not become an immutable
                # accepted capture that prevents a later bounded catch-up retry.
                results.append({"session": str(item.session), "state": "EOD_CANDLE_PENDING"})
                continue
            if len(observed) != 1 or observed[0].session != item.session:
                raise DataContractError("OPERATIONAL_RELEASE_SINGLE_SESSION_REQUIRED")
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
                evidence_reference=access.permission_reference,
            ),
            calendar=Calendar(sessions=(pinned_fact,)),
            baseline_identity=BASELINE,
            source_filename="upstox-session.json",
            expected_security_ids=(instrument_key,),
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
            configured_pipeline(config, repo),
            instrument_key=config.get("instrument_key", KEY),
        )
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, DataContractError):
        print(json.dumps({"state": "DAILY_INPUT_OR_PROVIDER_REJECTED", "scheduler_enabled": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
