-- Immutable event stream, unique records only. Reports pin their observed P15 vintage.
CREATE TABLE IF NOT EXISTS portfolio.paper_accounts (
    portfolio_id TEXT PRIMARY KEY REFERENCES portfolio.accounts(portfolio_id),
    starting_cash TEXT NOT NULL,
    classification TEXT NOT NULL CHECK (classification IN ('PAPER','TEST_ONLY_PAPER'))
);
CREATE TABLE IF NOT EXISTS portfolio.paper_events (
    portfolio_id TEXT NOT NULL REFERENCES portfolio.paper_accounts(portfolio_id),
    sequence BIGINT NOT NULL CHECK (sequence > 0),
    record_id TEXT NOT NULL CHECK (record_id ~ '^[a-f0-9]{64}$'),
    kind TEXT NOT NULL CHECK (kind IN ('ORDER_INTENT','ORDER_EVENT','FILL','REPORT')),
    payload JSONB NOT NULL,
    content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (portfolio_id, record_id),
    UNIQUE (portfolio_id, sequence)
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='paper_account_immutable' AND tgrelid='portfolio.paper_accounts'::regclass) THEN
        CREATE TRIGGER paper_account_immutable BEFORE UPDATE OR DELETE ON portfolio.paper_accounts
        FOR EACH ROW EXECUTE FUNCTION portfolio.reject_mutation();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='paper_event_immutable' AND tgrelid='portfolio.paper_events'::regclass) THEN
        CREATE TRIGGER paper_event_immutable BEFORE UPDATE OR DELETE ON portfolio.paper_events
        FOR EACH ROW EXECUTE FUNCTION portfolio.reject_mutation();
    END IF;
END $$;
