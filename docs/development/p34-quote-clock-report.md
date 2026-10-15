# P34 bounded quote-clock validation — actual acceptance

15 October 2026. Continued `p34-operational-readiness` from `f53a83c`; narrow
user-authorized receipt calibration, not a new feature phase. Financial formulas,
models, archive, portfolio, Decision Desk and public demo are unchanged.

## Implementation and trust boundary

[Policy, formulas, thresholds and limitations](../operations/p34-quote-clock-policy.md).
Two independent fixed NTP providers, three samples each, bounded uncertainty,
agreement/latency/freshness checks, replay/originate validation and memory-only
30-second evidence lease. Actual quote generation must be <= the **lower** UTC
receipt bound; generation within its uncertainty interval remains rejected.
No unconditional tolerance, upper-bound shortcut, timestamp rewriting, OS policy
change, request-delay workaround or HTTP Date override. Unauthenticated public
NTP assumes trustworthy independent sources/DNS without a common-path active
attacker; this is explicitly displayed and is not production time attestation.

Windows native precise UTC and high-resolution elapsed time avoid coarse Python
3.12 Windows clock artifacts. Original provider and local timestamps remain intact.
Missing calibration prevents the quote GET. Rejected/stale quotes expose no LTP.
Cache reads and chart processing consume the evidence lease; the frontend expires
the headline early while retaining the dated EOD chart and manual refresh.

## Genuine market observations

| Verification | Result |
| --- | --- |
| Initial real NTP calibration | PASS within the documented private assumption; about 53 ms-wide conservative interval |
| One direct six-key quote batch | **FAIL: 0/6 accepted**, one GET, no retries, no candles requested |
| Direct batch generation | 16:19:31.153 IST for all six |
| Original local receipt | 16:19:31.002348 IST, preserved |
| Corrected receipt interval | 16:19:31.146659 through 16:19:31.200154 IST |
| Chronology uncertainty | Generation 6.341 ms past the earliest bound; inside the interval is not a pass |
| First authenticated browser run | 1 passed / 1 failed, 27.9 s; strict acceptance failed 0/6, EOD/chart case passed |
| Final compiled authenticated browser run | **1 passed / 1 failed, 27.9 s**; strict acceptance still failed 0/6 |
| Final browser generation | First three 16:30:06.799 IST; other three 16:30:09.208 IST |
| Final browser lower-bound gaps | 3.226 ms and 13.937 ms respectively; no acceptance override |
| Final six chart/EOD observations | All latest returned candles dated **14 October 2026**; indicators dated to returned candles |

Each browser run used two bounded three-key quote batches, session OHLC and six
candle requests: 11 provider GETs reported by its initial observation step. These
are additional browser regression requests, separate from the one direct six-key
batch. No universe polling or full-NSE breadth claim. Six exact identities were
verified among 2,697 current NSE_EQ/type-EQ identities. The final dashboard case
opened all six stock routes, checked the headline against the actual API response,
verified rejection/EOD labeling, candle chart and indicator dates, and displayed
the NTP evidence. It does not establish accepted current LTP or genuine accepted
previous-close arithmetic: those remain unverified for these rejected responses.
The unchanged Decimal previous-close formula is covered by fixtures.

Raw market bodies/prices are not in the committed receipts. Browser screenshot,
trace and video were disabled. Private failure DOM artifacts were removed after
recording failure results. [Sanitized clocks/counts receipt](p34-quote-clock-verification.json).

## Tests, failures and preservation

* Final targeted P30/P31/P34 Python run: **99 passed, 3.26 s**. Includes constructed
  future/ambiguous/stale/naive/malformed timestamps, last trade after generation,
  stale/backward evidence, clock jumps, packet roots/chronology/nonce/size/mode/
  leap/Kiss-o'-Death, source contradictions, unavailable evidence preventing
  credential access/GET, replay and display expiry. Fixtures are TEST_ONLY.
* Final frontend run: **88 passed / 14 files, 44.81 s**, one worker; typecheck,
  lint and production build passed. Earlier default-parallel run had **83 passed /
  3 timeout failures**, not a clean pass; the initial relative test import and
  React effect lint failure were corrected. No timeouts/validation limits were
  increased. Counts from reruns overlap and are not added together.
* Ruff and mypy Linux/Windows checks passed; runtime provider Bandit reported no
  medium/high findings. These do not claim the existing container gate passes.
* Actual credential/value/encoding scan: **884 source/build files, zero leaks**;
  authenticated isolated operator, foreign-Origin rejection, actual PostgreSQL
  reader read-only and zero financial write privileges passed.
* **2,485 frozen artifacts** byte-hashed successfully, inventory
  `608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`;
  **47 original alerts** hash
  `dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41`.
  No artifact normalization or research execution. An old P20 preservation helper
  initially rejected three metadata files because its expected hashes use CRLF;
  current files match P34 Git baseline bytes exactly and converting LF to CRLF
  reproduces those old hashes. The separate frozen-artifact check used exact
  bytes throughout; no scanner or preservation rule was suppressed/modified.
* Original operator/account/password/personal records matched the existing
  preservation snapshot after cooperative restart. Only frontend_root changed;
  original config backup retained privately. Five anonymous private API probes
  returned 401. Public synthetic demo files and financial dependencies unchanged.

## Remaining requirements and local handoff

**CURRENT_QUOTES remains FAILED.** Public NTP evidence was obtained, but cannot
resolve the observed quote generation to before the earliest receipt bound.
Tighter independently supported timing evidence or an unambiguously earlier
future generation is needed for this policy. Windows correction alone does not
shrink NTP/network uncertainty. The direct response was 150.652 ms ahead of raw
local receipt under the previous local-only policy; that is an observed diagnostic,
not a manually entered correction or guarantee for future responses. See the
[administrator-reviewed correction and rollback](../operations/p34-clock-recovery.md).
No clock change was made and no provider polling loop is proposed.

Daily retained collection/scheduling, original P11–P14 model gates and strict
security remain separate. No scheduler activation, retained-data permissions
expansion, accepted model or Top 5/10/20 prediction follows. Production container
security retains its recorded upstream failures until a genuine passing rescan.

Normal application: http://127.0.0.1:8017/login. Latest compiled index SHA-256:
`89c37e810a429c8a9eee48d675c13cf468d4beffdac1b7a11c18be7aaba2312f`.
Existing CMD start/stop entrypoints use the updated private configuration:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p33-alphalens.cmd
```

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p33-alphalens.cmd
```

Branch: `p34-operational-readiness`, no main merge. Verified implementation pushed
as `8358c5e044416abfbf9048f24d60242d52fa2755`.

## GitHub delivery receipts

* [Foundation 38724839911](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38724839911):
  quality **PASSED**, **1047 passed / 8 skipped in 290.52 s**, real Linux/
  PostgreSQL 17. Frozen dependencies, Ruff/format, full mypy, runtime Bandit,
  dependency audit and required secret scan passed. Cloud CI does not run the
  credential-protected genuine Upstox acceptance test; its 0/6 failure above remains.
* The same foundation run's strict-container job **FAILED**. The downloaded fresh
  Trivy JSON contains **44 HIGH / 8 unique CVEs / 0 CRITICAL**, no listed fixed
  versions. Overall foundation is **FAILED**, not green. No scanner suppression,
  severity reduction, package mixing or security-gate change.
* [Frontend 38724839982](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38724839982):
  **PASSED**, 88 tests / 14 files in 7.18 s; typecheck/lint, compiled private/demo
  builds, **4 synthetic demo browser cases in 6.7 s**, and audit (0 vulnerabilities).
  These synthetic checks do not replace the separate authenticated real-provider
  browser run's one pass/one failure.
* Normal 8017 app was restarted from the final code and compiled build; index hash
  matched, original account/password/personal records matched, five anonymous
  private endpoints returned 401. Isolated 8029 test instance was stopped. Owned
  PostgreSQL remains running. No Windows clock/service policy changed.

This report-only follow-up records completed results for the exact implementation
commit above. It does not turn real quote or production-security failures into passes.
