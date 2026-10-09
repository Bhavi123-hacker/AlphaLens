# Frozen real NSE research economic evidence audit

Review baseline: `8507f7fd5457fe5e53e016c2cd7b8f14e6b6e430`, 2026-10-09.
This is a read-only audit of completed results, not another simulation or model
evaluation. All 152 fits, 504 backtests and the four already-completed 2026 final
holdout evaluations remain unchanged. No candidate selection, threshold change,
P11–P14 calibration or production promotion follows.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION; NOT PRODUCTION PIT.
P1_PRODUCTION_DATA_CLEARANCE = OPEN;
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.

## Scope and evidence

The [machine-readable audit](real-research-economic-audit.json) covers every
backtest, with its saved summary/trades/equity hashes, cause-event references and
source evidence. It includes a SHA256 inventory of all 2,485 completed run files
(8,505,278,241 bytes), including models, OOS predictions, locks and holdout
attempt markers. Inventory identity:
`608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`.
All paths, sizes and modification timestamps were unchanged after the audit.
The canonical bucket hashes and all 17 original action and 17 original price
file hashes were checked against their frozen manifests. This supplements the
existing [full artifact verification](../development/real-research-artifact-verification.json);
it does not repeat its 46-million-row OOS validation or any fit.

The auditor compares recorded trade lifecycles and every missing equity session
with canonical price availability and action flags. **Zero trade-status,
equity-null-session, action-source or summary-status inconsistencies were found.**
No execution defect explaining an unresolved outcome was demonstrated by these
checks. This is a bounded conclusion, not proof that all accounting choices are
economically complete.

## All 474 unresolved runs

| Mutually exclusive cause group | Runs |
|---|---:|
| Unreconciled economic actions, without observed price gaps | 258 |
| Both action uncertainty and price/identity gaps | 198 |
| Price/identity gaps, without action uncertainty | 18 |
| Total unresolved | 474 |

The other 30 runs retain their original full-path **raw-price diagnostic** status.
They are not newly cleared total-return results. The following cause counts
overlap across runs; they must not be added together.

| Evidence cause | Affected runs | Unique security/session/kind events |
|---|---:|---:|
| Raw economic action requires reconciliation | 456 | 288 |
| Verified missing Muhurat price slot | 135 | 21 |
| No observation for the held identity in an ordinary observed session | 93 | 46 |
| Same symbol observed under another ISIN, not automatically merged | 42 | 4 |

Among the 288 action events, 85 first trigger unresolved accounting and 203
occur after the position is already unresolved. These later actions are
additional evidence, not 203 new initial failures. The first triggers comprise
81 dividends, two bonuses and two rights events. Across all 288 events the
types are 266 dividends, 14 bonuses, five rights, two demergers and one split.
These counts are deduplicated by held security/session/event kind; a source
event repeated across model, strategy and cost runs is not independent evidence.
The 288 security/session/kind events refer to 280 distinct security/session
action dates; eight dates appear both as initial and subsequent causes in
different held-position histories.

Across all 504 runs the stored final trade statuses are 93,399 CLOSED, 1,032
UNRESOLVED_RAW_ECONOMIC_ACTION, 231 UNRESOLVED_MISSING_EXIT and 87 OPEN. These
counts include repetitions across the three cost scenarios. A legitimate OPEN
position at period end is not a fabricated exit or automatically an unresolved
economic failure.

There are 26 unique missing-exit events and 45 temporary missing-mark events.
All 474 unresolved runs also retain at least one permanently unresolved trade;
none is blocked exclusively by temporary marks. Temporary marks still matter
for the original full-path metrics. The engine deliberately retains
`ever_unknown`: later valid prices cannot reconstruct an unknown earlier NAV
or authorize a full-path return/Sharpe/drawdown claim.

The recorded final action status can overwrite an earlier missing-exit status
when an unresolved position later encounters an action. The audit preserves
both causes and chronology. That is a diagnostic limitation of the single
status field, not evidence that the missing exit was economically resolved.
In 45 trade instances (including cost-scenario repetitions), a missing exit was
the initial blocker and a later action became the final stored status.

## Missing source evidence versus software limitations

All 71 missing-exit/mark events were checked against original price Parquet:
**67 have no matching source observation**; **four have actual prices under
another ISIN**. No synthetic price, interpolation, zero terminal value or later
exit substitution was created.

The 21 missing Muhurat events all fall on **2023-11-12**, the only one of the
five known omitted sessions reached by these locked OOS periods. Twelve are
missing exits and nine are missing marks. The other four documented missing
Muhurat sessions remain missing in the frozen dataset; they were not silently
removed from the calendar.

The four identity-gap dates are **2022-10-19, 2022-10-20, 2022-10-21 and
2022-10-25** for `GLOBAL`: the held ISIN is `INE291W01011`, whereas real source
prices exist under `INE291W01029`. This is incomplete dated continuity/action
evidence, not an absent market price and not permission to merge by symbol.
No source-year provisional-ID boundary explained an audited event.

The remaining 46 events lack a matching original source observation. Examples
include SABEVENTS, VARDMNPOLY, VICEROY, GENSOL, ANSALAPI and BIRLATYRE. Absence
does not prove delisting, suspension, bankruptcy or zero recovery. The exact
security/date queue is in the JSON, with entry identity and record references.

All 81 initially blocking dividend records contain a declared cash amount;
the two bonus and two rights records contain ratios. It would be incorrect to
describe every action as missing source data. The frozen engine intentionally
does not reconcile dividend entitlement/payment, rights elections/cash flows,
quantity transformations or terminal recovery. The action schema has no
payment-date field. A declared amount/ratio alone is not a verified economic
ledger. Actions are symbol/date matched in the frozen canonical builder;
**34 action-event matches have differing nonempty price/action ISINs**. They
remain unresolved evidence requiring dated reconciliation; mismatch alone
does not establish a wrong company or authorize ignoring an action.

Actions are checked before the planned close exit, including entry-session
actions. That is the locked conservative policy, not a verified entitlement
model. Future improvements must distinguish ex-date entry from prior holdings
using evidenced timing and entitlement rules. The audit does not bypass this
policy, credit hypothetical dividends or reprice existing artifacts.

## Actionable remediation queue

| Priority | Work | Evidence needed / acceptance condition |
|---|---|---|
| 1 | Recover missing source observations | Legitimately licensed dated OHLCV for the 67 missing keys, including 2023 Muhurat; retain original files and availability/vintage limitations. Missing evidence stays unavailable. |
| 1 | Resolve identity transitions | Dated, usable security/action evidence linking GLOBAL's two ISINs with effective conversion semantics; reconcile the 34 action/price ISIN mismatches. Never merge on ticker alone. |
| 2 | Add explicit action accounting in a future version | Confirmed entitlement, effective date, quantity/cost/cash semantics and payment timing. Separate dividends, splits, bonuses, rights and demergers. Source amounts/ratios are evidence inputs, not automatic adjustments. |
| 2 | Investigate terminal/departure gaps | Dated listing/suspension/delisting/merger and reliable terminal consideration evidence for each affected identity. Retain unresolved holdings if economic value is unknown. |
| 3 | Improve diagnostic event history | Separate the initial blocking cause from subsequent action observations, rather than relying on a single overwritten status. Existing artifacts remain immutable. |
| 3 | Define bounded partial-path reporting | If useful, separately identify known segments and closed-only statistics. Do not turn a recovered later NAV into a complete historical equity curve. |

These are future, separately versioned data/accounting work items. They do not
authorize redoing the 2026 selection/evaluation, tuning on the holdout, replacing
existing backtests or training again. Any eventual reconciliation must preserve
the baseline and disclose changed economic assumptions in a distinct result.

## Verification and phase boundary

Targeted TEST_ONLY auditor tests cover temporary versus permanent gaps, action
precedence, later status overwrite, valid period-end open positions, rejected
prices, detectable stored-state inconsistency, identity alternatives, original
source hashes/absence and protected output paths. Static checks cover only the
new auditor/test logic. Existing Windows/PostgreSQL gates are retained; no schema,
financial engine or frozen dependency lock changed.

P17 is **NOT_STARTED**. The software baseline can be reviewed for a separately
authorized research-only API scope once security readiness is assessed. Economic
evidence remains insufficient for a production champion, calibrated product
signals or a complete total-return/performance claim. Genuine benchmark and PIT
fundamentals remain UNAVAILABLE; final-vintage and historical calendar/type
limitations remain. Container security status is recorded separately in
[the security review](../development/container-security-remediation.md).
