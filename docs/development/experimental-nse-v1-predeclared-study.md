# ALPHALENS_EXPERIMENTAL_NSE_V1: predeclared private pilot

Declared 16 October 2026 before the independent acquisition/training run.
This family does not load, modify or promote the original frozen models.

The fixed cohort is RELIANCE, TCS, INFY, HCLTECH, WIPRO, TECHM, HDFCBANK,
ICICIBANK, SBIN, KOTAKBANK, AXISBANK, ITC, HINDUNILVR, NESTLEIND, BRITANNIA,
MARUTI, M&M, BAJAJ-AUTO, SUNPHARMA, CIPLA, DRREDDY, LT, ULTRACEMCO, GRASIM,
NTPC, POWERGRID, ONGC, TATASTEEL, HINDALCO and BHARTIARTL. These are a manually
declared diverse, familiar current-watchlist cohort, not selected by measured
returns. Current-master exact NSE_EQ/type-EQ identity is mandatory. Unresolved
symbols are excluded without winner-based substitution. This is neither a
historical membership reconstruction nor a survivorship-free NSE study.

Acquire daily OHLCV from 1 January 2022 through 15 October 2026, one bounded
historical request per resolved instrument plus one current master, maximum 31
GETs, no automatic retries, shared provider rate ledger. Private noncommercial
retention and derived ML scope is the specific official reply documented in
docs/data/p34-private-upstox-use-decision.md. Store only in a new protected,
ignored private directory. Replays verify all checksums and make zero requests.
Subsequent captures have new immutable IDs; they never overwrite revisions.

The adjustment basis, historical availability clocks and exhaustive corporate
action coverage are UNKNOWN. Consequently this pilot excludes overnight price
changes, cross-date price levels and volume ratios from features and targets.
It studies same-candle dimensionless ratios, invariant to a uniform positive
multiplier of that candle's OHLC. This is an explicit methodological assumption,
not verified action-adjusted shareholder returns. Volume is retained for data
quality and displayed observations only. No dividend or total-return claim.

The 11 ordered features are current close/open minus one, (high-low)/open,
and trailing 5, 10 and 20 observed-session mean, population standard deviation
and fraction-positive of close/open minus one. Flat candles have true zero
return/range; no imputation. The target is the sign of the product of the next
five observed-session close/open ratios minus one. This is aggregate daytime
price movement across five separate sessions, not a five-day holding return,
executable return, or investment recommendation.

The reference grid is the union of genuine observed cohort candle dates.
Missing instrument dates invalidate the affected complete 20-slot feature
window or five-slot target. Windows crossing a gap exceeding seven calendar
days are conservatively excluded. No missing exchange session is fabricated;
exhaustive official calendar coverage is not established by this grid. Actual
publication timestamps and historical versions are absent: evaluation is
final-vintage retrospective research, never historical point-in-time simulation.

Chronological date groups use 60% training, 20% validation and untouched 20%
final evaluation; purge five slots at each preceding boundary and embargo five
at each following boundary. All securities sharing a date remain together.
Standardization fits training data only. Candidate: logistic regression,
C=1, balanced class weights, fixed seed 42, max_iter=1000. No parameter search
or final-period tuning. Baselines are training-majority direction and sign of
trailing-five-session mean daytime return. The logistic model is exploratory
regardless of whether it outperforms those baselines. Its sigmoid is labelled
an uncalibrated model score, never empirical confidence.

Report sample/date counts, balanced accuracy, precision/recall, Brier score,
rank correlation, date-cluster uncertainty, time-period stability and a
descriptive cost/turnover sensitivity where defined. These cannot establish
profitable investing. Do not claim independent model acceptance from a numerical
output. Inference uses only exact complete vectors at the latest observed grid
date and the verified saved model. Forecasts are created at actual runtime,
with source retrieval, dataset/model/feature IDs and immutable input hashes;
they cannot be backdated. Future reconciliation requires genuine later source
observations and five matured observed slots. Retrospective evaluation rows
never enter the prospective forecast ledger.

The new lists are EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED, restricted to
actual eligible scored cohort members. They never populate accepted rankings,
alerts, automated signals, official portfolio valuation or trading. The working
RELIANCE daily task remains unchanged; additional acquisition scheduling is a
separate qualification, not implied by this manual bounded pilot.
