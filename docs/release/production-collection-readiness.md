# Daily collection reliability and monitoring

Software changes preserve strict provider/identity/calendar/clock validation and
the approved500/250/600/1800 policy. No manual provider call, scheduled-task change
or expanded collection was made.

Malformed individual candle replies previously aborted the batch. They now get
sanitized immutable failure-attempt receipts and the remaining securities
continue. Authentication/permission/rate-limit responses still stop collection.
An interrupted raw write without its completed immutable response receipt is
preserved and reported as an orphan, never overwritten or silently adopted.
Other securities continue; an operator must resolve the orphan's evidence.
Replay uses accepted checkpoints and cannot duplicate accepted candles.

The read-only `scripts.nse_collection_status` command validates saved source
evidence and reports expected/retained sessions, per-security missing reasons,
last accepted-observation and failed runs, actual versus reserved requests,
remaining workflow capacity, unfinished reservations, next scheduled execution
and forecast freshness. Last successful means at least one accepted observation;
it never implies full500 coverage. A failed/partial terminal remains explicit.
The missing aggregate daily-success series is not replaced by session coverage.

After each durable collection terminal, a separate derived monitoring stage
records partial coverage, failure, missing terminal, stale forecasts and quota
conditions using the existing P20 local alert infrastructure. Publication failure
cannot replace or corrupt the collection terminal. Derived alerts and immutable
snapshots live only under `<market-root>/operational-monitoring-alerts`; original
47 alert records and outbound channels are untouched. Alert history may include
conditions that subsequently cleared. Reads neither initialize stores nor replay
the full raw archive.

Authenticated `GET /api/v1/nse-market/collection-health` serves that saved evidence
and snapshot age. The dashboard refreshes this local endpoint each minute, makes
zero provider requests and marks stale/unavailable monitoring explicitly.
The default status command remains read-only. `--publish-local-alerts` is an
explicit local derived-publication option; it does not acquire market data.

Tests cover malformed replies, interrupted checkpoints, restart/replay,
duplicate prevention, quota accounting including unfinished runs, derived-stage
failure isolation, alert deduplication, original-store preservation and
authenticated read-only API behavior. Genuine full-session reliability remains
**FIXED_AWAITING_LIVE_VERIFICATION** until complete successful source receipts
exist. Current measured counts and final regression results belong to
`ALPHALENS_PRODUCTION_READINESS_FINAL.md`.
