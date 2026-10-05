# Roadmap, dependency and acceptance record

Authority: DOCX §22; release amendments in DECISIONS.md. Phases are dependencies,
not permission to implement everything. Current authorization ends before P2.

| Phase | Deliverable | Release / present status |
| --- | --- | --- |
| P0 | Product contract | This milestone: contract satisfied; operational gates remain distinct. |
| P1 | Free source and contract | DEVELOPMENT research fixture validated under D36-D39; production/live clearance OPEN. |
| P2 | Raw ingestion | Deferred; requires explicit approval. |
| P3 | Data validation/quarantine/freshness | Deferred; P1 helpers are not P3 completion. |
| P4 | PIT universe | MVP dependency; deferred. |
| P5 | Production data model | MVP dependency; deferred; sole migrations owner db/. |
| P6 | Features | Technical and verified lawful context for V1; PIT fundamentals/sector optional; sentiment V2; deferred. |
| P7 | Targets/labels | MVP; exact conventions/costs must be versioned; deferred. |
| P8 | Baseline ML | MVP; chronological evaluation from first experiment; deferred. |
| P9 | Walk-forward | MVP; purge/embargo where appropriate; deferred. |
| P10 | Backtester | MVP; AlphaLens strategy acceptance also depends on P11–P14; deferred. |
| P11 | Risk | MVP; independent risk before actionable signals; deferred. |
| P12 | Ranking | MVP; versioned tested policy weights; deferred. |
| P13 | Signals/policy | MVP; deterministic audited context-aware transitions; deferred. |
| P14 | Explainability | Core MVP; optional news/analogs explicitly unavailable until supported; deferred. |
| P15 | Portfolio Guardian | Manual ledger/P&L MVP; independent checks; deferred. |
| P16 | Paper trading | V2 user-facing capability; shared decision logic; deferred. |
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
P1 DEVELOPMENT acceptance does not authorize P2; await explicit user approval.

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

## Proposed P1 V1 exit gate: P1_V1_FREE_v1

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
