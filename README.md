Current D70 replay: real P4/P5 canonical and P6/P7 supervised datasets are frozen
under the separately authorized research methodology. 6,827,699 feature rows;
SMA100 availability 73.1147%, SMA200 55.4085% (including degraded context).
Chronological model training is running; OOS/backtest results remain pending.
No production clearance, P11-P14 calibration or P17 work. Earlier statuses below
are historical. See [training report](docs/ml/real-data-training-report.md).

Current D70 scope: proceed through P4-P10 under the separately versioned
RESEARCH_EOD_FINAL_VINTAGE_V1 research methodology. Missing historical evidence
is not declared solved. REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION must propagate. Normal verified PIT behavior
is unchanged. Preserve chronology, missing calendar/price slots, no future ISIN
backfill, no current-universe reconstruction or holdout tuning. Production remains
OPEN/NOT_CLEARED. STOP before P11-P14 calibration and P17. See
 docs/data/research-methodology-amendment.md. Earlier statuses follow historically.

Current scope D69: user authorizes pinned TejHQ NSE public Parquet for
NONCOMMERCIAL RESEARCH; proceed without additional permission clarification.
REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY; production OPEN/NOT_CLEARED.
Preserve existing PIT/quality rules and unknown evidence. STOP before P17 and
P11-P14 recalibration. Historical audit conclusions below describe D68.

Pinned TejHQ acquisition/P2 normalization/P3 scoped validation COMPLETE: 35 native
originals checksum-verified; 7,225,761 normalized price rows, 5,288,138 VALID,
1,937,623 DEGRADED, zero rejected/quarantined. Current software verification:
506 passed/one production-live skip, PostgreSQL 17 replay/teardown exit 0; static
and dependency gates passed. P4-P10 real historical replay remains BLOCKED by
missing availability/completion/vintage clocks, an incomplete session calendar,
and dated identity/type evidence. No real model/performance claim or calibration.
See docs/data/real-10y-ingestion-report.md and docs/data/real-data-readiness.json.
The following D68 audit-only scope/status is historical and superseded by D69.

Current user-approved insertion (D68): real historical NSE research source audit
and, only after its hard rights/provenance gate passes, P2-P10 acquisition,
training and evaluation on real data. Branch real-data-10y-training from P16
3634b920e7e1d090b3fbf18af3548afb419e7b71. Audit currently BLOCKED; no new market
archive or real model training. STOP before P17. Production OPEN/NOT_CLEARED.

[Real-data ingestion report](docs/data/real-10y-ingestion-report.md) records
completed acquisition/P2/P3 and the historical evidence blocker. Source permission
is already authorized. The older access-request draft is superseded and unsent.
Software verification does not establish real-data training or performance.

P15 AND P16 DEVELOPMENT PASSED. P15 was committed as 2db5f15 before P16
implementation. Final P16 Windows-safe regression: 495 passed, one production/live
skip (1473.38s), including 35 P16 cases. PostgreSQL 17 ingestion, immutable replay,
restart recovery and teardown exited 0. Frozen lock/sync, Ruff, mypy, Bandit,
dependency audit and diff checks passed. STOP before P17; no production clearance.

P15 DEVELOPMENT PASSED: coherent Windows-safe 460 passed/one live skip (1128.68s),
37 P15 cases, PostgreSQL 17 replay/teardown exit 0 and all static/security/dependency
gates passed. 20 TEST_ONLY valuations/19 owned-security observations replay twice
with CLI/API equality. Commit P15 before P16 implementation. No production clearance.

Current authorization: **P15 Portfolio Guardian → verify/commit → P16 forward
paper simulation → verify/commit → STOP before P17**, from approved P14 5eaeb01
on `p15-p16-portfolio-paper` (D65-D67). No broker/API/frontend/live work.
[P15 accounting contract](docs/portfolio/p15-portfolio-guardian.md) defines exact
FIFO, cutoff valuations and honest chart-ready histories. All fixture values are
TEST_ONLY — NOT A REAL MARKET VALUATION / NOT A PERFORMANCE CLAIM.

# AlphaLens

AI-powered stock research and Portfolio Guardian decision support. AlphaLens never
places real trades. Initial product scope is NSE cash equities, INR, end-of-day V1.

## Historical P13/P14 milestone

Current authorization is **P13 then P14**, under D62-D64 from P12 `28070df`, on
`p13-p14-signals-explainability`. Verify/commit P13 before implementing P14;
verify/commit P14 separately, then STOP before P15. [P13 decision states](docs/decision/p13-signal-engine.md)
keep market and explicit synthetic-position contexts separate. Insufficient model
evidence blocks normal entry; full lifecycle demonstrations are TEST_ONLY only.
All thresholds and P12 weights remain DEVELOPMENT_ASSUMPTION, not genuine NSE
calibration. No portfolio, paper trading, API/frontend or live-data work.

P13 DEVELOPMENT PASSED: 394 passed/one live skip in the full Windows-safe suite;
PostgreSQL 17/replay/teardown and all static/security/dependency gates passed.
100 immutable TEST_ONLY signals replayed exactly. See [P13 verification](docs/development/p13-verification-report.md).
P13's separate commit must precede P14 code. No production signal calibration or
market-data clearance follows from this software acceptance.

P13 was committed as `490de2e` before [P14 offline explainability](docs/decision/p14-explainability.md)
began. P14 supplies deterministic summary, evidence and lineage cards, actual
feature values, checked local linear/native boosted-tree attribution, an explicit
sklearn-tree fallback, complete risk/ranking decomposition and price-free chart
annotations. Missing fundamentals/news/benchmark/action/live evidence remains
explicit. No new external package or paid LLM. [P14 verification](docs/development/p14-verification-report.md)
records P14 DEVELOPMENT PASSED: 423 passed/one live skip (1309.52s), PostgreSQL 17/
CLI replay/teardown exit 0 and all static/security/dependency gates. 100 explanations/
annotations and 128 actual selected P9 local linear attributions replay identically.
Separate P14 commit, then STOP before P15. User approval is required for P15 scope;
production market-data use remains NOT_CLEARED.

The following P11/P12 milestone is preserved as the approved baseline.

D59-D61 now authorize P11 risk, then P12 opportunity ranking from approved P10
`f709839`, on `p11-p12-risk-ranking`. Verify and commit P11 before P12 starts;
verify and commit P12 separately, then stop before P13. No signals, portfolio,
frontend or live recommendations. P11 DEVELOPMENT PASSED: 355 passed/one live
skip in one complete Windows-safe PostgreSQL run; all static/security gates and
current incremental Linux image passed. See [P11 risk](docs/decision/p11-risk-engine.md)
and [verification](docs/development/p11-verification-report.md). P11 was committed
as `b50314b` before P12 began. [P12 ranking](docs/decision/p12-opportunity-ranking.md)
DEVELOPMENT PASSED: fixed per-horizon candidates, explicit
risk penalties, retained exclusions and past-only rank history. No market winner
or live recommendation is established. Final coherent suite: 375 passed/one live
skip, PostgreSQL 17/CLI replay/teardown exit 0 and all quality/security gates passed.
See [P12 verification](docs/development/p12-verification-report.md), including the
corrected future-only exclusion leak and full rerun. Stop before P13.

The following P9/P10 checkpoint is preserved as the approved baseline.

P9 walk-forward evaluation and P10 backtesting are explicitly authorized in strict
order under D55-D58 from approved P8 58159b7, on p9-p10-evaluation-backtesting.
[P9 architecture](docs/ml/p9-walk-forward-evaluation.md) uses cutoff-specific P7
training snapshots, expanding disjoint tests, six model families per task, naive
comparators and genuine OOS predictions. P9 passed and was committed as `4e29b49`
before P10 began. [P10 architecture](docs/backtesting/p10-backtesting.md) consumes
only those OOS records for fixed hypothetical selection, exact cash/inventory,
next-session open fills, horizon exits and explicit cost scenarios. Missing exits
retain unresolved holdings. [Real-data readiness](docs/development/real-data-readiness.md)
records the remaining rights, universe, price, action, calendar and benchmark gaps.
TEST_ONLY — NOT A PERFORMANCE CLAIM. Production clearance is OPEN and production
market-data use is NOT_CLEARED. P10 DEVELOPMENT PASSED: 26 P10 cases and all
337 distinct repository tests passed across the final regression and targeted
Windows path retry; one live gate skip. See the [verification report](docs/development/p10-verification-report.md)
for exact runs and limitations. P11 onward requires separate approval.

The following records the approved historical P2-P7 milestones.

P0, the bounded P1 research fixture, and P2 raw-ingestion development are implemented.
P3/P4 are explicitly authorized sequential development under D43-D45 on
`p3-p4-validation-universe`. [P3 validation](docs/data/p3-data-validation.md)
passed and was committed before [P4 historical-universe development](docs/data/p4-point-in-time-universe.md).
Development fixtures do not establish real NSE PIT coverage.
**P3 DEVELOPMENT PASSED; P4 DEVELOPMENT PASSED.** Final verification:
[169 passed / one production-provider skip](docs/development/p4-verification-report.md).
P5 is now authorized under D46-D48 on `p5-canonical-data-model` from approved P4.
The [canonical model](docs/data/p5-canonical-data-model.md) integrates P2/P3/P4,
immutable PostgreSQL revisions/lineage, PIT reads and deterministic JSON/Parquet
snapshots. [P5 verification](docs/development/p5-verification-report.md) records the
current gate. D49-D50 now authorize P6/P7 sequentially from approved P5 649340a
on `p6-p7-features-labels`. P6 gates and commit preceded P7.
**P5 DEVELOPMENT PASSED:** 200 tests passed, one production/live-provider gate
skipped; real PostgreSQL and all static/security checks passed. This is ready for
subsequent authorized P6/P7 development, with production clearance still OPEN.
P0's contract is recorded in [DECISIONS.md](DECISIONS.md) and
[product contract](docs/product/product-contract.md). The DOCX remains the original
authoritative specification; approved amendments are recorded separately.

**P1 DEVELOPMENT:** a local CC BY research fixture is validated; production/live
data clearance remains OPEN. Five Mendeley datasets provide 300 bounded source rows,
299 canonical records and one explicit unavailable observation. This is not a
historical market universe or evidence of unbiased/PIT-safe performance.
AlphaLens requires ZERO paid dependencies. The mandatory path runs locally on
free/open-source software with compatible free data; cloud is optional.
See the [free-data strategy](docs/data/free-data-strategy.md). Earlier paid-provider
research is retained as evidence, not approval. Missing data is never fabricated.
The API contains only liveness/readiness endpoints. P6 supplies developer-only
[versioned technical features](docs/ml/p6-feature-engineering.md) from P5 snapshots.
P8 now supplies developer-only models; all product decision/UI phases remain deferred.
**P6 DEVELOPMENT PASSED:** 234 tests passed, one production/live-provider skip;
[P6 gate](docs/development/p6-verification-report.md). P7 follows the P6 commit.
P6 is committed as `ac6973f`. [P7 raw labels](docs/ml/p7-label-generation.md)
and explicit dataset alignment live in ml/labels, separate from ml/features and
ml/training package. P7 itself produces no models or investment results.
**P7 DEVELOPMENT PASSED:** 259 tests passed, one production/live-provider skip;
[P7 gate](docs/development/p7-verification-report.md) and
[TEST_ONLY descriptive outcome report](docs/development/p7-target-distribution.TEST_ONLY.json).
Both phases are complete; subsequent explicit user authorization permits P8 only.

See [local setup](docs/development/local-setup.md),
[research fixture and replay](docs/data/research-fixture-source.md),
[acceptance status](docs/product/roadmap-and-acceptance.md), and
[validation report](docs/data/p1-validation-report.md).

## Architecture

Modular monolith plus background workers when authorized. PostgreSQL is the
production structured store; object storage/Parquet retain versioned datasets and
artifacts; Redis is temporary cache/coordination, introduced when needed.
Provider parsing belongs behind vendor adapters. Backend owns authoritative
calculations and authorization. Data correctness precedes UI.

Prefer a per-date reconstructible NSE universe with verified historical identity,
availability and departed-security evidence. Historical NIFTY 500 is OPTIONAL for
V1; today's constituent list is never historical membership. Disclose actual legally
usable free history per dataset. PIT fundamentals remain UNAVAILABLE unless proven.

## Development verification

With a verified `uv` installation and generated lockfile:

```powershell
uv sync --frozen
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
```

Do not claim these checks passed unless they actually ran. The implementation
environment's results and blockers are recorded in the development report.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. P2 development proceeds independently under
D40-D42. See [P2 architecture and commands](docs/data/p2-raw-ingestion.md) and
[verification](docs/development/p2-verification-report.md). D43-D45 supersede the
historical stop-before-P3 restriction; production clearance remains OPEN.

## P9/P10 authorized development — 2026-10-06

P9/P10 are explicitly authorized sequentially under D55-D58 from approved P8
58159b7 on p9-p10-evaluation-backtesting. P9 gates/commit precede all P10 code.
The [walk-forward contract](docs/ml/p9-walk-forward-evaluation.md) preserves
cutoff-specific P7 training snapshots, fresh expanding folds and genuine OOS output.
TEST_ONLY — NOT A PERFORMANCE CLAIM. Stop before P11; production gates remain open.

P9 DEVELOPMENT PASSED: 311 passed / one production-live skip; frozen lock,
static/security/dependency gates, real PostgreSQL 17/replay/teardown and Linux CPU
image/import checks pass. Eight TEST_ONLY task/horizon arenas replay 960 genuine
OOS predictions deterministically. [Verification](docs/development/p9-verification-report.md).
P10 begins only after the P9 commit. No production or real market-value claim.
P15 is committed as `2db5f15`; P16 forward paper simulation is undergoing its
separate complete gate. [P16 contract](docs/portfolio/p16-paper-trading.md) defines
manual default, explicit signal policy, reserved paper cash, future evidenced
next-open fills, P15 accounting and immutable event recovery. No broker or real
execution. TEST_ONLY PAPER SIMULATION — NOT REAL MARKET PERFORMANCE.
