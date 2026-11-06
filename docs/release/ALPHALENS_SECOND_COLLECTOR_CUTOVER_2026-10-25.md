# Second collector cutover — 25 October 2026

**Final outcome: authorized rollback completed and verified. Successful patched
collection is not live-verified.** The scheduled failure-propagation path was
genuinely observed: contained worker, supervisor and Scheduler all returned1,
with no surviving collector process. The earlier0x8007042B/prematureReady symptom
did not recur in this run.

The original500-stock task action is restored. Its shared runtime retains41 known
dependency advisory records. The zero-advisory patched candidate and all evidence
remain available. The separate `AlphaLens-Private-EOD-Watchlist` is unchanged.
The private application remains **http://127.0.0.1:8041/nse-market**.

## Exact authority and preconditions

The operator explicitly approved only the second action replacement and conditional
exact-action rollback on `AlphaLens-Private-NSE-Market-Research`:

```text
Protected plan:
.local-data/scheduler-recovery-20261025/candidate-review-idle-final
Plan SHA-256:
02fbe143d5fb5b361c439a4ad784f8c0fd5899aafa80130cc1c793bd479c4a24
Candidate/source fingerprint:
e4dd5159e7716ba61803d914c1cce9d2776ee832f6c5afc346fb6e68ef46d084
```

Fresh preflight at16:50:28 UTC matched the exact approved fingerprint, task
definitions, candidate installation/RECORD evidence, protected configuration,
original environment inventory and approved collection policy. The preparation
tool still uses its conservative `BLOCKED_APPROVAL` label; a separate immutable
operator receipt records the explicit approval that authorized this execution.

| Precondition | Fresh result |
|---|---|
| Candidate replay |72 passed in44.25s, warnings treated as errors |
| Candidate dependency audit |Zero known advisories,102 installed packages |
| PostgreSQL compatibility |`SELECT 1` in an explicitly read-only transaction; no writes |
| Task idle state |Enabled/Ready, zero matching collector processes |
| Previous run |`6adec2f6818a410bac529a6592fcacfb` completed; both prior reservations have durable terminals |
| Day's reservations |1,200 consumed,600 remaining; nothing cleared or interrupted |
| Reviewed task/rollback/watchlist hashes |Exact matches |
| AC sampling |31 native observations, all online over60.015seconds |
| Immediate action guard |AC online and no AC-to-DC event in preceding10minutes |

The retained20-minute power query also records earlier transitions, the last
reconnection at16:35:38 UTC /22:05:38 IST. Those events were not hidden. The
bounded sampling and immediate guard establish observed pre-action stability,
not a promise of uninterrupted future power. No power or logging policy changed.

## Action update and genuine existing trigger

The action update completed at **16:52:51.556 UTC /22:22:51 IST**. Post-change
verification completed at **16:53:16.338 UTC**: exact proposed action, unchanged
non-action XML, preserved next trigger, byte-identical watchlist, unchanged policy
and the same complete candidate/source fingerprint. No immediate rollback was
needed. The private execution directory is
`.local-data/collector-second-cutover-20261025-1646`.

Only the action arguments changed from the original `run-nse-market.cmd`
scheduled path to the reviewed `run-nse-collector-isolated.cmd` path, using the
same protected configuration, native CMD and worktree. The500-stock universe,
250/run,600 reserved/run,1,800/day, three triggers20:30/21:30/22:30 IST, cooldown,
retries, principal, credentials, database targets and model/forecast rules were
preserved. Neither wrapper nor collector was manually run.

The original **22:30 IST /17:00 UTC** trigger started the patched supervisor and
worker. Process snapshots and durable diagnostics establish the contained
supervisor/worker hierarchy. Run:
`015fa7bf88a04c308fffe6bc4250e39b`; worker launch:
`4a1e0197ccc540208d722ef2c7ea74cb`.

| UTC | Genuine evidence |
|---|---|
|17:00:02.205 | Supervisor PID23592 records `CONTAINED_WORKER_STARTED`. |
|17:00:02.420 | Worker launcher PID29536 starts, parent redirector29552. |
|17:00:07.492 | Worker-start diagnostic. |
|17:00:12.682 | Initial independent date-bounds check passes. |
|17:00:12.769 | Existing cooldown waits24.256058seconds, within its60-second bound. |
|17:00:37.036 | Durable terminal `FAILED`, stage`PREFLIGHT`, code`DAILY_DATE_OR_CLOCK_DISCONTINUITY`; zero actual GETs. |
|17:00:37.043 | Worker-finished diagnostic, exit1. |
|17:01:20.999 | Worker launcher exit1. |
|17:01:21.431 | Supervisor records `CONTAINED_WORKER_EXIT`, exit1, after contained processes terminate. |
|17:01:31.116 | First observed SchedulerReady, last result1; no matching collector processes. |
|17:03:03.618 | Conditional rollback verified. |

The initial clock check passed; revalidation during cooldown failed. No new
`started.json` reservation was created, and the shared provider attempt ledger
remained unchanged. No candles were requested, no inference ran, no forecasts or
outcomes were appended, and no new market view was published by this failed run.
The partial saved dataset remains genuine earlier evidence.

The observer flags any nonzero scheduled result using a generic critical-lifecycle
label. The retained facts support the more precise conclusion here: **exit-code
propagation and termination agreed; collection preflight failed**. A matching
failure exit is not a successful daily collection or a reason to claim complete
patched-runtime acceptance.

## Clock evidence and limitations

`daily_clock.guard()` maps several receipt-validation exceptions to the same
`DAILY_DATE_OR_CLOCK_DISCONTINUITY` code. The name alone does not prove an OS
clock jump. No retained System time-change, sleep or power event explains the
17:00:37 rejection. Later AC-to-DC/AC events occurred at17:03:24.875 and17:03:39.425,
after both the failed run and rollback; they cannot explain the earlier failure.

Saved initial bounds have width **0.063712seconds**. The unchanged drift envelope
is0.001 in each direction, maximum receipt width0.100seconds, cache age30seconds.
After the saved24.256058-second cooldown, an otherwise continuous calibration
with that initial width projects to:

```text
0.063712 + 2 * 0.001 * 24.256058 = 0.112224116 seconds
```

That exceeds100ms while still younger than the30-second age limit. A private
**TEST_ONLY** replay using the existing `Calibration.receipt` reproduces
`NTP_RECEIPT_INTERVAL_TOO_WIDE` with a continuous clock and no NTP/provider call.
The current cache freshness test considers age, while receipt validation also
considers widening uncertainty. This is a concrete interval-expiry explanation
to investigate. The exact failed recheck calibration and underlying exception
were not retained, so the replay is not a claim to possess those missing inputs
or to rule out every other clock-continuity cause.

No clock tolerance, cache, probe cadence, time setting or collection code was
changed under this action-only approval. A separate repair should preserve the
existing width/age/continuity limits and NTP probe cadence, handle valid evidence
expiry within the existing bounded cooldown window, and add regression evidence
before a new reviewed fingerprint or further cutover. Do not repair this by
widening timestamp tolerances or running an unapproved retry.

## Authorized rollback and preservation

Before rollback, native getters verified taskReady, zero matching processes,
the complete current proposal and unchanged watchlist. Only the reviewed original
action was restored. Verification confirmed all original XML and next-trigger
invariants; no task setting, trigger or quota changed.

| Artifact | SHA-256 |
|---|---|
| Restored original market XML |`a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820` |
| Preserved watchlist XML |`d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419` |

This rollback was explicitly authorized with acknowledgment of41 original-runtime
advisories. It was not a silent dependency fallback. Both environments remain
present. The next unchanged trigger is **26 October20:30 IST /15:00 UTC**, on
the original runtime. No manual retry, added trigger or request is authorized.

After rollback, all13 authenticated saved-data HTTP checks returned200 and
unauthenticated monitoring returned401. This verifies the private application,
not a successful collector status: operational monitoring retains the failure.
Read-only checks preserved all945 original forecast bodies,945 records and914
unique decisions, with zero qualified matured outcomes. Fresh research/alert
checksums passed at17:08:49 UTC: **2,485 files /8,505,278,241 bytes**, and all47
original alerts. No model, research result, forecast or financial record changed.

Retained market coverage is **499/500** for23 October; SHERVANI remains missing.
There are312 saved experimental compatible scores, with saved generation time
15:09:11 UTC; they are not new scores from this failed run. Forward metrics remain
`NOT_YET_MEASURABLE`, independent model acceptance remains absent, and public
market-data rights remain uncleared.

## Final gates

- **VERIFIED_COMPLETE:** reviewed action transition, consistent live failure
  propagation/termination, conditional exact-action rollback and preservation.
- **BLOCKED_EVIDENCE:** successful patched collection/publication; clock evidence
  renewal during cooldown must be qualified before another attempt.
- **BLOCKED_SECURITY:** restored active/shared runtime has41 advisories; retained
  patched candidate has zero. The excluded watchlist was never changed.
- **BLOCKED_EXTERNAL_DATA:** SHERVANI candle/session-tradability evidence and
  genuine matured outcomes; no synthetic replacements or denominator reduction.
- **BLOCKED_MODEL_EVIDENCE / BLOCKED_EXTERNAL_DATA:** model acceptance and public
  rights remain separate from this operational attempt.
- **BLOCKED_APPROVAL:** no further cutover or manual collection is authorized.
  Any source repair needs a new tested fingerprint and explicit action approval.

The execution starts from `45fa8621c52b7ff7608f2e5c0d010cb0fb9e0dca`; tracked
delivery changes are documentation only. Final HEAD, exact CI/security results and
private evidence hashes are pinned in
`.local-data/collector-second-cutover-20261025-1646/second-cutover-final-attestation.json`.
