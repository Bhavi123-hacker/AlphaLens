# P24 native Windows local deployment

One foreground FastAPI/Uvicorn process serves the compiled dashboard and API on
127.0.0.1:8017. Node/Vite is needed for a build, not daily operation. No installer,
package download, Windows service/task, tunnel, data acquisition or external
delivery is run by the operational scripts. Existing Python and node_modules
D-drive junctions are reused. Docker is not required for this native milestone.

## Existing-environment build and configuration

```cmd
cd /d C:\Users\Dell\AlphaLens
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
node --version
.venv\Scripts\python.exe --version
.tools\bin\uv.exe lock --check
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p22-p25-runtime\web-deployed
cd apps\web
npm run build
cd ..\..
copy docs\operations\local-config.example.json D:\al-research\p22-p25-runtime\local-config.json
```

Build and configuration paths are examples reflecting the retained machine layout.
Review the private JSON file before use; select the **existing** initialized P21
auth root where one exists. The example's `operator-auth` path is a new operator
location, not a claim that an account already exists there. Never replace a populated
store. Keep database URLs/SMTP secrets out of JSON and Git; optional PostgreSQL URL
is supplied through existing ALPHALENS_DATABASE_URL private environment configuration.
No configured database means portfolio/paper readiness remains NOT_CONFIGURED/503.

If there is no account at the selected root, explicitly initialize it once:

```cmd
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root D:\al-research\p21-runtime\operator-auth bootstrap --username operator
```

This prompts twice without echo; no password is supplied on a command line. An
existing account is never overwritten. Account change/recovery/session commands
remain in [P21 operator instructions](../security/p21-windows-commands.md).

## Setup, start, check, stop

```cmd
cd /d C:\Users\Dell\AlphaLens
scripts\windows\setup-local.cmd D:\al-research\p22-p25-runtime\local-config.json
scripts\windows\start-alphalens.cmd D:\al-research\p22-p25-runtime\local-config.json
```

Wait for LOCAL_PROCESS_READY, then open `http://127.0.0.1:8017/login`. Start remains
in its own terminal. In a second CMD:

```cmd
cd /d C:\Users\Dell\AlphaLens
scripts\windows\check-alphalens.cmd D:\al-research\p22-p25-runtime\local-config.json
scripts\windows\stop-alphalens.cmd D:\al-research\p22-p25-runtime\local-config.json
```

Setup explicitly initializes only the additive operations schema. It validates the
compiled entry, store/paths/catalog/account readiness and reports safe component
statuses. `local_setup=PASSED` means configured resources are ready; `api_running`
is separately verified through bounded loopback HTTP. An offline process is never
called an HTTP success. PostgreSQL NOT_CONFIGURED is optional for historical
research, mandatory for financial records. Known policy blockers remain separate.

A kernel lock prevents duplicate launch. Startup binds its own loopback socket
before publishing ownership. Port conflicts are rejected without adopting a
listener. The cooperative stop command writes a nonce-matched request inside the
owner-restricted operations/local directory; only the owning foreground server
observes it. It waits for STOPPED and never kills a PID, enumerates/kills Python or
Node, touches PostgreSQL/Docker, or calls an HTTP shutdown endpoint. Ctrl+C in the
owning terminal is also supported. Kernel locks release after interruption; restart
publishes a fresh nonce, ignores stale shutdown requests and preserves databases.
Private instance/control files are mutable process state, not research evidence.

## Backup and isolated restore

Use a **new** directory per backup; pause mutations for cross-store consistency.

```cmd
scripts\windows\backup-alphalens.cmd D:\al-research\p22-p25-runtime\local-config.json D:\al-research\p22-p25-runtime\backup-NEW
.venv\Scripts\python.exe -m alphalens_api.operations.cli restore --source D:\al-research\p22-p25-runtime\backup-NEW --destination D:\al-research\p22-p25-runtime\restore-NEW
```

SQLite online backups include WAL transactions, validate integrity/schema/checksums,
publish the manifest last and retain owner-only permissions. Restore requires a
new destination, verifies the full manifest, revokes restored sessions and never
overwrites original accounts/alerts/operational state. PostgreSQL and frozen
research are outside this mutable-state backup; use their established independent
procedures. See [P22 recovery](p22-monitoring-recovery.md).

## HTTP and packaging security

Public resources are only the compiled shell/allowlisted asset extensions and
license notices. API dependencies remain mandatory, including protected OpenAPI.
Unknown API paths never return SPA success; dot files, data/model/SQLite files,
arbitrary paths and remote peers are rejected. Private storage cannot overlap the
frontend tree. Same-origin login/CSRF writes require the explicitly configured
8017 Origin. Cookies remain HttpOnly/SameSite Strict on actual loopback HTTP;
there is no false HTTPS or multi-owner claim. Shell CSP permits local scripts,
blocks external scripts/framing and permits existing inline styling only. Dynamic
chart loading and canvas are covered by actual deployed Chromium tests.

Native deployment uses the frozen local dependency lock, not the vulnerable image.
Strict container gate remains independent. No public deployment is cleared.
