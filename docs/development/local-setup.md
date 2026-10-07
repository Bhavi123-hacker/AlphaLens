# Local foundation setup

P14 offline commands (P13 passed/committed as 490de2e first):

```powershell
uv run --frozen alphalens-explain explain --signal SIGNAL_DIRECTORY --ranking RANK_DIRECTORY --risk RISK_DIRECTORY --features FEATURES_JSON --history PRIOR_SIGNAL_DIRECTORY --attribution LOCAL_ATTRIBUTION_JSON --output data/explanations
uv run --frozen python -m scripts.verify_p14_test_only --signals SIGNALS_ROOT --rankings RANKINGS_ROOT --risks RISKS_ROOT --features FEATURES_JSON --evaluations P9_ROOT --output data/explanation-replay
```

Repeat --history/--risk/--attribution for compatible trusted local evidence.
The CLI prints classified UTF-8 cards/annotations and never loads arbitrary model
binaries or calls an LLM. The library's from_p9 helper checks the exact model
checksum and P8's fixed reviewed skops allowlist; native external boosted-model
attribution accepts trusted in-memory pipelines. Missing attribution stays explicit.
Use the short Windows root and explicit native exit capture for full verification:

```powershell
$env:ALPHALENS_TEST_TEMP_ROOT='D:/al-tests'
$env:PYTHONUTF8='1'
uv run --frozen python -m scripts.verify_p5_postgres *> data/phase-verification.log
$verificationExit=$LASTEXITCODE
Write-Output "VERIFICATION_EXIT=$verificationExit"
exit $verificationExit
```

PowerShell can treat Docker progress on stderr as a wrapper error; preserve the
test summary, replay/teardown evidence and actual native exit code. Never suppress
test warnings or skip database gates to avoid that wrapper behavior. Stop before P15.

P13 offline developer commands (after approved P12 artifacts exist):

```powershell
uv run --frozen alphalens-signals evaluate --ranking RANK_DIRECTORY --risk RISK_DIRECTORY --security TEST:ALPHA --output data/signals
uv run --frozen python -m scripts.verify_p13_test_only --rankings P12_SNAPSHOTS_ROOT --risks P11_SNAPSHOTS_ROOT --output data/signal-replay
```

Optional --policy, repeated --history and --position accept trusted local immutable
evidence. Synthetic positions must be explicitly TEST_ONLY, with known event and
availability times. The normal policy never upgrades insufficient model evidence;
demonstration mode is explicit, TEST_ONLY and a DEVELOPMENT_ASSUMPTION. No user
holdings, broker execution, live data or API/frontend are added. Windows full runs
use ALPHALENS_TEST_TEMP_ROOT=D:/al-tests when the default drive lacks space.

Scope: P0-P8 plus sequential P9/P10 authorized under D55-D58. Stop before P11.

## P6 developer features

The workspace adds `alphalens-features` with only existing free `alphalens-data`
dependencies. After `uv sync --frozen`, build the TEST_ONLY canonical history and
run the commands in [P6 documentation](../ml/p6-feature-engineering.md).
Output JSON/Parquet/manifest files must remain under ignored data/ or .local-data/.
Use explicit cutoff plans; unavailable real fixture metadata remains unavailable.
Run real PostgreSQL regression with `python scripts/verify_p5_postgres.py`.
The runner now permits 1200 seconds for the expanded suite; no migration change.
P7 followed P6 gate/commit. P8 follows approved P7 9c2bad9.

## P8 developer baselines

```powershell
uv sync --frozen
uv run --frozen python -m scripts.build_p8_test_fixture --data-root data/p8-test-only
uv run --frozen alphalens-train baseline data/p8-test-only/supervised-5.json --config data/p8-test-only/config-classification-logistic-5.json --registry data/p8-models
uv run --frozen alphalens-train baseline data/p8-test-only/supervised-5.json --config data/p8-test-only/config-regression-ridge-5.json --registry data/p8-models
uv run --frozen alphalens-model evaluate <model_run_id> --input data/p8-test-only/supervised-5.json --registry data/p8-models
```

These are TEST_ONLY — NOT A PERFORMANCE CLAIM. Fixture preparation retains
immutable P2-P7 evidence under ignored storage and may take several minutes.
Run each horizon with its matching supervised/config files. Missing mature data
rejects fitting. Re-evaluation requires exact pinned input and local library
environment; it never refits or silently substitutes a different dataset.
Do not load copied/untrusted registries. [P8 contract](../ml/p8-baseline-machine-learning.md).

## P7 developer labels

P6 passed and was committed as ac6973f. `uv sync --frozen` installs the local
alphalens-labels package with existing data/features dependencies only.
See [P7 plans, execution bound, Decimal storage and CLI](../ml/p7-label-generation.md).
Specify an outcome cutoff/end independently of feature decisions. Use an explicit
feature subset for alignment; unavailable long-history features remain NULL.
Run Bandit on ml/labels/src as well as API/data/features and the existing real
PostgreSQL regression runner. No large matrix tables or new migration.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. Stop before P6.
P3 CLI: `uv run --frozen alphalens-validate data/<root>/canonical/<run_id>/canonical.json`.
See [P3 input/output commands](../data/p3-data-validation.md); outputs are ignored.
P4 TEST_ONLY preparation: `uv run --frozen python scripts/build_p4_test_fixture.py --data-root data/p4-test-only-v2`.
Query: `uv run --frozen alphalens-universe --input data/p4-test-only-v2/universe-input.json --date 2024-01-10 --decision-time 2024-01-10T12:00:00+00:00`.
The time is constructed fixture context, not an NSE close assumption.
See [P4 methodology/CLI/replay](../data/p4-point-in-time-universe.md).
P5 preparation: `uv run --frozen python -m scripts.build_p5_test_fixture --data-root data/p5-test-only`.
Build: `uv run --frozen alphalens-canonical-build data/p5-test-only/canonical-input.json --knowledge-cutoff 2024-01-20T12:00:00Z --start 2024-01-01 --end 2024-01-20 --output data/p5-snapshots`.
Apply `db/migrations/001_p2_ingestion_metadata.sql` then `002_p5_canonical.sql` to
a configured local PostgreSQL database before adding `--postgres`; supply
ALPHALENS_DATABASE_URL through a private environment, never command arguments or Git.
Disposable real PostgreSQL plus full gates and repeated canonical CLI persistence:
`uv run --frozen python scripts/verify_p5_postgres.py`.
This uses its own loopback port 55432/project/volume and removes those resources;
it does not operate on the regular local development database. No SQLite fallback.
See [P5 storage/PIT/replay policy](../data/p5-canonical-data-model.md).
Local real CC BY research artifacts now exist; no production provider, frontend or
later-phase engine is present. See [fixture replay](../data/research-fixture-source.md).

Current policy D26–D35 requires ZERO paid dependencies. Local PostgreSQL plus
upstream Docker Engine/Compose on a compatible host is sufficient in principle;
cloud is optional. Docker Desktop has conditional free eligibility and must not
be a mandatory paid prerequisite. Runtime licensing references are in the
[free-data review](../data/free-data-evaluation.md); no runtime installation or
platform migration was performed by the free-data decision task.

## Locked Python environment

uv.lock is genuinely generated and verified. Python >=3.12,<3.13 is required;
the verified interpreter is 3.12.4. uv 0.11.25 manages apps/api and ml/data.
Development tools are installed in ignored .venv. Hatchling is a locked development
dependency; both workspace build systems pin the verified 1.32.4 backend.

With a verified uv executable on PATH:

```powershell
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
uv run --frozen bandit -r apps/api/src ml/data/src
uv run --frozen pip-audit --skip-editable
uv run --frozen pytest -W error
```

The actual local executable is .tools/bin/uv.exe; use it in place of uv above.
Bootstrap and initial resolution commands used:

```powershell
python -m pip install --target .tools uv==0.11.25
.tools/bin/uv.exe lock
.tools/bin/uv.exe sync --frozen
```

Bootstrap, uncached sync/build and vulnerability lookup need approved network
access. No proxy/browser download/disabled TLS bypass was used. .tools is ignored.
The earlier socket denial and absent tools are historical, not current.
Do not replace uv.lock with a global pip freeze. A lock does not prove Docker,
provider access, production readiness or hosted CI success.

## HTTP test compatibility

The project intentionally declares httpx>=0.28,<0.29. Health tests use HTTPX
AsyncClient/ASGITransport and AnyIO's asyncio backend, following
[FastAPI async testing](https://fastapi.tiangolo.com/advanced/async-tests/).
The original warning came from global Starlette 1.3.1's TestClient import fallback.
No alternative HTTP package, package-source edit, downgrade or warning suppression
was used. Locked pytest passes with warnings treated as errors.
If application lifespan resources are added, explicitly exercise that lifecycle;
this health-only application currently has none.

## Docker/PostgreSQL verification

P1B research validation now verified Docker 29.6.2, Compose v5.3.1 and PostgreSQL
17.11: healthy startup, real host connectivity and committed TEST_ONLY marker
persistence across stop/start. Dedicated verification containers/network/volume were
removed afterward. User database volumes are not part of that disposable test scope.
Local ports remain bound to 127.0.0.1. The bridge allows outbound traffic; it is no
longer an isolated internal network, which failed to publish the port on this host.
The health probe uses a bounded Psycopg synchronous connection in a worker thread
to support Windows' default event loop without blocking the API event loop.

Historical result: the prior provider task verified Docker CLI 29.6.2, Compose v5.3.1 and Compose
configuration. Final free-data-strategy resume rechecked `docker info`: exit 1,
Docker Desktop Linux-engine pipe still absent. No services were started and actual
PostgreSQL connectivity was then unverified. No database substitute was used.

Once an accessible daemon is running, copy .env.example to ignored .env and set
your local password/URL. API database host is postgres; host-side tests use
localhost. No credentials should enter a committed file or command ledger.

```powershell
docker compose config --quiet
docker compose up -d postgres
# Set ALPHALENS_TEST_DATABASE_URL in an ignored local environment.
uv run --frozen pytest tests/integration/test_database_connectivity.py -W error
docker compose stop postgres
```

Stop in a finally block if the test fails. Preserve volumes; do not use down -v.
First image pulls need approved registry access. No tables or market data are
seeded. To start the health-only API afterward: docker compose up --build -d api.
Endpoints /api/v1/health/live and /ready do not claim market/model availability.

## Git and secrets

Repository initialized on main. The execution account changed after sandbox
removal; scoped commands used git -c safe.directory=C:/Users/Dell/AlphaLens ...
to trust only this known repo. No global trust setting or remote/push was added.
Initial commit follows local checks and staged-file audit; see git log -1 for hash.

.env is absent. Ignore rules cover env variants, keys, .aws, .venv, .tools and
local data. Example password/URL are empty placeholders. Fixtures are TEST_ONLY.

## Provider gate

```powershell
.tools/bin/uv.exe run --frozen alphalens-provider-status
```

Expected exit 2: UNKNOWN/BLOCKED/PROVIDER_NOT_SELECTED and zero production-provider records.
No production vendor adapter, paid access, current-member historical substitution or
fabricated market data exists. Research fixtures remain separate from production
source clearance, which is OPEN.

## P2 fixture ingestion

P2 is explicitly authorized under D40-D42 independently of
P1_PRODUCTION_DATA_CLEARANCE = OPEN. Stop before P3.

```powershell
uv run --frozen alphalens-ingest tests/fixtures/p2/TEST_ONLY.csv --spec tests/fixtures/p2/TEST_ONLY.spec.json
uv run --frozen python scripts/verify_p2_postgres.py
```

The first command uses ignored local file metadata/Parquet and verifies replay.
The second starts a dedicated disposable real PostgreSQL test project on loopback
55432, runs the full suite and PostgreSQL CLI, then removes its own test volume.
It generates secrets in memory and leaves normal development databases alone.
If Docker is unavailable, run the file command/full tests and report database skips;
do not substitute SQLite or block P2 development. See
[P2 architecture](../data/p2-raw-ingestion.md) and
[actual verification](p2-verification-report.md).

## P9/P10 authorized development — 2026-10-06

P9 developer replay (free CPU-only libraries, no new market download):
`uv run python -m scripts.verify_p9_test_only --inputs data/p9-test-only --output data/p9-evaluations`.
The script creates authored TEST_ONLY P2–P7 history if absent, invokes P7 at each
fold's historical cutoff, evaluates six families per task/four horizons twice,
and verifies OOS Parquet/manifest checksums. Results are NOT A PERFORMANCE CLAIM.
`alphalens-evaluate DATASET --features FEATURES --definition DEFINITION --output data/evaluation
--training-dataset fold-1=TRAIN1 --training-dataset fold-2=TRAIN2 ...` replays a
versioned definition with externally prepared cutoff-specific P7 aligned datasets.

After verified P9 outputs exist, P10's fixed TEST_ONLY arena:

```powershell
uv run --frozen python -m scripts.verify_p10_test_only --inputs data/p9-test-only --evaluations data/p9-evaluations --output data/p10-backtests
```

It authors an explicit TEST_ONLY execution-calendar supplement, replays all six
families per task/four horizons under three fixed cost/slippage scenarios plus
cohort/random controls twice, and persists checksum-verified JSON/Parquet.
No new market data is acquired. Some terminal outcomes are unresolved by design;
the system withholds affected portfolio metrics. No production model winner.

Developer single replay:

```powershell
uv run --frozen alphalens-backtest run --oos EVALUATION_DIRECTORY --canonical CANONICAL_INPUT_JSON --features FEATURES_JSON --calendar CALENDAR_JSON --definition DEFINITION_JSON --output data/single-backtest
```

Generate definitions through the typed `BacktestDefinition` contract and pin the
exact P9 OOS/evidence/calendar IDs. Full local regression:
`uv run --frozen python -m scripts.verify_p5_postgres`; it creates and removes only
its own disposable PostgreSQL 17 test resources. Static security paths now include
`ml/evaluation/src` and `backtesting/src`. See [P10 limitations](../backtesting/p10-backtesting.md)
and [real-data readiness](real-data-readiness.md). Stop before P11.

Allow ample local disk capacity for fixture captures and container build layers.
An explicitly chosen fresh `pytest --basetemp` on another local volume can keep
temporary regression evidence off a constrained system drive; verify the target
is task-specific and absent because pytest initializes it destructively. Do not
delete normal databases, accepted data, or unrelated Docker images to make a gate
appear passed. Full cold image builds need more space than an existing-image
package update; report resource failures honestly.

On Windows, also use a short fresh temporary root (for example
`$env:PYTEST_ADDOPTS='--basetemp=D:/alpt10r'` before the verification runner).
Nested dataset/model hashes can exceed Windows hard-link path limits under a
long archive root. Verify the chosen path is absent and task-specific before
pytest initializes it; the shorter path does not weaken dataset identity,
checksum or immutable artifact checks.

## P11/P12 Windows-safe verification

The test harness automatically chooses a fresh short Windows basetemp when none
is supplied explicitly. Its default parent is `drive:/al-tests`; choose a short
local volume with sufficient capacity using:

```powershell
$env:ALPHALENS_TEST_TEMP_ROOT='D:/al-tests'
$env:PYTHONUTF8='1'
uv run --frozen python -m scripts.verify_p5_postgres
```

The configured parent must be absolute and at most 32 characters. Each run owns
an absent unique child; only that child is initialized by pytest. The parent and
other runs are never recursively reset. Explicit `--basetemp` overrides remain
supported, with the same responsibility to choose a short, disposable path.
No blanket skips or artifact immutability exceptions are used. Do not print DSNs
or manually remove unrelated databases/images to make a check pass.

D59-D61 authorize P11 then P12 only, each with its own verification and commit.
Stop before P13; production data/model clearance remains open.

P11 developer risk replay:

```powershell
uv run --frozen alphalens-risk evaluate --canonical CANONICAL_INPUT --features FEATURES --session 2024-03-01 --security TEST:ALPHA --horizon 5 --evaluation P9_DIRECTORY --output data/risk
uv run --frozen python -m scripts.verify_p11_test_only --inputs P8_FIXTURE_DIRECTORY --evaluations P9_DIRECTORIES_ROOT --output data/risk-replay
```

The replay accepts only authored TEST_ONLY inputs and reuses verified P9 outputs;
it does not retrain or download data. Repeat --evaluation for independent
task/horizon arenas, with one unambiguous configured vintage per family/decision.
Full static/security paths now include decision/src. See the versioned risk
policy and [limitations](../decision/p11-risk-engine.md).

P12 historical opportunity replay (P11 passed/committed as b50314b first):

```powershell
uv run --frozen alphalens-rank --canonical CANONICAL_INPUT --features FEATURES --date 2024-03-01 --horizon 5 --top 10 --evaluation P9_DIRECTORY --output data/ranking
uv run --frozen python -m scripts.verify_p12_test_only --inputs P8_FIXTURE_DIRECTORY --evaluations P9_DIRECTORIES_ROOT --risks P11_SNAPSHOTS_ROOT --backtests P10_RUNS_ROOT --output data/ranking-replay
```

Repeat --evaluation, --risk, --history or --backtest for verified local directories.
Optional --policy pins fixed task families, weights/scales and the P11 policy.
Provided risk records must match the exact replayed evidence; future records are
ignored and missing current risk excludes candidates. Top-N never truncates the
stored complete snapshot. Both scripts accept authored TEST_ONLY fixtures only;
no downloads or model fitting occur. Stop before P13. Insufficient selection
evidence blocks non-TEST_ONLY ranking even when a research fixture is permitted
for earlier data/training experiments.
## P15 local portfolio commands

The `alphalens-portfolio` workspace installs through the existing frozen uv sync.
Use the create/add-transaction/import-position/positions/value/history commands
documented in [P15](../portfolio/p15-portfolio-guardian.md). Ledger outputs belong
in ignored `data/` or `.local-data/`. Input canonical envelopes retain P5 raw
artifact roots and are locally verified; no provider or broker connection exists.
Portfolio PostgreSQL metadata uses migration 003 with the existing local psycopg
connection conventions. Never include a connection string in logs or arguments.
