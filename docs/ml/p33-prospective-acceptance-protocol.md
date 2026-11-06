# Prospective independent acceptance protocol — p33.prospective.v1

Status: DESIGN_COMPLETE_NOT_APPROVED_OR_STARTED. This protocol does not accept
any of the four frozen candidates. No 2026 holdout replay or new fitting is allowed.

Before the first eligible observation, an independent reviewer must sign a
checksum-pinned registration containing candidate/artifact IDs, horizons, exact
ordered 38 features, eligible universe, source/rights and corporate-action basis,
decision clock, outcome maturity, missingness policy, costs, success margins and
the power analysis below. Missing registration means no acceptance. Freeze this
registration before inspecting prospective outcomes; amendments start a separate
version/cohort and cannot retroactively change an existing result.

Primary outcomes by declared task/horizon: balanced accuracy against a past-only
majority classifier; Brier score and reliability bins for probabilities; rank IC
against a fixed descriptive momentum baseline for regression/ranking. Naive zero
return and fixed historical momentum predictions are additional locked baselines.
Report sample counts, class balance, coverage/exclusions, calibration intercept/
slope, fold/session dispersion and all confidence intervals. These are distinct
statistics; loading a model or having finite outputs is not acceptance.

Minimum evidence is set by a prospective power calculation, not the current four
candidates' results. Independently choose an economically meaningful minimum
improvement delta, family-wise error budget and target power before observation.
For a binary proportion, n >= z²p(1-p)/precision² is only a planning lower bound;
use conservative p=0.5 and inflate for serial/cross-sectional dependence. Estimate
design effects from a separate permitted pre-period, not the locked 2026 holdout.
For paired model-minus-baseline losses, predeclare a session-block bootstrap or
HAC variance estimator, block length at least the longest overlapping horizon,
and solve n for the desired margin/power using independent pre-period variance.
The registration must contain actual numeric minimum independent sessions,
matured outcomes per horizon/class, effective sample size, duration and coverage;
absent values block acceptance. No invented universal row count substitutes for
this calculation. Require multiple non-overlapping chronological assessment
blocks and sufficient relevant market conditions; unavailable regime evidence is
reported rather than invented. Count session/security clustering, not millions
of correlated rows as independent observations.

Record predictions immutably before entry/outcome availability using existing
P19 prospective contracts. Matured P7 targets remain separate from predictors.
Use the original chronological purge and embargo conventions. No imputation of
ineligible rows, current-universe historical backfill, outcome-based deletions,
test-set threshold tuning or candidate switching. Report every registered
candidate/horizon and adjust inference for their multiplicity. Evaluate only
after the locked sample/maturity boundary; interim operational checks cannot
promote a model. Failed/late sessions remain in coverage denominators.

Economic assessment additionally needs compatible action-adjusted paths or
complete raw action accounting, executable next-session conventions, liquidity,
fees/slippage sensitivity, unresolved terminal outcomes, drawdown path and
turnover. Compare fixed cost scenarios over the complete prospective path.
Missing evidence is not zero cost or zero loss. Existing 474 unresolved backtests
remain unresolved and cannot supply a positive acceptance result.

Acceptance requires the registered confidence-bound improvement, calibration,
stability, coverage and economic/drawdown constraints jointly passing with an
independent written review. Numeric margins are external scientific decisions
to be locked before outcomes, not parameters the application guesses to approve
models. A negative result stays negative. Model acceptance does not clear P11–P14
publication, source rights, production security or applicable financial-advice
review. These gates remain independent.
