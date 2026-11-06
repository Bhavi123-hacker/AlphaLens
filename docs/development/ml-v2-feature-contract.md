# V2 feature formulas

Contract `nse.adjusted-price-context.20.v2`, defined before V2 fitting. These
formulas consume one immutable official-provider adjusted-OHLC snapshot. Prices
are split/bonus adjusted according to the staff evidence; dividends, complete
action coverage and historical publication vintages remain unverified.

For each instrument and observed decision date t, require all61 consecutive
observed-cohort slots t−60 through t. No missing slot is interpolated. A gap
above seven calendar days excludes the window. Any known corporate-action
hazard date intersecting the window excludes it. Derived features use float64;
original price observations remain exact decimal strings.

In exact input order:

1. Price returns1/5/20/60: `close[t]/close[t−k]−1`.
2. Return SD20/60: population standard deviation of the last20/60 individual
   close-to-close returns.
3. MA distances20/60: `close[t]/mean(last k closes)−1`.
4. RSI14: `100*mean(positive close changes)/(mean(positive changes)+mean(negative
   change magnitudes))`, with50 for an entirely unchanged14-change window. This
   is a simple14-change RSI variant, not Wilder smoothing.
5. MACD12–26 divided by current close. Both EMAs are initialized with the first
   close in the same61-close window; recurrence weight is `2/(period+1)`. No
   hidden earlier history or future rows enter the EMA.
6. Current drawdown60: `close[t]/max(last60 closes)−1`.
7. ATR14 divided by current close: arithmetic mean of the last14 values of
   `max(high−low, abs(high−previous_close), abs(low−previous_close))`.
8. Current range/open and close/open−1.
9. Mean of the last20 daily close/open−1 values and fraction strictly positive.
10. Same-date fixed-cohort mean5/20 returns, then the instrument's5/20 returns
    minus those respective means. Context includes only instruments with complete
    eligible lookbacks that date and requires at least80% of the fixed snapshot
    cohort. These are current-cohort retrospective context, not a historical NSE
    peer universe, index reconstruction or frozen momentum replacement.

The count is20: four returns, two SDs, two MA distances, RSI, MACD, drawdown,
ATR, range, OC, OC mean, positive fraction, two cohort means and two differences.
Features are not changed in response to historical evaluation results.

Primary outcome: exact provider-decimal `close[t+5]/open[t+1]−1`, converted to
float64 at the research boundary. Require every intervening observed slot, no
gap above seven calendar days, and no known action hazard. The binary label is
strictly positive versus nonpositive.10/20-slot outcomes use the same formula
with a different end slot and are readiness diagnostics only. Future observed
entry opens are reference prices; no prediction may use the already published
decision close as an executable entry.

Descriptive risk includes return SD, annualized volatility with an explicitly
assumed252-session year, and maximum close-price drawdown in the61-close window.
The window's current drawdown feature differs from its maximum path drawdown.
Raw volume may be displayed but enters no model formula, cross-date ratio or
nominal liquidity claim because the adjustment formula for volume is unknown.
