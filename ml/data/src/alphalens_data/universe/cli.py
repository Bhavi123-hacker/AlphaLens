"""Offline development universe snapshots and sampled survivorship audit."""

import argparse
from datetime import date, datetime
from pathlib import Path

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_data.universe.models import UniverseInput
from alphalens_data.universe.service import HistoricalUniverse, audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconstruct a development historical universe")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--decision-time", type=datetime.fromisoformat, required=True)
    parser.add_argument("--mode", choices=("historical", "live"), default="historical")
    parser.add_argument("--output-root", type=Path, default=Path("data/p4-snapshots"))
    parser.add_argument("--audit-snapshots", nargs="*", type=Path)
    args = parser.parse_args()
    try:
        root = local_output(args.output_root)
        data = UniverseInput.model_validate_json(args.input.read_bytes())
        universe = HistoricalUniverse(data)
        snapshot = universe.as_of(args.date, args.decision_time, mode=args.mode)
        universe.replay(snapshot)
        publish(root / (snapshot.snapshot_id + ".json"), snapshot.to_bytes())
        if args.audit_snapshots:
            from alphalens_data.universe.models import UniverseSnapshot

            prior = tuple(
                UniverseSnapshot.model_validate_json(p.read_bytes()) for p in args.audit_snapshots
            )
            for old in prior:
                universe.replay(old)
            report = audit(prior + (snapshot,))
            publish(root / (snapshot.snapshot_id + ".audit.json"), report.to_bytes())
        reasons: dict[str, int] = {}
        for entry in snapshot.excluded_securities:
            reasons[entry.membership_reason] = reasons.get(entry.membership_reason, 0) + 1
        print(
            stable_json(
                {
                    "session": snapshot.session_date.isoformat(),
                    "universe": data.definition.universe_id,
                    "classification": data.definition.classification,
                    "historical_universe_status": snapshot.historical_universe_status,
                    "eligible_count": len(snapshot.eligible_securities),
                    "eligible_securities": [
                        {
                            "security_id": e.security_id,
                            "symbol": e.identity.symbol if e.identity else None,
                            "analysis_eligible": e.analysis_eligible,
                            "analysis_reason": e.analysis_reason,
                        }
                        for e in snapshot.eligible_securities
                    ],
                    "excluded_count": len(snapshot.excluded_securities),
                    "reason_breakdown": reasons,
                    "snapshot_hash": snapshot.snapshot_id,
                    "version": data.definition.version,
                    "production_claims_permitted": False,
                }
            ).decode()
        )
        return 0
    except DataContractError as exc:
        print(
            stable_json(
                {"status": "REJECTED", "reason": exc.code, "production_claims_permitted": False}
            ).decode()
        )
        return 2
    except Exception:
        print(
            stable_json(
                {
                    "status": "REJECTED",
                    "reason": "UNIVERSE_EVIDENCE_OR_REPLAY_INVALID",
                    "production_claims_permitted": False,
                }
            ).decode()
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
