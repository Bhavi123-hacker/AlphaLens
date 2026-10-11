# P21 Windows CMD operations

Run from the existing checkout and D-drive-backed environment. Do not replace
junctions, delete environments or start duplicate servers. Authentication tests
and account examples use isolated TEST_ONLY identities; no real operator password
has been generated or stored by this development session.

## One-time local operator creation

Choose your own username and strong password. The example username below is an
explicit CLI argument, not a pre-created/default account. Use a real interactive
CMD terminal: passwords are prompted twice without echo and never appear in argv.
An already initialized account is preserved and bootstrap returns exit 2.

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_AUTH_ROOT=D:\al-research\p21-runtime\auth
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% bootstrap --username operator
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% diagnostics
```

Account schema/hidden prompting, duplicate refusal and permission enforcement were
verified with isolated Windows stores. Never pass a password on the command line,
pipe one into getpass, or point the auth root at the market/research archive.
Missing/unknown/unsafe auth storage fails closed; API startup performs no migration.

## Start the authenticated research backend

First CMD window, after account initialization:

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_AUTH_ROOT=D:\al-research\p21-runtime\auth
set ALPHALENS_RESEARCH_DATA_ROOT=D:\al-research\tejhq-final-vintage-v1-r3
set ALPHALENS_RESEARCH_RUN_ROOT=D:\al-research\tejhq-research-evaluation-v2-fit-parallel
set ALPHALENS_RESEARCH_REPORT_ROOT=C:\Users\Dell\AlphaLens\docs
set ALPHALENS_CATALOG_PATH=D:\al-research\p17-api\discovery.sqlite
set ALPHALENS_DAILY_ROOT=D:\al-research\p19-runtime\pipeline
set ALPHALENS_ALERTS_ROOT=D:\al-research\p20-runtime\alerts
set ALPHALENS_ALERT_MUTATIONS=true
set ALPHALENS_PORT=8017
.venv\Scripts\python.exe -m alphalens_api serve
```

This explicit local opt-in enables authenticated P20 read/acknowledgment/preferences
controls with CSRF. Set `ALPHALENS_ALERT_MUTATIONS=false` before startup if read-only
alert controls are preferred. Financial records remain GET-only in either case.
The browser run used the same startup with an isolated TEST_ONLY authentication
root and the existing `p20-runtime\browser-alerts` operational evidence store,
preserving the user's 47 original alerts. No fabricated market data was served.

If an existing exclusive local PostgreSQL workspace is deliberately configured,
retain its established ignored environment configuration for portfolio/paper reads.
Do not publish its DSN, create a competing account store or connect to a multi-owner
financial database. With no database configured these pages correctly report 503.

## Start the dashboard and sign in

Second CMD window:

```cmd
cd /d C:\Users\Dell\AlphaLens\apps\web
set PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%
set ALPHALENS_API_PROXY_TARGET=http://127.0.0.1:8017
set ALPHALENS_WEB_CACHE_DIR=D:\al-research\p21-runtime\web-cache
set ALPHALENS_WEB_OUTPUT_DIR=D:\al-research\p21-runtime\web-build
npm run dev
start "" http://127.0.0.1:5173/login
```

Use the username/password you just chose. Keep one host consistently; cookies are
host-only and localhost/127.0.0.1 are distinct cookie hosts. HTTP loopback has no
TLS protection. Protected navigation redirects to login; session refresh is real.
Settings → Account security supports password change, logout, inspection and
revocation. Settings → Notifications supports authenticated preferences. These
controls were verified in actual Chromium, including keyboard/mobile interactions.
The public process check remains:

```cmd
curl.exe http://127.0.0.1:8017/api/v1/health/live
```

Other research/portfolio/alert API reads now require a valid operator cookie.
Do not put cookies in query strings, shell history or documentation. Use the
authenticated browser's same-origin API and `/api/v1/openapi.json` for inspection.
Earlier unauthenticated curl examples in historical P17–P20 reports describe their
old phase checkpoints and are superseded by P21 authentication.

## Password and session operations

These dispatches were verified against isolated Windows stores. Session IDs below
are public metadata from `sessions`; substitute a returned real ID.

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_AUTH_ROOT=D:\al-research\p21-runtime\auth
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% change-password
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% sessions
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% revoke --session-id SESSION_ID
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% revoke
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% cleanup
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% diagnostics
```

`change-password` prompts for the current password and twice for the replacement.
All sessions are revoked on success. Lost-password recovery requires trusted local
OS/operator access, deliberate `RESET` confirmation and two hidden prompts:

```cmd
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% reset-password
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% status DISABLED
.venv\Scripts\python.exe -m alphalens_api.auth.cli --root %ALPHALENS_AUTH_ROOT% status ACTIVE
```

`DISABLED` or `LOCKED` revokes all sessions. Returning ACTIVE does not resurrect
them. Diagnostic output contains public account fields and sanitized audit events,
never hashes/tokens/CSRF/passwords. Normal success is exit 0; safe rejection exit 2.
After restart select the same auth root; valid unexpired sessions persist.
Backup/recovery requirements are in [the architecture](p21-authentication.md).

## Focused verification

```cmd
cd /d C:\Users\Dell\AlphaLens
set ALPHALENS_TEST_TEMP_ROOT=D:\al-tests
.venv\Scripts\python.exe -m pytest -W error tests\unit\test_p21_auth.py tests\integration\test_p21_api.py
.tools\bin\uv.exe lock --check
.venv\Scripts\ruff.exe check .
.venv\Scripts\mypy.exe
```

Frontend commands use the supported Node PATH above: `npm run typecheck`,
`npm run lint`, `npm test`, `npm run build`, `npm audit`. Do not use the unrelated
system Node runtime or reinstall through the existing node_modules junction.
Browser verification requires a deliberately provisioned isolated TEST_ONLY
account and protected outside-Git credential/state paths, plus the actual archive.
No application password is embedded in the browser tests or startup commands.

Stop each operator-started foreground service with Ctrl+C in its own terminal.
Do not kill unrelated Git, Docker, PostgreSQL, workers or server processes.
No enabled scheduled job, remote listener, tunnel, acquisition or external delivery
is installed. P19/P20 finite CLI processing remains available under its old evidence
gates; it does not become authorized live market acquisition through login.
