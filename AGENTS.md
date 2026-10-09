P17 DEVELOPMENT PASSED (D72): 595 passed / one expected live-production skip,
2263.64s, including the original 33 P17 cases and actual PostgreSQL 17 reads.
One later Uvicorn log-redaction case also passed (34 P17 cases total); final API
Ruff/format/mypy/Bandit passed. The full suite predates that logging-only change.
OpenAPI and loopback startup passed. Production remains blocked; strict Trivy
retains 44 HIGH OS findings, no waiver. Research artifacts/protocol are unchanged.
See docs/development/p17-verification-report.md. STOP after P17; P18 not started.
Earlier phase status entries below are historical.

D72 user-approved P17: implement a loopback-only, read-only research FastAPI
backend from 4133ac90b27ecabf27a11f19e53c33baa0d3c616 on p17-research-api.
Reuse immutable P5/P6/P9/P10 evidence, P15 FIFO and PostgreSQL P16 event recovery.
No estimator loading/fitting, holdout reevaluation, backtest execution, P11-P14
calibration, production champion, broker connection or automatic paper execution.
All 152 fits/504 backtests/46,072,188 OOS rows and hashes remain frozen. Missing
current risk/rank/signal/explanation and full-path economic evidence stay explicit.
Development acceptance is separate from production readiness: rights OPEN/use
NOT_CLEARED, RESEARCH_ONLY/final-vintage, P21 incomplete and strict Trivy blockers
remain. STOP after P17; P18/P19 require separate authorization. Exact contract:
docs/api/p17-research-api.md. D71 and earlier scope stops below are historical.

D71 baseline review: preserve completed 8507f7f research artifacts and protocol;
no retraining, holdout reevaluation or P11-P14 calibration. All 474 unresolved
backtests audited against stored trades/equity and checksum-verified source
evidence; zero checked lifecycle/valuation inconsistencies. Source/action and
identity/accounting limitations remain unresolved. Container-only patched
Python3.12/trixie and build-only uv changes retain the original local research
lock/toolchain. Actual Trivy rescan: 44 HIGH OS findings, zero CRITICAL/Rust;
strict container gate still FAILED, no suppression. See economic-remediation
and container-security-remediation reports. STOP before P17; production
OPEN/NOT_CLEARED, REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION. Earlier entries follow historically.

D70 real research replay COMPLETE: 152 model fits, 504 hypothetical backtests
and 46,072,188 OOS prediction records verified. Frozen dataset,
statistical configurations, folds and final-holdout boundaries are unchanged.
Completed accepted-run fits were reused after interruption; none was repeated.
The four development-locked candidates were evaluated once in 2026, without
retuning. All selected candidates remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE.
Thirty backtests have available full-path raw-price diagnostics; 474 retain
unresolved economic outcomes. All twelve Logistic fits reached their fixed
iteration limit; convergence is not established. No profitability claim follows.

Required offline research software gates: 548 passed / one expected live skip,
1912.67s, Windows-safe suite and PostgreSQL 17 replay/teardown exit 0; frozen
lock/sync, Ruff, mypy, Bandit and Python dependency audit passed. These already
completed gates were reused under unchanged statistical code and lock.
The repaired TruffleHog scan passed on GitHub. The separate foundation-container
scan FAILED on reported OS/Rust findings; it is not waived and full CI success
is not claimed. See docs/development/ci-container-scan-status.json.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.
NOT PRODUCTION PIT. Production remains OPEN/NOT_CLEARED; fundamentals and
benchmark remain UNAVAILABLE. P11-P14 are unchanged. STOP before P17.
The following earlier running/pending checkpoints are historical and superseded.

Current D70 execution: frozen dataset/statistical protocol unchanged; a
separately recorded bounded four-thread forest fit keeps serial prediction. Exact
synthetic and real-data tree/prediction parity passed. Latest coherent Windows/
PostgreSQL 17 gate: 548 passed/one live skip, 1912.67s, replay/teardown exit 0;
all static/security/dependency gates passed. Real P9/P10 completion remains
pending; no final-holdout result or calibration is claimed. STOP before P17.
Original serial source/plan/artifacts are retained. Earlier statuses follow.

Current D70 replay status: real canonical and supervised datasets are frozen.
6,827,699 feature rows; SMA100 73.1147% and SMA200 55.4085% available, including
declared degraded context. Feature/label commit 59037be follows methodology
4528520. Actual P9 development training is running under the pre-results locked
plan; no empirical success or final-holdout result is claimed yet. Latest complete
Windows/PostgreSQL regression: 546 passed/one live skip (1618.59s), actual canonical/supervised
manifest replay and disposable teardown exit 0; static/security/dependency gates passed.
Earlier dated blocker/status entries below are historical.

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

P15 AND P16 DEVELOPMENT PASSED. P15 was committed as 2db5f15 before P16
implementation. Final P16 Windows-safe regression: 495 passed, one production/live
skip (1473.38s), including 35 P16 cases. PostgreSQL 17 ingestion, immutable replay,
restart recovery and teardown exited 0. Frozen lock/sync, Ruff, mypy, Bandit,
dependency audit and diff checks passed. STOP before P17; no production clearance.

P15 DEVELOPMENT PASSED: coherent Windows-safe 460 passed/one live skip (1128.68s),
37 P15 cases, PostgreSQL 17 replay/teardown exit 0 and all static/security/dependency
gates passed. 20 TEST_ONLY valuations/19 owned-security observations replay twice
with CLI/API equality. Commit P15 before P16 implementation. No production clearance.

# Current user-approved P15/P16 scope (D65-D67)

P15 Portfolio Guardian then P16 forward paper simulation from approved P14
5eaeb01 on p15-p16-portfolio-paper. Verify/commit P15 before P16 implementation;
verify/commit P16 separately, STOP before P17. This supersedes historical phase
scope deferrals only. No broker credentials/connections/real orders, API/frontend
or live pipeline. P15 owns exact FIFO portfolio ledger/P&L and PIT valuation;
P16 reuses it for simulated fills. Unknown data stays unavailable/unresolved.
TEST_ONLY remains NOT A REAL MARKET VALUATION / NOT REAL MARKET PERFORMANCE.
All thresholds/costs remain explicit development assumptions; production gates
OPEN/NOT_CLEARED and fundamentals UNAVAILABLE. Original DOCX unchanged.

# AlphaLens engineering contract

Current user-approved scope (D62-D64): P13 decision states then P14 offline
explainability from approved P12 28070df, on p13-p14-signals-explainability.
Verify and commit P13 before any P14 implementation; verify and commit P14
separately, then STOP before P15. This supersedes historical phase deferrals only.
No portfolio, paper trading, API/frontend or live-data work. Thresholds/weights
remain DEVELOPMENT_ASSUMPTION, never fixture-calibrated market rules.

P13 DEVELOPMENT PASSED: coherent Windows-safe 394 passed/one live skip (1388.13s),
19 signal cases, actual future-knowledge replay, 100 deterministic TEST_ONLY
signals and CLI equality; static/security/dependency and PostgreSQL 17 checks
passed. PowerShell stderr wrapper ambiguity was resolved by explicit native exit
capture on a focused database replay. Commit P13 before any P14 implementation.

P13 was committed as 490de2e before P14 began. P14 owns offline deterministic
summary/evidence/lineage templates, exact local attribution and price-free chart
annotation contracts. No paid LLM/service or additional SHAP package. Native
boosted-tree SHAP and linear contributions retain their units; sklearn-tree
fallback is explicitly order dependent and NOT SHAP. Missing inputs never become
neutral analysis. Verify/commit P14 separately, then STOP before P15.

P14 DEVELOPMENT PASSED: coherent Windows-safe 423 passed/one live skip (1309.52s),
29 P14 cases and actual source future-evidence replay, PostgreSQL 17/CLI replay/
teardown exit 0; all static/security/dependency and incremental Linux gates passed.
100 TEST_ONLY explanations/annotations with 128 actual selected P9 linear local
attributions replay deterministically. No production clearance/calibration follows.
Commit P14 separately and STOP; P15 requires explicit user approval.

The complete `AlphaLens_Complete_Project_Documentation.docx` and approved
interpretations/amendments in `DECISIONS.md` are authoritative. Keep the DOCX
unchanged. Decisions must distinguish the original specification from user-approved
amendments. Stop and report contradictions instead of silently resolving them.

- Never fabricate market data, predictions, accuracy, or performance results.
- AlphaLens never executes real trades. Do not create broker order infrastructure
  or store broker credentials.
- Preserve point-in-time correctness and separate event/session, publication,
  availability, ingestion, effective interval, and revision semantics.
- Prevent look-ahead bias, leakage, and survivorship bias. Never replace historical
  membership with current constituents. Use chronological/walk-forward evaluation.
- Data correctness comes before UI. Never hide stale, partial, or unavailable data.
- Every actionable signal requires risk assessment and evidence-based explanation.
- Keep provider-specific formats behind vendor-specific adapters. UNKNOWN is not
  evidence of support. Provider access and licensing are explicit gates.
- ZERO paid dependencies. Never purchase/subscribe or require paid market/index
  data, APIs, cloud, databases, auth, model APIs, monitoring or trial-only services.
  The mandatory path must run locally with free/open-source software and compatible
  free data. Public accessibility is not permission to retain, train or redistribute.
  Preserve previous paid-provider research as historical evidence, not approval.
- Never commit credentials or secrets; do not log credentials, request bodies,
  provider URLs with tokens, or database connection strings.
- Tests accompany important financial/data logic. Constructed fixtures must be
  explicitly TEST-ONLY and never presented as historical data or performance.
- Follow the dependency-driven P0–P25 roadmap. Do not advance to later phases to
  make the product look complete. Security and observability start at foundation.
- D40-D42 authorize P2; D43-D45 authorize sequential P3 validation and P4 historical
  universe development independently of P1_PRODUCTION_DATA_CLEARANCE = OPEN.
  P3 must pass and be committed before P4. D46-D48 authorize P5 canonical model
  development from approved P4 commit 59da9a8. D49-D50 authorize combined P6/P7
  from approved P5 649340a: P6 must pass and be committed before P7.
  D51-D54 authorize P8 only from approved P7 9c2bad9 on p8-baseline-ml.
  P8 stopped before P9. D55-D58 now authorize P9 then P10 only, sequential gates/commits; stop before P11.
- Initial scope is NSE cash equities, INR, end-of-day V1. Prefer a reconstructible
  per-date universe from official historical records; validate classification,
  availability, departed coverage and rights. Historical NIFTY 500 is OPTIONAL;
  never fabricate it. Disclose actual verified legally usable depth per dataset.
- FUNDAMENTAL_PIT_DATA = UNAVAILABLE unless free PIT-safe evidence is established.
  Keep future interfaces extensible; never fill unavailable inputs with neutral or
  synthetic values. Use AVAILABLE / DEGRADED / STALE / UNAVAILABLE for declared
  data scope; models must declare their actual feature families.
- Local free PostgreSQL/container deployment is sufficient in principle; cloud is
  optional. Do not mandate Docker Desktop where its free licence does not apply.
- Research clearance and production clearance are separate (D36-D39). An explicit
  open dataset licence plus repository uploader-clearance representations, with no
  specific contrary evidence, may support local educational research fixtures.
  Record residual risk; do not require independent proof of every upstream right.
  RESEARCH_FIXTURE_USE = ACCEPTED_WITH_RESIDUAL_RISK is not production approval.
  PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
- Current authorization includes a bounded Mendeley research-fixture acquisition,
  file normalization/replay, provenance, focused tests and local PostgreSQL checks.
  Keep immutable raw and normalized third-party data in ignored local storage;
  commit only code, metadata, attribution and verification evidence. No public data
  redistribution in this milestone. P2 may use accepted research or TEST_ONLY
  fixtures; fixture results cannot support production investment claims.
- Research fixtures are not a historical market universe. They do not establish
  survivorship-bias control, PIT eligibility or unbiased NSE/NIFTY-wide performance.
  Unknown session-close/publication/availability/adjustment metadata stays unknown.
- P3/P4 reports and temporal files are development evidence only. Preserve versioned
  snapshots/reports; unknown knowledge never becomes historical eligibility.
  Rejected/missing prices do not erase known existence. CURRENT_SNAPSHOT_ONLY
  cannot be used as historical membership. P5 integrates these contracts, not a
  competing identity/quality/universe system.
- No frontend, risk engine or product ranking/signals/portfolio implementation,
  real-time pipeline, or production AWS provisioning in this milestone.
  P10 mechanical hypothetical selection under D55–D58 is an evaluation exception.
- Single schema/migration owner: `db/`. Provider/data libraries must not import
  FastAPI. Workers orchestrate domain logic; frontend never owns financial logic.
- P5 `p5.canonical.v1` wraps existing P4 facts, retains P2 lineage/P3 quality and
  pins input/snapshot identities. Canonical revisions and database projections are
  immutable; corrections require new knowledge/revision evidence. Persist financial
  values exactly with Decimal/NUMERIC, never silently round, adjust or upgrade class.
  Fundamentals remain unavailable and writes disabled.
- P6 consumes P5 cutoff snapshots only. Feature values exclude future revisions,
  targets and unknown availability/basis. Preserve missing/rejected session slots;
  no full-dataset scaler fitting. Persist technical derived values as declared float64.
- P7 is authorized only after the P6 gate/commit. Labels stay separate from features;
  completed t information precedes hypothetical t+1 open entry. Training requires
  matured targets and explicit feature/target/metadata boundaries. P8 consumes only
  P7 aligned datasets; no independent feature/target joins or eligibility upgrades.
- P6 passed/committed as ac6973f before P7. P7 p7.labels.v1 uses t+1 open -> t+h
  close raw outcomes; no costs, execution or terminal-value assumptions. Decisions
  require evidence they precede entry (v1 conservative bound: prior local date).
  Exact rational/Decimal targets preserve maturity, availability, classification
  and revisions. Known unadjusted economic actions exclude training eligibility.
- Report verification failures, skips, and unavailable tools honestly. A blocked
  external-data gate is not passed by tests using TEST-ONLY fixtures.
- P8 uses a single deterministic chronological development holdout. Training label
  availability must be <= training cutoff and strictly before validation local date
  start. No random temporal split, validation-fitted preprocessing or tuning search.
  Preserve P7 exclusions; no imputing ineligible rows into training. Targets convert
  explicitly to float64 only at estimator boundary. No cross-section recomputation.
- P8 TEST_ONLY metrics are NOT A PERFORMANCE CLAIM; research metrics are separately
  NOT PRODUCTION-VALIDATED. Naive comparisons never authorize production promotion.
  Local checksum-pinned skops artifacts are trusted local inputs only; never blindly
  trust serialized types or expose arbitrary model loading to untrusted input.
- P8 DEVELOPMENT PASSED: 293 tests / one production-live gate skip, static/security,
  real PostgreSQL 17/replay/teardown and local CI image build passed. P8 software
  acceptance does not clear production data/models. Subsequent P9/P10 authorization is D55-D58.

- P9/P10 user authorization (D55-D58): p9-p10-evaluation-backtesting from P8
  58159b7. Verify/commit P9 before any P10 implementation, then verify/commit P10
  and stop before P11. P9 consumes cutoff-specific P7 aligned training snapshots
  separately from later scoring outcomes; no independent feature/target joins.
  Expanding disjoint chronological test folds, fresh train-only preprocessing,
  availability/maturity purge and explicit embargo; no outer-test tuning.
- P9 OOS stream contains FOLD_TEST only. P10 may consume only that trusted local,
  checksum/schema/lineage-verified stream. No in-sample or tuning predictions.
  Mechanical hypothetical backtest selection is authorized; no product stock
  ranking, signals, risk engine, recommendation, portfolio product or broker orders.
- TEST_ONLY results remain NOT A PERFORMANCE CLAIM; RESEARCH_FIXTURE results
  remain NOT PRODUCTION VALIDATED. No production champion/promotion. Data clearance
  stays OPEN and production market-data use stays NOT_CLEARED. Zero paid services.

- P9 DEVELOPMENT PASSED: 311 passed/one live-production gate skip; frozen lock,
  Ruff/mypy/Bandit/dependency audit, PostgreSQL 17/replay/teardown and Linux CPU
  import/image checks passed. Eight TEST_ONLY evaluations/960 genuine OOS records
  replay deterministically; no production evidence. P9 was committed as 4e29b49
  before P10 started.
- P10 consumes verified P9 FOLD_TEST only; fixed mechanical policies, exact rational
  hypothetical cash/inventory, next known session open and horizon close exits.
  Calendar schedules need decision-time evidence; explicit open conventions never
  upgrade unknown P5 clocks. Missing fills incur no costs; unknown terminal exits
  retain unresolved holdings. Raw economic actions require conservative exclusions,
  never fabricated adjustment/recovery. TEST_ONLY benchmarks are never named NIFTY.
  Fixed cost/slippage scenarios are assumptions, not verified broker/tax schedules.
  P11 risk/P12 ranking/P13 signals/P14 explanations and portfolio/UI stay deferred.

- P10 DEVELOPMENT PASSED: 26 P10 cases; 337 distinct repository tests passed and
  one production-live skip across the final regression plus a two-case Windows
  short-path retry. Static/security/dependency, PostgreSQL 17/CLI replay/teardown
  and 192-run deterministic artifact/CLI gates passed. Exact failure history and
  image capacity limitation are in p10-verification-report.md. Stop before P11.

- D59-D61 subsequently authorize P11 risk then P12 opportunity ranking from P10
  f709839 on p11-p12-risk-ranking. P11 must pass and be committed before P12
  implementation. Verify and commit P12 separately, then stop before P13.
  These user-approved phases supersede earlier phase-specific deferrals only.
  No signals, explainability product, portfolio, frontend or live recommendations.
- Risk/ranking inputs must preserve P5/P6/P4/P3 knowledge boundaries. P7 targets
  are not predictive inputs. Model diagnostics and economic comparisons require
  explicit historical availability; full future evaluation reports cannot score
  an earlier decision. Missing evidence never implies LOW risk. TEST_ONLY remains
  NOT A PERFORMANCE CLAIM; production clearance OPEN/use NOT_CLEARED.
- P11 DEVELOPMENT PASSED: 355 passed/one live skip in a coherent short-root
  Windows run, PostgreSQL 17/CLI replay/teardown and all static/security/dependency
  gates passed. 100 TEST_ONLY risk snapshots replayed twice; current incremental
  Linux image imports passed. Commit P11 before P12; stop before P13.
- P11 was committed as b50314b2dc3eba55581f6e4d5792f0369019d635 before P12 began.
  P12 uses fixed configured families per task/horizon, observed normalized inputs
  and explicit P11 penalties; no optimistic per-security model selection. Ranking
  retains complete exclusions and past-only history. Insufficient model-selection
  evidence blocks non-TEST_ONLY ranking. P9/P10 report availability is mandatory.
- P12 DEVELOPMENT PASSED: final coherent 375 passed/one live skip (1411.25s),
  PostgreSQL 17/CLI replay/teardown exit 0 and all static/security/dependency gates.
  20 TEST_ONLY ranking snapshots replayed twice; artifact/CLI and corrected Linux
  image checks passed. Future-only P4 catalog placeholders are not historical
  candidates; require contemporaneous facts/known-membership reasons or available
  prices. Retain known ineligible candidates. Commit P12 separately, stop before
  P13. Production clearance remains OPEN/use NOT_CLEARED; no actual market winner.
P15 was verified and committed as 2db5f15 before P16 implementation. P16 now owns
offline forward paper intents/events/fills and uses P15 FIFO/valuation exclusively.
Manual default, explicit fixed-horizon policy, reservations, next evidenced open,
idempotent sessions and immutable PostgreSQL event recovery. Verify/commit P16
separately, then STOP before P17; no broker/API/frontend/live work is authorized.
