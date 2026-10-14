"""Explicitly enabled local operator records. Original financial APIs remain GET-only."""

import json
import sqlite3
import time
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from pydantic import JsonValue
from workers.alerts.contracts import Event
from workers.alerts.store import AlertStore
from workers.personal.analytics import (
    candidate,
    mark,
    observed,
    portfolio_review,
    preference_match,
    provider_request_failed,
    simulate,
)
from workers.personal.contracts import (
    UNSUPPORTED,
    AlertRule,
    JournalEntry,
    ManualEntry,
    NamedList,
    Profile,
    Scenario,
)
from workers.personal.store import PersonalStore, encode
from workers.providers.store import ProviderStore
from workers.providers.upstox import UpstoxClient
from workers.providers.upstox_terminal import IST, _lock, master, selected
from workers.providers.watchlist import cached, load

from alphalens_portfolio.accounting import reconstruct
from alphalens_portfolio.contracts import Ledger

from .core.domain_errors import APIError
from .providers import private_root
from .routes import Research
from .schemas import Classification, Envelope
from .services import response

router = APIRouter(prefix="/api/v1/personal", tags=["single local operator research records"])


def configured_router(enabled: bool) -> APIRouter:
    result = APIRouter()
    for route in router.routes:
        if enabled or "POST" not in getattr(route, "methods", set()):
            result.routes.append(route)
    return result


def store(request: Request) -> PersonalStore:
    root = request.app.state.settings.personal_root
    operator = request.state.operator
    if not root:
        raise APIError(
            "PERSONAL_WORKSPACE_NOT_INITIALIZED",
            "Initialize the owned local research workspace.",
            503,
        )
    if operator.get("role") != "ADMIN":
        raise APIError("PERSONAL_OWNER_REQUIRED", "The authorized local operator is required.", 403)
    return PersonalStore(root, operator["account_id"])


def wrap(data: Any) -> Envelope[JsonValue]:
    return response(data, "LOCAL_OPERATOR_RECORDS_AND_EXPLICIT_DESCRIPTIVE_EVIDENCE").model_copy(
        update={
            "version": "p32.personal.v1",
            "classification": Classification(
                data_reality="USER_RECORDED_AND_SCOPED_DESCRIPTIVE_EVIDENCE",
                usage_classification="LOCAL_OPERATOR_RESEARCH",
                final_vintage=None,
                research_profile=None,
            ),
            "quality_status": "USER_RECORDS_NOT_BROKER_VERIFIED_MARKS_UNRECONCILED",
        }
    )


def safe(call: Any) -> Any:
    try:
        return call()
    except (ValueError, OSError, sqlite3.Error) as exc:
        code = str(exc)
        if code.startswith("NO_SHORT_SELLING:"):
            raise APIError(
                "INSUFFICIENT_OWNED_SHARES", "Sale quantity exceeds recorded owned shares.", 422
            ) from None
        if code.startswith("NO_OVERDRAFT:"):
            raise APIError(
                "INSUFFICIENT_RECORDED_CASH",
                "Record genuine cash funding first, or use an acquisition lot "
                "when funding history is untracked.",
                422,
            ) from None
        allowed = {
            "PERSONAL_OWNER_MISMATCH",
            "PERSONAL_REVISION_CONFLICT",
            "PERSONAL_RECORD_NOT_FOUND",
            "IMMUTABLE_MANUAL_EVENT_CONFLICT",
            "FUTURE_MANUAL_EVENT_REJECTED",
            "KNOWN_FEES_CONFIRMATION_REQUIRED",
            "NSE_WHOLE_SHARE_QUANTITY_REQUIRED",
            "MANUAL_LEDGER_EVENT_LIMIT",
            "VERIFIED_MANUAL_IDENTITY_REQUIRED",
            "TARGET_WEIGHTS_EXCEED_100_PERCENT",
            "HYPOTHETICAL_NO_SHORT_SELLING",
            "SHOCK_RANGE_MINUS100_TO100_REQUIRED",
            "WHOLE_SHARE_SCENARIO_REQUIRED",
            "MANUAL_CLOCK_BEHIND_LAST_RECORD",
        }
        known = code if code in allowed else "PERSONAL_RECORD_VALIDATION_FAILED"
        raise APIError(
            known,
            "Record rejected. Check identity, dates, owned quantities, "
            "recorded cash funding, fees and current revision.",
            403
            if code == "PERSONAL_OWNER_MISMATCH"
            else 409
            if "CONFLICT" in code
            else 404
            if code == "PERSONAL_RECORD_NOT_FOUND"
            else 422,
        ) from None


async def body(request: Request) -> dict[str, Any]:
    if not request.app.state.settings.personal_mutations or request.headers.getlist(
        "x-alphalens-local"
    ) != ["p32"]:
        raise APIError(
            "PERSONAL_WRITE_CONTEXT_REQUIRED",
            "Explicitly enabled local operator controls are required.",
            403,
        )
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 65536:
            raise APIError("PERSONAL_BODY_LIMIT", "Narrow the user record payload.", 413)
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        value = json.loads(data, object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise APIError("INVALID_REQUEST", "Use one bounded JSON object.", 422) from None


def verified(service: Research, key: str) -> dict[str, Any]:
    root = private_root(service)
    with _lock:
        return selected(
            master(root, UpstoxClient(ProviderStore(root), budget=1), datetime.now(UTC)), key
        ).model_dump(mode="json")


def profile(request: Request) -> Profile:
    return Profile.model_validate(store(request).profile()["value"])


@router.get("/workspace")
def workspace(request: Request) -> Envelope[JsonValue]:
    def read() -> dict[str, Any]:
        owned = store(request)
        portfolios = [
            {
                "id": p["id"],
                "revision": p["revision"],
                "updated_at": p["updated_at"],
                "name": p["value"]["ledger"]["portfolio"]["portfolio_name"],
                "event_count": len(p["value"]["ledger"]["transactions"]),
            }
            for p in owned.listing("portfolios")
        ]
        return {
            "profile": owned.profile(),
            "portfolios": portfolios,
            "watchlists": owned.listing("watchlists"),
            "journal": owned.listing("journal"),
            "rules": owned.listing("rules"),
            "recent": owned.listing("recent")[:30],
            "mutations_enabled": request.app.state.settings.personal_mutations,
            "single_operator": True,
            "unsupported": list(UNSUPPORTED),
            "current_eligible_ml_predictions": 0,
            "automatic_acquisition": False,
            "outbound_notifications": False,
        }

    return wrap(safe(read))


@router.post("/profile")
async def save_profile(request: Request) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"revision", "profile"} or type(value["revision"]) is not int:
        raise APIError("INVALID_REQUEST", "Provide the preference revision and fields.", 422)
    return wrap(
        safe(
            lambda: store(request).save(
                "profile",
                "default",
                Profile.model_validate(value["profile"]).model_dump(),
                value["revision"],
            )
        )
    )


@router.post("/records/{kind}")
async def save_record(
    kind: Literal["watchlists", "journal", "rules"], request: Request, service: Research
) -> Envelope[JsonValue]:
    value = await body(request)
    if (
        set(value) != {"id", "revision", "value"}
        or type(value["revision"]) is not int
        or not isinstance(value["id"], str)
    ):
        raise APIError("INVALID_REQUEST", "Provide a bounded owned record and revision.", 422)
    identity = value["id"] or uuid4().hex
    if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
        raise APIError("INVALID_REQUEST", "Use an owned record identifier.", 422)

    def save() -> dict[str, Any]:
        model = (
            NamedList.model_validate(value["value"])
            if kind == "watchlists"
            else JournalEntry.model_validate(value["value"])
            if kind == "journal"
            else AlertRule.model_validate(value["value"])
        )
        payload = model.model_dump(mode="json")
        keys = payload.get("instrument_keys", []) or (
            [payload["instrument_key"]] if payload.get("instrument_key") else []
        )
        for key in keys:
            verified(service, key)
        if kind == "rules" and payload.get("portfolio_id"):
            store(request).get("portfolios", payload["portfolio_id"])
        return store(request).save(kind, identity, payload, value["revision"])

    return wrap(safe(save))


@router.post("/records/{kind}/{identity}/remove")
async def remove_record(
    kind: Literal["watchlists", "journal", "rules"], identity: str, request: Request
) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"revision"} or type(value["revision"]) is not int:
        raise APIError("INVALID_REQUEST", "Provide the current record revision.", 422)
    safe(lambda: store(request).remove(kind, identity, value["revision"]))
    return wrap({"removed": True})


@router.post("/recent")
async def recent(request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"instrument_key"}:
        raise APIError("INVALID_REQUEST", "Provide a current identity only.", 422)

    def save() -> dict[str, Any]:
        identity = verified(service, value["instrument_key"])
        owned = store(request)
        record_id = sha256(value["instrument_key"].encode()).hexdigest()[:32]
        records = [r for r in owned.listing("recent") if r["id"] == record_id]
        return owned.save(
            "recent", record_id, {"identity": identity}, records[0]["revision"] if records else 0
        )

    return wrap(safe(save))


@router.post("/portfolios")
async def create_portfolio(request: Request) -> Envelope[JsonValue]:
    value = await body(request)
    if set(value) != {"name"}:
        raise APIError("INVALID_REQUEST", "Provide a portfolio name.", 422)
    return wrap(safe(lambda: store(request).create_portfolio(NamedList.model_validate(value).name)))


@router.post("/portfolios/{identity}/entries")
async def record_entry(identity: str, request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)

    def record() -> dict[str, Any]:
        entry = ManualEntry.model_validate(value)
        instrument = verified(service, entry.instrument_key) if entry.instrument_key else None
        return store(request).record(identity, entry, instrument)

    return wrap(safe(record))


def review(request: Request, service: Research, identity: str, refresh: bool) -> dict[str, Any]:
    value = store(request).get("portfolios", identity)["value"]
    keys = tuple(
        sorted(
            {
                t["security_id"].removeprefix("upstox:")
                for t in value["ledger"]["transactions"]
                if t.get("security_id")
            }
        )
    )
    root = private_root(service)
    if refresh and keys:
        load(root, keys[:50])
    return portfolio_review(value, profile(request), cached(root, keys))


@router.get("/portfolios/{identity}")
def portfolio(
    identity: str, request: Request, service: Research, refresh: bool = False
) -> Envelope[JsonValue]:
    return wrap(safe(lambda: review(request, service, identity, refresh)))


@router.post("/portfolios/{identity}/scenario")
async def scenario(identity: str, request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)

    def calculate() -> dict[str, Any]:
        inputs = Scenario.model_validate(value)
        base = review(request, service, identity, False)
        keys = tuple(
            {r["instrument_key"] for r in base["holdings"]}
            | ({inputs.instrument_key} if inputs.instrument_key else set())
        )
        return simulate(base, inputs, cached(private_root(service), keys))

    return wrap(safe(calculate))


@router.get("/candidates")
def candidates(
    request: Request,
    service: Research,
    instrument_keys: str = Query(default="", max_length=1500),
    size: int = Query(default=10, ge=5, le=20),
) -> Envelope[JsonValue]:
    if size not in {5, 10, 20}:
        raise APIError("RESEARCH_SIZE_INVALID", "Choose5,10or20 research rows.", 422)
    keys = tuple(k for k in instrument_keys.split(",") if k)
    if len(keys) > 50:
        raise APIError("COHORT_LIMIT", "Choose at most50 observed identities.", 422)

    def read() -> dict[str, Any]:
        preferences = profile(request)
        items = cached(private_root(service), keys)
        rows = [candidate(items[k], preferences) for k in keys if k in items]
        holdings: set[str] = set()
        if preferences.consider_holdings:
            at = datetime.now(UTC)
            for portfolio in store(request).listing("portfolios"):
                state = reconstruct(
                    Ledger.model_validate(portfolio["value"]["ledger"]),
                    at.astimezone(IST).date(),
                    at,
                )
                holdings.update(
                    p.security_id.removeprefix("upstox:") for p in state.positions if p.quantity > 0
                )
        for row in rows:
            row["existing_recorded_holding"] = row["instrument_key"] in holdings
            if row["existing_recorded_holding"]:
                row["technical_observations"].append(
                    "EXISTING_RECORDED_HOLDING_REVIEW_NOT_NEW_ENTRY_ADVICE"
                )
        matches = [r for r in rows if r["preferences"]["state"] == "MATCHES_SUPPORTED_CONSTRAINTS"]
        matches.sort(
            key=lambda r: (
                r["metrics"]["price_return_percent"] is None,
                -(r["metrics"]["price_return_percent"] or 0),
                r["symbol"],
            )
        )
        return {
            "ranking_type": "DESCRIPTIVE_OBSERVED_MOMENTUM_NOT_PREDICTION",
            "selected_count": len(keys),
            "observed_count": len(items),
            "matches": matches[: min(size, preferences.desired_stocks)],
            "excluded": [r for r in rows if r not in matches],
            "missing_instruments": [k for k in keys if k not in items],
            "current_ml_rankings": "UNAVAILABLE",
            "eligible_prediction_count": 0,
            "source_limits": list(UNSUPPORTED),
        }

    return wrap(safe(read))


@router.get("/comparison")
def comparison(
    request: Request, service: Research, instrument_keys: str = Query(max_length=600)
) -> Envelope[JsonValue]:
    from workers.personal.comparison import compare

    safe(lambda: store(request).profile())
    keys = tuple(dict.fromkeys(k for k in instrument_keys.split(",") if k))
    if not 2 <= len(keys) <= 20:
        raise APIError("COMPARISON_COHORT_BOUND", "Choose2to20selected identities.", 422)
    return wrap(safe(lambda: compare(cached(private_root(service), keys), keys)))


@router.get("/historical-leaders")
def historical_leaders(
    request: Request,
    service: Research,
    start: date,
    end: date,
    securities: str = Query(default="", max_length=4000),
    category: Literal[
        "price_return", "risk_adjusted", "drawdown", "consistency", "low_volatility", "volume"
    ] = "price_return",
    size: int = Query(default=10, ge=5, le=20),
) -> Envelope[JsonValue]:
    if size not in {5, 10, 20}:
        raise APIError("RESEARCH_SIZE_INVALID", "Choose5,10or20 research rows.", 422)
    if start > end or (end - start).days > 1830:
        raise APIError(
            "HISTORICAL_WINDOW_INVALID", "Use a historical window of at most five years.", 422
        )
    keys = list(dict.fromkeys(k for k in securities.split(",") if k))
    if len(keys) > 20:
        raise APIError("HISTORICAL_COHORT_BOUND", "Choose up to20 archive identities.", 422)
    started = time.monotonic()
    preferences = safe(lambda: profile(request))
    rows = []
    # Whole observed archive cohort for supported stored20/60-session metrics;
    # arbitrary windows use explicit selected identities with exact bounded history.
    if not keys:
        snapshot = service.visual_market.snapshot(end)
        feature = (
            "return_20"
            if (end - start).days <= 40
            else "return_60"
            if (end - start).days <= 110
            else None
        )
        if not feature:
            raise APIError(
                "SELECT_HISTORICAL_COHORT",
                "Select archive identities for custom or longer windows.",
                422,
            )
        for row in snapshot["rows"]:
            fields = row
            # Stored row fields are exposed by build_market; missing remains missing.
            metrics = {
                "price_return_percent": fields.get(feature) * 100
                if isinstance(fields.get(feature), (float, int))
                else None,
                "maximum_drawdown_percent": fields.get("drawdown_20") * 100
                if isinstance(fields.get("drawdown_20"), (float, int))
                else None,
                "daily_volatility_percent": fields.get("volatility_20") * 100
                if isinstance(fields.get("volatility_20"), (float, int))
                else None,
                "volume": row.get("volume"),
                "mean_daily_return_over_volatility": None,
                "positive_period_fraction": None,
                "relative_volume": fields.get("volume_ratio_20"),
                "sample_count": 20 if feature == "return_20" else 60,
            }
            rows.append(
                {
                    "security_id": row["security_id"],
                    "symbol": row["symbol"],
                    "metrics": metrics,
                    "preferences": preference_match(preferences, metrics),
                    "window_basis": "STORED_" + feature.upper() + "_NOT_EXACT_CUSTOM_DATES",
                    "source": "P5_P6_FROZEN_ARCHIVE",
                    "as_of": snapshot["session"],
                }
            )
    else:
        for key in keys:
            if time.monotonic() - started > service.reader.settings.query_timeout_seconds:
                raise APIError("QUERY_TIMEOUT", "Narrow the historical cohort/window.", 504)
            history = service.history(key, start, end, 10000, 0)
            metrics = observed([p.model_dump(mode="json") for p in history.data])
            rows.append(
                {
                    "security_id": key,
                    "symbol": service.catalog.security(key)["latest_observed_symbol"],
                    "metrics": metrics,
                    "preferences": preference_match(preferences, metrics),
                    "window_basis": "EXPLICIT_OBSERVED_ARCHIVE_WINDOW",
                    "source": history.source,
                    "artifact_id": history.artifact_id,
                    "as_of": str(history.as_of_session),
                }
            )
    measure = {
        "price_return": "price_return_percent",
        "risk_adjusted": "mean_daily_return_over_volatility",
        "drawdown": "maximum_drawdown_percent",
        "consistency": "positive_period_fraction",
        "low_volatility": "daily_volatility_percent",
        "volume": "relative_volume",
    }[category]
    eligible = [r for r in rows if r["metrics"].get(measure) is not None]
    eligible.sort(
        key=lambda r: (
            (1 if category == "low_volatility" else -1) * r["metrics"][measure],
            r["security_id"],
        )
    )
    return service.response(
        {
            "category": category,
            "measure": measure,
            "start": str(start),
            "end": str(end),
            "observed_cohort": len(rows),
            "comparable_count": len(eligible),
            "leaders": eligible[:size],
            "excluded": [
                {
                    "security_id": r["security_id"],
                    "reason": "REQUIRED_COMPARABLE_METRIC_UNAVAILABLE",
                }
                for r in rows
                if r not in eligible
            ],
            "latency_ms": round((time.monotonic() - started) * 1000),
            "interpretation": (
                "HISTORICAL_HINDSIGHT_RAW_PRICE_DIAGNOSTICS_NOT_TOTAL_PROFIT_OR_FUTURE_PREDICTIONS"
            ),
            "corporate_actions": "UNVERIFIED",
            "cohort": "SELECTED_ARCHIVE_IDENTITIES"
            if keys
            else "OBSERVED_ARCHIVE_COHORT_STORED_WINDOW",
            "full_nse_market": False,
        },
        "CHECKSUM_VERIFIED_HISTORICAL_HINDSIGHT_LEADERS",
    )


@router.post("/rules/evaluate")
async def evaluate_rules(request: Request, service: Research) -> Envelope[JsonValue]:
    value = await body(request)
    if value:
        raise APIError("INVALID_REQUEST", "Evaluation uses cached evidence only.", 422)

    def evaluate() -> dict[str, Any]:
        owned = store(request)
        preferences = profile(request)
        rules = owned.listing("rules")
        now = datetime.now(UTC)
        results = []
        events = []
        for record in rules:
            rule = AlertRule.model_validate(record["value"])
            if not rule.enabled:
                continue
            key = rule.instrument_key
            item = cached(private_root(service), (key,)).get(key) if key else None
            observed_mark = mark(item)
            metrics = observed(item.get("rows", [])[-60:]) if item else observed([])
            q = item["quote"] if item else {}
            threshold = float(rule.threshold)
            actual: float | None = None
            if rule.kind.startswith("PRICE_") and observed_mark["price"] is not None:
                actual = float(observed_mark["price"])
            elif rule.kind.startswith("CHANGE_") and q.get("state") == "VALIDATED_SNAPSHOT":
                actual = float(q["change_percent"]) if q.get("change_percent") is not None else None
            elif rule.kind == "VOLUME_ABOVE":
                actual = metrics.get("volume")
            elif rule.kind == "VOLATILITY_ABOVE":
                actual = metrics.get("daily_volatility_percent")
            elif rule.kind == "DRAWDOWN_BELOW":
                actual = (
                    abs(metrics["maximum_drawdown_percent"])
                    if metrics.get("maximum_drawdown_percent") is not None
                    else None
                )
            elif rule.kind.startswith("RSI_") and item:
                actual = candidate(item, preferences)["metrics"]["rsi_14"]
            elif rule.kind == "CONCENTRATION_ABOVE" and rule.portfolio_id:
                data = review(request, service, rule.portfolio_id, False)
                matches = [h for h in data["holdings"] if not key or h["instrument_key"] == key]
                actual = max((h["cost_allocation_percent"] for h in matches), default=None)
            elif rule.kind == "STALE_DATA" and observed_mark["session"]:
                actual = (
                    now.astimezone(IST).date()
                    - date.fromisoformat(str(observed_mark["session"])[:10])
                ).days
            elif rule.kind == "PROVIDER_UNAVAILABLE":
                failure = provider_request_failed(item)
                actual = None if failure is None else int(failure)
            elif rule.kind == "PREFERENCE_MATCH" and item:
                actual = (
                    1
                    if candidate(item, preferences)["preferences"]["state"]
                    == "MATCHES_SUPPORTED_CONSTRAINTS"
                    else 0
                )
            below = rule.kind in {"PRICE_BELOW", "CHANGE_BELOW", "RSI_BELOW"}
            triggered = (
                actual < (-threshold if rule.kind == "CHANGE_BELOW" else threshold)
                if actual is not None and below
                else actual > threshold
                if actual is not None
                else None
            )
            if rule.kind in {"PROVIDER_UNAVAILABLE", "PREFERENCE_MATCH"}:
                triggered = actual == 1 if actual is not None else None
            result = {
                "rule_id": record["id"],
                "name": rule.name,
                "kind": rule.kind,
                "state": "MATCHED"
                if triggered
                else "NOT_MATCHED"
                if triggered is False
                else "INSUFFICIENT_EVIDENCE",
                "source": observed_mark["source"],
                "observation": observed_mark["session"],
                "provider_values_retained": False,
            }
            results.append(result)
            if triggered:
                session = (
                    date.fromisoformat(str(observed_mark["session"])[:10])
                    if observed_mark["session"]
                    else now.astimezone(IST).date()
                )
                identity = f"{record['id']}:{record['revision']}:{session}"
                fingerprint = sha256(encode(result).encode()).hexdigest()
                events.append(
                    Event(
                        code="PERSONAL_RESEARCH_ALERT",
                        component="P32",
                        evidence_ref="p32-rule:" + record["id"],
                        evidence_sha256=fingerprint,
                        event_at=now,
                        time_basis="DETECTOR_OBSERVATION_TIME",
                        session=session,
                        classification="USER_RECORDED",
                        mode="RECORDED",
                        reasons=(
                            "USER_THRESHOLD_MATCHED",
                            "NO_EXECUTION",
                            "SOURCE_PRICES_NOT_RETAINED",
                        ),
                        group="p32-personal-research",
                        identity=identity,
                    )
                )
        alerts_root = request.app.state.settings.alerts_root
        published = (
            AlertStore(alerts_root).publish(
                "p32-personal-rules", sha256(encode(results).encode()).hexdigest(), events, now=now
            )
            if alerts_root and events
            else 0
        )
        return {
            "results": results,
            "new_alerts": published,
            "duplicate_prevention": "RULE_REVISION_AND_OBSERVATION_SESSION",
            "network_requests": 0,
            "background_checks": False,
            "outbound": False,
        }

    return wrap(safe(evaluate))


@router.get("/copilot")
def copilot(
    request: Request,
    service: Research,
    question: Literal[
        "model-exclusions", "stock-momentum", "portfolio-risk", "model-history"
    ] = "model-exclusions",
    instrument_key: str = Query(default="", max_length=30),
    portfolio_id: str = Query(default="", max_length=32),
) -> Envelope[JsonValue]:
    safe(lambda: store(request).profile())
    claims: list[dict[str, Any]] = []
    if question == "model-exclusions":
        claims = [
            {
                "text": (
                    "Current ML rankings remain unavailable: all38compatible features, "
                    "contemporaneous peers, authorized retained ML use, adjustment/actions, "
                    "current risk/universe and independent model acceptance are required."
                ),
                "source": "/data-health",
                "evidence": "UNCHANGED_P12_P13_AND_MODEL_ACCEPTANCE_GATES",
            }
        ]
    elif question == "stock-momentum":
        item = cached(private_root(service), (instrument_key,)).get(instrument_key)
        if item:
            data = candidate(item, safe(lambda: profile(request)))
            claims = [
                {
                    "text": observation.replace("_", " ").lower(),
                    "source": data["evidence_link"],
                    "evidence": {"observation": data["mark"], "metrics": data["metrics"]},
                }
                for observation in data["technical_observations"]
            ]
        else:
            claims = [
                {
                    "text": "Load compatible selected-stock candles explicitly; "
                    "no usable cached evidence is available.",
                    "source": "/analysis",
                    "evidence": "INSUFFICIENT_EVIDENCE",
                }
            ]
    elif question == "portfolio-risk":
        data = safe(lambda: review(request, service, portfolio_id, False))
        claims = [
            {
                "text": holding["symbol"]
                + ": "
                + ", ".join(holding["diagnostics"]).replace("_", " ").lower(),
                "source": "/portfolios",
                "evidence": {
                    "ledger_state_id": data["ledger_state_id"],
                    "cost_allocation_percent": holding["cost_allocation_percent"],
                    "price_observation": holding["mark"],
                    "missing": holding["preference_match"]["missing"],
                },
            }
            for holding in data["holdings"]
        ]
    else:
        claims = [
            {
                "text": (
                    "Saved chronological OOS results can be inspected by horizon, fold and "
                    "baseline. Historical evidence does not establish a current accepted "
                    "model or resolve incomplete economic backtests."
                ),
                "source": "/research",
                "evidence": "CHECKSUM_VERIFIED_EXISTING_P9_P10_REPORTS_NO_NEW_EVALUATION",
            }
        ]
    return wrap(
        {
            "mode": "DETERMINISTIC_GUIDED_RESEARCH_NO_LLM",
            "question": question,
            "claims": claims,
            "financial_advice": False,
            "current_predictions": 0,
        }
    )
