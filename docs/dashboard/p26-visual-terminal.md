# Historical visual terminal

P26 extends the original P18 design, themes and authenticated local application.
No broker assets, paid dependencies, trading, acquisition or model execution.

| Page | Actual visual evidence |
| --- | --- |
| Overview | Unavailable index strip, observed-session breadth donut, movers bars, dated watchlist/sparklines |
| Market Map | 250-tile treemap, date/color/volume-or-volatility size controls, favorites, keyboard-accessible table, five movers panels |
| Screener | Price/volume/session return/volatility/RSI/SMA distance/drawdown/momentum/quality/favorites filters; missing values excluded |
| Comparison | Four distinct identities; shared last-observed cutoff; raw movement/return/drawdown and stored volatility/volume-ratio/RSI/MACD curves |
| Stock | Candles/line, volume, linked crosshair/zoom/pan, custom dates, eight selectable stored overlays/panes, statistics/distribution/drawdown/raw-movement/volatility and frozen per-security OOS plots |
| ML Lab | Metrics, best-first filtered fit table, fold trajectories, OOS counts, single-fit reliability/probability bins/confusion matrix/mature-label distribution |
| Backtests | Evidence/scenario distribution, stored equity/drawdown/cash utilization/exposure, bounded closed-trade histogram/outcome counts/chronology |
| Portfolio/Paper | Recorded FIFO cost-allocation proxy/P&L/quantity, persisted paper equity/drawdown and event quantity/ID lineage; unavailable without PostgreSQL records |
| Settings | Disabled provider capability matrix; local credential presence only, never credential content |

SMA20/50/100/200, EMA12/26, RSI14, MACD/signal/histogram, ATR14, volatility20
and volume ratio use original stored P6 values. Bollinger upper/lower reconstruct
stored SMA20 ± two sample standard deviations using the original width20 contract.
This is a separate view, not a new feature definition. VWAP remains unavailable.

Risk/signal snapshots, local contributions/importance, target joins, threshold
sweeps, sectors/themes, indices/benchmarks, market-cap sizes, full-universe 52-week
counts, full economic strategy/portfolio histories and live depth/options/OI/
Greeks/intraday remain unavailable where evidence is absent. No fabricated graphs.

RELIANCE resolves to ISIN INE002A01018: latest stored close ₹1,218, 2026-10-06.
Default is 2025-10-06 through 2026-10-06; provisional 2010/2011 records remain
distinct and navigable. Selected-range high/low uses up to 252 observed slots;
this is not a complete official 52-week calendar. Raw-price curves are not total
economic returns. Missing adjacent slots break returns; cumulative movement stops
at a missing observation. Final-session missing P6 features remain null.

Observed latest-session coverage: 2,589 research-equity candidates, 2,579 comparable
returns; this is not a complete NSE universe. Browser market budget 5,000 identities,
map 250 tiles, tables 25 rows, API pages 500, stock collection 5,000, trade page 500.
Every page exposes actual dates, source/provenance and quality limitations.

The four-session cache verifies dataset identities and source fingerprints before
reuse. Every cold-read file is checksum verified. Multi-security projections are
bounded and sorted, preserving the original P17 single-security ordering contract.
Reads release the existing two-slot semaphore between partitions, with bounded
waits. Concurrent snapshots are refused; no global read-capacity increase.

ECharts remains lazy and rich pages remain separate bundles. Chart engine now
681.15 kB minified / 228.27 kB gzip; its size warning remains. No unmeasured speedup
claim. Initial cold market verification measured 30.308 seconds before partition
scheduling; the supported private query_timeout_seconds=120 can accommodate cold
reads (maximum 120). Performance receipts describe actual scope and cache state.

Authenticated read-only additions:

```text
GET /api/v1/visual/market?session=YYYY-MM-DD&limit=500&offset=0
GET /api/v1/visual/stocks/{security_id}/statistics?start=...&end=...
GET /api/v1/visual/stocks/{security_id}/bands?side=upper|lower&start=...&end=...
GET /api/v1/visual/backtests/{backtest_id}/trades?limit=500&offset=0
GET /api/v1/visual/providers
```

[P26 OpenAPI](../api/p26-openapi.json) is additive; old snapshots stay preserved.
Global P21 authentication, Host/Origin/loopback guards and response limits remain.
Only the three new SPA routes are added to the compiled shell allowlist; private
paths and unknown API routes never become HTML. Chart accessibility descriptions
retain explicit historical labels. Keyboard palette: Ctrl+K; browser watchlist
rail appears on sufficiently wide desktops. Reduced motion remains respected.

Use an existing initialized private operator configuration. Build once:

```cmd
cd /d C:\Users\Dell\AlphaLens
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p26-runtime\web-build
npm --prefix apps/web run build
scripts\windows\start-alphalens.cmd path-to-your-private-config.json
```

Set that private configuration's frontend_root to the compiled directory. Open
http://127.0.0.1:8017/login if configured port 8017. In another CMD window:

```cmd
scripts\windows\check-alphalens.cmd path-to-your-private-config.json
scripts\windows\stop-alphalens.cmd path-to-your-private-config.json
```

Actual verification uses a separate TEST_ONLY operator and copied alert store
under D:\al-research\p26-runtime\TEST_ONLY_browser_auth. Do not adopt that test
account as a real operator. P21 bootstrap and P24 backup/recovery remain unchanged.
All frozen artifacts and original alerts were independently checksum verified.
