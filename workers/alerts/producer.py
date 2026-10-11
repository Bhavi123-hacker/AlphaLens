"""Bounded persisted evidence readers. Never runs ingestion, models or paper execution."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_data.daily.providers import assessment, check_source
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.normalization import checksum
from alphalens_portfolio.paper_storage import load as load_paper
from alphalens_portfolio.valuation import PortfolioSnapshot

from .contracts import Event, FreshnessEvidence
from .store import AlertError, AlertStore, timestamp


def reasons(values: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            {v for v in values if isinstance(v, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", v)}
        )
    )[:40]


def receipt_events(row: dict[str, Any]) -> list[Event]:
    run_id = row["run_id"]
    mode = row["mode"]
    codes = []
    state = row["state"]
    if state == "BLOCKED_SOURCE":
        codes.append("SOURCE_BLOCKED")
    elif state == "FAILED":
        codes.append("PIPELINE_FAILED")
    elif state == "BLOCKED_EVIDENCE":
        codes.append("POLICY_REJECTED")
    elif state in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        codes.append("PIPELINE_COMPLETED")
        if state == "COMPLETED_WITH_WARNINGS":
            codes.append("PIPELINE_WARNINGS")
        counts = row["counts"]
        if counts.get("counts", {}).get("VALID", 0):
            codes.append("DATA_VALIDATED")
        if counts.get("counts", {}).get("REJECTED", 0) or counts.get("quarantined", 0):
            codes.append("DATA_REJECTED")
        if counts.get("missing"):
            codes.append("DATA_MISSING")
    if row["inference_status"] == "UNAVAILABLE":
        codes.append("INFERENCE_BLOCKED")
    if row["ranking_status"] == "UNAVAILABLE" or row["signal_status"] == "UNAVAILABLE":
        codes.append("POLICY_REJECTED")
    codes = list(dict.fromkeys(codes))
    why = reasons(row["reasons"])
    changed = checksum(stable_json([row["identity"]["provider"], why, mode]))
    events = [
        Event(
            code=code,
            component="P19",
            evidence_ref=f"receipt:{run_id}",
            evidence_sha256=row["receipt_sha256"],
            event_at=row["completed_at"],
            time_basis="PERSISTED_EVENT_TIME",
            run_id=run_id,
            session=row["session"],
            classification=row["usage_classification"],
            final_vintage=row["final_vintage"],
            mode=mode,
            reasons=why,
            group=f"P19:{mode}:{code}",
            identity=changed
            if code in {"SOURCE_BLOCKED", "INFERENCE_BLOCKED", "POLICY_REJECTED"}
            else run_id,
        )
        for code in codes
    ]
    events.append(
        events[0].model_copy(
            update={
                "code": "PIPELINE_STARTED",
                "event_at": datetime.fromisoformat(row["started_at"]),
                "identity": run_id,
                "group": f"P19:{mode}:PIPELINE_STARTED",
            }
        )
    )
    if "RETRY_LIMIT_EXCEEDED" in why:
        events.append(
            events[0].model_copy(
                update={
                    "code": "RETRY_LIMIT",
                    "identity": run_id,
                    "group": f"P19:{mode}:RETRY_LIMIT",
                }
            )
        )
    return events


def process_daily(alerts: AlertStore, root: Path, *, now: datetime | None = None) -> dict[str, int]:
    """One validated receipt/checkpoint at a time; cursors are committed with alerts."""
    daily = Store(root)
    paths = sorted((daily.root / "runs").glob("*/request.json"))
    if len(paths) > 1000:
        raise AlertError("P19_INDEX_ARCHIVE_REQUIRED")
    result = dict(sources=0, published=0, invalid=0)
    clock = now or datetime.now(UTC)
    for path in paths:
        run_id = path.parent.name
        if not re.fullmatch("[a-f0-9]{64}", run_id):
            raise AlertError("P19_RUN_ID_INVALID")
        try:
            request = daily.read(run_id, "request.json")
            if (
                request.get("mode") not in {"DAILY", "HISTORICAL_REPLAY", "TEST_ONLY"}
                or checksum(
                    stable_json({k: v for k, v in request.items() if k != "source_received_at"})
                )
                != run_id
            ):
                raise AlertError("P19_REQUEST_IDENTITY_INVALID")
        except (DataContractError, OSError, ValueError, AttributeError, TypeError):
            # Integrity diagnostics are operational observations, not accepted market evidence.
            # Original market classification is unknown; this is a detector observation only.
            identity = checksum(stable_json([run_id, "REQUEST_INTEGRITY_FAILURE"]))
            event = Event(
                code="INTEGRITY_FAILURE",
                component="P19",
                evidence_ref=f"request-check:{run_id}",
                evidence_sha256=identity,
                event_at=clock,
                time_basis="DETECTOR_OBSERVATION_TIME",
                run_id=run_id,
                classification="UNVERIFIED_OPERATIONAL_EVIDENCE",
                mode="RECORDED",
                reasons=("SOURCE_CLASSIFICATION_UNVERIFIABLE", "REQUEST_IDENTITY_OR_READ_INVALID"),
                group="P19:INTEGRITY",
                identity=identity,
            )
            result["published"] += alerts.publish(
                f"P19:invalid-request:{run_id}", identity, [event], now=clock
            )
            result["invalid"] += 1
            continue
        source = f"P19:{run_id}"
        if daily.exists(run_id, "receipt.json"):
            try:
                row = daily.receipt(run_id)
                events = receipt_events(row)
                if "canonical" in row["products"]:
                    canonical = daily.read(run_id, row["products"]["canonical"]["file"])
                    if any(
                        v.get("analytical_type") == "UNKNOWN_UNUSABLE" for v in canonical["rows"]
                    ):
                        events.append(
                            events[0].model_copy(
                                update={
                                    "code": "IDENTITY_CONFLICT",
                                    "identity": run_id,
                                    "group": f"P19:{row['mode']}:IDENTITY_CONFLICT",
                                    "reasons": ("PERSISTED_INSTRUMENT_IDENTITY_UNRESOLVED",),
                                }
                            )
                        )
                if "features" in row["products"]:
                    features = daily.read(run_id, row["products"]["features"]["file"])
                    if any(
                        v.get("state") == "UNAVAILABLE"
                        for feature in features["rows"]
                        for v in feature["values"].values()
                    ):
                        events.append(
                            events[0].model_copy(
                                update={
                                    "code": "FEATURE_HISTORY",
                                    "identity": run_id,
                                    "group": f"P19:{row['mode']}:FEATURE_HISTORY",
                                    "reasons": ("PERSISTED_REQUIRED_FEATURES_UNAVAILABLE",),
                                }
                            )
                        )
                retries = sorted(path.parent.glob("retry-*.json"))
                if retries:
                    events.append(
                        events[0].model_copy(
                            update={
                                "code": "RECOVERED",
                                "identity": run_id,
                                "group": "P19:RECOVERED",
                            }
                        )
                    )
                # New alert mappings can replay independently of frozen receipts.
                fingerprint = checksum(stable_json(["p20.producer.v2", row["receipt_sha256"]]))
            except (DataContractError, OSError, ValueError, KeyError, TypeError, AttributeError):
                # Detector observations are evidence; corrupt products remain withheld.
                evidence: dict[str, Any] = dict(
                    version="p20.detector.v1",
                    code="INTEGRITY_FAILURE",
                    run_id=run_id,
                    observed_at=timestamp(clock),
                    reason="P19_SAVED_EVIDENCE_INVALID",
                )
                fingerprint = checksum(stable_json([run_id, "INTEGRITY_FAILURE"]))
                reference = f"detector:{fingerprint}"
                events = [
                    Event(
                        code="INTEGRITY_FAILURE",
                        component="P19",
                        evidence_ref=reference,
                        evidence_sha256=checksum(stable_json(evidence)),
                        event_at=clock,
                        time_basis="DETECTOR_OBSERVATION_TIME",
                        run_id=run_id,
                        session=request["session"],
                        classification="TEST_ONLY"
                        if request["mode"] == "TEST_ONLY"
                        else "RESEARCH_ONLY",
                        mode=request["mode"],
                        reasons=("P19_SAVED_EVIDENCE_INVALID",),
                        group="P19:INTEGRITY",
                        identity=fingerprint,
                    )
                ]
                # Reuse the detector receipt and its original observation clock.
                detector_path = alerts.root / "detectors" / f"{fingerprint}.json"
                if detector_path.exists():
                    evidence = json.loads(detector_path.read_bytes())
                    events[0] = events[0].model_copy(
                        update={
                            "event_at": datetime.fromisoformat(evidence["observed_at"]),
                            "evidence_sha256": checksum(stable_json(evidence)),
                        }
                    )
                else:
                    publish(detector_path, stable_json(evidence))
                result["invalid"] += 1
        else:
            started = (
                daily.read(run_id, "started.json") if daily.exists(run_id, "started.json") else None
            )
            retries = sorted(path.parent.glob("retry-*.json"))
            evidence = dict(
                request=request,
                started=started,
                retries=[daily.read(run_id, p.name) for p in retries],
            )
            fingerprint = checksum(stable_json(evidence))
            base = dict(
                component="P19",
                evidence_ref=f"checkpoint:{run_id}",
                evidence_sha256=fingerprint,
                event_at=datetime.fromisoformat(started["started_at"]) if started else clock,
                time_basis="PERSISTED_EVENT_TIME" if started else "DETECTOR_OBSERVATION_TIME",
                run_id=run_id,
                session=request["session"],
                classification="TEST_ONLY" if request["mode"] == "TEST_ONLY" else "RESEARCH_ONLY",
                mode=request["mode"],
                reasons=("UNPUBLISHED_CHECKPOINT_RECOVERY_REQUIRED",),
                identity=run_id,
            )
            events = [
                Event(code="PUBLICATION_INCOMPLETE", group="P19:PUBLICATION_INCOMPLETE", **base)
            ]
            if started:
                events.append(Event(code="PIPELINE_STARTED", group="P19:PIPELINE_STARTED", **base))
            if len(retries) >= 3:
                events.append(Event(code="RETRY_LIMIT", group="P19:RETRY_LIMIT", **base))
        result["published"] += alerts.publish(source, fingerprint, events, now=clock)
        result["sources"] += 1
    return result


def source_check(
    alerts: AlertStore, *, network: bool = False, now: datetime | None = None
) -> dict[str, Any]:
    clock = now or datetime.now(UTC)
    try:
        status = check_source(network=network)
    except (DataContractError, ValueError, KeyError, TypeError):
        status = check_source()
        status["availability"] = "SOURCE_METADATA_SCHEMA_INVALID"
    revision = status.get("observed_revision")
    if revision is not None and (
        not isinstance(revision, str) or not re.fullmatch("[a-f0-9]{40}", revision)
    ):
        status.pop("observed_revision", None)
        status["availability"] = "SOURCE_METADATA_SCHEMA_INVALID"
    # Public fixed metadata only. The timestamp is retrieval, never exchange publication.
    condition = {
        k: status.get(k)
        for k in ("status", "revision", "observed_revision", "availability", "reasons")
    }
    identity = checksum(stable_json(condition))
    evidence = dict(
        version="p20.source-check.v1", observed_at=timestamp(clock), condition=condition
    )
    path = alerts.root / "source-checks" / f"{identity}.json"
    if path.exists():
        evidence = json.loads(path.read_bytes())
    else:
        publish(path, stable_json(evidence))
    common = dict(
        component="P19",
        evidence_ref=f"source-check:{identity}",
        evidence_sha256=checksum(stable_json(evidence)),
        event_at=evidence["observed_at"],
        time_basis="DETECTOR_OBSERVATION_TIME",
        classification="RESEARCH_ONLY",
        mode="DAILY",
        reasons=reasons(status["reasons"]),
        identity=identity,
    )
    events = [Event(code="SOURCE_BLOCKED", group="P19:DAILY:SOURCE_BLOCKED", **common)]
    if status["availability"] in {
        "SOURCE_UNAVAILABLE_RETRY_LIMIT",
        "SOURCE_METADATA_SCHEMA_INVALID",
    }:
        events.append(Event(code="SOURCE_UNAVAILABLE", group="P19:SOURCE_UNAVAILABLE", **common))
    if status.get("observed_revision") and status["observed_revision"] != status["revision"]:
        events.append(Event(code="SOURCE_REVISION", group="P19:SOURCE_REVISION", **common))
    status["alerts_published"] = alerts.publish("P19:source-check", identity, events, now=clock)
    return status


def process_paper(alerts: AlertStore, path: Path, *, test_only: bool = False) -> int:
    if path.stat().st_size > 5_000_000:
        raise AlertError("PAPER_INPUT_SIZE_LIMIT")
    state = load_paper(path)
    if state.classification == "TEST_ONLY_PAPER" and not test_only:
        raise AlertError("TEST_ONLY_PAPER_IMPORT_BLOCKED")
    events = []
    orders = {o.order_id: o for o in state.orders}
    common = dict(
        component="P16",
        evidence_ref=f"paper-state:{state.state_id}",
        evidence_sha256=state.state_id,
        time_basis="PERSISTED_EVENT_TIME",
        classification=state.classification,
        mode="RECORDED",
    )
    for event in state.events:
        order = orders[event.order_id]
        code = "PAPER_FAILURE" if event.state in {"REJECTED", "NO_FILL"} else "PAPER_ORDER"
        events.append(
            Event(
                code=code,
                event_at=event.recorded_at,
                security_id=order.security_id,
                session=order.decision_session,
                reasons=(f"PAPER_STATE_{event.state}",),
                identity=event.event_id,
                group=f"P16:{order.order_id}:{code}",
                **common,
            )
        )
    for fill in state.fills:
        events.append(
            Event(
                code="PAPER_FILL",
                event_at=fill.simulated_at,
                session=fill.session,
                security_id=orders[fill.order_id].security_id,
                identity=fill.fill_id,
                group=f"P16:{fill.order_id}:PAPER_FILL",
                **common,
            )
        )
    for report in state.reports:
        if report.valuation.unavailable_positions or report.valuation.stale_positions:
            events.append(
                Event(
                    code="VALUATION_UNRESOLVED",
                    event_at=report.knowledge_cutoff,
                    session=report.session,
                    identity=report.report_id,
                    group="P15:VALUATION_UNRESOLVED",
                    **common,
                )
            )
    # Bound batches while preserving per-event identities across evolving checkpoints.
    total = 0
    for offset in range(0, len(events), 500):
        total += alerts.publish(
            f"P16:{state.state_id}:{offset}", state.state_id, events[offset : offset + 500]
        )
    return total


def process_valuation(alerts: AlertStore, path: Path, *, test_only: bool = False) -> int:
    if path.stat().st_size > 5_000_000:
        raise AlertError("VALUATION_INPUT_SIZE_LIMIT")
    snapshot = PortfolioSnapshot.model_validate_json(path.read_bytes())
    if snapshot.snapshot_id != path.stem:
        raise AlertError("VALUATION_FILE_IDENTITY_INVALID")
    is_test = snapshot.market_classification.value == "TEST_ONLY"
    if is_test and not test_only:
        raise AlertError("TEST_ONLY_VALUATION_IMPORT_BLOCKED")
    classification = "TEST_ONLY" if is_test else "RESEARCH_ONLY"
    common = dict(
        component="P15",
        evidence_ref=f"valuation:{snapshot.snapshot_id}",
        evidence_sha256=snapshot.snapshot_id,
        event_at=snapshot.knowledge_cutoff,
        time_basis="PERSISTED_EVENT_TIME",
        session=snapshot.session,
        classification=classification,
        mode="TEST_ONLY" if is_test else "RECORDED",
    )
    events = []
    for position in snapshot.positions:
        if position.freshness in {"UNAVAILABLE", "UNRESOLVED", "STALE"}:
            events.append(
                Event(
                    code="VALUATION_UNRESOLVED",
                    security_id=position.accounting.security_id,
                    identity=checksum(
                        stable_json([snapshot.snapshot_id, position.accounting.security_id])
                    ),
                    group="P15:VALUATION_UNRESOLVED",
                    reasons=reasons(position.reasons),
                    **common,
                )
            )
        elif position.quality != "VALID":
            events.append(
                Event(
                    code="HOLDING_QUALITY",
                    security_id=position.accounting.security_id,
                    identity=checksum(
                        stable_json([snapshot.snapshot_id, position.accounting.security_id])
                    ),
                    group="P15:HOLDING_QUALITY",
                    reasons=reasons(position.reasons),
                    **common,
                )
            )
    return alerts.publish(f"P15:{snapshot.snapshot_id}", snapshot.snapshot_id, events)


def check_freshness(
    alerts: AlertStore,
    evidence_path: Path,
    daily_root: Path,
    *,
    test_only: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    if evidence_path.stat().st_size > 100_000:
        raise AlertError("FRESHNESS_INPUT_SIZE_LIMIT")
    payload = evidence_path.read_bytes()
    digest = checksum(payload)
    if evidence_path.stem != digest:
        raise AlertError("FRESHNESS_FILE_CHECKSUM_INVALID")
    evidence = FreshnessEvidence.model_validate_json(payload)
    clock = now or datetime.now(UTC)
    is_test = evidence.classification == "TEST_ONLY"
    if is_test and not test_only:
        raise AlertError("TEST_ONLY_FRESHNESS_IMPORT_BLOCKED")
    # Caller-written flags cannot clear real source permissions. Current registry remains blocked.
    if not is_test and (not assessment().allowed("DAILY") or evidence.provider != assessment()):
        return {"status": "BLOCKED_SOURCE", "alerts_published": 0}
    if evidence.session.known_at > clock or evidence.release_window_known_at > clock:
        return {"status": "CALENDAR_OR_RELEASE_WINDOW_NOT_YET_KNOWN", "alerts_published": 0}
    if evidence.session.status != "TRADING":
        return {"status": "NON_TRADING_SESSION", "alerts_published": 0}
    if clock <= evidence.expected_available_at:
        return {"status": "RELEASE_WINDOW_PENDING", "alerts_published": 0}
    rows = Store(daily_root).receipts()
    mode = "TEST_ONLY" if is_test else "DAILY"
    observed = any(
        r["mode"] == mode
        and r["session"] == evidence.session.session.isoformat()
        and r["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
        for r in rows
    )
    if observed:
        return {"status": "OBSERVED", "alerts_published": 0}
    event = Event(
        code="SESSION_DELAYED",
        component="P19",
        evidence_ref=f"freshness:{digest}",
        evidence_sha256=digest,
        event_at=clock,
        time_basis="DETECTOR_OBSERVATION_TIME",
        session=evidence.session.session,
        classification=evidence.classification,
        mode=mode,
        group="P19:SESSION_DELAYED",
        identity=digest,
        reasons=("DOCUMENTED_RELEASE_WINDOW_EXCEEDED", "VERIFIED_TRADING_SESSION_NOT_OBSERVED"),
    )
    return {
        "status": "EXPECTED_SESSION_NOT_OBSERVED",
        "alerts_published": alerts.publish(f"P19:freshness:{digest}", digest, [event], now=clock),
    }


def inspect_lock(
    alerts: AlertStore, daily_root: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """One-shot kernel-lock probe, never stops or runs a worker."""
    if not daily_root.is_dir():
        raise AlertError("P19_ROOT_NOT_CONFIGURED")
    scope = checksum(str(daily_root.resolve()).encode())
    clock = now or datetime.now(UTC)
    try:
        with Store(daily_root).lock():
            return {"status": "AVAILABLE_AT_PROBE_TIME", "alerts_published": 0}
    except DataContractError as exc:
        if str(exc) != "DAILY_WORKER_BUSY":
            raise
    event = Event(
        code="WORKER_LOCK",
        component="P19",
        evidence_ref=f"lock-probe:{scope}",
        evidence_sha256=checksum(stable_json([scope, "DAILY_WORKER_BUSY"])),
        event_at=clock,
        time_basis="DETECTOR_OBSERVATION_TIME",
        classification="RESEARCH_ONLY",
        mode="RECORDED",
        reasons=("DAILY_WORKER_BUSY",),
        group="P19:WORKER_LOCK",
        identity=scope,
    )
    return {
        "status": "DAILY_WORKER_BUSY",
        "alerts_published": alerts.publish(
            f"P19:lock:{scope}", "LOCK_CONFLICT", [event], now=clock
        ),
    }
