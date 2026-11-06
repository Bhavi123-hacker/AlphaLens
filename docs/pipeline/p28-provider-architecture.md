# Read-only multi-provider preparation

P28 reuses P19, P2/P3 normalization/quality, P4/P5 identity lineage, P6 registry,
P20 alerts, P21 authorization and the frozen prospective/model contracts.
There is no second market-data database, public webhook, trading SDK or order route.

`alphalens_data.providers.multi_contracts` declares exchange-explicit Instrument,
Candle, Access, RequestPlan, Outcome and MarketProvider operations. Unsupported
quote, status and corporate-action methods return explicit unavailable outcomes.
All adapter transports remain disabled, even when a caller supplies optimistic
permission/activation flags. No hidden collection command exists.

`multi_adapters` parses bounded Upstox/INDstocks/Angel native JSON offline. Decimal
prices stay exact. Volume, timestamps, duplicate sessions and identity are validated.
Open time, retrieval time and unknown publication/revision metadata remain separate.
Price basis defaults UNKNOWN; P2 conversion requires separately evidenced raw basis,
ISIN and series. Cross-provider identity bridging cannot be inferred from a company
name/current master. Upstox BOD parser retains current-only semantics and unknown series.
Yahoo/Alpha/TejHQ have explicit disabled capability interfaces; their unverified
ongoing NSE formats are not presented as production-ready parsers.

P19 adds vendor dispatch only in TEST_ONLY mode. Fixture envelope hash, immutable
original native body hash and instrument revision hashes stay distinct. Existing
raw landing, P2/P3, canonical checkpoints, exact P6 definitions, publication/recovery,
duplicate and correction contracts are reused. DAILY's original hard blocker remains.
No original research archive, model or receipt is overwritten.

`workers.providers.session_plan` prepares at most31 dates from dated calendar facts.
Unknown weekdays never imply missing sessions. Holidays, special sessions, incomplete
releases, accepted duplicate hashes and corrected hashes retain separate states.
A missing-release warning requires a documented aware availability window. Open
timestamps are never turned into provider publication timestamps. Planning does not fetch.

`eligibility` reports exact peer denominator/coverage, cutoff/session/provider
identity, raw basis/series/actions and frozen38-feature compatibility via original
`input_compatibility`. `momentum_percentile_20` still needs contemporaneous complete
peers; no neutral value, current-universe backfill or formula substitution occurs.
The bounded P19 feature worker still caps128 securities/201 lookback slots and withholds
unsupported cross-sectional context. Full-universe daily inference is not verified.

The frozen h10 XGB model was checksum/report pinned and deserialized in an owned,
45-second subprocess with only two specifically scoped XGB types beyond the existing
reviewed types. Native configuration3.0.5 and38 post-preprocessing features matched;
zero predictions/training/evaluation ran and hash/global allowlist stayed unchanged.
This trusted-local diagnostic is not a security sandbox or inference acceptance.
HGB1/5/20 candidates retain their earlier verified metadata/preprocessing. All candidates
remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE. Top5/10/20 and current signals stay unavailable.

ProviderStore is a separate **operational** SQLite WAL/FULL store defined only by
`db/providers/schema.sql`: disabled selection, audit and quota reservations. Private
Windows DACL/current operator+SYSTEM or POSIX owner permissions, explicit version,
BEGIN IMMEDIATE, unique request/attempt keys and bounded retries survive restart.
Failure attempts consume limits. Retry-After is not shortened; auth rejection cannot
retry. Clock rollback, pending duplicates and storage-cap overflow are rejected.
Attempts/audit are capped100,000; archive/review is required, no silent deletion.
It stores no prices, credentials, tokens or financial accounts. Alpha's real diagnostic
quota ledger remains separate and is read without resetting it; no new actual call runs.

Protected `GET /api/v1/providers/comparison` reports six sources, prior sanitized
metadata evidence, read-only operational status, unknown provider quota, theoretical
capacity and independent ML blockers. Global P21 authentication/loopback/Host/Origin
protections remain. No write/acquire/enable API exists. Response classification is
provider documentation, not market observations. Old OpenAPI snapshots remain intact;
new `p28-openapi.json` drives the typed frontend generation check.

Settings/Data Health reuse existing ProviderReadiness and add six-source cards,
provider and capacity filters, documentation links, precise last verified dates,
unknown latency/quota, under-review status and no acquisition controls. Frontend
refresh is a read only and does not trigger provider requests. Short bounded retries
for local READ_CAPACITY preserve the original backend semaphore/resource limits;
401/403/503 are not retried into success. Rich P26 chart pages remain lazy-loaded.

An optional fresh `TEST_ONLY_demo*` root uses the existing small P17 synthetic
evidence builder, private authentication, empty alerts and disabled provider state.
It never falls back into normal mode and binds only127.0.0.1:8029. Persistent global
TEST_ONLY/synthetic banner and hero label prevent real-market claims. This prepares
local demonstration; public serving remains disabled. No real research is copied into it.

Existing P19 disabled schedule XML remains disabled; its illustrative time is not a
verified provider publication schedule. Nothing registers Windows tasks or starts
outbound channels. Prospective ledger stays empty until genuinely qualified forecasts
exist and outcomes mature. Corporate-action/benchmark evidence has not resolved any
of the474 original unresolved economic backtests.
