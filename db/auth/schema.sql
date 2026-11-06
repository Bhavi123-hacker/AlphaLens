PRAGMA user_version=1;
CREATE TABLE accounts (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 account_id TEXT NOT NULL UNIQUE, username TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role='ADMIN'),
 status TEXT NOT NULL CHECK(status IN ('ACTIVE','DISABLED','LOCKED')),
 created_at REAL NOT NULL, password_changed_at REAL NOT NULL
);
CREATE TABLE sessions (
 session_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
 account_id TEXT NOT NULL REFERENCES accounts(account_id), csrf_secret TEXT NOT NULL,
 created_at REAL NOT NULL, last_seen REAL NOT NULL, absolute_expires REAL NOT NULL,
 revoked_at REAL
);
CREATE INDEX sessions_expiration ON sessions(absolute_expires);
CREATE TABLE attempts (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 window_start REAL NOT NULL, failures INTEGER NOT NULL, blocked_until REAL NOT NULL
);
CREATE TABLE audit (
 sequence INTEGER PRIMARY KEY, event_type TEXT NOT NULL, event_at REAL NOT NULL,
 account_id TEXT, session_id TEXT
);
