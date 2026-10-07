-- P15 local domain storage. Application validation owns FIFO/no-overdraft semantics.
CREATE SCHEMA IF NOT EXISTS portfolio;
CREATE TABLE IF NOT EXISTS portfolio.accounts (
    portfolio_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$')
);
CREATE TABLE IF NOT EXISTS portfolio.transactions (
    portfolio_id TEXT NOT NULL REFERENCES portfolio.accounts(portfolio_id),
    transaction_id TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    PRIMARY KEY (portfolio_id, transaction_id),
    CHECK (effective_at <= recorded_at)
);
CREATE INDEX IF NOT EXISTS portfolio_transaction_cutoff ON portfolio.transactions(portfolio_id, recorded_at, effective_at);
CREATE OR REPLACE FUNCTION portfolio.reject_mutation() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Immutable portfolio records cannot be updated or deleted'; END;
$$;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='portfolio_account_immutable' AND tgrelid='portfolio.accounts'::regclass) THEN
        CREATE TRIGGER portfolio_account_immutable BEFORE UPDATE OR DELETE ON portfolio.accounts
        FOR EACH ROW EXECUTE FUNCTION portfolio.reject_mutation();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='portfolio_transaction_immutable' AND tgrelid='portfolio.transactions'::regclass) THEN
        CREATE TRIGGER portfolio_transaction_immutable BEFORE UPDATE OR DELETE ON portfolio.transactions
        FOR EACH ROW EXECUTE FUNCTION portfolio.reject_mutation();
    END IF;
END $$;
