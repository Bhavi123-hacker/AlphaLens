# P16 forward paper trading

P16 processes one newly observed EOD session at a time. It is an offline forward
simulation protocol, not another P10 historical backtester. Orders lock before
their future observations; new observations can fill/mark/exit but cannot change
the old decision. Synthetic sequential-clock fixture replay tests the protocol;
it does not establish an actual forward market track record. No broker client,
login, token, real order endpoint, real trade or paid service exists.

## Account and policy

P16 creates an explicitly PAPER P15 portfolio and one declared starting-cash
deposit. PAPER and TEST_ONLY_PAPER are simulated execution classifications; their
underlying RESEARCH_FIXTURE / TEST_ONLY market classifications remain separate.
Real production market data is still not cleared. V1 does not recapitalize,
withdraw cash, import real holdings, short, pyramid, optimize or use leverage.

`p16.paper_policy.v1` serializes revision, DEVELOPMENT_ASSUMPTION status, controlling
1/5/10/20-session horizon, order type, sizing, rank/risk limits, position count,
exit/review behavior and full P10 cost scenario. Defaults: signal orders disabled,
5-session control, fixed 1000 INR per new position, maximum three positions,
entry rank at most five, maximum entry risk MEDIUM, configured EXIT_SIGNAL exits,
no TAKE_PROFIT_REVIEW automatic exit, whole-share floor sizing and zero-cost
diagnostic scenario. These are engineered assumptions, never fixture-calibrated
Indian investment/broker rules. Change serialized policy revision/configuration
for new decisions; an old order keeps its own policy, costs and model lineage.

MANUAL_PAPER_ORDER requires a stable request ID, security/symbol, side, reason,
positive buy cash reservation and optional exact whole quantity; SELL requires
positive owned quantity. SIGNAL_POLICY_PAPER_ORDER requires explicitly enabled
policy, immutable P13 signal and matching P14 explanation. Latest available signal
per security in the configured horizon controls; ambiguous simultaneous snapshots
are rejected. Eligible entries are ordered by rank then security ID. Other horizons
cannot replace the controlling horizon with a more favorable daily selection.
Absent/future signals never become actions.

## Intent, fill and lifecycle

MARKET_ON_NEXT_OPEN is the only supported order type. At intent time an explicit
P10 calendar must evidence the next trading session and its open convention.
Missing calendar dates, unknown sessions/clocks or an already-passed open block
creation; future calendar publication cannot justify an old schedule. Decision
cutoff precedes the target open and follows completed t information. This is a
conservative EOD convention, not an intraday execution engine.

Pending buys reserve their maximum inclusive cash budget. Later orders cannot
spend reserved cash; holdings and pending entries consume position slots. Existing
holdings/pending orders block another entry by default. Fixed-cash and equal-weight
available-capital/free-slot sizing are explicit choices. At a future evidenced
open, automatic quantity is floor(budget / (slipped price times (1 + fee rate))).
Manual whole quantity must fit its original reservation or produces NO_FILL.

A fill is created only once the target session is evidenced complete and a VALID,
AVAILABLE, INR, RAW_UNADJUSTED P5 bar is known at processing cutoff. It uses that
bar's actual observed open; P4 eligibility must be known by the simulated open.
Its recorded availability is distinguished from its hypothetical open clock.
Missing/rejected/unknown-basis open means NO_FILL: no prior close, later close or
guessed midpoint substitution. Economic actions during the entry boundary or
unresolved actions affecting a held exit also block the fill. Execution symbols
use identity known at the simulated open; security ID and original intent persist.

Buy simulated price = observed open times (1 + slippage rate); sell price uses
(1 - slippage rate). Fees = quantity times simulated price times the declared
P10 fee rate. ZERO_COST_DIAGNOSTIC, LOW_COST_ASSUMPTION and HIGHER_COST_STRESS are
assumptions, not verified Indian brokerage/tax schedules. Exact rational monetary
values enter P15 BUY/SELL events; P15 exclusively computes cash, lots and P&L.

Orders retain PENDING, FILLED, CANCELLED, EXPIRED or NO_FILL events. REJECTED is
supported by the event contract; policy/request refusals are report skips rather
than fabricated executable orders. A skipped target processing session expires
the order; it cannot choose a later favorable open. Cancellation releases cash
with its own clock. A stream containing future cancellation cannot be used as an
earlier stream prefix. Terminal events cannot be overwritten or double-filled.

P13 ENTRY_SIGNAL remains separate from the intent and simulated fill. Only the
fill creates a P15 holding. P16's `position_context` supplies fill-evidenced,
explicitly synthetic TEST_ONLY PositionEvidence to the existing P13 contract;
P13/P14 were not redesigned or given fabricated ownership. HOLD/REVIEW/EXIT can
then be evaluated with that context. EXIT_SIGNAL may create a next-open exit
intent under enabled policy. Entry risk limits do not suppress a risk-triggered
exit. TAKE_PROFIT_REVIEW remains a manual review unless its auto-exit switch is
explicitly enabled. EXITED becomes available only after a complete evidenced
simulated exit. Research position context stays unavailable under P13's current
development boundary; no research/production signal promotion is implied.

## Daily cycle and idempotency

1. Observe a completed canonical session at an explicit knowledge cutoff.
2. Resolve prior pending intents using their pinned future open/policy.
3. Append exact simulated executions through P15.
4. Consume currently available P13/P14 evidence in the configured horizon.
5. Apply explicit paper policy/manual intents, reservations and skip rules.
6. Produce an immutable P15 valuation and deterministic paper daily report.
7. Persist account, unique intents/events/fills/report atomically.

The same processed session returns its locked state, even if later inputs or
policy versions are supplied. Unprocessed sessions/cutoffs must advance strictly;
no new retroactive intent or historical performance-based entry selection. Stable
order, event, fill, transaction, valuation and report hashes prevent double fills,
fees and positions. An immutable order embeds its policy, signal and explanation;
these preserve ranking, risk, prediction/model, feature/P4/P3/P2 lineage. Manual
orders explicitly have unavailable signal/explanation provenance, not invented
machine evidence. Fill lineage records the actual canonical revision, quality
key, raw links, source availability, simulated symbol and cost scenario.

Daily reports include session/cutoff and full policy; starting/ending/available/
reserved cash; P15 equity/P&L/positions/freshness; created orders, fills, exits,
signals considered and ordered skip reasons. Reasons include MAX_POSITIONS,
INSUFFICIENT_CASH, ALREADY_HELD, ALREADY_PENDING, RISK_POLICY_BLOCKED, STALE_DATA,
UNAVAILABLE_PRICE, CLASSIFICATION_BLOCKED, EXPLANATION_UNAVAILABLE,
PAPER_POLICY_DISABLED and explicit calendar/context failures.

## Persistence, performance and chart contracts

Migration 004 extends the existing portfolio schema. PostgreSQL stores unique
account configuration and typed immutable intent/event/fill/report records, with
P15 transactions in their existing table. One account row lock protects atomic
stream-prefix validation and updates. Concurrent/stale forks must reload the
current prefix. Restart reads those events and P15 ledger into the same state;
UPDATE/DELETE triggers prevent mutation. Daily reports retain observed P15
vintages for audit; derived chart series are not separate database copies.
Checksum-named local checkpoints support explicit developer replay and recovery.

Performance exposes initial capital, cash/available/reserved cash, evidenced
equity/market value, P15 realized/unrealized/total/session P&L, simple profit over
initial-capital return, fees/slippage and actual simulated fill count. A win/loss
requires a completely closed position cycle and uses changes in P15's recorded
realized P&L; open or partial exits cannot become wins. Drawdown requires at least
two complete observations; gaps/stale marks stay null. No tiny-history
annualization, Sharpe claim or market-accuracy claim is made.

Chart-ready equity, P&L, drawdown, per-security P&L, simulated trade markers and P14
signal markers carry actual immutable references. No rendering or fabricated
price points. Benchmark comparison is UNAVAILABLE by default; `compare_benchmark`
reuses P15's rights/classification-checked common-start normalization when genuine
permitted evidence exists. Constructed benchmarks never receive NIFTY names.

`alphalens-paper create --input definition.json --output data/paper` accepts
`{ "portfolio": <P15 PAPER definition>, "starting_cash": "10000" }`.
`process-session --input <checksum.json> --canonical canonical-input.json
--calendar calendar.json --session YYYY-MM-DD --cutoff <aware ISO instant>
--output data/paper` optionally accepts `--manual-orders`, `--policy`,
`--decision-history` JSON. `--postgres` persists atomically using configured
ALPHALENS_DATABASE_URL, never an argument or logged connection string.
`orders`, `positions`, `performance`, `history` read `--input <checksum.json>`.

**TEST_ONLY PAPER SIMULATION — NOT REAL MARKET PERFORMANCE.**
All fixture evidence also remains **TEST_ONLY — NOT A PERFORMANCE CLAIM**.
Fundamentals remain UNAVAILABLE; genuine NSE calibration has not been established.
Production clearance OPEN/use NOT_CLEARED. P17/API, frontend and live pipeline
remain outside this phase; paper money and fills never become real executions.
