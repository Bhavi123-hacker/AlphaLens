# AlphaLens final blocker resolution — 24 October 2026

Branch: **alphalens-master-completion**. Starting reference:
`f90531362a8300b052a830766969f5498fbf4024`. Implementation checkpoint:
`3f1c98e990a74fee3d2e23c5cd47015d90eade45`; regression-contract correction:
`76ce15d6ab89faaf9370d6c1338ff61b57408619`.
The report's own commit is obtainable with `git log -1 --format=%H -- docs/release/ALPHALENS_FINAL_BLOCKER_RESOLUTION_2026-10-24.md`.
No main merge or public deployment occurred.

## Separate release verdicts

| Capability | Status | Demonstrated boundary |
| --- | --- | --- |
| Daily publication recovery and read-only status software | VERIFIED_COMPLETE | Offline financial/data guards, recovery and monitoring tests; no timestamp relaxation. |
| Reliable full-cohort fresh daily collection | FIXED_AWAITING_LIVE_VERIFICATION | Latest actual run accepted 249/500 for 23 October within quota; full-cohort reliability is not demonstrated. |
| Full saved-master search and null-data stock detail | VERIFIED_COMPLETE | Latest verified master supports 3,207 searchable equities; independent coverage and identity evidence. |
| Fresh compatible experimental predictions on observed eligible stocks | VERIFIED_COMPLETE | Existing automatic task saved 150 real predictions for 23 October; exact read-only numerical replay passed. |
| Fresh predictions across all supported equities | BLOCKED_EXTERNAL_DATA | 150 qualify; remaining observations/features are incomplete. Full-master discovery does not supply historical features. |
| Classification metrics and original-cohort Top-N evaluation software | VERIFIED_COMPLETE | Matured-only metrics, immutable selection/forecast binding and explicit undefined denominators. |
| Qualified forward performance | BLOCKED_EXTERNAL_DATA | Latest count 783 records / 752 unique decisions / zero matured; original 633 records remain separately auditable. |
| Independently accepted ML model / investment rankings | BLOCKED_MODEL_EVIDENCE | Every audited candidate remains experimental; no model promoted. |
| Three historical secret findings | VERIFIED_COMPLETE | Exact committed fixture context and fingerprints reviewed; full raw scan still reports three findings and exit 183. |
| Exact implementation CI and container evidence | VERIFIED_COMPLETE | Both workflows passed at 76ce15d; complete-history disposition and strict HIGH/CRITICAL artifacts inspected. |
| Preserved live collector's shared Python environment | BLOCKED_SECURITY | A separate read-only audit still finds known advisories in certifi, filelock and Pillow. This environment is not the patched private-app candidate. |
| Authenticated private local deployment and restart | VERIFIED_COMPLETE | Port 8041, genuine saved-data browser checks, PostgreSQL and same-session restart persistence. |
| Public redistribution rights | BLOCKED_EXTERNAL_DATA | Private source scope is not a public NSE/Upstox redistribution grant. |
| Expanded collection, live scheduler changes, production/public activation | BLOCKED_APPROVAL | No new scope, scheduler mutation, migration, paid cost or publication authorized here. |

## A. Daily coverage: actual causes and fixes

The saved **21 October** session has **248 / 500** securities. Of the remaining
252, **250 were not queried for that session** and **two have saved empty
publication responses**. Earlier 21 October candle responses were empty; a later
22 October run accepted 248 securities using **499 actual GETs**: one master,
250 candle requests and 248 action requests. Empty replies were never converted
into accepted observations or zero-valued candles.

Subsequent evidence includes an independent-clock preflight failure with **zero
provider GETs**, unfinished launcher/reservation records and Windows interruption
result `0xC000013A`. The evidence does not establish the interruption's initiator.
Scheduler exit or Ready state does not prove collection.

Three software defects were repaired:

1. A failed saved-dashboard publication after the last accepted batch could remain
   stale indefinitely: the next zero-request replay returned before publication.
   Replay now recovers a missing/stale derived view. Partial batches recover even
   if subsequent replies are all empty. Dataset **and saved score lineage** must
   match before publication is treated as unchanged. No extra acquisition or
   estimator operation is needed for recovery.
2. Task Scheduler COM returns local wall fields wrapped with misleading timezone
   metadata. Monitoring now converts those local fields using the configured OS
   timezone. This fixes display only; source timestamps and market acceptance
   clocks are unchanged. Native values were compared with PowerShell task facts.
3. The newly observed genuine run exposed another accounting defect: its raw
   terminal result inherited **500 pending before collection** although 249 had
   been accepted. Derived dashboard/status counts correctly showed 251. Future
   terminal receipts now report accepted/pending counts from the full validated
   configured cohort, retain explicit prebatch counts and include excluded
   identities as missing. Complete, partial, empty and excluded-identity cases
   passed in a **25-test** focused run. The original genuine receipt is preserved.

The read-only command is:

```powershell
$env:PYTHONPATH = (Get-Location).Path
.local-data/completion-runtime/venv/Scripts/python.exe -m scripts.nse_collection_status `
  --root .local-data/nse-market-expansion `
  --provider-root D:/al-research/p28-runtime/provider-state --observe-windows
```

It prints expected/retained session, accepted/missing securities and reasons,
actual shared-account attempts, workflow reservations, unfinished receipts, last
successful accepted-observation run, next scheduled time and forecast freshness.
It validates raw saved lineage and can take minutes; it is not a page-load path.

The initial audit lacked 23/24 October calendar facts. During the resumed session,
the **unchanged existing task** independently launched at **15:57:20 UTC** and
saved those facts. The status read beginning **16:01:09 UTC** now identifies
**23 October** as expected, with **0 / 500 accepted for that session**, while
the latest retained 21 October remains **248 / 500**. It reports **3,508 lifetime
shared attempts**, including **three on 24 October**, all marked HTTP succeeded;
HTTP success is not candle acceptance. Known terminal-reported attempts remain
2,007. Reservations are **600 on 24 October / 4,800 over all recorded days**,
not 4,800 in one day. Next scheduled trigger is **22:30 IST**. The active run has
no terminal collection result at this cutoff. The 21:30 launcher exited while
another run held the existing guard; no coverage improvement is inferred.

This campaign made **zero manual provider requests** and did not start, stop,
reconfigure or enlarge either live task. The automatic task's separately observed
three GETs belong to its pre-existing approved policy. Full current coverage and
an aggregate daily update success rate remain unverified. Detailed evidence and
per-security reasons: [daily evidence](daily-blocker-evidence-2026-10-24.md).

### Later genuine terminal receipt — supersedes the active-run cutoff

At **16:09:55 UTC**, that pre-existing automatic run completed. Its checksum-
verified receipt `5aa0183f6b514ff0a4e5aa15b57a00a9` reports **504 actual GETs**
against **600 reserved**, **249 accepted securities for 23 October**, one
`PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE` response, successful saved-view
publication, **150 actual new experimental forecasts** and no model training.
The remaining **251** comprise 250 unqueried stocks and that one pending response.
The original plan stayed at 500 and no unapproved key was added. Two observed
series changes were recorded without rewriting historical identities.

The same authorized master GET refreshed the saved instrument master to **3,207
supported equities**, observed **15:57:55 UTC**. No additional manual call or
expanded collection was used. The original clock gate passed on actual independent
bounds; no tolerance or timestamp was changed. The run's zero process exit is
reported alongside its **partial** per-security result, never as full coverage.
The following current tables use this later verified result; earlier audit facts
above remain explicitly historical.

The post-run read-only status at **16:13:51 UTC** confirms **249 accepted / 251
missing**, **504 actual requests on 24 October / 4,009 over recorded days**,
**2,511 known terminal-reported attempts**, and the same **4,800 lifetime / 600
current-day reservations**. Forecast freshness now matches the expected session,
latest retained session and current dataset. Daily success-rate inference remains
unavailable. The first resumed-run facts were observed, not manually triggered.

## All-equity acceptance, measured independently

| Measurement | Saved evidence |
| --- | --- |
| Supported / searchable ordinary equities | **3,207 / 3,207**, verified master observed 24 October |
| Equities with genuine saved prices | **500** |
| Latest retained-session prices | **249**, 23 October |
| Sufficient latest-session feature vectors | **150**, 23 October |
| Compatible latest saved model predictions | **150**, observation 23 October, generated 24 October at 16:09:14 UTC |
| Predictions for latest retained session | **150**, experimental and uncalibrated |
| Independently accepted predictions | **0** |
| Dated Top 5 / 10 / 20 returnable | **5 / 10 / 20** across all eligible saved outputs |
| No saved price / no compatible latest saved prediction | **2,707 / 3,057**; overlapping categories |
| Latest feature exclusions | 80 known-action lookback exclusions, 19 missing lookback slots, 251 missing latest observations |
| Daily update success rate | Unavailable; **49.8%** retained-session coverage is not daily run success |

There is no arbitrary 302- or 500-stock ranking cap. A TEST_ONLY regression ranks
all **725** eligible inputs before Top-N pagination. The initial genuine replay
regenerated **302** sixteen-feature vectors from **61** saved session slots and
matched pinned model scores with **zero maximum feature/score error**. Saved
Top-20 forecast/source/feature/target lineage also verified. This reproduces dated
inference; it creates no new forecast and establishes no present model acceptance.
After the scheduled run, another read-only replay regenerated **all 150 new
sixteen-feature vectors** over **61** saved slots and exactly reproduced their
model scores and Top-N lineage, again with **zero maximum feature/score error**.
The model hash is unchanged. The verification itself made zero provider requests,
forecast writes, outcome writes or fits. The current Top5/10/20 draws from all
150 eligible outputs; the earlier 302 predictions remain in immutable history.

Representative actual detail/browser checks include RELIANCE/HDFCBANK with saved
charts and scores, TCS with stale prices/no score, AEGISVOPAK with dated evidence,
AGOL with seven observations and missing lookback, master-only AAKAAR, and
unsupported 0ABCL31. No missing price/score was substituted. Authoritative sector
and market-cap classifications are unavailable and were not guessed. Identity
history presents five verified observations and explicitly excludes one older
snapshot failing derivation verification; all originals remain intact. Absence
is never presented as verified delisting. See [coverage evidence](all-nse-coverage-2026-10-24.md).

## B. Forward outcomes

All **184** V2 ledgers were read with SQLite read-only/query-only transactions;
their byte hashes were unchanged at the initial audit cutoff. **633 raw records / 602 unique decisions**
include 31 overlaps, **zero stored outcome revisions** and **zero qualified
matured outcomes**. Forecasts enter on 19 or 21 October and require five qualified
future sessions. Only consecutive official links 16→19, 19→21 and 21→22 were
saved at the audit cutoff. The 20 October closure is explicit; weekdays cannot
replace official session facts. Genuine complete five-session prices/actions and
identity continuity remain missing. Newly saved calendar facts alone do not
create a price outcome. The later automatic run append produced **783 raw records /
752 unique decisions**, still 31 overlaps and **zero matured outcomes**. Read-only
evaluation validates all original declarations and forecast lineage, reports
**602 awaiting qualified five-session outcomes / 150 future entries not started**,
and sees five declarations with zero complete cohorts. The new declared entry
session is **26 October**, as saved in the official-calendar-linked declaration.
The 150 genuine new records are distinguished from the original 633; byte equality
of append-only stores is not claimed after their authorized append.

Precision, recall, F1, balanced accuracy, tied-score ROC-AUC, Brier and score bins
are implemented where mathematically applicable. Candidate/baseline comparisons
use matched samples. Original global declarations have 302/300/300/156 members;
none is completely matured. The fifth declaration has 150 members. Their immutable
Top-5/10/20 hit rates stay null.
No surviving-outcome reranking, classifier regression error, iid interval or
calibrated gain probability is invented. The UI says **Insufficient forward
evaluation data**. No original forecast or outcome was modified or backdated.

## C. Independent model acceptance

Every evaluated candidate's verdict is **BLOCKED_MODEL_EVIDENCE**. The complete
per-model/family/horizon table and immutable acceptance requirements are in the
[forward and model evidence report](forward-and-model-acceptance-2026-10-24.md).
It covers V1, both registered four-candidate V2 sets, six sequence candidates and
all 48 original family/task/horizon candidates. No historical fit, holdout
evaluation, threshold tuning or backtest was repeated.

Current evidence does not demonstrate independent point-in-time readiness,
accepted calibration, baseline superiority with registered date-block uncertainty,
economically complete transaction-cost performance, or prospective acceptance.
474 original economic outcomes remain unresolved. Compatible inference and
attractive development-period returns do not promote a model. Risk ordering
remains **EXPERIMENTAL_RESEARCH**, with the existing daily-volatility penalty
explicitly an unvalidated engineering assumption.

## D. Secret findings and security

All three findings are deliberately invalid/example configuration fixtures, with
exact source and matched-value fingerprints registered. Locations are the command
log (historical scanner line 218, actual assignment 453), configuration test line
31 and origin validation test line 248. No value is printed. None requires
rotation as an active credential. Any newly discovered real secret would block
release and require removal plus rotation.

The native full-history scan at `76ce15d` covered **146 reachable commits /
3,941 chunks / 11,669,440 bytes**, reporting **zero verified / three reviewed
fixtures**, **raw exit 183**. The separate source-review gate passed without
calling the raw scan clean. Nineteen adversarial tests verify that new, changed,
verified, malformed or incompletely scanned findings fail. CI now scans the whole
reachable history on every event with the same pinned scanner/default detectors,
verification and strict error handling. No path/detector exclusions, scanner
suppression, severity weakening or history rewrite occurred. See
[exact fixture review](../security/2026-10-24-secret-fixture-review.md).

Local patched Python audit reported **no known vulnerabilities**; Bandit reported
no findings. Full Ruff/format and strict mypy **410 files** passed. Exact CI,
container artifact and frontend results are appended below after completion.
The shared older `.venv` is preserved and is not claimed to have been patched.
A fresh read-only audit of its actual site-packages returned findings in
**certifi 2026.7.22, filelock 4.0.10 and Pillow 12.3.0**, so that live-worker
environment remains **BLOCKED_SECURITY**. The patched isolated candidate uses
certifi 2026.10.19, filelock 4.2.4 and Pillow 13.0.0 and passed its own audit.
The task still points through `project-python.cmd` to the old environment.
Changing that live interpreter/wrapper is outside this release authorization;
no shared dependency installation was modified. An exact migration proposal is
in the runbook. Do not deploy the old environment as a production collector.

## E. Private deployment, persistence and preservation

URL: **http://127.0.0.1:8041/nse-market**. Updated compiled build:
`.local-data/completion-release/web-build-blockers-20261024`; private config:
`.local-data/completion-release/qa-config-blockers.json`. The prior compiled build
and `qa-config.json` are preserved for rollback. Candidate Python/dependencies
remain isolated; original operator credentials/configuration are unchanged.

Four compiled Chromium cases passed in **1.4 minutes**: **two genuine saved-data**
cases and **two explicit offline fixture** cases. Genuine checks cover search,
prices/charts, Top5/10/20, explanations, saved forecasts, undefined evaluation,
full-master discovery and missing-price/history/unsupported stock pages. Their
network guard rejects external/provider/refresh acquisition.
After genuine scheduled publication, the same four-case suite passed again in
**47.5 seconds** against the **150 new forecasts**. The master freshness assertion
now follows its actual saved receipt; HINDADH's 47 observations demonstrate a
current missing lookback, while AGOL now correctly reports a missing latest
session. The first repeat still expected AGOL's older reason and failed that
assertion; the software classification was correct and no data gate was relaxed.

Fresh-session HTTP checks before and after a cooperative native restart all
returned **200** for PostgreSQL readiness, health monitoring, coverage, search,
market/history, evaluation and each Top-N size. Original saved counts and ranked
keys matched, and the **same authenticated session** survived restart. Financial
and coverage reads without authentication return **401**; minimal liveness is
deliberately public. An older test session expired during the elapsed pause under
the unchanged 30-minute idle policy; it was replaced before the actual restart
comparison, without changing account credentials or timeouts.

Read-only preservation verified **2,485 frozen files / 8,505,278,241 bytes** and
**47 original alerts**. A separate check at 15:56 UTC found **zero changes across
201 original logical stores/model/configuration items**. That cutoff precedes
the independently resumed scheduled run. No protected artifact was moved,
deleted, compressed, rewritten or replaced. No disk cleanup occurred.
Measured free space near final verification: **C: 22,507,143,168 bytes (20.96 GiB)**,
**D: 80,272,896,000 bytes (74.76 GiB)**. Space recovered by this task: **zero**.

Public preparation reuses the separate synthetic-only `vite.demo.config.ts`,
`apps/web/demo` package and CSP `connect-src 'none'`. It contains no private API
proxy, actual market data or trained model. No private-data reverse proxy or
public service was enabled. Public/private deployment remains separate; exact
redistribution rights, persistent hosting/security design and final approval are
still required. No paid costs or broker actions occurred.

## Test scope and known failures

- Final focused reliability/secret tests: **63 passed** (44 + 19); subsequent
  stale-master/publication/secret rerun: **33 passed in 9.00 seconds**.
- Scoped forward/stock-history backend: **73 passed**; full-master/discovery scoped
  backend: **41 passed**. These overlap other suites and are not added together.
- Frontend: **123 tests / 25 files passed**, TypeScript/ESLint and compiled build
  passed. The build retains an existing large-chart-chunk warning.
- Windows disposable PostgreSQL regression started while final fixtures were
  still being integrated: **1,639 passed / two failed / nine skipped**, 1,580.59s;
  cluster stopped successfully. The two failures were the older partial-test
  clock fixture and outdated stale-count assertion. Their corrected focused
  tests passed. This is **not** described as a clean final Windows full suite.
- Initial checkpoint Linux CI likewise found the old stale-count assertion:
  **1,639 passed / one failed / 13 skipped**. That result is preserved; the final
  exact-commit rerun is required below.

Private logs/receipts: `.local-data/blocker-resolution-20261024`,
`.local-data/completion-blockers-20261024`, and
`.local-data/completion/saved-blockers-replay-20261024.json`. They contain private
research evidence and are not publication assets. The release runbook documents
startup, logs, rollback and remaining boundaries.

## Exact next actions

1. Observe the existing collector's genuine terminal receipt; require per-security
   accepted coverage. Preserve interrupted reservations and cooldown protection.
2. Diagnose independent-clock/publication/interruption failures using saved facts.
   Any new manual provider probe or task change needs exact approval first.
3. Accumulate qualified future session prices, official links and action/identity
   evidence. Reconcile idempotently only after the original horizon matures.
4. Obtain genuinely independent model acceptance under the original registered
   standard; keep research labels until then. Do not retune known holdouts.
5. Obtain explicit public market-data rights and final deployment approval before
   publishing private NSE observations. Synthetic public demo remains separate.
6. Approve and execute the reviewed isolated-runtime migration before treating
   the existing live collector as security-cleared. Preserve its scope, quota,
   credentials and scheduled cadence; reverify actual receipts after migration.

## Final CI and artifact evidence

Status: **VERIFIED_COMPLETE** for implementation commit
`76ce15d6ab89faaf9370d6c1338ff61b57408619`:

| Exact check | Result |
| --- | --- |
| [Foundation 40109375808](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40109375808) | Quality and strict-container jobs both passed. |
| Linux / actual PostgreSQL 17 suite | **1,640 passed / 13 skipped**, 373.69 seconds, warnings as errors. Skips remain explicit; unavailable live production behavior is not passed. |
| Lock/frozen sync, Ruff/format, strict mypy | Passed; mypy checked **410** files. |
| Bandit and patched Python dependency audit | Passed; no findings / no known dependency vulnerabilities. |
| Full-history TruffleHog source review | **146 commits / 3,941 chunks / 11,669,440 bytes**, zero verified secrets, three exact reviewed fixtures, zero unexpected findings. Raw exit **183**, disposition exit **0**. |
| Fresh strict Trivy scan | **0 HIGH / 0 CRITICAL**, created `2026-10-24T15:59:45.102969612Z`; runtime import/non-root/auth checks also passed. Lower severities are outside this configured artifact's filter. |
| [Dashboard 40109375686](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40109375686) | **123 tests / 25 files**, generated client/license consistency, typing, lint, both builds, **four synthetic-demo isolation browser cases**, npm audit all passed; zero known npm vulnerabilities. |

Trivy artifact SHA-256:
`75a83caf51f756ef342da4fc851daf4f612e5ea9add777407314a74e0d7c0829`.
Scanned image ID:
`sha256:7166a1b9c4d6e4004cb7b9725bd65432b41fe56e235b353ddc42514010dd665d`.
The sanitized secret receipt's `head` exactly equals the implementation commit.
Artifacts and logs are retained privately in
`.local-data/blocker-resolution-20261024/ci-code` and in those CI runs.

The final checkpoint also corrects terminal receipt counters and adapts the
acceptance test to newly refreshed genuine evidence. Its own exact HEAD and
fresh CI artifacts are recorded in the private final attestation:
`.local-data/blocker-resolution-20261024/final-release-attestation.json`.
Those exact-HEAD checks must pass before final delivery. No clean
documentation-only changed-range scan substitutes for implementation-history
coverage: the workflow now repeats full reachable-history scanning each time.
