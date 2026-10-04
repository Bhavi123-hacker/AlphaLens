# Logical canonical entity catalog (not a schema migration)

D13 resolves §23.6. db/ is sole future migration owner in P5. No production schema,
seed data or financial rows are created now.

Market/history: securities, security_identifier_history, sector_history,
universe_memberships, price_bars, fundamentals, corporate_actions, market_context,
ingestion_runs, data_snapshots. Dated identities and revision-preserving PIT facts
are required; current ticker/sector fields cannot erase history.

User/portfolio: users, portfolios, holdings, transactions, watchlists, alerts,
notification_preferences. Transactions/opening entries eventually derive holdings.

ML/decision: feature_snapshots, predictions, risk_assessments, signals,
signal_transitions, explanations, model_runs, model_metrics, evaluation_results.
Versioned snapshots/rules and auditable state changes are required.

Simulation: backtests, paper_trades. Security: append-oriented audit_logs.
News/text and other deferred entities will require a reviewed amendment before
schema creation; no current news implementation or invented news records.

Prices: decimal positive OHLC, nonnegative integer volume, nullable turnover,
currency/exchange/session identifiers, raw versus adjusted distinction. Corporate
action adjustment factors must be versioned; actual transformation is later.
Availability, ingestion, publication, effective intervals and revisions remain
separate wherever meaningful. Unique keys must include source/revision semantics
instead of overwriting corrections. Final indexes, partitions, FKs and retention
are P5 design work and must account for real volume and licensing.
