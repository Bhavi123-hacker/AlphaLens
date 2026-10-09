# P17 local research API verification

Baseline: 4133ac90b27ecabf27a11f19e53c33baa0d3c616; development branch
`p17-research-api`. D72 expressly authorizes P17 and supersedes historical
stop-before-P17 entries. The original DOCX remains unchanged. P18/P19 are not
started. Development acceptance never means production readiness.

## Implemented and integrated

The API has 30 versioned GET paths and two retained foundation health paths.
OpenAPI contains 32 paths, unique operations and resolvable schema references.
`/docs` redirects to the offline JSON contract; no paid service or CDN is required.
Windows Uvicorn startup and actual loopback HTTP health/OpenAPI/stock/freshness
reads passed, followed by graceful shutdown. The last evidenced session remains
2026-10-06. Archive data is explicitly stale/historical, never intraday.

Real integrations read the existing canonical Parquet, stored P6 values,
152 frozen model reports, validated P9 FOLD_TEST predictions and all 504 P10
audited backtest records. There is no estimator loading, training, fold execution,
holdout evaluation, backtest execution or current-signal generation in a handler.
The 2026 results are read from their previously evaluated records.

P15 uses the existing PostgreSQL ledger and exact FIFO reconstruction. Ordinary
P15 valuation snapshots are not durably stored in this baseline: holdings/accounting
are readable, while current market valuation and portfolio curves remain explicitly
unavailable. P16 reads existing accounts/events and reuses recovery/performance;
it cannot create an intent, process a session, fill an order or connect to a broker.
Current risk/ranking/signal/explanation outputs remain unavailable, with 503 and
reason codes. No fixture is promoted to real evidence.

All 474 unresolved P10 summaries retain null full-path economic metrics: 258
action uncertainty only, 198 actions plus price/identity gaps, 18 price/identity
gaps only. Closed-trade statistics never substitute for full-strategy results.
Benchmarks and PIT fundamentals remain unavailable.

## Verification results

| Check | Result |
|---|---|
| Focused P17 plus legacy health integration | 37 passed in 106.80s, including the original 33 P17 cases |
| P17 PostgreSQL subset | Four cases passed against actual PostgreSQL 17; disposable databases recover/read/tear down |
| P17 actual frozen research subset | Five cases passed with configured local source paths |
| Final OpenAPI response annotation verification | One targeted test passed in 3.20s; no fit repeated |
| Final Uvicorn exception-log redaction | One additional targeted test passed in 1.40s; API Ruff/format/mypy/Bandit passed |
| Complete Windows-safe regression | 595 passed / one expected production-live skip in 2263.64s; native exit 0 |
| Frozen lock check/sync | Passed; uv.lock unchanged |
| Ruff check and format | Passed; 285 Python files formatted |
| Strict mypy | Passed; 178 source files |
| Bandit, all nine application/domain packages | Passed; no findings or new suppression |
| Python dependency audit | Passed, no known vulnerabilities; nine editable workspace packages have no registry release and are disclosed audit skips |
| Git whitespace | Passed |
| Docker build and container smoke | Built successfully; non-root startup, health/OpenAPI, absent runtime uv verified |
| Strict Trivy | FAILED: 44 HIGH OS package findings, zero CRITICAL; eight CVEs, no ignore or exit-code relaxation |

The full regression uses `D:\al-tests` for the established Windows short-root
strategy and D: for logs/cache. TEST_ONLY unit estimators may be exercised by
existing software tests; none of the 152 real research fits is rerun. The real-data
integration tests verify persisted price/indicator/OOS parity, missing Muhurat
slots, all 474 null economic outcomes, classification and read-only holdout access.
CI without the local archives explicitly skips those five optional real-data
cases rather than inventing a substitute.

Full preservation verification compared 2,485 files / 8,505,278,241 bytes, with
all artifact hashes unchanged, including frozen statistical code/protocol and
the original DOCX. Inventory checksum:
`608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`.
The receipt is `p17-artifact-preservation.json`. No frozen source or model
configuration, dataset hash, threshold, fold or holdout boundary changed.

## Performance and capacity

Ordinary reads project columns and scan one security bucket with Arrow batches,
date filters, bounded pagination and validated stored ordering. Discovery uses
a 4,083,712-byte offline SQLite index, not a seven-million-row memory preload.
The small source/hash receipt is committed as
`docs/api/p17-catalog-source-manifest.json`; the SQLite data remains local-only.
Request limits default to 500 rows, offset 10,000, two concurrent persisted reads,
a cooperative 30-second read budget, 1,000 ledger/events and a 2 MB response cap.
Database connections have a three-second connect and five-second SQL timeout.
Arrow's individual I/O calls are not forcibly cancellable; this is a documented
local-service limitation, not a production latency guarantee.

Six actual local service reads per operation (first with a new service checksum
cache, then five warm; OS filesystem cache was not reset):

| Operation | First request seconds | Warm median seconds | Response bytes |
|---|---:|---:|---:|
| Stock search | 0.0220 | 0.0159 | 4,019 |
| 250-session price history | 0.1022 | 0.0672 | 125,701 |
| 250 stored SMA200 values | 0.0867 | 0.0348 | 44,658 |
| Ten model reports | 0.0164 | 0.0149 | 9,968 |

These are local adapter timings, not public-deployment load tests. See
`p17-performance.json` and `p17-windows-startup.json`.

## Failures, storage and deployment limits

An initial Windows index publication encountered an open SQLite handle; explicit
connection closure fixed the builder without changing or rescanning source data.
Stored registry names were used after correcting an early feature-name lookup.
Both corrections were covered by the successful focused suites.

C: filled during Docker verification because Docker's existing internal storage
remains there. Two small report writes failed with ENOSPC and were regenerated
from preserved D: receipts. UV tools/cache and mypy cache were moved to D: with
original-path junctions. Incoming originals and P2 raw storage were moved to D:
with original-path junctions; all 177 relocated files were individually hashed
before and after, unchanged. The virtual environment was copied to D: for a safe switch after the complete
software suite exited; every non-cache dependency file is verified before removal
of the C: copy. Regenerable bytecode is excluded from that dependency comparison. No research worker
was killed, restarted or duplicated.

The full Dockerfile built the approved patched runtime; a small local API-source
overlay verified later API changes without reinstalling dependencies. Its image
digest is recorded in `p17-container-security.json`, and an exact image archive is
retained on D:. The final OpenAPI annotation and server logging configuration changes were tested
on the host; they do not change OS/dependency layers or vulnerability findings.
The launcher now applies the existing safe formatter to Uvicorn diagnostics,
including uncaught ASGI exception text. One additional subprocess test verifies
redaction in Uvicorn's real logger configuration. The complete suite predates
this logging-only change; 595 full-suite passes plus that new case give 596
distinct passing cases, with one expected production-live skip. An initial targeted
invocation referenced a nonexistent security test filename (exit 4, zero tests);
the correct new case then passed. No full-suite or real fit was repeated. Subsequent Docker daemon
commands stalled under disk pressure; task-owned cleanup/status is tracked
separately. No shared daemon shutdown, global prune or unrelated-container cleanup
is authorized or performed. A clean full container/security gate is not claimed.

The default listener is 127.0.0.1; remote peers and foreign origins are rejected,
proxy headers are not trusted and CORS is restricted to configured loopback origins
without credentials. Logs exclude request payloads, source paths and DSNs. There
is no fake authentication. P21 is incomplete; this is not a public private-account
service. Unauthenticated public deployment is prohibited.

## Acceptance boundary

P17_DEVELOPMENT_PASSED: local read API acceptance passed. Production
readiness remains false: data rights OPEN/use NOT_CLEARED; final-vintage assumptions;
four insufficient-evidence research candidates; unresolved economic paths;
missing current decision evidence; local-only artifacts; P21 authentication pending;
44 HIGH OS findings and strict container gate failure. P18 may consume these
research-only contracts only after separate user authorization. Stop after P17.
