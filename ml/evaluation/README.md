# Evaluation boundary

P9 consumes P7 aligned scoring and cutoff-specific training snapshots. Expanding
folds retrain P8/CPU boosted baselines with train-only preprocessing and maturity
purge. Deterministic OOS predictions are the only prediction input permitted for P10.
See docs/ml/p9-walk-forward-evaluation.md. No production champion or product ranking.
