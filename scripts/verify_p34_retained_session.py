"""One privately permitted operational EOD session and zero-GET replay; no model promotion."""

import json
from pathlib import Path

from workers.daily.engine import Worker
from workers.providers.automation import readiness, task_xml
from workers.providers.daily import run

from alphalens_api.auth.permissions import restrict
from alphalens_data.daily.contracts import Calendar
from alphalens_data.providers.multi_contracts import Access

REFERENCE = "UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN"


def main() -> None:
    from datetime import UTC, datetime

    repo = Path(__file__).resolve().parents[1]
    private = repo / ".local-data/p34-runtime"
    pipeline = repo / ".local-data/p34-private-operational-eod"
    if pipeline.exists() or (private.exists() and any(private.iterdir())):
        raise ValueError("NEW_ISOLATED_VERIFICATION_ROOTS_REQUIRED")
    private.mkdir(exist_ok=True)
    restrict(private)
    access = Access(
        provider="upstox",
        account_status="ACTIVE",
        credential_configured=True,
        permission_reference=REFERENCE,
        automation_permitted=True,
        retention_permitted=True,
        research_permitted=True,
        display_permitted=True,
        nse_verified=True,
        token_kind="READ_ONLY_ANALYTICS",
        operator_activation=True,
    )
    prior = json.loads((repo / ".local-data/p30-runtime/daily-config.json").read_bytes())
    calendar = Calendar.model_validate(
        {
            **prior["calendar"],
            "sessions": [s for s in prior["calendar"]["sessions"] if s["status"] == "NON_TRADING"],
        }
    )
    provider = repo / ".local-data/p30-upstox-validation"
    first = run(access, calendar, provider, pipeline, budget=2)
    second = run(access, calendar, provider, pipeline, budget=2)
    if first["sessions"] != second["sessions"] or second["api_calls"] != 0:
        raise ValueError("RETAINED_IDEMPOTENT_REPLAY_FAILED")
    receipts = Worker(pipeline).store.receipts()
    if len(receipts) != 1:
        raise ValueError("EXACTLY_ONE_GENUINE_SESSION_REQUIRED")
    receipt = receipts[0]
    if (
        receipt["counts"].get("observations") != 1
        or receipt["counts"].get("predictions") != 0
        or receipt["identity"]["provider"]["evidence_reference"] != REFERENCE
    ):
        raise ValueError("RETAINED_OBSERVATION_OR_PERMISSION_LINEAGE_FAILED")
    product = Worker(pipeline).store.product(receipt["run_id"], "provider_observations")
    if product["canonical_join_permitted"] or product["feature_eligibility"]:
        raise ValueError("OPERATIONAL_DATA_MUST_NOT_PROMOTE_FROZEN_RESEARCH")
    row = product["rows"][0]
    calendar = Calendar.model_validate(
        {
            "sessions": [
                json.loads(p.read_bytes()) for p in (pipeline / "captures").glob("*-session.json")
            ]
        }
    )
    config = private / "daily-config.json"
    config.write_text(
        json.dumps(
            {
                "access": access.model_dump(mode="json"),
                "calendar": calendar.model_dump(mode="json"),
                "pipeline_root": str(pipeline),
                "private_scope": "SINGLE_OPERATOR_NONCOMMERCIAL_NO_REDISTRIBUTION",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (private / "daily-task-disabled.xml").write_bytes(task_xml(config.resolve()))
    result = {
        "version": "p34.retained-session-verification.v1",
        "state": receipt["state"],
        "session": str(receipt["identity"]["session"]),
        "instrument_key": row["instrument"]["provider_key"],
        "received_at": row["received_at"],
        "first_api_calls": first["api_calls"],
        "replay_api_calls": second["api_calls"],
        "counts": receipt["counts"],
        "run_id": receipt["run_id"],
        "observation_id": row["observation_id"],
        "permission_reference": REFERENCE,
        "price_basis": row["price_basis"],
        "action_status": row["action_status"],
        "publication_time": row["publication_time"],
        "private_operational_retention": True,
        "retained_prices_in_receipt": False,
        "historical_canonical_join": False,
        "feature_eligibility": False,
        "predictions": 0,
        "readiness": readiness(access, calendar, datetime.now(UTC), pipeline),
        "scheduler_registered": False,
        "scheduler_enabled": False,
        "remaining_scheduler_requirement": "LOCAL_CLOCK_CONVERGENCE_AND_EXPLICIT_TASK_ACTIVATION",
        "frozen_research_modified": False,
    }
    (repo / ".local-data/p34-retained-session-verification.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"P34_RETAINED_SESSION_NOT_VERIFIED","provider_values_logged":false}')
        raise SystemExit(1) from None
