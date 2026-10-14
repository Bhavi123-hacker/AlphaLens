# P32 NSE-wide personal research and portfolio terminal

Dedicated branch `p32-personal-research-portfolio`, from verified P31
`245fb4b531b6023b25cb5325881d0190f08f4041`, continuing P30's protected baseline.
The original C/P26 checkout is separate. No public publication or brokerage work.

## Market access and price correction

The outdated primary chart came from StockWorkspace's unconditional frozen
`/stocks/{id}/history` reads. A separate RELIANCE component could not replace the
header/chart. P31 corrected that wiring; P32 makes current-master discovery and
the same primary provider workspace available to every verified accessible key.
Nothing is restricted to RELIANCE or BAJFINANCE in production selection.

The current official master contains **2,701 verified NSE_EQ/type-EQ identities**.
All are searchable by company, ticker, ISIN/key and paginated server-side. That is
identity availability, not 2,701tested quote entitlements or complete historical
common-equity/ML eligibility. Six independent stocks were tested through the real
compiled private application. Historical/ML eligibility is separate and current
eligible ML prediction count is **zero**.

| Tested stock | Verified current ISIN | Latest returned provider daily candle |
| --- | --- | --- |
| RELIANCE | INE002A01018 |13October2026 |
| BAJFINANCE | INE296A01032 |14October2026 |
| TCS | INE467B01029 |13October2026 |
| INFY | INE009A01021 |14October2026 |
| HDFCBANK | INE040A01034 |13October2026 |
| ICICIBANK | INE090A01021 |13October2026 |

Instrument keys are `NSE_EQ|` plus the verified master ISIN, validated with symbol,
segment, exchange and EQ type. Archive mapping requires unique latest dated ISIN
and symbol, rejecting missing/conflicting aliases. A single bounded SQLite read
now maps a page, replacing100separate searches. No company-name identity inference.

Full Quote V3, OHLC V3, official daily historical candles and scheduled NSE timings
return genuine responses. At the final six-stock source check, quote generation
was15October04:36:22.774IST for RELIANCE/BAJFINANCE/TCS. BAJFINANCE's reported last
trade was14October15:55:02.905IST. Generation was1.901308seconds ahead of local
receipt and was rejected. All six quotes in that sample were rejected for clock
evidence, so **no safely accepted15October quote is claimed**. Earlier P31 genuinely
accepted a14October quote; later clock rejection does not erase that earlier fact.
The14October BAJFINANCE daily candle is published. Same-day15October EOD remains
unavailable at this overnight check. Independently verified official final close
and provider corporate-action/adjustment compatibility remain unverified.

Accepted changes use exact LTP minus documented `prev_close_price`, with percentage
against that same field. EOD change uses the preceding returned candle and names
that basis; it is not silently a verified previous exchange session. Current and
previous OHLC are separate. Future/malformed/naive timestamps cannot expose LTP.
P31 real-browser assertions verify header equality with the identical backend
snapshot after display formatting and clean canvas tooltips. No cross-source price
inconsistency is inferred. The historical October6price is independently selectable.

## Universal chart, market workspace and performance

The provider source selector precedes the main header/chart. Explicit loading shows
the latest supported provider quote or clearly dated EOD fallback. An unavailable
provider view never silently presents the frozen archive as current. Archive age
and price basis remain prominent when selected.

Large candles/line chart, volume, crosshair, zoom/pan, expanded chart, custom dates
and1M/3M/6M/1Y/3Y/5Y/ALL are available. SMA20/50/100/200, EMA12/26, RSI14, MACD,
Bollinger, ATR and daily volatility reuse eligible P6 descriptive computations.
Warm-up/missing values remain missing. Currency display has two decimals; exact
underlying values are unchanged. Observed returns/drawdown/volatility come from the
backend. ALL means all returned bounded provider observations, not unlimited history.

Dark/light theme, readable typography, top NSE autocomplete, side navigation,
watchlist rail, large chart and stock-details panel are shared private UI foundations.
New pages: Research Preferences, My Portfolio, My Watchlists & Market Screening,
Explore Opportunities, guided Research Copilot, Journal and Smart Research Alerts.
Existing market map, screener, comparison, research, Evidence Passport, Intelligence,
legacy portfolios/paper analytics, alerts and diagnostics remain available.
Retained P19 blockers are collapsed/separate from manual Upstox access. No current
index strip or full-NSE breadth is fabricated.

Named watchlists allow up to50verified identities in one explicit quote batch.
Official quote capacity is500; local candle snapshots remain up to3stocks/request.
No thousands-of-requests homepage or background universe polling. Prices are
bounded/passively expired memory, at most600seconds; no observations are retained
in a market-price database, personal records or P20 alerts. Derived views honor
the remaining source lifetime, with no expiry-triggered acquisition.

Actual warm-index pagination:2,701unique identities,100/page,27timed HTTP pages,
**0.580seconds total,20.915ms median,25.992ms maximum**, maximum51,479response bytes.
Earlier implementation measured38.158seconds/1,480.194ms median; batching archive
mapping resolved that bottleneck. Both runs requested no market observations.
A TEST_ONLY5,000identity index/pagination case also passes. Browser payloads are
paged/debounced/lazy rather than duplicating the master in every component.

Heatmap/screener and gainers/losers show the actually observed selected cohort.
Price, volume, RSI, MACD, volatility, drawdown, momentum and SMA filters exclude
missing inputs. One quote never creates indicators. Comparison includes source
dates, normalized observed price movement, drawdown, volatility and sufficient-
sample correlation; action compatibility/total economic returns stay unknown.
Broad watchlist batching is functional, but full-universe polling and verified
sector grouping are unavailable. Inactive identities require repairing the list.

## Preferences, portfolio and research

The real active P21 single-operator account owns a protected persistent SQLite
sidecar. Preferences include budget, risk/horizon, preferred/avoided sectors,
market caps, dividend/style, drawdown, stock/sector exposure, stock count, holdings
consideration and liquidity/volatility limits. Supported numeric constraints apply
consistently; unavailable sector/cap/fundamental/dividend dimensions and uncalibrated
Low/Moderate/High mappings remain explicit. Defaults infer no financial circumstances.

Manual multiple opening lots, funded purchases, partial sales and recorded cash
events reuse **unchanged P15 FIFO**. Exact accounting is retained alongside rounded
display. No broker position or implicit funding is invented. CSV has current ISIN/
symbol validation, complete sequence preview without writes, explicit confirmation,
owner/revision binding and all-or-none transaction commit. Retry is idempotent.

Browser TEST_ONLY two-lot/partial-sale case leaves3shares, exact remaining basis600
and realized FIFO gain1,585. The separate confirmed CSV case leaves6shares, basis606
and realized gain191. These are constructed accounting tests, not market activity.
Original-user portfolios remain empty; test records stay in a different operator
and sidecar. Existing PostgreSQL financial tables remain untouched.

Portfolio Intelligence exposes cost-based stock concentration, source freshness,
supported preference evidence and volatility/drawdown reviews when available.
Indicative provider marks/P&L are separately labeled, transient and unreconciled
for operator quantities/actions. Accepted portfolio economic value, bank cash,
verified sector allocation and full reconstructed portfolio drawdown remain absent.
Scenarios support adding/reducing a selected stock, uniform shocks, optional target
weights and declared cash changes with **zero ledger writes/orders**. Journal notes,
hypotheses, later outcomes and lessons can be created/edited/removed by the operator.

Historical Winners & Risk-Adjusted Leaders supports1M/3M/6M/1Y/3Y/5Y/custom
windows and six categories through explicit checksum-verified progressive scans.
Actual one-month2026-09-06to2026-10-06: **2,617observed identities,2,513comparable,
104excluded**,64partitions,5.051seconds, largest step0.150seconds. No provider calls,
model runs or source writes. The five-year scan completed64partitions/3,226identities
in43.996seconds, but **zero fully comparable series** passed strict identity and
missingness rules; all3,226were excluded. Missing windows are not populated.
The UI's month-start clamp was caught during screenshot review, corrected and
reverified with actual start/end and nonzero window metrics.

Top5/10/20 are bounded historical/descriptive research views, never current ML
predictions. Saved Historical ML Leaderboard/reliability/economic views reuse genuine
existing evidence. The474unresolved backtests remain unresolved. Guided copilot
answers link to structured source evidence and use no external model. Alerts have
13supported rule types with explicit cached-evidence checks, P20 deduplication and
no provider-price retention, background checks or outbound delivery. Missing or
clock-rejected data does not become a provider-outage claim.

## Verification, security and remaining gates

Local targeted regression329passed85.67seconds; later added outage/mapping cases
passed in focused reruns, giving331distinct targeted cases across these runs.
Final new P32 tests and original terminal/API regressions pass. This is not a full
local repository-suite claim. Frontend85tests/14files, TypeScript, zero-warning
ESLint, production build, Ruff/format, mypy296sources and Bandit passed. The existing
lazy chart chunk remains681KB with Vite's size warning; no dependency gate was relaxed.

Actual compiled browser: eight full personalized journey cases passed36.1seconds
after range correction. Subsequent combined provider/archive/auth/PostgreSQL
regression is recorded in the final delivery checkpoint. Published synthetic demo:
all three actual browser checks passed7.5seconds; no republishing occurred.
Earlier native-route omissions, remount/contrast errors, selector/encoding issues
and a wrong assumed cohort count are recorded as failures, with fixes/reruns.
One additional test assertion was initially placed in the wrong accounting test;
the focused run failed and the corrected run passed. No failed run is called passed.

Credential scan checked actual protected Upstox/AlphaVantage/PostgreSQL values and
encodings across source, private compiled assets and demo assets: zero leaks.
Private API responses are checked too; foreign Origin returns403, anonymous private
reads401 and CSRF/owner/revision violations are rejected. Original real PostgreSQL
reader remains transaction-read-only, without INSERT/UPDATE/DELETE privileges;
original accounts/transactions/paper_accounts/paper_events counts remain zero.

Read-only SHA verification passed **2,485frozen files/8,505,278,241bytes and47original
alerts**, retaining inventory hashes608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17
anddc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41.
Original DOCX, research/model/economic artifacts, financial methods, PostgreSQL
migrations, lockfiles and public demo are unchanged. New SQLite DDL is owned by db/.

Private current prices/screenshots are not committed. Final local screenshots mask
provider prices; historical archive screenshots use permitted retained source data.
Failure DOM artifacts containing possible provider observations are removed after
sanitized failure evidence is recorded. Native start/stop and rebuild commands:
[P32 Windows runbook](p32-windows-commands.md). API/data contract:
[P32 workspace contract](../api/p32-personal-workspace.md).

Outstanding: independent official close; compatible corporate actions/adjustments;
verified sectors/fundamentals/caps/indices; complete long-window historical paths;
durable provider retention/ML-use/redistribution clearance; full-market polling;
current38-feature peers/risk/universe and independent model acceptance; current ML
rankings; retained ingestion/scheduler activation; public personalized advice and
multi-user/private-public security readiness. New personal sidecar backup is manual
until it is added to configured recovery roots. Nothing authorizes trading.

GitHub's inherited strict full-history TruffleHog findings and prior strict Trivy
44HIGH/eightCVEs remain production blockers. No scanner suppression or history
rewrite is applied. Exact P32 commits, actual CI outcomes and native deployment
proof are recorded below when returned by GitHub and the running application.
