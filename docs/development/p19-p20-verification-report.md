# Combined P19 activation review / P20 verification

Date: 2026-10-11. Branch: `p20-alerts-p19-activation`.
Baseline: `487a68552c79b1db1b09dfb3d03205854f26aae4`.
Authorization: D75; stop after P19/P20. Original specification unchanged.

## Acceptance and limitations

`P19_DEVELOPMENT_PASSED` is preserved.
`P19_LIVE_DATA_ACTIVATION = BLOCKED`.
`P20_DEVELOPMENT_PASSED` for the local operational alert implementation.
Production remains OPEN / NOT_CLEARED; P21 authentication is absent.
Software acceptance does not claim live source, forecast, stock recommendation,
external delivery, enabled scheduling or green container-security CI.

Before this session, P17 GET-only API, P18 dashboard and P19 incremental worker,
immutable receipts, historical replay/recovery and provider/model gates were
complete. P19 had 49 targeted cases, 43 frontend cases and five actual browser
checks; its documented combined 645-case historical verification was not a
zero-exit full-suite claim. No completed expensive research was repeated.

This session added a separate durable SQLite operational alert store, validated
fixed event templates, transactionally coupled receipt cursors/deduplication,
append-only evidence/audit, lifecycle and in-app outbox, preferences, quiet hours,
severity-aware cooldowns, finite retry/backoff, pagination/search and retention.
Source, pipeline and ML alerts consume existing validated persisted P19 evidence.
P15/P16 imports support genuine recorded portfolio/paper evidence; only isolated
TEST_ONLY imports were exercised because no new real paper transaction was needed.
Stock-event and prediction-available alerts stay rejected under current gates.

The API adds alert reads without changing default GET-only startup. Explicit local
operator opt-in enables only lifecycle/preferences projections with loopback,
Host/Origin, context-header, JSON/body-bound and closed-field checks. No webhook,
event injection, financial write, credential response or public listener exists.
CLI controls work without an enabled HTTP write server. The themed dashboard adds
bell/count, recent drawer, notification center, filters/search/pagination, evidence
and audit details, related page links and explicitly unavailable default write
controls. Overview, Data Health and Settings reuse the existing API/query/theme.

## Actual operational evidence

Six existing P19 run receipts were validated, never regenerated. The final alert
store is `D:/al-research/p20-runtime/alerts`: 47 immutable operational alerts,
15 in-app DELIVERED, 32 SUPPRESSED; lifecycle 43 NEW / four RESOLVED; unread count
11. Categories: 11 DATA_SOURCE, 14 PIPELINE, 22 ML_RESEARCH. A final replay read
six sources and published zero duplicates with zero invalid receipts. History is
available even for suppressed events; unread counts only NEW delivered alerts.
Measured replay 202.596 ms, 47-row history 2.292 ms; SQLite file 151,552 bytes at
measurement. These are local single-run timings, not production benchmarks.

During model-check development, the first parent artifact path omitted the
existing `p9` directory and produced four preliminary MODEL_MISSING diagnostics.
The implementation was corrected, all four actual artifact metadata/checksum
checks passed, and those four preliminary records were RESOLVED with an appended
OPERATOR_CORRECTION audit. Evidence was retained rather than silently deleted.
The correct checks establish fixed candidate identities/horizons/preprocessing,
cutoff and 38-column P6 feature order, not new-session inference acceptance.
No estimator was deserialized, fitted or used for forecasts.

A bounded public TejHQ metadata check recorded revision
`462800672774d71c1edb7e2c04adedff2a524aca`, repository lastModified
`2026-10-09T20:50:00.000Z`. No price payload was acquired. Actual publication,
newest observation, identity/action/calendar coverage and ongoing rights remain
unverified. Newly acquired market sessions: ZERO. Historical archive end remains
2026-10-06. Inference, current ranking/signals and stock alerts remain UNAVAILABLE.

See the [provider matrix and exact primary URLs](../pipeline/p19-activation-review-2026-10-11.md).
Official NSE public research baskets and an application route are real potential
options, but do not establish an issued zero-cost ongoing automated-use agreement.
TejHQ and Alpha Vantage are conditionally supported candidates; Yahoo is not
cleared. No candidate is approved for this ongoing worker. Provider flags and
P11-P14 rules were not relaxed. No missing-session alert was fabricated from a
weekday mask or invented release expectation. Explicit special-session evidence
is required; official Muhurat-session calendar information was reviewed.

## Automated checks

| Gate | Actual result |
| --- | --- |
| P20 unit/API | 51 distinct cases passed (37 unit, 14 API) |
| Final P20 plus unchanged P17 GET-only OpenAPI | 52 passed, 15.301 s |
| Latest API classification verification | 14 passed, 3.003 s |
| Targeted combined P19/P17/P20 | 125 distinct successful cases across recorded runs/retries; 49 P19, 25 P17, 51 P20 |
| Frontend unit/component | 50 passed, including the 43 prior cases |
| Actual Chromium | Final coherent 8 passed, 50.9 s; five existing plus three P20 |
| Accessibility | Desktop/mobile axe checks zero violations; keyboard/Escape and reduced-motion checks passed |
| TypeScript / ESLint / production build | Passed; final build 0.972 s after TypeScript |
| Ruff / formatting | Passed; formatting 330 files |
| mypy | Passed, 202 source files |
| Bandit | Passed, including API/data/domain and both worker packages |
| Frozen uv lock | `uv lock --check` passed, unchanged dependency lock |
| Python audit | `pip-audit --skip-editable`: no known vulnerabilities |
| Frontend audit | Full and production npm audits: zero vulnerabilities |
| Frozen artifacts | 2,485 SHA256-verified files, 8,505,278,241 bytes; 13.104 s |
| Git whitespace | Checked before commit |

The first P20 test run was 41 passed / one failed because a recovery test expected
TimeoutError while the existing worker correctly wraps it as DataContractError;
the oracle was corrected. The initial combined run was 120 passed / one failed:
the original P17 OpenAPI check exposed default registration of POST routes. The
implementation was corrected to omit POST routes by default; the original test
was preserved and passed. A default-state-route test was then corrected from 405
to 404 for an unregistered route. No required security assertion was weakened.

Initial P20 browser failures identified ambiguous select labels and an immediate
viewport assertion during the existing resize transition. Accessible aria-labels
were added; the new layout test waits for settled dimensions. The final all-page
run also exposed that transition in the original unchanged P19 browser test.
Desktop-width animation was disabled at the mobile breakpoint; a focused retry
and the final full eight-browser run passed. The original P19 test was not changed.

Actual browser runs used default read-only HTTP. Guarded write actions/preferences
were verified in isolated API tests and frontend component tests; actual enabled
HTTP browser mutation was not claimed. No duplicate browser worker was started
while the preceding run was active. Unrelated processes were not interrupted.

Tests cover concurrency/atomic rollback/restart, stable event identity, no replay
duplicates, payload tampering, severity/lifecycle/counts, INFO/category suppression,
overnight quiet hours/critical bypass, cooldown, finite failure retries and redaction,
retention tombstones, evidence lineage, real persisted domain contract imports,
calendar/holiday/special-session/release gates, source revision, worker-lock conflict,
blocked model/policy, disabled channels and remote/origin/API rejection. TEST_ONLY
market fixtures remain isolated; application mode rejects them. No new PostgreSQL
schema/account write was added; unchanged PostgreSQL gates are reused locally and
will also run in the existing GitHub foundation workflow.

## Preservation and security

[Preservation receipt](p20-artifact-preservation.json) records the frozen inventory
hash, protected DOCX/lock/model/dataset/evaluation evidence, unchanged P19 worker,
P11-P14/domain code and PostgreSQL migrations. Main remains
`9fa82284936f8b7a34f5409ba25cdce3538747b6`. Dataset/model artifacts and D-drive
junctions/environments are intact. No historical fits/backtests/holdout evaluation
or research snapshot generation was started.

Before P20, P19 GitHub dashboard, Python/PostgreSQL (638 passed/eight skips),
TruffleHog (zero findings), image build and runtime checks passed; strict Trivy
failed with 44 HIGH OS findings and zero CRITICAL. The prior scan offered no
FixedVersion entries. Current primary Debian tracker review still showed relevant
stable trixie vulnerabilities, with fixes limited to later distributions or
nontrivial ABI/package changes:
[CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720),
[CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742),
[CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369).
No supported stable remediation for the whole set was established. No unstable OS
mix, severity waiver, scanner suppression, history rewrite or broad container
rebuild was introduced. The image now includes required worker/schema code and CI
checks new runtime imports; its pinned OS/base and scanner policies are unchanged.
P20 GitHub head-specific results are recorded in [delivery status](p20-github-delivery.md).
The implementation push passed 689 Python/PostgreSQL cases with eight skips, but
failed on three retained historical unverified TruffleHog findings; container steps
were skipped in that run. This is not a green foundation workflow.

Desktop notification APIs were investigated using Microsoft documentation; no
compatible native delivery was configured/tested. Desktop remains unavailable.
Email remains unavailable without approved SMTP; no credentials or sender exist.
External delivery NOT_REQUESTED; no message or toast was sent. Optional digest
summaries are deferred; category/INFO suppression and cooldowns provide initial
anti-spam behavior. No Windows scheduled task was enabled or registered.

## Operator handoff and P21 boundary

[Windows CMD commands](../alerts/p20-windows-commands.md) cover source readiness,
existing blocked one-time request, receipt inspection, alert processing/history,
failed deliveries/retry, lock/model inspection, CLI state/preferences, recovery and
read-only API/dashboard startup. Commands match implemented dispatches; placeholders
for a user-selected alert/file are explicitly identified. Existing servers were
checked before startup; session-owned verification servers are stopped at handoff.

P20 software meets its local development acceptance criteria. It is ready for a
separately authorized P21 implementation, not public deployment or production use.
Remaining external gates: issued suitable ongoing data rights and delivery,
bounded genuine new-session verification, complete calendar/identity/action timing,
model/current risk/rank/signal acceptance, container security and future authentication.
No P21-P25 work was implemented. Acquisition/scheduling/outbound delivery require
independent evidence and explicit operator authorization.
