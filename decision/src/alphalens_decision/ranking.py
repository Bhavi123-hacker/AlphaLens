"""Historical complete-universe ranking with configured models and explicit risk penalties."""

from datetime import date
from math import tanh
from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.quality.models import QualityStatus
from alphalens_decision.comparison import ComparisonEvidence, summarize
from alphalens_decision.models import ModelDiagnostic, PredictionEvidence
from alphalens_decision.ranking_contracts import (
    ExcludedCandidate,
    RankedCandidate,
    RankingPolicy,
    RankSnapshot,
)
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_evaluation.contracts import digest, disclaimer


def score(
    probability: float | None,
    predicted_return: float | None,
    context: float | None,
    risk: RiskSnapshot,
    policy: RankingPolicy,
) -> tuple[dict[str, float | None], float, dict[str, float], float]:
    values = dict(
        probability=probability,
        normalized_return=0.5 + 0.5 * tanh(predicted_return / policy.return_scale)
        if predicted_return is not None
        else None,
        p6_momentum_percentile=context,
    )
    weights = (policy.probability_weight, policy.return_weight, policy.context_weight)
    available = [
        (v, w) for v, w in zip(values.values(), weights, strict=True) if v is not None and w > 0
    ]
    if not available:
        raise DataContractError("RANKING_PREDICTIVE_COMPONENT_UNAVAILABLE")
    if context is not None and not 0 <= context <= 1:
        raise DataContractError("RANKING_CONTEXT_NOT_NORMALIZED")
    raw = sum(v * w for v, w in available) / sum(w for _, w in available)
    worst = max(
        c.severity if c.severity is not None else risk.policy.missing_optional_severity
        for c in risk.components.values()
    )
    uncertainty = risk.components["model_uncertainty"].severity
    penalties = dict(
        risk=policy.risk_penalty_weight * worst,
        uncertainty=policy.uncertainty_penalty_weight
        * (uncertainty if uncertainty is not None else 1),
        quality=policy.quality_penalty_weight
        if risk.source_quality == QualityStatus.DEGRADED
        else 0.0,
        # Selection is insufficient for every v1 run, including seemingly strong fixture results.
        evidence=policy.evidence_penalty_weight,
        missing_components=policy.missing_component_penalty
        * sum(v is None for v in values.values()),
    )
    return values, raw, penalties, raw - sum(penalties.values())


class RankingEngine:
    def __init__(self, risk: RiskEngine, comparisons: ComparisonEvidence | None = None) -> None:
        self.risk = risk
        self.comparisons = comparisons or ComparisonEvidence()

    def evaluate(
        self,
        session: date,
        policy: RankingPolicy,
        risk_snapshots: tuple[RiskSnapshot, ...] | None = None,
        history: tuple[RankSnapshot, ...] = (),
    ) -> RankSnapshot:
        policy = RankingPolicy.model_validate(policy.model_dump())
        rows = [r for r in self.risk.features.rows if r.session_date == session]
        if not rows:
            raise DataContractError("RANKING_SESSION_FEATURES_UNAVAILABLE")
        cutoff = rows[0].knowledge_cutoff
        if any(r.knowledge_cutoff != cutoff for r in rows):
            raise DataContractError("RANKING_MIXED_DECISION_CUTOFFS")
        dataset = self.risk.snapshot(rows[0])
        universe = next(s for s in dataset.universe_snapshots if s.session_date == session)
        entries = {
            e.security_id: e for e in (*universe.eligible_securities, *universe.excluded_securities)
        }
        # P4 catalogs may retain unknown/future placeholders for auditing. Existence
        # in that catalog is not historical knowledge. Match P6's evidenced facts,
        # while retaining known prices even when identity/classification is missing.
        known_securities = (
            {
                e.security_id
                for e in entries.values()
                if e.identity is not None
                or e.membership_evidence is not None
                or e.membership_reason
                in {"EXCLUDED_NOT_YET_LISTED", "EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE"}
            }
            | {
                security
                for view in dataset.prices
                if (security := view.observation.security_id) is not None
                and view.observation.provenance.available_at is not None
                and view.observation.provenance.available_at <= cutoff
            }
            | {row.security_id for row in rows}
        )
        provided: dict[str, RiskSnapshot] = {}
        if risk_snapshots is not None:
            for r in risk_snapshots:
                if (
                    r.session_date != session
                    or r.horizon != policy.horizon
                    or r.knowledge_cutoff > cutoff
                ):
                    continue
                r = RiskSnapshot.model_validate(r.model_dump())
                if r.security_id in provided:
                    raise DataContractError("RANKING_AMBIGUOUS_RISK_VINTAGE")
                provided[r.security_id] = r
        visible_history = [
            RankSnapshot.model_validate(s.model_dump())
            for s in history
            if s.session_date < session
            and s.knowledge_cutoff <= cutoff
            and s.policy.policy_id == policy.policy_id
            and s.classification == dataset.classification
            and s.universe_definition_id == self.risk.reader.batch.definition.universe_id
        ]
        times = [s.session_date for s in visible_history]
        if len(times) != len(set(times)):
            raise DataContractError("RANKING_AMBIGUOUS_PAST_HISTORY")
        previous = max(visible_history, key=lambda s: s.session_date) if visible_history else None
        past = {r.security_id: r for r in previous.ranked} if previous else {}
        drafts: list[dict[str, Any]] = []
        excluded = []
        risks = []
        predictions: list[PredictionEvidence] = []
        diagnostics: dict[str, ModelDiagnostic] = {}
        for security in sorted(known_securities):
            entry = entries.get(security)
            symbol = entry.identity.symbol if entry and entry.identity else None
            reasons = []
            if not entry or not entry.universe_membership or not entry.analysis_eligible:
                reasons.append("UNIVERSE_INELIGIBLE")
            if not entry or not entry.identity:
                reasons.append("HISTORICAL_IDENTITY_UNAVAILABLE")
            row = next((r for r in rows if r.security_id == security), None)
            risk = None
            if row is None:
                reasons.append("FEATURE_UNAVAILABLE")
            else:
                expected = self.risk.evaluate(security, session, policy.horizon, policy.risk_policy)
                risk = provided.get(security) if risk_snapshots is not None else expected
                if risk is None:
                    reasons.append("RISK_UNAVAILABLE")
                elif risk != expected:
                    raise DataContractError("RANKING_RISK_EVIDENCE_OR_POLICY_MISMATCH")
                if risk:
                    risks.append(risk.risk_snapshot_id)
                    if not risk.analysis_permitted:
                        reasons.extend(("RISK_UNAVAILABLE", *risk.reasons))
                    if risk.source_quality == QualityStatus.REJECTED:
                        reasons.append("DATA_QUALITY_REJECTED")
                visible, known = self.risk.visible_models(row, policy.horizon)
                predictions.extend(visible)
                diagnostics.update({d.evidence_id: d for d in known})
            selected = [
                p
                for p in (visible if row else [])
                if (p.task == "classification" and p.family == policy.classifier)
                or (p.task == "regression" and p.family == policy.regressor)
            ]
            if not selected:
                reasons.append("MODEL_UNAVAILABLE")
            if not any(
                (p.task == "classification" and policy.probability_weight > 0)
                or (p.task == "regression" and policy.return_weight > 0)
                for p in selected
            ):
                reasons.append("WEIGHTED_PREDICTION_UNAVAILABLE")
            if dataset.classification != Classification.TEST_ONLY:
                reasons.append("MODEL_SELECTION_INSUFFICIENT_EVIDENCE")
            if reasons:
                excluded.append(
                    ExcludedCandidate(
                        security_id=security,
                        symbol=symbol,
                        reasons=tuple(sorted(set(reasons))),
                        risk_snapshot_id=risk.risk_snapshot_id if risk else None,
                    )
                )
                continue
            if risk is None or row is None:
                raise DataContractError("RANKING_REQUIRED_EVIDENCE_UNAVAILABLE")
            probability = next(
                (p.probability for p in selected if p.task == "classification"), None
            )
            predicted_return = next(
                (p.prediction for p in selected if p.task == "regression"), None
            )
            context = row.values["momentum_percentile_20"].value
            components, raw, penalties, adjusted = score(
                probability, predicted_return, context, risk, policy
            )
            reasons = [
                *risk.reasons,
                "MODEL_SELECTION_INSUFFICIENT_EVIDENCE",
                "TEST_ONLY_SELECTED_CANDIDATE",
            ]
            for name, value in components.items():
                if value is None:
                    reasons.append(f"{name.upper()}_UNAVAILABLE")
            drafts.append(
                dict(
                    security_id=security,
                    symbol=symbol,
                    session_date=session,
                    horizon=policy.horizon,
                    probability=probability,
                    predicted_return=predicted_return,
                    components=components,
                    raw_opportunity_score=raw,
                    penalties=penalties,
                    risk_adjusted_score=adjusted,
                    overall_risk=risk.overall_level,
                    quality_state=risk.source_quality,
                    availability=risk.availability,
                    observed_price_available_at=risk.observed_price_available_at,
                    reasons=tuple(sorted(set(reasons))),
                    prediction_evidence_ids=tuple(sorted(p.evidence_id for p in selected)),
                    model_run_ids=tuple(sorted({p.model_run_id for p in selected})),
                    evaluation_ids=tuple(sorted({p.evaluation_id for p in selected})),
                    feature_set_id=risk.feature_set_id,
                    canonical_dataset_id=risk.canonical_dataset_id,
                    universe_snapshot_id=risk.universe_snapshot_id,
                    risk_snapshot_id=risk.risk_snapshot_id,
                )
            )
        ranked = []
        for rank, draft in enumerate(
            sorted(drafts, key=lambda r: (-r["risk_adjusted_score"], r["security_id"])), 1
        ):
            old = past.get(draft["security_id"])
            ranked.append(
                RankedCandidate(
                    rank=rank,
                    **draft,
                    previous_rank=old.rank if old else None,
                    rank_change=old.rank - rank if old else None,
                    previous_rank_snapshot_id=previous.rank_snapshot_id
                    if old and previous
                    else None,
                )
            )
        evaluations = {p.evaluation_id for p in predictions}
        economics = [
            e
            for e in self.comparisons.economics
            if e.available_at <= cutoff
            and e.period_end < session
            and e.horizon == policy.horizon
            and e.evaluation_id in evaluations
        ]
        for e in economics:
            if (
                e.classification != dataset.classification
                or e.canonical_input_id != self.risk.reader.batch.input_id
                or e.feature_set_id != self.risk.features.feature_set_id
            ):
                raise DataContractError("RANKING_ECONOMIC_EVIDENCE_VINTAGE_MISMATCH")
        known_ranking = [
            r
            for r in self.comparisons.ranking
            if r.available_at <= cutoff
            and r.horizon == policy.horizon
            and r.evaluation_id in evaluations
        ]
        if any(r.classification != dataset.classification for r in known_ranking):
            raise DataContractError("RANKING_DIAGNOSTIC_CLASSIFICATION_MISMATCH")
        payload: dict[str, Any] = dict(
            session_date=session,
            knowledge_cutoff=cutoff,
            horizon=policy.horizon,
            policy=policy,
            classification=dataset.classification,
            feature_set_id=self.risk.features.feature_set_id,
            canonical_input_id=self.risk.reader.batch.input_id,
            canonical_dataset_id=dataset.dataset_id,
            universe_snapshot_id=universe.snapshot_id,
            universe_definition_id=self.risk.reader.batch.definition.universe_id,
            prediction_set_id=digest(sorted({p.evidence_id for p in predictions})),
            risk_snapshot_ids=tuple(sorted(set(risks))),
            model_selection_status="TEST_ONLY_SELECTED_CANDIDATE"
            if ranked
            else "INSUFFICIENT_EVIDENCE",
            model_comparison=summarize(
                list(diagnostics.values()), self.comparisons, economics, known_ranking
            ),
            ranked=tuple(ranked),
            excluded=tuple(excluded),
            previous_snapshot_id=previous.rank_snapshot_id if previous else None,
            downstream_references=dict(
                price_and_benchmark="P5 canonical snapshots",
                prediction_history="P9 evaluation IDs",
                risk_history="P11 risk snapshot IDs",
                rank_history="P12 rank snapshot IDs",
                hypothetical_pnl="P10 backtest IDs when historically available",
                sector="UNAVAILABLE",
            ),
            disclaimer=disclaimer(dataset.classification),
        )
        provisional = RankSnapshot.model_construct(rank_snapshot_id="0" * 64, **payload)
        content = provisional.model_dump(mode="json", exclude={"rank_snapshot_id"})
        return RankSnapshot.model_validate(dict(rank_snapshot_id=digest(content), **content))
