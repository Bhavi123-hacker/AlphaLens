P15 AND P16 DEVELOPMENT PASSED. P15 was committed as 2db5f15 before P16
implementation. Final P16 Windows-safe regression: 495 passed, one production/live
skip (1473.38s), including 35 P16 cases. PostgreSQL 17 ingestion, immutable replay,
restart recovery and teardown exited 0. Frozen lock/sync, Ruff, mypy, Bandit,
dependency audit and diff checks passed. STOP before P17; no production clearance.

Current scope amendment D65-D67 authorizes P15 then P16 only, with separate
verification/commits from P14 5eaeb01. P15 owns portfolio ledger/accounting/valuation;
P16 owns forward simulated intents/fills and reuses P15. P17/API, frontend and live
pipeline remain deferred. No real execution or broker credential path. Production
clearance OPEN/use NOT_CLEARED, fundamentals UNAVAILABLE. Historical statuses below
are preserved as historical records, not restrictions on this newly approved scope.

# Roadmap, dependency and acceptance record

Current D62-D64 authorization: P13 decision states, then P14 offline explainability
from P12 28070df. P13 must pass all gates and commit before P14 implementation;
P14 must pass and commit separately, then STOP before P15. Canonical states,
explicit position boundary, serialized development assumptions, per-horizon
evidence, PIT history/identity and leakage checks determine software acceptance.
Fixture success never clears real-data, signal calibration or production gates.

Authority: DOCX §22; release amendments in DECISIONS.md. Phases are dependencies,
not permission to implement everything. D43-D45 authorize sequential P3/P4
development; P3 must pass and be committed first. D46-D48 subsequently authorize
P5 canonical development from approved P4. D49-D50 now authorize P6/P7 from
approved P5 649340a: P6 gate and commit before P7. D51-D54 authorize P8 from
approved P7 9c2bad9 on p8-baseline-ml. D55-D58 subsequently authorize P9 then P10 from P8 58159b7; stop before P11.
P1_PRODUCTION_DATA_CLEARANCE = OPEN and does not block development.

| Phase | Deliverable | Release / present status |
| --- | --- | --- |
| P0 | Product contract | This milestone: contract satisfied; operational gates remain distinct. |
| P1 | Free source and contract | DEVELOPMENT research fixture validated under D36-D39; production/live clearance OPEN. |
| P2 | Raw ingestion | DEVELOPMENT PASSED; verification in p2-verification-report.md. Production clearance independently OPEN. |
| P3 | Data validation/quarantine/freshness | DEVELOPMENT PASSED under D43-D44; p3-verification-report.md. Live freshness/calendar evidence remains unavailable. |
| P4 | PIT universe | DEVELOPMENT PASSED after P3 gate/commit; p4-verification-report.md. TEST_ONLY PIT/survivorship mechanics verified; real historical-universe evidence unavailable. |
| P5 | Canonical data model | DEVELOPMENT PASSED under D46-D48; p5-verification-report.md. Approved P6/P7 baseline 649340a; production data NOT_CLEARED. |
| P6 | Features | DEVELOPMENT PASSED under D49-D50; p6-verification-report.md. Committed ac6973f before P7. |
| P7 | Targets/labels | DEVELOPMENT PASSED; p7-verification-report.md. Separate matured t+1-open outcomes; approved P8 baseline 9c2bad9. |
| P8 | Baseline ML | DEVELOPMENT PASSED under D51-D54; p8-verification-report.md. Reproducible single holdout/software gates only; stop before P9. |
| P9 | Walk-forward | DEVELOPMENT PASSED; 311 tests/one live gate skip; p9-verification-report.md. Commit before P10. |
| P10 | Backtester | DEVELOPMENT PASSED; 26 P10 cases / 337 distinct repository tests passed, one live gate skip; p10-verification-report.md. Hypothetical mechanics, no product strategy acceptance. |
| P11 | Risk | DEVELOPMENT PASSED: 355 passed/one live skip, coherent Windows-safe PostgreSQL regression and quality gates; commit before P12. |
| P12 | Ranking | DEVELOPMENT PASSED after P11 b50314b: final coherent 375 passed/one live skip and PostgreSQL/quality gates; complete historical candidates/exclusions, fixed models, risk penalties, past-only history. Commit separately, stop before P13. |
| P13 | Signals/policy | DEVELOPMENT PASSED: 394 passed/one live skip, deterministic canonical states/history, explicit synthetic-position boundary, all quality/PostgreSQL gates. Committed as 490de2e before P14. |
| P14 | Explainability | DEVELOPMENT PASSED after P13 commit: coherent 423 passed/one live skip, 100 deterministic explanations/annotations, 128 actual local attributions and all quality/PostgreSQL gates. Commit separately, STOP before P15. |
| P15 | Portfolio Guardian | DEVELOPMENT PASSED: 460 passed/one live skip, exact FIFO/PIT histories and all PostgreSQL/quality gates; commit before P16. |
| P16 | Paper trading | DEVELOPMENT PASSED: 495 passed/one live skip, 35 P16 cases, PostgreSQL 17/recovery and all quality gates; separate commit after P15 2db5f15. STOP before P17. |
| P17 | Product API | MVP; local health skeleton is not completion; deferred. |
| P18 | Frontend | MVP after data/evidence dependencies; deferred. |
| P19 | Market-hours monitoring | Later, only verified provider cadence/latency; deferred. |
| P20 | Notifications | In-app MVP; Telegram/email V2; deferred. |
| P21 | Security hardening | Baseline now, full hardening before any release; deferred. |
| P22 | Observability | Safe logs now, full monitoring/recovery before release; deferred. |
| P23 | Performance/scale | Measured requirements before release; deferred. |
| P24 | Deployment | Local free deployment sufficient for V1; cloud optional, no paid dependency; deferred. |
| P25 | Final acceptance | Full amended scope; separate MVP checklist excludes V2/V3. |

Advanced regime models, portfolio optimization and LLM assistant are V3/optional;
real-money execution is permanently outside scope.
Original phase numbering is preserved. D26–D35 amend release requirements, not the
historical DOCX: historical NIFTY 500 and PIT fundamentals are optional, actual
verified free depth replaces an unconditional 10–15-year V1 requirement, and all
required software/services/data must have a compatible zero-cost path.

## P1 DEVELOPMENT gate under D36-D39 (current)

The subsequent user-approved research decision supersedes the larger proposed
P1_V1_FREE_v1 checklist below for DEVELOPMENT acceptance only. Preserve the former
checklist as the historical proposal and as evidence of unsolved production needs.

Required: explicit open licence; repository uploader-clearance representation;
documented residual risk; real capture with immutable artifacts/hashes; successful
canonical normalization, deterministic replay and complete provenance; passing
relevant tests; zero paid dependencies. Actual results and remaining limitations:
[P1 validation](../data/p1-validation-report.md).

Historical-universe reconstruction and PRODUCTION_DATA_CLEARANCE remain OPEN.
Research cohort membership cannot substitute for historic NSE/NIFTY membership.
P1 DEVELOPMENT passage did not automatically authorize P2. Subsequent explicit
user approval in D40-D42 now authorizes it independently of production clearance.

## P2 DEVELOPMENT acceptance under D40-D42

Current P3/P4 gates under D43-D45: both DEVELOPMENT PASSED sequentially.
P3 commit 304ab3d predates all P4 work. P3 quality/session/provenance/anomaly/replay
and P4 temporal identity/availability/listing/departure/type/anti-leakage/replay
mechanics pass with explicit fixture scope. Production/live clearance remains OPEN.
P5 was subsequently authorized under D46-D48; P3/P4 reports below remain historical.
Reports: [P3](../development/p3-verification-report.md),
[P4](../development/p4-verification-report.md).

## P5 DEVELOPMENT acceptance under D46-D48

Durable security identity with P4 temporal facts; canonical sessions/EOD/actions;
fundamental schema with unavailable reads and blocked writes; original P2 raw and
normalized/quarantine lineage; P3 quality with historical existence preserved;
PIT availability/effective/receipt/revision separation; immutable revision replay;
pinned input/cutoff/snapshot IDs; exact Decimal PostgreSQL/Parquet representations;
classification guardrails and anti-lookahead tests. Real PostgreSQL migrations,
constraints, indexes, persistence/replay and all quality gates are required.
Actual gate and limitations: [P5 verification](../development/p5-verification-report.md).
P1_PRODUCTION_DATA_CLEARANCE remains OPEN. No P6 authorized by development passage.

Raw capture, complete manifests/SHA256, idempotency, immutable revision lineage,
source-neutral parsing, strict decimal normalization, basic row validation,
evidence-preserving quarantine, canonical Parquet/JSON, testable provenance,
deterministic replay, classification guards and metadata persistence implemented.
Actual quality gates: [P2 verification](../development/p2-verification-report.md).
No production market-data availability is required for this development gate.
D43-D45 subsequently authorize P3/P4 development; the P2 report remains historical.

## P0 acceptance (unchanged)

| Criterion | Status / evidence |
| --- | --- |
| Product name, goals and personas fixed | SATISFIED: product-contract.md. |
| NSE cash-equity market and EOD V1 fixed | SATISFIED: D01–D02. |
| Historical universe requirement and no-survivor fallback fixed | SATISFIED AS CONTRACT: D28 supersedes D03; dynamic historical evidence preferred, NIFTY 500 optional; actual coverage UNKNOWN. |
| Seven canonical states and ownership boundaries fixed | SATISFIED: D05–D06; detailed transitions deferred. |
| Manual portfolio, paper scope and exclusions fixed | SATISFIED: D04/D07/D21. |
| Security/no-execution/LLM boundaries fixed | SATISFIED AS CONTRACT: threat-model.md; full auth/security not implemented. |
| §23 inconsistencies explicitly resolved | SATISFIED: D01/D02/D05/D09–D11/D13/D15–D17. |
| Glossary, assumptions, decision ownership and dependency gates recorded | SATISFIED: glossary.md and DECISIONS.md; owner of scope/budget approvals is user, technical evidence collection is implementation work. |
| Source preserved and rules persistent | SATISFIED: source SHA256, AGENTS.md. |

## Historical proposed P1 V1 exit gate: P1_V1_FREE_v1

The following checklist/statuses describe the earlier free-data-strategy baseline,
not current development authorization. D39 superseded this gate for development;
D40-D42 explicitly authorize P2 independently of production/live clearance.

Proposed for review under the user's new policy; not an assertion of passed
acceptance or authority to build an adapter. It replaces mandatory paid-provider,
10–15-year, NIFTY 500 and fundamental coverage expectations for V1, while retaining
the DOCX's requirement for representative real history through the abstraction.
Detailed protocol and limitations: [free-data strategy](../data/free-data-strategy.md).

| ID | Required evidence | Current status |
| --- | --- | --- |
| F1 | At least one verified free source for required price data; no billing, paid account, expiring trial or paid runtime dependency. | BLOCKED: public routes documented, usable price payload/access not tested. |
| F2 | Document source-specific permissions/limits for automation, raw retention, snapshots, normalization, research/ML/backtesting and intended display/derived outputs; identify any restricted distribution scope. | NOTES COMPLETE; compatible grant NOT ESTABLISHED. Research-only permission cannot pass a user-facing distribution gate. |
| F3 | Preserve neutral provider.py; version and test the schema mapping for actual source identifiers, sessions, adjustment basis, availability and revisions before adapter work. | FOUNDATION EXISTS; NIFTY_500-only universe and other reported schema gaps need a versioned P1 review. No adapter now. |
| F4 | A bounded representative REAL sample through the approved abstraction/mapping, including ordinary sessions and real missing/corrected/action/identity/departed cases relevant to the supported scope. | BLOCKED: 0 real records; TEST_ONLY fixtures do not count. Untested cases remain unsupported and cannot be hidden. |
| F5 | Retain permitted exact raw bytes, source/retrieval/rights metadata and SHA256; normalize and replay deterministically with hashes, row counts, duplicate/revision handling and complete accepted/excluded accounting. | BLOCKED on real sample and rights; fixture-only replay helpers exist. |
| F6 | Document actual historical date/security coverage per dataset, gaps, schema transitions, calendar evidence, original-versus-latest vintages and as-of eligibility. No promised five/ten/fifteen-year minimum. | BLOCKED: documented depth is not measured coverage. |
| F7 | Demonstrate explicit per-date universe methodology on the sample, contemporaneous security classification/IDs, later departures and absence semantics; disclose residual survivorship and missing-outcome limits. | PROPOSED; not empirically demonstrated. Never seed from today's listed/index members. |
| F8 | Mandatory temporal, identity, OHLCV/unit and corporate-action/adjustment checks pass for the declared usable scope; unknown availability is excluded from PIT claims. | BLOCKED on real evidence. Dropping optional fundamentals does not waive price/action correctness. |
| F9 | Explicit unavailable-capability and model-input-family contract: NIFTY 500 optional, FUNDAMENTAL_PIT_DATA = UNAVAILABLE, sector optional; four availability states and no fabricated substitutions. | SATISFIED AS PRODUCT CONTRACT; later implementation remains deferred. |
| F10 | Publish discrepancies, rights constraints, exclusions and reproducible sample results; user reviews P1 exit and separately authorizes P2. | NOT ACHIEVED. P2 prohibited. |

P0 remains complete by user approval. No paid-provider selection is needed to close
P1, but a verified compatible free source and real sample are still indispensable.
Free-data research does not itself approve a source, adapter or P2. Historical
NIFTY 500 or PIT fundamentals may be unavailable without blocking this scoped gate;
missing required rights, price/action integrity or PIT universe evidence cannot.

## Development foundation acceptance

Skeleton/configuration/tests are authored. Runtime PostgreSQL, dependency locking,
lint/type/security/container checks are independent verification gates. See
docs/development/verification-report.md for actual results, including skips and
failures. CI being authored is not a passing CI run.

## P9/P10 authorized development — 2026-10-06

D55-D58 authorize P9 and P10 sequentially from approved P8 58159b7. Acceptance
is scientific software structure, leakage resistance and deterministic replay,
not fixture investment performance. P9 must pass/commit before P10 starts; P10
must pass/commit before stopping. P11 requires separate user approval.

P9 DEVELOPMENT PASSED and committed as 4e29b49 before P10 began. P10 acceptance
requires verified P9 OOS-only input, next-session-open timing, explicit calendar
knowledge, fixed policies, equal weights, exact cash/inventory reconciliation,
no fabricated fills/recoveries, costs and sensitivity, classified benchmarks,
metrics with honest unavailable states, complete artifact/lineage output,
adversarial tests and all quality/PostgreSQL gates. Neither phase's fixture
acceptance demonstrates real economic/predictive value. The separate
[real-data readiness report](../development/real-data-readiness.md) is required.
