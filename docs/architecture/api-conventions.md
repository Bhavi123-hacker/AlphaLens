# P17 current API conventions (D72)

P17 implements a local research-only GET API under /api/v1, with stable security
IDs, bounded pagination/date filters and safe domain errors. The authoritative
[endpoint/availability contract](../api/p17-research-api.md) distinguishes persisted
research evidence, unavailable current signals and partial portfolio valuations.
OpenAPI JSON is enabled at /openapi.json; /docs redirects to the offline contract.
Routers own no financial formulas or training operations. PostgreSQL connections
are read-only, CORS is loopback-only without credentials, and actual remote peers
are denied. The supported launcher disables forwarded headers and binds 127.0.0.1.
Authentication/object authorization and public deployment remain blocked by P21.
Envelope classification/source/as-of/version/quality/reasons preserve research
restrictions and exact financial strings. Empty records differ from unavailable
evidence. Production is never implied by 200 health/readiness responses.

## Historical foundation-only contract before D72

# API conventions

Version prefix /api/v1. Stable opaque security_id, plural collections, documented
pagination/filter/sort limits, object-level authorization and safe error codes.
Symbols are lookup/display attributes with dated mappings.

Planned paths: /stocks/{security_id}, /portfolios, /model-performance,
/portfolios/{portfolio_id}/performance. These product endpoints do not exist yet.

Implemented local endpoints:
- GET /api/v1/health/live: process alive; explicitly foundation_only.
- GET /api/v1/health/ready: 503 if database missing/unreachable, 200 only when
  real SELECT 1 succeeds. This says nothing about market data/provider/ML readiness.

No fabricated sample responses. Stable errors contain error_code, safe message,
request_id. Request IDs are generated internally; caller IDs/URLs/bodies are not
logged. API is local/test only, OpenAPI/docs disabled, trusted local hosts, no
CORS allowlist beyond default denial, no-store and basic security headers.

Health is intentionally unauthenticated for local operations. No product data,
authentication/session system or full P17 authorization exists. OIDC, tenant BOLA
checks, rate limiting, body limits and production TLS are later release gates.
