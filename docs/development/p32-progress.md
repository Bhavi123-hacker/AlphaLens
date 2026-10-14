# P32 personalized research and portfolio execution

Current user mission extends P31 rather than replacing its delivered price fix.
Verified clean branch245fb4b, original C worktree5314909 retained, P31 Linux CI
still running. Dedicated branch p32-personal-research-portfolio created locally.
P31 compiled app is running on8017; isolated test operator8029 is separate.

Implement genuine single-operator preferences, manual FIFO-ledger portfolio,
descriptive risk/what-if/watchlist/alerts/journal and historical discovery. Universal
master search and provider-first charts remain shared foundations. No current ML
rankings without original independent gates. Provider observations remain transient;
user-entered acquisition prices are distinct from provider data. No automatic
acquisition/outbound notifications or public publication.

## Checkpoint1 — universal provider and owned manual records

Current official master:2701verified NSE_EQ/EQ identities, no hardcoded stock set.
Actual six-symbol compiled browser check passed: RELIANCE,BAJFINANCE,TCS,INFY,
HDFCBANK,ICICIBANK. Twelve bounded provider GETs in that check; subsequent selected
watchlist reused its transient cache without GETs. BAJFINANCE latest14October;
quote clock rejections remain enforced. Source dates/identities/clock-only receipt
is in ignored first-results; no provider price/body retention.

Indexed/paginated master search,50-identity quote planner (official maximum500),
SMA100/volatility/custom-date chart controls, single-operator preferences,
manual P15 FIFO sidecar, risk/what-if, journal/rules/copilot/opportunity screens
implemented. No source blend, original financial-module change or inferred cash.
New SQLite schema is owned by db/; original PostgreSQL schemas remain unchanged.

Eighteen new targeted backend cases passed4.96s; original P31 terminal regression
also passed with manual financial cases. Windows repeated timestamps exposed a
FIFO tie-order issue; sequence event IDs fixed it without changing P15 or clock
rules. Unknown fees/cash and acquisition execution clocks remain explicit.

First real five-case browser run:1passed/4failed because native shell route
allowlist omitted the new page URLs. Added exact routes and personal storage
overlap protection. Second four-case run: manual multi-lot/partial-sale/scenario
passed; preference success message vanished on form remount, causing watchlist
dependent case to stop; journal persisted/layout checks passed but WCAG caught
low-contrast opacity during page-entry animation. Fixed remount and kept entry
animation transform-only. These failures are not reported as passes.

Full archive discovery has explicit progressive checksum-verified reads, bounded
per-request deadlines, ownership and cancellation. No provider calls/background
work/model evaluation. Actual all-cohort read verification follows.

P31 Linux/PostgreSQL CI960passed/8skipped in289.95s. Full-history TruffleHog failed
on three inherited unverified URI/Postgres findings; later container stages did
not run. Frontend CI passed. No scanner suppression/history rewrite/waiver.
