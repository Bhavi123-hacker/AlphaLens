# P22-P25 final local development verification

Date: 2026-10-11. Branch `p22-p25-final-development`, approved P21 baseline
`de80e3d136287e0834429bd8d93b18ab3846ba98`. Main remains
`9fa82284936f8b7a34f5409ba25cdce3538747b6`. This sprint stops after P25.

## Phase outcomes

| Gate | Status | Executed evidence |
| --- | --- | --- |
| P22_DEVELOPMENT_STATUS | PASSED | Actual protected health/metrics, durable verified probe/outbox, P20 deduplication, rotating redacted logs, online backup and isolated restore, deployed monitoring/a11y |
| P23_DEVELOPMENT_STATUS | PASSED | Real authenticated/API baseline and compiled Chromium before/after; initial Market/Backtests JS reduced by 588,970 decoded bytes; ineffective cache reverted |
| P24_LOCAL_DEPLOYMENT_STATUS | PASSED | Actual CMD setup/start/check/duplicate refusal/backup/stop/restart; compiled single loopback service and genuine isolated TEST_ONLY login; session persistence and port conflict tests |
| P25_DEVELOPMENT_ACCEPTANCE | PARTIALLY_VERIFIED | Local software/browser/preservation/security tests passed; current-head PostgreSQL/native-image CI evidence pending push |

P22 checkpoint a373f16; P23 75cbc27 plus lint import correction ff5f980;
P24 f098b8e. Final P25 commit and head-specific CI are recorded in the delivery
section after review. The original P17 API snapshot is preserved byte-for-byte;
current additive API and generated client are separately versioned in p25-openapi.

## Executed verification

| Check | Actual result |
| --- | --- |
| One ordinary Windows suite, strict warnings | **774 passed / 11 skipped / zero failures, 1208.13s**; 785 collected cases; actual frozen research reads enabled |
| Later CLI liveness correction | **29 passed, 26.18s** across three new P25 cases and affected P22/P24 cases; full Windows suite was already running and was not repeated |
| CI portability correction | **Nine passed, 16.95s** for actual Windows supervisor/API/CLI behavior; strict Linux-platform mypy passed for 225 sources, Ruff/format/Bandit passed |
| P22 targeted initial regression | 97 P22/P19/P20 cases; earlier 42 P22/P21 cases; 20 distinct new P22 backend cases passed across documented additions |
| P24 API/config/port tests | Five passed with strict warnings, 4.75s; initial root/Windows path-normalization failures corrected |
| P24 real supervisor | One passed, 8.36s; actual sockets, duplicate refusal, persisted cookie through restart, logout and cooperative stop |
| P24 sidecar/auth regression | 62 passed, 33.407s; vanished sidecar tolerated, existing unsafe sidecar rejected; all original P21 cases included |
| Frontend unit/components | **59 passed, 30.35s**, including strengthened changed-preference response/refetch regression |
| Final deployed Chromium | **17 distinct scenarios passed across runs**: final run 16 passed/one failure, then corrected lifecycle-aware alert test one passed/25.8s; not a zero-exit full-browser claim |
| P23 browser measurement/regression | Actual before/after fresh contexts; separate real stock/SMA200/gap/a11y scenario passed, 7.7s |
| TypeScript / ESLint / generated client / build | Passed against supported Node 22.23.3; current client regenerated and checked; chart-size warning remains disclosed |
| Ruff / formatting / strict mypy | Passed; 373 formatted files and 225 configured typed sources after final CLI correction |
| Bandit | Full configured source/worker scope zero findings; changed health/local scope separately zero findings |
| pip-audit / npm audit | Zero known vulnerabilities in installed audited Python dependencies / zero npm findings |
| Frozen lock / whitespace | uv 0.11.25 lock --check passed; both dependency locks unchanged; git diff --check passed |
| Research / original alert preservation | **2,485 files / 8,505,278,241 bytes**, approved SHA inventory and original 47-alert inventory unchanged, 67.929s |
| Native CMD backup / isolated restore | Passed on deployed TEST_ONLY state; manifests/hash/schema validated; restored sessions revoked; original state untouched |
| Local Docker build / rescan | Unavailable: shared daemon did not answer bounded client; no restart/prune/shared-process stop |

Windows skips: ten PostgreSQL integration cases because no ALPHALENS_TEST_DATABASE_URL
or compatible local binaries/service was configured; one deliberately blocked
production/live source gate. No SQLite replacement was claimed as PostgreSQL.
Two local retained research-fixture and five frozen archive cases ran successfully;
GitHub without those external files legitimately skips them. The existing CI
PostgreSQL 17 service supplies the missing independent database verification.

Full Windows result predates only the final CLI diagnostic correction and its three
new tests, which passed separately. It is not reported as a newly rerun complete
788-case suite. Ordinary tests use isolated TEST_ONLY computational fixtures;
none of the 152 historical fits, 504 historical backtests or 2026 final-holdout
evaluation was restarted. No training/research workload ran against the archive.

## Browser failure history and corrections

Initial P24 deployed run: nine passed/seven failed. Genuine issues were lost
preference-save confirmation after a form remount and keyboard-inaccessible
monitoring overflow. Harness assumptions included a source event on the first
ID-sorted page, development-only Origin, wrong isolated expiry root and new
monitoring label/schema assertions. These were corrected without security waivers.

Next P24 run: 16 passed/one failure in56.4s. That failure exposed an actual
vanishing SQLite sidecar ACL-inspection race; a narrowly scoped fix and negative
permission regression passed, and targeted deployed monitoring passed. Final P25
run: 16 passed/one failure in1.9m, because the prior test had legitimately persisted
ACKNOWLEDGED on the same retained alert. The corrected test respects forward-only
lifecycle and persistence; its targeted run passed. No event was reset/recreated
to make a demo or test pass. Final aggregate coverage is explicit above.

Receipts, raw audits, protected TEST_ONLY credentials/state and browser traces stay
under owner/SYSTEM-restricted `D:/al-research/p22-p25-runtime`, outside Git.
Relevant receipts: p25-full-windows.xml/log, p25-health-final.xml,
p25-frontend-tests.log, p25-browser.json, p25-browser-alert.json, p25-build.log,
p25-bandit.json, p25-health-bandit.json, p25-pip-audit.json, p25-npm-audit.json.
Preservation receipt is [versioned separately](p25-artifact-preservation.json).

## Connected workflow and regression matrix

| Module | Verification and retained limitations |
| --- | --- |
| P0-P6 | Contracts/validation/identity/universe/calendar/indicators ordinary cases; actual RELIANCE chart, SMA200, missing Muhurat slot and no fabricated price interpolation |
| P7-P10 | Chronology/OOS/persisted model/evaluation/backtest read cases; actual historical metrics and once-evaluated holdout labels; 474 unresolved economics remain withheld |
| P11-P14 | Risk/ranking/state/explanation ordinary cases and unchanged source roots; current real outputs remain unavailable |
| P15-P16 | Financial unit/FIFO/paper evidence cases; deployed pages show explicit unconfigured PostgreSQL states; independent PG CI required, no real orders or fabricated valuations |
| P17-P18 | Actual search/chart/indicators/research/backtest/nav/desktop/mobile/a11y and typed bounded reads; no financial logic moved to React |
| P19-P20 | Original six receipts/checkpoints and 47 alerts preserved; worker/policy/recovery/dedup/delivery tests; actual alert filtering/detail/read/ack/preferences, source/inference still blocked |
| P21 | Actual login, invalid credentials, refresh, expiry, revocation/password change, multi-tab logout/cache clearing, CSRF/private API/Host/origin/peer denial |
| P22-P24 | Actual status/storage/request metrics, strict private endpoints, accessible monitoring, durable outbox recovery, online backup/isolated restore, measured deferral, owned deployment lifecycle |

Mutable financial/account/alert state was tested in isolated environments, never
by changing production research observations. Database-backed pages preserve 503
when not configured. Login cannot turn absent signals into a recommendation.

## Independent system readiness

| Capability | Status |
| --- | --- |
| Local application/authentication/monitoring/notifications | Development PASSED, tested with isolated genuine accounts; operator setup still required for personal use |
| Historical research | PASSED for preserved read-only research use, not production PIT or trading profitability |
| Incremental worker | Offline/replay software PASSED; new-session live activation blocked |
| P19_LIVE_DATA_ACTIVATION | BLOCKED; zero new live sessions acquired |
| P1_PRODUCTION_DATA_CLEARANCE | OPEN |
| PRODUCTION_MARKET_DATA_USE | NOT_CLEARED |
| CURRENT_RESEARCH_SIGNAL_READINESS | BLOCKED/UNAVAILABLE; current inference/rank/signals not enabled |
| Economic validation | BLOCKED/INSUFFICIENT; 474 full paths unresolved, four candidates insufficient evidence |
| P21_SECURITY_READINESS | BLOCKED_FOR_PRODUCTION |
| CONTAINER_SECURITY_GATE | FAILED; last verified approved image 44 HIGH/eight unique CVEs/zero CRITICAL; new-head scan pending |
| PRODUCTION_DEPLOYMENT_READINESS | BLOCKED; no public listener/deployment/brokerage/acquisition/outbound task |

All eight official Debian tracker pages were rechecked; compatible supported
stable fixes remain unavailable. Full findings/versions/mitigations/residual risk:
[security review](p25-security-review.md). Historical unverified example findings
stay documented; TruffleHog policies/history are unchanged. Current-head scan is
reported separately after execution. Optional email/desktop channels remain disabled.

## Operator handoff

[Exact CMD setup/start/check/stop/account/backup/restore instructions](../operations/p24-windows-local-deployment.md).
Select existing P21 auth root when initialized, otherwise perform one explicit
hidden-password bootstrap. Copy the non-secret example only into a new private
config path; preserve existing configuration. No actual operator password/account
was generated by this sprint. Use compiled frontend, existing D-drive environment
and storage paths; Node is required only for a build. No enabled scheduled task.

## GitHub delivery

Implementation commit bc439b5265a78c26fcb2aa8e4482eb012ffc210f was pushed normally.
[Frontend CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38162509051)
PASSED: 59 tests, frozen generated client/licenses, TypeScript, lint, build and
zero dependency findings. [First foundation run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38162509049)
FAILED before tests/scans because Linux typing could not narrow a Windows-only
socket constant under `os.name`. The equivalent `sys.platform == "win32"` guard
preserves runtime binding behavior and allows platform-specific static narrowing.
Nine affected Windows cases and strict Linux-platform typing passed after correction.
No scanner/settings/permissions changed. Corrected-head PostgreSQL/native smoke/
scanner results remain pending. No merge or force push is authorized.
