# Final authored repository tree

Current source tree: 73 files including the unchanged DOCX and genuine uv.lock.
Git is initialized. Runtime .tools/.venv/caches and Git metadata are excluded from
this source listing. No real market artifacts exist.

```text
AlphaLens/
|-- .github/
|   |-- workflows/
|   |   `-- ci.yml
|   `-- dependabot.yml
|-- apps/
|   |-- api/
|   |   |-- src/
|   |   |   `-- alphalens_api/
|   |   |       |-- core/
|   |   |       |   |-- __init__.py
|   |   |       |   |-- config.py
|   |   |       |   |-- errors.py
|   |   |       |   `-- logging.py
|   |   |       |-- __init__.py
|   |   |       |-- health.py
|   |   |       `-- main.py
|   |   `-- pyproject.toml
|   `-- web/
|       `-- README.md
|-- backtesting/
|   `-- README.md
|-- db/
|   |-- schemas/
|   |   `-- canonical-entities.md
|   `-- README.md
|-- docs/
|   |-- architecture/
|   |   |-- api-conventions.md
|   |   `-- system-boundaries.md
|   |-- data/
|   |   |-- data-contract.md
|   |   |-- p1-validation-report.md
|   |   |-- provider-decision.md
|   |   `-- provider-evaluation.md
|   |-- development/
|   |   |-- command-log.md
|   |   |-- local-setup.md
|   |   |-- repository-tree.md
|   |   `-- verification-report.md
|   |-- product/
|   |   |-- glossary.md
|   |   |-- product-contract.md
|   |   `-- roadmap-and-acceptance.md
|   `-- security/
|       `-- threat-model.md
|-- infra/
|   |-- docker/
|   |   `-- api.Dockerfile
|   `-- README.md
|-- ml/
|   |-- data/
|   |   |-- src/
|   |   |   `-- alphalens_data/
|   |   |       |-- providers/
|   |   |       |   `-- __init__.py
|   |   |       |-- __init__.py
|   |   |       |-- contracts.py
|   |   |       |-- errors.py
|   |   |       |-- manifest.py
|   |   |       |-- normalization.py
|   |   |       |-- provider.py
|   |   |       |-- sample_ingestion.py
|   |   |       `-- validation.py
|   |   `-- pyproject.toml
|   |-- evaluation/
|   |   `-- README.md
|   |-- explainability/
|   |   `-- README.md
|   |-- features/
|   |   `-- README.md
|   |-- inference/
|   |   `-- README.md
|   |-- registry/
|   |   `-- README.md
|   `-- training/
|       `-- README.md
|-- tests/
|   |-- contract/
|   |   |-- test_provider_contract.py
|   |   `-- test_provider_normalization.py
|   |-- fixtures/
|   |   `-- README.md
|   |-- integration/
|   |   |-- test_api_health.py
|   |   |-- test_database_connectivity.py
|   |   |-- test_provider_live.py
|   |   `-- test_sample_replay.py
|   |-- unit/
|   |   |-- test_configuration.py
|   |   |-- test_data_validation.py
|   |   |-- test_log_redaction.py
|   |   `-- test_temporal_eligibility.py
|   `-- conftest.py
|-- workers/
|   `-- README.md
|-- .dockerignore
|-- .editorconfig
|-- .env.example
|-- .gitattributes
|-- .gitignore
|-- .pre-commit-config.yaml
|-- .python-version
|-- AGENTS.md
|-- AlphaLens_Complete_Project_Documentation.docx
|-- compose.yaml
|-- DECISIONS.md
|-- pyproject.toml
|-- uv.lock
`-- README.md
```
