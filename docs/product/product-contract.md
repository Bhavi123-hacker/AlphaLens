# P0 product contract

Status: scope approved by the user; implemented as documentation, not product code.
Authority: source DOCX §§1–5, 9–12, 17, 21–23, 27 plus DECISIONS.md amendments.

## Product and users

AlphaLens provides explainable stock research, evaluated forecasts, risk-aware
signals, and portfolio monitoring. Primary user: retail investor. Secondary personas:
active trader, long-term investor, quant/analyst. V1's EOD cadence is explicit even
for users interested in shorter-term research. Evidence and uncertainty accompany
outputs; no profit guarantee or fixed accuracy promise.

## Market and cadence

NSE cash equities only; INR. Session/display timezone Asia/Kolkata; persisted
instants are timezone aware and normalized to UTC. Exchange session calendars
require a real verified source; weekdays are not a sufficient trading calendar.
10–15 years is a conditional coverage goal, not currently acquired history.

Prefer historical NIFTY 500. Membership history, departed-security data and rights
must be verified. Current constituents cannot reconstruct historical membership.
If unavailable, report and propose a smaller reconstructible universe; approval
is required before changing scope. No unsupported universe promise is published.

## Eventual MVP and exclusions

Eventual MVP: authenticated broad-universe research, trustworthy historical data,
technical/basic fundamental features, evaluated baseline predictions, ranking,
risk-aware explainable signals, manual portfolios and transaction history, P&L,
backtesting with honest assumptions, watchlists and basic in-app alerts.
These are future deliverables, not this foundation's implemented functionality.

Excluded from first release: news sentiment, user-facing paper trading,
Telegram/email notifications, advanced regimes, natural-language/LLM assistant,
portfolio optimization, broker integration, and real-money execution. Real-money
execution and broker credentials are permanently excluded from AlphaLens.
Browser push can be considered in a later authorized notification phase.
Optional §26 enhancements are not implicitly committed deliverables.

## Canonical signal vocabulary and context

WATCH, SETUP_FORMING, ENTRY_SIGNAL, HOLD, TAKE_PROFIT_REVIEW, EXIT_SIGNAL, EXITED.
BUY/SELL are transaction sides, not stored signal states. ENTRY/SETUP/EXIT REVIEW
examples in source are noncanonical. Every future actionable signal requires a
valid prediction, independently assessed risk, explanation, invalidation criteria,
time horizon, data/model/rule versions, and validity/freshness metadata.
No transition occurs without a deterministic logged reason.

HOLD/EXITED need position context; research output never implies a transaction.
Transition ownership and allowed transitions remain design work before P13.

## Preferred research timing

Completed session t information -> prediction after required information is
available -> earliest hypothetical execution at session t+1 open.
If inputs/processing become available after that open, no simulated fill at that
past open is valid. No thresholds, fees, slippage, cost model or exact 1D/5D/20D
labels have been invented. P7 must version and justify them before training.

## Portfolio and simulation boundary

Users will record manual positions/transactions, without bank/UPI/payment or broker
credentials. Ledger entries are authoritative; holdings/P&L are derived. Opening
positions require auditable entries. Cost-basis, corrections, dividends and
corporate-action accounting must be designed before P15.
Backtesting simulates decisions, not real execution. Paper trading is V2 and must
share signal logic with backtesting. This milestone implements neither.

## Honesty and security

No invented prices, forecasts, metric values or analog outcomes. No hidden stale
data. Optional unavailable evidence has explicit unavailable/not-applicable reasons.
Model probability, ranking strength, risk and uncertainty are distinct quantities.
Security starts now: minimal local health surface, safe errors/logs, no secrets in
Git, user ownership and operator separation in the architecture. Full authentication,
authorization and production operations are later phase work, not claimed complete.
