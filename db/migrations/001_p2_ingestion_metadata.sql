-- P2 technical metadata only; no P5 financial/entity schema is introduced.
CREATE SCHEMA IF NOT EXISTS p2_ingestion;
CREATE TABLE IF NOT EXISTS p2_ingestion.raw_artifacts (
    artifact_id text PRIMARY KEY CHECK (artifact_id ~ '^[a-f0-9]{64}$'),
    manifest jsonb NOT NULL CHECK (manifest->>'artifact_id' = artifact_id)
);
CREATE TABLE IF NOT EXISTS p2_ingestion.runs (
    run_id text PRIMARY KEY CHECK (run_id ~ '^[a-f0-9]{64}$'),
    artifact_id text NOT NULL REFERENCES p2_ingestion.raw_artifacts(artifact_id),
    report jsonb NOT NULL CHECK (report->>'run_id' = run_id)
        CHECK (report->>'artifact_id' = artifact_id)
);
CREATE OR REPLACE FUNCTION p2_ingestion.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'P2 ingestion metadata is immutable';
END;
$$;
DROP TRIGGER IF EXISTS raw_artifacts_immutable ON p2_ingestion.raw_artifacts;
CREATE TRIGGER raw_artifacts_immutable BEFORE UPDATE OR DELETE ON p2_ingestion.raw_artifacts
FOR EACH ROW EXECUTE FUNCTION p2_ingestion.reject_mutation();
DROP TRIGGER IF EXISTS runs_immutable ON p2_ingestion.runs;
CREATE TRIGGER runs_immutable BEFORE UPDATE OR DELETE ON p2_ingestion.runs
FOR EACH ROW EXECUTE FUNCTION p2_ingestion.reject_mutation();
