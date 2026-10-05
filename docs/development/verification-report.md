# Foundation and P1 verification report

## 2026-10-05: P1 runtime check and public provider evaluation

P0 is complete by user approval. Work is on `p1-provider-evaluation`, based on
main `9fa82284936f8b7a34f5409ba25cdce3538747b6`; no merge or push. This increment
changes research/verification documentation only. Source DOCX, DECISIONS.md,
neutral interface, application code, TEST_ONLY fixtures and lockfile are unchanged.

| Check | Actual result |
| --- | --- |
| Docker CLI / Compose | 29.6.2 / v5.3.1 present at initial P1 check. |
| Docker Engine | BLOCKED on initial check and resume: `docker info --format '{{.ServerVersion}}'` exits 1. The dockerDesktopLinuxEngine pipe does not exist. |
| compose.yaml | PASS on initial check and resume: `docker compose config --quiet` exits 0 with process-only TEST_ONLY configuration. This validates Compose interpolation/configuration, not database URL semantics or connectivity. No .env created. |
| PostgreSQL start/health/connectivity | NOT VERIFIED: no available engine, no service started and no health/connectivity result. No substitutes. |
| Cleanup | No services started, therefore none to stop. Process-only configuration removed. |
| Locked tests | PASS on resume: `uv run --offline --frozen pytest -W error -ra`, 47 passed, 2 skipped, 0 warnings (0.63 seconds). |
| Ruff lint / format | PASS on resume: lint clean; 58 files already formatted. |
| mypy | PASS on resume: no issues in 27 source files. |
| Bandit | PASS on resume: 533 lines scanned; no issues or suppressions. |
| Skips | Real PostgreSQL URL absent; approved provider/licensed historical sample absent. Neither gate passed. |
| Provider research | Three complete shortlist evaluations and a supplemental NSE Indices assessment. Source-linked matrices, rights/PIT/universe gaps, conditional ranking and vendor questions recorded. |
| Provider/data gate | OPEN: no selection, purchase, account, vendor messages, API capture or real records. |
| Contract completeness | Additional financial-period/basis, revision-time, volume-basis and reference-history semantics identified for a versioned P1 review before adapter normalization. No code changed. |
| Dependency vulnerability audit | Historical pip-audit result retained below; not rerun for documentation-only edits. No new dependency-security claim. |
| Documentation audit | PASS: 42 source IDs; 165 main-matrix cells each have one evidence state; all 30 dimensions covered for the shortlist and supplement; source references/local links resolve. Public evidence does not certify delivered data. |
| Source/scope/secret controls | PASS: DOCX checksum unchanged; application/data code, decisions, lockfile and main unchanged; .env and local datasets absent; example secret fields empty; ignored secret paths and TEST_ONLY markers checked. Narrow credential-pattern check found no matches; not a comprehensive secret scan. |

The first one-off documentation audit incorrectly expected Python fixture builders
under tests/fixtures and failed at that assertion. Builders actually live in
tests/conftest.py; tests/fixtures contains their policy README. The audit was
corrected to inspect the actual files and passed. No tests or fixtures were changed
to satisfy the audit.
An extended audit then had a generated-script quoting error before executing any
checks. After fixing the one-off helper, the audit passed again, including exact
source-reference URL matching. Both failed invocations are retained in the ledger.

Exact Docker error:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine;
check if the path is correct and if the daemon is running:
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

The Python environment remains reproducible from the existing uv.lock; this run
used offline locked execution without new installations. Full local runtime
verification remains blocked on an available Docker Linux daemon. P1 additionally
needs written usage rights, proven historical universe/PIT scope, complete mapping
and a representative real sample. No P2 work was performed.

Research outcomes and remaining questions: [provider evaluation](../data/provider-evaluation.md),
[recommended decision](../data/provider-decision.md), [P1 gate](../data/p1-validation-report.md).
Final source/changed-file/link/state/Git checks and commit result are recorded in
command-log.md and the user report.

## Earlier approved foundation remediation (historical record)

The following results are retained from the approved baseline. Current reruns are
listed separately above; installations and pip-audit below are historical results.

## Actual results

| Check | Result |
| --- | --- |
| DOCX | PASS: unchanged SHA256 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a. Verified before edits and repeatedly afterward. |
| Git | Initialized on main; initial commit follows runnable checks and staged-file audit. Hash/status reported to user; no remote/push. |
| uv.lock | PASS: genuinely generated, 65 resolved packages; lock --check passes. |
| Locked .venv | PASS: sync --frozen, 64 installed packages including two local editable packages. Root is a non-package workspace. |
| Workspace builds | PASS: API/data packages built; verified Hatchling 1.32.4 build backend pinned. |
| Ruff lint / format | PASS after SIM117, UP046 and resulting blank-line fixes. |
| mypy | PASS: no issues in 27 source files. |
| Bandit | PASS: no issues, no nosec/rule suppressions. |
| pip-audit --skip-editable | PASS: no known vulnerabilities. Local API/data distributions skipped as editable; third-party dependencies audited. |
| pytest -W error | PASS: 47 passed, 2 skipped, zero warnings. |
| Real PostgreSQL | SKIPPED/BLOCKED: Docker engine absent, no test database URL; psycopg now installed. |
| Real provider | SKIPPED/BLOCKED: no selected/licensed provider or real capture. |
| Compose config | PASS using explicit TEST_ONLY local configuration values. |
| Docker runtime | UNAVAILABLE: dockerDesktopLinuxEngine named pipe absent. No services started, so no teardown required. |
| Secret/env controls | PASS: ignored paths, absent .env, empty example secrets, narrow token/private-key pattern check. Not a comprehensive secret scan. |
| Data honesty | PASS: TEST_ONLY guards retained; no vendor, real dataset, frontend or synthetic real-market claims. |
| Hosted CI / container build and scan | NOT RUN; no hosted deployment or image-security claim. |

The Python development environment is reproducible from the actual lockfile with
compatible Python 3.12 and approved dependency access. Full runtime verification
remains incomplete because Docker/PostgreSQL is unavailable. P1's provider/data
exit gate remains separately incomplete.

## Exact versions

| Component | Version |
| --- | --- |
| Python | 3.12.4 |
| Bootstrap uv | 0.11.25 (1fc7de7c4, 2026-06-26) |
| pip in .venv | 26.2.1 |
| Ruff | 0.16.10 |
| mypy | 1.20.2 |
| Bandit | 1.9.4 |
| pip-audit | 2.10.1 |
| psycopg / psycopg-binary | 3.3.6 / 3.3.6 |
| Hatchling | 1.32.4 |
| httpx | 0.28.1 |
| FastAPI / Starlette | 0.141.1 / 1.7.0 |
| Pydantic / settings | 2.13.5 / 2.15.0 |
| pytest / AnyIO | 9.1.1 / 4.15.1 |
| uvicorn | 0.54.0 |
| Git | 2.53.0.windows.1 |
| Docker CLI / Compose | 29.6.2 (dfc4efb) / v5.3.1 |

All requested Python tools are installed/usable. uv is in ignored .tools; project
dependencies are in ignored .venv. The global Python package environment was not
modified by the target bootstrap (global pip remains 25.3).

## Root causes and fixes

The earlier sandbox denied pip sockets with WinError 10013. No pip config files,
custom indexes or no-index setting were found; the only cached wheel was unrelated.
The grouped install stopped at Ruff before independently attempting every other
tool. Hatchling had not been separately installed. These failures never proved
that the distributions did not exist. After the user enabled access, bootstrap,
registry resolution, artifact downloads and isolated sync succeeded.

httpx was already installed and explicitly required. The original warning was
real in global Starlette 1.3.1's TestClient fallback, not an intentional project
requirement for an alternative package. Tests use the declared HTTPX ASGI transport
per [official FastAPI documentation](https://fastapi.tiangolo.com/advanced/async-tests/).
No alternate dependency, source-library modification, downgrade or suppression.
Warnings-as-errors tests pass in the global and new locked environments.

Git initialized under the prior sandbox account. Initial staging failed because
.git/index.lock was denied. After the account/access change, only the exact known
repository is trusted using a per-command safe.directory setting.

Ruff's first run found two actual style issues. Fixes preserved database context
cleanup and used Python 3.12 generic syntax. The resulting blank-line issue was
formatted. Bootstrap/local-data directories are excluded from project linting.
A combined delete/add documentation patch was rejected without changing files;
the reports were subsequently replaced through a single update per file.

## Remaining blockers

An accessible Docker Linux daemon is needed for real PostgreSQL start/test/stop.
No fake substitute or runtime success is claimed. Hosted CI, container image
build/scan, OS image/action digest hardening and production readiness are unverified.

Provider selection, budget/rights evidence, representative real history and
historical NIFTY 500/departed coverage remain UNKNOWN/BLOCKED. No P2, production
ingestion, feature/model/backtest/risk/ranking/signal/portfolio system, frontend or
AWS infrastructure was added.
