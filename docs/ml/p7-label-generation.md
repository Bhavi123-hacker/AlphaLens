# P7 leakage-safe forward labels

Authority: D49-D50. P6 DEVELOPMENT PASSED (234 passed / one production gate skip)
and committed as `ac6973f3b9a85dfff1e6094e348065ab177b4535` before any P7 files.
Branch p6-p7-features-labels; approved P5 649340a is the canonical baseline.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
No P8 training, evaluation, backtesting, ranking, signals, portfolio or UI work.

## Definitions, decision and hypothetical execution

`alphalens_labels` is a separate package depending on canonical data and P6.
Features are immutable inputs, never targets with a different column name.
Before building outcomes, replay the feature contract at its original per-row
cutoffs through P5 and compare its complete pinned bytes/identity. Source input
and classification must match. Future outcome data is passed only to target logic.

Version `p7.labels.v1` has four initial paired definitions at horizons 1, 5, 10,
20 verified trading sessions. Each names its raw continuous return and derived
binary direction, version, required inputs, horizon, entry/exit, price basis,
quality/null policies, decimal precision/rounding and cost assumption status.
Definitions are not tuned against distributions or hypothetical strategy returns.

Information: completed session t. Decision: explicit P6 cutoff after required
t information is available. Entry: next verified trading session t+1 OPEN.
Exit: close of the h-th verified future trading session, t+h. A 1-session label
is the next session's open-to-close outcome. A 5-session label holds through
five future trading sessions including entry. No entry at t close exists.

P5 provides close and availability evidence but no verified session-open instant.
V1 therefore requires the decision strictly before the entry session's local
Asia/Kolkata date begins. This conservative evidence gate proves it precedes that
date's open without inventing a clock time. It does not change the t+1-open
convention. Late cutoffs on the entry date receive
DECISION_NOT_PROVEN_BEFORE_ENTRY_OPEN and NULL, even if an actual opening time
could later establish feasibility. A future open-time evidence extension can
relax this explicitly versioned bound. No execution/fill or transaction is simulated.

## Exact raw return and direction

`forward_return_h = exit_close / entry_open - 1`, evaluated algebraically as
`(exit_close - entry_open) / entry_open`. Source prices remain exact P5 Decimal.
Numerator subtraction uses precision 76, sufficient for exact P5 NUMERIC(38,18)
inputs; division uses explicit 38 significant digits and ROUND_HALF_EVEN,
independent of the caller's decimal context. Recurring decimal ratios necessarily
have a finite representation; this precision is part of the versioned contract.
Exact numerator/denominator and entry/exit prices survive as reproducibility evidence.
There is no additional fixed-scale quantization. Parquet stores Decimal text
losslessly alongside int8 direction and typed dates/timestamps; no PostgreSQL
matrix migration is needed. Future downstream float conversion must be explicit.

Direction is 1 for strictly positive raw return, 0 for zero or negative return;
NULL when continuous outcome is unavailable. No success/+5% threshold or tuning.
Cost status RAW_MARKET_OUTCOME_NO_COSTS: no fees/slippage, net-strategy return,
dividend reinvestment or terminal-value assumptions. Full economics belong to P10.

## Session evidence, maturity and knowledge

Outcome plans specify aware outcome_cutoff and observed outcome_end separately
from feature decision cutoffs. The observed scope cannot extend beyond the
exchange-local date at outcome_cutoff. Horizons traverse P5 evidenced trading
sessions; explicitly non-trading dates do not count. Every calendar date between
decision and exit must have known canonical status. No date+h shortcut, inferred
weekend/holiday, nearby-price substitution, forward fill or backward fill.

| State | Meaning |
| --- | --- |
| MATURE | Exact entry/exit and all required future slots known, complete and usable. |
| NOT_YET_MATURE | Scope has not supplied h complete future sessions; target date stays NULL when not evidenced. No fabricated future calendar or prices. |
| UNAVAILABLE | Required calendar, membership, quality, timing, price or basis evidence missing/rejected. Reasons retained. |
| TERMINAL_EVENT | Evidenced delisting inside the known horizon window; raw return NULL and no zero terminal-value assumption. |

All h future outcome slots must be usable, including intermediate observations.
This conservative quality policy does not shorten windows around bad/missing days.
REJECTED/unavailable prices block targets. ALLOW_DEGRADED propagates warnings;
VALID_ONLY blocks degraded windows. Unknown/mixed basis blocks output.

label_available_at is the maximum evidenced availability of consumed future
session, entry/exit/intermediate bar, quality, membership and action evidence.
P5 bars cannot precede their completed close; a target cannot become mature before
its outcome is known. Later revisions produce a new target set and advance
availability to that revision. Previously pinned original sets remain immutable.
Unknown availability fails closed; no historical publication/ingestion is invented.
Historical mode respects evidenced historical availability, as in P5; live training
data ingestion and production pipelines are outside scope.

Known economic actions inside UNADJUSTED windows propagate DEGRADED with
CORPORATE_ACTION_UNADJUSTED_NOT_TOTAL_INVESTMENT_RETURN. No price repair or pure
investment-return claim. Missing action coverage remains NOT_ESTABLISHED; absence
of a known event is not proof of no action. Symbol changes are not economic actions.
Terminal outcomes and unavailable rows remain in storage, not silently dropped.

## Alignment and training eligibility without training

`p7.alignment.v1` joins stable security/session/decision identity and original
feature canonical/universe snapshot IDs to the selected label horizon. It requires
compatible source/feature/label IDs, classification and supported P6 registry.
Dataset hashes are checked; different canonical pins cannot silently join.

Explicit disjoint feature_columns, target_columns and metadata_columns are stored
in contracts/Parquet metadata. Feature columns must be selected from the P6 registry.
Target names use target_forward_return_h and target_direction_h; labels, maturity,
target dates, IDs and availability never enter feature columns. Rows are sorted
by session/security and retained even when unusable. Decisions/session columns
alone suffice for a later chronological split; no fold/model/scaler is implemented.

TRAINING_ELIGIBLE requires decision information by training_as_of, historical
analytical eligibility, usable selected features, mature label available by that
cutoff, compatible classification and accepted quality. Default refuses degraded
features/targets; an explicit allow_degraded option is recorded in identity.
Known unadjusted action windows remain ineligible even with that option.
FEATURE_UNAVAILABLE, UNIVERSE_INELIGIBLE, LABEL_NOT_MATURE, LABEL_UNAVAILABLE,
quality and timing reasons explain ineligible rows. Targets after training_as_of
are masked to NULL even if a later outcome artifact contains them.
Selecting all P6 features includes unavailable 100/200-session values in the short
fixture and therefore yields ineligible rows; explicitly selecting a usable raw
subset is permitted and recorded. No neutral fill or optimization occurs.

## Identity, artifacts and CLI

Label set SHA256 includes canonical input/outcome snapshot IDs, feature set ID,
versions, parameters/horizons, execution/basis/quality/cutoff/universe conventions,
classification and rows. Alignment has its own ID including selected columns,
horizon, training cutoff and degraded policy. Same captured inputs yield identical
JSON/Parquet; changed evidence, scope or meaningful definitions create new IDs.
Final canonical_dataset_id is the outcome snapshot; each row additionally pins
feature_canonical_dataset_id and the feature-time universe snapshot.

Immutable local artifacts: labels.json, labels.parquet, label-manifest.json,
target-distribution.json and a separate alignment-ID directory containing
supervised.json/supervised.parquet. Manifest carries definitions, compatible
feature ID, source IDs, horizons/conventions, classification/basis, row/range and
maturity/quality counts. Distribution is descriptive fixture count, mean, median,
sample standard deviation, positive/missing proportions only, with explicit
TEST_ONLY/RESEARCH_FIXTURE classification and no predictive-success claims.

After the P6 fixture/features command, create an outcome plan in ignored storage:

```json
{"outcome_cutoff":"2024-03-10T12:00:00Z","outcome_end":"2024-03-10","horizons":[1,5,10,20]}
```

```powershell
uv run --frozen alphalens-labels build data/p6-test-only/canonical-input.json --features data/p6-features/<feature_set_id>/features.json --plan data/label-plan.json --output data/p7-labels --feature-columns return_1 sma_5 --allow-degraded
```

These are TEST_ONLY software checks, not real NSE history or historical performance.
Fixture availability/basis/calendar/classification cannot become PRODUCTION.
FUNDAMENTAL_PIT_DATA remains UNAVAILABLE. Stop before P8 even after P7 passes.
