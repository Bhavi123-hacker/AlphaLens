"""One guarded operational V2 process; no training, orders or implicit activation."""

import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from workers.experimental_nse.acquire import PERMISSION, digest, encoded, initialize, private_path
from workers.providers.daily_clock import guard
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply, UpstoxClient

from alphalens_api.auth.permissions import verify
from alphalens_data.daily.storage import Store

from . import data, models, pipeline
from .features import build
from .forward import summary

IST = ZoneInfo("Asia/Kolkata")
CADENCE = ("20:30", "21:30", "22:30")


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    root: Path
    provider_root: Path
    permission_reference: StrictStr = PERMISSION
    max_requests_per_run: StrictInt = Field(default=120, ge=1, le=120)
    max_runs_per_day: StrictInt = Field(default=3, ge=1, le=3)
    cooldown_minutes: StrictInt = Field(default=60, ge=60, le=1440)
    max_catchup_calendar_days: StrictInt = Field(default=31, ge=1, le=31)
    cadence: tuple[StrictStr, ...] = CADENCE
    timezone: StrictStr = "Asia/Kolkata"
    scheduled_collection_enabled: StrictBool = False


def configured(path: Path) -> Config:
    verify(path, directory=False)
    value = Config.model_validate_json(path.read_bytes())
    if (
        value.permission_reference != PERMISSION
        or value.cadence != CADENCE
        or value.timezone != str(IST)
    ):
        raise ValueError("V2_OPERATIONAL_POLICY_NOT_APPROVED")
    for location in (value.root, value.provider_root):
        if not location.is_absolute() or location.is_symlink():
            raise ValueError("PRIVATE_ABSOLUTE_OPERATIONAL_ROOT_REQUIRED")
        verify(location)
    return value


def policy(config: Config) -> dict[str, Any]:
    base = data.load(config.root)
    identities = sorted(i["provider_key"] for i in base["identities"])
    if len(identities) != 50 or len(set(identities)) != 50:
        raise ValueError("EXACT_APPROVED_50_STOCK_COHORT_REQUIRED")
    return {
        "version": "nse.v2.daily.operations.1",
        "cohort_sha256": digest(encoded(identities)),
        **config.model_dump(mode="json", exclude={"scheduled_collection_enabled"}),
        "maximum_daily_gets": config.max_requests_per_run * config.max_runs_per_day,
        "training": False,
        "orders": False,
    }


def scheduled_approval(config: Config) -> None:
    path = private_path(config.root, "workflow", "collection-approval.json")
    if not config.scheduled_collection_enabled or not path.is_file():
        raise ValueError("EXPLICIT_CADENCE_QUOTA_APPROVAL_REQUIRED")
    verify(path, directory=False)
    approval = json.loads(path.read_bytes())
    if (
        approval.get("policy_sha256") != digest(encoded(policy(config)))
        or approval.get("approved_by") != "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL"
        or approval.get("scope") != "PRIVATE_50_STOCK_RECURRING_COLLECTION"
        or datetime.fromisoformat(approval["approved_at"]) > datetime.now(UTC)
    ):
        raise ValueError("EXACT_OPERATIONAL_APPROVAL_RECEIPT_REQUIRED")


class Meter:
    def __init__(self, config: Config, *, enabled: bool) -> None:
        self.limit, self.calls, self.enabled = config.max_requests_per_run, 0, enabled

    def factory(self, store: ProviderStore, **kwargs: Any) -> Any:
        delegate = UpstoxClient(store, **kwargs)
        meter = self

        class Client:
            calls = 0

            def get(self, operation: Any, **arguments: Any) -> Reply:
                if not meter.enabled:
                    raise ValueError("EXPLICIT_COLLECTION_REQUIRED")
                if meter.calls >= meter.limit:
                    raise ValueError("V2_RUN_REQUEST_BUDGET_EXHAUSTED")
                # Reserve before the call; an interrupted request still consumes budget.
                meter.calls += 1
                self.calls += 1
                return delegate.get(operation, **arguments)

        return Client()


def _folder(root: Path) -> Path:
    return private_path(root, "workflow")


def _record(root: Path, value: dict[str, Any], name: str) -> None:
    folder = _folder(root)
    body = encoded(value)
    path = private_path(folder, name)
    with path.open("xb") as handle:
        handle.write(body)
    private_path(folder, name + ".sha256").write_text(digest(body), encoding="ascii")
    temporary = private_path(folder, uuid.uuid4().hex + ".tmp")
    temporary.write_bytes(encoded({"name": name, "sha256": digest(body)}))
    temporary.replace(private_path(folder, "latest.json"))


def _latest(root: Path) -> dict[str, Any] | None:
    folder = _folder(root)
    pointer = private_path(folder, "latest.json")
    if not pointer.exists():
        return None
    selection = json.loads(pointer.read_bytes())
    if not re.fullmatch(r"[0-9a-f]{32}\.(start|done)\.json", selection["name"]):
        raise ValueError("V2_OPERATIONAL_RECEIPT_PATH_REJECTED")
    body = private_path(folder, selection["name"]).read_bytes()
    if digest(body) != selection["sha256"]:
        raise ValueError("V2_OPERATIONAL_RECEIPT_HASH_REJECTED")
    result: dict[str, Any] = json.loads(body)
    return result


def _history(root: Path, suffix: str) -> list[dict[str, Any]]:
    result = []
    files = list(_folder(root).glob("*." + suffix + ".json"))
    if len(files) > 10000:
        raise ValueError("V2_OPERATIONAL_HISTORY_ARCHIVE_REQUIRED")
    for path in files:
        body = private_path(_folder(root), path.name).read_bytes()
        check = private_path(_folder(root), path.name + ".sha256")
        if digest(body) != check.read_text(encoding="ascii"):
            raise ValueError("V2_OPERATIONAL_HISTORY_HASH_REJECTED")
        result.append(json.loads(body))
    return sorted(result, key=lambda r: r["started_at"])


def read_status(root: Path | None) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "state": "NO_SAVED_OPERATIONAL_RUN",
        "last_failure": None,
        "stages": [],
        "automatic_acquisition_enabled": False,
        "inference_schedule_enabled": False,
        "next_action": "Run the guarded private V2 workflow to check readiness.",
    }
    if root is None:
        return empty
    value = _latest(root)
    if value is None:
        return empty
    history = _history(root, "done")
    failed = [r["last_failure"] for r in history if r.get("last_failure")]
    successful = [r["completed_at"] for r in history if r["state"] != "FAILED"]
    return {
        **empty,
        **value,
        "last_run_at": value["started_at"],
        "state": "INTERRUPTED_OR_RUNNING" if value["state"] == "STARTED" else value["state"],
        "last_failure": failed[-1] if failed else None,
        "last_success_at": successful[-1] if successful else None,
    }


def _cached_timing(root: Path, day: date) -> Reply | None:
    # Only files whose dated source checksum belongs to the verified ancestry qualify.
    current = data.load_current(root)
    while True:
        receipt = current.get("timing_receipts", {}).get(str(day))
        folder = (
            private_path(root, "captures", current["capture_id"], "raw")
            if current.get("capture_id")
            else private_path(root, "current-raw")
        )
        if receipt:
            raw = private_path(folder, str(day) + ".json").read_bytes()
            if digest(raw) != receipt["sha256"]:
                raise ValueError("V2_TIMING_CHECKSUM_REJECTED")
            return Reply(200, raw, datetime.fromisoformat(receipt["received_at"]), "ACCEPTED")
        previous = current.get("parent_capture_id")
        if previous == "LEGACY_CURRENT":
            current = json.loads(private_path(root, "current.json").read_bytes())
        elif previous:
            current = json.loads(
                private_path(root, "captures", previous, "current.json").read_bytes()
            )
        else:
            return None


def _plan(
    config: Config, dataset: dict[str, Any], clock: dict[str, Any], meter: Meter
) -> dict[str, Any]:
    today = date.fromisoformat(clock["session_date"])
    keys = {i["provider_key"] for i in dataset["identities"]}
    latest = date.fromisoformat(dataset["sessions"][-1])
    observed = {r["key"] for r in dataset["rows"] if r["session"] == str(latest)}
    first = latest if observed != keys else latest + timedelta(days=1)
    if today < latest or (today - first).days > config.max_catchup_calendar_days:
        raise ValueError("V2_CLOCK_OR_BOUNDED_CATCHUP_REVIEW_REQUIRED")
    client = meter.factory(ProviderStore(config.provider_root), budget=20, retries=0)
    scanned = 0
    day = first
    while day <= today:
        reply = _cached_timing(config.root, day)
        if reply is None or (datetime.now(UTC) - reply.received_at).days > 7:
            if not meter.enabled:
                return {"state": "OFFICIAL_SESSION_LOOKUP_PENDING", "day": str(day)}
            if scanned >= 10:
                return {"state": "BOUNDED_CALENDAR_CATCHUP_PENDING", "day": str(day)}
            reply = client.get("timings", end=day)
            scanned += 1
        timing = data.timing_fact(reply, day)
        if timing is not None:
            if datetime.fromisoformat(timing["close_at"]) >= datetime.fromisoformat(
                clock["lower_at"]
            ):
                return {"state": "BEFORE_SESSION_CLOSE", "day": str(day)}
            return {"state": "CAPTURE_REQUIRED", "day": str(day), "reply": reply}
        day += timedelta(days=1)
    return {
        "state": "NON_TRADING_SESSION" if first <= today else "SOURCE_SESSION_COMPLETE",
        "day": str(today),
    }


def run(
    config: Config, *, collect: bool = False, scheduled: bool = False, dry_run: bool = False
) -> dict[str, Any]:
    initialize(config.root)
    folder = _folder(config.root)
    folder.mkdir(exist_ok=True)
    with Store(private_path(config.root, "workflow-control")).lock():
        return _run(config, collect=collect, scheduled=scheduled, dry_run=dry_run)


def _run(config: Config, *, collect: bool, scheduled: bool, dry_run: bool) -> dict[str, Any]:
    now = datetime.now(UTC)
    identity = uuid.uuid4().hex
    meter = Meter(config, enabled=(collect or scheduled) and not dry_run)
    result: dict[str, Any] = {
        "version": "nse.v2.operational.run.1",
        "run_id": identity,
        "started_at": now.isoformat(),
        "state": "STARTED",
        "collect": meter.enabled,
        "reserved_requests": config.max_requests_per_run if meter.enabled else 0,
        "dry_run": dry_run,
        "source_requests_last_run": 0,
        "stages": [],
        "last_failure": None,
        "automatic_acquisition_enabled": scheduled and config.scheduled_collection_enabled,
        "inference_schedule_enabled": scheduled and config.scheduled_collection_enabled,
    }
    stage = "preflight"
    try:
        if scheduled:
            scheduled_approval(config)
        if config.permission_reference != PERMISSION:
            raise ValueError("V2_PRIVATE_RESEARCH_PERMISSION_REQUIRED")
        policy(config)
        stage = "clock"
        clock = guard()
        result["clock"] = clock
        result["control_lower_at"] = clock["lower_at"]
        result["control_upper_at"] = clock["upper_at"]
        result["quota_day"] = clock["session_date"]
        lower = datetime.fromisoformat(clock["lower_at"])
        upper = datetime.fromisoformat(clock["upper_at"])
        stage = "quota"
        starts = _history(config.root, "start")
        collected = [r for r in starts if r["collect"]]
        if any(
            datetime.fromisoformat(r.get("control_lower_at", r["started_at"])) > upper
            for r in collected
        ):
            raise ValueError("V2_OPERATIONAL_CLOCK_ROLLBACK")
        if (
            meter.enabled
            and sum(
                r.get(
                    "quota_day",
                    str(datetime.fromisoformat(r["started_at"]).astimezone(IST).date()),
                )
                == clock["session_date"]
                for r in collected
            )
            >= config.max_runs_per_day
        ):
            raise ValueError("V2_DAILY_REQUEST_QUOTA_EXHAUSTED")
        if (
            meter.enabled
            and collected
            and (
                lower
                - max(
                    datetime.fromisoformat(r.get("control_upper_at", r["started_at"]))
                    for r in collected
                )
            ).total_seconds()
            < config.cooldown_minutes * 60
        ):
            raise ValueError("V2_COLLECTION_COOLDOWN_ACTIVE")
        _record(config.root, result, identity + ".start.json")
        stage = "clock"
        result["stages"].append(
            {
                "stage": stage,
                "state": "PASS",
                "message": "Independent date bounds agree; source timestamps are unchanged.",
            }
        )
        stage = "source"
        dataset = data.load_current(config.root)
        plan = _plan(config, dataset, clock, meter)
        result["plan"] = {k: v for k, v in plan.items() if k != "reply"}
        if plan["state"] == "CAPTURE_REQUIRED" and meter.enabled:
            dataset = data.closed_current(
                config.root,
                config.provider_root,
                session_date=date.fromisoformat(plan["day"]),
                client_factory=meter.factory,
                session_reply=plan["reply"],
            )
            plan["state"] = (
                "PUBLICATION_PENDING"
                if dataset.get("collection_pending")
                else "SOURCE_SESSION_COMPLETE"
            )
        elif plan["state"] == "CAPTURE_REQUIRED":
            plan["state"] = "COLLECTION_READY_REQUIRES_EXPLICIT_RUN"
        result["stages"].append(
            {
                "stage": stage,
                "state": plan["state"],
                "message": "One bounded source-qualified session at most; no invented candles.",
            }
        )
        stage = "quality"
        dataset = data.load_current(config.root)
        latest = dataset["sessions"][-1]
        coverage = sum(r["session"] == latest for r in dataset["rows"])
        result["latest_observation_date"] = latest
        result["source_session_coverage"] = coverage
        result["stages"].append(
            {
                "stage": stage,
                "state": "PASS" if coverage == 50 else "PUBLICATION_PENDING",
                "message": f"{coverage}/50 observations; action/feature exclusions stay separate.",
            }
        )
        output = (
            config.root / "price-only"
            if (config.root / "price-only/evaluation.json").exists()
            else config.root
        )
        report = pipeline.verified(output / "evaluation.json")
        model = models.load_model(output / "model.json", report["model_sha256"])
        if dry_run:
            frame = build(
                dataset["rows"],
                dataset["sessions"],
                dataset["quality"]["excluded_sessions"],
                include_context=len(model["feature_names"]) == 20,
            )
            result["eligible_vectors"] = sum(r.session == latest for r in frame.samples)
            result["prospective"] = summary(output)
        else:
            stage = "reconciliation"
            result["reconciliation"] = pipeline.reconcile_saved(config.root, dataset)
            stage = "inference"
            next_open = dataset.get("next_session_timing", {}).get("open_at")
            if (
                coverage == 50
                and plan["state"] in ("SOURCE_SESSION_COMPLETE", "NON_TRADING_SESSION")
                and next_open
                and datetime.fromisoformat(next_open) > datetime.fromisoformat(clock["upper_at"])
            ):
                result["inference"] = {
                    k: v
                    for k, v in pipeline.infer(config.root).items()
                    if k in ("forecast_write", "replayed", "gap")
                }
            else:
                result["inference"] = {
                    "state": "NO_NEW_ELIGIBLE_FUTURE_ENTRY",
                    "backdated_forecasts": 0,
                }
            result["prospective"] = summary(output)
        result["state"] = (
            "PUBLICATION_PENDING"
            if coverage != 50 or plan["state"] == "PUBLICATION_PENDING"
            else plan["state"]
        )
        result["next_action"] = (
            "Review saved research; collect the next official session after close. "
            "Missed entries are never backdated."
        )
        result["stages"].append(
            {
                "stage": "research",
                "state": "DRY_RUN_VERIFIED" if dry_run else "PASS",
                "message": "Experimental research evidence; accepted rankings stay isolated.",
            }
        )
    except Exception as error:
        code = str(error)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{3,120}", code):
            code = "V2_OPERATIONAL_STAGE_FAILED"
        result["state"] = "FAILED"
        result["last_failure"] = {
            "at": datetime.now(UTC).isoformat(),
            "stage": stage,
            "code": code,
            "message": (
                "The update stopped safely. Check credentials, clock, publication and the stage. "
                "No replacement data or forecasts were generated."
            ),
        }
        result["next_action"] = (
            "Resolve the named prerequisite, then rerun within the approved cooldown and quota."
        )
    result["source_requests_last_run"] = meter.calls
    result["completed_at"] = datetime.now(UTC).isoformat()
    if result["state"] != "FAILED":
        result["last_success_at"] = result["completed_at"]
    _record(config.root, result, identity + ".done.json")
    return result
