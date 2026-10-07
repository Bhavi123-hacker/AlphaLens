"""Explain approved TEST_ONLY signals, including safely loaded selected P9 models."""

import argparse
from collections import Counter
from pathlib import Path

from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_decision.evidence import project
from alphalens_decision.explanation_models import from_p9
from alphalens_decision.explanation_storage import load, save
from alphalens_decision.explanations import explain
from alphalens_decision.ranking_storage import load as load_rank
from alphalens_decision.risk_storage import load as load_risk
from alphalens_decision.signal_storage import load as load_signal
from alphalens_evaluation.contracts import disclaimer
from alphalens_evaluation.storage import load as load_oos
from alphalens_features.models import FeatureDataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("signals", "rankings", "risks", "features", "evaluations", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    features = FeatureDataset.model_validate_json(args.features.read_bytes())
    signals = tuple(load_signal(p.parent) for p in args.signals.glob("*/signal-manifest.json"))
    risks = tuple(load_risk(p.parent) for p in args.risks.glob("*/risk-manifest.json"))
    predictions = {}
    paths = {}
    for path in sorted(args.evaluations.glob("*/walk-forward-manifest.json")):
        oos = load_oos(path.parent)
        # Deliberately project predictions only: no future fold diagnostics.
        for p in project(oos).predictions:
            predictions[p.evidence_id] = p
            paths[p.evaluation_id] = path.parent
    if not signals or any(s.classification != Classification.TEST_ONLY for s in signals):
        raise ValueError("Authored TEST_ONLY signals required")
    results = []
    methods: Counter[str] = Counter()
    for signal in sorted(signals, key=lambda s: (s.session_date, s.horizon, s.security_id)):
        ranking = load_rank(args.rankings / signal.ranking_snapshot_id)
        attributes = tuple(
            from_p9(paths[p.evaluation_id], p, features)
            for identity in signal.prediction_ids
            if (p := predictions.get(identity)) is not None
        )
        first = explain(signal, ranking, risks, features, signals, attributes)
        if first != explain(signal, ranking, risks, features, signals, attributes):
            raise ValueError("Explanation replay mismatch")
        if load(save(first, args.output)) != first:
            raise ValueError("Explanation artifact replay mismatch")
        methods.update(a.method for a in attributes)
        results.append(first)
    report = dict(
        classification="TEST_ONLY",
        disclaimer=disclaimer(Classification.TEST_ONLY),
        production_claims_permitted=False,
        deterministic_replay=True,
        snapshot_count=len(results),
        annotation_count=len(results),
        horizons=[1, 5, 10, 20],
        states=dict(Counter(r.state for r in results)),
        local_attribution_methods=dict(methods),
        explanation_ids=[r.explanation_id for r in results],
        missing_evidence_counts=dict(Counter(f.code for r in results for f in r.missing_evidence)),
        threshold_status="DEVELOPMENT_ASSUMPTION",
        shap_new_dependency=False,
        production_data_clearance="OPEN",
        production_market_data_use="NOT_CLEARED",
    )
    publish(args.output / "explanation-suite.TEST_ONLY.json", stable_json(report))
    print(f"{len(results)} deterministic TEST_ONLY explanations/annotations; {dict(methods)}")
    print(disclaimer(Classification.TEST_ONLY))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
