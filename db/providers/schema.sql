-- Mutable local operational state only; no market prices or credentials.
CREATE TABLE schema_version(version INTEGER PRIMARY KEY CHECK(version=1));
INSERT INTO schema_version VALUES(1);
CREATE TABLE selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 provider TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled=0));
CREATE TABLE attempts(provider TEXT NOT NULL, request_id TEXT NOT NULL,
 attempt INTEGER NOT NULL CHECK(attempt BETWEEN 1 AND 3), reserved_at REAL NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('PENDING','SUCCEEDED','FAILED','RATE_LIMITED','AUTH_REJECTED')),
 retry_at REAL, PRIMARY KEY(provider,request_id,attempt));
CREATE INDEX attempt_window ON attempts(provider,reserved_at);
CREATE TABLE audit(id INTEGER PRIMARY KEY, at REAL NOT NULL,
 event TEXT NOT NULL, provider TEXT NOT NULL);
