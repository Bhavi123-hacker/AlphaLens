# Registered ALPHALENS_EXPERIMENTAL_NSE_V2 protocol

Registered 16 October 2026 before V2 expansion acquisition and before actual
V2 fits. V1 and original P9–P14 artifacts/holdouts remain immutable. All historical
data through 16 October 2026 is **known development/diagnostic information**,
including V1's already inspected final period. Independent confirmation requires
genuinely future observations and independent human review.

## Source and outcome

Use the official Upstox staff price-basis evidence in
`docs/data/ml-v2-source-and-target-audit.md`: OHLC is split/bonus adjusted, not
dividend adjusted. Do not double-adjust or rewrite V1 UNKNOWN metadata. Rights,
demergers, exhaustive action coverage, adjustment vintages, historical membership
and original publication/revision clocks remain unresolved.

Primary target is `close[t+5]/open[t+1]-1`, on complete observed-cohort slots:
the **split/bonus-adjusted price component** of a five-session holding interval.
Entry is a later session's open, never the decision's published EOD close. Exit
is the fifth session's close. This is not dividend total return, verified fills
or actual profit. Horizons10/20 are label readiness diagnostics, not searched
for improved results. A prospective forecast needs already received data,
verified elapsed observation session, actual recorded time and the next eligible
session's officially dated open still in the future. No weekday guessing,
backdating or entry-date shifting. Otherwise scores are timing-ineligible research.

## Predeclared cohort, permissions and bounds

Reuse the genuine V1 30-stock snapshot read-only. Add these20 current securities:
ADANIPORTS, APOLLOHOSP, ASIANPAINT, BAJFINANCE, BAJAJFINSV, BEL, BPCL, COALINDIA,
DIVISLAB, EICHERMOT, HEROMOTOCO, INDUSINDBK, JSWSTEEL, SBILIFE, HDFCLIFE,
SHRIRAMFIN, SIEMENS, TITAN, TRENT, UPL. No return-based substitutions. Resolve
exact NSE_EQ/type-EQ symbol/ISIN/key. This50-security current fixed cohort is not
historical NSE membership or a survivorship-free study.

History: 2022-01-01–2026-10-15. Initial budget at most80 shared-ledger GETs:
master,20 histories, up to50 transient action references, no automatic retries.
Historical retention/derived ML uses the existing official private noncommercial
permission. Raw Fundamentals bodies remain transient; retain only minimal derived
private exclusion facts, source/receipt/hash and disclosed scope interpretation.
An explicit separate current-session capture allows at most60 GETs: master,
50 official current-day historical-intraday `days/1` candles, nine official dated
timing checks. Require independent lower clock bound after actual official close;
retain exact provider timestamps/receipts. No resampling or certified-final-close
upgrade. No new unattended acquisition or material recurring volume is enabled.

## Quality, features and targets

Validate finite positive OHLC ordering, integer volume, identity/request/date,
duplicates and hashes. Grid is the union of genuine observed dates, not an
exhaustive exchange calendar. Missing slots remain missing. Known action dates
exclude intersecting lookback/target windows; unavailable/unparseable action
evidence stays an explicit gap. Quarantine unexplained absolute close-to-close
or overnight gaps above40% and identical full OHLCV across different securities
on the same date, without inferring adjustment factors. Preserve revisions.

`nse.adjusted-price-context.20.v2`, in order: returns1/5/20/60; returnSD20/60;
SMA distances20/60; RSI14; MACD12–26/close; drawdown60; ATR14/close; range/open;
current open-close return; OC mean20 and positive fraction20; fixed-cohort mean
returns5/20; stock-minus-cohort returns5/20. Require complete61-slot lookbacks
and at least80% contemporaneously supported fixed-cohort context. These are new
declared formulas, not replacements for frozen cross-sectional momentum. No
cross-date volume ratios, invented benchmark/sector/PIT membership or fundamentals.

## Fixed experiment budget and selection

Primary h5 only, four fixed configurations:

- Logistic: C1, balanced classes, seed42, max_iter1000, train-only scaler.
- Ridge: alpha10, train-only scaler; regression scores are not probabilities.
- HistGradientBoostingClassifier:100 iterations, depth3, min_leaf100, l2=10, seed42.
- RandomForestClassifier:100 trees, depth4, min_leaf100, max_features0.7,
  seed42, at most4 threads.

Expanding annual folds evaluate2023/2024/2025/2026 on earlier training dates only;
all same-date securities stay together. Purge20 and embargo20 observed slots;
training targets mature before evaluation starts. Fit preprocessing on training
only. Select highest mean date-wise rankIC across2023–2025, deterministic ties
by listed algorithm order. 2026 is known-period diagnostics, never an independent
test and never used to select. At most16 fold fits plus one selected full eligible
development refit; no tuning search or discarded failures.

Baselines: training-majority, five-slot momentum, five-slot mean reversion,
equal eligible fixed cohort and low historical volatility. Equal cohort is not
an official index benchmark. Report BA, precision/recall, ROC-AUC, Brier/calibration
where applicable, date-wise rankIC, quantile separation, time/regime/security
slices, missingness/redundancy/stability and sample counts. Use20-date moving
blocks preserving same-date stock groups. Historical family-wise comparisons
use Bonferroni correction across4 candidates ×3 directional baselines. They are
development statistics, not independent evidence of an edge.

## Economic and independent acceptance rules

Price-reference simulations, if complete, use non-overlapping five-slot cohorts,
top5/10/20 and equal/momentum/low-vol baselines. Assume observed future reference
open/close fills, and show10/25/50/100bps assumed round-trip costs with0/5/10bps
slippage per side. These are sensitivity assumptions, not verified historical
taxes, fees, executable prices, cash entitlements or actual returns. Missing
prices invalidate scenarios. Genuine economic acceptance requires independently
compatible action/cash/execution/cost and benchmark evidence, currently unresolved.

Before eligible future outcomes, lock minimum126 distinct future decision dates,
1,000 matured forecasts,30 securities and two calendar quarters; frozen selected
primary-horizon model; simultaneous95%20-date-block lower BA improvement>0.02
versus directional baselines; mean date-wise IC>0.02; Brier better than majority
if calibrated probabilities are claimed; adequately sampled positive time/regime
robustness and independently supported net economics. Never lower thresholds.

Engineering, research and independent human approval are separate. Codex cannot
be the independent reviewer. Approval binds a frozen protocol/model/data/outcome
bundle and independently established reviewer identity/scope. A boolean, fit,
backtest or signature alone cannot clear original accepted publication gates.
Until all real requirements pass, report NO_DEMONSTRATED_EDGE and accepted ranks0.
States: EXPERIMENTAL_UNVALIDATED, BACKTESTED_NOT_PROSPECTIVELY_ACCEPTED,
PROSPECTIVE_EVALUATION_IN_PROGRESS, and only after genuine independent evidence
INDEPENDENTLY_ACCEPTED. Preserve the existing RELIANCE task unchanged.
