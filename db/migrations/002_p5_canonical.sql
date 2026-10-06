-- P5 canonical ownership: immutable financial evidence, not features or models.
CREATE SCHEMA IF NOT EXISTS canonical;
CREATE TABLE IF NOT EXISTS canonical.securities (
 security_id text PRIMARY KEY CHECK (length(security_id) BETWEEN 1 AND 256),
 exchange text NOT NULL CHECK (exchange = 'NSE'),
 classification text NOT NULL CHECK (classification IN ('TEST_ONLY','RESEARCH_FIXTURE')),
 UNIQUE(security_id, classification)
);
CREATE TABLE IF NOT EXISTS canonical.record_revisions (
 record_key text PRIMARY KEY CHECK (record_key ~ '^[a-f0-9]{64}$'),
 kind text NOT NULL CHECK (kind IN ('IDENTITY','MEMBERSHIP','SESSION','BAR','ACTION','QUALITY')),
 source text NOT NULL,
 logical_record_id text NOT NULL,
 revision_id text NOT NULL,
 revision_number integer NOT NULL CHECK (revision_number > 0),
 parent_key text REFERENCES canonical.record_revisions(record_key),
 security_id text,
 classification text NOT NULL CHECK (classification IN ('TEST_ONLY','RESEARCH_FIXTURE')),
 effective_from date NOT NULL,
 effective_to date CHECK (effective_to > effective_from),
 published_at timestamptz,
 available_at timestamptz,
 ingested_at timestamptz NOT NULL,
 artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[a-f0-9]{64}$'),
 payload jsonb NOT NULL,
 FOREIGN KEY(security_id, classification) REFERENCES canonical.securities(security_id, classification),
 UNIQUE(kind,source,logical_record_id,revision_id),
 UNIQUE(kind,source,logical_record_id,revision_number),
 UNIQUE(parent_key), UNIQUE(record_key,kind),
 CHECK ((revision_number = 1) = (parent_key IS NULL)),
 CHECK (available_at <= ingested_at AND published_at <= ingested_at AND published_at <= available_at),
 CHECK (payload->>'schema_version' = 'p5.canonical.v1'),
 CHECK (payload->>'kind' = kind AND payload->>'logical_record_id' = logical_record_id
   AND payload->>'revision_id' = revision_id AND (payload->>'revision_number')::integer = revision_number),
 CHECK ((payload->>'security_id') IS NOT DISTINCT FROM security_id),
 CHECK ((payload->>'effective_from')::date = effective_from
   AND (payload->>'effective_to')::date IS NOT DISTINCT FROM effective_to),
 CHECK (payload->'provenance'->>'source' = source AND payload->'provenance'->>'classification' = classification
   AND payload->'provenance'->>'artifact_sha256' = artifact_sha256),
 CHECK ((payload->'provenance'->>'available_at')::timestamptz IS NOT DISTINCT FROM available_at
   AND (payload->'provenance'->>'published_at')::timestamptz IS NOT DISTINCT FROM published_at
   AND (payload->'provenance'->>'ingested_at')::timestamptz = ingested_at),
 CHECK ((available_at IS NULL) = (payload->'provenance'->>'availability_basis' = 'UNKNOWN'))
);
CREATE INDEX IF NOT EXISTS canonical_revision_pit ON canonical.record_revisions
 (kind,security_id,available_at,revision_number);
CREATE INDEX IF NOT EXISTS canonical_revision_effective ON canonical.record_revisions
 (security_id,effective_from,effective_to);
CREATE OR REPLACE FUNCTION canonical.check_parent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p canonical.record_revisions;
BEGIN
 IF NEW.parent_key IS NOT NULL THEN
  SELECT * INTO STRICT p FROM canonical.record_revisions WHERE record_key = NEW.parent_key;
  IF ROW(p.kind,p.source,p.logical_record_id,p.security_id,p.classification)
     IS DISTINCT FROM ROW(NEW.kind,NEW.source,NEW.logical_record_id,NEW.security_id,NEW.classification)
     OR NEW.revision_number <> p.revision_number+1 OR NEW.ingested_at < p.ingested_at
     OR NEW.available_at < p.available_at
     OR NEW.payload->>'supersedes_revision_id' IS DISTINCT FROM p.revision_id THEN
   RAISE EXCEPTION 'Invalid canonical revision chain';
  END IF;
 END IF;
 RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS canonical_revision_parent ON canonical.record_revisions;
CREATE TRIGGER canonical_revision_parent BEFORE INSERT ON canonical.record_revisions
 FOR EACH ROW EXECUTE FUNCTION canonical.check_parent();

CREATE TABLE IF NOT EXISTS canonical.security_identity_history (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'IDENTITY' CHECK(kind='IDENTITY'),
 source_security_id text NOT NULL, symbol text NOT NULL, isin text, series text,
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE INDEX IF NOT EXISTS canonical_identity_symbol ON canonical.security_identity_history(symbol);
CREATE INDEX IF NOT EXISTS canonical_identity_isin ON canonical.security_identity_history(isin) WHERE isin IS NOT NULL;
CREATE TABLE IF NOT EXISTS canonical.membership_evidence (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'MEMBERSHIP' CHECK(kind='MEMBERSHIP'),
 listing_status text NOT NULL CHECK(listing_status IN ('LISTED','DELISTED','NOT_YET_LISTED','UNKNOWN')),
 security_type text NOT NULL CHECK(security_type IN ('COMMON_EQUITY','ETF','REIT','INVIT','PREFERENCE','DEBT','UNKNOWN')),
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE TABLE IF NOT EXISTS canonical.trading_sessions (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'SESSION' CHECK(kind='SESSION'),
 session_date date NOT NULL, exchange text NOT NULL CHECK(exchange='NSE'),
 status text NOT NULL CHECK(status IN ('VERIFIED_TRADING_SESSION','VERIFIED_NON_TRADING_SESSION','UNKNOWN_SESSION_STATUS')),
 calendar_evidence_reference text,
 CHECK(status='UNKNOWN_SESSION_STATUS' OR calendar_evidence_reference IS NOT NULL),
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE TABLE IF NOT EXISTS canonical.quality_reports (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'QUALITY' CHECK(kind='QUALITY'),
 session_date date NOT NULL, report_sha256 text NOT NULL CHECK(report_sha256 ~ '^[a-f0-9]{64}$'),
 status text NOT NULL CHECK(status IN ('VALID','DEGRADED','REJECTED')),
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE TABLE IF NOT EXISTS canonical.corporate_actions (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'ACTION' CHECK(kind='ACTION'),
 corporate_action_id text NOT NULL,
 event_type text NOT NULL CHECK(event_type IN ('SPLIT','BONUS','DIVIDEND','RIGHTS','MERGER','DEMERGER','SYMBOL_CHANGE','DELISTING','OTHER')),
 factor numeric(38,18) CHECK(factor > 0 AND factor < 'Infinity'::numeric),
 cash_value numeric(38,18) CHECK(cash_value >= 0 AND cash_value < 'Infinity'::numeric),
 currency text CHECK(currency='INR'),
 CHECK(cash_value IS NULL OR currency IS NOT NULL),
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE TABLE IF NOT EXISTS canonical.market_bars_eod (
 record_key text PRIMARY KEY, kind text NOT NULL DEFAULT 'BAR' CHECK(kind='BAR'),
 security_id text NOT NULL REFERENCES canonical.securities(security_id), session_date date NOT NULL,
 price_basis text NOT NULL CHECK(price_basis IN ('OBSERVED_UNKNOWN_BASIS','RAW_UNADJUSTED','ADJUSTED')),
 open numeric(38,18), high numeric(38,18), low numeric(38,18), close numeric(38,18), volume bigint,
 currency text CHECK(currency='INR'), quality_key text REFERENCES canonical.quality_reports(record_key),
 rejection_reason_codes text[] NOT NULL,
 corporate_action_key text REFERENCES canonical.corporate_actions(record_key),
 original_price_key text REFERENCES canonical.market_bars_eod(record_key),
 CHECK ((open IS NULL AND high IS NULL AND low IS NULL AND close IS NULL AND volume IS NULL
    AND cardinality(rejection_reason_codes)>0)
   OR (open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL AND volume IS NOT NULL
    AND open>0 AND high>0 AND low>0 AND close>0 AND high<'Infinity'::numeric
    AND high>=open AND high>=close AND high>=low AND low<=open AND low<=close AND volume>=0)),
 CHECK ((price_basis='ADJUSTED') = (corporate_action_key IS NOT NULL AND original_price_key IS NOT NULL)),
 FOREIGN KEY(record_key,kind) REFERENCES canonical.record_revisions(record_key,kind)
);
CREATE INDEX IF NOT EXISTS canonical_bar_history ON canonical.market_bars_eod(security_id,session_date);
CREATE INDEX IF NOT EXISTS canonical_bar_session ON canonical.market_bars_eod(session_date);
-- Fundamentals contract exists in Python; no facts accepted until free PIT evidence is cleared.
CREATE TABLE IF NOT EXISTS canonical.normalized_evidence (
 normalized_record_id text PRIMARY KEY,
 artifact_id text NOT NULL REFERENCES p2_ingestion.raw_artifacts(artifact_id),
 normalization_version text NOT NULL, payload jsonb NOT NULL,
 UNIQUE(normalized_record_id,artifact_id)
);
CREATE TABLE IF NOT EXISTS canonical.quarantine_evidence (
 quarantine_key text PRIMARY KEY,
 artifact_id text NOT NULL REFERENCES p2_ingestion.raw_artifacts(artifact_id), payload jsonb NOT NULL,
 UNIQUE(quarantine_key,artifact_id)
);
CREATE TABLE IF NOT EXISTS canonical.record_lineage (
 lineage_id text PRIMARY KEY,
 record_key text NOT NULL REFERENCES canonical.record_revisions(record_key),
 artifact_id text NOT NULL REFERENCES p2_ingestion.raw_artifacts(artifact_id),
 normalized_record_id text, quarantine_key text, source_record_id text, evidence_reference text NOT NULL,
 CHECK ((normalized_record_id IS NULL) <> (quarantine_key IS NULL)),
 FOREIGN KEY(normalized_record_id,artifact_id) REFERENCES canonical.normalized_evidence(normalized_record_id,artifact_id),
 FOREIGN KEY(quarantine_key,artifact_id) REFERENCES canonical.quarantine_evidence(quarantine_key,artifact_id)
);
CREATE INDEX IF NOT EXISTS canonical_lineage_record ON canonical.record_lineage(record_key);
CREATE TABLE IF NOT EXISTS canonical.dataset_inputs (
 input_id text PRIMARY KEY CHECK(input_id ~ '^[a-f0-9]{64}$'), payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS canonical.input_records (
 input_id text REFERENCES canonical.dataset_inputs(input_id),
 record_key text REFERENCES canonical.record_revisions(record_key), PRIMARY KEY(input_id,record_key)
);
CREATE TABLE IF NOT EXISTS canonical.dataset_snapshots (
 dataset_id text PRIMARY KEY CHECK(dataset_id ~ '^[a-f0-9]{64}$'),
 input_id text NOT NULL REFERENCES canonical.dataset_inputs(input_id),
 knowledge_cutoff timestamptz NOT NULL, start_session date NOT NULL, end_session date NOT NULL,
 payload jsonb NOT NULL,
 CHECK(start_session<=end_session),
 CHECK(payload->>'dataset_id'=dataset_id AND payload->>'input_id'=input_id)
);
CREATE INDEX IF NOT EXISTS canonical_snapshot_lookup ON canonical.dataset_snapshots(input_id,knowledge_cutoff,start_session,end_session);
CREATE OR REPLACE FUNCTION canonical.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Canonical evidence is immutable'; END; $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['securities','record_revisions','security_identity_history','membership_evidence',
 'trading_sessions','quality_reports','corporate_actions','market_bars_eod','normalized_evidence',
 'quarantine_evidence','record_lineage','dataset_inputs','input_records','dataset_snapshots'] LOOP
 EXECUTE format('DROP TRIGGER IF EXISTS immutable ON canonical.%I',t);
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON canonical.%I FOR EACH ROW EXECUTE FUNCTION canonical.reject_mutation()',t);
 END LOOP;
END $$;

-- Domain projections must agree with their immutable canonical payload.
CREATE OR REPLACE FUNCTION canonical.check_projection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p jsonb; n jsonb; k text; v jsonb;
BEGIN
 SELECT payload INTO STRICT p FROM canonical.record_revisions WHERE record_key=NEW.record_key;
 n := to_jsonb(NEW)-'record_key'-'kind';
 FOR k,v IN SELECT * FROM jsonb_each(n) LOOP
  IF TG_TABLE_NAME IN ('security_identity_history','membership_evidence') THEN
   IF v IS DISTINCT FROM COALESCE(p->'fact'->k,'null'::jsonb) THEN
    RAISE EXCEPTION 'Canonical identity/membership projection mismatch'; END IF;
  ELSIF TG_TABLE_NAME='quality_reports' THEN
   IF k='status' THEN p:=jsonb_set(p,'{status}',p->'evidence'->'report'->'status');
   ELSE p:=jsonb_set(p,ARRAY[k],p->'evidence'->k); END IF;
   IF v IS DISTINCT FROM p->k THEN RAISE EXCEPTION 'Canonical quality projection mismatch'; END IF;
  ELSIF TG_TABLE_NAME='market_bars_eod' AND k IN ('open','high','low','close','volume') THEN
   IF k='volume' THEN
    IF (v#>>'{}')::bigint IS DISTINCT FROM (p->'values'->>k)::bigint THEN
     RAISE EXCEPTION 'Canonical volume projection mismatch'; END IF;
   ELSIF (v#>>'{}')::numeric IS DISTINCT FROM (p->'values'->>k)::numeric THEN
    RAISE EXCEPTION 'Canonical price projection mismatch'; END IF;
  ELSIF TG_TABLE_NAME='market_bars_eod' AND k IN ('corporate_action_key','original_price_key') THEN
   IF v IS DISTINCT FROM COALESCE(p->'adjustment'->k,'null'::jsonb) THEN
    RAISE EXCEPTION 'Canonical adjustment reference mismatch'; END IF;
  ELSIF k IN ('factor','cash_value') THEN
   IF (v#>>'{}')::numeric IS DISTINCT FROM (p->>k)::numeric THEN
    RAISE EXCEPTION 'Canonical action value projection mismatch'; END IF;
  ELSIF v IS DISTINCT FROM COALESCE(p->k,'null'::jsonb) THEN
   RAISE EXCEPTION 'Canonical projection mismatch';
  END IF;
 END LOOP;
 RETURN NEW;
END; $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['security_identity_history','membership_evidence','trading_sessions',
 'quality_reports','corporate_actions','market_bars_eod'] LOOP
 EXECUTE format('DROP TRIGGER IF EXISTS projection_agreement ON canonical.%I',t);
 EXECUTE format('CREATE TRIGGER projection_agreement BEFORE INSERT ON canonical.%I FOR EACH ROW EXECUTE FUNCTION canonical.check_projection()',t);
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION canonical.check_record_lineage() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM canonical.record_lineage l
   JOIN p2_ingestion.raw_artifacts a USING(artifact_id) WHERE l.record_key=NEW.record_key
   AND a.manifest->>'sha256'=NEW.artifact_sha256 AND a.manifest->'spec'->>'source'=NEW.source
   AND a.manifest->'spec'->>'classification'=NEW.classification) THEN
  RAISE EXCEPTION 'Canonical source/checksum lineage missing'; END IF;
 IF NOT EXISTS (SELECT 1 FROM canonical.record_lineage l JOIN canonical.normalized_evidence n
   USING(normalized_record_id) WHERE l.record_key=NEW.record_key
   AND n.normalization_version='p5.reference.v1' AND n.payload=NEW.payload) THEN
  RAISE EXCEPTION 'Canonical normalized declaration missing'; END IF;
 RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS canonical_required_lineage ON canonical.record_revisions;
CREATE CONSTRAINT TRIGGER canonical_required_lineage AFTER INSERT ON canonical.record_revisions
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION canonical.check_record_lineage();
