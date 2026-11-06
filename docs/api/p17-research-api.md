# P17 research-only backend

D72 authorizes a local, read-only FastAPI integration from remediation baseline
4133ac90b27ecabf27a11f19e53c33baa0d3c616. It does not authorize P18/P19, public
deployment, training, model selection, backtest execution or P11-P14 calibration.
Development acceptance and production readiness are separate gates.

The existing research archive remains REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION. It is NOT PRODUCTION PIT. P1 clearance is OPEN;
production market-data use is NOT_CLEARED. All four locked candidates retain
REAL_RESEARCH_INSUFFICIENT_EVIDENCE. No API result authorizes a real trade.

## Architecture and deployment inputs

`apps/api/src/alphalens_api` owns request validation, routers, Pydantic contracts,
application services, configuration, dependency injection and boundary errors.
`artifacts.py` reads immutable P5/P6/P9/P10 Parquet/JSON; `catalog.py` provides an
offline discovery index. `portfolio_reads.py` reads PostgreSQL and calls existing
P15 FIFO reconstruction and P16 event recovery/performance. Routers contain no
indicator, estimator, ranking, transition, order-fill or accounting formulas.

Persisted I/O endpoints are synchronous functions, executed in FastAPI's worker
pool. Health never loads an estimator. No model is deserialized at startup or
during any request. There are no write, training, refresh or execution routes.
No database migration executes during startup or a request. `db/` remains the
sole migration owner.

Configure resource locations through ALPHALENS_RESEARCH_DATA_ROOT,
ALPHALENS_RESEARCH_RUN_ROOT, ALPHALENS_RESEARCH_REPORT_ROOT and
ALPHALENS_CATALOG_PATH. Report root is the repository's `docs` directory. The
archive and binary model/OOS artifacts are local-only and absent from Git and the
container image. A cloned repository alone cannot serve prices/predictions.
Installing the existing root workspace with `uv sync --frozen` is required;
standalone installation of only the API wheel is not the supported deployment.
No dependency or frozen uv.lock modification is required.

An explicit `python -m alphalens_api build-catalog` command builds a small derived
SQLite discovery index outside both frozen roots. It scans canonical partitions
in projected 65,536-row batches, aggregating observed identity groups; it never
loads seven million rows at once or changes source bytes. The source receipt
pins index bytes, canonical identity, source dataset/revision and six small
reports. Existing output files are refused. Use a new output path when rebuilding
an index. SQLite is solely an analytical lookup cache; durable portfolio/paper
storage remains PostgreSQL. This setup command is not an HTTP write operation.

## Endpoint availability matrix

All routes use `/api/v1`. Collections have `limit` (1-500) and `offset` (0-10,000)
where applicable. Results use stable ascending identities, then sessions. No
caller-controlled sort expression, filesystem reference or SQL fragment is used.

| GET route | Implemented source | Availability and limitations |
|---|---|---|
| `/health` | Process state | Liveness only, production_ready=false |
| `/ready` | Configured read adapters and PostgreSQL schema probe | 200 only for required research read sources plus ledger schema; otherwise 503; never production readiness |
| `/system/status` | Safe component diagnostics | Missing components have reason codes; no DSN/path disclosure |
| `/system/data-freshness` | Identity-verified observed-session calendar | Last evidenced EOD date; archive is not live/intraday |
| `/stocks?q=...` | P5-derived identity catalog | Literal substring of symbol/name/ISIN/security ID; all analytical types are disclosed |
| `/stocks/{security_id}` | Observed identity groups | Dated symbol/identifier observations; not authoritative listing intervals |
| `/stocks/{security_id}/history` | Hash-verified canonical partition | Exact raw OHLCV, start/end filtering, explicit missing calendar slots |
| `/stocks/{security_id}/indicators?feature=...` | Stored P6 column and registry | Definition/version/units/quality; unavailable warm-up stays null; no target columns |
| `/research/models` | Frozen P8/P9 reports | Model/task/horizon/phase, training protocol, metrics, naive/ranking evidence |
| `/research/models/{model_id}` | Same report | Metadata only; never estimator execution |
| `/research/evaluation` | Frozen comparison report | Existing development, 2025 confirmation and once-evaluated 2026 holdout, unchanged |
| `/research/predictions` | Verified partitioned P9 FOLD_TEST files | Required model_id and security_id; stored OOS only, no live predictions or target columns |
| `/opportunities`, `/rankings`, `/signals` | No genuine persisted current outputs | Explicit UNAVAILABLE/503; no research-metric-to-signal conversion |
| `/signals/{security_id}`, `/explanations/{security_id}` | Same evidentiary gate | Known identity required; UNAVAILABLE/503, no fixture promotion |
| `/portfolios` and `/portfolios/{portfolio_id}` | PostgreSQL P15 accounts | Actual recorded metadata, or honest empty database state |
| `/portfolios/{portfolio_id}/holdings` | Existing P15 FIFO reconstruction | Quantity, lots, basis, realized P&L; current price/risk/signals unavailable without persisted evidence |
| `/portfolios/{portfolio_id}/transactions` | Immutable P15 ledger | Recorded transactions/provenance; no broker-verification claim |
| `/portfolios/{portfolio_id}/performance` | P15 accounting | Partial: accounting available; full valuation/history null because ordinary P15 valuations are not persisted here |
| `/paper/accounts` and `/paper/accounts/{account_id}` | PostgreSQL P16 | Actual simulated accounts and recovered state, never real execution |
| `/paper/accounts/{account_id}/orders` | Immutable intents/events | Stored simulated orders and states only; no scheduling or processing |
| `/paper/accounts/{account_id}/trades` | Immutable fills | Simulated fills with existing lineage; no synthetic API fills |
| `/paper/accounts/{account_id}/performance` | Existing P16 performance/P15 reports | Preserves unavailable valuations; bounded persisted equity/drawdown series |
| `/research/backtests` and `/research/backtests/{backtest_id}` | P10 summaries and D71 audit | All 504 stored results, including cause counts and source-evidence hashes |
| `/research/backtests/{backtest_id}/performance` | P10 equity Parquet and summary | Paginated stored series; null full-path metrics remain null for all 474 unresolved runs |

Legacy `/health/live` and `/health/ready` retain their foundation-only liveness
and SELECT-1 connectivity contracts. They are not the composite P17 `/ready`.

## Response and error contracts

Pydantic envelopes contain `data`, `source`, `as_of_session`, `classification`,
`version`, `artifact_id`, `provenance`, `evidence_status`, `quality_status`,
`missing_data_reasons` and optional `page`. Research payloads expose the source
dataset/revision, canonical/profile identities and final-vintage revision warning.
Every price/prediction references its persisted canonical/prediction identity.
P6 responses include the original feature definition and original state column.
P9 reports retain estimator configuration and training cutoff, without loading
the estimator. Ordinary health/source absence does not assert data clearance.

Financial values retain domain precision: Decimal prices serialize as strings,
and P15/P16 Fraction values serialize as exact strings (including rational forms).
Feature/model diagnostics remain declared floats. The response cap defaults to
2,000,000 bytes. Narrow the query when a response exceeds it; values are never
silently truncated. Mixed portfolio types are marked MIXED_RECORD_TYPES in the
account collection and retain each account's own domain classification. Individual
USER_RECORDED, TEST_ONLY and simulated results keep their actual provenance.

Errors have `error_code`, safe `message` and generated `request_id`. Invalid
input/date/horizon is 422; unknown recorded identity is 404; missing required
dataset/artifact/database is 503; occupied read capacity is 429; query-budget
expiry is 504; excessive response/ledger size is 413. Unsupported methods are
405. Current opportunities/signals return a classified null-data unavailable
envelope with 503. Empty recorded collections are successful only after the
corresponding source/database has been read. Unresolved P10 metadata is readable
with 200 and its explicit UNRESOLVED_ECONOMIC_OUTCOMES status; unavailable metrics
are not replaced by closed-only statistics.

The seven canonical states remain WATCH, SETUP_FORMING, ENTRY_SIGNAL, HOLD,
TAKE_PROFIT_REVIEW, EXIT_SIGNAL and EXITED. No real current snapshots satisfy
the existing P11-P14 gates, so none is invented by P17. No signal evaluator or
explanation generator is called. Benchmark and PIT fundamentals remain
UNAVAILABLE. Raw action/terminal gaps are never resolved through the API.

## Temporal and performance behavior

Identity is the original stable internal ID, including conservative provisional
year-scoped identities. Same ticker with different ISINs is never merged.
Catalog ranges are first/last observations, not proof of uninterrupted listing.
Historical prices display identifiers from that very observation; a future ISIN
or symbol is not backfilled. All calendar slots between a security's observed
boundaries are exposed, including the five verified missing Muhurat sessions.
Missing rows have null OHLCV and an explicit observed-range/listing-proof caveat.
No forward/backward fill or price interpolation occurs.

Ordinary price/feature requests access one hash-partitioned file with column
projection and Arrow date/identity filters. Row streaming is bounded; original
ordering is checked while reading. The entire seven-million-row dataset and the
46-million-row consolidated OOS file are never loaded for normal requests.
Predictions require both a single persisted model ID and stable security ID;
one matching OOS partition is used. SHA256 is checked on first access and when
size/mtime changes. This is a trusted local immutable-artifact boundary, not a
signature or hostile-filesystem defense. Hashing is subject to the read budget.
Model identity, dataset identity and FOLD_TEST metadata must match before serving.

Default Parquet read budget is 30 seconds and concurrent expensive reads are
limited to two; PostgreSQL uses read-only transactions, three-second connect
timeout, five-second statement timeout and at most 1,000 ledger/event records
before existing reconstruction. Large ledgers fail explicitly rather than
silently omitting lots or events. Cold checksum scans cost more than warm reads.
This is a measured local integration, not a multi-user throughput guarantee.

## Security boundary

`python -m alphalens_api` binds 127.0.0.1. Non-loopback peers and unconfigured
browser origins are rejected before private reads. Trusted hosts are restricted;
forwarded headers are disabled in the supplied launcher. CORS permits only
configured loopback frontend origins, GET, and no credentials. Request IDs are
generated internally; URLs, request bodies, configuration paths and DSNs are not
logged. Responses have no-store/nosniff/CSP headers. OpenAPI JSON is local at
`/openapi.json`; `/docs` redirects to that offline contract without CDN scripts.

P21 object authorization/authentication is not implemented. Do not expose this
service through public listeners, reverse proxies or tunnels, even if upstream
appears to the app as a loopback peer. No fake login is supplied. Use a local
least-privilege PostgreSQL role with SELECT on the portfolio tables; do not use
real brokerage credentials. Explicit test evidence can only run in environment
test and is classified TEST_ONLY; ordinary research mode rejects fixture data.

The Docker default is also loopback-only inside the container. Ordinary published
Docker ports do not reach that listener. Smoke checks run inside the container;
public container networking is not a supported workaround. The image excludes
datasets and the build-only uv installer. The approved baseline still has 44
HIGH OS findings; no Trivy ignore, exit-code relaxation or production security
claim is authorized. See the separate verification and security receipts.

## Windows CMD setup and safe requests

Use the existing frozen workspace. These operator examples refer to the existing
local archives; application logic contains no personal absolute paths.

```cmd
cd /d C:\Users\Dell\AlphaLens
set UV_CACHE_DIR=D:\alphalens-uv-cache
.tools\bin\uv.exe sync --frozen
set ALPHALENS_RESEARCH_DATA_ROOT=D:\al-research\tejhq-final-vintage-v1-r3
set ALPHALENS_RESEARCH_RUN_ROOT=D:\al-research\tejhq-research-evaluation-v2-fit-parallel
set ALPHALENS_RESEARCH_REPORT_ROOT=C:\Users\Dell\AlphaLens\docs
set ALPHALENS_CATALOG_PATH=D:\al-research\p17-api\discovery.sqlite
set ALPHALENS_ENVIRONMENT=development
set ALPHALENS_TEST_ONLY_EVIDENCE=false
.venv\Scripts\python.exe -m alphalens_api serve
```

The above index was prepared during P17. On a fresh local installation, choose
an absent catalog output outside the frozen roots and run this once before
`serve`: `.venv\Scripts\python.exe -m alphalens_api build-catalog`.
Do not rerun it against an existing index. No training command is required.

Configure ALPHALENS_DATABASE_URL privately in the process environment using a
local PostgreSQL connection and an already migrated database (003/004 for P15/P16,
after existing migrations). Never commit the value or paste it into an issue/log.
Without a configured database, portfolio/paper requests return 503 and composite
readiness is false; health and configured research reads can still work.

From a second CMD window:

```cmd
curl.exe -f http://127.0.0.1:8000/api/v1/health
curl.exe http://127.0.0.1:8000/api/v1/ready
curl.exe -f http://127.0.0.1:8000/openapi.json
curl.exe -f "http://127.0.0.1:8000/api/v1/stocks?q=RELIANCE&limit=10"
curl.exe -f "http://127.0.0.1:8000/api/v1/stocks/tejhq:isin:INE002A01018/history?start=2023-11-10&end=2023-11-14"
curl.exe -f "http://127.0.0.1:8000/api/v1/stocks/tejhq:isin:INE002A01018/indicators?feature=sma_200&start=2026-01-01&limit=10"
curl.exe -f "http://127.0.0.1:8000/api/v1/research/models?horizon=5&phase=2026&limit=10"
curl.exe -f http://127.0.0.1:8000/api/v1/research/evaluation
curl.exe "http://127.0.0.1:8000/api/v1/signals/tejhq:isin:INE002A01018"
```

Use a model_run_id returned by `/research/models` together with security_id for
`/research/predictions`. Horizon values are 1/5/10/20; phase filters preserve the
stored names `development`, `2025`, `2026`. Signals intentionally return 503.
P18 may subsequently integrate these contracts only after separate authorization.
