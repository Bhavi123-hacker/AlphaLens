# Database boundary

Single schema/migration owner. P5 canonical financial/entity development is now
authorized by D46-D48; production market-data use remains NOT_CLEARED.
`migrations/001_p2_ingestion_metadata.sql` owns the explicitly authorized P2
technical metadata schema: immutable raw-artifact manifests and processing reports,
with SHA256 IDs, primary/foreign keys and mutation-rejecting triggers. No financial
entity tables or market records are stored in PostgreSQL in P2.

Apply this idempotent SQL using a locally configured PostgreSQL administrative
connection before running `alphalens-ingest --postgres`. Do not commit the DSN.
The disposable `scripts/verify_p2_postgres.py` runner applies it automatically in
a dedicated test database, verifies persistence and removes its own test volume.

Apply `002_p5_canonical.sql` after 001 for canonical securities, immutable revision
headers/domain projections, normalized/quarantine lineage and pinned datasets.
Temporal identity/membership payloads reuse P4 facts; quality preserves P3 reports.
Financial, revision, projection, classification and lineage constraints are enforced
in PostgreSQL. Fundamental facts are intentionally not populated or stored yet.
Migrations are replayable without modifying existing records; mutation triggers
protect canonical tables. The caller owns transactions; batch writes include all
required lineage before the deferred constraints run.

`scripts/verify_p5_postgres.py` verifies real PostgreSQL 17, migrations, constraints,
indexes, immutable writes, revisions, PIT reads, snapshot identity and repeated CLI
builds. It drops its isolated test database and dedicated container/network/volume.
See [schema relationships and index rationale](../docs/data/p5-canonical-data-model.md).
