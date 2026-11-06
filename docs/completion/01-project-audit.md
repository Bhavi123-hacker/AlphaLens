# AlphaLens completion audit — 24 October 2026

This campaign continues `alphalens-master-completion` from
`da4382242371c17ebdf2cecc620541931b91e313`. The initial checkout was dirty:
monitoring/UI tests, `uv.lock`, preservation tooling, development-storage wrapper,
and six completion evidence documents already existed. They were preserved and
reviewed, not reset. No branch merge or research rerun is part of this release.
Two registered worktrees exist: this D: tree and the protected C: P26 checkout.

The user mandate supersedes historical phase stops only within its express
scope. It permits safe implementation, offline testing and isolated deployment;
new provider requests, live task changes, destructive cleanup and public deployment
remain approval boundaries. The original DOCX, holdout, models and saved forecasts
remain protected. See `DECISIONS.md` D95 for the exact existing 500-stock policy.

## Verified architecture and shortest release path

FastAPI serves an authenticated loopback React/TypeScript/Vite application.
`workers/providers` owns Upstox V3 requests, clocks, source contracts and a shared
request ledger. `workers/nse_market` owns the fixed cohort, immutable observations,
compatible inference and daily orchestration. SQLite stores auth, personal records,
forecasts and operational state; the owned PostgreSQL17 cluster serves historical
research projections. Credentials stay in Windows Credential Manager.

The shared `.venv` and `node_modules` have existing D: junction targets and older
dependencies. Do not synchronize them as a release shortcut. Candidate dependencies,
test clusters, builds and logs use isolated D: locations. The new saved-candle
projection is an explicit derived worker publication, not an implicit acquisition
or full-history rebuild during dashboard reads.

The shortest safe release is: patch isolated dependencies; verify preserved
source/models; publish a saved daily-candle view; replay actual compatible
inference without new forecast publication; verify risk-aware Top-N, history and
pending outcomes; build and deploy the compiled authenticated application locally;
exercise real saved APIs/browser navigation; restart and compare preservation.

## Component gap matrix

Effort describes bounded engineering work, not a promise to clear external evidence.

| Requirement | Existing implementation / current defect | Required change | Effort | Dependencies | Test method | Priority |
|---|---|---|---|---|---|---|
| Storage | C: emergency already recovered; mixed D: evidence/caches | Fresh non-reparse inventory, exact proposed cleanup only | Small | Active paths/hashes | Drive byte measurements and reference audit | P0 |
| Startup | Native launcher and owned PostgreSQL; no live listener at first check | Isolated patched runtime and compiled build | Medium | Dependencies/config/auth | Actual health/auth/restart checks | P0 |
| Daily candles | Existing500 workflow; empty Oct21 responses, later partial recovery, clock/interruption failures | Preserve source gates, expose exact pending/accepted counts | Medium | Independent clock/session/source | Existing offline pipeline tests and genuine receipts | P1 |
| Latest quotes | QuoteV3 implemented; strict clock/display gates remain | Reuse selected private transport explicitly | Small | Approved live request | Offline contract; no new live request in campaign | P1 |
| Market dashboard | Existing terminal can request provider on stock navigation | Saved-only OHLCV/search/movement/leader views | Medium | Verified retained candles | Exact Decimal/gaps/auth tests and browser | P1 |
| Charts | Existing interactive candles/volume/indicators | Saved-source default; explicit provider action | Medium | Immutable projection | Browser candle/volume and no-provider checks | P1 |
| ML | Compatible frozen V2 price classifier; no independent acceptance | Actual saved-vector/source replay, no retraining | Medium | Model/schema/checksums | Recomputed numerical parity | P1 |
| Top5/10/20 | Actual scores but stale rows could appear; score-only order | Stale exclusion, registered volatility penalty, stable ties | Medium | Valid scores/risk | Adversarial API tests and saved replay | P1 |
| Persistence | Append-only versioned forecast ledgers already exist | Preserve originals; show dated model/input/creation evidence | Small | Compatible model and future entry | Idempotence/no-backdating/history tests | P1 |
| Outcome tracking | Matured-only evaluation exists; no actual saved outcomes | Keep null metrics/pending state; report metric gaps | Small | Qualified future sessions/retrieval | Future-evidence exclusion and immutable reads | P2 |
| Scheduler | Exact500 policy registered; recent interrupted starts | Monitor task/worker mismatch; prepare repair for approval | Medium | Live-task approval | Offline launch/lock/quota/replay and read-only task audit | P2 |
| Backtesting | 504 frozen runs,474 unresolved economics | Audit source-backed evidence; no invented recoveries/rerun | Evidence-bound | Corporate actions/identities/prices | Checksum inventory and existing accounting evidence | P2 |
| Security | New local Python/npm advisories supersede old historical results | Isolated compatible dependency fixes, strict audits | Medium | Install/registry/scan availability | Tests/types/lint/audits/Bandit/secrets | P3 |
| Local release | Existing Windows deployment architecture | New immutable config/build and isolated QA auth | Medium | Compiled build/database | Real HTTP/browser/restart/preservation | P3 |
|1000 stocks | Dated candidate universe already prepared | Verify plan; no expanded activation | Small | Exact new budget approval | Deterministic preparation and quota tests | P4 |
| GPU/streaming/public | CPU/IrisXe; no Feed entitlement or public data clearance | Document evidence and leave inactive | Evidence-bound | Hardware/rights/security/approval | Capability inspection only | P4 |

## Readiness

Software implementation is not independent model acceptance, current successful
daily delivery or public production clearance. Final observed results, exact
commands and separate verdicts belong to the final completion report and dated
release test report. Older README paragraphs are historical and must not be used
as current execution evidence.
