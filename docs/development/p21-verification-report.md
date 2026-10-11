# P21 verification and resume checkpoint

Date: 2026-10-11. Branch `p21-auth-security`, baseline
`eaeb01dcfa77cea4d1325de693373ae7e2020a58`. D76 authorizes P21 and bounded
security remediation only. Original P17/P18/P19/P20 development evidence is reused
where unchanged; no historical fit, holdout evaluation or backtest was restarted.

## Completed implementation

One actual local ADMIN account, explicit hidden CLI bootstrap/recovery, Argon2id,
protected transactional SQLite storage, durable guessing limits and safe audit
events. Hashed random opaque sessions rotate on login, expire after 30 idle
minutes/eight hours, and support server-side logout/revocation/password change.
The API never initializes the account at startup and has no bypass/default password.

Every private declared API operation requires the active operator dependency.
Only process liveness aliases and the guarded login route are public. Research,
portfolios, paper accounts, alerts, preferences, daily status and account/session
details are protected. Foreign Origins/Hosts/peers/forwarded headers are rejected.
Browser mutations require JSON, Origin and synchronizer CSRF, with existing P20
context/opt-in restrictions. Financial routes remain GET-only and their evidence
semantics/precision are unchanged. Browser-scoped protected OpenAPI is available.

React has genuine login, intended-route restoration, safe session refresh,
password change, logout and active-session inspection/revocation. Central
same-origin cookie transport keeps CSRF only in memory; 401 clears private cache
and UI, request epochs reject late private results, and cross-tab logout propagates
only public session identity. Idle/absolute UI guards do not bypass server checks.
Settings integrate authenticated notification preferences/read/acknowledgment.
Dark/light styling, keyboard, mobile and reduced-motion behavior are preserved.

This is a single-operator workspace. Existing P15/P16/P20 have no per-user ownership,
so second-user provisioning and multi-owner isolation are not claimed. HTTP loopback
does not provide TLS. Public production security remains a separate blocked gate.

## Actual local verification

| Check | Actual result |
|---|---|
| Initial P21 unit/API checks | 20 unit + 27 API passed before later hardening |
| Updated focused P21 checks | 51 passed, 31.71 s, including native Windows ACL enforcement, concurrent sessions, password reauthentication limits and Unicode/salt behavior |
| Full Windows ordinary software suite, once | **734 passed / 16 skipped, 1073.20 s, exit 0**; 750 collected; no historical research execution |
| Later CLI additions | 2 passed, 0.92 s: current-password change, explicit recovery/cancel and refusal of echoed prompting |
| Later route additions | 2 passed, 4.17 s: every declared private operation denied anonymously, protected browser schema and ambiguous cookie denial |
| Final strict body validation | 12 targeted cases passed, 4.45 s; includes two new duplicate-field/invalid-Unicode cases and affected positive/context/CSRF regressions |
| POSIX WAL initialization correction | 60 P21 unit/API cases passed on Windows, 32.44 s; new open-WAL/reinitialization permission regression, no permission-policy relaxation |
| Previously skipped actual archive reads | 5 passed, 18.37 s; stored OHLCV/SMA200/OOS/once-evaluated holdout/backtest/classification reads, no estimator execution |
| Frontend unit/component | **57 passed**; existing 50 plus seven authentication/cache/transport cases |
| Final changed auth UI check | Seven focused cases passed after cross-tab/session guards, 6.42 s |
| Actual Chromium | **16 distinct scenarios passed across original run and documented targeted additions/retries**; not a zero-exit single full-browser-run claim |
| TypeScript / ESLint / production build | Passed; preexisting large chart-chunk warning retained, no warning suppression |
| npm audit / Python pip-audit | Passed; zero known vulnerabilities in actual audited dependency environments |
| Ruff / formatting | Passed; 346 Python files formatted at final code checkpoint |
| Strict mypy | Passed, 209 configured sources; new helper/preservation/runtime scripts separately passed with Linux platform typing |
| Bandit | Passed, zero findings, no suppression; all existing API/domain/worker scopes retained |
| Frozen lock / offline frozen sync | Passed; all old locked versions unchanged, five auth-only additions |
| Git whitespace | Passed |
| Research/alert preservation | Passed: 2,485 files, 8,505,278,241 bytes, SHA256 gate 61.296 s; 47 original immutable alert events preserved |

Full Windows skips were ten real PostgreSQL cases (no configured local listener),
five real-archive cases (optional paths initially absent) and one production/live
source gate. The five archive skips were then exercised with their actual saved
paths and passed; no synthetic substitute was used. Seven added CLI/route/body/WAL cases
were verified separately after collection. Combined Windows evidence is **746
distinct passed repository cases**, with ten local PostgreSQL cases and the
production/live gate still skipped locally. PostgreSQL is verified separately
by the actual GitHub foundation service, not replaced with SQLite.

The final P21 files contain 26 unit cases and 33 API cases. The full Windows run
included 24/29, and the six additions passed separately. Dedicated P21 tests use
raw ASGI transport to verify authenticated and anonymous flows. Existing domain
tests now receive a genuinely persisted random TEST_ONLY session through an
explicit test helper; no dependency override or runtime authentication bypass.
P17 financial OpenAPI assertions retain GET-only financial operations while
allowing the authorized new auth routes. Historical negative URI fixtures remain.

Browser checks used the actual HTTP API and preserved research archive, an
isolated TEST_ONLY auth store under D:, and the existing separate operational
browser alert store. They did not intercept requests or generate fake stock rows.
The eight earlier chart/research/P19/P20 scenarios passed with valid sessions,
including notification preference/read/acknowledgment writes with CSRF. New cases
cover anonymous denial, cookie flags, refresh, invalid/keyboard login, logout,
revocation, mobile/axe accessibility, account controls, real password change,
actual server expiration and clearing another open tab's private cache.

Failure history is retained outside Git: the first browser run passed 11/13 and
found a login destination redirect race; removing the racing redirect fixed the
two affected cases, which passed with the new password-change case (three passed).
The first expiry test clicked a settings control after the legitimate 401 had
already removed it; removing that stale action let the actual expiry scenario
pass. Cross-tab logout passed separately. These failures were corrected, not waived.
An initial frontend command used unrelated system Node and failed before tests;
the existing supported Node 22.23.3 environment was then used. No dependency
junction or package was regenerated. Intermediate lint/type issues were fixed.

Machine receipts/logs: `D:\al-research\p21-runtime\full-windows.xml`,
`full-windows.log`, `p21-focused.xml`, `p21-cli-additions.xml`,
`p21-route-additions.xml`, `p21-body-hardening.xml`, `actual-research-reads.xml`, `browser-report*.json`,
`pip-audit.json`, `npm-audit.json` and `bandit.json`. Browser traces and isolated
credentials/state remain outside Git; no real operator password was created.
The original unrelated Git/Docker processes were preserved.

## Preservation and restrictions

[Actual preservation receipt](p21-artifact-preservation.json) confirms all 2,485
frozen research files and protected dataset/model/protocol reports, original DOCX,
main commit and ML/decision/portfolio/backtesting/P19/P20/db-domain source roots.
All prior dependency versions remain; Argon2, its bindings/CFFI/parser and Windows
native DACL support are the only lock additions. Original archive/toolchain checks
are historical evidence; the new lock hash is not misrepresented as unchanged.
The `.venv` and node_modules D-drive junction targets were retained.

P19_LIVE_DATA_ACTIVATION = BLOCKED. No new session was acquired. Experimental
inference/current ranking/signals remain UNAVAILABLE. Source rights/production
market-data clearance stay OPEN/NOT_CLEARED and research classification remains
RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION. Authentication does not clear
these gates. No scheduler, broker, public listener/tunnel or outbound channel was
enabled, and no frozen model selection/calibration was changed.

## Security / GitHub delivery status

The first P21 foundation run [38147200821](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38147200821)
failed ordinary tests: 646 passed, 47 failed, 55 setup errors, eight skipped.
The common cause was POSIX initialization opening SQLite before restricting the
database file, so WAL/SHM inherited its original broad creation mode. Also,
SQLite's transaction context manager does not close the connection. The strict
permission check correctly refused these files. The correction creates a new
POSIX database atomically with mode 0600 before SQLite opens it, verifies existing
files without broadening permissions, and explicitly closes the initialization
connection. No permission check or scanner is relaxed. A regression checks
permissions while WAL/SHM are open and after repeated initialization. All 60
P21 unit/API cases pass on Windows (32.44s), Ruff/format/mypy/Bandit pass. The
first dashboard run [38147200748](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38147200748)
passed. PostgreSQL/container/secret gates remain pending the corrected CI run;
later steps were skipped in that first failed foundation run.

The corrected foundation run [38154688734](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38154688734)
passed **749 tests / eight skips, 241.69s**, with actual PostgreSQL 17, frozen
lock, Ruff/format, strict mypy, Bandit, dependency audit and TruffleHog. Docker
build and native-library imports passed. The added P19 runtime smoke then found
that the image omitted `scripts.build_tejhq_research` and its transitive
`scripts.acquire_tejhq_research` import. The Dockerfile now includes these two
unchanged helper modules; their guarded acquisition/replay entry points are never
executed by imports or the bounded smoke. The strict container scan was skipped
after this smoke failure, so this run is not reported as a container scan pass.
The corresponding dashboard run 38154688778 passed. No domain code was changed.

Baseline actual CI is confirmed: foundation run 38140990151 passed ordinary
quality/PostgreSQL/TruffleHog/build and failed strict Trivy with 44 HIGH instances,
eight unique CVEs, zero CRITICAL. P21 retains strict scanning and adds actual
container auth/native smoke plus removal of unnecessary mount/umount SUID bits.
Local Docker was unavailable; shared infrastructure was not reset. See the
[eight-CVE review](p21-container-security-review.md) for versions, supported fixes,
presence evidence and unchanged secret-scan history.

Final code revision `4ad6bdc8db36898d72ce8f00ed9f26ee16eab2af` was pushed normally.
[Foundation 38155163814](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155163814)
passed 749 tests / eight skips in 253.20s with PostgreSQL 17; frozen lock, Ruff,
format, strict mypy, Bandit, pip-audit and TruffleHog (zero verified/unverified)
passed. Docker build, native ML/API/worker imports, non-root/build-tool boundary,
Argon2id/bootstrap/session/revocation and mount-helper permission smoke all passed.
[Dashboard 38155163752](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155163752)
passed. The only remaining foundation failure is strict Trivy: 44 HIGH instances,
eight unique CVEs, zero CRITICAL. All affected versions/instances match P20; no
FixedVersion is supplied by the actual Debian 13.7 image report. The
[actual scan receipt](p21-container-scan-status.json) retains image ID/raw SHA256.
No security policy was disabled or weakened. CI is not claimed wholly green.

GitHub skips are five local frozen-archive reads and two local research-fixture
reads without their external files, plus the production/live gate. The five
archive reads and two research-fixture reads passed on Windows; all ten
PostgreSQL cases skipped locally passed in CI. Across current Windows/Linux
receipts, 756 distinct repository cases passed, one production/live case remains
intentionally unavailable. This is combined evidence, not a single zero-skip run.

**P21_DEVELOPMENT_PASSED.** **P21_SECURITY_READINESS = BLOCKED_FOR_PRODUCTION.**
**CONTAINER_SECURITY_GATE = FAILED.** The development pass is independent of
unresolved supported-distribution CVEs, HTTP/public-deployment/multi-owner/data
clearance gates. The [delivery report](p21-github-delivery.md) records commits,
pushes, head-specific CI and operator handoff. Final handoff changes are metadata/
documentation only and reuse the verified code tests.

Setup, password/session/recovery diagnostics and safe stop commands are in
[verified Windows operations](../security/p21-windows-commands.md). The complete
[security architecture/threat model](../security/p21-authentication.md) and
[57-route matrix](../security/p21-api-access.json) explain deployment/ownership
limits. P22 can be considered only after a separate user authorization; none of
P22–P25 is implemented by this checkpoint.
