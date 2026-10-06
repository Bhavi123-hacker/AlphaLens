# P9 walk-forward development verification

Date: 2026-10-06. Branch: p9-p10-evaluation-backtesting.
Approved baseline: 58159b7aa321ee3207d50d232b8ccca97a757176 (P8).
P9 DEVELOPMENT PASSED. P10 has not started; P9 must be committed first.

First commands were git status, git branch --show-current and git log --oneline -8.
Clean p8-baseline-ml matched approved P8; P8 DEVELOPMENT PASSED was documented,
P9/P10 directories were deferred, and production clearance remained OPEN/use
NOT_CLEARED. Created the new branch directly from P8; main is unchanged at
9fa82284936f8b7a34f5409ba25cdce3538747b6. Source DOCX remains SHA256
196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a.
Requested P6/P7/P8 docs/reports/results and package contracts were inspected.
P2–P8 library behavior and database schemas were preserved.

See [P9 contract](../ml/p9-walk-forward-evaluation.md) for exact policies.
Three disjoint expanding folds retrain six families per task independently for
1/5/10/20 sessions. CPU LightGBM 4.6.0/CatBoost 1.2.8/XGBoost 3.0.5 were verified
free/open-source, installed and pinned; CPU XGBoost avoids NCCL/GPU dependencies.
P7 cutoff-specific TRAIN datasets prevent later target revisions entering earlier
folds. TRAIN-only preprocessing, maturity/availability purge and explicit embargo
preserve earlier knowledge. No tuning or production champion exists.

The deterministic arena script executed eight task/horizon evaluations twice:
144 fold models per pass and 960 OOS predictions. Replay matched manifests,
predictions, fold metrics and negative controls. Parquet/JSON/skops audit artifacts
were persisted locally and integrity-checked; developer CLI exercised the same
contract. A final replay verified all eight manifests/960 OOS rows with explicit
fold training-dataset and effective-cutoff guards. Metrics, naive deltas, fold
stability and negative controls are retained in
[machine-readable TEST_ONLY evidence](p9-walk-forward-results.TEST_ONLY.json).
All results: **TEST_ONLY — NOT A PERFORMANCE CLAIM**. No real predictive accuracy,
model superiority, investment return or historical NSE universe is demonstrated.
Ranking diagnostics are unavailable in the small integrated cross-section; a
five-security authored diagnostic verifies IC/top/bottom formulas. Uncertainty
and regime analysis remain unavailable for this fixture, with explicit reasons.

OOS issuance uses feature/universe eligibility at decision time. Missing/rejected
future outcomes remain nullable, explicitly excluded from metrics and retained as
predictions for P10. This prevents erasing an earlier prediction because a later
delisting/terminal outcome is unknown. TRAIN eligibility is never upgraded.

Development failures were handled honestly: LightGBM initially warned about
generated names; its train-only imputer now preserves matching output names.
CatBoost 1.2.8 lacked the newer sklearn tag protocol; a small BaseEstimator adapter
implements the public protocol without suppressing warnings. P7 rejects outcome
scope/cutoff before supplied feature decisions, so fold snapshots use historical
P6 plans and P7's existing builders unchanged. A fixed ranking test caught the
incorrect truthiness fallback for probability zero; explicit nullable comparison
corrected it. An initial focused run had 17 passed/one sorting failure, corrected
before the final gate. A preliminary full PostgreSQL run was interrupted to add
the missing-outcome OOS guard; its dedicated resources were explicitly torn down
before starting the final regression. Intermediate reports are not claimed passed.

P1_PRODUCTION_DATA_CLEARANCE = OPEN.
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
No new market data acquisition, secrets or paid dependency/service introduced.
P10 requires this gate and a separate P9 commit first. P11 onward remains deferred.

## Final gates

- Full `pytest -W error -ra --tb=short` on real PostgreSQL 17: **311 passed,
  one production/live-provider gate skipped**, 1188.91 seconds; no test warnings.
- All 18 new P9 cases passed, including all tasks/horizons/families, fresh per-fold
  preprocessors, chronology/maturity/embargo, genuine OOS membership, tamper checks,
  future actions/current classification revisions/listings and deterministic replay.
- `uv lock --check` / `uv sync --frozen`: PASS (94 resolved / 93 checked packages).
- Ruff check/format: PASS (161 files). Strict mypy: PASS (101 source files).
- Bandit API/data/features/labels/training/evaluation: PASS, 8380 lines, zero findings.
- Dependency audit: no known vulnerabilities; editable workspace packages excluded
  by the existing audit policy and checked by repository static/security gates.
- PostgreSQL migrations/constraints/PIT tests, ingestion CLI and two canonical
  CLI replays: PASS. Dedicated container/network/volume teardown: PASS (runner exit 0).
- Local Linux CI image build and all new CPU-library imports with `-W error`: PASS.
  OpenMP runtime is explicit; unprivileged home creation avoids Matplotlib cache
  permission warnings. No hosted or paid service is needed.
- `git diff --check`: PASS. DOCX/main hashes unchanged; no raw third-party data,
  credentials or secrets in the changes. P2–P8 libraries/database schemas unchanged.

Final arena identities also pin resolved estimator/preprocessing configurations
and output containers. Eight evaluations/960 OOS rows were replayed twice with
current identity/manifest guards, persisted and checksum/round-trip verified.
Neither fixture candidates nor negative-control scores clear production gates.
P9 SOFTWARE acceptance is complete; commit before P10. P11 remains unauthorized.
