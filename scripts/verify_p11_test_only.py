"""Replay authored risk evidence twice; no new data, model fitting or performance claim."""

import argparse
import json
from collections import Counter
from pathlib import Path

from alphalens_data.canonical.assembly import verify_local_batch
from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_data.quality.files import local_output
from alphalens_decision.evidence import load_models
from alphalens_decision.risk import RiskEngine
from alphalens_decision.risk_storage import load, save
from alphalens_evaluation.contracts import disclaimer
from alphalens_features.models import FeatureDataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--evaluations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    envelope = json.loads((args.inputs / "canonical/canonical-input.json").read_bytes())
    batch = verify_local_batch(
        CanonicalBatch.model_validate(envelope["batch"]), envelope["artifact_roots"]
    )
    if batch.classification != Classification.TEST_ONLY:
        raise ValueError("This replay script accepts authored TEST_ONLY inputs only")
    features = FeatureDataset.model_validate_json((args.inputs / "features.json").read_bytes())
    models = load_models(
        sorted(p.parent for p in args.evaluations.glob("*/walk-forward-manifest.json"))
    )
    if models is None:
        raise ValueError("Verified P9 model evidence required")
    sessions = {p.session_date for p in models.predictions}
    engine = RiskEngine(CanonicalReader(batch), features, models)
    snapshots = []
    for row in features.rows:
        if row.session_date not in sessions:
            continue
        for horizon in (1, 5, 10, 20):
            first = engine.evaluate(row.security_id, row.session_date, horizon)
            second = engine.evaluate(row.security_id, row.session_date, horizon)
            if first != second:
                raise ValueError("Risk replay mismatch")
            directory = save(first, args.output)
            if load(directory) != first:
                raise ValueError("Risk storage round-trip mismatch")
            snapshots.append(first)
    report = dict(
        classification="TEST_ONLY",
        disclaimer=disclaimer(Classification.TEST_ONLY),
        production_claims_permitted=False,
        deterministic_replay=True,
        snapshot_count=len(snapshots),
        horizons=[1, 5, 10, 20],
        risk_levels=dict(Counter(r.overall_level for r in snapshots)),
        availability=dict(Counter(r.availability.value for r in snapshots)),
        reasons=dict(Counter(reason for row in snapshots for reason in row.reasons)),
        feature_set_id=features.feature_set_id,
        canonical_input_id=batch.input_id,
        model_evaluations=sorted({p.evaluation_id for p in models.predictions}),
        risk_snapshot_ids=[r.risk_snapshot_id for r in snapshots],
    )
    publish(local_output(args.output) / "risk-suite.TEST_ONLY.json", stable_json(report))
    print(stable_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
