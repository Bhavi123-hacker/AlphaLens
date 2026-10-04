# Roadmap, dependency and acceptance record

Authority: DOCX §22; release amendments in DECISIONS.md. Phases are dependencies,
not permission to implement everything. Current authorization ends before P2.

| Phase | Deliverable | Release / present status |
| --- | --- | --- |
| P0 | Product contract | This milestone: contract satisfied; operational gates remain distinct. |
| P1 | Provider and contract | Foundation implemented; selection/licensed real-history gate BLOCKED. |
| P2 | Raw ingestion | Deferred; requires explicit approval. |
| P3 | Data validation/quarantine/freshness | Deferred; P1 helpers are not P3 completion. |
| P4 | PIT universe | MVP dependency; deferred. |
| P5 | Production data model | MVP dependency; deferred; sole migrations owner db/. |
| P6 | Features | Technical/fundamental/market MVP; sentiment V2; deferred. |
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
| P24 | AWS deployment | Production direction only; deferred. |
| P25 | Final acceptance | Full amended scope; separate MVP checklist excludes V2/V3. |

Advanced regime models, portfolio optimization and LLM assistant are V3/optional;
real-money execution is permanently outside scope.

## P0 acceptance

| Criterion | Status / evidence |
| --- | --- |
| Product name, goals and personas fixed | SATISFIED: product-contract.md. |
| NSE cash-equity market and EOD V1 fixed | SATISFIED: D01–D02. |
| Historical universe requirement and no-survivor fallback fixed | SATISFIED AS CONTRACT: D03; actual data remains UNKNOWN. |
| Seven canonical states and ownership boundaries fixed | SATISFIED: D05–D06; detailed transitions deferred. |
| Manual portfolio, paper scope and exclusions fixed | SATISFIED: D04/D07/D21. |
| Security/no-execution/LLM boundaries fixed | SATISFIED AS CONTRACT: threat-model.md; full auth/security not implemented. |
| §23 inconsistencies explicitly resolved | SATISFIED: D01/D02/D05/D09–D11/D13/D15–D17. |
| Glossary, assumptions, decision ownership and dependency gates recorded | SATISFIED: glossary.md and DECISIONS.md; owner of scope/budget approvals is user, technical evidence collection is implementation work. |
| Source preserved and rules persistent | SATISFIED: source SHA256, AGENTS.md. |

## P1 acceptance

| Criterion | Status |
| --- | --- |
| Provider-neutral interface, errors, capability evidence | SATISFIED: provider.py/contracts.py. |
| Temporal, identity, units, revision and missing-data contract | SATISFIED AS FOUNDATION: data-contract.md and tests. |
| Bounded sample verification/replay mechanism | SATISFIED FOR TEST-ONLY INPUTS; no real-provider evidence. |
| Evaluation and licensing checklist | SATISFIED AS DOCUMENTATION; candidate-specific results UNKNOWN. |
| Vendor selected with verified licensed access | BLOCKED: no approved provider/access/budget. |
| Representative real history through abstraction | BLOCKED: no vendor-specific adapter or real capture. |
| Historical NIFTY 500/departed-security feasibility | BLOCKED/UNKNOWN: no membership evidence. |
| P1 full exit gate | NOT SATISFIED. Do not start P2. |

## Development foundation acceptance

Skeleton/configuration/tests are authored. Runtime PostgreSQL, dependency locking,
lint/type/security/container checks are independent verification gates. See
docs/development/verification-report.md for actual results, including skips and
failures. CI being authored is not a passing CI run.
