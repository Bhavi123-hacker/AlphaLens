"""Prepare scoped P19 research requests without changing the frozen archive."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from workers.daily.context import trailing
from workers.daily.features import definitions
from workers.daily.schedule import disabled_task

from alphalens_data.daily.contracts import Calendar, Request, Session
from alphalens_data.daily.providers import BASELINE, assessment
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare separate P19 request; never training or ingestion"
    )
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session", type=date.fromisoformat, required=True)
    parser.add_argument("--replay-payload", type=Path)
    parser.add_argument("--security", action="append", default=[])
    args = parser.parse_args()
    if (args.output / "request.json").is_file():
        existing = Request.model_validate_json((args.output / "request.json").read_bytes())
        supplied = checksum(args.replay_payload.read_bytes()) if args.replay_payload else None
        context = json.loads((args.output / "context.json").read_bytes())["rows"]
        if (
            existing.session != args.session
            or existing.payload_sha256 != supplied
            or existing.feature_security_ids != tuple(args.security)
            or checksum(stable_json(context)) != existing.context_sha256
        ):
            raise ValueError("EXISTING_REQUEST_DIFFERS_USE_SEPARATE_REVISION_DIRECTORY")
        print(
            json.dumps(
                {"run_id": existing.run_id, "request_reused": True, "cutoff_preserved": True}
            )
        )
        return
    at = datetime.now(UTC)
    source = json.loads((args.archive_root / "research-calendar.json").read_bytes())
    # This run observes the final-vintage calendar now. Never assert actual historic publication.
    calendar = Calendar(
        sessions=tuple(
            Session(
                session=s["session_date"],
                status="TRADING",
                known_at=at,
                evidence_reference="FROZEN_RESEARCH_CALENDAR_OBSERVED_NOW",
                evidence_type=s["evidence"],
            )
            for s in source["sessions"]
        )
    )
    history = (
        trailing(args.archive_root, tuple(args.security), calendar, args.session, at)
        if args.security
        else []
    )
    mode = "HISTORICAL_REPLAY" if args.replay_payload else "DAILY"
    request = Request(
        mode=mode,
        session=args.session,
        source_received_at=at,
        provider=assessment(),
        calendar=calendar,
        baseline_identity=BASELINE,
        source_filename=f"nse_{args.session.year}.parquet",
        payload_sha256=checksum(args.replay_payload.read_bytes()) if args.replay_payload else None,
        feature_registry_id=checksum(
            stable_json([d.model_dump(mode="json") for d in definitions(args.session, at)])
        ),
        context_sha256=checksum(stable_json(history)),
        feature_security_ids=tuple(args.security),
        coverage_scope="EXPLICIT_FEATURE_SCOPE_REPLAY_NOT_COMPLETE_UNIVERSE"
        if args.security
        else "SOURCE_RELEASE_ONLY_NOT_ALL_NSE_EQUITIES",
    )
    publish(args.output / "request.json", stable_json(request.model_dump(mode="json")))
    publish(args.output / "context.json", stable_json({"rows": history}))
    repo = Path(__file__).resolve().parents[1]
    publish(
        args.output / "disabled-task.xml",
        disabled_task(
            repo / ".venv/Scripts/python.exe",
            repo,
            args.output / "request.json",
            args.output / "pipeline",
        ),
    )
    print(
        json.dumps(
            {
                "run_id": request.run_id,
                "mode": mode,
                "context_rows": len(history),
                "scheduler": "DISABLED_NOT_REGISTERED",
            }
        )
    )


if __name__ == "__main__":
    main()
