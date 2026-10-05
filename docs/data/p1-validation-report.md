# Current P1 DEVELOPMENT research-fixture validation

2026-10-05. Branch: p1-real-sample-validation. Approved baseline: 84abd599daccc832cbcb0d54d4f70e3f3755d6f0.
P0 PASSED. P1 DEVELOPMENT GATE PASSED. P2 NOT STARTED OR AUTHORIZED.
PRODUCTION_DATA_CLEARANCE = OPEN. PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.

The user-approved D36-D39 research gate supersedes the former production-sized
clearance requirement for this development milestone only. Earlier caution is
preserved below. No production provider, paid dependency or broad pipeline was added.

| Development criterion | Actual result |
| --- | --- |
| Explicit open-licence fixture | PASS: five named Mendeley Data V1 datasets, CC BY 4.0. |
| Repository clearance representation | PASS: Mendeley terms 3.2-3.3 documented; no specific contrary evidence found in this review. |
| Residual risk and production separation | PASS: ACCEPTED_WITH_RESIDUAL_RISK; upstream entitlement not independently established; production OPEN. |
| Real capture | PASS: five original CSVs, 1,322,193 bytes; 12,984 original rows retained locally. |
| Raw integrity | PASS: all five SHA256/byte sizes match pre-acquisition repository file metadata; original CSVs read-only, no overwrite. |
| Bounded normalization | PASS: 300 selected rows, 299 valid canonical records; one missing-data observation explicitly UNAVAILABLE, never filled. |
| Replay | PASS: two independent reads/parses plus final rerun produce identical canonical bytes. |
| Provenance | PASS: every accepted row verified against its original physical CSV row, source-fields hash, artifact/hash, DOI/version/licence/contributors and capture manifest. |
| Tests | PASS: 64 passed, one separate production/live-provider skip, warnings as errors; real fixture and PostgreSQL checks ran. |
| Tooling/security | PASS: Ruff lint, format (65 files), mypy (31 files), Bandit (911 lines, zero findings); no new dependency/lock change. |
| Zero paid dependency | PASS: no account, subscription, purchase, API key or paid service introduced. |
| P2 authorization | NOT GRANTED: stop after commit and request user approval. |

## Measured bounded coverage

Requested interval: 2024-01-01 through 2024-03-31. Actual observed dates:
2024-01-01 through 2024-03-28, 60 unique dates per source. These are observations,
not a certified exchange-session calendar. Only bounded financial rows were normalized;
full-file dates were scanned to describe artifact coverage, not certify all history.

| Security | Original file date bounds | Original rows | Bounded source rows | Canonical rows |
| --- | --- | --- | --- | --- |
| 3MINDIA.NS | 2002-07-01 to 2024-04-29 | 5429 | 60 | 59 |
| ABB.NS | 2002-07-01 to 2024-04-29 | 5429 | 60 | 60 |
| ACI.NS | 2022-11-21 to 2024-04-30 | 355 | 60 | 60 |
| 360ONE.NS | 2019-09-19 to 2024-04-30 | 1141 | 60 | 60 |
| ABSLAMC.NS | 2021-10-11 to 2024-04-30 | 630 | 60 | 60 |

Canonical and replay SHA256:
`1853dc8abe5529e4d241700ee3de679b7010b28d83ec845c28372f3baae97dc2`.
Raw hashes, exact byte sizes, acquisition instants, DOIs, names, versions and licences:
[research-sample-manifest.json](research-sample-manifest.json).
Machine-readable quality and replay results:
[research-sample-validation.json](research-sample-validation.json).

## Data quality and scientific limits

- 3M India row 5403, 2024-03-15: missing OHLCV (and source adjclose). Explicit
  UNAVAILABLE observation, no bar emitted; the 3M fixture is DEGRADED for this window.
- ACI, 360ONE and ABSLAMC report zero volume on 2024-01-15. Preserved exactly;
  these observations are not independent evidence of exchange-correct volume.
- No duplicate security/session keys, malformed dates/numbers or OHLC violations
  were found among accepted bounded records. All 299 pass finite/positive OHLC,
  high/low consistency and nonnegative integral-volume validation.
- No fabricated missing sessions or holiday calendar. Missing-relative-to-cohort
  reports do not establish all-market session completeness or tradability.
- Historical available_at, published_at and session_close_at remain null. Dataset
  publication is catalog metadata only. All 299 remain historically PIT-ineligible.
- Source adjclose remains in retained source fields. Adjustment methodology,
  historical revisions, corporate actions, index/sector context and fundamentals
  are UNAVAILABLE/UNKNOWN. No forward fill, neutral substitution or synthetic input.
- Snapshot-scoped security identifiers do not establish permanent exchange identity.
  Currency INR is an explicit NSE-instrument reference mapping, not a CSV column.
- RESEARCH_FIXTURE_DATASET is not HISTORICAL_MARKET_UNIVERSE_DATASET. Survivorship
  bias is not solved; no NSE/NIFTY-wide performance or model accuracy is claimed.
- AVAILABLE/DEGRADED describes fixture usability only; this historical snapshot is
  STALE for live decisions. No frontend or product signals exist.

## Runtime verification

Docker 29.6.2 / Compose v5.3.1 now ran PostgreSQL 17.11. Compose validated;
service reached healthy; the real host PostgreSQL test passed. A committed TEST_ONLY
marker survived stop/start, then was dropped. Dedicated services/network/test volume
were removed cleanly. No SQLite, mocked connection or financial database was used.

The first test failed under Windows' default Proactor event loop, which Psycopg's
async driver rejects. A synchronous, timeout-bounded probe now runs in a worker
thread. Host connection still failed until the Docker Desktop internal-network
port-publication issue was isolated and fixed. The bridge now permits outbound
traffic; published service ports remain 127.0.0.1 only. These are foundation fixes,
not production infrastructure. Failures and remediation are retained in the ledger.

The one remaining skipped test is explicitly the PRODUCTION/live provider gate.
It neither substitutes for nor invalidates the independently exercised research gate.
A fresh checkout without the ignored research files will skip its real-fixture tests
until the checksum-pinned artifacts are acquired; no synthetic fallback exists.

Sources, attribution, permission reasoning, acquisition failures and replay instructions:
[research-fixture-source.md](research-fixture-source.md).

## Historical P1 validation records retained unchanged

The following sections preserve the previous stricter gate and its actual results.
D36-D39 supersede its development-clearance requirement, not its unsolved production,
historical-universe or temporal limitations.

---

# Current P1 free-data validation status

Updated 2026-10-05 on `p1-free-data-strategy`, from accepted research commit
`f8400265f6e6877da4154a916d87cd163a59071d`.
**P0 COMPLETE. P1 NOT ACHIEVED. P2 NOT STARTED OR AUTHORIZED.**
Real market records ingested: **0**. Approved source adapters: **0**.
Paid dependencies selected/purchased: **0**. No source approved.

The policy change is approved; the detailed revised exit checklist
[P1_V1_FREE_v1](../product/roadmap-and-acceptance.md) is proposed for review.
Research findings and a proposed method do not pass the real-sample gate.

| Gate | Current result |
| --- | --- |
| Free-source research | COMPLETE AS DOCUMENTATION: eleven official source families, twelve evidence dimensions, rights/PIT/depth limitations and URLs. |
| Zero-paid policy / scope | RECORDED: D26-D35. Earlier paid research retained as history; those options cannot be mandatory V1 dependencies. |
| Free required-price source | NOT VERIFIED FOR USE: report/MCP access documented, no usable price sample obtained. Public filings/pages read are not a price dataset. |
| Compatible retention/automation/ML/backtest/output rights | BLOCKED: no AlphaLens-specific compatible grant; published restrictions need clarification. Free research eligibility unknown. |
| Provider/source abstraction | FOUNDATION EXISTS: provider.py unchanged. No adapter. Versioned universe/identity/revision/adjustment mapping review remains necessary. |
| Verified price-history interval | NONE MEASURED: MCP advertises rolling five years; no interval acquired or certified. Report actual legally usable coverage later. |
| Historical universe | CONDITIONAL METHOD PROPOSED: per-date observed/classified equities. Historic reference, departed coverage and availability not demonstrated. |
| Historical NIFTY 500 | OPTIONAL / UNAVAILABLE: current constituents cannot stand in for past membership. Absence alone no longer blocks scoped V1. |
| PIT fundamentals | FUNDAMENTAL_PIT_DATA = UNAVAILABLE: original/revised numeric archive plus rights and historical availability not established. Optional for V1. |
| Corporate actions / price basis | INCOMPLETE: public discovery routes exist; complete action terms, correction history and raw/adjusted reconciliation unvalidated. |
| Real representative sample, checksums and replay | BLOCKED: zero records normalized through a real mapping. TEST_ONLY replay helpers are not source evidence. |
| Availability and model-family contract | RECORDED: AVAILABLE / DEGRADED / STALE / UNAVAILABLE, no artificial/neutral substitutes; no feature engine or model implemented. |
| Entire revised P1 V1 exit gate | NOT PASSED. Optional omissions do not waive mandatory rights, price/action integrity, temporal or universe gates. |

The next evidence step is a no-fee rights/coverage clarification, then an explicitly
approved bounded real-sample/contract task if that succeeds. A manual permitted
sample and an automated retained ML dataset are different scopes. Do not infer
authorization to implement an adapter from this decision document. P2 needs its own
explicit approval after P1 review.

A useful technical ranking model is scientifically plausible but not established
from any verified dataset held here. No guaranteed accuracy, historical performance,
fabricated constituents, publication times or numeric replacements are produced.

## Local runtime and current verification scope

Local free PostgreSQL/container deployment is sufficient in principle, not runtime
certification. On final resume, `docker info` again exited 1 because the
`dockerDesktopLinuxEngine` pipe is absent. PostgreSQL was not started or connected;
no services needed teardown and no substitutes were introduced.

Current decision-work checks and exact results are recorded in
[verification-report.md](../development/verification-report.md) and
[command-log.md](../development/command-log.md). Earlier test and runtime outcomes
below are historical, not new runs.

Current evidence and methodology:
[free-data-evaluation.md](free-data-evaluation.md),
[free-data-strategy.md](free-data-strategy.md),
[provider-decision.md](provider-decision.md).

## Historical record: earlier P1 validation retained verbatim

The body below records the previous paid-provider evaluation and its then-current
gate. D26-D35 supersede mandatory paid selection, NIFTY 500 and fundamental scope.
Its actual checks/skips remain valid historical records, not evidence of free-data
sample ingestion.

---

# P1 validation report

Updated 2026-10-05. **P0 COMPLETE by user approval. P1 NOT ACHIEVED. P2 NOT STARTED.**
Branch: `p1-provider-evaluation`; baseline main commit:
`9fa82284936f8b7a34f5409ba25cdce3538747b6`.

Real records ingested: **0**. Approved vendor adapters: **0**.
Provider selected: **none**. No licensed access or representative capture obtained.
No historical predictions/performance claims. Public documentation examples are
evidence of documented schemas only, not AlphaLens market data or empirical tests.

## P1 criteria and actual evidence

The original DOCX section 22 P1 requires provider choice, adapter interface and
licensing notes; its exit gate requires a representative historical set through
the abstraction. User amendments add explicit evidence/licensing/universe/PIT
constraints. Research alone does not satisfy the ingestion gate.

| Criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Neutral MarketDataProvider interface | SATISFIED as foundation | Existing provider.py retained; no default adapter. |
| Public provider evaluation | SATISFIED as research | Three shortlist candidates, all 30 dimensions, four evidence states, separate rights/PIT matrices and source register. No vendor accuracy certified. |
| Ranked recommendation | SATISFIED as research | Conditional NSE primary + separately licensed membership; GFD fallback; EODHD rejected for current primary requirements. User decision pending. |
| Licensing notes | SATISFIED as documentation | Restrictions documented; actual storage/raw/snapshot/ML/display/derived grants remain UNKNOWN. |
| Actual provider selection/access | BLOCKED | No approval, commercial agreement or credentials. |
| Complete canonical provider mapping | INCOMPLETE | Schema review required for financial period/basis, revision time, volume basis and reference histories; see provider-decision.md. Existing TEST_ONLY checks cover only their defined foundation scope. |
| Historical NIFTY 500 universe | UNKNOWN | Separate NSE Indices enquiry recommended. Actual membership intervals/announcement times/departed prices not demonstrated. |
| PIT fundamentals | UNKNOWN | No original/restated archive tested; field presence does not establish availability. |
| Representative historical set via abstraction | BLOCKED | No permitted real capture or approved adapter. |
| Real-sample checksums/replay/completeness | BLOCKED | TEST_ONLY replay tests do not substitute. |
| Entire P1 exit gate | NOT ACHIEVED | Provider, rights, schema mapping and real sample gates remain. |

## Existing helpers and their limits

Foundation includes frozen EOD records/requests, scoped capability evidence,
separate publication/availability/ingestion fields and revision identity,
fail-closed temporal eligibility, half-open membership intervals, bounded canonical
replay/duplicate checks and source-origin guards. These are not production ETL,
a full quality engine or a universe builder. Research found additional required
schema semantics; do not claim complete production compatibility.

The four research evidence states are deliberately not promoted into the runtime
capability enum. A documented product or PARTIALLY_VERIFIED capability cannot
activate production support. Constructed fixtures remain explicitly TEST_ONLY.

## Independent local runtime result

Docker CLI 29.6.2 and Compose v5.3.1 are installed. `docker info` exits 1 because
the `dockerDesktopLinuxEngine` named pipe does not exist. Compose configuration
validation exits 0 using process-only TEST_ONLY values; no .env was written.
PostgreSQL was not started, health was not reached, and no real connection was
verified. No services were started, so no teardown was necessary. Docker did not
block provider research. No SQLite/mocks replaced the real connectivity check.

`uv run --offline --frozen pytest -W error -ra`: **47 passed, 2 skipped, 0 warnings**.
Skipped: real PostgreSQL (ALPHALENS_TEST_DATABASE_URL absent) and real provider
(no approved adapter/licensed sample). A skipped integration test is not a passed
runtime or P1 external-data gate. Dependencies/code are unchanged on this branch.
On resume, Ruff lint and format checks, mypy and Bandit also passed. The earlier
pip-audit result remains historical; no fresh dependency-vulnerability scan is
claimed for this documentation-only increment.

## Bounded real-sample acceptance protocol (not executed)

After written rights, scope approval and provider selection, perform a versioned
P1 schema review with meaningful tests, then implement only the approved named
adapter. Choose actual cases with the provider, never fabricate a response:

1. Establish the licensed window, source product/version, identifiers/series,
   supplied coverage inventory and permitted raw/snapshot retention.
2. Obtain a bounded sample spanning ordinary history, earliest coverage, a new
   listing, suspension/missing session, rename, departed/delisted member, splits,
   dividend, bonus, merger and demerger. Select real events from evidence; do not
   invent dates or numerical expectations.
3. Obtain a baseline historical index roster and complete dated changes for a
   small contiguous interval, including an off-cycle event and a later leaver.
   Reconcile membership with security history and end-of-life prices/actions.
4. Obtain one original/restated filing pair and demonstrate differing eligibility
   before and after evidenced availability. Preserve fiscal period, publication,
   revision and capture times. Unknown timestamps remain ineligible.
5. Compare records against authoritative source documents under permitted use;
   check units, INR, raw/adjusted OHLCV, timezone and actual exchange sessions.
   Verify pagination/ranges and report partial/missing responses explicitly.
6. Capture exact permitted raw bytes and hashes, versions and mapping decisions.
   Repeat/replay the bounded capture and account for duplicates/corrections. No
   production-scale ingestion, scheduler or P2 ETL is authorized by this protocol.
7. Report discrepancies, licence limits and all untested requirements. Only then
   ask for an explicit P1 selection/exit review. P2 requires separate approval.

## Scope conclusion

Full intended P1 scope cannot pass now. A scientifically valid reduced scope is
only a proposal: verified prices/actions plus a reconstructible historical universe,
with fundamentals excluded if PIT evidence is unavailable. Smaller membership or
a shorter period requires explicit approval and evidence including leavers. No
scope downgrade, provider selection or implementation is made by this report.

See [provider evaluation](provider-evaluation.md), [decision and vendor questions](provider-decision.md),
[sources](provider-research-sources.md), [runtime report](../development/verification-report.md)
and [command ledger](../development/command-log.md).
