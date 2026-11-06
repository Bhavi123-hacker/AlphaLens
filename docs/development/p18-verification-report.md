# P18 dashboard acceptance — 2026-10-09

**P18_DEVELOPMENT_PASSED. PRODUCTION_READY = false.** P18 presents the existing
GET-only P17 research evidence; P19 has not started. Baseline is
`4c768cf62b6c20d8eceaa493d662f56595ae6eb7`; delivery branch is `p18-dashboard`.
The user-approved D73 scope supersedes historical frontend deferrals only.

## Delivered application and actual integration

React/TypeScript, Vite, Tailwind, React Router, TanStack Query, modular Apache
ECharts and Lucide provide ten working routes: Overview, Market Explorer, Stock
Analysis, ML Research Lab, Opportunities & Signals, Portfolio Analytics, Paper
Trading, Backtesting, Data Health and Settings. The default navy/cyan design has
desktop sidebar collapse, mobile navigation, dark/light themes, keyboard search,
browser-local favorites, reduced motion and accessible evidence panels.

The typed client is generated offline from P17's unchanged OpenAPI, with runtime
validation of domain JSON. Application requests are GET-only and same-origin;
loopback proxy/servers, cancellation, 40-second reads, two concurrent requests,
bounded retries and explicit HTTP errors preserve P17 restrictions. Local reads
are attempted even when the browser reports Internet disconnection; failure is
reported from the actual loopback request rather than silently pausing forever.

| Integration | Verified outcome |
| --- | --- |
| Discovery and identity | Actual RELIANCE search retains different provisional/ISIN IDs; `tejhq:isin:INE002A01018` opens its own record |
| OHLCV | Actual candlestick/line and volume series, session crosshair, zoom/pan, date filters and null calendar slots |
| Stored features | Genuine P6 SMA200 and RSI14 displayed; SMA/EMA/MACD/ATR/volatility/volume/Bollinger context use registered stored values |
| Missing session | 2023-11-12 remains an evidenced calendar slot with five unavailable OHLCV fields; no fills or zeros |
| Research reports | All 152 persisted fits are readable; development, 2025 confirmation and previously evaluated 2026 holdout remain distinct |
| Predictions | Explicit model/security-scoped read displays genuine checksum-verified P9 FOLD_TEST rows, capped at 100; no fitting or live forecasting |
| Backtests | All 504 stored metadata records and an existing detail/performance response are readable; 474 unresolved paths keep unavailable metrics |
| Current opportunities | Actual unavailable API responses are displayed; seven signal definitions are reference material only |
| Portfolio and paper | Default no-database responses are honest 503 states; isolated PostgreSQL tests verify existing P15/P16 read adapters and replay |
| Health and freshness | P17 liveness/readiness and actual 2026-10-06 evidence date are exposed independently of production readiness |

Portfolio/paper browser acceptance covers the real missing-database deployment,
not invented accounts. Connected empty/holdings cases additionally have visibly
TEST_ONLY component coverage. No browser write or execution control exists.
Missing valuation/history, benchmark and PIT fundamentals stay unavailable.
The audit partitions remain 258 action-only, 198 mixed action/price-identity,
18 price-identity-only unresolved backtests. Closed-trade statistics are never
converted into complete strategy returns. Four selected research candidates
retain `REAL_RESEARCH_INSUFFICIENT_EVIDENCE`.

## Fresh verification

| Check | Result |
| --- | --- |
| Frozen frontend installation | Separate D-drive `npm ci --no-fund`: 286 installed packages; lock SHA256 matches source |
| Frontend unit/component tests | 40 passed, three files; final JSON receipt confirms all 40 |
| Real Chromium integration | Four passed, 30.2 seconds; no intercepted/synthetic market responses |
| Browser runtime | Zero JavaScript page errors across all four scenarios |
| Automated accessibility | Zero axe WCAG A/AA findings on inspected desktop stock and mobile research pages; this is not a whole-application accessibility certification |
| TypeScript / ESLint | Passed |
| Production build | Passed; modular chart chunk 588.20 kB / 197.70 kB gzip retains Vite's size advisory |
| npm dependency audit | Zero vulnerabilities; free/open-source license texts retained |
| Fresh backend compatibility | 34 passed, 109.10 seconds, including actual frozen-artifact/API reads |
| Fresh PostgreSQL regression | Four passed, 31.74 seconds; PostgreSQL 17.11, isolated persistence/read/replay and disposable teardown |
| API Ruff / format | Passed, 15 files |
| mypy | Passed, 178 source files |
| API Bandit | Passed |
| Existing Python lock | `uv lock --check` passed; unchanged lock and dependencies |
| OpenAPI | Existing frozen schema retained; frontend client regenerated successfully |
| Git whitespace | `git diff --check` passed before delivery |

The existing full P17 suite is prior evidence: 595 passed/one expected live skip
plus its later log-redaction case. It was **not rerun** for frontend-only changes.
No real-data fit, evaluation, candidate selection, holdout evaluation or backtest
was rerun. No Docker build/Trivy rerun is claimed: the backend image and its strict
security workflow are unchanged. A separate frontend workflow verifies lock,
contracts, licenses, types, lint, unit tests, build and dependency audit.

Earlier browser checks exposed ambiguous ticker selection, a keyboard-inaccessible
scroll region and offline query pausing. The final scenarios select stable ISIN
identity, use focusable scroll regions and report actual loopback outcomes; all
four final scenarios pass. Earlier dependency/toolchain incompatibilities were
resolved with pinned TypeScript 5.9.3 and Node 22.23.3, without force/legacy peer
installation or security suppression.

## Visual and performance evidence

Actual Chromium screenshots were inspected for chart scales, date controls,
indicator panes, numerical tables, legends and mobile navigation. Desktop stock,
research, overview and backtest screenshots plus a 390×844 mobile research capture
are local in `D:\al-research\p18-runtime\browser-results`. The two retained
research screenshots show derived existing metrics, not raw market-data files:
[desktop](../frontend/screenshots/research-desktop.png),
[mobile](../frontend/screenshots/research-mobile.png).

The mobile root has no horizontal overflow; wide evidence tables scroll inside
keyboard-focusable containers. Real missing price/indicator slots remain gaps.
Model comparison bars include zero, with bounded probability scales, so near-chance
balanced accuracy is not visually exaggerated. Large tables remain deliberately
scrollable; a mobile handset cannot show every metric column simultaneously.

Charts collect at most 5,000 security-session slots, 500 per request; explicit
truncation is shown. Metadata uses bounded pages, predictions are opt-in and
there is no interval/focus-triggered mass refetch. Pages/charts are lazy loaded.
The 588 kB chart chunk advisory is retained; there is no public-deployment or
cross-machine latency/load-test claim. Fonts and licenses are served locally.

## Frozen baseline preservation

The preservation receipt records a full SHA256 check of **2,485 existing files /
8,505,278,241 bytes**, matching the approved inventory
`608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`.
Fourteen protected source/report files were compared with P17, including the
original DOCX, Python lock, dataset identity, model/evaluation/backtest reports,
statistical code, OpenAPI and existing strict CI workflow. All match. Main remains
`9fa82284936f8b7a34f5409ba25cdce3538747b6`.
See [machine-readable preservation receipt](p18-artifact-preservation.json).

The 152 fits, 504 backtests, 46,072,188 OOS predictions, frozen source hashes,
training protocol, confirmation/holdout boundaries and P11–P14 policies remain
unchanged. Data and model files are not committed or bundled. D-drive dependencies,
builds, browser downloads and caches preserve existing research junctions.

## Restrictions and next phase

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION remain explicit. P1 clearance is OPEN and
production market-data use NOT_CLEARED. P21 authentication is absent; loopback
research development is mandatory. The 44 HIGH OS container findings are neither
waived nor relabeled. No broker, automatic refresh or production champion exists.

P18 is ready for user review and a separate decision about P19 development.
Production readiness remains blocked. Exact Windows CMD startup and verification
commands are in [the frontend guide](../frontend/p18-dashboard.md).
STOP after P18.
