# P28 Windows operations (CMD)

The isolated worktree shares the existing D-backed environment without reinstalling it.
Use `project-python.cmd`: it pins PYTHONPATH to this checkout rather than following
the shared environment's original editable-package mapping. Original C/P26 stays clean.
Secrets are never command arguments. No command below enables collection or a task.

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\project-python.cmd -m workers.providers.cli comparison
scripts\windows\project-python.cmd -m workers.providers.cli status --root D:\al-research\p28-runtime\provider-state
scripts\windows\project-python.cmd -m workers.providers.cli select --root D:\al-research\p28-runtime\provider-state --provider upstox
scripts\windows\project-python.cmd -m workers.providers.cli capabilities --provider upstox
```

The existing P28 provider state was initialized once. `init --root NEW-directory`
refuses an existing directory. Selection is saved but always disabled. Comparisons
never make provider requests; CLI archive date is unknown unless read through the API.

Compiled application checks/start/stop were exercised using a private isolated
TEST_ONLY operator, genuine archive and copied alerts (not the real operator database):

```bat
scripts\windows\check-alphalens.cmd D:\al-research\p28-runtime\TEST_ONLY_browser_auth\config.json
scripts\windows\start-alphalens.cmd D:\al-research\p28-runtime\TEST_ONLY_browser_auth\config.json
start "" http://127.0.0.1:8028/login
rem In another CMD window:
scripts\windows\stop-alphalens.cmd D:\al-research\p28-runtime\TEST_ONLY_browser_auth\config.json
```

Log in with the isolated account supplied privately during verification; no password
is in this document. For real operation, retain your existing private account/config
and update only frontend_root/providers_root/loopback origin as described in the P24
deployment guide. Do not replace populated auth/alerts stores with test state.
Provider comparison is in Settings and Data Health. Private API:
`GET /api/v1/providers/comparison` requires the existing authenticated browser session.

Verified offline request/planning/replay example (no provider calls):

```bat
rem Choose a NEW TEST_ONLY_ directory; the generator preserves existing directories.
scripts\windows\project-python.cmd -m scripts.build_p28_offline_request --root D:\al-research\p28-runtime\TEST_ONLY_new_replay --provider upstox
scripts\windows\project-python.cmd -m workers.providers.cli plan --provider upstox --instruments D:\al-research\p28-runtime\TEST_ONLY_new_replay\instruments.json --from-date 2026-10-09 --to-date 2026-10-09
scripts\windows\project-python.cmd -m workers.providers.cli catch-up-plan --provider upstox --calendar D:\al-research\p28-runtime\TEST_ONLY_new_replay\calendar.json --from-date 2026-10-09 --to-date 2026-10-10
scripts\windows\project-python.cmd -m workers.providers.cli verify-fixture --provider upstox --fixture D:\al-research\p28-runtime\TEST_ONLY_new_replay\bundle.json --from-date 2026-10-09
scripts\windows\project-python.cmd -m workers.daily.cli replay --root D:\al-research\p28-runtime\TEST_ONLY_new_replay\pipeline --request D:\al-research\p28-runtime\TEST_ONLY_new_replay\request.json --payload D:\al-research\p28-runtime\TEST_ONLY_new_replay\bundle.json
scripts\windows\project-python.cmd -m workers.daily.cli status --root D:\al-research\p28-runtime\TEST_ONLY_new_replay\pipeline
```

Repeat replay reuses the same receipt. Native body and fixture-envelope hashes differ.
`resume --root ... --run-id ... --payload ...` uses the existing P19 saved request/context;
inspect the actual run ID in status first. No synthetic observation enters normal mode.
Read-only real worker inspection:

```bat
scripts\windows\project-python.cmd -m workers.daily.cli status --root D:\al-research\p19-runtime\pipeline
scripts\windows\project-python.cmd -m workers.daily.cli prospective-status --root D:\al-research\p19-runtime\pipeline
scripts\windows\project-python.cmd -m workers.providers.model_probe --root D:\al-research\tejhq-research-evaluation-v2-fit-parallel
```

The fixed trusted XGB probe does not predict, fit, evaluate or change its artifact.
It is a local operator diagnostic, not an arbitrary model-loading API.

Future Upstox token import, only after the account is approved and a read-only
Analytics Token is obtained by the operator (not executed with a real token here):

```bat
scripts\windows\project-python.cmd -m workers.providers.cli import-analytics
```

This uses a hidden console prompt, Credential Manager readback and preserves a
different existing credential. It does not verify server scope/expiry or activate
the adapter. No trading-enabled OAuth credential, password or TOTP is collected.
The Alpha Vantage credential migration/probe already succeeded. Do not repeat it
to use more quota. The original plaintext can be removed by the operator; it has
not been deleted. Keep protected credential access in the same Windows account.

Optional separate synthetic demo (no real data, no default password, loopback only):

```bat
scripts\windows\project-python.cmd -m scripts.prepare_provider_demo --root D:\al-research\p28-runtime\TEST_ONLY_demo_new --frontend D:\al-research\p28-runtime\web-final --username demo_operator
scripts\windows\start-alphalens.cmd D:\al-research\p28-runtime\TEST_ONLY_demo_new\config.json
```

The demo has an explicit synthetic banner, new private account, no real alerts and
no acquisition. It is not authorization to publish the private backend publicly.

Focused tests and frontend checks:

```bat
set ALPHALENS_TEST_TEMP_ROOT=D:\al-tests
scripts\windows\project-python.cmd -m pytest tests\unit\test_p28_provider_adapters.py tests\unit\test_p28_pipeline.py tests\unit\test_p28_readiness.py tests\unit\test_p28_sessions.py tests\unit\test_p28_demo.py tests\integration\test_p28_provider_api.py -q
set "PATH=D:\al-research\p18-runtime\node-v22.23.3-win-x64;%PATH%"
cd apps\web
npm test
npm run typecheck
npm run lint
npm run build
```

Actual browser tests also require the isolated credential/state variables documented
in the P21/P26 verification guides. No browser account password belongs in CMD history.
Existing notification processing/recovery and backup commands remain in P20/P22/P24
operations guides; run only against the intended private store.
