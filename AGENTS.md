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
- Current authorization is ONLY P0, P1 foundation, and minimal development setup.
  Stop before P2; explicit user approval is required to start it.
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
- The proposed P1_V1_FREE_v1 gate cannot pass without a real permitted sample,
  reproducible normalization, checksums/provenance and universe/coverage evidence.
  Current task is decision work only: no adapter, paid service selection or P2.
- No frontend, feature/model/backtest/risk/ranking/signal/portfolio implementation,
  real-time pipeline, or production AWS provisioning in this milestone.
- Single schema/migration owner: `db/`. Provider/data libraries must not import
  FastAPI. Workers orchestrate domain logic; frontend never owns financial logic.
- Report verification failures, skips, and unavailable tools honestly. A blocked
  external-data gate is not passed by tests using TEST-ONLY fixtures.
