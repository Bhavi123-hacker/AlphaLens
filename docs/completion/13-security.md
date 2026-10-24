# Security verification — 24 October 2026

Status: **PARTIAL** for the isolated candidate; **BLOCKED_EVIDENCE** for a public/production release. This report distinguishes the preserved shared installation, the tested isolated candidate, and historical CI evidence. Scanner severities and failure policies remain unchanged.

## Fresh findings and remediation

| Surface | Actual check | Result |
| --- | --- | --- |
| Preserved shared Python installation | `.venv/Scripts/python.exe -m pip_audit --path .venv/Lib/site-packages --format json --progress-spinner off` | Exit **1**, **41 advisories /3 packages**: certifi 2026.7.22 (1), filelock 4.0.10 (3), Pillow 12.3.0 (37). No ignore list. |
| Isolated release Python installation | `.local-data/completion-runtime/venv/Scripts/python.exe -m pip_audit --path .local-data/completion-runtime/venv/Lib/site-packages --format json --progress-spinner off` | Exit **0**, **no known vulnerabilities**. Candidate versions include certifi 2026.10.19, Pillow 13.0.0 and filelock 4.2.4. |
| Original frontend lock | `npm.cmd audit --json` in `apps/web` | Exit **1**, **2 HIGH /0 CRITICAL affected packages**. zod 4.6.5 and undici 8.11.2. This is the original lock audit, not proof that installed runtime packages were enumerated. |
| Candidate frontend lock | Supported Node 22.23.3 npm, isolated `install --package-lock-only --ignore-scripts --save-exact zod@4.6.7`, then `update undici --package-lock-only --ignore-scripts` | Exit **0** for both operations; final dependency audit **0 vulnerabilities**. Only zod and undici package versions change: zod **4.6.7**, undici **8.12.3**. |
| Python application static security | `python -m bandit -r` over the exact CI application/data/ML/backtesting/decision/portfolio/worker targets, JSON output | Exit **0**, **46,018 lines**, **0 findings /0 errors /0 skipped tests /0 nosec** at this audit checkpoint. |

The advisory fixes are certifi >=2026.10.19, filelock >=4.2.1 and Pillow >=13.0.0. Zod's constrained-collection validation could exhaust memory; undici has an excessive content-encoding denial-of-service advisory and two additional moderate advisories, fixed from 8.12.2. The patch uses compatible versions and changes no severity thresholds, suppressions or final-holdout models.

The shared `.venv` is a junction to `D:\al-research\p17-api\workspace-venv-original`; both checkouts use it. The shared frontend dependencies are a junction to `D:\al-research\p18-runtime\node_modules`. Neither shared installation was synchronized or overwritten by this audit. A clean candidate lock therefore does **not** cure the preserved installation or authorize an unattended collector environment change. Candidate frontend dependencies are installed separately under `.local-data/completion-runtime/web-dependencies`; release tests must use this directory and Node 22.23.3. PATH's Node 20.17.0 does not meet the package's declared engine requirement.

Private exact outputs: `.local-data/completion-20261024/{pip-audit-active.private.json,pip-audit-candidate.private.json,npm-audit.private.json,bandit.private.json,npm-zod-update.private.log,npm-undici-update.private.log,npm-candidate-ci.private.log}`. The first attempt to combine `--disable-pip` without a requirements file returned usage exit 2 and is not a valid audit; the corrected `--path` commands above are the evidence.

## Containers, secrets and CI

The latest locally saved strict-container artifact was directly parsed: `.local-data/gpu-verification-20261021/ci-trivy/trivy-results.json`, created **2026-10-21T15:30:59.667769859Z**, has **0 HIGH /0 CRITICAL**. It supersedes the historical 44-HIGH scan for that exact 21 October image only. It does not establish that today's rebuilt candidate is clean.

A fresh `docker version --format '{{.Server.Version}}'` could not connect to the Docker Desktop Linux engine named pipe. The engine is stopped. No engine/service/task configuration was changed. The separately available Trivy executable is 0.70.0 but its cached vulnerability database was last updated **9 October**; an offline pass against that stale cache would not be accepted as a fresh release scan. **Fresh candidate container scan: BLOCKED_EVIDENCE.** Keep the Windows loopback candidate separate from container/public production acceptance; build and scan the exact final image with current vulnerability metadata before container delivery.

[Foundation CI run 39626089270](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39626089270) is historical evidence for implementation commit `79c64a6f4a05d7ded0451b9a5bbb17f70d1800c2`: backend/PostgreSQL 17 **1,545 passed /13 skipped** and strict container passed, but the workflow **FAILED overall** at full-history TruffleHog. Its saved result has **0 verified /3 unverified findings**, exit **183**. Existing review identifies historical test/configuration placeholder locations; that explanation does not turn the scanner gate green. No history rewrite, detector exclusion, secret suppression, or changed result policy is applied. Native TruffleHog was not available on PATH, so this campaign does not claim a fresh full-history pass. See [the retained history review](../security/final-secret-history-audit.md).

[Frontend CI run 39626089120](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39626089120) previously passed 116 tests, typecheck/lint/build, four synthetic-demo browser cases and its then-current npm audit. Today's new advisories are independently recorded above. Prior CI success does not substitute for candidate regression or final-commit CI.

Current `.github/workflows/ci.yml` keeps explicit Trivy HIGH/CRITICAL, exit 1, and TruffleHog verified/unknown scanning, plus real PostgreSQL CI, Bandit and dependency audits. The Dockerfile pins its base/installer, upgrades supported OS packages, uses a non-root application user, and omits runtime uv; these controls do not waive vulnerability checks.

## Release boundaries

- Candidate dependency remediation: **COMPLETE_VERIFIED** for vulnerability-service results; application compatibility is reported in [the release test results](../release/2026-10-24-test-results.md).
- Preserved shared runtime dependency health: **BLOCKED_EVIDENCE**, still vulnerable until a separately scoped tested update is deployed.
- Current source Bandit: **COMPLETE_VERIFIED** at the audit checkpoint; any subsequent code changes need appropriate checks.
- Fresh full-history secret gate and fresh candidate container gate: **BLOCKED_EVIDENCE**.
- Public exposure and production-data clearance: **BLOCKED_APPROVAL /BLOCKED_EVIDENCE**. Keep private research data authenticated and on loopback. No public deployment, provider request, paid resource, scheduler change, production migration or credential output was performed by this audit.
