# Local foundation setup

Scope: P0-P5 plus explicitly authorized sequential P6/P7 under D49-D50.

## P6 developer features

The workspace adds `alphalens-features` with only existing free `alphalens-data`
dependencies. After `uv sync --frozen`, build the TEST_ONLY canonical history and
run the commands in [P6 documentation](../ml/p6-feature-engineering.md).
Output JSON/Parquet/manifest files must remain under ignored data/ or .local-data/.
Use explicit cutoff plans; unavailable real fixture metadata remains unavailable.
Run real PostgreSQL regression with `python scripts/verify_p5_postgres.py`.
The runner now permits 1200 seconds for the expanded suite; no migration change.
P7 implementation follows only after P6 passes and is committed. Stop before P8.

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
