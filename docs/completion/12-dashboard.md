# Dashboard integration — 24 October 2026

**COMPLETE_VERIFIED** for the genuine saved-data HTTP path; final compiled browser
and restart results are recorded in the dated release report. Public/live/model
acceptance remains separate.

The existing responsive terminal is reused. `/nse-market` now adds retained-candle
search, completed-session close, absolute/percentage change, volume, dated
freshness and gainers/losers/volume leaders. These use private checksum-verified
observations, not fabricated rows, exchange-wide coverage or streaming quotes.
Changes require the preceding observed cohort slot; gaps stay unavailable.

Stock navigation defaults to saved OHLCV with candlestick/line and volume charts,
up to120 observed slots, including explicit empty slots. An explicit provider
button retains the existing private selected-stock terminal. It is disabled by
configuration in the isolated release. Saved browsing issues no provider requests.

Five-session experimental Top5/10/20 lists expose original model scores, company,
identity, observed price/date, volatility/drawdown, rationale, missing evidence and
source/model timestamps. Stale candidates are excluded. The new ordering selector
offers original scores or the registered daily-volatility penalty. It preserves
the original score, model and saved forecasts; it is not an empirically accepted
investment rule. Unsupported horizons/profit probabilities/target prices are not
manufactured.

Existing stock/model comparison, forecast-history, performance, economic research,
portfolio/watchlist and system-health components remain connected. The prospective
view deduplicates overlapping decisions and displays null accuracy for zero
qualified outcomes. Task-start/terminal-receipt mismatch now appears independently
from reservations, actual GET attempts, accepted candles and forecast publication.

The complete source archive is validated by the worker, then published as an
immutable derived price/research snapshot. Reads verify that publication's
checksum/time/dataset lineage and retain its publication timestamp. They do not
reconstruct448k source rows on every search; later sources appear after another
explicit worker publication. Captured candle coverage and the older saved
forecast observation date remain distinct.

The QA release has independent authentication/personal/operations stores and uses
genuine private research data. TEST_ONLY browser fixtures are separately labelled.
No local credential, private market response, screenshot or forecast body is
committed to the public repository.
