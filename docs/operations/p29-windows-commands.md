# P29 Windows runbook (existing installation, no paid services)

The isolated branch lives at D:/al-research/p28-worktree. C:/Users/Dell/AlphaLens
remains the clean P26 branch, untouched. Existing .venv/node_modules junctions
are reused. project-python.cmd pins imports to the correct worktree.

## Start the actual operator application

A new private operator-config.json was prepared from the existing final-completion
config, retaining actual auth,47alerts,operations,research and daily store paths.
Only compiled frontend_root and disabled provider-state root are updated. Existing
operator account is initialized; no password/account was created/reset. Config
readiness check PASSED with PostgreSQL NOT_CONFIGURED and policy gates separate.
Tests exercised the same launcher against a separate TEST_ONLY operator/store
on8028; real operator HTTP mutations were not performed during the sprint.

```cmd
cd /d D:\al-research\p28-worktree
scripts\windows\check-alphalens.cmd D:\al-research\p29-runtime\operator-config.json
scripts\windows\start-alphalens.cmd D:\al-research\p29-runtime\operator-config.json
```

After LOCAL_PROCESS_READY open http://127.0.0.1:8017/login in your browser and use
your existing local operator credentials. One foreground process serves compiled
React+authenticated API. The new page is /intelligence; stock pages contain the
Evidence Passport. Settings contains provider comparison and account controls.
No Node development server is needed for normal use. No scheduler or external
notifications are enabled. Startup defaults native library threads1 unless an
operator explicitly configured a different value. In a second CMD:

```cmd
cd /d D:\al-research\p28-worktree
scripts\windows\check-alphalens.cmd D:\al-research\p29-runtime\operator-config.json
scripts\windows\stop-alphalens.cmd D:\al-research\p29-runtime\operator-config.json
```

Stop cooperates only with the private owned nonce; never kills unrelated processes.
Port conflicts/duplicate launches are rejected. Services used for tests were stopped.
Do not replace operator config with TEST_ONLY config or supply test credentials.

## Account diagnostics / setup if installing into a NEW uninitialized location

```cmd
scripts\windows\project-python.cmd -m alphalens_api.auth.cli --root D:\al-research\p21-runtime\operator-auth diagnostics
```

Current account is present; do not bootstrap over it. Existing hidden-prompt
bootstrap for a genuinely NEW root, if needed on another installation:

```cmd
scripts\windows\project-python.cmd -m alphalens_api.auth.cli --root "YOUR_NEW_PRIVATE_AUTH_ROOT" bootstrap --username YOUR_CHOSEN_USERNAME
```

Do not put passwords in arguments. Account/session/password controls are in
Settings; existing authorized local recovery procedures remain in P21 docs.

## Providers, daily evidence and notifications

These verified read commands make no external market request:

```cmd
scripts\windows\project-python.cmd -m workers.providers.cli comparison
scripts\windows\project-python.cmd -m workers.providers.cli status --root D:\al-research\p28-runtime\provider-state
scripts\windows\project-python.cmd -m workers.providers.cli capabilities --provider upstox
scripts\windows\project-python.cmd -m workers.daily.cli status --root D:\al-research\p19-runtime\pipeline
scripts\windows\project-python.cmd -m workers.daily.cli prospective-status --root D:\al-research\p19-runtime\pipeline
```

Use authenticated Notifications and monitoring/Data Health pages for genuine alert
and operational history. P28 runbook covers bounded offline fixture replay,
planning, secure future Analytics import, retry and recovery commands. Do not
repeat Alpha credential/probe requests; original key migration succeeded and
only RELIANCE.BSE was found. Plaintext removal is now safe for the operator after
confirming same-user credential access; nothing was deleted automatically.

## Backup / new-location restore

The exact command interfaces were executed on isolated mutable test state. Choose
NEW destinations for your operator backup; pause mutations for cross-store
consistency. SQLite online backup+manifest and isolated restore are verified;
restored sessions are revoked, original stores are never overwritten.

```cmd
scripts\windows\backup-alphalens.cmd D:\al-research\p29-runtime\operator-config.json D:\al-research\p29-runtime\operator-backup-NEW
scripts\windows\project-python.cmd -m alphalens_api.operations.cli restore --source D:\al-research\p29-runtime\operator-backup-NEW --destination D:\al-research\p29-runtime\operator-restore-NEW
```

These do not back up PostgreSQL or copy8.5GB research. See P29 PG readiness for
explicit authorized17 bootstrap and independent pg_dump/pg_restore guidance.
No real financial DB backup/restore is claimed locally.

## Focused verification / demo

```cmd
set "ALPHALENS_TEST_TEMP_ROOT=D:\al-tests"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
scripts\windows\project-python.cmd -m pytest -W error -ra tests\unit\test_p29_intelligence.py tests\unit\test_p29_postgres_setup.py tests\unit\test_p29_public_demo.py tests\integration\test_p29_intelligence_api.py tests\integration\test_p29_postgres.py
set "PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%"
cd apps\web
npm test
npm run typecheck
npm run lint
set "ALPHALENS_DEMO_OUTPUT_DIR=D:\al-research\p29-runtime\public-demo"
npm run build:demo
npm run preview:demo
```

Demo opens127.0.0.1:8031; no login or private API, all examples synthetic. Ctrl+C
stops only this preview. Public-demo runbook covers independent browser tests,
retained licences and a future zero-subscription static publication plan.
Do not publish the private backend, unrestricted archive or account directories.
