"""Authenticated exploratory archival diagnostics, no current recommendations or model runs."""

import threading
import time
from collections import OrderedDict
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import JsonValue
from workers.daily.inference import input_compatibility
from workers.intelligence.methods import FIELDS, drift, number, regime, reliability

from .artifacts import confined
from .core.domain_errors import APIError
from .routes import Research, dates
from .schemas import Envelope
from .services import ResearchService
from .visual import build_market, snapshot_rows

router = APIRouter(prefix="/api/v1/intelligence", tags=["exploratory research intelligence"])


class WindowRead:
    """Two bounded immutable-source windows, one projection per partition for all sessions."""

    def __init__(self, service: ResearchService) -> None:
        self.service = service
        self.lock = threading.Lock()
        self.cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

    def read(self, selected: date | None, count: int) -> dict[str, Any]:
        reader = self.service.reader
        canonical = reader.manifest("canonical-manifest.json")
        feature = reader.manifest("supervised-manifest.json")
        calendar = reader.calendar()["sessions"]
        observed = [
            s["session_date"] for s in calendar if s["price_status"] == "SOURCE_ROWS_PRESENT"
        ]
        day = str(selected) if selected else max(observed)
        if day not in observed:
            raise APIError("SESSION_NOT_OBSERVED", "Choose an observed archive session.", 422)
        end = observed.index(day)
        selected_days = observed[max(0, end - count + 1) : end + 1]
        all_days = [s["session_date"] for s in calendar]
        first_index = all_days.index(selected_days[0])
        read_start = all_days[max(0, first_index - 1)]
        root = reader.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "Archive is unavailable.")
        fingerprint = tuple(
            (str(p), p.stat().st_size, p.stat().st_mtime_ns, e["sha256"])
            for m in (canonical, feature)
            for e in m["identity"]["files"]
            if (p := confined(root, e["path"]))
        )
        key = (day, count, canonical["dataset_id"], feature["dataset_id"], fingerprint)
        if not self.lock.acquire(blocking=False):
            raise APIError("READ_CAPACITY", "Research intelligence read is occupied.", 429)
        try:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            history: dict[str, list[dict[str, Any]]] = {}
            features: dict[str, dict[str, dict[str, Any]]] = {d: {} for d in selected_days}
            deadline = time.monotonic() + reader.settings.query_timeout_seconds
            for entry in canonical["identity"]["files"]:
                with reader.budget(wait_seconds=5):
                    path = reader.verify(confined(root, entry["path"]), entry["sha256"], deadline)
                    rows, more = snapshot_rows(
                        path,
                        [
                            "security_id",
                            "session_date",
                            "symbol",
                            "isin",
                            "name",
                            "analytical_type",
                            "close",
                            "volume",
                            "quality",
                            "quality_reasons",
                        ],
                        None,
                        date.fromisoformat(read_start),
                        date.fromisoformat(day),
                        50000,
                        0,
                        deadline,
                    )
                if more:
                    raise APIError(
                        "RESPONSE_LIMIT", "Intelligence partition exceeds bounded scope.", 422
                    )
                for row in rows:
                    history.setdefault(row["security_id"], []).append(row)
                if len(history) > 20000 or sum(map(len, history.values())) > 220000:
                    raise APIError("RESPONSE_LIMIT", "Observed window exceeds memory scope.", 422)
            supported = [f for f in FIELDS if f in feature["identity"]["feature_columns"]]
            for entry in feature["identity"]["files"]:
                with reader.budget(wait_seconds=5):
                    path = reader.verify(confined(root, entry["path"]), entry["sha256"], deadline)
                    rows, more = snapshot_rows(
                        path,
                        [
                            "security_id",
                            "session_date",
                            *supported,
                            *(f + "__state" for f in supported),
                        ],
                        None,
                        date.fromisoformat(selected_days[0]),
                        date.fromisoformat(day),
                        50000,
                        0,
                        deadline,
                    )
                if more:
                    raise APIError("RESPONSE_LIMIT", "Feature window exceeds bounded scope.", 422)
                for row in rows:
                    target = features.get(str(row["session_date"]))
                    if target is not None:
                        if row["security_id"] in target:
                            raise APIError("IDENTITY_CONFLICT", "Duplicate feature identity.", 409)
                        target[row["security_id"]] = row
            snapshots = []
            for selected_day in selected_days:
                i = all_days.index(selected_day)
                snapshot = build_market(
                    history,
                    features[selected_day],
                    selected_day,
                    all_days[i - 1] if i else None,
                    supported,
                    [d for d in all_days if read_start <= d <= selected_day],
                )
                snapshots.append(snapshot)
            result = {
                "snapshots": snapshots,
                "available_sessions": observed,
                "dataset_id": canonical["dataset_id"],
                "feature_dataset_id": feature["dataset_id"],
                "projection_seconds": round(
                    reader.settings.query_timeout_seconds - (deadline - time.monotonic()), 6
                ),
            }
            self.cache[key] = result
            while len(self.cache) > 2:
                self.cache.popitem(last=False)
            return result
        finally:
            self.lock.release()


def window(service: ResearchService, selected: date | None, count: int) -> dict[str, Any]:
    return service.intelligence_window.read(selected, count)


@router.get("/regime")
def market_regime(
    service: Research, session: date | None = None, sessions: int = Query(5, ge=1, le=10)
) -> Envelope[JsonValue]:
    data = window(service, session, sessions)
    series = [regime(s["rows"], date.fromisoformat(s["session"])) for s in data["snapshots"]]
    last = data["snapshots"][-1]
    pit = regime(last["rows"], date.fromisoformat(last["session"]), strict_pit=True)
    quality = regime(
        [r for r in last["rows"] if r["quality"] == "VALID"], date.fromisoformat(last["session"])
    )
    return service.response(
        {
            "timeline": series,
            "strict_pit": pit,
            "valid_only_sensitivity": quality,
            "available_sessions": data["available_sessions"],
            "dataset_id": data["dataset_id"],
            "feature_dataset_id": data["feature_dataset_id"],
            "projection_seconds": data["projection_seconds"],
            "current_forecast": "UNAVAILABLE",
            "source": "PINNED_FINAL_VINTAGE_ARCHIVE_NOT_LIVE",
        },
        "P5_P6_EXPLORATORY_ARCHIVAL_REGIME_NOT_P11_POLICY",
        as_of=date.fromisoformat(last["session"]),
    )


@router.get("/drift")
def research_drift(
    service: Research, session: date | None = None, sessions: int = Query(5, ge=2, le=10)
) -> Envelope[JsonValue]:
    data = window(service, session, sessions)
    if len(data["snapshots"]) < 2:
        raise APIError("INSUFFICIENT_SESSIONS", "Two observed sessions are required.")
    first, last = data["snapshots"][0], data["snapshots"][-1]
    result = drift(
        first["rows"],
        last["rows"],
        date.fromisoformat(first["session"]),
        date.fromisoformat(last["session"]),
    )
    result.update({"source": "FINAL_VINTAGE_ARCHIVE_NOT_LIVE", "dataset_id": data["dataset_id"]})
    return service.response(
        result,
        "P6_EMPIRICAL_PAST_REFERENCE_DISTRIBUTION_DIAGNOSTIC",
        as_of=date.fromisoformat(last["session"]),
    )


@router.get("/reliability")
def model_reliability(
    service: Research,
    horizon: int | None = Query(None),
    phase: Literal["development", "2025", "2026"] | None = None,
) -> Envelope[JsonValue]:
    if horizon is not None and horizon not in {1, 5, 10, 20}:
        raise APIError("HORIZON_INVALID", "Use a preserved research horizon.", 422)
    rows = [
        r
        for r in service.reports()
        if (horizon is None or r["horizon"] == horizon) and (phase is None or r["phase"] == phase)
    ]
    return service.response(reliability(rows), "P9_STORED_REPORT_RELIABILITY_NO_EVALUATION_RERUN")


@router.get("/passport/{security_id}")
def passport(
    security_id: str, service: Research, start: date | None = None, end: date | None = None
) -> Envelope[JsonValue]:
    dates(start, end)
    identity = service.catalog.security(security_id)
    last = end or date.fromisoformat(identity["last_observed"])
    try:
        first = last.replace(year=last.year - 1)
    except ValueError:
        first = last.replace(year=last.year - 1, day=28)
    history = service.history(security_id, start or first, last, 10000, 0)
    if history.page and history.page.has_more:
        raise APIError("RESPONSE_LIMIT", "Narrow the passport interval.", 422)
    observed = [p for p in history.data if p.close is not None]
    latest = max(observed, key=lambda p: p.session) if observed else None
    manifest = service.reader.manifest("supervised-manifest.json")
    columns = tuple(manifest["identity"]["feature_columns"])
    vector: dict[str, Any] = {}
    if latest:
        with service.reader.budget(wait_seconds=5) as deadline:
            rows, _ = service.reader.rows(
                service.reader.partition(manifest, security_id, deadline),
                ["security_id", "session_date", *columns, *(f + "__state" for f in columns)],
                security_id,
                latest.session,
                latest.session,
                2,
                0,
                deadline,
            )
        if len(rows) > 1:
            raise APIError("IDENTITY_CONFLICT", "Feature evidence is ambiguous.", 409)
        if rows:
            vector = {
                f: {"value": rows[0].get(f), "state": rows[0].get(f + "__state", "UNAVAILABLE")}
                for f in columns
            }
    compatibility = input_compatibility(columns, vector)
    exposed_vector = {
        name: {**entry, "value": number(entry["value"])} for name, entry in vector.items()
    }
    blockers = [
        {
            "layer": "source",
            "code": "NO_APPROVED_ONGOING_NSE_PROVIDER",
            "evidence": "P28 account/permission/technical gates not cleared",
        },
        {
            "layer": "freshness",
            "code": "ARCHIVED_OBSERVATION_NOT_CURRENT_SESSION",
            "evidence": str(latest.session) if latest else "NO_PRICE_OBSERVATION",
        },
        {
            "layer": "availability",
            "code": "ACTUAL_HISTORICAL_PUBLICATION_AVAILABILITY_UNKNOWN",
            "evidence": "FINAL_VINTAGE_RESEARCH_ASSUMPTION",
        },
        {
            "layer": "actions",
            "code": "CURRENT_CORPORATE_ACTION_BASIS_NOT_VERIFIED",
            "evidence": "RAW_UNADJUSTED prices; complete economic adjustment not established",
        },
        {
            "layer": "model",
            "code": "INDEPENDENT_MODEL_ACCEPTANCE_NOT_PASSED",
            "evidence": "Frozen candidates remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE",
        },
        {
            "layer": "peers",
            "code": "FRESH_CONTEMPORANEOUS_PEER_UNIVERSE_UNAVAILABLE",
            "evidence": "Archived percentiles do not establish new-session peer coverage",
        },
        {
            "layer": "policy",
            "code": "CURRENT_RISK_RANK_SIGNAL_EVIDENCE_UNAVAILABLE",
            "evidence": "Unchanged P11-P14 acceptance requirements",
        },
    ]
    blockers.extend(
        {"layer": "features", "code": code, "evidence": feature}
        for feature, code in compatibility["excluded"].items()
    )
    data = {
        "version": "p29.evidence-passport.v1",
        "security_id": security_id,
        "identity": identity,
        "observed_identity": {"symbol": latest.symbol, "isin": latest.isin} if latest else None,
        "exchange": "NSE_ARCHIVE_SOURCE_CONTEXT_NOT_NEW_PROVIDER_VERIFICATION",
        "source": "PINNED_TEJHQ_FINAL_VINTAGE",
        "latest_observed_session": str(latest.session) if latest else None,
        "latest_stored_session": identity["last_observed"],
        "price_basis": "RAW_UNADJUSTED",
        "freshness": "HISTORICAL_NOT_LIVE",
        "selected_slots": len(history.data),
        "observed_prices": len(observed),
        "missing_slots": len(history.data) - len(observed),
        "usable_prices": sum(p.quality in {"VALID", "DEGRADED"} for p in observed),
        "quality_counts": {
            q: sum(p.quality == q for p in history.data)
            for q in sorted({p.quality for p in history.data})
        },
        "quality_reasons": sorted({r for p in history.data for r in p.quality_reasons}),
        "corporate_actions": "UNAVAILABLE_FOR_CURRENT_ECONOMIC_ADJUSTMENT",
        "calendar": "OBSERVED_SOURCE_SLOTS_NOT_COMPLETE_OFFICIAL_CALENDAR",
        "feature_dataset_id": manifest["dataset_id"],
        "feature_count": len(columns),
        "features": exposed_vector,
        "feature_compatibility": compatibility,
        "model_artifacts": [
            {
                "horizon": r["horizon"],
                "family": r.get("model_family", "UNAVAILABLE"),
                "model_run_id": r["model_run_id"],
                "sha256": r.get("model_sha256"),
                "acceptance": "NOT_PASSED",
            }
            for r in service.reports()
            if r["phase"] == "2026"
        ],
        "blockers": blockers,
        "current_shortlist": "UNAVAILABLE",
        "evidence_confidence_percentage": None,
        "classification": "TEST_ONLY"
        if service.reader.settings.test_only_evidence
        else "RESEARCH_ONLY_FINAL_VINTAGE_NOT_PIT",
    }
    return service.response(
        data,
        "P5_P6_P9_EVIDENCE_PASSPORT_NO_SCORE_OR_RECOMMENDATION",
        security_id,
        as_of=latest.session if latest else None,
    )
