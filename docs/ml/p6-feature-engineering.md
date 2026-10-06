# P6 point-in-time feature engineering

Authority: D49-D50, explicit user amendments to development scope; original DOCX
unchanged. P1_PRODUCTION_DATA_CLEARANCE = OPEN;
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED; FUNDAMENTAL_PIT_DATA = UNAVAILABLE.

## Architecture and decision time

`alphalens_features` depends on P5 only. CLI verifies a P5 input envelope through
its established loader; numerical code accepts a CanonicalReader. For each
explicit decision `(session t, knowledge_cutoff)`, P5 reads only observations and
revisions available by that cutoff in historical mode, never a latest snapshot
reused backward. Verified historical receipt may be later, as allowed by P5.
Live feature acquisition/execution is outside scope.

Completed session t information -> snapshot after required information is
available -> future outcome prediction (deferred P8) -> earliest hypothetical
t+1 open execution (P7 target convention). A late source remains unavailable at
an earlier cutoff. No t-close execution assumption exists. Decision plans specify
aware UTC cutoffs; no timestamp is inferred from future bars or label outcomes.

P4/P5 determine historical existence, listing/type, identity and analytical
eligibility at each decision. Known active but excluded securities retain rows
with reasons and null values. Not-yet-effective listings cannot enter analytical
rows or peers. Departed securities retain earlier features. P3/P5 status is
authoritative; there is no competing validator or identity system.

Verified canonical trading/non-trading evidence must cover every calendar date
from history_start to decision t (or the trailing 201-session bound). Unknown
calendar slots fail closed. Session offsets count evidenced trading sessions,
never calendar days or filtered valid bars. No exchange holiday rules are invented.
P5's old five-date UNKNOWN_SESSION_STATUS fixture remains unchanged.

## Versioned definitions and formulas

Registry schema `p6.features.v1`; 41 features with the optional designated
benchmark, 38 without. Definitions carry version/family/input fields, maximum
lookback, minimum history, cutoff/null/quality policies, parameters and formula.
Price/volume data is converted from P5 Decimal/int to float64 only inside derived
technical calculations. Original financial values remain exact and unchanged.

Let C/H/L/V be close/high/low/volume on the verified trailing session grid.
The following windows include t, except returns also need their starting close.

| Features | Exact definition / minimum observations |
| --- | --- |
| return_1/5/10/20/60 | C[t]/C[t-n]-1; n+1 closes. |
| log_return_1 | natural log(C[t]/C[t-1]); 2 positive closes. |
| sma_5/10/20/50/100/200 | arithmetic mean of n closes; n observations. |
| distance_sma_n | C[t]/SMA[n]-1, same windows. |
| ema_12/26 | At most last 50 closes; arithmetic mean of first n is seed at position n; alpha=2/(n+1), recursive alpha*C+(1-alpha)*previous; minimum n. |
| macd / macd_signal / macd_histogram | EMA12 minus EMA26 aligned starting at position 26 of the same trailing at-most-50 closes; signal uses EMA9 with arithmetic mean of first 9 MACD values as seed; histogram=MACD-signal. Minimum 34 closes for all three. |
| rsi_14 | At most last 50 closes, minimum 15. Differences produce gain=max(delta,0), loss=max(-delta,0). Seed each average from first 14 differences, then Wilder ((13*previous)+new)/14. RSI=100-100/(1+gain/loss). Both zero -> 50; zero loss with positive gain -> 100; zero gain with positive loss -> 0. |
| atr_14 | Same trailing history/minimum as RSI. TR=max(H-L,abs(H-Cprevious),abs(L-Cprevious)); first close supplies the predecessor, no invented initial TR. Seed mean first 14 TR then Wilder smoothing as above. |
| volatility_5/10/20/60 | Sample standard deviation (ddof=1) of n consecutive simple session returns, n+1 closes; unannualized. |
| volume_sma_20 / ratio_20 / zscore_20 | Mean last 20 V; V[t]/mean; (V[t]-mean)/sample stdev. Zero denominator -> NULL. Current V participates; never full-dataset statistics. |
| close_to_high_20 | C[t]/max(last 20 highs)-1. |
| range_location_20 | (C[t]-min(last 20 lows))/(max(last 20 highs)-min(last 20 lows)); zero range -> NULL. |
| drawdown_20 | C[t]/max(last 20 closes)-1. |
| bollinger_location_20 / width_20 | Bands mean +/- 2 sample stdev of 20 closes; location=(C-lower)/(4*stdev), zero spread -> NULL; width=4*stdev/mean. |
| relative_return_20 | Security return20 minus designated benchmark return20. |
| market_return_20 / market_volatility_20 | Designated canonical benchmark return20 and sample volatility20. Benchmark must have known eligible usable history; evidence designation required. |
| momentum_percentile_20 | Among historically eligible non-benchmark rows with usable return20: (strictly smaller count+(tie count-1)/2)/(peer count-1). Singleton -> NULL; ties use deterministic midrank. Any degraded peer degrades ranks. |

The finite 50-session recursive window is intentional and versioned: it is not
an all-history EMA/RSI/ATR. Every decision reseeds inside its own trailing window,
so earlier discarded observations cannot affect it. Calculation work is bounded
by 201 observations per security/decision; P5 service queries and evidence assembly
are development implementations, not production-scale benchmark claims.
OBV, trend regression, sectors, fundamentals and global scaler fitting are absent.

## Missingness, quality and corporate actions

Insufficient history -> NULL / INSUFFICIENT_HISTORY. Missing session price -> NULL
with REQUIRED_SESSION_PRICE_UNAVAILABLE. No fill, backfill or dropping bad days.
REJECTED, unavailable quality, stale or universe-ineligible required observations
cannot participate. ALLOW_DEGRADED propagates warning reasons and DEGRADED;
VALID_ONLY rejects those windows. Each feature's full required trailing window
has its own gate, including the seed window of recursive indicators.

V1 requires one explicitly evidenced basis: UNADJUSTED maps to P5 RAW_UNADJUSTED;
ADJUSTED requires P5's existing adjustment evidence. UNKNOWN/mixed basis fails
closed, never upgraded to unadjusted. Known economic actions inside unadjusted
windows mark corporate-action limitations (reason CORPORATE_ACTION_UNADJUSTED)
and DEGRADED; no repair. P3 discontinuity warnings survive. Missing corporate-action
coverage is a standing limitation; absence of a known action does not prove absence.
Later action/revision knowledge cannot change earlier cutoff values; a newly pinned
input changes dataset identity. Fundamental registry family is reserved only;
no P/E/EPS/valuation inputs or fabricated neutral values exist.

## Identity, storage and developer commands

Rows carry stable security/date, decision/cutoff, set version, per-decision P5
snapshot ID, P4 universe snapshot ID, source versions/revision keys, classification,
basis, analytical eligibility, quality and per-feature reasons. Cross-sectional
provenance includes participating peers. Final dataset canonical_dataset_id pins
the last decision snapshot; canonical_input_id pins the entire immutable P5 input;
each row retains its own cutoff-specific dataset ID. Future evidence may change
these full input identities without changing earlier numerical features.

Feature set ID is SHA256 of complete stable JSON excluding its own ID. It includes
definitions, parameters, cutoff plan, quality/basis/universe versions, classifications,
canonical input/snapshot IDs and rows. Changed executable definitions require a
new supported code/version; arbitrary formulas cannot impersonate built-ins.
JSON is full evidence; Parquet has stable typed columns, float64 nullable values,
session/security sorting, per-row evidence and complete manifest schema metadata.
Manifests include count/range/security/null/quality summaries and definitions.
Repeated builds over the same captured input are byte-identical. New captures can
have new receipt identities. Publication is immutable under ignored local data/.
No PostgreSQL matrix table or new migration is needed.

```powershell
uv run --frozen python -m scripts.build_p6_test_fixture --data-root data/p6-test-only
uv run --frozen alphalens-features build data/p6-test-only/canonical-input.json --plan data/p6-test-only/feature-plan.json --output data/p6-features
```

The 70-session TEST_ONLY history includes synthetic securities, a synthetic
benchmark (not NIFTY), future listing and departure. It exercises through 60-session
returns/volatility; 100/200-session SMA/distance remain explicitly unavailable.
It supplies constructed mechanics, never historical market evidence or performance.
Golden mathematics and P5/P4 integrated leakage tests are in test_p6_features.py.
Stop after P6 gate/commit before starting authorized P7.
