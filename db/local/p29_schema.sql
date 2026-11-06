-- Metadata only; immutable P15/P16 migration files remain unchanged.
CREATE SCHEMA alphalens_local;
CREATE TABLE alphalens_local.setup_version (
    singleton BOOLEAN PRIMARY KEY CHECK(singleton),
    version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO alphalens_local.setup_version(singleton,version)
VALUES(TRUE,'p29.local-postgres.v1');
