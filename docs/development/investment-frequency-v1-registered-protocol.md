# Investment frequency V1 — registered development research

Registered before executing the four policies below. This is a new analysis of
saved, already inspected historical development predictions, not an independent
test, a new model fit, or prospective validation. Original artifacts stay intact.

## Hypothesis and fixed budget

Repeated full liquidation and re-entry every five eligible decision dates charges
60 basis points at each completed round trip under the existing registered
50-bps cost plus 5-bps slippage per side. Fewer decisions may reduce that drag,
while also changing market exposure and potentially sacrificing gross returns.
That tradeoff must be measured, not assumed favorable.

Exactly four policies, one execution each, with no subsequent parameter search:

1. Saved LSTM Top 5, start every 10 eligible decision dates.
2. Saved LSTM Top 5, start every 20 eligible decision dates.
3. Saved XGBoost Top 5, start every 10 eligible decision dates.
4. Saved XGBoost Top 5, start every 20 eligible decision dates.

Use the exact immutable sequence benchmark `historical-predictions.json` and
`report-final.json`, checksummed against their sidecars. No model training,
feature changes, extra provider requests, scoring threshold optimization, cost
changes, or substitution of missing observations. Pin input and protocol hashes.

## Clock, membership, outcome and reference assumptions

The clock is the sorted common list of decision dates in the original saved
historical prediction table. Start with its first date and select every 10th or
20th date, deterministically. Retain the original next observed open to fifth
subsequent observed close target. Entry follows the decision date; exit must be
later than decision and no later than the next selected decision close (the
following entry is at a later opening). Fail closed
if incompatible target sessions occur within a selection or horizons overlap.

All candidates must have the same eligible saved outcome and finite score. Sort
descending score then exact instrument key, select five (or actual smaller
coverage), equal weight, liquidate completely at the registered fifth close.
Cash between references earns an explicitly assumed zero. These are **five-session
holdings with sparse entry**, not 10/20-session holding-return predictions or a
continuous carry-position simulation. No annualization or cash yield invention.
The approximate active-session fraction is 5 / decision spacing and is labelled
as such; no measured intraday exposure claim follows.

Current-fixed-cohort retrospective membership, final-vintage observations and
unknown historical publication/action completeness remain limitations. Source
adjusted price-component references exclude dividends and verified broker fills.
Full-path mark-to-market, gaps, capacity and actual bid/ask spreads are unavailable.
Endpoint drawdown must never be described as full-path portfolio drawdown.

## Comparators, costs and measurement

For each identical sparse schedule, compute saved mean-reversion Top 5 and the
equal eligible cohort. Also reproduce the original five-date schedule for each
model and the same baselines as an audit; do not overwrite its report. Compare
relative returns on matched dates, and separately show original higher-exposure
results. A sparse policy beating an unmatched fully invested policy is not proof
of superior selection. No genuine NSE index benchmark is currently qualified.

Retain 25/50/100-bps round-trip sensitivities plus 5-bps slippage per side.
At the central scenario charge every complete allocated round trip 60 bps,
including unchanged names, exactly as before. Report gross/net compounded
reference returns, cost/slippage decomposition in log-wealth units (exact
telescoping order: gross, then 50-bps cost, then 10-bps slippage), decision count,
membership turnover, selection concentration, losing blocks, calendar-period
contributions and endpoint drawdown. Membership turnover is diagnostic and does
not reduce liquidation costs. No hypothetical change to original cost policy.

Paired uncertainty: 500 deterministic moving-block replicates of four consecutive
selected decisions, seed 1729, compare mean net reference return to each matched
baseline. Preserve shared dates; mark intervals as exploratory, dependent on
development data, and not adjusted for four-policy/two-comparator selection.
Reject a claim of demonstrated edge regardless of a favorable point estimate:
new independent frozen future forecasts and existing acceptance requirements
remain necessary. All four results, including negative results, are retained.

## Output and integrity

Write a new private immutable receipt and bounded API-ready report under
`.local-data/investment-evidence-research`. Record original input hashes,
generation time, exact target, all policy rules, all comparisons and exclusions.
Do not write any forecast/outcome ledger, accepted service or original artifact.
The analysis produces no current predictions and no accepted investment advice.
