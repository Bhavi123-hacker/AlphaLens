# Intraday V3 source activation readiness

Prepared 26–27 October 2026. **BLOCKED_APPROVAL. No activation performed.**
Private dashboard: http://127.0.0.1:8041/nse-market.

The active checkout remains clean at
`6a5b73af588624cadc1e464d8ca90b5944421893`. The isolated candidate starts at
`4ed22cca8eb668a54c3d1510d38240fde5543f08`. Preparation commits are pushed from
the isolated candidate to `alphalens-master-completion`; updating that remote
branch does not deploy source into the active checkout.

## Exact scope

The comparison contains ten previously delivered files and three preparation files:

| File | Review and activation decision |
| --- | --- |
| `workers/nse_market/engine.py` | Include: optional accepted-response request metadata, backward compatible with existing callers. Apply first. |
| `workers/nse_market/daily.py` | Include: same-day Intraday V3 routing and strict single-session response checks. Apply second. |
| `apps/web/src/api/nse-market.ts` | Exclude: forecast timestamp typing; no collector dependency. |
| `apps/web/src/pages/NseMarket.tsx` | Exclude: timestamp/freshness presentation. |
| `apps/web/tests/nse-market.test.tsx` | Exclude: display verification. |
| `tests/unit/test_nse_daily_delivery_routing.py` | Qualification only; not copied into active source. |
| `tests/fixtures/upstox_20261026_empty_daily.json` | Qualification only: retained empty envelope, no prices. |
| `tests/fixtures/upstox_20261026_empty_daily.metadata.json` | Qualification provenance only. |
| `docs/release/ALPHALENS_MARKET_DATA_DELIVERY_RECOVERY.md` | Investigation evidence; excluded from activation. |
| `DECISIONS.md` | Existing decision record; excluded from activation. |
| `scripts/nse_intraday_activation.py` | Preparation only: read-only CLI and TEST_ONLY byte-transaction primitive; not imported by the collector. |
| `tests/unit/test_nse_intraday_activation.py` | Preparation qualification only; excluded from active source. |
| `docs/release/ALPHALENS_INTRADAY_V3_ACTIVATION_READINESS.md` | Preparation report only; excluded from activation. |

This preparation adds an isolated plan builder/verifier and TEST_ONLY tests.
Those preparation files are also excluded from the two-file activation payload.
No new package, environment installation, dependency version, model, database
schema, task action, launcher, supervisor or clock implementation is proposed.
The sole new import in the worker diff is the existing Upstox `Operation` type.

| Payload | Exact proposed disk SHA-256 |
| --- | --- |
| `engine.py` | `fbe48eb3d0dbcca64b2a44b3da59c952cce81f71337f27f1f6ea438104987588` |
| `daily.py` | `0d5629022a2b597ff46ea50c4e64b6168a53b1835fb31839126905fc7b7bff46` |

Current combined runtime/source fingerprint:
`a19e1024fd39105320358c7365dc81ed04d6672c770bc2ef16d50e213d685b7d`.
Proposed combined fingerprint:
`98d635dc30737ac7c034fbcd6bd463ac4a4553878e4efac906ee4f4701c05eac`.
The latter is a projection using the same verified installation and only the two
replacement files; it has not been observed in an activated collector. The
326-file proposed source aggregate is
`e13b20bbcbe5eb948ff5bc00dec9be27e8a655d198f2f7e6b18c546ddf77bf47`.

## Request and acceptance contract

[Official Intraday V3 documentation](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data/)
defines `GET /v3/historical-candle/intraday/{instrument_key}/days/1` for the current
trading day, without from/to dates. The existing adapter percent-encodes the key
once (`NSE_EQ%7CISIN`). Historical targets retain the existing historical route
and original date bounds. No extra historical fallback request is introduced.

The independent IST date, official completed-session fact, original candle schema,
OHLCV validation, receipt bounds, security identity and corporate-action gates
remain enforced. Exactly one target-session daily candle is required. Empty,
wrong-day, duplicate, multiday and pre-close replies remain unavailable. A reply
crossing into the next day cannot be accepted under the earlier day's guard.
Older missing sessions remain missing; the correction does not backfill them.

[Published standard API limits](https://upstox.com/developer/api-documentation/rate-limiting/)
are 50 requests/second, 500/minute and 2,000/30 minutes per API per user. The
existing shared conservative rate limiter remains unchanged. These published
windows are separate from the operator's 600 reserved GETs/run and 1,800/day.
The existing 250-stock envelope remains within its 600-request ceiling
(500 candle/action requests plus up to 71 existing overhead requests). Adding
250 fallback requests would exceed that envelope and is explicitly excluded.

[Analytics Token documentation](https://upstox.com/developer/api-documentation/analytics-token/)
describes historical-data access; it does not establish this operator's current
token validity, all endpoint permissions, public display rights or an exact
after-close publication/finality guarantee. No authenticated permission probe or
live routing comparison was performed during preparation.

## Independent failures retained

On 26 October, the 21:30 run
`bd3661ba454c416a9b6034ac56a6b61a` lost its ancestor at
16:10:12.161069 UTC and the supervisor interrupted the worker with exit 125.
A DC transition at 16:10:11.0572018 UTC and AC restoration at
16:10:13.0831103 bracket that event. The task stops on battery under its existing
policy. This is a strong temporal association, not proof of the exact terminating
process. The 30-minute execution limit had not elapsed. Scheduler Operational
logging is disabled and access to Security process-audit events is denied; neither
setting was changed. Its missing terminal receipt and reservation are preserved.

The 22:30 run `42825678795f45049755ab6d6ecfdcd7` failed at
17:00:24.130159 UTC with `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`, before any new
reservation or GET. Worker, launcher, supervisor and Scheduler consistently
reported failure. The retained calibration result is unavailable; individual
probe timeout/sample/width rejection detail was not retained. A clock jump or
stale cooldown evidence is not established. Routing changes fix neither failure.

## Verification and preservation

The focused routing/activation suite passed 57 cases, including fixture success,
saved-empty replay, no fallback, day rollover, bounded requests, payload/hash/path
tampering, interrupted two-file application, reverse rollback, duplicate apply,
unknown edits and post-power runtime/source/accounting drift. Fixtures are
TEST_ONLY and provide no evidence of fresh provider candles or forecast accuracy.
Broader focused regression passed 668 cases (1,042 unrelated cases deselected).
Ruff, formatting and mypy passed (439 checked source files). Exact preparation-commit
CI results are sealed in the private qualification receipt before the final
protected plan is produced.

Fresh 27 October read-only qualification verifies 2,485 research files
(8,505,278,241 bytes), 47 original alerts, all 945 original forecast bodies,
914 unique decisions, zero qualified outcomes and PostgreSQL connectivity.
The patched interpreter's dependency audit reports zero known advisories.
No package or original record was modified. The existing 08:30 watchlist run
added two successful provider attempts while preparation resumed: the shared
ledger therefore contains 5,019 attempts, compared with 5,017 in the prior
evening's baseline. No manual provider request was made. Both missing historical
terminal receipts remain untouched. Calendar-day quota accounting is not reset.

The market task and watchlist XML hashes remain respectively:
`12ad71c4bdafeaa84f5ea8fc3ad00d1b2791af2d14663883463d7c1747fd73ef`
and `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
The market task is enabled/Ready with zero matching collectors. Its existing
next trigger is 27 October 20:30 IST, followed by 21:30 and 22:30. The watchlist,
500-security policy, quotas, cooldown, retries, credentials and targets are unchanged.

Latest retained price coverage remains 499/500 for 23 October; no 26 October
candles are accepted. The 312 saved predictions are historical experimental
outputs. There is no new successful collection or fresh prediction claim.

## Protected proposal and approval boundary

The final plan is produced only after preparation code is committed and its
required checks pass, under:

```text
D:\al-research\p28-worktree\.local-data\intraday-v3-activation-20261026\candidate-review-final
```

`plan.json` binds the exact source commit, changed-file hashes, original literal
disk bytes, proposed bytes, current/projected runtime identities, both task XMLs,
unchanged config/approval/reservation/accounting state, qualification evidence,
ordered procedure, preconditions and conditional rollback. Its final SHA-256 is
reported in the delivery message and a separate private attestation. Private
plans, credentials and retained data are never committed.

The verifier is read-only and explicitly reports its identity/power subset.
It does not grant authorization or replace fresh full dependency, preservation
and database checks. It rechecks active-path process identity, tasks, source,
runtime and ledgers after the AC sample. Stable AC requires at least 60 seconds
of samples and no DC event in the preceding ten minutes. Any changed hash,
unexpected process, active reservation, insufficient trigger distance, uncertain
clock evidence or failed security gate means stop. No clock/NTP probe is made
by the preparation tool. The plan expires before the next scheduled trigger.

After a new exact approval and all fresh gates, the procedure permits only
`engine.py` then `daily.py` replacement, keeping the same task action and patched
interpreter. A critical attributable failure requires an explicitly authorized
conditional rollback, only while idle with recognized old/new source bytes:
restore `daily.py` first, then `engine.py`, and verify the original fingerprint.
Unknown edits must not be overwritten. Rollback changes no data or reservation
and retains the patched zero-advisory interpreter; it does not return to the
old 41-advisory runtime. Do not fast-forward the complete candidate into active.

**BLOCKED_APPROVAL:** no source replacement, task change, collector restart,
manual collection, added provider call, quota reset or public deployment is
authorized by this preparation. Genuine live collection remains unverified.
