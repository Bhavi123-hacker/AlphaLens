-- Research manifests are isolated from ordinary verified-PIT projections.
CREATE SCHEMA IF NOT EXISTS research;
CREATE TABLE IF NOT EXISTS research.datasets (
    dataset_id text PRIMARY KEY CHECK (dataset_id ~ '^[a-f0-9]{64}$'),
    profile_id text NOT NULL CHECK (profile_id ~ '^[a-f0-9]{64}$'),
    classification text NOT NULL CHECK (classification = 'RESEARCH_ONLY'),
    final_vintage text NOT NULL CHECK (final_vintage = 'FINAL_VINTAGE_RESEARCH_ASSUMPTION'),
    payload jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CHECK (payload->>'dataset_id' IS NOT DISTINCT FROM dataset_id),
    CHECK (payload->'identity'->>'research_profile_id' IS NOT DISTINCT FROM profile_id),
    CHECK (payload->'identity'->>'usage_classification' IS NOT DISTINCT FROM classification),
    CHECK (payload->'identity'->>'final_vintage' IS NOT DISTINCT FROM final_vintage),
    CHECK (payload->'identity'->'research_profile'->>'profile'
           IS NOT DISTINCT FROM 'RESEARCH_EOD_FINAL_VINTAGE_V1')
);
CREATE OR REPLACE FUNCTION research.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Research manifest evidence is immutable'; END; $$;
DROP TRIGGER IF EXISTS immutable ON research.datasets;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON research.datasets
FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
