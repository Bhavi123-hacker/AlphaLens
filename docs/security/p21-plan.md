# D76 P21 implementation contract

Authorized 2026-10-11 from P20 eaeb01dcfa77cea4d1325de693373ae7e2020a58,
branch p21-auth-security. This supersedes earlier phase stops only; stop after
P21 and bounded container remediation. No research fitting/evaluation/backtesting,
market acquisition, public deployment or outbound notifications.

Use a single local operator, ADMIN role only. Existing P15/P16/P20 workspace
records have no verified per-user ownership. A second user is not provisioned;
authenticated workspace access is not a multi-owner isolation claim. Existing
financial data and all 47 alert records remain unchanged.

An explicit CLI initializes a separate D-drive SQLite authentication store, with
Argon2id password hashes, transactional schema versioning, restricted filesystem
permissions, durable login-attempt limits and safe audit events. No automatic
migration/bootstrap or plaintext/default credential at server startup. Recovery
requires local operator filesystem access and a hidden password prompt.

Opaque random sessions are stored as SHA256 hashes, rotated at login, and expire
after 30 idle minutes or eight absolute hours. Cookies are host-only, HttpOnly,
SameSite=Strict and scoped to /api/v1. The actual HTTP loopback deployment uses
Secure=false and makes no HTTPS claim. A random synchronizer CSRF secret is kept
in the restricted auth store and frontend memory only, never logs/storage. Mutations
require allowed Origin, JSON, a bounded body, exact fields and constant-time CSRF
verification. Login requires explicit local browser request context and Origin.

FastAPI dependencies protect every route except explicit process liveness and
login. Authentication is mandatory; absent storage fails closed. Research data
unavailability remains 503 after valid authentication. Financial writes stay absent.
P20 projection controls require the authenticated operator, CSRF and its existing
explicit mutation flag. Untrusted forwarded headers remain unsupported/rejected.

React provides genuine login, session restoration, safe redirect, password change,
logout and session revocation. Central cookie transport, memory-only CSRF and cache
cancellation/clearing prevent stale private data after logout/401. No mock runtime
session, public signup or email reset. Tests use isolated TEST_ONLY accounts.

Container work starts with the actual P20 receipt: 44 HIGH package instances / eight
unique CVEs / zero CRITICAL. Use only supported compatible bases/packages; native
ML/API/worker smoke checks and an actual strict scan are mandatory for any candidate.
No unstable core-library mixing, ignore list, ignore-unfixed or severity waiver.
If the shared Docker daemon does not answer bounded probes, leave it untouched and
use available CI evidence; do not globally restart/prune it.

References: [Argon2 API](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
