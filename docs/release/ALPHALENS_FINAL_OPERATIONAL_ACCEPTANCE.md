# AlphaLens final operational acceptance — 25 October 2026

Branch: `alphalens-master-completion`. Starting reference:
`491c93f7e34b65a5d44dc8978e8e62069948389d`. Verified implementation checkpoint:
`8ad499698dc193017ea6b60169396a683d6a2435`. Subsequent delivery changes contain
this report, the cutover runbook and browser-test synchronization only. The exact
delivered HEAD and its final CI/artifact hashes are recorded in the private
`.local-data/operational-acceptance-20261025/final-release-attestation.json` and
the delivery message. A document cannot embed its own future Git commit hash.

The authenticated private application remains **http://127.0.0.1:8041/nse-market**.
This is a verified private experimental research application; full live coverage,
collector security cutover, independent model acceptance and public data rights
remain separate, unresolved gates. No overall completion percentage is assigned.

## Recalculated measurements

The baseline was captured at **06:54:24 UTC** from a clean `491c93f` checkout.
Saved-source audits, HTTP reads and numerical replay independently agree:

| Capability | Measured result | Status |
|---|---|---|
| Supported/searchable common-equity identities | **3,207 / 3,207**, dated verified master | VERIFIED_COMPLETE |
| Saved price/chart histories | **500**; **2,707** searchable identities have no saved prices | VERIFIED_COMPLETE |
| Descriptive risk histories | **337**, where saved observations permit calculation | VERIFIED_COMPLETE |
| Approved collection cohort | **500**, unchanged | VERIFIED_COMPLETE |
| Expected completed and latest retained session | **23 October 2026** | VERIFIED_COMPLETE |
| Configured-cohort coverage | **498/500 (99.6%)**; genuine candles only | FIXED_AWAITING_LIVE_VERIFICATION |
| Historically session-eligible denominator | **Unknown**; no unsupported reduction to 498 | BLOCKED_EXTERNAL_DATA |
| Compatible latest-session feature vectors and predictions | **312**, observation23 October; saved inference24 October17:26:00 UTC | VERIFIED_COMPLETE |
| Latest feature exclusions within500 | **152** known-action lookback, **34** missing lookback, **2** missing latest observation | BLOCKED_EXTERNAL_DATA |
| Research Top5/10/20 | **5/10/20** from all312 eligible scores, before pagination | VERIFIED_COMPLETE |
| Accepted investment predictions/rankings | **0**; scores remain `EXPERIMENTAL_RESEARCH` | BLOCKED_MODEL_EVIDENCE |
| Immutable forecast records / unique decisions | **945 /914**, including31 overlapping records | VERIFIED_COMPLETE |
| Qualified matured outcomes | **0** | BLOCKED_EXTERNAL_DATA |
| Forward accuracy, hit rates, return comparison and confidence intervals | **NOT_YET_MEASURABLE**; zero qualified samples, null metrics | BLOCKED_EXTERNAL_DATA |
| Independently accepted models | **0 of63 evaluated candidates** | BLOCKED_MODEL_EVIDENCE |
| Private app / isolated collector dependency advisories | **0 /0** in fresh installed-package audits | VERIFIED_COMPLETE |
| Active shared collector dependency advisories | **41 records across3 packages** | BLOCKED_SECURITY |
| Candidate cutover | Prepared and offline verified; **not approved or performed** | BLOCKED_APPROVAL |
| Expanded daily collection / public deployment | Neither activated | BLOCKED_APPROVAL |
| Public raw-price/derived-prediction redistribution grant | Not established | BLOCKED_EXTERNAL_DATA |

The312 outputs are dated genuine saved inferences, not newly dated25 October
predictions or calibrated probabilities. Numerical replay regenerated every vector
and score with **zero maximum error**, using the unchanged model SHA-256
`f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3`.
Top20 selection/feature/target lineage matches saved forecast bodies. The risk
penalty remains an unvalidated engineering assumption. Replay wrote **zero**
forecasts/outcomes and performed no fit or provider request.

## Two missing securities and reliability repair

| Security | Saved identity / current exchange token | Last accepted candle |23 October evidence |
|---|---|---|---|
| SHERVANI | `NSE_EQ\|INE011D01013`; token764890 |19 October | Two empty arrays, received24 October16:03:30 and17:06:10 UTC |
| RRECL | `NSE_EQ\|INE0AK901016`; token764850 |21 October | Not queried for this target session |

The exchange tokens come from the24 October master and are explicitly dated.
Both identities are current common-equity entries. That does not prove historical
listing/tradability, suspension status or that a23 October candle should exist.
Saved action references are non-exhaustive; no saved action, delisting or identity
evidence conclusively explains either gap. The original empty-attempt receipts
did not retain HTTP status; the report leaves it null rather than inventing200.
Raw prices and provider bodies remain in private evidence.

A software defect let an already-attempted empty-response security consume a
bounded batch slot before an unqueried target-session security. `daily.py` now
selects unattempted target identities first, then uses dated history and stable
identity ordering. An empty directory is not an attempted request. The request,
stock-count, cooldown, calendar, timestamp and acceptance limits are unchanged.
Tests cover empty responses, bounded progress across restarts, recovery, duplicate
prevention and zero-GET replay. A genuine missing provider candle remains missing.
The repair is **FIXED_AWAITING_LIVE_VERIFICATION**, not proof of500/500 coverage.

The read-only `scripts.nse_operational_health` command joins saved coverage,
per-security gaps, forecast maturity, model verdicts, dated security/runtime
qualification, reservations, scheduler observation and publication evidence.
`--publish` writes only derived private health artifacts. Existing collection
alerts remain in their separate store; the original47 are untouched. Calendar,
master, policy, terminal, reservation, ledger and qualification changes invalidate
the snapshot, including midnight and newly completed sessions within24 hours.
Derived-report or diagnostic-disk failures cannot rewrite the durable collection
terminal or manufacture success. A successful scheduler exit is not full coverage.

Latest retained collection receipts used **1,003 actual GETs on24 October**, with
two600-request reservations. On25 October the checked500-stock reservation ledger
had no collecting reservation:1,800 reserved requests and three approved slots
remained. Unused capacity does not authorize a manual collection. Aggregate daily
update success remains unavailable; retained-session coverage is not substituted.

## Collector cutover and rollback

The exact plan and commands are in [operational-collector-cutover.md](operational-collector-cutover.md).
Both current tasks remain unchanged:
`AlphaLens-Private-NSE-Market-Research` and `AlphaLens-Private-EOD-Watchlist`.
The original RELIANCE task is outside the proposed action replacement.

The proposal changes only the500-stock task's action from
`run-nse-market.cmd PRIVATE_CONFIG auto --scheduled` to
`run-nse-collector-isolated.cmd PRIVATE_CONFIG`. Both retain native
`C:\Windows\System32\cmd.exe`, the worktree directory and the same protected
configuration. The new wrapper uses
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe` and
the existing scheduled launcher. It was **not run against the real configuration**.

Preserved policy:500 securities,250/run,600 reserved GETs/run,1,800/day,
three reservations/day,60-minute conservative cooldown and20:30/21:30/22:30 IST.
Principal, trigger boundaries, enabled states, retries, credentials, databases,
models and forecast policy are unchanged. At preparation the task was idle
`Ready`, with next execution25 October15:00 UTC /20:30 IST.

The current shared environment resolves to
`D:\al-research\p17-api\workspace-venv-original`. It remains available. Its
certifi2026.7.22, filelock4.0.10 and Pillow12.3.0 have1,3 and37 advisory records
respectively. The candidate uses certifi2026.10.19, filelock4.2.4 and Pillow13.0.0.
Frozen lock, base executable, installed versions and RECORD integrity passed.
The fresh inventory covered15,387 RECORD-listed and15,404 total non-bytecode
files; explicitly unhashed/bootstrap entries are included in the fresh hash.
No earlier complete venv manifest exists, so historical bitwise identity is not
claimed. Fresh before/after fingerprints and runtime source identity match.

Final private proposal:
`.local-data/operational-acceptance-20261025/cutover-approved-scope-final/plan.json`.
The directory name is not approval. Plan SHA-256:
`c91635db2a204ee4d47e08ccb44a0ae3026bffe0c76e563fb66da7d731c55a23`.
Candidate fingerprint:
`ac15c85b392f795b447fee121c3768431a5b9ce67f6a3cc0eeccfd36532c35f6`.

| Task artifact | SHA-256 |
|---|---|
| Actual before and rollback XML | `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820` |
| Proposed XML, not installed | `fd8ab60d851b47b83d06dce4a63847dc6de7cbaeac0420f24950bcd481eeac8a` |
| Preserved RELIANCE XML | `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419` |

Actual after equals actual before; no cutover or live rollback occurred. Rollback
verification is an offline state simulation, not a claim of Windows scheduler
transactionality. Upfront approval must cover conditional action restoration on
critical failure, with an explicit record that it restores the known vulnerable
runtime and `BLOCKED_SECURITY`. There is no silent fallback or second permission
request when that conditional restoration is already authorized. If the approval
does not cover it, do not begin cutover. Require fresh preflight and idle state
before any future approved action. Live candidate collection can be verified only
from the next existing authorized trigger's genuine receipts.

## Forward outcomes and scientific verdicts

[The complete decision/model audit](operational-forward-model-review.md) records
all914 decisions and an explicit verdict for every63-model candidate. All are
**EXPERIMENTAL_INSUFFICIENT_EVIDENCE**; none is promoted. The registry pins frozen
protocols and evidence hashes. This software/evidence review is not an external
independent acceptance signature.

Of the decisions,300 have proven required dates19,21,22,23,26 October and a
26 October10:00 UTC maturity. Another302 have only21,22,23,26 proven; the fifth
date is unknown. The312 latest entries start26 October and have only that future
date proven. Twenty October is explicitly closed in the saved official evidence.
No weekday assumption supplies a missing date. Six paths intersect known action
exclusions. Every decision still lacks future target observations; known dates
do not establish prices. Original forecast clocks/bodies and all187 ledger file
hashes were preserved in the complete read-only audit.

The append-only reconciliation path retains raw-calendar, publication, action,
identity, chronology and price gates. Projected chart prices alone cannot qualify
outcomes. Existing authorized orchestration calls reconciliation; no extra task
was installed. At zero qualified samples, accuracy/BA/precision/recall/F1/AUC,
Brier, Top-N hits, benchmark returns and confidence intervals remain null and
`NOT_YET_MEASURABLE`. No classification output becomes invented MAE/RMSE.

Acceptance still requires the registered independent evidence, including126
future decision dates,1,000 qualified outcomes,30 securities, two quarters,
date-block statistical comparisons/calibration, regime robustness and evidence-
qualified economics. Known final periods are not new untouched holdouts. No fit,
holdout retuning, corporate-action invention or frozen backtest overwrite occurred.

## Full-universe feasibility and rights

[The universe and rights report](operational-universe-rights.md) verifies all3,207
detail contracts using one indexed saved-source join, with truthful missing-price,
unsupported-instrument and insufficient-history cases. This is not3,207 individual
browser sessions or3,207 daily predictions.

An all-master successful stock cycle needs6,414 candle/action GETs, plus up to923
metadata GETs under the existing bounded plan:13 batches and7,800 reservations
against1,800/day, requiring at least five capacity days. It cannot provide full
daily coverage under the existing policy. Receipt-based ordinary seven-job
workload extrapolations span0.68–5.63 active hours; the interrupted outlier remains
separately visible. These are estimates, not a guaranteed benchmark or entitlement.
Measured scenarios include9.16–10.24 MiB incremental raw data/day and59.78 MiB per
full immutable projection; three projections plus raw observations are about
189.07 MiB/session. The46.53 GiB/252-session figure is a planning assumption,
not measured future usage. Bootstrap history is separately budgeted.

Private research and authenticated personal use remain bounded by the recorded
source permission and existing approved policy. Public display, raw redistribution,
public derived predictions and commercial use have no established clearance.
Public architecture remains gated by provider/exchange permission and explicit
operator approval; it includes HTTPS/auth, least privilege, backups/restore,
rate limiting, health/audit logs and rollback. Existing synthetic public-demo
checks are separate. No public service, network opening, paid resource, expanded
provider collection or database exposure was activated.

## Verification and preservation

| Check | Exact result |
|---|---|
| Windows candidate backend/PostgreSQL regression | **1,752 passed /9 skipped**,1451.21s; disposable PostgreSQL stopped with exit0 |
| Linux/PostgreSQL17 CI at8ad4996 | **1,748 passed /13 skipped**,348.11s |
| Frontend unit/component suite | **130 passed**,26 files,156.04s; one worker |
| Private browser saved-data and TEST_ONLY failure paths | **4 passed**,57.3s: two genuine saved-source cases and two explicitly TEST_ONLY cases |
| Private authentication browser subset | **5 passed**,19.5s: invalid login, revocation, responsive keyboard/accessibility, session inspection, cross-tab logout |
| Bound candidate cutover compatibility | **47 passed**,9.40s; launcher, faults, restart/replay, quotas and fairness |
| Tool-only post-harness verification | **15 passed**,0.51s |
| Ruff/format/mypy, core Bandit and dependency checks | Passed;431 mypy files; no core Bandit findings |
| Standalone cutover tool Bandit | Three reported LOW subprocess advisories; zero MEDIUM/HIGH; no suppression |
|8ad4996 CI foundation/frontend | Runs40176947022 /40176947075 passed, including synthetic-demo checks |
|8ad4996 strict container | **0 HIGH /0 CRITICAL**, no reported vulnerabilities; Ubuntu24.04 |
| Complete historical secret scan at8ad4996 |154 reachable commits;4,127 chunks;12,053,759 bytes; three exact reviewed fixtures; zero verified/unexpected secrets |
| Authenticated HTTP and restart persistence |13 endpoints200; unchanged saved coverage, forecast counts and Top5/10/20; same session survives restart |
| Protected research/alerts | **2,485 files**,8,505,278,241 bytes and **47 original alerts**, read-only checksums passed |

Windows skips include genuinely absent real-research fixtures and optional
PyTorch; they are not GPU/live passes. Constructed test results are never forward
performance evidence. Full CI is required again on the delivered report/test
commit; its exact results and hashes are pinned in the final private attestation.
The unchanged application modules reuse the full Windows regression; later
cutover-harness/browser-test deltas have their own passing focused verification.

The container report SHA-256 at8ad4996 is
`09ddcabf8dc4b80b4a07fd88f63dc2d95f6b2f747c1052da6e7813aeb792bfe6`.
The raw secret scanner intentionally retained exit183 and `raw_scan_clean=false`.
The three source-reviewed findings remain the PostgreSQL TEST_ONLY documentation
example and two invalid/rejected URI fixtures registered by immutable source and
fingerprint. No new exclusion, detector disablement, credential rotation waiver
or scanner severity reduction was introduced. No real exposed secret was found.

Failure evidence is retained: the first frontend run had129 passes and a cold
settings-route timeout; the unchanged suite passed130 with one worker. The first
bound cutover harness had42 passes/five Windows long-path failures, repaired by
the existing short test-root allocator. Browser failures identified an ambiguous
coverage locator and an asynchronous response assertion; the final checks retain
the assertion and verify the HTTP response before reading its rendered content.
A restart probe before listener readiness was refused; the post-ready probe is
the acceptance evidence. No test or financial validation was removed or weakened.

Native configuration:
`.local-data/completion-release/qa-config-operational-20261025.json`;
compiled frontend:
`.local-data/completion-release/web-build-operational-20261025`.
The prior configuration/build and both Python environments are preserved.
PostgreSQL listens only on127.0.0.1:15430 and the application on127.0.0.1:8041.
Overall legacy operational status may remain DEGRADED because independent
production/source/model gates are blocked; database readiness and private
research functionality do not clear those gates.

## Exact remaining actions

1. **BLOCKED_APPROVAL:** approve the hash-bound, action-only500-stock cutover and
   upfront conditional rollback scope. Recheck idle task, hashes, candidate and
   policy immediately before applying. Preserve the separate RELIANCE task.
2. **FIXED_AWAITING_LIVE_VERIFICATION:** inspect the next existing authorized run
   for RRECL progress and SHERVANI's genuine response; report configured and
   evidence-qualified eligible denominators separately. No manual request is
   included in this delivery.
3. **BLOCKED_SECURITY:** the old shared/RELIANCE path retains41 advisory records.
   The proposed500-stock cutover alone does not clear the separately preserved
   RELIANCE runtime; changing that path needs its own exact approval.
4. **BLOCKED_EXTERNAL_DATA:** wait for real future sessions/prices and complete
   calendar/action/identity/source evidence, then reconcile idempotently. Do not
   turn a scheduled maturity date into an observed outcome.
5. **BLOCKED_MODEL_EVIDENCE:** gather the registered prospective evidence and an
   independent pinned review; keep all63 candidates experimental meanwhile.
6. **BLOCKED_APPROVAL / BLOCKED_EXTERNAL_DATA:** full-universe recurring collection
   requires an exact source/cadence/quota/storage policy; public deployment needs
   explicit operator approval and verified provider/exchange redistribution rights.

No live task was changed or launched, no provider quota increased, no original
forecast/model/research/alert record deleted, no destructive cleanup performed,
no main merge made, and no public or paid deployment activated.
