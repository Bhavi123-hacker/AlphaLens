# Real-data walk-forward status

Status: **NOT_RUN_SOURCE_GATE_BLOCKED**. No real P9 folds, OOS predictions,
predictive metrics, ranking IC, top/bottom spreads, year/regime comparisons,
stability intervals or naive comparisons were produced. They are UNAVAILABLE;
[machine-readable status](walk-forward-results.json) uses null results.

Once approved P7 cutoff-specific datasets exist, P9 must retrain each family
independently on preceding eligible history, respect label availability and
purge/embargo, fit preprocessing only on TRAIN, and test later disjoint sessions.
Later scoring outcomes remain separate from historical training vintages.
Predictive and ranking diagnostics, worst fold and folds beating naive must all
be retained, including weak periods. Current constituents cannot define the past.

2025 confirmation and a genuinely untouched 2026 final-period evaluation are
proposed if actual coverage supports them. Exact boundaries must be serialized
before any final-period results are viewed. No outer-test tuning, model selection,
loser deletion or favorable-regime selection occurred. No real candidate winner
is claimed and P11-P14 thresholds remain unchanged development assumptions.

See [source audit](../data/real-data-source-audit.md) for the blocker and
[training report](real-data-training-report.md) for unexecuted model scope.
