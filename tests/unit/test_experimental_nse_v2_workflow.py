"""TEST_ONLY operational failures and calendar controls; never real NSE evidence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import pytest
from pydantic import ValidationError
from workers.experimental_nse.acquire import initialize
from workers.experimental_nse_v2 import data, models, pipeline, workflow
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


class FixedClock(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> Self:
        return cls(2026, 10, 17, 12, tzinfo=tz)


def reply(day: str, *, closed: bool) -> Reply:
    body = {
        "status": "success",
        "data": []
        if closed
        else [
            {
                "exchange": "NSE",
                "start_time": int(
                    datetime.fromisoformat(day + "T03:45:00+00:00").timestamp() * 1000
                ),
                "end_time": int(datetime.fromisoformat(day + "T10:00:00+00:00").timestamp() * 1000),
            }
        ],
    }
    return Reply(200, json.dumps(body).encode(), NOW, "ACCEPTED")


def clock() -> dict[str, str]:
    return {"session_date": "2026-10-17", "lower_at": NOW.isoformat(), "upper_at": NOW.isoformat()}


@pytest.fixture
def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[workflow.Config, dict[str, Any], list[str]]:
    root = tmp_path / "TEST_ONLY"
    initialize(root)
    config = workflow.Config(root=root, provider_root=tmp_path / "TEST_ONLY_provider")
    dataset: dict[str, Any] = {
        "identities": [{"provider_key": f"NSE_EQ|TEST{i:08d}"} for i in range(50)],
        "sessions": ["2026-10-16"],
        "rows": [{"key": f"NSE_EQ|TEST{i:08d}", "session": "2026-10-16"} for i in range(50)],
        "quality": {"excluded_sessions": {}},
        "next_session_timing": {"open_at": "2026-10-19T03:45:00+00:00"},
    }
    calls: list[str] = []
    monkeypatch.setattr(workflow, "datetime", FixedClock)
    monkeypatch.setattr(data, "load", lambda root: dataset)
    monkeypatch.setattr(data, "load_current", lambda root: dataset)
    monkeypatch.setattr(
        workflow,
        "guard",
        lambda: {
            "session_date": "2026-10-17",
            "lower_at": NOW.isoformat(),
            "upper_at": NOW.isoformat(),
        },
    )
    monkeypatch.setattr(workflow, "_cached_timing", lambda root, day: reply(str(day), closed=True))
    monkeypatch.setattr(pipeline, "verified", lambda path: {"model_sha256": "TEST_ONLY"})
    monkeypatch.setattr(models, "load_model", lambda *args: {"feature_names": ["TEST_ONLY"] * 16})

    def reconciled(*args: Any) -> dict[str, int]:
        calls.append("reconcile")
        return {"pending": 31}

    def inferred(*args: Any) -> dict[str, Any]:
        calls.append("infer")
        return {"forecast_write": {"inserted": 0, "replayed": 31}, "replayed": True}

    monkeypatch.setattr(pipeline, "reconcile_saved", reconciled)
    monkeypatch.setattr(pipeline, "infer", inferred)
    monkeypatch.setattr(workflow, "summary", lambda *args: {"forecasts": 31, "outcomes": 0})
    return config, dataset, calls


def test_holiday_from_official_dated_evidence_still_reconciles_without_gets(setup: Any) -> None:
    config, _, calls = setup
    result = workflow.run(config)
    assert result["state"] == "NON_TRADING_SESSION"
    assert result["source_requests_last_run"] == 0
    assert calls == ["reconcile", "infer"]
    assert result["prospective"] == {"forecasts": 31, "outcomes": 0}
    assert workflow.read_status(config.root)["state"] == "NON_TRADING_SESSION"


def test_unknown_calendar_is_never_filled_from_weekdays(
    setup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, dataset, _ = setup
    monkeypatch.setattr(workflow, "_cached_timing", lambda *args: None)
    meter = workflow.Meter(config, enabled=False)
    result = workflow._plan(config, dataset, clock(), meter)
    assert result["state"] == "OFFICIAL_SESSION_LOOKUP_PENDING"
    assert meter.calls == 0


def test_oldest_first_catchup_and_special_session_close(
    setup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, dataset, _ = setup
    dataset["sessions"] = ["2026-10-15"]
    for row in dataset["rows"]:
        row["session"] = "2026-10-15"
    monkeypatch.setattr(workflow, "_cached_timing", lambda root, day: reply(str(day), closed=False))
    plan = workflow._plan(config, dataset, clock(), workflow.Meter(config, enabled=False))
    assert plan["state"] == "CAPTURE_REQUIRED" and plan["day"] == "2026-10-16"
    dataset["sessions"] = ["2026-10-16"]
    for row in dataset["rows"]:
        row["session"] = "2026-10-16"
    before_close = {"session_date": "2026-10-17", "lower_at": "2026-10-17T09:00:00+00:00"}
    assert (
        workflow._plan(config, dataset, before_close, workflow.Meter(config, enabled=False))[
            "state"
        ]
        == "BEFORE_SESSION_CLOSE"
    )


def test_elapsed_entry_skips_new_predictions_but_not_reconciliation(setup: Any) -> None:
    config, dataset, calls = setup
    dataset["next_session_timing"]["open_at"] = "2026-10-16T03:45:00+00:00"
    result = workflow.run(config)
    assert calls == ["reconcile"]
    assert result["inference"]["backdated_forecasts"] == 0


def test_scheduled_collection_requires_explicit_exact_approval(setup: Any) -> None:
    config, _, calls = setup
    result = workflow.run(config, scheduled=True)
    assert result["state"] == "FAILED"
    assert result["last_failure"]["code"] == "EXPLICIT_CADENCE_QUOTA_APPROVAL_REQUIRED"
    assert result["source_requests_last_run"] == 0 and calls == []


def test_cooldown_and_interrupted_reserved_daily_quota_are_enforced(setup: Any) -> None:
    config, _, _ = setup
    first = workflow.run(config, collect=True)
    assert first["source_requests_last_run"] == 0
    blocked = workflow.run(config, collect=True)
    assert blocked["last_failure"]["code"] == "V2_COLLECTION_COOLDOWN_ACTIVE"
    folder = config.root / "workflow"
    for i in (1, 2):
        workflow._record(
            config.root,
            {
                "collect": True,
                "started_at": "2026-10-17T01:00:00+00:00",
                "state": "STARTED",
                "run_id": str(i),
            },
            f"{i:032x}.start.json",
        )
    blocked = workflow.run(config, collect=True)
    assert blocked["last_failure"]["code"] == "V2_DAILY_REQUEST_QUOTA_EXHAUSTED"
    assert blocked["source_requests_last_run"] == 0
    assert len(list(folder.glob("*.start.json"))) == 3


def test_meter_shared_limit_and_no_automatic_retries(
    setup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, _, _ = setup
    network: list[str] = []

    class Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            assert kwargs["retries"] == 0

        def get(self, operation: str, **kwargs: Any) -> str:
            network.append(operation)
            return "TEST_ONLY"

    monkeypatch.setattr(workflow, "UpstoxClient", Client)
    meter = workflow.Meter(config.model_copy(update={"max_requests_per_run": 1}), enabled=True)
    a = meter.factory(ProviderStore(config.provider_root), budget=1, retries=0)
    b = meter.factory(ProviderStore(config.provider_root), budget=1, retries=0)
    a.get("timings")
    with pytest.raises(ValueError, match="BUDGET"):
        b.get("timings")
    assert network == ["timings"] and meter.calls == 1


def test_failure_diagnostics_are_retained_and_receipt_tamper_rejected(setup: Any) -> None:
    config, _, _ = setup
    failed = workflow.run(config, scheduled=True)
    assert failed["state"] == "FAILED"
    workflow.run(config)
    assert (
        workflow.read_status(config.root)["last_failure"]["code"]
        == "EXPLICIT_CADENCE_QUOTA_APPROVAL_REQUIRED"
    )
    selected = json.loads((config.root / "workflow/latest.json").read_bytes())
    (config.root / "workflow" / selected["name"]).write_text("{}")
    with pytest.raises(ValueError, match="HASH"):
        workflow.read_status(config.root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("scheduled_collection_enabled", 1),
        ("scheduled_collection_enabled", "true"),
        ("max_requests_per_run", True),
        ("max_requests_per_run", "120"),
        ("max_requests_per_run", 120.0),
        ("max_runs_per_day", False),
        ("cooldown_minutes", "60"),
        ("max_catchup_calendar_days", 31.0),
    ],
)
def test_operational_config_rejects_coerced_boolean_and_integer_values(
    setup: Any,
    field: str,
    value: Any,
) -> None:
    config, _, _ = setup
    values = config.model_dump()
    values[field] = value
    with pytest.raises(ValidationError):
        workflow.Config.model_validate(values)
    with pytest.raises(ValidationError):
        workflow.Config.model_validate_json(
            json.dumps(
                {
                    **config.model_dump(mode="json"),
                    field: value,
                }
            )
        )


def test_independent_clock_cooldown_survives_forward_operating_system_clock_jump(
    setup: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, _, _ = setup
    assert workflow.run(config, collect=True)["state"] == "NON_TRADING_SESSION"

    class JumpedClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls(2026, 10, 20, 18, tzinfo=tz)

    monkeypatch.setattr(workflow, "datetime", JumpedClock)
    monkeypatch.setattr(
        workflow,
        "guard",
        lambda: {
            "session_date": "2026-10-17",
            "lower_at": "2026-10-17T12:30:00+00:00",
            "upper_at": "2026-10-17T12:30:01+00:00",
        },
    )
    result = workflow.run(config, collect=True)
    assert result["last_failure"]["code"] == "V2_COLLECTION_COOLDOWN_ACTIVE"
    assert result["source_requests_last_run"] == 0
    assert result["quota_day"] == "2026-10-17"
    assert len(list((config.root / "workflow").glob("*.start.json"))) == 1


def test_publication_pending_capture_reconciles_but_never_scores_old_dataset(
    setup: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, dataset, calls = setup
    monkeypatch.setattr(workflow, "_cached_timing", lambda root, day: reply(str(day), closed=False))

    def pending(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append("capture")
        assert str(kwargs["session_date"]) == "2026-10-17"
        return {**dataset, "collection_pending": {"new_observations": 0}}

    monkeypatch.setattr(data, "closed_current", pending)
    result = workflow.run(config, collect=True)
    assert result["state"] == "PUBLICATION_PENDING"
    assert calls == ["capture", "reconcile"]
    assert result["inference"]["backdated_forecasts"] == 0
    assert result["prospective"]["outcomes"] == 0


@pytest.mark.parametrize("approval", [None, "wrong-policy"])
def test_enabled_schedule_cannot_make_requests_without_exact_approved_policy(
    setup: Any,
    monkeypatch: pytest.MonkeyPatch,
    approval: str | None,
) -> None:
    config, _, calls = setup
    config = workflow.Config.model_validate(
        {**config.model_dump(), "scheduled_collection_enabled": True}
    )
    if approval is not None:
        folder = config.root / "workflow"
        folder.mkdir(exist_ok=True)
        path = folder / "collection-approval.json"
        path.write_text(
            json.dumps(
                {
                    "policy_sha256": "0" * 64,
                    "approved_by": "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL",
                    "scope": "PRIVATE_50_STOCK_RECURRING_COLLECTION",
                    "approved_at": NOW.isoformat(),
                }
            )
        )
        path.chmod(0o600)

    class ForbiddenClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError("TEST_ONLY no provider client may be constructed before approval")

    monkeypatch.setattr(workflow, "UpstoxClient", ForbiddenClient)
    result = workflow.run(config, scheduled=True)
    assert result["state"] == "FAILED"
    assert result["source_requests_last_run"] == 0 and calls == []
    assert not list((config.root / "workflow").glob("*.start.json"))
