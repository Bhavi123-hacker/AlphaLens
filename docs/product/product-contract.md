# P0 product contract

Current development amendment D49-D50 authorizes sequential P6 features and P7
labels from approved P5 649340a. P6 gate/commit must precede P7; stop before P8.
Completed-session information is evaluated after its actual availability;
hypothetical entry starts no earlier than the next verified session open. Features
never consume supervised outcomes. Production data remains NOT_CLEARED, clearance
OPEN, and PIT fundamentals UNAVAILABLE. See [P6 formulas](../ml/p6-feature-engineering.md).
P6 and P7 now pass DEVELOPMENT sequentially; P6 was committed before P7.
[P7 convention and maturation](../ml/p7-label-generation.md) does not authorize
P8 or any model/performance claim. Production clearance remains independent.

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
Use the maximum verified, legally usable free historical depth available per
dataset and disclose actual coverage, gaps and versions. V1 has no unconditional
10–15-year requirement. Roughly five years is acceptable if actually established;
the measured research-fixture coverage is documented in the P1 validation report.
Longer histories remain architecturally possible. These are subsequent user
amendments D26-D39, not original DOCX text.

Prefer a dynamic universe from official daily historical records and contemporaneous
security classification/identifiers, using only evidence available by the decision
time. Historical NIFTY 500 is OPTIONAL for V1. Current constituents never reconstruct
past membership. A traded-security observation is not proof of next-session
tradability or complete listed coverage. Rights, departed coverage and timestamp
evidence remain gates; see the [proposed method](../data/free-data-strategy.md).

## Zero-paid-dependency contract

The required product path runs locally on free/open-source software and compatible
free data. No required paid subscriptions, constituent feeds, APIs, cloud, databases,
auth, model APIs, monitoring or expiring trials. Past paid-provider research is
preserved; no recommendation was approved for implementation. Free public access
does not establish retention, automation, ML, backtesting or display permission.

Local PostgreSQL and a free container runtime are sufficient deployment targets in
principle; cloud deployment is optional. Prefer upstream Docker Engine/Compose on
a compatible local host; do not require a paid Docker Desktop entitlement. Later
auth/monitoring must have a free self-hostable path without weakening security.
Actual Docker/PostgreSQL verification is reported separately from this policy.

## Educational research clearance versus production clearance

Under user-approved D36-D39, an explicit open dataset licence plus repository
uploader-clearance representations and no specific contrary evidence can support
local research, feature/ML experiments and backtesting development. Preserve full
provenance/attribution and residual upstream-rights risk. This is
ACCEPTED_WITH_RESIDUAL_RISK, never a zero-risk claim or production clearance.
AlphaLens does not publicly redistribute raw or normalized third-party records in
this milestone. PRODUCTION_DATA_CLEARANCE remains OPEN.

The selected cohort is a RESEARCH_FIXTURE_DATASET, not a HISTORICAL_MARKET_UNIVERSE_DATASET.
It proves bounded file normalization and replay. It does not solve survivorship
bias, PIT availability, adjustment/revision history or exchange-wide coverage.
P1 DEVELOPMENT may pass under its own gate; later phases still require explicit approval.

## Eventual MVP and exclusions

Eventual MVP: authenticated broad-universe research, trustworthy historical data,
technical features, evaluated baseline predictions, ranking,
risk-aware explainable signals, manual portfolios and transaction history, P&L,
backtesting with honest assumptions, watchlists and basic in-app alerts.
These are future deliverables, not this foundation's implemented functionality.

Fundamentals and historical sector context are optional and require their own PIT
evidence. Currently `FUNDAMENTAL_PIT_DATA = UNAVAILABLE`. Future interfaces remain
extensible, but no fundamental analysis or neutral replacement is forced into V1.
Price/volume-based ML remains conditional on lawful data, action/identity quality,
temporal eligibility and demonstrated out-of-sample evidence. No model has been built.

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
Chronological splits, walk-forward validation, leakage checks, benchmark comparison,
risk adjustment and out-of-sample reporting remain requirements even with fewer
feature families. Costs/slippage must be explicitly justified and versioned later.
Security starts now: minimal local health surface, safe errors/logs, no secrets in
Git, user ownership and operator separation in the architecture. Full authentication,
authorization and production operations are later phase work, not claimed complete.

## Canonical missing-data behaviour

Status applies per data family and declared purpose/as-of scope, not just globally.
These are product rules to implement in later approved phases, not new runtime enums.

| Status | Meaning | Required behaviour |
| --- | --- | --- |
| AVAILABLE | Rights, quality, coverage, freshness and temporal eligibility meet the declared scope. | Display real provenance/as-of metadata; the model names the families actually used. |
| DEGRADED | A disclosed subset is usable; some optional coverage/families are absent. | Explain the limitation. Run only a model explicitly trained/validated for the available family set; do not silently change its inputs. |
| STALE | Previously usable evidence is older than its versioned freshness policy permits. | Show age and last-known scope if retention/display rights permit; block dependent fresh actionable output. No freshness threshold is invented now. |
| UNAVAILABLE | No permitted source, required data, verified PIT eligibility or usable coverage. | Return absent/not-computed plus a reason; no synthetic, neutral, zero or fabricated input/output. Unknown historical availability is unavailable for PIT, not merely stale. |

An unavailable required family blocks its dependent model or signal. Missing optional
fundamentals may degrade overall product coverage while a validated price-only model
remains available for its expressly declared scope. Stale/partial inputs never hide
behind an aggregate AVAILABLE badge. UI explanations must say which family, why,
actual coverage/as-of and affected outputs; no UI is implemented in this task.
