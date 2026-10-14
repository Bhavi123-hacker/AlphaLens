"""P19 incremental orchestration with exclusive restart-safe publication."""

import shutil
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from scripts.build_tejhq_research import research_id

from alphalens_data.canonical.models import EODValues
from alphalens_data.daily.contracts import Observation, Request
from alphalens_data.daily.providers import BASELINE, PINNED_REVISION
from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import ArtifactSpec, CanonicalEOD, Classification, Versions
from alphalens_data.ingestion.normalizing import normalize
from alphalens_data.ingestion.parsing import ParsedRow
from alphalens_data.ingestion.storage import RawLanding, stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.tejhq import REQUIRED, parse_batch
from alphalens_data.providers.test_bundle import parse_bundle
from alphalens_data.quality.engine import validate
from alphalens_data.quality.models import ArtifactEvidence, ValidationInput
from alphalens_data.research import assess

from .features import definitions, update
from .gates import policy_snapshot


def select_session(path: Path, session: date) -> tuple[list[ParsedRow], dict[int, str]]:
    source = pq.ParquetFile(path)
    if not REQUIRED.issubset(source.schema_arrow.names):
        raise DataContractError("SOURCE_PARQUET_SCHEMA_INVALID")
    parsed: list[ParsedRow] = []
    names: dict[int, str] = {}
    first = 2
    for batch in source.iter_batches(batch_size=4096):
        rows = batch.to_pylist()
        for i, row in enumerate(rows, first):
            if row["date"] == session:
                parsed.extend(parse_batch([row], i))
                names[i] = row.get("name") or ""
                if len(parsed) > 10000:
                    raise DataContractError("DAILY_RELEASE_ROW_LIMIT")
        first += len(rows)
    return parsed, names


class Worker:
    def __init__(
        self,
        root: Path,
        approved_historical_hashes: frozenset[str] = frozenset(),
        hook: Callable[[str], None] | None = None,
    ) -> None:
        self.store = Store(root)
        self.approved = approved_historical_hashes
        self.hook = hook or (lambda _: None)

    def run(
        self,
        request: Request,
        payload: Path | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        if len(history or []) > 201 * 128:
            raise DataContractError("BOUNDED_CONTEXT_ROW_LIMIT")
        if checksum(stable_json(policy_snapshot())) != request.decision_policy_id:
            raise DataContractError("UNCHANGED_DECISION_POLICY_REQUIRED")
        if checksum(stable_json(history or [])) != request.context_sha256:
            raise DataContractError("TRAILING_CONTEXT_CHECKSUM_MISMATCH")
        registered = [
            d.model_dump(mode="json")
            for d in definitions(request.session, request.source_received_at)
        ]
        if checksum(stable_json(registered)) != request.feature_registry_id:
            raise DataContractError("FEATURE_REGISTRY_MISMATCH")
        with self.store.lock():
            if self.store.exists(request.run_id, "receipt.json"):
                return self.store.receipt(request.run_id)
            if len(
                list((self.store.root / "runs").glob("*/request.json"))
            ) >= 1000 and not self.store.exists(request.run_id, "request.json"):
                raise DataContractError("DAILY_RUN_INDEX_LIMIT_ARCHIVE_REQUIRED")
            if shutil.disk_usage(self.store.root).free < 1_073_741_824:
                raise DataContractError("DAILY_FREE_DISK_GUARD")
            if self.store.exists(request.run_id, "request.json"):
                # First acquisition clocks survive restart and duplicate invocation.
                request = Request.model_validate(self.store.read(request.run_id, "request.json"))
            else:
                self.store.write(request.run_id, "request.json", request.model_dump(mode="json"))
            self.store.write(request.run_id, "context.json", {"rows": history or []})
            if not self.store.exists(request.run_id, "started.json"):
                self.store.write(
                    request.run_id, "started.json", {"started_at": datetime.now(UTC).isoformat()}
                )
            try:
                return self._run(request, payload, history or [], started)
            except (OSError, TimeoutError):
                # Operational failure is immutable evidence, not publication of partial products.
                attempts = list(
                    self.store.path(request.run_id, "request.json").parent.glob("retry-*.json")
                )
                if len(attempts) >= 3:
                    return self.finish(request, "FAILED", {}, ["RETRY_LIMIT_EXCEEDED"])
                self.store.write(
                    request.run_id,
                    f"retry-{len(attempts)}.json",
                    dict(
                        state="RETRYABLE_FAILURE",
                        reason="LOCAL_IO_OR_TIME_BUDGET",
                        at=datetime.now(UTC).isoformat(),
                    ),
                )
                raise DataContractError("RETRYABLE_FAILURE_RESUME_SAME_REQUEST") from None
            except (DataContractError, ValueError):
                return self.finish(request, "FAILED", {}, ["INPUT_OR_EVIDENCE_CONTRACT_REJECTED"])

    def _run(
        self, request: Request, payload: Path | None, history: list[dict[str, Any]], started: float
    ) -> dict[str, Any]:
        def check(stage: str) -> None:
            self.hook(stage)
            if time.monotonic() - started > request.timeout_seconds:
                raise TimeoutError

        calendar_status = request.calendar.status(request.session, request.source_received_at)
        if request.mode == "DAILY":
            reasons = list(request.provider.reasons)
            if not request.provider.allowed(request.mode):
                reasons.append("ONGOING_PROVIDER_NOT_CLEARED")
            elif request.provider.source != "upstox":
                reasons.append("AUTOMATED_SOURCE_ADAPTER_NOT_VERIFIED")
            if calendar_status != "TRADING":
                reasons.append(calendar_status)
            if not any(
                s.session == request.session and s.evidence_type == "OFFICIAL_VERIFIED_SESSION"
                for s in request.calendar.sessions
            ):
                reasons.append("OFFICIAL_SESSION_EVIDENCE_REQUIRED")
            if reasons:
                return self.finish(request, "BLOCKED_SOURCE", {}, reasons)
            if request.session <= date(2026, 10, 6):
                return self.finish(
                    request, "BLOCKED_EVIDENCE", {}, ["FROZEN_SESSION_NOT_NEW_OPERATIONAL_DATA"]
                )
            if payload is None:
                return self.finish(request, "BLOCKED_EVIDENCE", {}, ["SOURCE_OBSERVATION_PENDING"])
            if payload.stat().st_size > 2_000_000:
                raise DataContractError("OPERATIONAL_RELEASE_SIZE_LIMIT")
            data = payload.read_bytes()
            if checksum(data) != request.payload_sha256:
                raise DataContractError("SOURCE_PAYLOAD_CHECKSUM_MISMATCH")
            from workers.providers.operational_release import stage

            operational_products, reasons, counts = stage(request, data, self.store, check)
            return self.finish(
                request, "COMPLETED_WITH_WARNINGS", operational_products, reasons, **counts
            )
        if calendar_status != "TRADING":
            return self.finish(request, "BLOCKED_EVIDENCE", {}, [calendar_status])
        if payload is None:
            return self.finish(request, "BLOCKED_EVIDENCE", {}, ["SOURCE_OBSERVATION_PENDING"])
        if request.mode == "HISTORICAL_REPLAY" and request.payload_sha256 not in self.approved:
            raise DataContractError("HISTORICAL_PAYLOAD_NOT_PINNED_APPROVED")
        if request.mode == "HISTORICAL_REPLAY" and (
            request.provider.revision != PINNED_REVISION
            or request.baseline_identity != BASELINE
            or request.provider.source != "tejhq"
            or request.provider.dataset != "indian-markets"
        ):
            raise DataContractError("HISTORICAL_REPLAY_BASELINE_MISMATCH")
        if payload.stat().st_size > 100_000_000:
            raise DataContractError("SOURCE_PAYLOAD_SIZE_LIMIT")
        data = payload.read_bytes()
        if checksum(data) != request.payload_sha256:
            raise DataContractError("SOURCE_PAYLOAD_CHECKSUM_MISMATCH")
        products: dict[str, dict[str, str]] = {}
        if not self.store.exists(request.run_id, "normalized.json"):
            vendor_rows = None
            vendor_names: dict[int, str] = {}
            adapter_evidence: dict[str, Any] = {}
            native_data = data
            if request.provider.source != "tejhq":
                if request.mode != "TEST_ONLY":
                    raise DataContractError("NON_TEJHQ_ADAPTER_OFFLINE_TEST_ONLY")
                native_data, vendor_rows, vendor_names, adapter_evidence = parse_bundle(
                    data, request.provider.source, request.session, request.source_received_at
                )
            raw = RawLanding(self.store.root / "raw-landing")
            # Only this P19-owned RawLanding is used; outer kernel lock proves no
            # other P19 writer exists. Recover its abandoned P2 capture lock safely.
            capture_lock = raw.root / ".capture.lock"
            if capture_lock.exists():
                capture_lock.unlink()
            classification = (
                Classification.TEST_ONLY
                if request.mode == "TEST_ONLY"
                else Classification.RESEARCH_ONLY
            )
            manifest, _ = raw.capture(
                native_data,
                ArtifactSpec(
                    source=request.provider.source,
                    dataset=request.provider.dataset,
                    source_identifier="p19:" + request.provider.revision,
                    source_session_date=request.session,
                    original_filename=request.source_filename,
                    content_type="application/json"
                    if vendor_rows is not None
                    else "application/vnd.apache.parquet",
                    classification=classification,
                    currency="INR",
                    currency_evidence="P19_PINNED_SOURCE_INR_SCHEMA",
                    rights_evidence=request.provider.evidence_reference,
                ),
                Versions(
                    parser="p28.offline-adapters.v1"
                    if vendor_rows is not None
                    else "p19.tejhq.session.v1"
                ),
            )
            selected, names = (
                (list(vendor_rows), vendor_names)
                if vendor_rows is not None
                else (select_session(payload, request.session))
            )
            records, quarantine = normalize(tuple(selected), manifest)
            quality = validate(
                ValidationInput(
                    records=records,
                    quarantine=quarantine,
                    artifacts=(
                        ArtifactEvidence(
                            manifest=manifest,
                            observed_sha256=checksum(native_data),
                            observed_byte_size=len(native_data),
                            normalized_sha256=checksum(
                                stable_json(
                                    [
                                        r.model_dump(mode="json", exclude={"record_id"})
                                        for r in records
                                    ]
                                )
                            ),
                        ),
                    ),
                    classification=classification,
                    start_session=request.session,
                    end_session=request.session,
                )
            )
            statuses = {(s.security_id, s.session_date): s for s in quality.sessions}
            observations, rejected = [], 0
            for row in records:
                state = statuses[(row.security_id, row.session_date)]
                assessment = assess(row.series, row.isin, names[row.source_row_number])
                stable = research_id(row)
                prior_exclusion = any(
                    h["security_id"] == stable
                    and str(h["session_date"]) < request.session.isoformat()
                    and (
                        not h.get("received_at")
                        or datetime.fromisoformat(h["received_at"]) <= request.source_received_at
                    )
                    and h.get("analytical_type") == "EXCLUDED_NON_EQUITY"
                    for h in history
                )
                if prior_exclusion:
                    assessment = assessment.model_copy(
                        update={
                            "analytical_type": "EXCLUDED_NON_EQUITY",
                            "reason": "PRIOR_EXPLICIT_EXCLUSION_RETAINED",
                        }
                    )
                # P5 exact-value validation; no price adjustment or identifier backfill.
                EODValues(
                    open=row.open, high=row.high, low=row.low, close=row.close, volume=row.volume
                )
                observation = Observation(
                    source=row,
                    stable_security_id=stable,
                    analytical_type=assessment.analytical_type,
                    identity_reason=assessment.reason,
                    quality=state.status.value,
                    quality_reasons=state.reason_codes,
                )
                observations.append(
                    observation.model_dump(mode="json")
                    | {"canonical_record_id": observation.identity}
                )
                rejected += state.status.value == "REJECTED"
            self.store.write(
                request.run_id,
                "normalized.json",
                dict(
                    rows=observations,
                    raw_manifest=manifest.model_dump(mode="json"),
                    quality=quality.model_dump(mode="json"),
                    quarantined=len(quarantine),
                    rejected=rejected,
                    adapter_evidence=adapter_evidence,
                ),
            )
        check("normalized")
        normalized = self.store.read(request.run_id, "normalized.json")
        products["validation"] = self.store.write(
            request.run_id, "validation.json", normalized["quality"]
        )
        rows = []
        for item in normalized["rows"]:
            source = CanonicalEOD.model_validate(item["source"])
            rows.append(
                dict(
                    security_id=item["stable_security_id"],
                    symbol=source.symbol,
                    isin=source.isin,
                    session_date=source.session_date.isoformat(),
                    quality=item["quality"],
                    quality_reasons=item["quality_reasons"],
                    analytical_type=item["analytical_type"],
                    canonical_record_id=item["canonical_record_id"],
                    received_at=request.source_received_at.isoformat(),
                    open=str(source.open),
                    high=str(source.high),
                    low=str(source.low),
                    close=str(source.close),
                    volume=source.volume,
                    economic_action=None,
                    action_status="CURRENT_ACTION_EVIDENCE_UNAVAILABLE",
                    price_basis="RAW_UNADJUSTED",
                )
            )
        observed_ids = {r["security_id"] for r in rows}
        missing = sorted(set(request.expected_security_ids) - observed_ids)
        products["canonical"] = self.store.write(
            request.run_id,
            "canonical.json",
            dict(
                rows=rows,
                missing_security_ids=missing,
                missing_scope="EXPLICIT_EXPECTED_SECURITY_IDS_ONLY_NO_CURRENT_UNIVERSE_INFERENCE",
            ),
        )
        if not rows:
            return self.finish(
                request, "BLOCKED_EVIDENCE", products, ["MISSING_SOURCE_OBSERVATION"]
            )
        if all(r["quality"] == "REJECTED" for r in rows):
            return self.finish(
                request,
                "BLOCKED_EVIDENCE",
                products,
                ["ALL_OBSERVATIONS_REJECTED_BY_P3"],
                counts={"REJECTED": len(rows)},
            )
        check("canonical")
        if not self.store.exists(request.run_id, "features.json"):
            selected_rows = [
                r
                for r in rows
                if not request.feature_security_ids
                or r["security_id"] in request.feature_security_ids
            ]
            features = update(
                selected_rows,
                history,
                request.calendar,
                request.session,
                request.source_received_at,
            )
            self.store.write(request.run_id, "features.json", features)
        products["features"] = self.store.write(
            request.run_id, "features.json", self.store.read(request.run_id, "features.json")
        )
        check("features")
        counts = Counter(r["quality"] for r in rows)
        reasons = [
            "P3_CROSS_SESSION_REFERENCE_CONTEXT_UNAVAILABLE",
            "CURRENT_ACTION_EVIDENCE_UNAVAILABLE",
            "REPLAY_NOT_NEW_DAILY_OBSERVATION",
            "MODEL_RESEARCH_EVIDENCE_INSUFFICIENT",
            "RANKING_ACCEPTANCE_GATE_NOT_MET",
            "SIGNAL_ACCEPTANCE_GATE_NOT_MET",
        ]
        if missing:
            reasons.append("EXPECTED_SECURITY_OBSERVATIONS_MISSING")
        if request.feature_security_ids:
            reasons.append("EXPLICIT_BOUNDED_FEATURE_SCOPE_NOT_FULL_RELEASE")
        if (
            normalized["quarantined"]
            or normalized["rejected"]
            or normalized["quality"]["dataset_blocked"]
        ):
            reasons.append("RELEASE_PARTIAL_OR_REJECTED")
        check("before_publish")
        return self.finish(
            request,
            "COMPLETED_WITH_WARNINGS",
            products,
            reasons,
            counts=dict(counts),
            quarantined=normalized["quarantined"],
            missing=len(missing) if request.expected_security_ids else None,
            feature_rows=len(self.store.read(request.run_id, "features.json")["rows"]),
        )

    def finish(
        self,
        request: Request,
        state: str,
        products: dict[str, Any],
        reasons: list[str],
        **counts: Any,
    ) -> dict[str, Any]:
        started = self.store.read(request.run_id, "started.json")["started_at"]
        receipt = dict(
            version=request.version,
            run_id=request.run_id,
            identity=request.model_dump(mode="json", exclude={"source_received_at"}),
            mode=request.mode,
            session=request.session.isoformat(),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
            source_received_at=request.source_received_at.isoformat(),
            state=state,
            products=products,
            counts=counts,
            reasons=sorted(set(reasons)),
            coverage_scope=request.coverage_scope,
            data_reality="TEST_ONLY" if request.mode == "TEST_ONLY" else "REAL_MARKET_OBSERVATIONS",
            usage_classification="TEST_ONLY" if request.mode == "TEST_ONLY" else "RESEARCH_ONLY",
            final_vintage="FINAL_VINTAGE_RESEARCH_ASSUMPTION"
            if request.mode == "HISTORICAL_REPLAY"
            else None,
            production_ready=False,
            production_market_data_use="NOT_CLEARED",
            inference_status="UNAVAILABLE",
            ranking_status="UNAVAILABLE",
            signal_status="UNAVAILABLE",
            decision_policy_id=request.decision_policy_id,
        )
        receipt["receipt_sha256"] = checksum(stable_json(receipt))
        self.store.write(request.run_id, "receipt.json", receipt)
        return self.store.receipt(request.run_id)
