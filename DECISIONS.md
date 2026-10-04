# Approved AlphaLens decisions

Status: approved product contract and P1 foundation scope; provider gate OPEN.
Authority: complete source document plus the user's approval and eleven amendments
in this conversation. These entries are interpretations or amendments, not claims
that the source document originally contained them.

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

## Remaining decisions and blockers

- Provider/vendor, credentials, evidenced capabilities, licensing, and data budget:
  OPEN; user/provider evidence required before real sample and selection.
- Historical NIFTY 500 feasibility: UNKNOWN. Smaller universe cannot be chosen
  silently; requires a separately approved evidence-based proposal.
- Exact 1D/5D/20D label definitions, thresholds, cost/slippage model: deferred P7.
- Identity provider, production hosting/event broker/budget, retention values,
  production RPO/RTO: deferred decisions before their consuming work; license
  retention constraints must be known before any real-data persistence.
- Actual exchange calendar source: UNKNOWN; no invented holidays/session schedule.
