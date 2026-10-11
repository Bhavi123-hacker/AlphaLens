# D75: P19 activation review and P20 local research alerts

Approved 2026-10-11 from P19 `487a68552c79b1db1b09dfb3d03205854f26aae4`
on `p20-alerts-p19-activation`. This is a user-approved amendment to historical
P19 stops; P21-P25 remain excluded. Original DOCX/research/policies are frozen.

## Recorded before implementation

P20 consumes verified P19 receipts/checkpoints and optionally verified P15/P16
local files or read-only PostgreSQL recovery. It never trains, executes an order,
calculates a competing valuation, downloads market prices or runs through page loads.
Fixed templates and validated reason codes exclude raw errors, credentials, URLs,
account names, quantities and balances. Event time is the actual persisted event
clock or a separately labeled detector observation time, never invented publication.

A separate SQLite operational store uses transactions, FULL synchronization, WAL,
unique event keys, evidence checksums, durable processed-source cursors, lifecycle
audit and a delivery outbox. Schema ownership stays in `db/`. In-app delivery is
local persistence only, separate from NEW/READ/ACKNOWLEDGED/RESOLVED lifecycle.
Deduplication survives pruning through tombstones; pruning removes only resolved
low-severity old alerts. Hard capacity guards stop cursor advancement until an
operator resolves/archives records. Source events remain recoverable upstream.

Severity-aware cooldowns and category/INFO preferences suppress delivery only.
Quiet hours defer delivery; ERROR/CRITICAL bypass them. Finite attempts/backoff
apply to failed in-app publication; external channels have no sender and stay
NOT_REQUESTED. Stock signals are rejected while P11-P14 gates are unsatisfied.

HTTP remains read-only by default. Explicit `ALPHALENS_ALERT_MUTATIONS=true`
permits only lifecycle/preferences writes. Those require loopback access, allowed
Origin, JSON and a custom local intent header; P17 CORS remains GET-only, so the
dashboard uses its existing same-origin proxy. No alert injection route or public
webhook exists. Local CLI always supports lifecycle/preferences operations.

React extends existing theme/components with bell, notification drawer/center,
severity/category/state/search filters, evidence details, working lifecycle controls,
preferences/quiet hours, and recent alerts on Overview/Data Health. No fabricated
runtime entries, outbound delivery or automatic schedule is enabled.

P19 remains blocked until separately verified source/calendar/identity/model
evidence passes. Current provider audit and exact verification results will be
recorded separately. Container security remains an independent strict blocker.
