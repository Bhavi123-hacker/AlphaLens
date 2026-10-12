# P29 autonomous research/product sprint

Start 2026-10-12T08:23:29Z; budget3-4h maximum, target completion by11:53Z,
hard stop12:23Z. Branch p29-research-intelligence-final-sprint from verified
P28 e223f8a1d94d63dc1ae0adc79d9d3c06830675e0. Worktree remains
D:/al-research/p28-worktree (name intentionally retained to preserve dependencies).
Original C/P26 5314909 is clean and untouched. No other task's work was reset/stashed.

## Existing verified work reused

P26 visual terminal and P28 six-provider/offline integration are delivered.
P28:51 targeted cases,228 overlapping regression (232distinct),71frontend,
eight distinct actual browser scenarios across7+focused1 after documented failures.
P28 source/permissions/inference/scheduler remain blocked. Exactly one previous
Alpha search, BSE only, no further quota used. Upstox still under review.
Full read-only2485file/8.5GB/47alert hashes reverified36.286s at P28 checkpoint;
actual C report hashes and Git-identical isolated checkout text verified separately.

## Ordered deliverables

1. Practical readiness: inspect installed PostgreSQL17 (17/18 binaries found,
   no service/listener running), configure only a NEW isolated local cluster if
   feasible; no unrelated DB or fictitious accounts/holdings/orders. Worktree-safe
   launcher already fixed. Cold READ_CAPACITY frontend retry verified.
2. Evidence Passport + exact per-stock why-unavailable lineage and detailed drawer.
3. Descriptive archival regime/coverage/quality-sensitivity and timelines;
   strict PIT assessment must remain INSUFFICIENT_EVIDENCE where clocks unavailable.
4. Model Reliability Matrix from stored reports, no holdout reevaluation/selection.
5. Drift/stability diagnostics (empirical Wasserstein/robust summaries, minimum
   samples, paired-cohort sensitivity; no significance or automatic promotion).
6. Independent static synthetic public-demo package with landing/interactive
   charts/heatmap/passport/methodology/architecture. Never calls private API,
   contains no private research/credentials; prepare, do not publish.
7. Actual API/frontend/browser/startup/security verification, documentation,
   meaningful commits/push/CI and final handoff. No scanner weakening.

## Research assumptions declared before running new diagnostics

Regime diagnostic v1 is exploratory, descriptive, separate from P11-P14 and model
selection. Default min128 observed securities and80% required metric coverage;
uptrend/downtrend: median20-session raw return beyond +/-3% and trend participation
beyond60%/below40%; stress: median daily volatility20 above3% and at least20% of
observed drawdowns below-10%. Otherwise mixed/sideways. Missing never zero. These
are predeclared interpretation assumptions, not calibrated market/strategy rules.
No thresholds are chosen from2026 holdout outcomes. Strict PIT requires explicit
availability clocks <=cutoff; frozen final-vintage snapshots cannot establish it.
Retrospective charts must disclose final-vintage/source/observed cohort limitations.

Drift v1 compares two ordered historical source sessions, finite same-definition
features, minimum128 observations per distribution. Report empirical distance in
original units and quantiles/missingness, not significance; paired IDs distinguish
composition change from within-cohort changes without calling it survivorship control.
Reliability statuses reflect recorded metric/calibration/sample/economic availability;
they never grant model acceptance or a profitability claim.

NEXT: finish bounded PostgreSQL readiness, then implement pure intelligence methods
and authenticated read APIs/UI. API running owned8028 may be restarted cooperatively;
do not touch other processes. P28 GitHub foundation38224098734 andfrontend38224098502
running at checkpoint; inspect later without emitting secret-scan candidates.

2026-10-12T09:10Z checkpoint: research methods + four protected APIs implemented.16 focused cases passed4.97s after fixing fixture overrides/missing model-family handling; initial Argon2 failures traced to machine commit pressure (<1GiB free virtual), not security settings. Only owned8028 API stopped cooperatively; unrelated Dell/WSL/Oracle processes untouched. Inference deserializer/training imports and CLI heavy read dependencies moved behind execution paths, preserving actual gates/hashes and shutdown access. Frontend Intelligence page (regime/reliability/drift/passport tabs), stock Evidence Passport and typed schemas wired; typecheck passed, lint pending. Strict PIT returns insufficiency for unknown clocks; archival descriptions remain explicitfinal-vintage, no current inference. PostgreSQL17/18 folders contain data only, no native tools; no listener/service; Docker client bounded15s timeout, no restart/prune. Prepare safe operator setup rather than touch existingdata. Next: finish frontend tests/browser + genuine bounded diagnostic read, static demo package + PG setup helper, security/CI/report/commits.

2026-10-12T10:02Z checkpoint:16 new intelligence cases,5 PG offline guards,1
public-generator case verified;65-case overlapping P19/intelligence/PG regression
passed,1 local PG integration skip.4 frontend cases passed. Static independent
public demo generated128 synthetic identities/90dates, no private API/model
results; actual3 browser cases passed5.70s after a documented initial2pass/1mobile
overflow failure. The original P28 tests remain reused. Genuine bounded archive
reads succeeded:2-session cold12.212s/warm0.147s, drift1.223s/passport0.340s/
reliability0.019s. Full findings stay in protected D runtime; source conditions
not changed. Latest archived regime insufficiency and strict PIT insufficiency
remain explicit. New original synthetic-demo scopedMIT + runtime notices added.
PG correction:127.0.0.1:5432 accepts TCP, anonymous access rejected; server version
not verified. Existing17/18 data folders lack tools. No DB created/migrated, no
Docker restart/prune. Hidden-password new-only PG17 bootstrap+read-only role
prepared; actual guarded CI verification pending. Compiled private app/build
verification next, then docs/security/milestonepush to allow CI.

Browser initial global setup timeout on cold login; eight-case retry running. Host commit pressure prevents a concurrent Node launch (paging-file allocation failure), so checks must run sequentially. No security/hash parameters or unrelated services changed.

2026-10-12T10:15Z checkpoint: full frontend76passed9.42s after updating the
existing navigation expectation (15destinations) and correcting an introduced
Windows text-encoding issue. Ruff436files and strict mypy262sources passed;
Bandit and pip-audit zero known vulnerabilities. Compiled private/static builds
passed with existing chart-size warning retained. New static delivery test
rerun pending. Initial private browser aborted after firstcase timeout and
secondcase slow-read failure; trace proves Chromium ERR_INSUFFICIENT_RESOURCES
fetching lazy Intelligence module, not unsupported fabricated data. Own API
stopped cooperatively, no other process changed. Generic redacted PageBoundary
recovery UI added/tested. Actual TEST_ONLY SQLite backup+isolated restore passed
with manifest and restored sessions revoked; original operational stores intact.
Eight Debian tracker pages rechecked; same stable vulnerable families, no safe
container fix. Docs/methods/API/PG/demo/security/performance drafted. Next:
first verified engineering milestonecommit/push for real CI, then bounded
private-browser resource recovery and final acceptance/handoff.
