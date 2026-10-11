# Integrated local API contract

The original [P17 contract/snapshot](p17-research-api.md) is retained unchanged as
historical evidence. [Current OpenAPI](p25-openapi.json) adds the existing P19,
P20 and P21 routes and new P22 read-only monitoring; financial/research response
semantics remain unchanged. The React generated client now references this current
contract; runtime Zod validators and closed mutation-route allowlists remain active.

| API family | Authorization and behavior |
| --- | --- |
| `/health/live`, `/health` | Minimal public process health only; no private diagnostics |
| `/auth/login` | Public entry, explicit local Origin/JSON/P21 context, Argon2id and rate limiting |
| `/auth/session`, `/auth/sessions` | Genuine active local ADMIN session |
| `/auth/logout`, `/auth/password`, `/auth/sessions/revoke` | Session, Origin, content type and CSRF; explicit allowed fields/body bound |
| `/stocks`, `/research`, `/system`, `/opportunities`, `/signals`, `/rankings`, `/explanations` | Authenticated; historical persisted evidence only; unsupported current decisions remain 503 |
| `/portfolios`, `/paper` | Authenticated singleton operator; optional PostgreSQL required; no multi-owner claim or trading writes |
| `/daily/*` | Authenticated immutable P19 reads; acquisition/model/signals stay gated |
| `/alerts/*` GET | Authenticated original event evidence and mutable lifecycle/delivery projections |
| `/alerts/preferences`, `/alerts/{id}/state` POST | Explicit alert-mutation setting plus authenticated Origin/CSRF/P20 context; narrow local changes only |
| `/operations/status`, `/operations/metrics`, `/operations/history` | Authenticated actual probes/process metrics/verified persisted history; no worker or delivery triggered by GET |
| `/openapi.json`, `/api/v1/openapi.json`, `/docs` | Authenticated schema access |

All HTTP services retain loopback peer, trusted Host and forwarded-header rejection.
Only explicitly configured loopback origins are accepted; no credentialed wildcard
CORS. 401 remains unauthenticated, 403 policy/origin rejection, 404 missing/concealed
resource and 503 genuinely missing evidence/storage. Response-size and pagination
bounds, decimal precision and TEST_ONLY classification gates remain unchanged.

Compiled frontend pages/assets are a separate mounted static shell, not API routes
and not an auth bypass. Unknown API paths do not fall back to HTML. Public shell
contains no private research/account/alert data; API access still requires a session.

P22 status separately identifies service availability, PostgreSQL configuration,
source/inference policy blockers, actual run state and storage thresholds. Metrics
contain fixed request families and bounded samples, no usernames/security IDs/raw
request URLs. Monitoring history verifies persisted probe hashes and rejects
TEST_ONLY probes in application mode. CLI publication alone processes the durable
outbox into P20; page reads never send notifications.
