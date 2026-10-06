# AlphaLens engineering contract

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
