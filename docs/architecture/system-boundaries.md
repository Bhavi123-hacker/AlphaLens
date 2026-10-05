# System boundaries

Modular monolith plus separately deployed background workers later. No execution
subsystem. Source: §§6, 8–19; approved decisions govern conflicts.

```mermaid
flowchart LR
    P[Production free source: not cleared] --> A[Production adapter: blocked]
    A --> D[Canonical PIT data]
    D --> F[Versioned features: later]
    F --> M[Evaluated models: later]
    M --> R[Independent risk: later]
    R --> Q[Policy and signals: later]
    Q --> E[Evidence and explanations: later]
    E --> U[User decision]
```

No path from any component to a real broker/order service. Future manual transaction
recording is user-reported history, not order execution.

Current code: health-only local FastAPI and provider-neutral P1 contracts/eligibility/
canonical serialization/in-memory sample check, plus a bounded offline Mendeley
research-file adapter and reproducible replay. The diagram describes the future
production path, which remains blocked. Local research artifacts have a separate
RESEARCH_FIXTURE_DATASET scope and do not enter the canonical PIT path above.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. D40-D42 separately authorize P2 infrastructure
development using fixtures. The source-neutral `alphalens_data.ingestion` package
adds immutable raw landing, parser/normalizer contracts, row validation/quarantine,
canonical Parquet/JSON, replay and metadata repositories without importing FastAPI.
Acquisition is a separate byte-source protocol alongside the existing provider.py
boundary; no provider capabilities or production adapter are implied.

API owns validation/application/domain orchestration, permissions and authoritative
calculations later. Data package cannot import API/FastAPI. Workers will orchestrate
shared services; backtest and paper trading will share decision policy. Frontend
is presentation only and deferred.

PostgreSQL: canonical structured records and ledger/application history; object
storage/Parquet: raw and dataset/artifact snapshots; Redis: disposable coordination
and cache when justified. P2 technical metadata tables are owned by db/migrations;
the P5 financial/entity schema and event broker remain deferred.

Revised filings, identifier history, universe membership and adjustments must
remain reconstructible. Required future linkage: data_snapshot_id, feature version,
model/target version, risk/policy version, prediction timestamp and explanation ID.

Under D26–D35, local free PostgreSQL/container deployment is sufficient in principle;
cloud deployment is optional and cannot introduce a required paid dependency.
Future deployment still requires least privilege, private services, appropriate
transport/secret protection, reproducible setup and tested recovery. Authentication
and monitoring must have free self-hostable paths. No cloud resources are provisioned.
