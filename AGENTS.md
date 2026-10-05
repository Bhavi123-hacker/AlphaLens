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
  P3 must pass and be committed before P4. Stop before P5; approval required.
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
- No frontend, feature/model/backtest/risk/ranking/signal/portfolio implementation,
  real-time pipeline, or production AWS provisioning in this milestone.
- Single schema/migration owner: `db/`. Provider/data libraries must not import
  FastAPI. Workers orchestrate domain logic; frontend never owns financial logic.
- Report verification failures, skips, and unavailable tools honestly. A blocked
  external-data gate is not passed by tests using TEST-ONLY fixtures.
