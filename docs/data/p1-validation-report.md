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
