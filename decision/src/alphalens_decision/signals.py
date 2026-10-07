"""Pure past-only transition engine over approved immutable P12/P11 evidence."""

from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.quality.models import QualityStatus
from alphalens_decision.ranking_contracts import RankSnapshot
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_decision.signal_contracts import PositionEvidence, SignalPolicy, SignalSnapshot
from alphalens_evaluation.contracts import digest, disclaimer

LEVELS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "VERY_HIGH": 3, "UNAVAILABLE": 4}
FAILURES = {
    "rank": "RANK_FALLS_BELOW_THRESHOLD",
    "score": "OPPORTUNITY_SCORE_BELOW_THRESHOLD",
    "probability": "PREDICTIVE_STRENGTH_BELOW_THRESHOLD",
    "return": "EXPECTED_RETURN_BELOW_THRESHOLD",
    "risk": "RISK_EXCEEDS_LIMIT",
    "uncertainty": "MODEL_CONFIDENCE_DROPS",
    "quality": "DATA_QUALITY_DEGRADES",
    "history": "INSUFFICIENT_HISTORY",
    "model_evidence": "MODEL_EVIDENCE_UNAVAILABLE",
    "eligible": "RANK_OR_UNIVERSE_INELIGIBLE",
    "freshness": "SOURCE_DATA_NOT_FRESH",
    "corporate_action": "CORPORATE_ACTION_UNCERTAINTY",
}


def evaluate(
    ranking: RankSnapshot,
    security_id: str,
    risks: tuple[RiskSnapshot, ...],
    policy: SignalPolicy,
    history: tuple[SignalSnapshot, ...] = (),
    positions: tuple[PositionEvidence, ...] = (),
) -> SignalSnapshot:
    ranking = RankSnapshot.model_validate(ranking.model_dump())
    if ranking.horizon != policy.horizon or (
        policy.test_only_state_demonstration and ranking.classification != Classification.TEST_ONLY
    ):
        raise DataContractError("SIGNAL_POLICY_CLASSIFICATION_OR_HORIZON_MISMATCH")
    candidate = next((r for r in ranking.ranked if r.security_id == security_id), None)
    excluded = next((r for r in ranking.excluded if r.security_id == security_id), None)
    if candidate is None and excluded is None:
        raise DataContractError("SECURITY_NOT_KNOWN_AT_RANKING_DECISION")
    risk_id = (
        candidate.risk_snapshot_id if candidate else excluded.risk_snapshot_id if excluded else None
    )
    visible = [
        r
        for r in risks
        if r.security_id == security_id
        and r.horizon == policy.horizon
        and r.session_date == ranking.session_date
        and r.knowledge_cutoff <= ranking.knowledge_cutoff
    ]
    if len(visible) > 1:
        raise DataContractError("AMBIGUOUS_SIGNAL_RISK_EVIDENCE")
    risk = visible[0] if visible else None
    if risk:
        risk = RiskSnapshot.model_validate(risk.model_dump())
        if (
            risk.risk_snapshot_id != risk_id
            or risk.knowledge_cutoff != ranking.knowledge_cutoff
            or risk.classification != ranking.classification
            or risk.feature_set_id != ranking.feature_set_id
            or risk.canonical_input_id != ranking.canonical_input_id
            or risk.canonical_dataset_id != ranking.canonical_dataset_id
            or risk.universe_snapshot_id != ranking.universe_snapshot_id
            or risk.universe_definition_id != ranking.universe_definition_id
            or risk.policy != ranking.policy.risk_policy
            or candidate is not None
            and (
                candidate.overall_risk != risk.overall_level
                or candidate.quality_state != risk.source_quality
                or candidate.observed_price_available_at != risk.observed_price_available_at
                or not set(candidate.prediction_evidence_ids).issubset(risk.prediction_evidence_ids)
            )
        ):
            raise DataContractError("SIGNAL_RISK_RANKING_LINEAGE_MISMATCH")
    past = [
        s
        for s in history
        if s.security_id == security_id
        and s.horizon == policy.horizon
        and s.session_date < ranking.session_date
        and s.knowledge_cutoff < ranking.knowledge_cutoff
        and s.policy == policy
        and s.classification == ranking.classification
        and s.universe_definition_id == ranking.universe_definition_id
    ]
    for s in past:
        SignalSnapshot.model_validate(s.model_dump())
    if len({s.session_date for s in past}) != len(past):
        raise DataContractError("AMBIGUOUS_SIGNAL_HISTORY")
    past.sort(key=lambda s: s.session_date)
    previous = past[-1] if past else None
    contexts = [
        p
        for p in positions
        if p.security_id == security_id
        and p.horizon == policy.horizon
        and p.available_at <= ranking.knowledge_cutoff
        and p.entry_at < ranking.knowledge_cutoff
    ]
    contexts.sort(key=lambda p: p.available_at)
    if len({p.available_at for p in contexts}) != len(contexts):
        raise DataContractError("AMBIGUOUS_POSITION_EVIDENCE")
    position = contexts[-1] if contexts else None
    if position and ranking.classification != Classification.TEST_ONLY:
        raise DataContractError("SYNTHETIC_POSITION_CLASSIFICATION_MISMATCH")
    if position:
        PositionEvidence.model_validate(position.model_dump())
    price_time = risk.observed_price_available_at if risk else None
    freshness = (
        "STALE"
        if risk and risk.feature_availability == "STALE"
        else "EOD_COMPLETE"
        if price_time is not None
        and price_time <= ranking.knowledge_cutoff
        and risk
        and risk.analysis_permitted
        else "UNAVAILABLE"
    )
    uncertainty = risk.components["model_uncertainty"].severity if risk else None
    quality = (
        str(
            risk.source_quality.value
            if isinstance(risk.source_quality, QualityStatus)
            else risk.source_quality
        )
        if risk
        else "UNAVAILABLE"
    )
    probability = candidate.probability if candidate else None
    estimated_return = candidate.predicted_return if candidate else None
    demonstration = (
        policy.test_only_state_demonstration and ranking.classification == Classification.TEST_ONLY
    )
    shared = dict(
        eligible=bool(candidate and risk and risk.analysis_permitted),
        risk=bool(risk and LEVELS[risk.overall_level] <= LEVELS[policy.maximum_risk]),
        uncertainty=uncertainty is not None and uncertainty <= policy.maximum_model_uncertainty,
        quality=quality == "VALID" or not policy.require_valid_quality and quality == "DEGRADED",
        history=bool(risk and risk.evidence_sufficiency == "SUFFICIENT"),
        model_evidence=bool(demonstration),
        freshness=freshness == "EOD_COMPLETE",
        corporate_action=bool(
            risk
            and not any(
                reason in {"KNOWN_UNADJUSTED_CORPORATE_ACTION", "CORPORATE_ACTION_UNCERTAINTY"}
                for reason in risk.components["corporate_action_risk"].reasons
            )
        ),
    )
    entry = dict(
        shared,
        rank=bool(candidate and candidate.rank <= policy.entry_maximum_rank),
        score=bool(candidate and candidate.risk_adjusted_score >= policy.entry_minimum_score),
        probability=probability is not None and probability >= policy.entry_minimum_probability,
        **{
            "return": estimated_return is not None
            and estimated_return >= policy.entry_minimum_return
        },
    )
    retain = dict(
        shared,
        rank=bool(candidate and candidate.rank <= policy.retain_maximum_rank),
        score=bool(candidate and candidate.risk_adjusted_score >= policy.retain_minimum_score),
        probability=probability is not None and probability >= policy.retain_minimum_probability,
        **{
            "return": estimated_return is not None
            and estimated_return >= policy.retain_minimum_return
        },
    )
    confirmations = int(all(entry.values()))
    if confirmations:
        next_date = ranking.session_date
        for s in reversed(past):
            if (next_date - s.session_date).days > policy.maximum_history_gap_days or not all(
                s.entry_conditions.values()
            ):
                break
            confirmations += 1
            next_date = s.session_date
    negative = set(excluded.reasons if excluded else ())
    negative.update(FAILURES[k] for k, passed in entry.items() if not passed)
    if risk:
        negative.update(risk.reasons)
    positive = set()
    if entry["rank"]:
        positive.add("HIGH_OPPORTUNITY_RANK")
    if entry["risk"]:
        positive.add("ACCEPTABLE_RISK")
    if estimated_return is not None and estimated_return > 0:
        positive.add("EXPECTED_RETURN_POSITIVE")
    if candidate and candidate.rank_change is not None and candidate.rank_change > 0:
        positive.add("RANK_IMPROVING")
    if (
        candidate
        and candidate.components["p6_momentum_percentile"] is not None
        and candidate.components["p6_momentum_percentile"] >= policy.positive_momentum_percentile
    ):
        positive.add("STRONG_RELATIVE_MOMENTUM")
    if position:
        if position.exit_at is not None:
            state, trigger = "EXITED", "EVIDENCED_SYNTHETIC_EXIT"
        elif not all(retain.values()):
            state, trigger = "EXIT_SIGNAL", "CONTINUATION_REQUIREMENTS_FAILED"
        elif position.profit_review_requested:
            state, trigger = "TAKE_PROFIT_REVIEW", "EXPLICIT_SYNTHETIC_REVIEW_REQUEST"
        else:
            state, trigger = "HOLD", "EVIDENCED_ACTIVE_SYNTHETIC_POSITION"
    elif previous and previous.state == "ENTRY_SIGNAL" and all(retain.values()):
        state, trigger = "ENTRY_SIGNAL", "ENTRY_RETAINED_BY_HYSTERESIS"
    elif all(entry.values()) and confirmations >= policy.confirmation_observations:
        state, trigger = "ENTRY_SIGNAL", "ENTRY_REQUIREMENTS_CONFIRMED"
    elif (
        candidate
        and candidate.risk_adjusted_score >= policy.setup_minimum_score
        and (
            probability is not None
            and probability >= policy.retain_minimum_probability
            or estimated_return is not None
            and estimated_return > policy.retain_minimum_return
        )
        and shared["eligible"]
        and shared["risk"]
        and shared["freshness"]
    ):
        state, trigger = "SETUP_FORMING", "FAVORABLE_BUT_INCOMPLETE_ENTRY_EVIDENCE"
    else:
        state, trigger = "WATCH", "ENTRY_AND_SETUP_REQUIREMENTS_NOT_MET"
    invalidation = dict(
        RISK_EXCEEDS_LIMIT=policy.maximum_risk,
        MODEL_CONFIDENCE_DROPS=policy.maximum_model_uncertainty,
        PREDICTIVE_STRENGTH_BELOW_THRESHOLD=policy.retain_minimum_probability,
        RANK_FALLS_BELOW_THRESHOLD=policy.retain_maximum_rank,
        OPPORTUNITY_SCORE_BELOW_THRESHOLD=policy.retain_minimum_score,
        EXPECTED_RETURN_BELOW_THRESHOLD=policy.retain_minimum_return,
        DATA_QUALITY_DEGRADES="VALID" if policy.require_valid_quality else "VALID_OR_DEGRADED",
        CORPORATE_ACTION_UNCERTAINTY="KNOWN_OR_UNVERIFIED_ACTION_STATE",
        MODEL_EVIDENCE_UNAVAILABLE="REQUIRED_EVIDENCE_MISSING",
        SOURCE_DATA_NOT_FRESH="EOD_COMPLETE_REQUIRED",
        INSUFFICIENT_HISTORY="SUFFICIENT_REQUIRED",
        RANK_OR_UNIVERSE_INELIGIBLE="ELIGIBLE_REQUIRED",
        TECHNICAL_PRICE_INVALIDATION="UNAVAILABLE_NO_APPROVED_PRICE_POLICY",
    )
    payload: dict[str, Any] = dict(
        security_id=security_id,
        symbol=candidate.symbol if candidate else excluded.symbol if excluded else None,
        session_date=ranking.session_date,
        decision_time=ranking.knowledge_cutoff,
        knowledge_cutoff=ranking.knowledge_cutoff,
        horizon=policy.horizon,
        policy=policy,
        context="POSITION_DECISION_STATE" if position else "MARKET_OPPORTUNITY_STATE",
        state=state,
        previous_state=previous.state if previous else None,
        previous_signal_snapshot_id=previous.signal_snapshot_id if previous else None,
        confirmation_count=confirmations,
        entry_conditions=entry,
        retention_conditions=retain,
        opportunity_rank=candidate.rank if candidate else None,
        raw_score=candidate.raw_opportunity_score if candidate else None,
        risk_adjusted_score=candidate.risk_adjusted_score if candidate else None,
        risk_level=risk.overall_level if risk else "UNAVAILABLE",
        model_confidence=candidate.model_confidence if candidate else "INSUFFICIENT_EVIDENCE",
        signal_confidence="TEST_ONLY_DEVELOPMENT_EVIDENCE"
        if demonstration and all(shared.values())
        else "INSUFFICIENT_EVIDENCE",
        probability=probability,
        expected_return_estimate=estimated_return,
        prediction_horizon=policy.horizon,
        preferred_review_horizon=policy.review_horizon,
        invalidation_conditions=invalidation,
        positive_reasons=tuple(sorted(positive)),
        negative_reasons=tuple(sorted(negative)),
        transition_reasons=(trigger,),
        ranking_snapshot_id=ranking.rank_snapshot_id,
        risk_snapshot_id=risk.risk_snapshot_id if risk else None,
        prediction_ids=candidate.prediction_evidence_ids if candidate else (),
        model_run_ids=candidate.model_run_ids if candidate else (),
        evaluation_ids=candidate.evaluation_ids if candidate else (),
        feature_set_id=ranking.feature_set_id,
        canonical_input_id=ranking.canonical_input_id,
        canonical_dataset_id=ranking.canonical_dataset_id,
        universe_snapshot_id=ranking.universe_snapshot_id,
        universe_definition_id=ranking.universe_definition_id,
        observed_price_available_at=price_time,
        data_freshness=freshness,
        availability="DEGRADED"
        if candidate and risk and freshness == "EOD_COMPLETE"
        else "UNAVAILABLE",
        quality=quality,
        classification=ranking.classification,
        position_evidence=position,
        disclaimer=disclaimer(ranking.classification),
    )
    draft = SignalSnapshot.model_construct(signal_snapshot_id="0" * 64, **payload)
    content = draft.model_dump(mode="json", exclude={"signal_snapshot_id"})
    return SignalSnapshot.model_validate(dict(signal_snapshot_id=digest(content), **content))
