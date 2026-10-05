# Database boundary

Single schema/migration owner. P5 financial/entity migrations remain deferred.
`migrations/001_p2_ingestion_metadata.sql` owns the explicitly authorized P2
technical metadata schema: immutable raw-artifact manifests and processing reports,
with SHA256 IDs, primary/foreign keys and mutation-rejecting triggers. No financial
entity tables or market records are stored in PostgreSQL in P2.

Apply this idempotent SQL using a locally configured PostgreSQL administrative
connection before running `alphalens-ingest --postgres`. Do not commit the DSN.
The disposable `scripts/verify_p2_postgres.py` runner applies it automatically in
a dedicated test database, verifies persistence and removes its own test volume.
