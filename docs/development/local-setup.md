# Local foundation setup

Scope: P0/P1 foundation and bounded research fixture only. P2 remains unauthorized.
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

Expected exit 2: UNKNOWN/BLOCKED/PROVIDER_NOT_SELECTED and zero real records.
No vendor adapter, paid access, current-member historical substitution or fabricated
market data exists. P1 real-provider acceptance is incomplete. Stop before P2.
