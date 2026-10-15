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

The final refreshed official master contains **2,697 verified NSE_EQ/type-EQ identities**
(15 October morning; the earlier overnight master contained 2,701).
All are searchable by company, ticker, ISIN/key and paginated server-side. That is
identity availability, not 2,697 tested quote entitlements or complete historical
common-equity/ML eligibility. Six independent stocks were tested through the real
compiled private application. Historical/ML eligibility is separate and current
eligible ML prediction count is **zero**.

| Tested stock | Verified current ISIN | Latest returned provider daily candle |
| --- | --- | --- |
| RELIANCE | INE002A01018 |14October2026 |
| BAJFINANCE | INE296A01032 |14October2026 |
| TCS | INE467B01029 |14October2026 |
| INFY | INE009A01021 |14October2026 |
| HDFCBANK | INE040A01034 |14October2026 |
| ICICIBANK | INE090A01021 |14October2026 |

Instrument keys are `NSE_EQ|` plus the verified master ISIN, validated with symbol,
segment, exchange and EQ type. Archive mapping requires unique latest dated ISIN
and symbol, rejecting missing/conflicting aliases. A single bounded SQLite read
now maps a page, replacing100separate searches. No company-name identity inference.

Full Quote V3, OHLC V3, official daily historical candles and scheduled NSE timings
return genuine responses. Earlier accepted quote generation was **15 October
04:40:55.018 IST** for RELIANCE/BAJFINANCE/TCS and **04:41:15.407 IST** for
INFY/HDFCBANK/ICICIBANK. All six passed the unchanged timestamp checks. BAJFINANCE's
last trade was **14 October 15:55:02.905 IST**; a newly generated snapshot is not a
new-session trade. Its generation preceded receipt by 0.036097 seconds. Today's
quote snapshot was available at that check; today's trade or EOD is not claimed.
An earlier 04:36:22.774 IST sample was 1.901308 seconds ahead of receipt and was
rejected. No tolerance, system-clock change or validation weakening was introduced
to turn that rejection into success. ICICIBANK's 14 October candle also appeared
in the later check, superseding its earlier 13 October result.
The final six-symbol compiled-browser run returned **14 October daily candles for
all six symbols**. RELIANCE/BAJFINANCE/TCS accepted quote generation was **15 October
08:20:36.970 IST**, received 0.598654 seconds later. INFY/HDFCBANK/ICICIBANK quote
generation **08:20:43.587 IST** was 0.081748 seconds ahead of receipt, correctly
rejected without exposing LTP; those views used explicitly dated provider candles.
The run used 11 bounded snapshot-provider GETs, and the six-stock quote watchlist
then reused memory without additional provider calls. Same-day 15 October EOD remains
unavailable at this pre-session check. Independently verified official final close
and provider corporate-action/adjustment compatibility remain unverified.

Accepted changes use exact LTP minus documented `prev_close_price`, with percentage
against that same field. EOD change uses the preceding returned candle and names
that basis; it is not silently a verified previous exchange session. Current and
previous OHLC are separate. Future/malformed/naive timestamps cannot expose LTP.
Final P32 real-browser regression assertions verify header equality with the identical backend
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

Final warm-index pagination: 2,697 unique identities, 100/page, 26 timed HTTP pages
after warming the first page, **0.574 seconds total, 21.545 ms median, 25.434 ms
maximum**, maximum 51,476 response bytes. The earlier 2,701-identity run measured
0.580 seconds/20.915 ms median/25.992 ms maximum.
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
after range correction. Combined regression subsequently passed14cases with one
PostgreSQL browser case failing because its old global setup session was revoked
by the existing active-session cap after many genuine logins. That case now obtains
its own real session; the focused rerun passed3.7seconds. Thus15distinct final
private browser cases passed across documented runs, not one clean15-case run.
Published synthetic demo:
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

The earlier broad/history TruffleHog failure remains recorded; the final push-range
scan passes and does not establish a clean full-history scan. Final strict Trivy
still fails with 44 HIGH instances/eight CVEs/zero CRITICAL. No scanner suppression
or history rewrite is applied. Exact CI outcomes and native deployment proof follow.

## Delivery checkpoint

Implementation committed and pushed as `9d573a0eea1ebf92248cad49d4d15fba340e4c64`.
Initial frontend CI [38652753852](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38652753852)
passed. Initial foundation CI
[38652753839](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38652753839)
passed Python/PostgreSQL and dependency gates, failed the history scanner and
skipped subsequent container steps. These are not reported as a successful run.

The normal app on **http://127.0.0.1:8017/login** now runs P32 compiled UI and
backend with the original operator roots. Served index SHA256 is
`02a0107eb0198d2ee2238f7a08cb9155a5057a81be1d7660b0cc731b5ed044ac`.
Anonymous personal/provider reads return401; all new native page routes serve the
same compiled index. Original personal sidecar has zero portfolios, watchlists,
journal entries and rules, and no assumed budget. Test records stay on the isolated
8029 operator. No original operator password reset or password-based re-login was
performed; actual login/logout was verified with the isolated genuine account.
Original PostgreSQL15430 remains reachable and original47alerts remain unchanged.

Screenshot files are local and ignored under
`.local-data/p32-browser-runtime/final-regression/`: `provider-1600-redacted.png`,
`provider-1366-redacted.png`, `provider-390-redacted.png`, `archive-desktop.png`,
`historical-leaders.png`, `TEST_ONLY-portfolio-redacted.png` and opportunity views.
Provider values and canvas are masked, rather than retained in screenshots.

Packaging review added the personal worker and its SQL DDL to the existing
explicit Docker COPY list. No base image, dependency pin, scanner or security
threshold changed. Local Docker daemon is unavailable; no new local image build
or fresh Trivy pass is claimed. A native deployment verifier initially called the
wrong store listing method; corrected helper now passes and records the actual
served hash and original/test workspace isolation.

## Final continuation and independently executed container gate

Packaging/verifier correction committed and pushed as
`222728416c9b5e5c63663b7dc7c87990c4ec270e`. The container is now a separate required
job, so an earlier scanner failure cannot prevent its build/runtime/security checks.
The strict scanner settings and failure exit code remain unchanged.

- [Final frontend CI 38672535684](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38672535684)
  passed typecheck, lint, 85 tests, production/demo builds, demo browser and audit.
- [Final foundation CI 38672535585](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38672535585):
  quality passed, **984 passed/eight skipped in 282.49 seconds** on real Linux/
  PostgreSQL 17; frozen lock/sync, Ruff, mypy, Bandit and audit passed. Unchanged
  push-range TruffleHog found zero verified/unverified secrets (seven chunks/723
  bytes); this does not erase the earlier broad/history findings.
- Actual Linux container build, personal-worker/SQL imports, non-root/build-tool
  boundary and authentication smoke passed. **Strict Trivy failed: 44 HIGH
  instances, eight distinct CVEs, zero CRITICAL**, confirmed from its downloaded
  JSON artifact. Overall foundation conclusion remains FAILED; no waiver.
- Renewed local targeted P32 backend: **24 passed in 8.90 seconds**. Repository
  Ruff/format passed (507 files). A helper formatting failure was corrected before
  push. The first local pytest invocation lacked the required short temp-root
  variable and did not run tests; the corrected invocation passed.
- Renewed frontend: **85 passed/14 files in 18.56 seconds**, TypeScript passed.
  The first fully parallel run had three 5-second timeouts/82 passes under local
  load; rerunning with two workers passed without changing test timeouts/assertions.
- Actual compiled personalized journey: **eight passed in 52.1 seconds**. The
  first launch lacked the existing D-drive Chromium path and ran no browser cases;
  setting PLAYWRIGHT_BROWSERS_PATH to the existing installation resolved it.
  Separate original terminal/PostgreSQL browser regression: **seven passed in
  22.2 seconds**. Thus all 15 cases passed across these two clean runs.
- Published synthetic public demo: **three passed in 11.3 seconds**, no publication
  or private/backend data exposure. Credentials/source/private build/demo scan:
  842 files, zero protected-value/encoding leaks. Foreign Origin rejected, real
  PostgreSQL reader SELECT-only, original financial-table counts zero.
- Fresh frozen verification from unchanged C checkout: **2,485 files,
  8,505,278,241 bytes and 47 original alerts passed in 43.379 seconds**. The D
  helper initially stopped on three JSON newline differences from the old recorded
  Windows hashes; each D file exactly matches baseline Git bytes and C matches
  recorded hashes. No normalization or frozen-file edits were made. Frozen domains,
  original DOCX, locks and public demo diff against P31 is empty.

Final sanitized source receipt: [p32-source-verification.json](p32-source-verification.json).
Updated local screenshots under `.local-data/p32-browser-runtime/continued-final/`
and `continued-regression/` include desktop/laptop/mobile terminal views, historical
leaders, opportunities and TEST_ONLY portfolio, with provider prices/canvas masked.
These are private local artifacts, not published price redistribution.

The actual native stop commands cooperatively stopped isolated test8029, original
operator8017 and the exactly owned PostgreSQL15430 service. Native start then
restores the original operator on8017 with the verified compiled build. No password
reset, existing ledger write, research rerun or unrelated process termination.
