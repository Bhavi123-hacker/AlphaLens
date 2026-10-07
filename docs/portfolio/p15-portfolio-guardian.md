# P15 Portfolio Guardian

P15 is an offline accounting and monitoring domain, not a historical backtester,
broker connection or trade executor. P5 owns canonical market evidence; P10 retains
historical evaluation; P13/P14 own decision states and explanations. P15's separate
`alphalens-portfolio` workspace package reuses their contracts without changing them.

## Identity and ledger

`Portfolio` pins ID, name, INR, creation clock, classification and serialized
`p15.accounting.v1` policy. USER_RECORDED and PAPER accounts cannot mix execution
types. User declarations never imply broker or exchange verification. TEST_ONLY
manual accounts exist for engineering demonstrations; a real USER_RECORDED account
cannot use either TEST_ONLY or RESEARCH_FIXTURE marks as real valuations.

BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAWAL and OPENING_POSITION preserve stable event
identity, security ID, declared symbol, effective session/time, recording time,
quantity, price, fees, currency, source, provenance, reference and notes. Recording
must follow effectiveness. Historical reads require both clocks at/before cutoff
and session at/before requested session. Events are reconstructed by effective
clock, recording clock and stable transaction ID. Identical IDs are idempotent;
different payloads conflict. Backdated additions must leave all known prefixes valid.

## Exact accounting

FIFO consumes earliest open lots. All quantities and financial values are exact
rationals, serialized as integer/fraction text (P10's exact arithmetic convention).
Floating inputs are rejected. Display conversion never changes stored arithmetic.
BUY debits quantity times price plus fees; buy fees enter lot cost basis. SELL
credits quantity times price minus sell fees; realized P&L is net proceeds less
FIFO allocated basis. Partial lots allocate basis proportionately without rounding.
Shorts, oversells, overdraft and negative quantities/costs are rejected.

An OPENING_POSITION requires user-declared quantity, inclusive total cost basis and
effective date; it consumes no cash and is an external capital contribution at its
declared basis. No missing past trade/lot or pre-entry price history is invented.

For each position:

- Remaining cost basis = sum of remaining FIFO lot bases.
- Display average cost = remaining basis / open quantity, unavailable after exit.
- Market value = open quantity times evidenced EOD close.
- Unrealized P&L = market value minus remaining cost basis.
- Total P&L = realized P&L plus unrealized P&L.
- Return percentage = 100 times total P&L / gross lifetime acquisition basis.

The return denominator includes every bought/imported lot and capitalized fee; it
is a cost-based measure, **not** a money-weighted or time-weighted investment return.
Portfolio aggregates use the same definitions, with equity = cash + position market
value. Cash deposits/withdrawals change net external capital, not profit. Closed
positions remain in accounting history with zero open basis and retained realized P&L.

Session P&L requires a compatible strictly prior snapshot and complete EOD marks:
current equity minus prior equity minus the change in net external capital. A first
observation or incomplete/stale mark has unavailable session P&L. Per-security
session P&L is change in total position P&L with complete marks. "Session" does not
claim an intraday/day-clock observation. Skipped sessions are never interpolated.

## Market evidence and lifecycle

Valuation accepts only P5 VALID, AVAILABLE, INR, RAW_UNADJUSTED closes known at
cutoff, on/after the first holding session. The latest such observation is
EOD_COMPLETE if it matches the requested session, otherwise STALE with its actual
older date. Rejected/unknown-basis prices cannot become marks. A missing price is
UNAVAILABLE. Stale observed values may be retained explicitly; they are never live
or current-session prices. If any open position is unpriced/unresolved, aggregate
market value, equity and unrealized/total P&L are unavailable; cash/basis/realized
accounting remain available. An entirely empty canonical read has a separately
versioned empty-read identity, never an invented P5 bar/dataset.

Known effective economic actions overlapping the holding period and known
delistings produce UNRESOLVED marks; quantity and basis remain as recorded. V1 has
no automatic split/bonus/merger/dividend accounting: authoritative application
semantics are not yet established. No action records is not proof of complete
action coverage. Security IDs survive symbol changes; PIT display symbols use P5.
Unknown terminal economic value is neither zero nor removal of the holding.

## Chart and evidence contracts

`History` contains immutable session valuations, per-security P&L and portfolio
series. Explicit chronological (session, cutoff) observations preserve their own
knowledge vintages; no pre-entry security history or missing-session interpolation.
`price_history` returns the existing P5 OHLCV/basis/quality/provenance views.
`DecisionHistory` optionally supplies actual P11/P12/P13/P14 snapshots and P9/P8
prediction evidence. Current references and `monitoring_history` expose their
cutoff-filtered series; missing risk/rank/signal is explicit, never synthesized.
P14 annotations retain session, horizon, signal ID and explanation ID, with no
fabricated chart prices. Portfolio risk is transparent count/value by security-risk
level and largest marked-position concentration, **not** VaR or diversification risk.

Benchmark comparison is UNAVAILABLE by default. Explicit P10 benchmark evidence
must match canonical input/classification and rights reference. Observed valid
same-session benchmark marks align to complete portfolio observations, normalize
to 100 at their common start and report observed-price returns/relative returns.
Portfolio normalization removes net external flows under a session-end flow
assumption; it is not dividend total return or intraday flow-adjusted performance.
Constructed benchmarks may only be called TEST_ONLY_BENCHMARK, never NIFTY 50.

## Persistence, identity and commands

PostgreSQL migration `003_p15_portfolio.sql` owns account/transaction metadata.
JSON financial values remain exact fraction text; SHA256 identities and relational
timestamps support immutable replay. UPDATE/DELETE triggers reject mutation.
Account row locks serialize application appends and accounting validation; callers
own outer commit boundaries. Derived chart series are reproduced, not redundantly
persisted. Trusted local JSON ledgers use checksum filenames and immutable publish.
This local developer contract has no authentication/API or multi-user release claim.

Snapshot identity pins visible ledger content, cutoff/session, P5 dataset/input,
accounting/corporate-action policy, referenced decision IDs and both execution and
market classifications. Later unseen transactions do not change the visible ledger
identity. A newly supplied canonical input has a new audit identity; future-only
facts cannot alter earlier economic values or overwrite an old immutable snapshot.

`alphalens-portfolio create --input portfolio.json --output data/portfolios`
creates a local immutable ledger. `add-transaction` / `import-position` accept
`--input transaction.json --ledger <checksum.json> --output data/portfolios`.
`positions` accepts ledger `--input`, `--session`, `--cutoff`; `value` also requires
verified `--canonical canonical-input.json`. `history` takes explicit
`--observations` JSON session/cutoff pairs and the canonical input. Output exposes
cash, basis, market/equity value, realized/unrealized/total/session P&L and freshness.

**TEST_ONLY — NOT A REAL MARKET VALUATION.** All fixture evidence also remains
**TEST_ONLY — NOT A PERFORMANCE CLAIM.** RESEARCH_FIXTURE is not production
validated. Fundamentals remain UNAVAILABLE. No paid dependency, broker credential,
optimization, automated rebalance, watchlist position, chart renderer or API is added.
Production clearance stays OPEN; production market-data use stays NOT_CLEARED.
