# AlphaLens

AI-powered stock research and Portfolio Guardian decision support. AlphaLens never
places real trades. Initial product scope is NSE cash equities, INR, end-of-day V1.

## Current milestone

P0, the bounded P1 research fixture, and P2 raw-ingestion development are implemented.
P0's contract is recorded in [DECISIONS.md](DECISIONS.md) and
[product contract](docs/product/product-contract.md). The DOCX remains the original
authoritative specification; approved amendments are recorded separately.

**P1 DEVELOPMENT:** a local CC BY research fixture is validated; production/live
data clearance remains OPEN. Five Mendeley datasets provide 300 bounded source rows,
299 canonical records and one explicit unavailable observation. This is not a
historical market universe or evidence of unbiased/PIT-safe performance.
AlphaLens requires ZERO paid dependencies. The mandatory path runs locally on
free/open-source software with compatible free data; cloud is optional.
See the [free-data strategy](docs/data/free-data-strategy.md). Earlier paid-provider
research is retained as evidence, not approval. Missing data is never fabricated.
The API contains only liveness/readiness endpoints. Later-domain directories contain
responsibility notes, not working product features.

See [local setup](docs/development/local-setup.md),
[research fixture and replay](docs/data/research-fixture-source.md),
[acceptance status](docs/product/roadmap-and-acceptance.md), and
[validation report](docs/data/p1-validation-report.md).

## Architecture

Modular monolith plus background workers when authorized. PostgreSQL is the
production structured store; object storage/Parquet retain versioned datasets and
artifacts; Redis is temporary cache/coordination, introduced when needed.
Provider parsing belongs behind vendor adapters. Backend owns authoritative
calculations and authorization. Data correctness precedes UI.

Prefer a per-date reconstructible NSE universe with verified historical identity,
availability and departed-security evidence. Historical NIFTY 500 is OPTIONAL for
V1; today's constituent list is never historical membership. Disclose actual legally
usable free history per dataset. PIT fundamentals remain UNAVAILABLE unless proven.

## Development verification

With a verified `uv` installation and generated lockfile:

```powershell
uv sync --frozen
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy
```

Do not claim these checks passed unless they actually ran. The implementation
environment's results and blockers are recorded in the development report.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. P2 development proceeds independently under
D40-D42. See [P2 architecture and commands](docs/data/p2-raw-ingestion.md) and
[verification](docs/development/p2-verification-report.md). Stop before P3 until
the user explicitly approves it.
