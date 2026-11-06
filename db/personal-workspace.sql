-- P32 separate local operator records; original PostgreSQL schemas stay unchanged.
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE records(
 owner TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
 body TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(owner,kind,id)
);
CREATE TABLE audit(
 id INTEGER PRIMARY KEY, owner TEXT NOT NULL, operation TEXT NOT NULL,
 record_id TEXT NOT NULL, at TEXT NOT NULL
);
