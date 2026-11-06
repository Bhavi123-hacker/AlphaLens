# P21 GitHub delivery and operator handoff

Branch: `p21-auth-security`, from approved P20
`eaeb01dcfa77cea4d1325de693373ae7e2020a58`. Main is unchanged. All pushes are
ordinary branch pushes; no merge, force push, history rewrite or scanner waiver.

## Implementation

`c4c5f9d36b68852c572f640fae575eade2fc7a60` implemented P21. Commit
`6438c2969e08647e3779b0f3a7d72ab779495e56` corrected POSIX database/WAL creation
permissions and initialization connection closure. Runtime packaging correction
`4ad6bdc8db36898d72ce8f00ed9f26ee16eab2af` includes two unchanged P19 import
helpers in the image; their acquisition/replay entry points are never executed.
The later handoff commit contains documentation and scan metadata only.

One local ADMIN operator uses Argon2id, an explicitly initialized owner-restricted
SQLite store, hashed opaque sessions, idle/absolute expiration, rotation and
server-side logout/revocation. Password change and explicit OS-operator recovery
revoke sessions. There is no default account, public registration or auth bypass.
Every private API operation requires backend authorization; mutations also require
Origin/JSON/CSRF and existing local P20 opt-in. Portfolio/paper records remain
read-only and unavailable evidence remains unavailable after login.

The React dashboard has actual login, protected navigation, safe intended-route
restoration, refresh, expiration, cross-tab logout, cache clearing, password change
and session inspection/revocation. P20 preferences and read/acknowledgment actions
were verified with a real session and CSRF. Existing financial/alert schemas have
no per-user ownership: this is an exclusive single-operator workspace, not private
multi-user isolation. No second account or viewer is provisioned.

## Verification and CI

The [verification report](p21-verification-report.md) records every failure,
correction, skip and receipt. Local evidence includes one ordinary Windows run
(734 passed / 16 skipped), seven later test additions and five real-archive reads:
746 distinct Windows cases passed across those runs. The final P21-focused check
passed all 60 cases. Frontend: 57 tests, TypeScript, ESLint, build and zero-finding
npm audit. Actual Chromium: 16 distinct scenarios passed across the documented
runs and targeted corrections. No synthetic application-market fallback was used.

Corrected Linux/PostgreSQL run 38154688734 passed 749 / eight skipped, 241.69s;
Ruff/format/mypy/Bandit/pip-audit/frozen lock and TruffleHog passed. It exposed the
runtime import packaging omission before Trivy, which was then corrected.
Historical secret-scan fixtures remain documented without printing their values.
Final code-image [foundation run 38155163814](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155163814)
at `4ad6bdc8db36898d72ce8f00ed9f26ee16eab2af` passed **749 / eight skips, 253.20s**,
all quality/dependency gates, TruffleHog (zero verified/unverified), Docker build,
native imports and actual authentication/P19/P20 runtime smoke. Networking was
disabled for container smoke; mount/umount were verified without SUID.
[Dashboard run 38155163752](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155163752)
passed. Foundation remains **FAILED solely at strict Trivy: 44 HIGH package/CVE
instances, eight CVEs, zero CRITICAL**, unchanged before/after. See the
[image/scan receipt](p21-container-scan-status.json) and
[eight-CVE remediation/blocker review](p21-container-security-review.md).

P21_DEVELOPMENT_PASSED. P21_SECURITY_READINESS = BLOCKED_FOR_PRODUCTION.
CONTAINER_SECURITY_GATE = FAILED. The final handoff push contains only evidence
metadata/documentation; head-specific follow-up workflow status is checked after
push and reported separately, without treating a red security gate as green.

## Preserved evidence and restrictions

The [preservation receipt](p21-artifact-preservation.json) verifies 2,485 frozen
files (8,505,278,241 bytes), all 47 original immutable alert payloads, original
DOCX, old locked dependency versions, research/domain code and main. Existing
Python/node_modules junctions and unrelated Git/Docker processes were preserved.
No historical model fit, backtest, holdout evaluation or model selection was run.

P19 live activation remains BLOCKED; newly acquired sessions: zero. Current
experimental inference/rankings/signals remain UNAVAILABLE. Production data
clearance is OPEN/NOT_CLEARED, RESEARCH_ONLY/final-vintage classification unchanged.
Email/desktop delivery remain disabled/unconfigured. No scheduler, automatic NSE
acquisition, broker, outbound notification, public listener or tunnel was enabled.

## Local operation

Use [verified Windows CMD instructions](../security/p21-windows-commands.md) for
the exact D-drive-backed account bootstrap, environment variables, backend and
dashboard startup, hidden password change/recovery, session listing/revocation,
sanitized diagnostics, focused tests and Ctrl+C shutdown. Create your own initial
account interactively; this development session created only isolated TEST_ONLY
accounts. Do not place credentials in commands, environment values or Git.

Backend: `127.0.0.1:8017`; dashboard/login: `http://127.0.0.1:5173/login`.
HTTP loopback does not provide HTTPS protection. PostgreSQL 17 compatibility is
verified in CI; local financial pages require the operator's existing exclusive
database configuration or correctly return 503. Authentication uses its separate
local store, with no financial/research migration.

P22 may be considered only under separate user authorization. P22-P25 were not
started. Production deployment remains blocked by its independent security,
HTTPS/network/ownership and market-data clearance gates.
