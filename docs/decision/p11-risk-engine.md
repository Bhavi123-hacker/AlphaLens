# P11 point-in-time risk engine

Authorized under D59-D60 from P10 f709839. P11 must pass and be committed before
P12 implementation. No trading action, loss-probability forecast, position sizing
recommendation or profit promise is produced. TEST_ONLY — NOT A PERFORMANCE CLAIM.
RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED. Production clearance remains open.

## Evidence boundary

Risk uses one P6 decision row, its replay-verified P5 historical snapshot, P4
membership/identity and P3 quality. Decision, session, price basis, classification
and input identities must match. Unknown or rejected observations remain missing;
session slots are never compressed into a fabricated continuous history.
P6 ATR, unannualized rolling volatility and current drawdown are reused. P11 adds
past-only volume/gap and recent drawdown diagnostics where no P6 equivalent exists.
Fundamentals, market capitalization, order books and sectors remain unavailable.

P9 predictions are projected into a target-free contract. Future outcomes,
scoring exclusions and P7 targets are not decision inputs. Full future P9/P10
reports cannot evaluate an earlier risk decision. Fold diagnostics become usable
only once the complete evaluated fold's scored outcomes are available; unknown
availability means unavailable. Each diagnostic carries task, horizon, family,
model/evaluation references, sample count and explicit knowledge time. Later
reports/predictions are filtered before calculating disagreement or uncertainty.
These are simulated historical availability rules, not a claim the software ran
on that historical wall clock. Inputs are trusted local artifacts, not authenticated
external documents merely because they have checksums.

## Components and policy

Each component retains measured values, availability, normalized severity, level
and sorted reasons. Normalized severity is an engineering policy, not empirical
probability. All scales/minimums are serialized in the versioned risk policy.

| Dimension | Measurement / interpretation |
| --- | --- |
| Volatility | P6 20/60-session sample standard deviations and ATR14/current close; normalize against explicit daily-volatility and ATR-ratio scales. No future returns. |
| Drawdown | P6 current drawdown20; recent maximum drawdown from past 20-session prefix peaks. No future recovery. |
| Liquidity proxy | Past 20 observed volumes: zero-volume frequency, P6 relative volume and sample coefficient of variation. VOLUME_BASED_LIQUIDITY_PROXY does not establish executable capacity. |
| Gap | Past open/previous close minus one, absolute latest/maximum gaps and fixed large-gap frequency. Missing sessions or known unadjusted economic actions prevent a clean market-gap assessment. |
| Market | Relative security/benchmark volatility where the evidenced P6 benchmark context exists. Zero/unknown benchmark volatility is unavailable. No beta estimate without its own future approved evidence/formula. |
| Model uncertainty | Probability proximity to 0.5, cross-family probability/return dispersion, historically available fold instability/calibration and sample sufficiency. No invented confidence intervals. |
| Data quality | Actual current P3/P5 quality and unavailable/stale feature evidence, separately from long-indicator warmup. REJECTED blocks analytical eligibility; DEGRADED adds a reason. |
| Corporate actions | Known raw-price economic actions and NOT_ESTABLISHED coverage remain explicit. Symbol-only changes are not an economic adjustment. No invented factors or neutral corporate-action confidence. |
| Evidence sufficiency | Deterministic required/sufficient history and validation counts; SUFFICIENT, LIMITED or INSUFFICIENT. Missing observations cannot imply LOW risk. |

Overall LOW/MEDIUM/HIGH/VERY_HIGH follows the worst usable component, with explicit
uncertainty floors for missing optional evidence. Essential history/price/universe
or quality failures produce UNAVAILABLE and block analytical permission. A strong
prediction never erases an unfavorable component. There is no unexplained weighted
overall score. Components/reasons are engineering diagnostics; P14 owns full
user-facing explanations and P13 owns actions.

The initial policy uses a 20-session component window, 21 required price slots
and 61 slots for sufficient longer history. Daily volatility severity is divided
by 0.05, ATR/price by 0.10, drawdown magnitude by 0.30, zero-volume frequency by
0.10, volume coefficient of variation by 2, absolute gap by 0.05 and large-gap
frequency by 0.20. Excess relative volatility over 1 is divided by 2. Values are
clamped to [0,1]. Probability dispersion uses 0.25; return dispersion uses 0.05.
Calibration/sample diagnostics require 100 historical scored observations.
Component severity bands are <0.25 LOW, <0.50 MEDIUM, <0.75 HIGH, else VERY_HIGH.
These are deliberately disclosed development assumptions, not calibrated market
risk boundaries or probability-of-loss estimates. They cannot be tuned against
the same TEST_ONLY outcomes to assert a market edge.

The 21-slot minimum does not override P6 input requirements. ATR14 inherits its
bounded 50-slot recursive history policy; pre-listing/missing slots can keep ATR
unavailable even when 20 daily returns exist. Risk therefore requires the actual
P6 core feature states as well as the declared minimum count. Unknown action
coverage marks observed raw gap diagnostics DEGRADED, not verified ordinary market
gaps. Model sample counts are per family, not multiplied across models scoring the
same fold; ambiguous diagnostic vintages are rejected.

## Snapshots, CLI and limitations

A risk snapshot pins security/session/knowledge cutoff/horizon, policy and engine
version, feature set, canonical and universe snapshots, visible model evidence,
classification, measured components, overall level, reasons and eligibility.
SHA256 identity covers the complete versioned result except its own ID. New input
dataset versions may change audit IDs even when unchanged earlier measurements
demonstrate PIT invariance. Adding invisible model evidence must not change the
visible snapshot. JSON artifacts are immutable, locally stored and checksum-pinned;
readers verify schema, ID, classification and checksum. No unsafe model loading.

Developer command: `alphalens-risk evaluate --canonical INPUT --features FEATURES
--session DATE --security SECURITY --horizon 5 --output data/risk`, optionally with
verified P9 evaluation directories and a serialized risk policy. Output contains
risk components/reasons and classification, never BUY/SELL or a recommendation.

The authored fixtures verify mechanics only. Real historical universe, calendar,
corporate-action coverage, benchmark, costs/rights and adequate independent model
validation remain required. Research and production approval are separate.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
