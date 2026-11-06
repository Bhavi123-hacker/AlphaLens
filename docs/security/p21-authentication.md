# P21 local operator security

User-approved D76, 2026-10-11, from P20
`eaeb01dcfa77cea4d1325de693373ae7e2020a58`, branch `p21-auth-security`.
The original DOCX is unchanged. This milestone replaces the historical P21
managed-identity proposal with a free local operator account and opaque sessions.
It does not implement public deployment, signup, email recovery or P22–P25.

## Identity and ownership

There is exactly one account, enforced by the database singleton constraint.
Its only role is ADMIN. No public/default administrator exists. A local CLI
prompts without echo to initialize it; API startup never initializes or migrates
storage. Repeating bootstrap refuses to replace an existing account.

P15 portfolios, P16 paper accounts and P20 notifications currently have workspace
identifiers, not verified user ownership. Authentication permits the operator to
read that exclusive workspace. Arbitrary financial identifiers do not grant an
unauthenticated caller access. A second user, viewer role, owner reassignment and
multi-owner isolation are deliberately unsupported. Use an exclusive PostgreSQL
workspace, never a shared multi-owner financial database with this release.
Financial APIs remain read-only. No broker or execution path is introduced.

Existing 47 P20 alerts remain in their original store with unchanged identities,
payloads and lineage. The authorized operator controls their lifecycle/preferences
projections. No alert evidence is reassigned, deleted or regenerated.

## Passwords and recovery

Established `argon2-cffi` Argon2id hashing uses independent library-generated salts,
64 MiB memory, three iterations and parallelism four. Verification uses the
library; hashes needing an upgrade are replaced only after valid credentials.
Unknown/disabled accounts return the same invalid-credentials response and perform
password verification using a real or dummy hash. No custom password cryptography.

Passwords are 15–128 characters, at most 1,024 UTF-8 bytes, without control
characters, username inclusion, extremely repetitive values or the small offline
common-password denylist. There is no comprehensive breached-password service or
claim of one. No password is accepted through CLI arguments or environment variables.
Hidden prompting rejects getpass's echoed fallback. Password confirmation is required.

Five failed login/reauthentication attempts in five minutes impose a five-minute
workspace-wide limit. SQLite transactions serialize this policy across processes
and persist it across restart; changing usernames or spoofing forwarded IPs cannot
bypass it. Successful login clears failed attempts, but cannot bypass an active
limit. This global limit can cause local denial of service; local recovery remains
available to the trusted OS operator. No background rate-limit service is required.

Password change requires the current password, validates the replacement and
revokes all sessions. Explicit CLI recovery requires local filesystem access,
`RESET` confirmation and a hidden replacement prompt; it unlocks the account,
clears attempt state and revokes all sessions. It does not email credentials.
OS access sufficient to modify the store is a trusted recovery boundary.

## Sessions and browser security

Each successful login creates a fresh 256-bit opaque random bearer token. Only
its SHA256 digest is stored. The separate public session UUID is used for listing
and revocation; it is not a credential. A supplied valid browser session is retired
after successful login. Maximum ten active sessions; oldest sessions are revoked
when necessary. Idle expiration is 30 minutes, absolute expiration eight hours.
Server-side account status, role, revocation and expiry are checked on every
protected request. Last activity cannot regress during concurrent reads.

The cookie `alphalens_session` is host-only, HttpOnly, SameSite=Strict and scoped
to `/api/v1`. `Secure=false` is intentional for the actual HTTP loopback runtime;
this release makes no HTTPS, encrypted-cookie-at-rest or public-network claim.
No bearer token appears in URLs, localStorage or frontend responses. API responses
and errors are no-store. The CLI can list public session metadata and revoke one
or all sessions; logout revokes the server record before deleting the cookie.

A separate random synchronizer CSRF secret is stored under the auth store's
restricted filesystem permissions and returned only through authenticated session
or successful login responses. React keeps it in module memory. Every protected
mutation requires a single exact allowed Origin, JSON type and matching
`X-CSRF-Token`. Login requires Origin, JSON and `X-AlphaLens-Local: p21`, with no
existing session required. Auth bodies are limited to 8 KiB and exact string fields; duplicate JSON fields,
invalid Unicode and ambiguous content types are rejected.
P20 also retains its local context header and explicit mutation-enable flag.

Private GET requests require authentication too. Foreign browser Origins,
non-loopback peers, foreign Hosts and forwarded/proxy headers are rejected.
Credentialed cross-origin access is not enabled; use the existing same-origin
loopback Vite proxy. The launcher still binds only 127.0.0.1 with proxy headers
and access logging disabled. No fixed development credential or query bypass exists.

React verifies the actual server session before rendering private routes. Login
restores a validated local destination. Logout/password change/401/expiration
cancel queries, clear private caches and discard memory-only CSRF. Request epochs
reject late responses from a previous session. A same-origin BroadcastChannel
announces only the public session UUID so logout clears another open tab.
Idle/absolute UI timers hide private content; focus checks handle paused tabs.
The server remains authoritative, and no automatic heartbeat extends sessions.
401 does not become a retry loop; 403 stays forbidden and 503 research evidence
remains unavailable. No fixture or mock login exists in application mode.

## Storage and migration contract

`ALPHALENS_AUTH_ROOT` selects a separate local directory, normally
`D:\al-research\p21-runtime\auth`. Do not point it at research/archive directories.
`auth.sqlite3`, WAL and shared-memory files contain sensitive material and must
never be committed or served through Vite. The separate `db/auth/schema.sql`
is version 1; only explicit CLI initialization applies it transactionally.
Unknown versions or partially populated unknown schemas fail closed.

Windows uses native pywin32 DACL APIs: protected directory, current operator SID
and SYSTEM only, inheritable full access. Every database/sidecar is checked for
the same allow list. POSIX requires owner-only directory 0700 and database 0600,
matching the effective UID. A broad/unexpected permission fails authentication.
On POSIX, a new database is created atomically with mode 0600 before SQLite opens
it, so WAL/SHM inherit private permissions. Existing files are verified rather
than silently repaired. Initialization explicitly closes its SQLite connection;
the transaction context manager alone does not close it. The open-sidecar and
reinitialization regression is part of P21 verification.
The root must be on a local filesystem supporting these permissions and SQLite
locking; network shares and permissive FAT volumes are unsupported.

Writes use `BEGIN IMMEDIATE`, foreign keys, five-second busy timeout, WAL and
synchronous FULL. Account/session/attempt changes and their fixed audit events
commit atomically. Failed credential events commit before the safe exception is
returned. Crash recovery uses SQLite WAL, not research publication machinery.
No destructive migration runs at API startup. Expired/revoked session cleanup is
explicit CLI work or bounded maintenance during login, and does not touch research.

Auth audit diagnostics retain the newest 100,000 events; the CLI displays only
the latest 50 sanitized event types/times and public account fields. Stored events
include bootstrap, login success/failure/limit, denied access, logout, password
verification failure/change/recovery, session rotation/revocation and status change.
When storage is absent, rejected requests still produce sanitized request/status
logs. No password, raw token, CSRF, financial payload, SMTP setting or DSN is logged.
Back up auth diagnostics separately if longer audit retention is needed.

For consistent backup, stop the operator's API and auth CLI activity, then copy
the complete auth directory (including any WAL/SHM) to a protected operator-owned
location. Never copy a live DB file alone, distribute it or restore it over an
active store. Restore to a separately named protected directory, validate schema/
permissions with `diagnostics`, revoke all sessions and select that root explicitly.
Backups can contain password hashes and usable session/CSRF material and require
the same access restrictions. Offline reset recovers account access without
altering immutable research or portfolio evidence.

## API access matrix

Only GET `/api/v1/health/live`, GET `/api/v1/health` (the existing process-only
alias) and POST `/api/v1/auth/login` are public. Liveness does not expose database,
daily status, portfolio or configuration details. Authenticated details remain
protected, including readiness and offline OpenAPI schema.

| Route family | Authentication / authorization | Mutation |
|---|---|---|
| stocks, history, features, research models/predictions/evaluations, backtests | Active ADMIN operator | GET only |
| risk, opportunities, rankings, signals, explanations | Active operator; unchanged evidence gates | GET only; unavailable remains 503 |
| portfolios, holdings, valuations, paper accounts/orders/events/trades | Active operator; exclusive local workspace | GET only |
| daily status/runs/checkpoints/latest/predictions/signals | Active operator; P19 gates unchanged | GET only |
| alerts/history/unread/details/preferences | Active operator; one workspace | GET; projection POST only when opted in + CSRF |
| auth/session and auth/sessions | Active operator | GET |
| auth/logout, auth/password, auth/sessions/revoke | Active operator; own session metadata | POST + Origin + CSRF |
| health/ready, readiness/data-health, `/api/v1/openapi.json`, `/openapi.json`, `/docs` | Active operator | GET |

See [machine-readable route matrix](p21-api-access.json). Root `/openapi.json`
and `/docs` require an explicit authenticated client cookie header; the normal
browser cookie is scoped to `/api/v1`, so use `/api/v1/openapi.json` after login.
The frozen P17 generated domain client is retained; auth requests have their own
typed Zod contracts. Server dependencies, not React guards, enforce authorization.

401 means absent/invalid/expired credentials. 403 means local-origin/context/CSRF
rejection or forbidden access. Unknown owned session IDs return 404. Missing
storage or legitimate research evidence returns 503. Unsupported roles cannot
be stored; additional owners cannot be provisioned. Authentication grants no
data rights, model promotion, signals or production readiness.

## Threat model and limits

| Threat | Implemented control | Residual boundary |
|---|---|---|
| Password guessing/account takeover | Argon2id, password policy, durable rate limits, secure bootstrap | OS compromise, breached-password checking and recovery access |
| API bypass / IDOR / financial privacy | Mandatory dependency and singleton ADMIN; financial GET only | Multi-owner records must not share this workspace |
| Cookie theft/fixation | HttpOnly, random rotated hashed sessions, expiry/revocation | Local HTTP has no TLS; privileged OS/browser compromise |
| CSRF / malicious loopback website | Exact Origin, synchronizer token, Strict cookie, JSON/context headers | Same-origin XSS can act as the operator |
| XSS | React text rendering, existing bounded trusted evidence, no token localStorage | Dev server is not a production CSP/TLS deployment |
| Privilege escalation | Single enforced role, owned session revocation, no public provisioning | OS administrator controls local store |
| Untrusted proxy/DNS rebinding | Loopback peer/bind, trusted hosts, exact origins, reject forwarded headers | Remote tunnels/reverse proxies remain prohibited |
| Unsafe DB / leakage | Parameterized SQLite, isolated store, transactions, schema checks, native ACL | Operator backups and exclusive PostgreSQL configuration |
| Secret logs / frontend cache | Fixed safe audit fields, existing redaction, no-store, cache/epoch clearing | TEST_ONLY browser traces stay outside Git with restricted identity storage |

This is local development security, not an independent penetration test or
production certificate. Remaining container CVEs, production HTTPS/proxy design,
multi-user ownership and market-data clearance are separate blockers. P19 live
activation remains BLOCKED; current inference/ranking/signals remain UNAVAILABLE.
External notification channels and acquisition/scheduling remain disabled.

References: [Argon2 maintained API](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
and [CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
