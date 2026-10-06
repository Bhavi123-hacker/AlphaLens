"""Past-only component risk. Financial inputs remain exact; derived measures are float64."""

from datetime import date
from statistics import mean, pstdev, stdev
from typing import Any

from alphalens_data.canonical.models import Availability, CanonicalDataset, PriceView, ReadContext
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.errors import DataContractError
from alphalens_data.quality.models import QualityStatus
from alphalens_decision.models import Horizon, ModelDiagnostic, ModelEvidence, PredictionEvidence
from alphalens_decision.risk_contracts import Metric, RiskComponent, RiskPolicy, RiskSnapshot, level
from alphalens_evaluation.contracts import digest, disclaimer
from alphalens_features.engine import calendar_dates
from alphalens_features.models import FeatureDataset, FeatureRow


def component(
    metrics: dict[str, Metric],
    severity: float | None,
    reasons: list[str] | tuple[str, ...] = (),
    degraded: bool = False,
) -> RiskComponent:
    severity = min(1.0, max(0.0, severity)) if severity is not None else None
    return RiskComponent(
        metrics=metrics,
        severity=severity,
        level=level(severity),
        availability=Availability.UNAVAILABLE
        if severity is None
        else Availability.DEGRADED
        if degraded
        else Availability.AVAILABLE,
        reasons=tuple(sorted(set(reasons))),
    )


def model_uncertainty(
    predictions: list[PredictionEvidence], diagnostics: list[ModelDiagnostic], policy: RiskPolicy
) -> RiskComponent:
    probabilities = [p.probability for p in predictions if p.probability is not None]
    returns = [p.prediction for p in predictions if p.task == "regression"]
    groups = {(p.family, p.task) for p in predictions}
    counts = [
        sum(d.sample_count for d in diagnostics if (d.family, d.task) == group) for group in groups
    ]
    validation_rows = min(counts) if counts else 0
    reasons = []
    uncertainty: list[float] = []
    metrics: dict[str, Metric] = {
        "classification_models": len(probabilities),
        "regression_models": len(returns),
        "historical_validation_rows_per_family_minimum": validation_rows,
        "models_probability_positive": sum(p > 0.5 for p in probabilities),
        "probability_mean": mean(probabilities) if probabilities else None,
        "probability_dispersion": pstdev(probabilities) if probabilities else None,
        "predicted_return_mean": mean(returns) if returns else None,
        "predicted_return_dispersion": pstdev(returns) if returns else None,
    }
    if probabilities:
        uncertainty.extend(
            (
                1 - 2 * abs(mean(probabilities) - 0.5),
                pstdev(probabilities) / policy.probability_dispersion_scale,
            )
        )
        if pstdev(probabilities) / policy.probability_dispersion_scale >= 0.5:
            reasons.append("MODEL_DISAGREEMENT")
    if returns:
        uncertainty.append(pstdev(returns) / policy.return_dispersion_scale)
        if pstdev(returns) / policy.return_dispersion_scale >= 0.5:
            reasons.append("MODEL_DISAGREEMENT")
    instability = []
    for family, task in groups:
        values = [
            d.primary_metric
            for d in diagnostics
            if d.family == family and d.task == task and d.primary_metric is not None
        ]
        if len(values) > 1:
            instability.append(
                pstdev(values)
                / (
                    policy.brier_scale
                    if task == "classification"
                    else policy.return_dispersion_scale
                )
            )
    metrics["normalized_fold_instability"] = max(instability) if instability else None
    uncertainty.extend(instability)
    brier = [d.brier_score for d in diagnostics if d.brier_score is not None]
    metrics["historical_brier_mean"] = mean(brier) if brier else None
    if brier:
        uncertainty.append(mean(brier) / policy.brier_scale)
        if mean(brier) / policy.brier_scale >= 0.5:
            reasons.append("CALIBRATION_WEAKNESS")
    if instability and max(instability) >= 0.5:
        reasons.append("MODEL_FOLD_INSTABILITY")
    if not predictions:
        reasons.append("MODEL_UNAVAILABLE")
    if validation_rows < policy.minimum_validation_rows:
        reasons.append("INSUFFICIENT_MODEL_VALIDATION")
    if probabilities and not all(
        any(
            d.calibration_available and d.family == p.family and d.task == p.task
            for d in diagnostics
        )
        for p in predictions
        if p.task == "classification"
    ):
        reasons.append("CALIBRATION_UNAVAILABLE")
    if any(
        r in reasons
        for r in ("MODEL_UNAVAILABLE", "INSUFFICIENT_MODEL_VALIDATION", "CALIBRATION_UNAVAILABLE")
    ):
        uncertainty.append(policy.missing_model_severity)
    return component(
        metrics,
        max(uncertainty) if uncertainty else policy.missing_model_severity,
        reasons,
        degraded=bool(reasons),
    )


class RiskEngine:
    def __init__(
        self, reader: CanonicalReader, features: FeatureDataset, models: ModelEvidence | None = None
    ) -> None:
        if (
            features.canonical_input_id != reader.batch.input_id
            or features.classification != reader.batch.classification
            or features.feature_set_id
            != digest(features.model_dump(mode="json", exclude={"feature_set_id"}))
            or models is not None
            and models.classification != features.classification
        ):
            raise DataContractError("RISK_INPUT_IDENTITY_OR_CLASSIFICATION_MISMATCH")
        self.reader, self.features, self.models = reader, features, models
        self._snapshots: dict[date, CanonicalDataset] = {}

    def row(self, security_id: str, session: date) -> FeatureRow:
        row = next(
            (
                r
                for r in self.features.rows
                if r.security_id == security_id and r.session_date == session
            ),
            None,
        )
        if row is None:
            raise DataContractError("RISK_FEATURE_ROW_UNAVAILABLE")
        return row

    def snapshot(self, row: FeatureRow) -> CanonicalDataset:
        if row.session_date not in self._snapshots:
            self._snapshots[row.session_date] = self.reader.build(
                self.features.feature_set.plan.history_start,
                row.session_date,
                ReadContext(knowledge_cutoff=row.knowledge_cutoff),
            )
        snapshot = self._snapshots[row.session_date]
        universe = next(
            s for s in snapshot.universe_snapshots if s.session_date == row.session_date
        )
        if (
            snapshot.dataset_id != row.canonical_dataset_id
            or universe.snapshot_id != row.universe_snapshot_id
        ):
            raise DataContractError("RISK_P6_P5_VINTAGE_MISMATCH")
        return snapshot

    def visible_models(
        self, row: FeatureRow, horizon: Horizon
    ) -> tuple[list[PredictionEvidence], list[ModelDiagnostic]]:
        predictions, diagnostics = [], []
        if self.models:
            predictions = [
                p
                for p in self.models.predictions
                if p.security_id == row.security_id
                and p.session_date == row.session_date
                and p.horizon == horizon
                and p.available_at <= row.knowledge_cutoff
            ]
            for p in predictions:
                if (
                    p.decision_time != row.decision_time
                    or p.feature_set_id != self.features.feature_set_id
                    or p.canonical_dataset_id != row.canonical_dataset_id
                    or p.universe_snapshot_id != row.universe_snapshot_id
                ):
                    raise DataContractError("RISK_PREDICTION_FEATURE_VINTAGE_MISMATCH")
            families = {(p.family, p.task) for p in predictions}
            evaluations = {p.evaluation_id for p in predictions}
            diagnostics = [
                d
                for d in self.models.diagnostics
                if d.horizon == horizon
                and d.evaluation_id in evaluations
                and (d.family, d.task) in families
                and d.available_at <= row.knowledge_cutoff
            ]
        return predictions, diagnostics

    def evaluate(
        self, security_id: str, session: date, horizon: Horizon, policy: RiskPolicy | None = None
    ) -> RiskSnapshot:
        policy = policy or RiskPolicy()
        row = self.row(security_id, session)
        snapshot = self.snapshot(row)
        universe = next(s for s in snapshot.universe_snapshots if s.session_date == session)
        entry = next(
            (
                e
                for e in (*universe.eligible_securities, *universe.excluded_securities)
                if e.security_id == security_id
            ),
            None,
        )
        dates, calendar_reason = calendar_dates(snapshot, session)
        views = {
            v.observation.session_date: v
            for v in snapshot.prices
            if v.observation.security_id == security_id
        }
        slots = [views.get(d) for d in dates[-policy.minimum_history :]]
        usable = [v for v in slots if v is not None and self.usable(v, row)]
        complete = len(slots) >= policy.minimum_history and len(usable) == len(slots)
        current = views.get(session)
        quality = current.quality if current else "UNAVAILABLE"
        actions = [
            a
            for a in snapshot.corporate_actions
            if a.security_id == security_id and a.event_type != "SYMBOL_CHANGE"
        ]
        window_actions = [
            a
            for a in actions
            if a.ex_date is None
            or dates
            and dates[max(0, len(dates) - policy.minimum_history)] <= a.ex_date <= session
        ]
        values = {name: value.value for name, value in row.values.items()}
        components: dict[str, RiskComponent] = {}
        vol = values.get("volatility_20")
        atr = values.get("atr_14")
        close = (
            float(current.observation.values.close)
            if current and current.observation.values
            else None
        )
        components["volatility_risk"] = component(
            {
                "volatility_20": vol,
                "volatility_60": values.get("volatility_60"),
                "atr_price_ratio": atr / close if atr is not None and close else None,
            },
            max(vol / policy.volatility_scale, atr / close / policy.atr_ratio_scale)
            if vol is not None and atr is not None and close
            else None,
            ["HIGH_VOLATILITY"]
            if vol is not None and vol / policy.volatility_scale >= 0.5
            else ["VOLATILITY_FEATURE_UNAVAILABLE"]
            if vol is None or atr is None
            else [],
        )
        draw = values.get("drawdown_20")
        closes = [float(v.observation.values.close) for v in usable if v.observation.values][
            -policy.window :
        ]
        max_draw = None
        if complete and not window_actions:
            peak = closes[0]
            drawdowns = []
            for value in closes:
                peak = max(peak, value)
                drawdowns.append(value / peak - 1)
            max_draw = min(drawdowns)
        magnitude = (
            max(abs(draw), abs(max_draw)) if draw is not None and max_draw is not None else None
        )
        components["drawdown_risk"] = component(
            {"current_drawdown": draw, "recent_max_drawdown": max_draw},
            magnitude / policy.drawdown_scale if magnitude is not None else None,
            ["DEEP_RECENT_DRAWDOWN"]
            if magnitude is not None and magnitude / policy.drawdown_scale >= 0.5
            else ["DRAWDOWN_HISTORY_UNAVAILABLE"]
            if magnitude is None
            else [],
        )
        volumes = [v.observation.values.volume for v in usable if v.observation.values][
            -policy.window :
        ]
        zeros = sum(v == 0 for v in volumes) / len(volumes) if complete else None
        cv = stdev(volumes) / mean(volumes) if complete and mean(volumes) else None
        ratio = values.get("volume_ratio_20")
        liquidity_scores = [zeros / policy.zero_volume_scale] if zeros is not None else []
        if cv is not None:
            liquidity_scores.append(cv / policy.volume_cv_scale)
        if ratio is not None:
            liquidity_scores.append(max(0, 1 - ratio))
        components["liquidity_proxy_risk"] = component(
            {
                "proxy": "VOLUME_BASED_LIQUIDITY_PROXY",
                "zero_volume_frequency": zeros,
                "volume_ratio_20": ratio,
                "volume_cv": cv,
            },
            max(liquidity_scores) if complete and liquidity_scores else None,
            ["LOW_VOLUME_HISTORY"]
            if not complete
            else ["ZERO_VOLUME_OBSERVATIONS"]
            if zeros
            else [],
        )
        gaps = []
        if complete and not window_actions:
            for previous, following in zip(usable, usable[1:], strict=False):
                if previous.observation.values and following.observation.values:
                    gaps.append(
                        float(
                            following.observation.values.open / previous.observation.values.close
                            - 1
                        )
                    )
        gap_frequency = (
            sum(abs(g) >= policy.large_gap_threshold for g in gaps) / len(gaps) if gaps else None
        )
        gap_score = (
            max(
                max(map(abs, gaps)) / policy.absolute_gap_scale,
                gap_frequency / policy.gap_frequency_scale,
            )
            if gaps and gap_frequency is not None
            else None
        )
        components["gap_risk"] = component(
            {
                "latest_gap": gaps[-1] if gaps else None,
                "maximum_absolute_gap": max(map(abs, gaps)) if gaps else None,
                "large_gap_frequency": gap_frequency,
            },
            gap_score,
            (
                ["KNOWN_ACTION_DISCONTINUITY"]
                if window_actions
                else ["GAP_HISTORY_UNAVAILABLE"]
                if not gaps
                else ["LARGE_HISTORICAL_GAPS"]
                if gap_score and gap_score >= 0.5
                else []
            )
            + ["GAP_ACTION_COVERAGE_NOT_ESTABLISHED"],
            degraded=True,
        )
        benchmark = values.get("market_volatility_20")
        relative = (
            vol / benchmark if vol is not None and benchmark is not None and benchmark > 0 else None
        )
        components["market_risk"] = component(
            {
                "relative_volatility": relative,
                "benchmark_evidence": self.features.feature_set.plan.benchmark_evidence_reference,
                "benchmark_label": "TEST_ONLY_BENCHMARK"
                if benchmark is not None and row.classification.value == "TEST_ONLY"
                else "EVIDENCED_BENCHMARK"
                if benchmark is not None
                else None,
            },
            max(0, relative - 1) / policy.relative_volatility_excess_scale
            if relative is not None
            else None,
            ["BENCHMARK_UNAVAILABLE"] if relative is None else [],
        )
        predictions, diagnostics = self.visible_models(row, horizon)
        components["model_uncertainty"] = model_uncertainty(predictions, diagnostics, policy)
        components["data_quality_risk"] = component(
            {"source_quality": str(quality), "feature_availability": row.quality_state.value},
            0
            if quality == QualityStatus.VALID
            else 0.5
            if quality == QualityStatus.DEGRADED
            else 1,
            []
            if quality == QualityStatus.VALID
            else ["DEGRADED_SOURCE_DATA"]
            if quality == QualityStatus.DEGRADED
            else ["DATA_QUALITY_REJECTED"]
            if quality == QualityStatus.REJECTED
            else ["SOURCE_DATA_UNAVAILABLE"],
            degraded=quality != QualityStatus.VALID,
        )
        components["corporate_action_risk"] = component(
            {
                "coverage": self.features.corporate_action_coverage,
                "known_economic_actions": len(actions),
            },
            1 if actions and row.price_basis == "UNADJUSTED" else policy.missing_optional_severity,
            ["KNOWN_UNADJUSTED_CORPORATE_ACTION"]
            if actions and row.price_basis == "UNADJUSTED"
            else ["CORPORATE_ACTION_UNCERTAINTY"],
            degraded=True,
        )
        observed_count = sum(self.usable(views.get(d), row) for d in dates)
        sufficient = (
            "INSUFFICIENT"
            if not complete
            else "LIMITED"
            if observed_count < policy.sufficient_history
            else "SUFFICIENT"
        )
        components["historical_evidence"] = component(
            {
                "usable_historical_observations": observed_count,
                "required_history": policy.minimum_history,
                "sufficient_history": policy.sufficient_history,
            },
            1 if sufficient == "INSUFFICIENT" else 0.5 if sufficient == "LIMITED" else 0,
            ["INSUFFICIENT_HISTORY"]
            if sufficient == "INSUFFICIENT"
            else ["LIMITED_HISTORY"]
            if sufficient == "LIMITED"
            else [],
        )
        permitted = bool(
            entry
            and entry.analysis_eligible
            and row.analytical_eligible
            and complete
            and components["volatility_risk"].severity is not None
            and components["drawdown_risk"].severity is not None
            and quality in {QualityStatus.VALID, QualityStatus.DEGRADED}
            and row.quality_state != Availability.STALE
            and not (actions and row.price_basis == "UNADJUSTED")
        )
        reasons = {reason for c in components.values() for reason in c.reasons}
        if not entry or not entry.universe_membership or not entry.analysis_eligible:
            reasons.add("UNIVERSE_INELIGIBLE")
        if calendar_reason:
            reasons.add(calendar_reason)
        severity = max(
            c.severity if c.severity is not None else policy.missing_optional_severity
            for c in components.values()
        )
        payload: dict[str, Any] = dict(
            security_id=security_id,
            symbol=entry.identity.symbol if entry and entry.identity else None,
            session_date=session,
            decision_time=row.decision_time,
            knowledge_cutoff=row.knowledge_cutoff,
            horizon=horizon,
            feature_set_id=self.features.feature_set_id,
            canonical_input_id=self.reader.batch.input_id,
            canonical_dataset_id=snapshot.dataset_id,
            universe_snapshot_id=row.universe_snapshot_id,
            universe_definition_id=self.reader.batch.definition.universe_id,
            observed_price_available_at=current.observation.provenance.available_at
            if current
            else None,
            source_quality=quality,
            feature_availability=row.quality_state,
            classification=row.classification,
            policy=policy,
            components=components,
            overall_level=level(severity) if permitted else "UNAVAILABLE",
            model_confidence="INSUFFICIENT_EVIDENCE"
            if row.classification.value == "TEST_ONLY"
            or any(
                r in reasons
                for r in (
                    "INSUFFICIENT_MODEL_VALIDATION",
                    "CALIBRATION_UNAVAILABLE",
                    "MODEL_UNAVAILABLE",
                )
            )
            else "DESCRIPTIVE_DIAGNOSTICS_ONLY",
            evidence_sufficiency=sufficient,
            analysis_permitted=permitted,
            availability=Availability.DEGRADED if permitted else Availability.UNAVAILABLE,
            reasons=tuple(sorted(reasons)),
            prediction_evidence_ids=tuple(sorted(p.evidence_id for p in predictions)),
            diagnostic_evidence_ids=tuple(sorted(d.evidence_id for d in diagnostics)),
            model_run_ids=tuple(sorted({p.model_run_id for p in predictions})),
            evaluation_ids=tuple(sorted({p.evaluation_id for p in predictions})),
            disclaimer=disclaimer(row.classification),
        )
        provisional = RiskSnapshot.model_construct(risk_snapshot_id="0" * 64, **payload)
        content = provisional.model_dump(mode="json", exclude={"risk_snapshot_id"})
        return RiskSnapshot.model_validate(dict(risk_snapshot_id=digest(content), **content))

    @staticmethod
    def usable(view: PriceView | None, row: FeatureRow) -> bool:
        expected = "RAW_UNADJUSTED" if row.price_basis == "UNADJUSTED" else "ADJUSTED"
        return bool(
            view
            and view.analysis_eligible
            and view.observation.values
            and view.observation.price_basis == expected
            and view.availability in {Availability.AVAILABLE, Availability.DEGRADED}
        )
