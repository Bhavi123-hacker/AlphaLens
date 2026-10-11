PRAGMA user_version=1;
CREATE TABLE IF NOT EXISTS alerts (
 id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, evidence TEXT NOT NULL,
 evidence_hash TEXT NOT NULL, category TEXT NOT NULL, severity TEXT NOT NULL,
 event_code TEXT NOT NULL, event_at TEXT NOT NULL, created_at TEXT NOT NULL,
 lifecycle TEXT NOT NULL DEFAULT 'NEW', delivery TEXT NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT, delivered_at TEXT,
 delivery_reason TEXT, group_key TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS alerts_time ON alerts(created_at DESC,id);
CREATE TABLE IF NOT EXISTS seen (event_key TEXT PRIMARY KEY, alert_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (source_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
 sequence INTEGER PRIMARY KEY, alert_id TEXT, action TEXT NOT NULL,
 at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), payload TEXT NOT NULL
);
