# Approved AlphaLens decisions

Status: P0-P7 DEVELOPMENT PASSED; P6 committed before P7; stop before P8.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. Production market-data use remains NOT_CLEARED.
Authority: complete source document plus the user's approved amendments, including
the subsequent zero-paid-dependency instruction recorded below. These entries are
interpretations or amendments, not claims that the source document contained them.
D01–D25 preserve the earlier decisions. Where explicitly superseded, D26–D35 govern
current V1 scope, as amended by D36-D42 below. Accepted provider research is
evidence, not production provider approval.

Source: `AlphaLens_Complete_Project_Documentation.docx`, dated 2026-10-04.
SHA256: `196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a`.

| ID | Decision | Basis and effect |
| --- | --- | --- |
| D01 | NSE cash equities; INR; exchange sessions in Asia/Kolkata, stored aware UTC instants | User amendment 1; resolves §23.10. No BSE, derivatives, or multi-market scope. |
| D02 | V1 is end-of-day first | Amendment 2; resolves §23.9. No intraday/real-time implementation or claims. Later monitoring needs verified provider latency and entitlements. |
| D03 | Prefer historical NIFTY 500 membership, conditionally | Amendment 3; §§6.6, 27. Historical membership, departed securities, and licensing must be verified. Never use today's members as historical members. If unsupported, report and propose a smaller reconstructible universe for approval. |
| D04 | AlphaLens never places real trades | Amendment 5 overrides future broker-integration suggestions in §§4.2/4.3/21. No order infrastructure or broker credentials. Manual transaction records and simulations are distinct from execution. |
| D05 | Seven canonical signal states | §23.1/Rule 05: WATCH, SETUP_FORMING, ENTRY_SIGNAL, HOLD, TAKE_PROFIT_REVIEW, EXIT_SIGNAL, EXITED. BUY/SELL are transaction sides. No alternative stored/API signal enums. |
| D06 | Preserve research versus position context | Approved plan interpretation of §9.3: HOLD/EXITED cannot establish user transactions. Position context and allowed transitions must be designed before P13; no state engine now. |
| D07 | Freeze MVP exclusions | Amendment 4: news sentiment, user-facing paper trading, Telegram/email, advanced regimes, LLM assistant, portfolio optimization, broker integration, real-money execution excluded. Execution is permanently excluded, not a later version. |
| D08 | Preferred executable research timing only | Amendment 6: completed session t information -> prediction after required information is available -> earliest hypothetical execution at t+1 open. Missing that open cannot claim the fill. Thresholds, exact labels, fees, slippage, and costs remain UNDECIDED until versioned/justified later. |
| D09 | Canonical monorepo | §23.3 and approved plan: apps/web, apps/api, ml/{data,features,training,inference,evaluation,explainability,registry}, backtesting, workers, infra, db, docs, tests. One migration owner in db; CI in .github/workflows. |
| D10 | Stable security IDs and plural API paths | §23.4: /api/v1/stocks/{security_id}, /portfolios, /model-performance, /portfolios/{portfolio_id}/performance. Symbols are historical attributes, not identity. Paths are documentation only except health endpoints. |
| D11 | Canonical available_at, distinct other times | Amendment 9/§23.5: preserve published_at, ingested_at, event/session time, effective interval, and revision identity. Unknown availability is not PIT eligible. Live use also requires ingestion by the decision time. Verified later historical ingestion need not change historical availability. |
| D12 | Revision-preserving raw/normalized/derived data | §§6, 21: immutable source payloads, checksums, versions, reproducibility. Preserve original and restated filings. Fully revised adjusted history cannot silently enter historical features. |
| D13 | Canonical entity names | §23.6: securities, price_bars, fundamentals, corporate_actions, universe_memberships, security_identifier_history, sector_history, market_context, ingestion_runs, data_snapshots, users, portfolios, holdings, transactions, watchlists, alerts, notification_preferences, feature_snapshots, predictions, risk_assessments, signals, signal_transitions, explanations, model_runs, model_metrics, evaluation_results, backtests, paper_trades, audit_logs. Logical catalog only; P5 owns schema/migrations. Deferred domains are not implemented. |
| D14 | P1 evidence before selection | Amendments 7/8: provider.py is neutral; no selected_provider.py. Only create providers/<actual_vendor>.py after verified selection/access. No candidate is approved, no paid access assumed or purchased; unsupported and UNKNOWN remain distinct. |
| D15 | File-based P1 sample, production ingestion later | §23.8: bounded in-memory sample/replay contracts now; licensed real sample persistence can later use ignored local storage. P2/P3 raw landing, scheduling, quarantine, broad ETL are not authorized. No provisional production schema. |
| D16 | Phase order and release scope are different | §23.2/7: dependency-led P0–P25; tag release scope explicitly. P25 is full amended scope acceptance, not MVP completion. Excluded optional domains cannot prevent an honest separately defined MVP gate. |
| D17 | Early security/observability; later hardening | §§17–19 versus P21/P22: safe configuration/errors/logs, dependency controls, private local services now; later phases deepen testing and operations. Health-only API under §27 is not P17 completion. |
| D18 | Temporal evaluation starts with baselines | P8 already needs chronological out-of-sample evaluation; P9 formalizes walk-forward. Train-only transformations, matured labels, overlap purge/embargo, final untouched evaluation. No models now. |
| D19 | Backtester integration gate depends on decision logic | P10 may establish simulator interfaces later; follow-AlphaLens results require shared P11–P14 risk/policy/signal logic. No duplicate paper/backtest logic. |
| D20 | Core evidence cannot wait for V2 | Every actionable signal needs risk and explanation. Use appropriate attribution later; no causality claims. Missing optional news/analogs are explicitly unavailable, never invented; historical analog statistics require real evidence. |
| D21 | Transaction-led portfolios | §§11/15: auditable opening positions and transactions eventually derive holdings/P&L. Cost basis, corporate actions, corrections, and dividends need definitions before P15. No portfolio implementation now. |
| D22 | Managed OIDC direction; vendor undecided | Approved plan/§27: avoid custom password auth. USER/ADMIN/DATA_OPERATOR/ML_OPERATOR and object ownership are architectural requirements. No protected product endpoints or login now. |
| D23 | Local development first; AWS direction only | §27: Docker/Compose and PostgreSQL skeleton; cloud budget, service choices, event broker, retention values, RPO/RTO remain OPEN. No cloud purchases/provisioning. |
| D24 | Preserve source and persistent engineering rules | Amendments 10/11: DOCX unchanged; AGENTS.md persists rules; stop/report new contradictions. TEST-ONLY fixtures are not provider or market evidence. |
| D25 | Bound this authorization | Only P0/P1 foundation and development skeleton. Stop before P2; no frontend, production ML, features, backtester, risk/ranking/signals, portfolio, or AWS implementation. |

## Subsequent user-approved free-data amendments — 2026-10-05

These amendments follow the accepted provider research at commit
`f8400265f6e6877da4154a916d87cd163a59071d`. That research and its conditional paid
recommendation remain historical evidence; the recommendation was not approved.
The following policy comes from the user's new instruction, not the original DOCX.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D26 | ZERO paid dependencies | No required paid data, constituents, APIs, cloud, databases, auth, ML/model APIs, monitoring or trial-only services. No purchase/subscription. The mandatory runnable path must use local free/open-source software and compatible free data. Supersedes the former possibility of a paid V1 provider/budget in D14/D23. Public access is not a usage licence. |
| D27 | Free-data-first, evidence before implementation | Official NSE daily records/reference/disclosures are the conditional investigation priority. The paid NSE, NSE Indices, Global Datafeeds and EODHD options previously evaluated are ineligible as mandatory V1 dependencies. This does not establish that any free alternative is approved. Keep the neutral provider.py boundary; no adapter in this task. |
| D28 | Dynamic historical NSE universe preferred; historical NIFTY 500 OPTIONAL | Supersedes D03's preferred mandatory-universe direction. Derive each date's candidates only from historically evidenced records and classification available by that decision time. Never use today's constituents or current listed-symbol inventory retrospectively. The proposed methodology still needs actual coverage/rights validation; no claim of full historic tradability or survivorship-free data. |
| D29 | Disclose actual depth per dataset | Replaces an unconditional V1 10–15-year requirement: use the maximum verified, legally usable free historical depth available per dataset and disclose actual coverage, gaps and versions. Approximately five years is acceptable if verified, not a new guarantee or minimum. Architecture remains capable of longer histories. |
| D30 | PIT fundamentals optional; currently unavailable | FUNDAMENTAL_PIT_DATA = UNAVAILABLE until free rights, original/revised statements, publication evidence and revision linkage are demonstrated. Fiscal-period end never substitutes for availability. Future feature interfaces remain extensible; no fundamental input or neutral-value substitute is forced into V1. |
| D31 | Technical ML scope is conditional, with unchanged scientific standards | Price/return/volume/volatility/momentum/MA/RSI/MACD/ATR and lawful, temporally valid context may support later research. Sector context needs historical assignments. Chronological/walk-forward evaluation, leakage controls, justified/versioned costs/slippage, benchmarks, risk adjustment and out-of-sample reporting remain mandatory. No guaranteed accuracy, fabricated results, feature engine or model now. D08/D18/D20 remain binding. |
| D32 | Canonical availability behaviour | AVAILABLE, DEGRADED, STALE, UNAVAILABLE describe a data family's fitness for a stated purpose/as-of scope. Missing required inputs block dependent output. Missing optional families are disclosed, never replaced by synthetic/neutral values; models declare the families actually used. Correctness is never weakened to populate a screen. Detailed contract in product-contract.md; implementation deferred. |
| D33 | Local free deployment sufficient; cloud optional | Supersedes D23's AWS production direction as a release requirement. PostgreSQL and upstream Docker Engine/Compose on a compatible local host are sufficient in principle; runtime verification is separate. Docker Desktop cannot be universally mandatory because its free eligibility is conditional. No paid cloud/service dependency. |
| D34 | Authentication and operations must have a free local path | Supersedes any paid-managed-auth interpretation of D22. Keep standard authentication protocols and security requirements, with a self-hostable open-source option when that phase is approved. No vendor or implementation selected; optional cloud/auth/monitoring cannot make the local path depend on billing or an expiring trial. |
| D35 | Redefine P1 V1 evidence gate without weakening correctness | User authorizes the free-data strategy and requires a proposed revised gate. P1_V1_FREE_v1 is proposed in roadmap-and-acceptance.md for review, not declared passed. It still needs a real permitted representative sample, reproducible normalization through the abstraction, provenance/checksums, actual coverage and a tested historical-universe method. NIFTY 500 and PIT fundamentals may be explicitly unavailable. P2 still needs separate approval. |

Research details and unresolved rights: [free-data-evaluation.md](docs/data/free-data-evaluation.md).
The [methodology](docs/data/free-data-strategy.md) is a proposal to validate, not an
implemented universe or a finding that source permissions have been granted.

## Subsequent user-approved research-fixture decision - 2026-10-05

The previous P1B attempt stopped without data acquisition because upstream rights
were unresolved. That cautious evidence is preserved. The user now explicitly
accepts residual upstream-rights risk for a non-commercial educational/research
fixture, rather than requiring production-level clearance for development.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D36 | Separate research from production clearance | An established research repository's explicit CC BY/CC0 licence and uploader rights representations suffice for bounded local research when no specific contrary evidence is found. Preserve provenance and attribution, disclose residual risk, and do not require independent proof of every upstream right. RESEARCH_FIXTURE_USE = ACCEPTED_WITH_RESIDUAL_RISK; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED; PRODUCTION_DATA_CLEARANCE = OPEN. Supersedes the previous research-fixture blocking interpretation of D14/D27/D35, not the production gate. |
| D37 | Mendeley bounded fixture authorized | Select five compatible NSE-labelled stock datasets; preserve necessary original files even if they contain longer history, but initially normalize only a common bounded interval. Use named source-specific file parsing, not production ingestion. Retain raw/normalized data only in ignored local storage; commit metadata, hashes, attribution, code and tests. No public redistribution by AlphaLens in this milestone. |
| D38 | Missing metadata must remain missing in canonical research records | A dated CSV does not prove session-close time, original publication/availability, revision timing, price-adjustment basis or stable exchange identity. A versioned, narrow canonical extension may represent unknown session-close time and distinguish REAL_RESEARCH_FIXTURE origin. Existing PIT eligibility remains fail-closed. Dataset publication is separate from historical bar availability. Snapshot-scoped IDs are not permanent NSE security IDs. |
| D39 | P1 DEVELOPMENT gate supersedes the production-sized fixture gate | Pass only after open-licence/repository representations/residual risk, real acquisition, immutable hashes, canonical normalization, deterministic replay, complete provenance, tests and zero paid dependencies are demonstrated. Historical-universe reconstruction and production/live clearance are separately OPEN; this cohort does not solve survivorship bias. P2/P4 must distinguish RESEARCH_FIXTURE_DATASET from HISTORICAL_MARKET_UNIVERSE_DATASET. P1 passage permits requesting P2 approval, never starting P2 automatically. |

Dataset selection and access evidence: [research-fixture-source.md](docs/data/research-fixture-source.md).
Actual gate outcome: [p1-validation-report.md](docs/data/p1-validation-report.md).

## Subsequent user-approved P2 development amendments - 2026-10-06

These amendments implement the user's explicit one-month execution strategy.
They are amendments to the original phase gate, not statements in the DOCX.
The existing uncommitted P1 work was reviewed, verified and committed as baseline
`3f8880c` with explicit user approval before creating `p2-raw-ingestion`.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D40 | Production clearance does not block downstream infrastructure development | P0 COMPLETE; P1 research/architecture sufficient for development; P1_PRODUCTION_DATA_CLEARANCE = OPEN. Supersedes D15/D25/D35/D39 restrictions on starting P2 after the user's explicit authorization. Does not approve production/live data, historical-universe methodology or investment-performance claims. |
| D41 | Authorize bounded P2 raw-ingestion foundation | Source-neutral acquisition, immutable local raw landing, manifests/SHA256, versioned parsing/normalization, basic validation/quarantine, canonical Parquet/JSON, provenance, replay, structured logs, developer CLI and metadata persistence. TEST_ONLY and already accepted RESEARCH_FIXTURE inputs permitted. Zero paid dependencies; no public research-data redistribution. Production capture remains disabled. |
| D42 | Keep phase and data gates separate | P2 DEVELOPMENT requires verified implementation/tests, not production-data availability. P2's row-level validation/quarantine does not complete P3's wider quality/freshness scope. Technical ingestion metadata migrations live exclusively in db/; P5 financial/entity schema stays deferred. Stop before P3; no features, labels, ML, backtesting, frontend, signals, portfolios, real-time or AWS provisioning. |

Implementation and limitations: [P2 architecture](docs/data/p2-raw-ingestion.md).
Verification: [P2 development report](docs/development/p2-verification-report.md).

## Subsequent user-approved P3/P4 development amendments - 2026-10-06

The user explicitly authorizes both phases from approved P2 commit
`d3eee20ed9318435639a83b8afea3fe7c8c002d1`. These are amendments to the original
DOCX development gates; the DOCX is unchanged.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D43 | Sequential combined P3/P4 authorization | Branch p3-p4-validation-universe; implement, verify and commit P3 before P4. Supersedes D42's stop-before-P3 restriction only. Do not modify/merge main. |
| D44 | Bounded P3 quality layer | Consume P2 canonical records and row quarantine; deterministic dataset/session/temporal/provenance/identifier/anomaly checks, transparent metrics, severity and eligibility reports. No invented calendars or corporate-action adjustments; file storage suffices, no freshness UI or unavailable financial-family fabrication. TEST_ONLY/accepted RESEARCH_FIXTURE only; production clearance OPEN. |
| D45 | Bounded P4 temporal identity/universe | Half-open effective intervals and separately evidenced availability; preserve revision knowledge, listings, departures and symbol changes. TEST_DYNAMIC_CASH_UNIVERSE fixtures prove implementation, not real NSE coverage. Unknown classifications/availability fail closed; current constituents cannot become historical truth. Minimal file-based identity model, no P5 schema, sector/index history without evidence, features, labels, ML, signals or backtesting. Stop before P5 even after both development gates pass. |

Implementation interpretation under D45 (not an additional user amendment): P4
needs scoped P2 quarantine evidence to distinguish bad G prices from known G
existence and valid A prices. This is versioned as `p3.quality.v2`; v1 reports and
the P3 gate commit remain preserved. P2 behavior is unchanged. Full input hashes
pin snapshots; corrections need explicit new input/knowledge-state snapshots.

## Subsequent user-approved P5 development amendments - 2026-10-06

These amend the DOCX development authorization; the source document is unchanged.
Baseline: approved P4 commit `59da9a82d5c0f6f5a39fd36b4f645cc10035261b`.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D46 | Authorize P5 canonical model | Branch p5-canonical-data-model from approved P4. Supersedes D45's stop-before-P5 restriction only. No main merge; P6/features, labels, ML, backtesting, signals, ranking, portfolio and frontend remain unauthorized. |
| D47 | Integrate source and knowledge evidence | Reuse P2 raw/normalized lineage, P3 reports and P4 temporal identity/universe. Preserve effective/publication/availability/receipt and immutable revisions. Unknown availability/basis stays unknown; rejected observations remain evidence with unavailable values where normalization failed. No inferred calendars or automatic price adjustments. |
| D48 | Canonical development storage and gates | db/ owns PostgreSQL canonical migrations, constraints and indexes; analytical Parquet is a deterministic versioned export. TEST_ONLY/accepted RESEARCH_FIXTURE permitted; production remains NOT_CLEARED and P1 clearance OPEN. Corporate-action structure is evidence-based; fundamental schema/interface remains UNAVAILABLE without seeded facts. Real PostgreSQL and anti-leakage tests required. Stop before P6 after gate/commit. |

Implementation interpretation under D46-D48 (not additional user scope): shared
immutable revision headers and typed domain projections retain complete contract
payloads, including sparse evidence. P4 owns temporal identity/membership; P3 owns
quality; P2 remains the artifact lineage root. Fundamentals have a typed interface
with writes disabled and UNAVAILABLE reads; no fabricated facts or premature table
population. Input IDs pin replay state, including receipt metadata; different fresh
captures may have different IDs. P5 DEVELOPMENT PASSED with constructed evidence;
[verification and unresolved production gates](docs/development/p5-verification-report.md).
P6 is still separately gated by user approval.

## Subsequent user-approved P6/P7 amendments - 2026-10-06

These amend development authorization, not the original DOCX. Approved baseline:
`649340aeae012683718b882a0f31754ad2d8ed36`, P5 DEVELOPMENT PASSED. Initial checks:
clean working tree, approved P5 HEAD, documented gate, no P6/P7 implementations,
production clearance OPEN and use NOT_CLEARED; DOCX checksum unchanged.

| ID | Decision | Basis, supersession and effect |
| --- | --- | --- |
| D49 | Combined sequential P6/P7 authorization | User explicitly authorizes both on p6-p7-features-labels from approved P5. P6 must pass all gates and be committed before P7 implementation. Supersedes D46-D48 stop-before-P6 restrictions only. Main unchanged; stop before P8 even after both pass. |
| D50 | Bounded PIT technical features and separate targets | P6 consumes P5, reuses P3/P4, pins decision cutoffs and immutable inputs, emits versioned technical/context features with explicit unavailable reasons. P7 may use future observations only as supervised targets, with versioned t+1 open conventions and maturation. No fabricated fundamentals, adjustment, current constituents, global fitted scalers, production data or investment claims. |

P6 implementation interpretation under D49-D50: v1 raw derived indicators are
float64; source financial facts remain exact P5 Decimal. Recursive indicators use
an explicitly bounded trailing 50-session history with SMA seeds. Verified
canonical calendar evidence is required for every calendar date in the window;
TEST_ONLY calendars describe artificial sessions, not NSE holidays. No new runtime
dependency or migration is needed. [P6 formulas and policies](docs/ml/p6-feature-engineering.md).

P6 DEVELOPMENT PASSED and committed as
`ac6973f3b9a85dfff1e6094e348065ab177b4535` before P7 started: 234 passed, one
production/live gate skipped, all static/security and real PostgreSQL gates passed.
P7 implementation interpretation under D49-D50 (not a new user amendment):
raw 1/5/10/20-session outcome enters t+1 open and exits t+h close; positive=1,
nonpositive=0; no costs or economic terminal-value assumptions. No verified open
timestamp exists in P5, so decisions must precede the entry local date start,
otherwise feasibility is unavailable. Versioned 38-significant-digit Decimal
division retains exact rational evidence. Known unadjusted action windows are
degraded and excluded from training eligibility. Feature replay/IDs and explicit
column namespaces preserve separation. [P7 contract](docs/ml/p7-label-generation.md).
P7 DEVELOPMENT PASSED: 259 passed, one production/live gate skipped; all static/
security/PostgreSQL regression/replay/teardown gates passed. P1 production clearance
remains OPEN and market-data use NOT_CLEARED. [Verification](docs/development/p7-verification-report.md).
No P8 authorization follows automatically from these development gates.

## Historical unresolved decisions at the free-data-strategy baseline

The following items record the situation at commit 84abd59. D36-D39 now authorize
the narrower research-fixture task; production/live and historical-universe
limitations remain open. See the current validation report for measured results.

- A zero-cost source compatible with retention, historical research/backtesting,
  ML and intended outputs: NOT ESTABLISHED. Public pages do not settle these rights.
- Historical daily-file completeness, contemporaneous classification/identifiers,
  original versions and availability evidence: UNKNOWN; dynamic universe feasibility
  is conditional. Historical NIFTY 500 is optional and remains unverified.
- Real sample/adapter: none. No adapter is authorized in this decision-only task.
  A versioned P1 schema review must address the existing NIFTY_500-only literal and
  other reported mapping gaps before real normalization; no code changed here.
- Exact 1D/5D/20D label definitions, thresholds, cost/slippage model: deferred P7.
- Free local identity/operations choices, retention values and production RPO/RTO:
  deferred before their consuming work; data-retention rights must be known before
  real-data persistence. No paid budget is assumed or needed to pass V1.
- Actual exchange calendar source: UNKNOWN; no invented holidays/session schedule.
