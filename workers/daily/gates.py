"""Expose unchanged P11–P14 contracts, with no recalibration or synthetic outputs."""

from typing import Any

from alphalens_decision.explanation_contracts import ExplanationPolicy
from alphalens_decision.models import Horizon
from alphalens_decision.ranking_contracts import RankingPolicy
from alphalens_decision.risk_contracts import RiskPolicy
from alphalens_decision.signal_contracts import SignalPolicy


def policy_snapshot() -> dict[str, Any]:
    horizons: tuple[Horizon, ...] = (1, 5, 10, 20)
    return dict(
        risk=RiskPolicy().model_dump(mode="json"),
        rankings=[RankingPolicy(horizon=h).model_dump(mode="json") for h in horizons],
        signals=[SignalPolicy(horizon=h).model_dump(mode="json") for h in horizons],
        explanations=ExplanationPolicy().model_dump(mode="json"),
        verdict="UNAVAILABLE",
        reasons=[
            "MODEL_SELECTION_INSUFFICIENT_EVIDENCE",
            "CURRENT_VERIFIED_RISK_AND_UNIVERSE_SNAPSHOTS_UNAVAILABLE",
            "RESEARCH_CANDIDATE_NOT_PRODUCTION_PROMOTED",
        ],
        recalibration=False,
    )
