# P33 native Windows operation and personal recovery

Run from CMD. Existing authentication, protected Windows credentials and original
PostgreSQL/personal stores are reused. The one-time P33 configuration has already
been created; do not rerun setup or reset the operator password.

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p33-alphalens.cmd
```

Open http://127.0.0.1:8017/login. This starts only the owned PostgreSQL instance
on15430 and the authenticated loopback application using the P33 compiled build.
Keep this foreground CMD running. Cooperative stop from another CMD:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p33-alphalens.cmd
```

Stop drains the matching application, then smart-stops its owned PostgreSQL
cluster. It does not kill unrelated Python/PostgreSQL processes. Other isolated
AlphaLens test instances using that cluster must be stopped first.

Verify deployment without changing credentials:

```bat
scripts\windows\project-python.cmd scripts\verify_p33_runtime.py
```

The recorded P33 original-state receipt must exist. Verification compares the
original personal records/account credentials and served index against the new
compiled index; it does not log in as or reset the original operator.

## Consistent personal backup

Choose a **new** private destination for every backup; existing paths are refused.
Example (change the example suffix if that directory already exists):

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\project-python.cmd -m alphalens_api.local.cli --config .local-data\p33-runtime\operator-config.json backup --destination D:\al-research\p33-backup-20261015-manual
```

The v2 manifest covers configured auth, alerts, operations, prospective and
personal SQLite stores. Personal records include preferences, named watchlists,
portfolio ledger events, journal, rules and recent research. SQLite online backup
includes committed WAL changes, with schema/owner checks, quick_check, byte sizes
and SHA256 per database. A failed backup has no complete manifest. It is not a
single distributed transaction across databases; pause manual edits for a common
cross-store checkpoint. Each database is transaction-consistent.

Backups are private operational state, including password hashes and user-entered
purchase prices. They do not copy provider roots, transient provider observations
or Windows Credential Manager token/password values. Keep filesystem ACLs and
secure the backup directory; never upload it to GitHub or the public demo. The
frozen research archive and PostgreSQL require their existing separate protection;
this command is not a PostgreSQL or full-machine backup.

Restore always targets a **new isolated directory**, never the active stores:

```bat
scripts\windows\project-python.cmd -m alphalens_api.local.cli --config .local-data\p33-runtime\operator-config.json restore --source D:\al-research\p33-backup-20261015-manual --destination D:\al-research\p33-restore-20261015-inspection
```

Verify the returned manifest/integrity result and inspect this isolated restore
before any operator-directed recovery cutover. Restored auth sessions are revoked.
The command does not repoint the running configuration or overwrite financial
records. Old p22.backup.v1 manifests remain readable; only v2 includes personal
state. A different personal owner, corrupt/missing file, unsupported schema or
occupied destination rejects restoration.

Actual P33 original online backup is recorded privately in
`.local-data\p33-original-preservation.json`; isolated test-store backup/restore
and restart equality are recorded in `.local-data\p33-personal-recovery.json`.
Do not run the test-store verifier on the original operator configuration.

## Clock repair needed on this Windows host

`w32tm /query /status` reported unsynchronized Local CMOS Clock. An ordinary
`w32tm /resync` attempt was denied (0x80070005). After an administrator verifies
the intended trusted Windows time source/network policy, run from elevated CMD:

```bat
w32tm /query /status
w32tm /resync
w32tm /query /status
```

Do not change the application timestamp gate or manually set a guessed time.
Then explicitly refresh one selected stock. A valid quote must have aware quote
time <= local receipt and last-trade time <= quote time. HTTP Date only diagnoses
skew; it does not establish independent clock synchronization. Before repair,
the UI can show a correctly labelled provider daily candle while rejecting LTP.

## Rebuild private frontend

While the application is stopped:

```bat
cd /d D:\al-research\p28-worktree\apps\web
D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe node_modules\typescript\bin\tsc -b
D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe node_modules\vite\bin\vite.js build --outDir ../../.local-data/p33-web-build --emptyOutDir
```

Check each exit code before starting. Older P31/P32 launchers select older build
directories. No scheduler, outbound notifier or provider retention is activated
by these commands.
