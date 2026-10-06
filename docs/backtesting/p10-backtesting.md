# P10 deterministic hypothetical backtesting

Version `p10.backtest.v1`, authorized by D55–D58 only after P9 passed and was
committed as `4e29b49eea97bf1b439db2886aa4d2dc62ee5ec4`. This is an experimental
economic replay, not the P11 risk engine, P12 ranking product, P13 signals, P14
explanations or a portfolio product. It never fits models or executes orders.

**TEST_ONLY — NOT A PERFORMANCE CLAIM.** Research results must separately state
**RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED**. Production data/models remain
uncleared. The authored schedule and benchmark are not historical NSE evidence.

## Input boundary and identity

`alphalens_backtesting` accepts only checksum/schema/identity-verified P9
`OOSDataset` records with role `FOLD_TEST`, pinned to permitted fold/model
identities and their exact cutoff-specific P7 training datasets. In-sample or
tuning output cannot enter the supported input contract. Checksums provide
integrity, not authenticity: inputs remain trusted local research artifacts.

P5 execution facts and P6 rows provide prices and the evidence chain. They never
generate or rescore predictions. Future label availability, realized targets and
P9 scoring exclusions never determine selection; predictions with unknown future
outcomes remain eligible for replay. Missing recoveries therefore cannot silently
remove a historical holding. No current-constituent substitution exists.

`BacktestDefinition` pins P9 evaluation/OOS IDs, canonical input, feature set,
historical universe, execution calendar, model family/horizon, date interval,
fixed selection, sizing/capacity/capital, execution/rebalance/missing-price/action
rules, exact cost assumptions, benchmark evidence, classification, code version
and seed. Optional comparison-context identity pins a predefined arena's scope.
SHA256 over the definition, environment and arithmetic contract produces the
backtest ID. Changes to meaningful inputs or configuration change identity.

## Calendar and execution

Completed session t information produces a decision at its evidenced availability.
Earliest entry is the next verified trading session's open, with the conservative
P7 requirement that the decision precede the entry's local calendar date. Entry
never uses t close. Exit is the h-th verified trading session's close counting
entry as session one, matching P7 horizons 1/5/10/20.

P5 has no separate opening-clock field. A versioned `ExecutionCalendar` supplements
it with per-date trading/non-trading/unknown status, schedule availability,
evidence reference and optional explicit opening convention. The complete path to
entry and planned exit must have been knowable at the decision. Unknown dates or
late schedule evidence prevent a fill. Unknown clocks remain null; the prior-date
bound is retained. The TEST_ONLY calendar explicitly authors daily sessions and
04:00 UTC opens; it makes no claim about actual NSE dates or opening times.

Observed open/close prices use the P5 revision and P3 quality visible by that
session's local date end; later corrections cannot rewrite an earlier fill or
mark. Open prices are observed ex post for execution accounting, never inspected
to allocate capital or select securities. This EOD vintage convention is explicit
and is not a claim that a consolidated EOD bar was published at the opening time.
P5 confirms the session and historical membership is checked at the opening
boundary. VALID/DEGRADED raw observations retain their quality; rejected, missing,
unknown-basis or unavailable observations never fill. No automatic close fallback.
The replay period requires complete known calendar dates; unknown schedule facts
cannot silently remove historical sessions. Unknown valuation history also makes
later drawdown points unavailable even if NAV marking subsequently resumes.
A holding whose expected trading session is not confirmed stays unresolved; a
later quote cannot produce an exit with a silently shortened session horizon.

## Fixed experimental policies and money

Supported policies: TOP_K, TOP_PERCENTILE (ceil of available cohort size), and
PREDICTION_THRESHOLD. Probability is the classification score, including zero;
regression uses its predicted return. Stable security-ID ties are deterministic.
There is no outer-test policy search. Default experiment: TOP_K=2, maximum three
positions, new OOS decisions use free slots, and existing holdings stay until their
horizon exit. A missing selected fill never selects a replacement using future
open evidence.

EQUAL_WEIGHT means available unreserved cash divided by free capacity slots;
selected slots receive identical budgets fixed at decision time. Unused slots
remain cash. Pending allocations reserve cash and capacity; overlapping horizons
cannot introduce leverage, overspending or duplicate holdings. Configurable INR
capital defaults to 100000; normalized starting wealth is 1.0. Fractional quantities
are explicitly hypothetical, not exchange orders or a realistic lot-size model.

Cash, quantities, fees, allocations and P&L use exact rational arithmetic. Decimal
display uses explicit precision 76 / HALF_EVEN, with rational quantities,
allocations, trade P&L and equity retained for exact reconstruction. Estimation of
statistics alone converts state to float64. Each marked session enforces
NAV − initial capital = realized P&L + unrealized P&L, nonnegative cash and the
maximum-position constraint. No large serialized objects enter PostgreSQL.

## Assumed costs and slippage

These are versioned scenarios, **not verified broker charges or Indian taxes**.
All basis points apply per executed side, with explicit brokerage/exchange/fees
components. Slippage worsens entry open and exit close deterministically.

| Scenario | Brokerage | Exchange | Taxes/fees | Slippage |
| --- | ---: | ---: | ---: | ---: |
| ZERO_COST_DIAGNOSTIC | 0 | 0 | 0 | 0 |
| LOW_COST_ASSUMPTION | 2 | 1 | 2 | 2 |
| HIGHER_COST_STRESS | 10 | 5 | 10 | 10 |

All values are bps. Entry quantity includes fees in its reserved budget; exit
credits proceeds less fees. No fill means no costs. These assumptions use no
future volume/market-impact statistics. Fixed scenario sensitivity flags an
available positive zero-cost outcome that vanishes under the assumed costs.
Unknown economic outcomes yield an unavailable sensitivity result.

## Missing outcomes, actions and benchmark

The initial supported basis is RAW_UNADJUSTED. Corporate-action completeness is
NOT_ESTABLISHED. Known economic actions affecting a holding make it unresolved;
no invented split factor, dividend cash or terminal recovery is applied. Symbol
changes alone are not an economic action. Future action evidence cannot influence
earlier selection, fills or marks. This conservative policy explicitly limits
economic interpretation; adjustment-aware processing remains a future extension.

Missing/rejected planned exit retains inventory and reports an unresolved exit.
Later quotes do not silently establish terminal recovery or a different exit.
Unknown delisting recovery is neither zero nor a removed holding. Unknown marks
produce null NAV/P&L/drawdown; whole-period portfolio metrics are withheld if any
session is unresolved. Closed-trade diagnostics retain the unresolved count and
are explicitly a closed-only subset, not portfolio performance.

Benchmark evidence must pin canonical input, classification, rights reference
and return basis. Constructed benchmark name must be TEST_ONLY_BENCHMARK, never
NIFTY 50. The price-only cost-free benchmark enters at the first later evidenced
open and uses aligned closes; missing evidence remains unavailable. No real
permitted benchmark history has been demonstrated; price return is not TRI.

## Metrics and artifacts

Where defined: total gross/net return, normalized wealth, maximum drawdown,
closed-trade win/loss/flat rates, mean/median return, profit factor, historical
mean trade net P&L, entry-plus-exit notional turnover / mean NAV, trade count,
holding sessions, exposure, cash utilization and benchmark-relative return.
Exposure and cash utilization describe end-of-session inventory/marks. A
one-session position can have zero EOD exposure despite using capital intraday;
these are not intraday time-weighted risk measures.
Gross return adds fees/slippage back for the same executed quantities; it is not
a separately reinvested zero-cost portfolio. Zero-loss profit factor is undefined.

CAGR, sample annualized volatility, Sharpe, Sortino and Calmar require at least
252 observed sessions and 365 calendar days, valid positive equity and non-TEST
classification. The annual-session count and risk-free rate are explicit
assumptions. Undefined denominators stay null. TEST_ONLY always reports annual
metrics INSUFFICIENT_EVIDENCE. Origin-fold trade diagnostics describe closed P&L
and unresolved counts; overlapping holdings make these different from independent
fold portfolio returns. No automatic single-metric model champion exists.

Immutable outputs, stable schemas/order and SHA256 checksums:
backtest-manifest.json, definition.json, summary.json, equity-curve.parquet,
drawdown.parquet, trade-ledger.parquet, positions.parquet, session-pnl.parquet,
selection-decisions.json, cost-sensitivity.json and model-comparison.json.
The ledger pins each P9 prediction/model/fold, entry/exit evidence, quantities,
prices, costs, planned/actual exit and reasons, quality/action/classification state.
Audit chains reach P8 model configuration, P7 aligned data/labels, P6 feature set,
P5 canonical snapshots, P4 universe, P3 quality reports and P2 source artifacts.

The deterministic arena compares all six families for both tasks/four horizons
under three costs, plus equal-weight eligible OOS-cohort and seeded random controls.
The cohort baseline is not claimed to cover securities without P9 feature-eligible
predictions. Insufficient capacity prevents a whole-cohort allocation explicitly.
Comparisons retain P9 predictive/ranking diagnostics, economics, trade-origin fold
diagnostics and cost sensitivity. Fixture scores never declare a market winner.
Arena saves require both comparison reports and a pinned comparison context;
standalone CLI definitions use null comparison context and explicitly unavailable
comparison reports. This prevents substituting different report modes under the
same artifact identity.

## Developer use and boundaries

`alphalens-backtest run --oos EVALUATION_DIR --canonical CANONICAL_INPUT_JSON
--features FEATURES_JSON --calendar CALENDAR_JSON --definition DEFINITION_JSON
--output IGNORED_LOCAL_DIRECTORY` emits a UTF-8 JSON hypothetical summary with
its classification and cost-scenario assumptions.

`python -m scripts.verify_p10_test_only --inputs P8_FIXTURE_DIRECTORY
--evaluations P9_EVALUATIONS_DIRECTORY --output data/p10-backtests` runs the fixed
matrix twice, checks deterministic replay and verifies stored schemas/checksums.
No new market history is downloaded. See [real-data readiness](../development/real-data-readiness.md)
before interpreting any result as evidence for actual stock selection.

P1_PRODUCTION_DATA_CLEARANCE = OPEN. PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
P11 and all later product decision/UI phases require separate user approval.
