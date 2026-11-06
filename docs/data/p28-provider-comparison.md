# P27/P28 free NSE provider decision

Verified/reviewed 2026-10-12. Operator confirms Upstox UNDER REVIEW and no provider
has yet supplied verified permission for all intended automation, retention, ML
and public derived-data display. No subscription, signup, KYC submission, order,
Yahoo price request, new bulk TejHQ acquisition or scheduled job was performed.

**Live source selected: none. Conditional first candidate: Upstox read-only Analytics.**
INDstocks is a promising batching alternative, not an approved substitute.
Free software/API pricing does not clear exchange data rights or account eligibility.

| Source | Free access / account | NSE and historical evidence | Candles / quotes per call | Limits | Decision / blocker |
|---|---|---|---|---|---|
| Upstox | Analytics free; existing account under review; token absent | Documented NSE_EQ ISIN master and V3 daily history from Jan 2000; max 10-year request window; no genuine candles tested | 1 / 500 | Standard 50/s, 500/min, 2,000/30min; daily quota not established | SOURCE_CONDITIONALLY_SUPPORTED: active entitlement, token, permission and evidence needed |
| INDstocks | FAQ free API; brokerage account + completed KYC; no account action performed | Documented NSE cash OHLCV; 1day window up to one year per call, not total history depth | 5 / 1,000 | Data/quotes 5/s and 100,000/day; other windows unknown | SOURCE_CONDITIONALLY_SUPPORTED: no token/account, rights and quality not verified |
| Angel One | FAQ describes free SmartAPI including history; account/auth entitlement required | NSE history/quote interfaces documented; current docs returned unauthorized; history depth/window not confirmed | 1 / 50 | Indexed history 3/s, 180/min, 5,000/hour; quote narrative/table conflict requires confirmation | SOURCE_NOT_CLEARED: current docs/auth/terms unresolved |
| Alpha Vantage | Existing Windows-protected key; standard free 25/day | One SYMBOL_SEARCH RELIANCE request returned RELIANCE.BSE India/Bombay; no NSE proof and no price sessions acquired | NSE not established | 25/day; all external usage and actual remainder unknown | SOURCE_NOT_CLEARED: valid search credential is not NSE or research-use clearance |
| Yahoo / yfinance | Free Apache-2.0 wrapper; data permissions separate | .NS versus .BO mapping, history/download interfaces reviewed offline; no authorized Yahoo observation obtained | Permitted batching/quota unknown | No verified authorized quota | SOURCE_NOT_CLEARED: unofficial access is not automation/retention permission |
| TejHQ | Existing pinned noncommercial historical authorization only | Genuine frozen archive ends 2026-10-06; prior status advertised Oct9, not acquired or validated | Snapshot design, completeness/rate limits unverified | Unknown | SOURCE_CONDITIONALLY_SUPPORTED ongoing; archive RESEARCH_ONLY remains preserved |

## Official evidence and actual checks

* Upstox [Analytics Token](https://upstox.com/developer/api-documentation/analytics-token/):
  one-year, read-only GET, no trading operations; market/history calls need no static IP.
  [V3 history](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/),
  [instruments](https://upstox.com/developer/api-documentation/instruments/),
  [rates](https://upstox.com/developer/api-documentation/rate-limiting/),
  [full quotes V3](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/).
  Current BOD master is not historical membership. Instrument type EQ does not prove
  equity series EQ. Daily candle timestamp is open time, not publication time.
  No complete retention/ML/public-display grant was verified. NSE segment/account
  eligibility must be confirmed after activation; software cannot activate it.
* INDstocks [FAQ](https://api-docs.indstocks.com/faq/),
  [conventions](https://api-docs.indstocks.com/conventions/),
  [history](https://api-docs.indstocks.com/historicalData/),
  [quotes](https://api-docs.indstocks.com/MarketQuote/),
  [official developer home](https://api-docs.indstocks.com/).
  Request window uses epoch milliseconds; returned ts uses epoch seconds at candle
  open. Missing requested keys indicate missing coverage. One-year cap can silently
  truncate a wider window, so completeness must be checked. Token lifetime is
  documented as 24h; no real authentication tested. No complete data-use grant verified.
* Angel [official FAQ](https://smartapi.angelone.in/faq) and
  [docs](https://smartapi.angelone.in/docs). Documentation access was not bypassed.
  Prepared 31-day offline window is an internal conservative limit, not a verified
  provider historical-window contract. Authentication/session requirements and
  exact current quote limits remain unresolved. No real credentials were requested.
* Alpha [documentation](https://www.alphavantage.co/documentation/),
  [free allowance](https://www.alphavantage.co/support/),
  [terms](https://www.alphavantage.co/terms_of_service/).
  See [sanitized credential/source decision](alpha-vantage-provider-decision.md).
  Exactly one successful authenticated metadata request at
  2026-10-12T05:13:06.585056+00:00; zero price downloads. No speculative NSE alias calls.
  Credential Manager import/readback succeeded; original plaintext was preserved.
  Private/noncommercial terms do not establish actual NSE coverage or our entire
  retention/ML/public-display scope. No paid tier or educational exemption assumed.
* Yahoo [yfinance](https://github.com/ranaroussi/yfinance),
  [history implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py),
  [batching implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/multi.py),
  [Indian wrapper](https://github.com/0xramm/Indian-Stock-Market-API).
  yfinance's software license is Apache-2.0 with personal-use/data-rights warnings.
  The Indian wrapper About text says Flask while current code is JavaScript/
  Cloudflare; root LICENSE was absent despite an MIT claim. No code was copied.
  Useful ideas: batching, formatting separate from ingestion, exchange-explicit IDs.
  Reject its .NS/.BO-collapsing search deduplication and bare-symbol exchange assumption.
  Cookie/crumb, browser impersonation and NSE autocomplete paths were not executed.
* TejHQ [docs](https://tejhq.dev/docs), [repository](https://github.com/tejhq/tej-bazaar),
  [dataset](https://huggingface.co/datasets/tejhq/indian-markets).
  Earlier P19/final-completion reports are reused. MIT software/dataset labels do not
  resolve ongoing upstream rights, publication/revision clocks, corporate actions,
  complete calendar or historical identity evidence. Prior HEAD/status responses
  establish availability claims only, not validated session coverage.
  [NSE terms](https://www.nseindia.com/static/nse-terms-of-use) remain relevant;
  publicly accessible exchange URLs do not authorize automated extraction/retention.

All providers retain unresolved corporate-action completeness, revision tracking,
price-adjustment semantics and long-term reliability for this deployment. Upstox
and INDstocks have documented current identifier designs, not verified historical
universe reconstruction. No actual NSE security count/new session is claimed.

## Rate-only daily capacity estimates

One new daily candle per instrument, known documented batching, zero network
latency, no master/status/retry/correction overhead. These are mathematical lower
bounds, not measured ingestion throughput. 2,589 is the latest archived research
cohort proxy; full current supported NSE universe size remains unknown.

| Provider | 50 instruments | 500 instruments | 2,589 archived proxy |
|---|---|---|---|
| Upstox | 50 calls / >=1s | 500 / >=10s | 2,589 / >=1,861.78s including rolling windows |
| INDstocks | 10 / >=2s | 100 / >=20s | 518 / >=103.6s |
| Angel history (conditional limits) | 50 / >=16.667s | 500 / >=166.667s | 2,589 / >=863s |
| Alpha | Hypothetical 50 requests exceeds 25/day; NSE unestablished | Exceeds quota | Exceeds quota |
| Yahoo / TejHQ | Not established | Not established | Not established |

No quotes are substituted for daily EOD candles. A successful single-instrument
request would not establish full-market coverage, special-session completeness,
adjustment equivalence or sustainable daily operation.

## Permission inquiry prepared for operator review (not sent)

Please confirm whether our zero-subscription local research use may automatically
retrieve NSE cash-equity daily observations, retain original data indefinitely,
compute technical features, perform private ML inference and store forecasts,
and display derived research in (a) an authenticated local app and (b) a public demo.
Please identify permitted instrument/universe scope, applicable upstream exchange
license, quotas, revision/corporate-action/adjustment conventions and attribution/
redistribution limits. Public display must be assessed separately from private use.

After Upstox approval: verify NSE cash entitlement; generate only the free read-only
Analytics Token; import via hidden local prompt; retain generation/expiry evidence;
obtain applicable permissions; authorize a bounded genuine technical test. Then
validate ISIN/series, raw basis, clocks, complete session and actions before changing
source gates. Scheduling needs a separate explicit activation decision. Models
and ranking also retain independent acceptance gates. No API token alone clears them.
