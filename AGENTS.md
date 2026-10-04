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
- Never purchase/subscribe to paid services without explicit authorization.
- Never commit credentials or secrets; do not log credentials, request bodies,
  provider URLs with tokens, or database connection strings.
- Tests accompany important financial/data logic. Constructed fixtures must be
  explicitly TEST-ONLY and never presented as historical data or performance.
- Follow the dependency-driven P0–P25 roadmap. Do not advance to later phases to
  make the product look complete. Security and observability start at foundation.
- Current authorization is ONLY P0, P1 foundation, and minimal development setup.
  Stop before P2; explicit user approval is required to start it.
- Initial scope is NSE cash equities, INR, end-of-day V1. Historical NIFTY 500
  membership is conditional on evidence, departed-security coverage, and licensing.
- No frontend, feature/model/backtest/risk/ranking/signal/portfolio implementation,
  real-time pipeline, or production AWS provisioning in this milestone.
- Single schema/migration owner: `db/`. Provider/data libraries must not import
  FastAPI. Workers orchestrate domain logic; frontend never owns financial logic.
- Report verification failures, skips, and unavailable tools honestly. A blocked
  external-data gate is not passed by tests using TEST-ONLY fixtures.
