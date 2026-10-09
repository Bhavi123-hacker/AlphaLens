# P18 local research dashboard

P18 is the React/TypeScript presentation layer over the GET-only P17 API. It
does not own financial accounting, features, model fitting, signal transitions
or execution. The user-approved D73 scope supersedes the historical P18 deferral
only; P19 and later phases are not authorized.

## Architecture and design

`apps/web/src/App.tsx` provides ten routed workspaces and a collapsible desktop
sidebar, mobile navigation, global identity search and evidence-date header.
Pages are lazy loaded. Reusable panels, status badges, skeletons, dialogs and
evidence details live in `components/`. `api/generated.ts` is generated from the
committed P17 OpenAPI document; `api/contracts.ts` additionally validates the
variable JSON payloads that OpenAPI deliberately leaves domain-specific.

React Router owns URLs. TanStack Query deduplicates and caches persisted reads;
there is no interval polling or focus-triggered mass refetch. Queries use
AbortSignal cancellation and a two-request queue. Transient errors get at most
one retry; evidentiary HTTP 503 failures are not retried into invented success.
The proxy target is restricted to an unauthenticated loopback HTTP origin.
No database credentials or local artifact paths enter frontend configuration.

CSS theme tokens define navy/charcoal surfaces, cyan accents, restrained green/red
financial directions and amber evidence warnings. Inter and JetBrains Mono are
self-hosted open fonts. Light theme, compact tables and up to 100 favorites are
browser-local presentation preferences; they are not server portfolio records.
Motion uses brief CSS transitions and respects reduced-motion preferences.
Keyboard search, semantic tables, native modal dialogs, visible focus and a skip
link support accessibility. Dense tables scroll within their own containers.

## Route and integration map

| Page | P17 reads | Availability semantics |
| --- | --- | --- |
| Overview `/` | health, freshness, stocks, models, evaluation, portfolios | A useful historical workspace even without PostgreSQL; no invented security total |
| Explorer `/market` | stocks | Search symbol/name/ISIN, stable-ID sorting, 25-row pages; distinct identities retained |
| Analysis `/analysis`, `/stocks/:security_id` | stock detail, history, indicators | Genuine OHLCV and stored P6 values; null prices and warm-up values stay gaps |
| Research `/research` | models, model detail, evaluation, scoped predictions | Separate development/2025/2026; predictions only on explicit bounded request |
| Opportunities `/opportunities` | opportunities, rankings, signals, security explanation | Actual 503 evidence restrictions; state definitions are reference only |
| Portfolios `/portfolios` | portfolios, metadata, holdings, transactions, performance | Exact P15 FIFO records or missing-DB/empty state; unavailable valuations stay null |
| Paper `/paper` | accounts, metadata, orders, trades, performance | Read-only simulated records; no placement or execution controls |
| Backtests `/backtests` | backtests, detail, performance | Original P10 metrics and audit causes; closed trades are not full-strategy returns |
| Data health `/data-health` | health, ready, status, freshness | Liveness and research readiness distinct from production readiness |
| Settings `/settings` | no financial writes | Browser-local appearance/favorites and safe connection explanation |

The application always preserves returned source, session, class, quality,
artifact/version and missing reasons. Exact decimal and rational strings are
retained in tables. Graphic-only conversion rounds to four decimals using BigInt
and rejects unsafe magnitude, zero denominators and values that would falsely
round to zero. Chart rendering is approximate display, never financial accounting.

## Chart and resource contracts

ECharts renders candlesticks or a close line with volume, linked crosshairs,
inside/slider zoom, panning, ResizeObserver sizing and separate indicator panes.
Session axes use literal ISO dates, avoiding timezone drift. Missing calendar
observations remain explicit chart slots; lines use `connectNulls: false`.
No forward/back-fill, price interpolation or alternative indicator formula exists.

SMA20/50/100/200, EMA12/26, RSI14, MACD/signal/histogram, ATR14, volatility20,
volume ratio20 and Bollinger location/width controls refer to actual registered
P6 names. Bollinger price bands are not fabricated from location/width features.
At most four selected feature series are read concurrently through the global
two-read queue. Feature versions/formulas/units remain in returned evidence.
Ranges use the security's last observed date, not a live market clock.

Ordinary requests use 1–500 API rows and existing date/offset bounds. A single
security's chart collection stops at 5,000 session slots and explicitly marks
truncation. The 152 model reports fit one 500-row request; 504 backtest metadata
rows require two pages. Equity pages are limited to 500; prediction inspection is
limited to 100. No whole NSE/OOS dataset or estimator is loaded into the browser.

All 474 unresolved backtests retain unavailable full-path economic metrics.
Cause counts are derived from the actual returned audit rows: action uncertainty,
mixed action/price-identity gaps and price-identity gaps. Partial evidenced equity
pages are labeled partial and retain nulls. No full-strategy return is calculated
from closed-trade diagnostics. Benchmark comparison and PIT fundamentals remain
unavailable. Candidate selections are read-only and retain insufficient evidence.

## Local Windows CMD startup

Use the existing D-drive layout and prepared P17 discovery index. The commands
below use port 8017 to avoid the unrelated shared listener on 8000. No shared
service is interrupted. Do not rebuild the catalog, train or reevaluate models.

Backend CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_RESEARCH_DATA_ROOT=D:\al-research\tejhq-final-vintage-v1-r3
set ALPHALENS_RESEARCH_RUN_ROOT=D:\al-research\tejhq-research-evaluation-v2-fit-parallel
set ALPHALENS_RESEARCH_REPORT_ROOT=C:\Users\Dell\AlphaLens\docs
set ALPHALENS_CATALOG_PATH=D:\al-research\p17-api\discovery.sqlite
set ALPHALENS_ENVIRONMENT=development
set ALPHALENS_TEST_ONLY_EVIDENCE=false
set ALPHALENS_PORT=8017
.venv\Scripts\python.exe -m alphalens_api serve
```

Frontend CMD window, using the checksum-verified portable Node 22 installation:

```cmd
cd /d C:\Users\Dell\AlphaLens\apps\web
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set npm_config_cache=D:\alphalens-npm-cache
set TEMP=D:\al-research\p18-runtime\temp
set TMP=%TEMP%
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-local.ps1 -NodeExecutable D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe
set ALPHALENS_API_PROXY_TARGET=http://127.0.0.1:8017
set ALPHALENS_WEB_CACHE_DIR=D:\al-research\p18-runtime\vite-cache
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p18-runtime\build
npm run dev
```

Open and check from a third CMD window:

```cmd
start "" http://127.0.0.1:5173
curl.exe -f http://127.0.0.1:8017/api/v1/health
curl.exe -f http://127.0.0.1:5173/api/v1/health
curl.exe "http://127.0.0.1:5173/api/v1/stocks?q=RELIANCE&limit=10"
```

Run frontend verification from the frontend CMD environment above:

```cmd
npm run typecheck
npm run lint
npm test
npm audit
npm run build
set PLAYWRIGHT_BROWSERS_PATH=D:\al-research\p18-runtime\browsers
set ALPHALENS_BROWSER_OUTPUT_DIR=D:\al-research\p18-runtime\browser-results
set ALPHALENS_BROWSER_REPORT=D:\al-research\p18-runtime\browser-report.json
npx playwright install chromium --no-shell
npm run test:browser
```

Browser tests require both running local services and actual persisted P17 data.
Unit fixtures are visibly TEST_ONLY and are never used as application fallback.
If a usable Node 22.23.3 or later within Node 22 is installed elsewhere, pass its executable to setup-local
and update the process PATH. All source configuration is path-independent.
For ordinary installations with adequate space, `npm ci` in `apps/web` can be
used without the D-drive junction. Preserve existing dependency ownership.

## Security and limitations

Local development only: loopback listeners, restricted frontend origins, no fake
authentication, paid service, broker integration, public tunnel or deployment.
P21 is incomplete; private financial records must not be exposed publicly.
Backend artifact roots remain local-only deployment requirements. Vite filesystem
serving is restricted to the web app/dependencies and denies private/data formats.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION,
P1 OPEN and production use NOT_CLEARED remain unchanged. The existing 44 HIGH
container findings and strict Trivy gate remain unresolved; this frontend does
not change the container image or claim production security. No frozen model,
dataset, holdout, accounting or calibrated policy is modified.

Actual acceptance evidence is recorded in
`docs/development/p18-verification-report.md`; a passing build alone is not P18
acceptance. STOP after P18; P19 requires a separate user decision.
