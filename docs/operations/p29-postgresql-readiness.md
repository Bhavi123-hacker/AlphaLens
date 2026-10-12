# PostgreSQL17: explicit operator setup, existing data preserved

Actual local assessment:127.0.0.1:5432 accepts TCP; authenticated server version
and authorization are unavailable. Anonymous read-only metadata access was
rejected. Existing C:/Program Files/PostgreSQL/17 and18 contain data directories
without the required bin tools; no identified Windows service. Docker client
probe timed out in15s; no daemon restart/prune or shared container interruption.
No database, role, holding, order, fill or valuation was created during the local
assessment. Normal Portfolio/Paper APIs remain NOT_CONFIGURED, not simulated.

## Prepared safe workflow

```cmd
cd /d D:\al-research\p28-worktree
scripts\windows\project-python.cmd -m alphalens_api.local.postgres diagnose
scripts\windows\project-python.cmd -m alphalens_api.local.postgres bootstrap
scripts\windows\project-python.cmd -m alphalens_api.local.postgres check
```

Diagnose is verified and non-destructive. Bootstrap is an explicit interactive
operator operation, not run automatically or locally during the sprint. Requires
an authenticated existing loopback PostgreSQL17 administrator and securely prompts
without echo. It refuses an existing target credential/database/role, non17server
and audit configurations that might log password-verifier DDL. No tool install,
existing cluster migration/reset or recreation is performed. On partial failure
preserve created state for operator inspection; never auto-delete a populated DB.

Only NEW alphalens_research_local and alphalens_research_reader, original003P15/
004P16 schema plus db/local/p29_schema.sql version tracking. Reader has SELECT/
USAGE/CONNECT only, no superuser/createDB/createRole/replication, default read-only
and8connections. Password is generated randomly and encrypted by libpq SCRAM,
not custom cryptography. Connection URI is readback-verified in current-user
Windows Credential Manager target AlphaLens/PostgreSQL/ResearchReadOnly.
The public API never returns it; config contains only the fixed target name.

After successful operator bootstrap add this nonsecret field to the operator's
private local JSON configuration and restart via the existing launcher:

```json
"database_credential_target": "AlphaLens/PostgreSQL/ResearchReadOnly"
```

This enables real read-only schema access; empty account tables remain empty.
It does not import private financial records or invent demonstration holdings.
Five offline safety tests are verified. A guarded isolated PostgreSQL17 CI test
verifies new schema/reader/no accounts and existing-object preservation. Local
integration is skipped because no authorized TEST_ONLY PostgreSQL17 connection
is supplied; actual corrected implementation CI38241808202 passed this case within909passed/8skipped.
This proves isolated PG17 integration, not access to the unconfigured local financial DB.

Use official PostgreSQL17 pg_dump/pg_restore with an operator-supplied secured
credential path for financial DB backups; this sprint does not claim an executed
PG backup/restore. Existing verified SQLite online-backup/new-location restore
commands remain in p24-windows-local-deployment.md. Never blindly restore over
real auth/alerts/research or17/18 existing data.
