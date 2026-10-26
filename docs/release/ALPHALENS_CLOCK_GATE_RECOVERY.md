# Daily clock-gate recovery and third-cutover readiness

Campaign date: 25 October 2026; final read-only qualification refreshed26 October.
Starting reference:
`077fc189e3340ced78957c049803e6814296396a`, branch
`alphalens-master-completion`. Clock implementation checkpoint:
`227eec0088fa5c18815840fd549fd0b023c57e89`.

**No third cutover has been performed or approved.** The original scheduled-task
action and the excluded watchlist remain unchanged. The private application is
available at **http://127.0.0.1:8041/nse-market**. New provider calls, manual
collection, quota changes, clock/power/logging changes and public deployment were
not performed. This report separates reproducible software defects from missing
original observations and future live verification.

## Failure reconstruction

Saved run `015fa7bf88a04c308fffe6bc4250e39b`, launcher
`4a1e0197ccc540208d722ef2c7ea74cb`, ran under the second approved candidate.
Times below are UTC; add 05:30 for IST. Every event occurred on 25 October.

| Time UTC | Retained evidence |
| --- | --- |
| 17:00:02.205130 | Native contained supervisor started the worker |
| 17:00:02.419675 | Worker launcher started |
| 17:00:07.492192 | Worker started |
| 17:00:12.682441 | Initial independent date guard accepted |
| 17:00:12.769425 | Cooldown began; requested wait 24.256058 seconds |
| 17:00:37.036220 | Durable preflight failure: `DAILY_DATE_OR_CLOCK_DISCONTINUITY` |
| 17:00:37.042919 | Worker finished with exit 1 |
| 17:01:20.998521 | Launcher exited 1 |
| 17:01:21.431073 | Supervisor confirmed contained worker exit 1 |
| 17:01:31.116465 | Scheduler was Ready, result 1, zero matching workers |
| 17:03:03.617582 | Previously authorized exact-action rollback verified |
| 17:03:24.874722 /17:03:39.424546 | Recorded DC/AC transitions, after rollback |

The initial local timestamp was `17:00:12.682441+00:00`; independent receipt
bounds were `17:00:14.181389+00:00` through `17:00:14.245101+00:00`, width
**63.712 ms**. Local and both bounds agreed on the IST date, 25 October.
Neither this check nor the failure crossed a UTC or IST date boundary.

The original path was `operational._run` → `daily_clock.guard` →
`quote_clock.recent` → `Calibration.receipt`, followed by bounded cooldown sleep
and a second `guard`. `recent` allowed reuse by age, while `receipt` also
required width ≤100 ms and wall/monotonic agreement. The original daily wrapper
collapsed width, stale-age, wall/monotonic, malformed evidence and IST-date
failures into one generic code.

**Confirmed software defect:** a calibration can be younger than the 30-second
cache lifetime but already unusable because uncertainty widens at 1000 ppm in
each direction. A continuous-clock replay matching the saved initial bounds
gives:

```text
63.712 ms + 2 × 1000 ppm × 24.256058 seconds = 112.224116 ms
112.224116 ms > unchanged 100 ms maximum
24.256058 seconds < unchanged 30-second maximum age
```

Only 18.144 seconds of width lifetime remain at that starting width. Frozen
original `077fc189` code returns the unusable cached calibration and raises
`NTP_RECEIPT_INTERVAL_TOO_WIDE`, then the observed generic daily error, in this
explicitly constructed replay.

**Unproven original branch:** the actual failed calibration, cache-attempt time,
raw exception, sample monotonic timestamps and process/boot observations were
not retained. The replay establishes a concrete, timing-consistent defect; it
does not recover those missing observations or prove an OS clock jump. A fresh
read-only System-log query for 16:59–17:04 UTC found only the two selected power
events after rollback. That limited log evidence cannot exclude every possible
clock anomaly. Scheduler Operational logging remains disabled and no logging
policy was changed.

The failed run created no collecting reservation and made zero provider GETs.
The existing two reservations remained 1,200 requests, with 600 unused; shared
provider attempts stayed 4,515. No reservation was erased or recycled. Worker,
supervisor and Scheduler agreed on exit 1; the earlier `0x8007042B` symptom did
not recur in this run.

## Repair and safety invariants

`workers/providers/daily_clock.py` now provides an explicit post-cooldown
`refresh`. It requires six genuinely new observations from the original two
sources, all acquired after refresh begins. It re-combines them under the
unchanged source, latency, disagreement, age, offset and width rules. Cached
evidence is never assigned a later expiry or relabelled as new.

If the current calibration is cached, renewal waits conservatively until its
original 30-second age has elapsed. It then calls the existing throttled
`recent`; the original quote-clock implementation and eight-probes-per-30-second
ceiling are unchanged. Missing/invalid evidence is not repeatedly probed into
acceptance. A new calibration must also overlap the previous independent
interval projected through actual monotonic elapsed time. That projection is
used only to test continuity; it is never accepted as a fresh receipt.

`workers/providers/clock_continuity.py` independently records native UTC,
monotonic time, process PID plus per-process UUID, exact boot identity and
suspend-inclusive/exclusive timers. Checks occur before renewal, after waiting
and probing, and before returning accepted evidence. The original wall-clock
tolerance, 5 ms plus 1000 ppm elapsed drift, is retained. Missing, nonfinite,
naive, backwards, changed-process/boot, suspended or inconsistent observations
fail closed. Continuity intervals over 120 seconds also fail; this is not a UTC
validity grant.

Windows uses precise interrupt and unbiased interrupt timers, with coarse
`GetTickCount64` retained only diagnostically. Exact boot identity uses native
`NtQuerySystemInformation` class90 with an exact32-byte result. This internal
Windows interface is changeable; absent/unsupported interfaces block acceptance
without a coarse fallback. Linux uses its boot UUID and boot/monotonic clocks.
These observations establish continuity, not independently authenticated UTC.
NTP remains explicitly unauthenticated under the existing network assumptions.

Accepted clock receipts now retain calibration identity, sample monotonic times,
the full bounded evidence, process/boot/timer observations and refresh timing.
Known receipt/continuity failures retain a sanitized stage and precise reason
in the durable terminal receipt while preserving the public generic error
where applicable. No credentials or provider URLs are included.

`operational._collection_preflight` passes only the remaining original
60-second budget to renewal. It then rechecks date/session, immutable daily
reservations, cooldown, approval, cohort and credential readiness before a new
reservation or provider meter can exist. Quotas remain250 securities/run,
600 reserved GETs/run,1,800/day and three collecting reservations/day; the
60-minute cooldown and20:30/21:30/22:30 IST triggers are unchanged.

The 60-second limit is an **acceptance/reservation deadline**, not a hard DNS or
process-termination deadline. Existing blocking DNS/NTP operations can finish
later; late evidence is rejected and cannot authorize collection. The tests
include this case. No scheduler timeout or network retry policy was changed.

Both existing launcher paths import this common checkout. The original task
will therefore load the repaired clock source on its next existing trigger,
while continuing to use its original41-advisory interpreter. The running private
application was not restarted.

## Deterministic verification and replay

The two new test modules contain66 cases, including native Windows observations.
They cover evidence widening/expiry during cooldown, valid six-sample renewal,
missing/invalid/replayed observations, independent interval conflict, UTC/IST
rollover, winter/summer India handling, wall/monotonic disagreement, suspend,
process restart, boot identity changes and budget exhaustion. Integration cases
exercise the real refresh through operational preflight and prove there is no
reservation or meter before clock acceptance; quota exhaustion fails without
clock renewal or provider access. Existing duplicate/restart/launcher tests are
retained.

The original-code replay freezes the relevant `077fc189` files. Both original
and corrected replays explicitly prohibit sockets/DNS and make zero NTP/provider
requests. The corrected replay matches the retained initial bounds exactly,
then accepts new **TEST_ONLY constructed** observations after24.256058 seconds
of cooldown,5.744942 seconds of conservative cadence wait and2 seconds of
constructed acquisition:32.001 seconds total. The new interval is40 ms wide,
age0, with six new samples and a distinct calibration ID. The original accepted
receipt is unchanged. Missing, invalid, replayed and discontinuous variants
continue to reject. This is offline software evidence, not fresh live NTP or
successful provider collection.

Primary private evidence is retained in
`.local-data/clock-gate-recovery-20261025/forensics/`:
`clock-failure-forensics.json`, `original-clock-replay.json`, source snapshots,
`replay_original_clock.py`, `replay_corrected_clock.py`, the timestamped corrected
replay and `system-clock-power-window.json`. The corrected receipt created at
17:59:48 UTC has SHA-256
`f215b66372ed98b9f8877b71cf61675a2fe6ed6e86b325602c56ade4e9fb4e91`.

| Verification | Measured result |
| --- | --- |
| Windows full backend /disposable PostgreSQL | **1,843 passed,9 skipped**,1516.77s; test exit0 and database shutdown0 |
| Frozen Windows clock and native supervisor cases | **83 passed**,17.70s |
| Exact implementation CI/Linux/PostgreSQL | **1,822 passed,30 skipped**,319.38s |
| Frontend | **130 passed /26 files**; typecheck, lint and dependency audit pass |
| Private compiled browser | **Two genuine saved-data cases plus two TEST_ONLY failure cases passed**,1.4m |
| Implementation container | Three targets,**zero vulnerabilities**,including zero HIGH/CRITICAL |
| Historical secret review | Raw exit183/clean=false;3 exact reviewed fixtures;0 verified secrets/0 unexpected findings |
| Static checks | Ruff/format,Bandit and mypy437 files pass; Linux-target typing also passes |

The full Windows run began before the final receipt-only
`sample_monotonic_seconds` audit-field addition. The83 frozen Windows cases and
the entire exact-checkpoint Linux suite include that final source. These are
reported separately rather than claiming every Windows full-run import had the
final file hash. All skips remain skips, including blocked live data, separately
configured local research evidence and optional PyTorch; no skip is an accuracy,
GPU or production pass.

The unsupported PATH Node20 frontend attempt failed before running tests.
With documented Node22.23.3, an initial default-worker run passed129 cases and
hit the existing Settings lazy-route timeout in one case while the backend suite
was active. Its log is retained. A complete unchanged run with two workers
passed all130 cases in60.24s; no assertions or timeouts were weakened. Fresh CI
independently passed the normal frontend suite and four separate synthetic-demo
browser cases. The private browser cases above made no provider requests and
are not public deployment evidence.

Implementation evidence: [foundation/security CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40219340033)
and [frontend/demo CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40219339991),
both exact `227eec0`. Full-history scanning covered all160 reachable commits,
without a since/depth limit or scanner weakening. Raw findings remain visible
and the exact reviewed-fixture manifest remains unchanged. Private artifacts are
in `ci-implementation-227eec0/`; logs and Windows/disposable-cluster results are
retained in the campaign directory.

After the documentation commit, its exact final CI, container/secret artifacts,
clean pushed-tree check, plan verification and report hash are sealed in
`.local-data/clock-gate-recovery-20261025/final-clock-recovery-attestation.json`.
The final report commit is also obtainable with
`git log -1 --format=%H -- docs/release/ALPHALENS_CLOCK_GATE_RECOVERY.md`;
its self-hash is not invented inside its own contents.

## Runtime, deployment and preservation

Read-only candidate inspection verified Python3.12.4,102 distribution versions,
the frozen lock/base interpreter and15,387 installed RECORD files with zero
mismatches. A new fingerprint also covers15,404 installed non-bytecode files
and the runtime source. No claim of prior full bitwise identity is made.
Candidate dependency audit: **zero known advisories**. The retained active
shared runtime still has **41 advisories**:certifi1,filelock3,Pillow37. This is
an active collector security blocker until a separately approved cutover passes.

PostgreSQL17.11 read-only connectivity and `SELECT1` passed. Fresh QA login and
all13 saved-data API checks returned200; unauthenticated collection-health
access returned401. The earlier retained cookie returned401; a new
authorized QA session succeeded without application restart or data refresh.

Measured saved state:3,207 searchable equities,500 with saved histories,
499/500 observations for23 October,312 genuine saved experimental predictions,
945 immutable forecast records,914 unique decisions and zero qualified matured
outcomes. Top5/10/20 return exactly5/10/20. Scores use23 October observations and
were generated25 October15:09:11.372907 UTC; they were not regenerated by this
campaign. Zero models are independently accepted. SHERVANI remains missing;
no candle or eligible-universe denominator was invented. Forward accuracy
remains not measurable.

All2,485 protected research files/8,505,278,241 bytes,47 original alerts and945
original forecast bodies passed preservation checks. The original task XML hash
remains `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`;
watchlist XML remains
`d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
The task was Ready with zero matching workers; next existing execution is
26 October15:00 UTC/20:30 IST. No live task action was changed.

## Third-cutover boundary

The new protected proposal is:

```text
D:\al-research\p28-worktree\.local-data\clock-gate-recovery-20261025\candidate-review-final
Plan SHA-256:
698a329ea7d51a4ac96acd739bf469cde937a63088c61564216e0f473236b402
Candidate/source fingerprint:
a19e1024fd39105320358c7365dc81ed04d6672c770bc2ef16d50e213d685b7d
```

Preparation was read-only with respect to the live system: all210 focused tests
passed in36.91s, source/runtime fingerprints matched before and after them, and
the installation/lock/base Python/package/RECORD checks passed. It binds the
frozen runtime/source, focused test log, original action, action-only replacement
and exact rollback XML. The separate fresh candidate dependency audit found0
advisories on26 October. Earlier approval hashes and fingerprints are invalid
for this repair. The preparation tool has no activation mode.

Fresh `verify-plan` returned `preflight=VERIFIED_COMPLETE`, the exact fingerprint
above, `tasks_modified=false`, `provider_requests=0` and
`status=BLOCKED_APPROVAL`. Its protected receipt is
`candidate-verify-plan.json`. Read-only re-verification command:

```powershell
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.nse_collector_cutover verify-plan --directory D:/al-research/p28-worktree/.local-data/clock-gate-recovery-20261025/candidate-review-final
```

The rollback XML is byte-identical to the retained original action/configuration;
it was checked without applying it. No new rollback operation or live rollback
test was performed. Fresh native AC readings also observed13/13 online samples
over60 seconds on26 October; this bounded observation must be renewed before
any future cutover and does not authorize one.

Before a future authorized change: require stable AC, fresh read-only
`verify-plan`, exact candidate/security/configuration identity, enabled idleReady
state, zero matching processes and no interrupted reservation. Change only the
reviewed market task action; exclude the watchlist and preserve every policy.
Observe the next existing trigger without manual collection. Require actual
worker termination, coherent Scheduler status, durable receipts, actual GET
accounting and genuine publication before claiming live verification. Any
conditional rollback needs explicit new approval and exact idle/action checks.

Current boundaries remain: clock repair **FIXED_AWAITING_LIVE_VERIFICATION**;
third cutover **BLOCKED_APPROVAL**; active collector advisories
**BLOCKED_SECURITY**; missing SHERVANI/forward observations
**BLOCKED_EXTERNAL_DATA**; independent model acceptance
**BLOCKED_MODEL_EVIDENCE**. Public deployment remains blocked by rights and
operator approval. Successful offline renewal does not clear these gates.
