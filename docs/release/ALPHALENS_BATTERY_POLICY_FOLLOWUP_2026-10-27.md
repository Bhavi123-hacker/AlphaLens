# NSE battery-policy execution and 21:30 follow-up

Private dashboard: http://127.0.0.1:8041/nse-market.
The active collector remains the reviewed patched runtime with fingerprint
`98d635dc30737ac7c034fbcd6bd463ac4a4553878e4efac906ee4f4701c05eac`.
This follow-up changes no active collector code, task, application configuration,
clock rule, provider permission, reservation or protected data.

## Approved change was not applied

The operator approved only the two NSE task battery flags under protected plan
SHA-256 `24698ecdfc693c333c904bc9a823e7865f7fdc6569eb2fdd8d3d1496cd19636b`.
Its expiry was **27 October 2026, 21:15 IST**. The watchlist was excluded.

Fresh read-only checks passed: exact plan/artifacts, original task definitions,
idle Ready with zero workers, 326 source hashes, full installed RECORD/runtime
identity, read-only database connectivity, unchanged application configuration,
request/reservation state, 2,485 protected research files, 47 original alerts,
945 original forecast bodies and 19,503 original market-store files. Three
explicitly derived health pointers are excluded from the original immutable-file
comparison; their earlier bytes and all immutable reports remain retained.
Battery charge was 91%, then 90%, on AC, with no observed recent shutdown event
or active shutdown process. Existing idle sleep/hibernation settings were read,
not altered.

The execution wrapper first expected a flat fingerprint field while the fresh
report actually contained `identity.fresh_fingerprint_sha256`. The resulting
KeyError occurred before any task mutation. After correcting that consumer, the
native wrapper rejected execution at its additional **21:14:30 safety cutoff**;
the authorization record was created at 21:14:41.661074. This extra cutoff was
introduced by the execution wrapper, not required by the approved plan. The
format error and extra cutoff were avoidable execution defects. They are not
attributed to operator power, licensing or market data.

The native guard ran before `Set-ScheduledTask`. Readback established that both
original flags remain true and the exact original XML hashes remain:

- NSE task: `12ad71c4bdafeaa84f5ea8fc3ad00d1b2791af2d14663883463d7c1747fd73ef`.
- Excluded watchlist: `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.

No rollback was needed or performed. The original sealed plan remains unchanged
and expired; a later instruction to continue does not reuse its authorization.
Detailed evidence is private under
`.local-data/nse-battery-policy-execution-20261027-2109`, including
`stopped-execution-report.json`, native output and all successful preflight receipts.

## Actual existing 21:30 scheduled run

Run `c8d767defccd4d80b11e179dcbcdf580` was launched by its existing trigger,
without a manual collector invocation.

| Event, 27 October IST | Retained result |
| --- | --- |
| 21:30:10.409210 | Worker attempt began |
| 21:30:12.646191 | Initial independent date guard accepted six samples |
| 21:30:12.766173 | Cooldown began, shortfall 22.999826 seconds |
| 21:30:44.918001 | Durable FAILED receipt: `DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE` |
| 21:30:44.936334 | Worker finished, exit 1 |
| 21:31:08.862898 | Launcher exited, code 1 |
| 21:31:09.327337 | Supervisor confirmed contained-worker exit 1 |
| Readback | Scheduler Ready, last result 1, zero workers |

The refresh obtained no accepted calibration. `recent()` catches several
transport, validation and combination exceptions and returns `None`; the precise
rejected observations and low-level reason were not retained. The evidence does
not distinguish timeout, DNS/transport error, rejected packet, source disagreement
or interval rejection. It does not establish a clock jump, timezone defect,
suspend/resume or the identity of any network failure. No new NTP test was made.

The initial saved interval was 60.981 ms wide. Projecting it across the recorded
22.999826-second cooldown with the unchanged 1,000 ppm envelope in each
direction gives approximately 106.981 ms, beyond the 100 ms limit. Reusing the
initial evidence would therefore be unsafe even though its nominal age was
below 30 seconds. The required fresh renewal must remain in place.

The System-log query succeeded: two records exist in the selected window,
21:29:30–21:32 IST, with zero matching power/time/Kernel-General events. This
bounded absence does not prove every physical event was recorded. Unlike the
20:30 exit-125 ancestor interruption, this launch has a coherent worker/launcher/
Scheduler exit 1 and a durable terminal receipt. No ancestor interruption was
recorded for this launch.

The attempt created **no new collecting reservation**, made **zero provider
requests** and produced **zero valid candles or new forecasts**. Shared attempts
remain 5,019, including the two earlier watchlist requests today. The prior
600-request reservation remains consumed; 1,200 reserved requests remain under
the existing policy. No reservation was reset or released. Intraday V3 was not
reached, so this is not a live routing verdict. The next existing trigger is
22:30 IST; it is not manually started by this work.

## Offline repair and verification

`scripts/review_nse_battery_evidence.py` is a read-only evidence reviewer with
no task mutation, network or collector-start operation. It consumes the actual
nested runtime format, recomputes its fingerprint, checks source/integrity facts,
rejects stale or future reports, validates the exact two-node XML delta, and uses
the exact approved expiry without an added 30-second cutoff. The CLI always
uses real current UTC; it has no historical-time override or apply option.
Passing this review does not replace fresh live power/process/quota/preservation
checks or explicit operator approval.

Historical replay of the retained bundle at 21:14:41.661074 passes with
18.338926 seconds before the original expiry. This is an offline format/boundary
test, not evidence that activation occurred or could finish in that interval.
The real-time CLI rejects the expired plan with exit 2 and zero task changes.

The dependency report has zero known advisories among 93 third-party packages.
Nine exact local AlphaLens workspace distributions have no PyPI advisory entry;
their skipped status remains explicit, with source integrity/static/test checks
reported separately. Unknown skips, changed skip reasons and any reported
vulnerability are rejected. No scanner is changed or suppressed.

Verification:

- 70 focused Windows tests passed, including 25 new evidence/boundary cases and
  the existing daily-clock-refresh and scheduled-preflight tests.
- A separate five-module clock/cooldown run passed 138 tests. These runs overlap;
  their counts must not be added as a distinct-test total.
- Reconstructing the six retained initial samples reproduced the original
  initial clock receipt exactly, without network access. It does not reconstruct
  the missing refresh observations.
- Ruff and formatting passed for the whole checkout; strict mypy passed for the
  new reviewer/tests with explicit package bases; targeted Bandit passed.

Private forensic evidence is under
`.local-data/nse-battery-policy-followup-20261027-2136`.
The existing dashboard, 312 dated experimental scores, 945 forecasts/914 unique
decisions and zero qualified forward outcomes remain unchanged. Model acceptance
and accuracy claims are not advanced by software tests.

## Remaining gates

The separate replacement proposal is **INACTIVE / BLOCKED_APPROVAL**:
`.local-data/nse-battery-policy-review-20261027-final-v2/plan-INACTIVE.json`, SHA-256
`13ba808a167f863b84388378a2dad7f41790c5fc66d228c1024a5773b4df7981`.
It expires **28 October 2026, 19:30 IST** and changes only the same two NSE
battery flags. It binds original/proposed XML, exact conditional rollback,
review-only commands, the tested reviewer/tests, original failure and 21:30
evidence, source/runtime identity and unchanged quotas. It requires known battery
charge of at least 30% and neither low nor critical status regardless of AC,
no imminent shutdown/suspend, all fresh live checks and new explicit approval.
No stable-AC waiting rule, extra 30-second cutoff or clock relaxation is added.
The original expired plan and an earlier rejected preparation remain untouched;
they cannot be substituted for this final-v2 proposal.

Battery execution requires new explicit approval of this exact replacement.
It is independent of missing fresh clock evidence and does not promise
provider candle delivery. The excluded watchlist still has its separately
reported 43 shared-runtime advisories and cannot be changed under an NSE task
approval. Public market-data rights, public deployment and expanded collection
remain uncleared. No new provider request, manual collector, scheduler change,
power/clock policy change, model fit or public deployment was performed here.
