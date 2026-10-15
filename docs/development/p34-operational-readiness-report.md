# P34 operational readiness — actual acceptance,15October2026

Started from verified P33 `0c6ad7d` in the owned D-drive worktree; branch
**p34-operational-readiness**. No UI/portfolio/preferences/leaderboard/Decision Desk
or public-demo feature rebuild was performed. **Current quotes are not accepted.**
The final target is not called fully complete.

## Clock and actual current-price result

Administrator resync succeeded at14:27:02IST. Independent NTP measurements still
found local lag: Windows350.8443ms, Google355.5743ms, NIST358.9628ms median in the
post-resync observations; their maximum reported distances were25.80/27.56/124.86ms.
Google's shorter path and Microsoft's path both exclude zero within those reported
intervals. These unauthenticated estimates have network/clock assumptions; they are
not UTC certification. Cloudflare's earlier probes timed out and are not passes.

At14:32 the native programmed adjustment was nominal;30seconds gained only11.1µs
against a monotonic clock. At14:47–14:48 Windows reported+96ppm adjustment, and a
second30second window gained2.9113ms (+97.04ppm). Thus **a slow correction is now
being applied**, while the final measured offset remains345.2751ms. Last-good-sync
was still14:27:02, Hold state persisted, and the service again reported stale data.
An illustrative constant-rate correction takes roughly an hour, not an assured ETA.
The [clock diagnosis/recovery note](../operations/p34-clock-recovery.md) records
uncertainty, configuration, exact observations and safe administrator options.

One explicit fresh Upstox Full Quote V3 batch after the user's resync tested all
six independently verified current NSE_EQ/EQ identities at14:34IST. It made **one
quote GET**, no retry, no history request and no price retention. Quote generation
was14:34:00.680IST; actual local receipt14:34:00.338724IST: **341.276ms ahead**.

| Stock | Reported last trade,IST | Quote generation,IST | Receipt,IST | Result |
| --- | --- | --- | --- | --- |
| RELIANCE |14:33:59.306|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|
| BAJFINANCE |14:34:00.144|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|
| TCS |14:33:58.683|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|
| INFY |14:33:59.200|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|
| HDFCBANK |14:34:00.014|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|
| ICICIBANK |14:33:59.377|14:34:00.680|14:34:00.338724|QUOTE_TIME_REJECTED|

**0/6 accepted.** All six last trades precede generation, but generation exceeds
local receipt. This is consistent with the independently observed local lag;
provider absolute clock error is not separately certified. No quote time was
edited, receipt delayed, NTP correction added, or validation tolerance relaxed.
An initial14:23batch also rejected6/6 at372.496ms; it is not the post-resync result.

Authenticated browser regression independently recorded0/6 accepted and failed
the explicit CURRENT_QUOTES test. Other display tests passed: every selected
stock used its own provider chart, latest daily session **14October2026**, distinct
from its quote/trade timestamps. No15October EOD was invented during the session.
Rejected LTP stays absent; the dashboard prominently labels its dated provider
candle fallback. Indicator end dates match the daily observations. The six-stock
browser scan reused warm snapshots where available; its additional provider budget
was5GETs in the final acceptance case, not full-universe polling.

The [official V3 contract](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/)
defines prev_close_price as the previous trading session's close. Existing exact
Decimal calculation remains LTP−prev_close_price, percentage100×difference/previous.
Fixture tests for that field and strict future/naive/malformed timestamps pass.
Because real LTP failed validation, real accepted-LTP/change display is **not**
claimed verified. Provider daily changes remain a separate dated candle calculation.

## Software changes and genuine retained-data progress

New read-only clock/quote verification tools preserve metadata only, refuse receipt
overwrite, whitelist time sources and bound requests/timeouts. Windows native
diagnostics have explicit platform guards and a protected system executable path.
One initial native-export helper failure was fixed with a documented fallback;
Linux/Windows mypy differences were fixed and checked on both platforms.

New official source-use evidence was found in
[Upstox topic17302/post3](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3).
The staff response specifically permits private non-commercial historical-data,
feature/statistics/model retention and private ML development, subject to API
terms/rate limits. The reply/profile identify a Software Engineer, Upstox; an
administrator/community manager first acknowledged the question. This is specific
market-data evidence, not general customer-data retention language. The
[source-use decision and unsent remaining clarification](../data/p34-private-upstox-use-decision.md)
records applicability, residual conditions and excluded public/commercial uses.

Within that narrow user-authorized scope, **one genuine RELIANCE14October session**
was retained in `.local-data/p34-private-operational-eod`, with official elapsed
session timing and current verified identity. First run:2GETs (timing+candle),
1observation,0missing,0features,0predictions, COMPLETED_WITH_WARNINGS. Received at
09:09:30.958379UTC on15October. Immediate replay: **0GETs, identical receipt/run**.
Actual shared daily CLI replay also made0GETs. Run ID:
`14ff78073842564bf1f0dff05b9a01815428387917b444b336a3cf38ef044015`.

UNKNOWN price basis, unavailable corporate actions/publication time, current-only
identity, incomplete peer universe and model acceptance warnings are retained.
No frozen canonical join, historical rewrite or feature promotion occurred. Only
sanitized metadata is committed; native prices remain in the ignored private root.

Fixed actual orchestration gaps: P19 requests now propagate the exact approved
source-use reference instead of a hardcoded P30 label; CLI/readiness use the same
explicit, namespace-validated isolated operational root; catch-up now consumes
verified completed receipts, reporting DUPLICATE_ACCEPTED_REVISION_NO_FETCH for
the captured day instead of incorrectly claiming it is awaiting a release. Tests
also refuse future completion evidence, escaped paths and unrelated private stores.
No permission default or model/publication gate was weakened. Original denied
P30 configuration remains unchanged; P34 has a separate private configuration.

Source/retained-release readiness is now READY_FOR_OPERATOR_TASK_ACTIVATION for
that private worker. The prepared XML remains disabled/unregistered. **No live
scheduled collection was enabled** while local clock readiness is unresolved.
Collection readiness does not establish same-day publication completeness, current
model readiness or full NSE retention. The bounded worker uses explicit past
sessions and can lag same-day EOD; missing dates/publication remain unknown.

## Exact ML blocker classification and next evidence

Actual read-only audit reverified all four frozen artifact checksums, exact ordered
38-feature columns, preprocessing lineage and restricted serialized types. No
estimator was deserialized, fitted, scored or promoted. The single qualified
private retained session clears neither compatible inputs nor acceptance.

| Blocker | Engineering state / required independent evidence |
| --- | --- |
| Adjustment basis | Adapters/compatibility checks work; provider basis remains UNKNOWN. Need authoritative raw/adjusted definition, revision scope and action treatment compatible with the frozen model; do not relabel UNKNOWN. **Missing external data.** |
| Corporate actions | Transient reference exists; complete dated known-at/ex/effective/revision/action accounting evidence is absent. Price jumps are not evidence. **Missing external data.** |
| Session calendar | Official14October timing verified; complete dated historical calendar including special sessions still absent. Preserve12November2023 Muhurat gap. **Missing external data.** |
| Eligible peers | Current2,697identity master is not a dated analytical universe or verified complete contemporaneous return20 cohort. Need series/type/membership/knowledge and revision evidence. **Missing external data.** |
| momentum_percentile_20 | Original P6 formula already exists: (less+(equal−1)/2)/(n−1) over eligible non-benchmark peers, n>1, with peer lineage/degradation. P19 correctly refuses recomputation over affected-only or six sampled stocks. **Input evidence dependency, not a missing formula.** |
| Current risk snapshots | Original P11/P12/P13/P14 engines remain; qualified compatible feature/universe/action/risk inputs are missing. Technical descriptive risk remains usable. **Missing external data.** |
| Independent acceptance | Four artifacts loading/inspecting correctly is not predictive validation. **Missing independent research evidence.** |

The separately versioned [p33.prospective.v1 protocol](../ml/p33-prospective-acceptance-protocol.md)
is retained: independent prospective registration before outcomes; exact columns,
universe/decision clocks, chronology/maturity/purge/embargo, powered sample/session
minima, baselines, calibration/stability and clustered confidence, costs/liquidity/
drawdown and independent review. Numerical margins/minima must be scientifically
predeclared, not chosen to approve the four candidates. No new protocol is invented
to avoid those requirements. A meaningful prospective record requires future
eligible sessions and matured outcomes; it cannot be compressed into this sprint.
474economic backtests remain unresolved. Current eligible ML predictions/rankings=0.

## Verification, failures and preservation

* Final actual compiled regression: **16passed/1failed in58.3seconds** over17cases.
  The failure is the explicit six-quote acceptance criterion,0accepted vs6required;
  it is not ignored, skipped or counted as passed. The passing cases cover source
  switching/selected charts, indicators/precision, observed-cohort heatmap/screener/
  comparison, auth, PostgreSQL, preferences, watchlists, exact FIFO/partial sale,
  scenarios, Decision Desk/opportunities, alert dedup, journal, CSV preview/confirm,
  historical leaders and responsive/accessibility checks.
* Earlier initial P34 run had2failures: the same actual quote criterion and a new
  test's reliance on worker-local state after Playwright restarted a failed worker.
  The latter harness error was fixed by independent observation setup. A separate
  fallback-only case passed in9.6seconds; it overlaps the final suite's fallback
  case and is not added as another distinct successful case.
* Targeted Windows suite:48passed in7.18seconds before final catch-up/portability
  refinement; final changed subset22passed in1.45seconds. These overlap. Ruff,
  format and mypy --platform linux / --platform win32 passed; runtime provider
  Bandit passed after replacing a diagnostic assert with an explicit check.
* Published unchanged synthetic demo:4passed in9.5seconds, including CSP/private
  API isolation/accessibility. No publication or real data was added to the demo.
* Actual personal online backup/isolated restore matched1profile,19TEST_ONLY
  portfolios,10watchlists,10journal entries,7rules,4recent records. Restored sessions
  revoked; source unchanged; provider payloads excluded. Personal hash
  `b91a46be017b8cf99af33ff768208b8dbb6b56cbc4d3fcd4291ccb46ac5d738d`.
* Frozen preservation:2,485files/8,505,278,241bytes and47original alerts verified
  read-only in68.665seconds. No fits, holdout/backtest reruns or domain/lock changes.
* Credential/encoding scan:877source/build files at the recorded run,0leaks;
  foreign Origin rejected; real PostgreSQL reader SELECT-only with no financial
  write privileges, original financial tables unchanged/empty. Later report-only
  files do not contain credentials. Final deployment/security receipts follow.

Real original operator account/password/personal records remain identical;
authentication browser cases used the existing isolated genuine test operator.
No original password login/reset was fabricated. Current frontend runtime source
was not changed, so its latest compiled index remains
`da8ddf75c13b15364b877dd1a1170f95e1a0c07a6b5f2876d87200dcbbcc2575`.
The normal loopback app is http://127.0.0.1:8017/login. Native restart verification
and final CI evidence are recorded in the delivery addendum.

## Container security

Supported pinned Python3.12/trixie image already upgrades compatible Debian
packages. Fresh P34 CI builds/native ML imports/authentication smoke pass, but
strict scanning remains failed; downloaded final counts are recorded below. Local
Docker daemon is unavailable, so no local image-test pass is claimed.
Official Debian trackers still mark the relevant supported-release packages
affected: util-linux CVE-2026-76642/78408/78409/78410, acl CVE-2026-54369,
ncurses CVE-2025-69720, systemd CVE-2026-16742, perl CVE-2026-9538.
See [acl](https://security-tracker.debian.org/tracker/CVE-2026-54369),
[util-linux](https://security-tracker.debian.org/tracker/CVE-2026-78408),
[systemd](https://security-tracker.debian.org/tracker/CVE-2026-16742) and
[perl](https://security-tracker.debian.org/tracker/CVE-2026-9538).
Fixes in testing/unstable are not compatible stable-security updates; no
unsupported package mixing, severity downgrade, suppression or lock modification.
No untested different-libc base is presented as a compatible fix. **Upstream
security vulnerabilities remain a production blocker.**

## Mandatory capability acceptance table

| Capability | Status | Genuine verification | Remaining requirement |
| --- | --- | --- | --- |
| Current NSE quotes | FAILED |0/6accepted; fresh post-resync quote ahead of receipt341.276ms | **Local Windows configuration:** finish/review measured time correction, then strict quote recheck |
| Latest NSE EOD candles | VERIFIED_SELECTED_COHORT | Six series end14Oct2026;15Oct EOD pending at testing | **External data:** provider publication, not invented close |
| Universal stock charts | VERIFIED_SUPPORTED_WORKFLOW |2,697current identities; six correct selected provider charts and archive separation | Actual broader price coverage requires bounded queries; no full-NSE breadth claim |
| Personal research workspace | VERIFIED | Authenticated preferences/watchlists/alerts/journal/CSV browser regression | Unsupported fundamental dimensions remain **external data** dependencies |
| Portfolio reviews | VERIFIED_DESCRIPTIVE | Manual FIFO/partial-sale/scenario/risk reviews; no ledger mutation from scenarios | Accepted economic/action-adjusted history needs **external data** |
| Historical opportunity discovery | VERIFIED_WITH_COVERAGE | Genuine archive leader scan in browser; P33strict/partial-window rules unchanged | Strict long-window special-session gaps are **missing external data** |
| Daily retained NSE ingestion | VERIFIED_ONE_PRIVATE_SESSION |14OctRELIANCE,2GETs then0GETreplay, source-qualified isolated root | Expand only within private source scope; compatible model evidence separate |
| Scheduled updates | DISABLED | Offline scheduler tests; disabled XML; real source/release readiness passes | **Local Windows configuration:** clock readiness before task activation; no hidden live task |
| Complete ML features | UNAVAILABLE |38ordered contract verified; complete eligible current vector absent | **Missing external data:** basis/actions/calendar/dated peers/current risk |
| Independently accepted ML model | UNAVAILABLE | Four artifact checksums verified; no estimator execution/acceptance | **Missing independent research evidence:** predeclared prospective evaluation/review |
| Current Top5/10/20ML rankings | UNAVAILABLE | Zero accepted predictions; frozen P11–P14 unchanged | Feature/model/risk/publication gates; **external data/research evidence** |
| Public demo | VERIFIED_SYNTHETIC | Four actual published-site browser passes; no private API | Real redistribution/public advice is **contractual/regulatory**, not granted |
| Production security | FAILED | Fresh strict container scan; runtime/auth smoke separate | **Upstream security vulnerabilities**, supported fix and passing rescan |

The actual software errors found in this scope were provenance/root/catch-up
connections and diagnostic portability/test harness issues; they were repaired
and tested. None explains away the still-measured local clock lag. Private
historical retention permission now has specific evidence; public redistribution
and model acceptance remain independent, not generic development-incomplete labels.

## Delivery and commands

Branch **p34-operational-readiness**, pushed; no main merge. Implementation commits
82eefda,67d8ddd,7637348. Initial CI runs failed Linux diagnostics typing; that
failure is preserved and was fixed with explicit platform guards/types, not ignored.
Final CI links/results and exact additional commit IDs follow in the addendum.

Unchanged compiled UI/start/stop commands, from CMD:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p33-alphalens.cmd
```

From another CMD:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p33-alphalens.cmd
```

Private worker/manual readiness commands (no task registration):

```bat
scripts\windows\p30-daily-readiness.cmd .local-data\p34-runtime\daily-config.json
scripts\windows\p30-daily-update.cmd .local-data\p34-runtime\daily-config.json
```

These existing wrappers now resolve the explicit isolated P34 operational root.
Daily update is a real bounded acquisition command when a newly eligible past
session exists, not merely a status probe. Do not run it as a polling loop or
silently schedule it. Original P30 source-denied configuration remains untouched.

## Final verified delivery receipts

Implementation through `7637348425569e2aa3702fbc01bdec091e77f117`:

* [Foundation38712553179](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38712553179):
  quality **PASSED**, **1006passed/8skipped in282.66seconds**, actual Linux/
  PostgreSQL17. Frozen lock/sync, Ruff/format, mypy, runtime Bandit and dependency
  audit passed. Strict push-range TruffleHog found0verified/0unknown results
  (12chunks/3,209bytes). These are full-run counts, not a sum of targeted reruns.
* That same foundation run's container build/non-root/native imports/authentication
  passed; downloaded Trivy JSON confirms **44HIGH/8CVEs/0CRITICAL**, so
  strict-container and overall foundation remain **FAILED**. No suppression.
* [Frontend38712553837](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38712553837)
  **PASSED**: typecheck/lint,86tests/14files, frozen client/notices, private/demo
  builds, synthetic demo Chromium cases and npm audit.
* Extra diagnostic-tool Bandit inspection reports3LOW subprocess-use heuristics
  (B404 and two B603),0MEDIUM/HIGH. The tool invokes the protected Windows-system
  executable with an argv list, whitelisted source, no shell and bounded timeouts.
  No scanner exclusion/suppression was added; the separate tooling scan is not
  called a clean scan. Mandatory unchanged runtime scan passes. An earlier
  diagnostic assert/PATH lookup and literal token-kind heuristic were repaired
  with explicit checks, protected path and the existing enum.
* Final protected-credential/value/encoding scan: **880source/build files,0leaks**;
  same-origin/auth/read-only database checks passed. Three private failure DOM
  artifacts were removed after their failure outcomes were recorded.
* Isolated test application was stopped/restarted; personal-record hash matched
  the pre-restart backup exactly. Then it was stopped. Original8017application
  was cooperatively stopped/restarted with the same operator configuration; served
  index matched the unchanged compiled hash, original account/password/personal
  records were identical and five private API probes returned401 anonymously.
  Original47alerts and owned PostgreSQL15430remain preserved; normal app is running.
* [Sanitized verification metadata](p34-verification-metadata.json) records quote
  and trade clocks, NTP uncertainty/rate, real retained-session lineage, actual
  browser failures/passes, restore/frozen/security proof and model hashes. It
  contains no provider prices, credentials or user transactions. The published
  synthetic demo remains https://bhavi123-hacker.github.io/AlphaLens/ unchanged.

The final report/receipt commit adds no runtime/frontend change. New report-only
CI events do not replace the exact verified code outcomes above or turn the
CURRENT_QUOTES/production-security failures into passes.

## Narrow clock follow-up

See [15 October clock follow-up](p34-clock-follow-up.md) and its sanitized
measurement receipt. At 15:14 IST two independent sources still measured about
243 ms positive lag, despite active gradual correction. Per the user's conditional
instruction, no new quote request, browser acceptance rerun or task activation was
performed before convergence. The linked runbook now includes administrator-reviewed
maintenance and policy rollback, and the follow-up gives a finite ML evidence plan.
