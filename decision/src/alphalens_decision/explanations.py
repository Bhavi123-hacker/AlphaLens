"""Three deterministic explanation layers, each statement tied to visible evidence."""

from typing import Any

from alphalens_data.errors import DataContractError
from alphalens_decision.attribution import verified_row
from alphalens_decision.explanation_contracts import (
    EvidenceFactor,
    ExplainabilitySnapshot,
    ExplanationPolicy,
    LocalAttribution,
)
from alphalens_decision.ranking_contracts import RankSnapshot
from alphalens_decision.risk_contracts import RiskSnapshot
from alphalens_decision.signal_contracts import SignalSnapshot
from alphalens_decision.signals import evaluate
from alphalens_evaluation.contracts import digest
from alphalens_features.models import FeatureDataset

REASON_TEXT = {
    "HIGH_OPPORTUNITY_RANK": "Rank meets the configured entry rank limit.",
    "ACCEPTABLE_RISK": "Overall risk meets the configured maximum.",
    "EXPECTED_RETURN_POSITIVE": "The model return estimate is positive; it is not guaranteed.",
    "RANK_IMPROVING": "Rank improved relative to the recorded earlier ranking.",
    "STRONG_RELATIVE_MOMENTUM": "Momentum percentile meets the policy threshold.",
    "RISK_EXCEEDS_LIMIT": "Risk is above the configured limit or unavailable.",
    "MODEL_CONFIDENCE_DROPS": "Model uncertainty exceeds the configured limit or is unavailable.",
    "MODEL_EVIDENCE_UNAVAILABLE": "Insufficient model selection blocks normal entry.",
    "DATA_QUALITY_DEGRADES": "Source quality does not meet the configured requirement.",
    "INSUFFICIENT_HISTORY": "Historical evidence does not meet the policy requirement.",
    "SOURCE_DATA_NOT_FRESH": "Complete historical EOD evidence is unavailable or stale.",
    "CORPORATE_ACTION_UNCERTAINTY": "Uncertain corporate actions limit raw-price interpretation.",
    "RANK_OR_UNIVERSE_INELIGIBLE": "Rank eligibility or usable risk evidence is missing.",
    "RANK_FALLS_BELOW_THRESHOLD": "Rank does not meet the configured entry rank limit.",
    "OPPORTUNITY_SCORE_BELOW_THRESHOLD": "Adjusted score does not meet the entry threshold.",
    "PREDICTIVE_STRENGTH_BELOW_THRESHOLD": "Model probability does not meet the entry threshold.",
    "EXPECTED_RETURN_BELOW_THRESHOLD": "Model return estimate does not meet the entry threshold.",
}
STATE_TEXT = {
    "WATCH": "Available evidence does not complete the configured setup requirements.",
    "SETUP_FORMING": "Some setup evidence exists; entry checks or confirmation are incomplete.",
    "ENTRY_SIGNAL": (
        "Configured entry or retention requirements pass. "
        "No position is established or profit guaranteed."
    ),
    "HOLD": "Explicit synthetic position evidence exists and configured continuation checks pass.",
    "TAKE_PROFIT_REVIEW": (
        "Continuation checks pass and the synthetic context requests review. "
        "No automatic exit is implied."
    ),
    "EXIT_SIGNAL": (
        "The synthetic position fails continuation checks. An exit has not been evidenced."
    ),
    "EXITED": "An exit event is evidenced in the explicit synthetic position context.",
}


def explain(
    signal: SignalSnapshot,
    ranking: RankSnapshot,
    risks: tuple[RiskSnapshot, ...],
    features: FeatureDataset | None = None,
    history: tuple[SignalSnapshot, ...] = (),
    attributions: tuple[LocalAttribution, ...] = (),
    policy: ExplanationPolicy | None = None,
) -> ExplainabilitySnapshot:
    """Reproduce P13 before explaining; optional evidence is filtered before identity."""
    policy = policy or ExplanationPolicy()
    signal = SignalSnapshot.model_validate(signal.model_dump())
    replay = evaluate(
        ranking,
        signal.security_id,
        risks,
        signal.policy,
        history,
        (signal.position_evidence,) if signal.position_evidence else (),
    )
    if replay != signal:
        raise DataContractError("EXPLANATION_SIGNAL_REPLAY_MISMATCH")
    candidate = next((r for r in ranking.ranked if r.security_id == signal.security_id), None)
    risk = next((r for r in risks if r.risk_snapshot_id == signal.risk_snapshot_id), None)
    row = (
        verified_row(features, signal.security_id, signal.session_date, signal.knowledge_cutoff)
        if features
        else None
    )
    if features and (
        features.feature_set_id != signal.feature_set_id
        or features.canonical_input_id != signal.canonical_input_id
        or features.classification != signal.classification
        or row is not None
        and (
            row.universe_snapshot_id != signal.universe_snapshot_id
            or row.classification != signal.classification
            or row.canonical_dataset_id != signal.canonical_dataset_id
        )
    ):
        # Per-cutoff P6 rows/P11/P12 pin the same snapshot, distinct from the
        # full feature dataset's source canonical dataset ID.
        raise DataContractError("EXPLANATION_FEATURE_LINEAGE_MISMATCH")
    local = [
        a
        for a in attributions
        if (
            a.prediction.security_id == signal.security_id
            and a.prediction.session_date == signal.session_date
            and a.prediction.horizon == signal.horizon
            and a.prediction.available_at <= signal.knowledge_cutoff
        )
    ]
    for a in local:
        LocalAttribution.model_validate(a.model_dump())
        p = a.prediction
        if (
            row is None
            or p.evidence_id not in signal.prediction_ids
            or p.model_run_id not in signal.model_run_ids
            or p.evaluation_id not in signal.evaluation_ids
            or p.classification != signal.classification
            or p.feature_set_id != signal.feature_set_id
            or p.decision_time != signal.decision_time
            or p.universe_snapshot_id != signal.universe_snapshot_id
            or p.canonical_dataset_id != row.canonical_dataset_id
            or a.feature_row_id != digest(row.model_dump(mode="json"))
            or a.policy != policy
            or any(c.actual_value != row.values[c.feature_name].value for c in a.contributions)
            or p.task == "classification"
            and p.probability != signal.probability
            or p.task == "regression"
            and p.prediction != signal.expected_return_estimate
        ):
            raise DataContractError("EXPLANATION_LOCAL_ATTRIBUTION_LINEAGE_MISMATCH")
    local.sort(key=lambda a: (a.prediction.task, a.prediction.model_run_id))
    if len({a.prediction.evidence_id for a in local}) != len(local):
        raise DataContractError("AMBIGUOUS_LOCAL_EXPLANATION")
    feature_values = (
        {
            name: dict(
                value=value.value,
                availability=value.state.value,
                reasons=value.reason_codes,
                source_reference=f"{signal.feature_set_id}:{name}",
            )
            for name, value in sorted(row.values.items())
        }
        if row
        else {}
    )
    evidence = dict(
        entry_conditions=signal.entry_conditions,
        retention_conditions=signal.retention_conditions,
        thresholds=signal.policy.model_dump(mode="json"),
        rank=signal.opportunity_rank,
        adjusted_score=signal.risk_adjusted_score,
        probability=signal.probability,
        expected_return=signal.expected_return_estimate,
        risk=signal.risk_level,
        quality=signal.quality,
        momentum_percentile=candidate.components["p6_momentum_percentile"] if candidate else None,
        rank_change=candidate.rank_change if candidate else None,
    )

    def factor(code: str) -> EvidenceFactor:
        return EvidenceFactor(
            code=code,
            text=REASON_TEXT.get(code, f"Recorded evidence flag: {code}."),
            source_reference=signal.signal_snapshot_id,
            evidence=evidence,
        )

    positive = [factor(c) for c in signal.positive_reasons]
    negative = [factor(c) for c in signal.negative_reasons]
    # Rank local factors by magnitude within each output space; never aggregate
    # probability points, log odds and return units into an invented importance.
    for attribution in local:
        for direction, factors in (("POSITIVE", positive), ("NEGATIVE", negative)):
            top = sorted(
                (c for c in attribution.contributions if c.direction == direction),
                key=lambda c: (-abs(c.contribution), c.feature_name),
            )[: policy.top_factors]
            for contribution in top:
                c = contribution
                factors.append(
                    EvidenceFactor(
                        code=f"LOCAL_{direction}:{attribution.prediction.task}:{c.feature_name}",
                        text=(
                            f"{c.feature_name} = "
                            f"{c.actual_value if c.actual_value is not None else 'unavailable'}; "
                            f"local model contribution {c.contribution:+.{policy.display_digits}g} "
                            f"in {attribution.output_space} using {attribution.method}."
                        ),
                        source_reference=attribution.attribution_id,
                        evidence=c.model_dump(mode="json"),
                    )
                )
    missing = [
        (
            "FUNDAMENTAL_PIT_UNAVAILABLE",
            "Fundamental PIT analysis unavailable.",
            signal.feature_set_id,
        ),
        ("NEWS_UNAVAILABLE", "News and sentiment analysis unavailable.", "P14_OFFLINE_SCOPE"),
        (
            "LIVE_INTRADAY_UNAVAILABLE",
            "Live/intraday data unavailable; this is historical EOD evidence.",
            "EOD_V1",
        ),
        (
            "TECHNICAL_PRICE_INVALIDATION_UNAVAILABLE",
            "Technical price invalidation unavailable; no approved price-level policy.",
            signal.policy.price_invalidation_policy,
        ),
    ]
    benchmark = {
        name: value
        for name, value in feature_values.items()
        if features
        and next(
            d for d in features.feature_set.definitions if d.feature_name == name
        ).feature_family
        == "MARKET_CONTEXT"
    }
    if not benchmark or not any(v["value"] is not None for v in benchmark.values()):
        missing.append(
            (
                "BENCHMARK_UNAVAILABLE",
                "Benchmark context unavailable at this decision.",
                signal.feature_set_id,
            )
        )
    if features is None or features.corporate_action_coverage == "NOT_ESTABLISHED":
        missing.append(
            (
                "CORPORATE_ACTION_COVERAGE_NOT_ESTABLISHED",
                "Complete corporate-action coverage is not established.",
                signal.feature_set_id,
            )
        )
    if row is None:
        missing.append(
            (
                "FEATURE_ROW_UNAVAILABLE",
                "Decision feature values unavailable; no values have been substituted.",
                signal.feature_set_id,
            )
        )
    explained_ids = {a.prediction.evidence_id for a in local}
    if set(signal.prediction_ids) - explained_ids or not signal.prediction_ids:
        missing.append(
            (
                "LOCAL_ATTRIBUTION_UNAVAILABLE",
                "Local attribution unavailable for one or more predictions; "
                "no feature importance is inferred.",
                signal.signal_snapshot_id,
            )
        )
    missing.append(
        (
            "INDEPENDENT_MODEL_VALIDATION_INSUFFICIENT",
            "Independent model-selection/calibration evidence is insufficient; "
            "fixture metrics are not a market track record.",
            ranking.rank_snapshot_id,
        )
    )
    weights = dict(
        probability=ranking.policy.probability_weight,
        normalized_return=ranking.policy.return_weight,
        p6_momentum_percentile=ranking.policy.context_weight,
    )
    observed = {
        name: weight
        for name, weight in weights.items()
        if candidate and candidate.components[name] is not None and weight > 0
    }
    denominator = sum(observed.values())
    breakdown = dict(
        rank=signal.opportunity_rank,
        raw_score=signal.raw_score,
        adjusted_score=signal.risk_adjusted_score,
        normalized_components=candidate.components if candidate else {},
        weighted_raw_contributions={
            name: value * observed[name] / denominator
            for name, value in candidate.components.items()
            if name in observed and value is not None
        }
        if candidate
        else {},
        penalties=candidate.penalties if candidate else {},
        ranking_policy=ranking.policy.model_dump(mode="json"),
        threshold_status="DEVELOPMENT_ASSUMPTION",
        interpretation="Ordering score; not confidence or expected profit.",
        ordering_policy=ranking.policy.tie_policy,
        cohort_size=len(ranking.ranked),
        excluded_count=len(ranking.excluded),
        previous_rank=candidate.previous_rank if candidate else None,
        rank_change=candidate.rank_change if candidate else None,
        why_rank=(
            "Descending adjusted scores, with security ID breaking ties."
            if candidate
            else "Excluded from ranking; no ordinal rank assigned."
        ),
        peer_adjusted_scores=[
            dict(security_id=r.security_id, rank=r.rank, adjusted_score=r.risk_adjusted_score)
            for r in ranking.ranked
        ],
    )
    shared_actual = dict(
        eligible=candidate is not None and bool(risk and risk.analysis_permitted),
        risk=signal.risk_level,
        uncertainty=risk.components["model_uncertainty"].severity if risk else None,
        quality=signal.quality,
        history=risk.evidence_sufficiency if risk else "UNAVAILABLE",
        model_evidence=signal.model_confidence,
        freshness=signal.data_freshness,
        corporate_action=risk.components["corporate_action_risk"].model_dump(mode="json")
        if risk
        else None,
        rank=signal.opportunity_rank,
        score=signal.risk_adjusted_score,
        probability=signal.probability,
        **{"return": signal.expected_return_estimate},
    )
    summary = [
        signal.disclaimer,
        STATE_TEXT[signal.state],
        f"Model horizon: {signal.horizon} sessions. Each horizon is evaluated independently.",
        "Signal/ranking thresholds are DEVELOPMENT_ASSUMPTION; NSE calibration is unavailable.",
    ]
    unmet = tuple(k.replace("_", " ") for k, v in sorted(signal.entry_conditions.items()) if not v)
    if unmet:
        summary.append("Entry requirements still unmet: " + ", ".join(unmet) + ".")
    elif signal.confirmation_count < signal.policy.confirmation_observations:
        summary.append(
            f"Entry confirmation: {signal.confirmation_count} qualifying observations; "
            f"policy requires {signal.policy.confirmation_observations}."
        )
    summary.append(
        "Possible entry requires every reported entry check and the configured confirmation. "
        "Worsening evidence can invalidate continuation; no transition is promised."
    )
    if signal.probability is not None:
        summary.append(
            f"Model positive-class probability: {signal.probability:.{policy.display_digits}g}; "
            "calibrated signal confidence is unavailable."
        )
    if signal.expected_return_estimate is not None:
        summary.append(
            f"Model estimated {signal.horizon}-session return: "
            f"{100 * signal.expected_return_estimate:+.{policy.display_digits}g}%. "
            "MODEL ESTIMATE — NOT GUARANTEED."
        )
    if signal.policy.test_only_state_demonstration:
        summary.append(
            "Explicit synthetic TEST_ONLY state demonstration; "
            "no validated market entry or user holding is established."
        )
    if signal.preferred_review_horizon is not None:
        summary.append(
            f"Configured review horizon: {signal.preferred_review_horizon} sessions; "
            "no promised holding period or profit."
        )
    lineage = dict(
        signal_snapshot_id=signal.signal_snapshot_id,
        ranking_snapshot_id=signal.ranking_snapshot_id,
        risk_snapshot_id=signal.risk_snapshot_id,
        prediction_ids=signal.prediction_ids,
        model_run_ids=signal.model_run_ids,
        evaluation_ids=signal.evaluation_ids,
        feature_set_id=signal.feature_set_id,
        canonical_input_id=signal.canonical_input_id,
        canonical_dataset_id=signal.canonical_dataset_id,
        universe_snapshot_id=signal.universe_snapshot_id,
        universe_definition_id=signal.universe_definition_id,
        feature_row_id=digest(row.model_dump(mode="json")) if row else None,
        feature_input_versions=row.input_versions if row else (),
        feature_input_revision_keys=row.input_revision_keys if row else (),
        cutoff_canonical_snapshot_id=row.canonical_dataset_id if row else None,
        feature_source_canonical_dataset_id=features.canonical_dataset_id if features else None,
        symbol_at_decision=signal.symbol,
        classification=signal.classification.value,
        risk_policy=risk.policy.model_dump(mode="json") if risk else None,
        ranking_policy_id=ranking.policy.policy_id,
        ranking_policy_version=ranking.policy.version,
        signal_policy_id=signal.policy.policy_id,
        signal_policy_version=signal.policy.version,
        explanation_policy=policy.model_dump(mode="json"),
        versions=dict(
            signal=signal.signal_engine_version,
            ranking=ranking.ranking_version,
            risk=risk.risk_engine_version if risk else None,
            features=features.schema_version if features else None,
            model="p8.baseline.v1 / p9.walk_forward.v1",
            canonical="p5.canonical.v1",
            universe="P4",
            quality="P3",
        ),
        previous_signal_snapshot_id=signal.previous_signal_snapshot_id,
        position_evidence_id=signal.position_evidence.evidence_id
        if signal.position_evidence
        else None,
        attribution_ids=tuple(a.attribution_id for a in local),
        fundamental_pit_data="UNAVAILABLE",
        production_data_clearance="OPEN",
        production_market_data_use="NOT_CLEARED",
    )
    payload: dict[str, Any] = dict(
        policy=policy,
        signal_snapshot_id=signal.signal_snapshot_id,
        security_id=signal.security_id,
        symbol=signal.symbol,
        session_date=signal.session_date,
        knowledge_cutoff=signal.knowledge_cutoff,
        horizon=signal.horizon,
        state=signal.state,
        headline=(
            f"{signal.classification.value}: {signal.symbol or signal.security_id} "
            f"— {signal.state} — {signal.horizon} sessions"
        ),
        plain_language_summary=tuple(summary),
        positive_factors=tuple(positive),
        negative_factors=tuple(negative),
        risk_factors=dict(
            overall_level=signal.risk_level,
            policy="WORST_COMPONENT_ESSENTIAL_FAILURE_UNAVAILABLE",
            components={n: c.model_dump(mode="json") for n, c in sorted(risk.components.items())}
            if risk
            else {},
            source_quality=signal.quality,
            missing_risk_snapshot=risk is None,
        ),
        missing_evidence=tuple(
            EvidenceFactor(
                code=c, text=t, source_reference=s, evidence=dict(availability="UNAVAILABLE")
            )
            for c, t, s in missing
        ),
        feature_values=feature_values,
        feature_contributions=tuple(local),
        model_evidence=dict(
            probability=signal.probability,
            expected_return_estimate=signal.expected_return_estimate,
            expected_return_label=signal.expected_return_label,
            expected_return_unit="FRACTIONAL_RETURN",
            model_confidence=signal.model_confidence,
            signal_confidence=signal.signal_confidence,
            model_comparison=ranking.model_comparison,
            local_scope="LOCAL_PREDICTION",
            global_importance="UNAVAILABLE_NOT_USED_AS_LOCAL",
            uncertainty=risk.components["model_uncertainty"].model_dump(mode="json")
            if risk
            else None,
        ),
        ranking_breakdown=breakdown,
        invalidation_conditions=signal.invalidation_conditions,
        state_transition_conditions=dict(
            current_trigger=signal.transition_reasons,
            entry_checks=signal.entry_conditions,
            continuation_checks=signal.retention_conditions,
            observed_values=shared_actual,
            required_policy=signal.policy.model_dump(mode="json"),
            why_not_entry=tuple(k for k, v in sorted(signal.entry_conditions.items()) if not v),
            confirmation=dict(
                observed=signal.confirmation_count, required=signal.policy.confirmation_observations
            ),
            entry_retained_by_hysteresis="ENTRY_RETAINED_BY_HYSTERESIS"
            in signal.transition_reasons,
            position_boundary=(
                "HOLD/review/exit require explicit position context; "
                "EXITED requires evidenced exit."
            ),
            review_boundary="Explicit contemporaneous synthetic review request; no automatic exit.",
            interpretation="Conditions describe possible transitions; no transition is promised.",
        ),
        data_freshness=dict(
            as_of_session=signal.session_date.isoformat(),
            knowledge_cutoff=signal.knowledge_cutoff.isoformat(),
            freshness=signal.data_freshness,
            availability=signal.availability,
            observed_price_available_at=signal.observed_price_available_at.isoformat()
            if signal.observed_price_available_at
            else None,
            quality=signal.quality,
            scope="HISTORICAL_EOD_NOT_LIVE",
        ),
        lineage=lineage,
        classification=signal.classification,
        disclaimer=signal.disclaimer,
    )
    draft = ExplainabilitySnapshot.model_construct(explanation_id="0" * 64, **payload)
    content = draft.model_dump(mode="json", exclude={"explanation_id"})
    return ExplainabilitySnapshot.model_validate(dict(explanation_id=digest(content), **content))
