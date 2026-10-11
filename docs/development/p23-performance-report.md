# P23 measured performance

Measured on Windows/Python 3.12 and supported Node 22.23.3, against the existing
real historical archive/catalog, genuine retained alert evidence and a separately
initialized TEST_ONLY authentication store. No model execution or backtest rerun.
Eight sequential authenticated API samples per workload (first separately from
seven warm samples), measured wall time, process CPU and payload bytes. ASGI
measurements exclude network latency; OS caches were not flushed. Small-sample
p95 is descriptive. Financial routes returned genuine 503 NOT_CONFIGURED states;
these are not successful portfolio-query benchmarks.

| Workload | Baseline warm median ms |
| --- | ---: |
| Session validation | 8.44 |
| Overview status / freshness | 27.71 / 17.23 |
| Stock search | 25.83 |
| OHLCV, 250 slots | 353.83 |
| SMA200, 250 slots | 118.22 |
| Model directory / evaluation | 79.08 / 49.66 |
| Historical OOS predictions, 20 rows | 278.19 |
| Backtest summary | 56.66 |
| Alerts / unread count | 36.60 / 35.18 |
| P19 runs / P22 status | 213.60 / 233.68 |
| Unconfigured portfolio / paper state | 24.70 / 27.77 |

Reproduce with configured existing research roots and:

```cmd
.venv\Scripts\python.exe -m scripts.benchmark_local_platform --output D:\al-research\p22-p25-runtime\api-new.json
```

The output must be a new filename. The script creates isolated TEST_ONLY account
and operations state beside that receipt; credentials are neither printed nor
persisted. Original alert evidence is read-only. First model identity selection
primes existing checksum checks before workload measurement. Dataset scope stays
6,827,699 feature rows / 46,072,188 preserved OOS rows / 152 fits / 504 backtests;
each HTTP response is bounded and is not an archive-wide throughput measurement.

A bounded parsed-metadata cache and shared monitoring reader were evaluated.
They did not produce reliable gains (models 79.08 -> 82.32 ms, operations 233.68
-> 242.70 ms). Both optimizations were reverted. Existing checksum/lineage,
availability and classification checks remain intact. No private response cache
was introduced. One monitoring reason was corrected for an unreadable directory.

## Retained frontend improvement

ECharts/core was already modular. The remaining 588.20-kB / 197.70-kB-gzip shared
chart engine was being downloaded by Market Explorer and the Backtests directory,
even though neither initial screen rendered a chart. `Chart` now loads the same
engine asynchronously only when a chart renders, with an accessible Suspense
placeholder. Chart disposal, resize, themes, reduced motion and options remain
unchanged. The chunk-size warning remains honest: chart-heavy pages still need
the engine. Total chart functionality was not removed or severity policies altered.

Actual Chromium, compiled Vite preview, fresh browser contexts, genuine login:

| Route | Before JS bytes | After JS bytes | Before ready ms | After ready ms |
| --- | ---: | ---: | ---: | ---: |
| Market Explorer | 1,056,178 | 467,208 | 449.47 | 373.91 |
| Backtests directory | 1,047,434 | 458,464 | 643.50 | 464.37 |

Both routes stopped downloading the 588-kB engine until needed. Two first-load
timings are descriptive, not statistical latency claims. Browser resource sizes
are decoded bytes; actual network compression depends on local serving. Backend
observed working set 151,420,928 bytes, peak 219,394,048 bytes and cumulative CPU
3.765625 s after the bounded browser reads (not a full-universe worker benchmark).

Receipts under `D:/al-research/p22-p25-runtime`: `api-before.json`,
`api-after.json` (rejected optimization), `browser-before.json`,
`browser-after.json`, `web-before-correct.log`, `web-after.log`,
`p23-regression.xml` and actual chart browser report. The rejected-cache tests
were removed with that implementation; 29 retained P17/P22 cases in the 31-case
experimental run passed. TypeScript/build and strict mypy passed. Final combined
browser/security checks will verify the retained chart behavior again in P25.

P19/P20 retain bounded lookback, batch sizes, concurrency, immutable checkpoints
and idempotent cursors. No historical recomputation, model reload optimization or
full-universe worker speed claim was necessary or made.
