# Economic accounting — 24 October 2026

Status: **PARTIAL** implementation, **BLOCKED_EXTERNAL_EVIDENCE** for complete
historical economic returns. The 504 original backtests are preserved. No
corrected backtest, new final-holdout simulation, or fabricated terminal value
was produced.

The existing machine-readable audit,
`docs/backtesting/real-research-economic-audit.json`, records
`CONSISTENT_WITH_FROZEN_ENGINE`, baseline
`8507f7fd5457fe5e53e016c2cd7b8f14e6b6e430`, and inventory identity
`608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`.
This campaign parsed that saved evidence rather than repeating the 504
simulations. Its cause partition remains:

| Mutually exclusive group | Original runs | Required work |
| --- | ---: | --- |
| Action uncertainty alone | 258 | Verified entitlement, effective quantity and cash-flow semantics |
| Action uncertainty plus price/identity gaps | 198 | Both action reconciliation and source/identity evidence |
| Price/identity gaps alone | 18 | Legally usable missing prices or dated terminal consideration |
| Raw-price full-path diagnostics | 30 | Still lack certified total-return/economic acceptance |

The 474 unresolved runs are not evidence of 474 software defects. The previous
auditor checked stored trade lifecycle, null equity sessions, source actions and
summary states with zero detected inconsistencies. That bounded conclusion does
not establish economically complete accounting. All unresolved runs retain a
permanently unresolved trade; later prices do not reconstruct unknown earlier
NAV. Original `ever_unknown` behavior remains conservative.

Across all 504 runs, saved terminal trade states are 93,399 CLOSED, 1,032
UNRESOLVED_RAW_ECONOMIC_ACTION, 231 UNRESOLVED_MISSING_EXIT and 87 OPEN.
These include repeated cost scenarios. A legitimate period-end OPEN position
does not authorize an invented exit. First causes and subsequent causes must
remain distinct when later action status overwrites an earlier missing exit.

| Evidence gap | Deduplicated audit finding | Treatment |
| --- | --- | --- |
| Corporate actions | 288 security/session/kind events: 266 dividends, 14 bonuses, 5 rights, 2 demergers, 1 split | No blanket adjustment or dividend cash credit |
| First blocking actions | 81 dividends, 2 bonuses, 2 rights | Source amounts/ratios exist; entitlement and cash timing remain unverified |
| Missing source observations | 67 of 71 missing-exit/mark events lack matching original prices | Preserve unknown, never zero recovery/interpolation |
| Alternative identity observations | 4 GLOBAL dates have another ISIN | Require dated continuity/conversion evidence |
| Missing Muhurat prices reached by OOS | 21 events on 2023-11-12 | Preserve the genuine calendar slot and missing price |
| Action identity matches | 34 nonempty price/action ISIN mismatches | Reconcile dated identities before applying action semantics |

Existing financial modules remain useful. `backtesting/src/alphalens_backtesting`
implements exact money/cost contracts, immutable outputs and conservative
research accounting. `portfolio/src/alphalens_portfolio` supplies manual FIFO
and hypothetical paper-ledger semantics. Neither one supplies missing historical
entitlement, payment dates, rights elections, demerger consideration, suspension
exits or delisting recovery. A generic action calculator without verified
inputs would not clear these frozen runs; no redundant replacement engine was
added under that claim.

A future versioned economic ledger should record, per exact identity and dated
position: settled/entitled quantities; ex/record/effective/payment dates; cash
receivable versus paid cash; split/bonus quantity and cost-basis conservation;
explicit rights election and subscription cash; dated demerger consideration;
known transaction costs; observed marks; and unresolved terminal claims.
NAV must equal cash plus known receivables plus known marked holdings, with
unknown constituents preventing a complete NAV claim. Entry on an ex-date
requires evidenced entitlement semantics rather than the frozen engine's
conservative action-before-exit rule. Unknown terminal recovery remains unknown.

No legally usable new dated evidence establishing those facts was supplied or
acquired. Source reconciliation is therefore the next dependency. Once obtained,
register the separate methodology before any corrected evaluation, preserve
all original files/results, test conservation and event-order edge cases with
TEST_ONLY fixtures, and seek approval before changing final-holdout rules.

Separate known-period economic research already exists in
`workers/nse_market/economic_research.py`. The saved report was read and hashed:
`0a55dd7c1483fd0da79db5e2b849132fc612f8a707f70a76a9be91d4f387c09f`.
It contains four registered sparse-entry policies, 27,820 saved predictions,
420 decision dates, 97 securities, zero new fits and zero provider requests.
It preserves 2025–October 2026 as known development information. Five-session
LSTM Top 5 reference returns were −8.7210% gross/−44.9781% after assumed costs;
XGBoost was +13.0354% gross/−31.7746% after assumed costs. All four sparse-entry
policies remain negative under the original cost case, and all eight paired
baseline intervals include zero. These are conditional price-reference
simulations, not repairs to the 504 original runs or executable investment P&L.

Verification coverage is provided by `test_research_backtest_audit.py`,
`test_research_backtesting.py`, `test_investment_economic_research.py` and
portfolio tests in the campaign regression. Current exact test results and
protected-file preservation are recorded in `14-end-to-end-verification.md`.
