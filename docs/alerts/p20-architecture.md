# P20 alert contracts and operational architecture

P20 consumes persisted research events independently of market-data processing.
The existing six P19 receipts are read and verified, including older completed
schemas; their checkpoints/products are never upgraded or rewritten. No ingestion,
training, scoring, valuation or paper execution is triggered by API/page loads.

## Event and storage contract

`p20.event.v1` contains stable ID/dedup identity, a closed event code, component,
category/severity (fixed templates), evidence reference and SHA256, event clock,
explicit time basis, related run/session/security, reasons, classification and mode.
Receipt/model/paper checksums use their existing canonical unsigned identity
semantics; detector references identify observed operational conditions, not accepted
market payloads. Capture time is never upgraded to exchange publication time.
Unreadable source classification is `UNVERIFIED_OPERATIONAL_EVIDENCE`; it is an
integrity diagnostic, never synthetic market history. TEST_ONLY imports are blocked
from normal application reads. No arbitrary title, message or event injection API exists.

Separate SQLite storage uses `db/alerts/schema.sql` (the sole schema owner), WAL,
FULL synchronization, a 10-second busy bound and `BEGIN IMMEDIATE` writes.
Immutable alert evidence/hash, unique `seen` tombstones, source cursor/fingerprint,
delivery outbox and append audit commit atomically. Concurrent publishers/restart
replays cannot duplicate an event. A failed transaction advances no cursor.
SQLite is operational notification storage; canonical PostgreSQL and frozen archives
are untouched. The DB root should be private, local and writable by its operator.
There is no P21 multi-user account or authentication claim.

Lifecycle: NEW → READ → ACKNOWLEDGED → RESOLVED, allowing direct forward jumps.
Same-state updates are idempotent; backward transitions fail. Audit entries preserve
the original evidence; detail reads return the latest 200 transitions and an explicit
truncation flag. Reading an alert does not change delivery success.

Delivery: PENDING / DELIVERED / FAILED / RETRY_PENDING / SUPPRESSED, with separate
external-channel NOT_REQUESTED. IN_APP means local notification visibility, not a
Windows toast or email. Unread counts include NEW, DELIVERED alerts only; history
retains all states and suppression reasons.

## Eligibility, deduplication and anti-spam

Receipt events include start/completion/warnings/failure, blocked source/inference/
policy, quality/missing observations, retry exhaustion and recovered publication.
Incomplete checkpoints explicitly say a worker might still be active. Corrupt evidence
creates a CRITICAL detector event and never exposes corrupt products. Public source
metadata checks are one-shot and bounded; changes/outages are separate from rights.

Receipt dedup keys use component/code/identity/classification, SHA256 encoded.
Recurring blocked-source/inference/policy conditions key on material provider/reason/
mode content, not retrieval clock or repeated status requests. Run completion is
per run. Source cursors include the producer mapping revision so additive alert rules
can replay without repeating existing events. Retention keeps dedup tombstones.

INFO delivery defaults off; category preferences govern future delivery. WARNING/INFO
cooldowns default 3600 seconds. ERROR/CRITICAL bypass cooldown and quiet hours;
an explicit excluded category still suppresses delivery, never evidence retention.
Quiet hours use Asia/Kolkata, support overnight ranges and defer low-severity
delivery with a 5-minute recheck; they consume no delivery attempt. Local publication
failures retry after 30, 60, … seconds, capped at 3600 seconds and 1–5 attempts
(default 3). Exhausted FAILED events are retained; `retry` processes due outbox
events only and never resets the attempt cap. No external transport is implemented.

Pruning is explicit: resolved INFO/WARNING older than 7–365 retention days (default
90) may be removed; ERROR/CRITICAL remain. At 10,000 retained alerts, 200,000
tombstones, 100,000 sources or 1,000,000 audit entries, publication stops visibly
without advancing the source cursor. Operators must archive operational storage
with its tombstones/cursors; upstream immutable receipts remain recoverable. No
retention operation touches research artifacts. Pagination/search are bounded.
Optional digest summaries are deferred; avoiding low-value success delivery is
already supported without another aggregation engine.

## Portfolio, paper and future stock support

Explicit local imports validate existing P16 hash-named checkpoints and P15
hash-named valuation snapshots. They report recorded states/fills and unresolved/
degraded valuation evidence, omitting account names, quantities, cash, prices and
raw reason text. No trades/valuations are created for notifications. TEST_ONLY
imports require a CLI flag and still cannot be served by the application API.

The freshness reader validates a hash-named, reviewed calendar/release document.
It requires contemporaneously known trading and release-window evidence, handles
explicit special sessions, and distinguishes non-trading days from pending releases.
Current real-provider clearance remains blocked; caller flags cannot enable it.

Frozen model inspection verifies the exact four existing candidates without loading
estimators. Missing artifacts, integrity failures and feature-order mismatches are
operational alerts. Current forecast availability remains disabled. STOCK_SIGNAL
is reserved in the category vocabulary but cannot be enabled in preferences or
published as a stock event. No BUY/SELL, watchlist breakout or positive-IC trigger exists.

## API, UI and security

GET `/api/v1/alerts`, `/unread-count`, `/{id}`, `/preferences` reuse P17 envelopes.
History filters: category, severity, lifecycle, delivery, search; limit 1–100 and
offset 0–10,000. All responses verify stored evidence and classification.

POST `/{id}/state` and `/preferences` update notification projections only. Default
`ALPHALENS_ALERT_MUTATIONS=false` does not register any POST route; the default
OpenAPI remains GET-only. Explicit opt-in additionally
requires the existing loopback peer/Host/Origin controls, exactly one approved Origin,
`X-AlphaLens-Local: p20`, JSON content type, an 8192-byte streamed body bound and
closed state/preference validation. P17 financial/research routes remain GET-only;
CORS remains GET-only, with no credentials. Writes use the same-origin local Vite
proxy. There is no public webhook, remote write server, outbound sender or event API.
The custom header is a request-context guard, not authentication. Other local users
are outside this single-owner pre-P21 security boundary.

The existing themed shell adds a bell/unread counter, recent-alert drawer, notification
history, filters/search/pagination, evidence/audit details and related workspace links.
Overview/Data Health show meaningful delivered alerts. Settings exposes category,
INFO, quiet-hour, cooldown, retry and retention preferences. Disabled local mutations
have disabled controls and CLI guidance. Error states never use fixture fallback.
Native dialogs preserve keyboard focus/Escape; motion respects the existing reduced
motion policy. Email remains unavailable without authorized SMTP; desktop remains
unavailable because no opt-in native delivery was configured or tested. Neither is
advertised as delivered. Optional desktop work would require platform app identity
and a tested native delivery integration; no extra dependency was added for it.

Microsoft's [notification overview](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/)
and [Windows App SDK delivery guide](https://learn.microsoft.com/windows/apps/develop/notifications/app-notifications/app-notifications-dotnet)
describe native registration/runtime requirements. A compatible packaged or
unpackaged integration and actual opt-in delivery were not established here.
Desktop delivery therefore remains unavailable rather than reporting a success.

Machine-readable contracts are [event schema](p20-event-schema.json),
[preferences schema](p20-preferences-schema.json) and
[OpenAPI](p20-openapi.json). The OpenAPI artifact includes the explicitly opt-in
notification projection routes; it was generated in-process without starting a
write server. The frozen P17 OpenAPI and generated financial client are unchanged.
