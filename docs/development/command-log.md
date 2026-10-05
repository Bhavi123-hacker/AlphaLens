# P1 research-fixture task: command and outcome ledger

## 2026-10-06 P3 sequential development

- Ran git status, branch --show-current and log --oneline -5 before all edits.
  Clean exact approved P2 HEAD d3eee20; P2 DEVELOPMENT PASSED; production OPEN.
- Read engineering decisions/contracts/P2 code/tests and original DOCX phase text.
  Created p3-p4-validation-universe from approved P2; main untouched.
- Added source-neutral quality contracts/engine/file loader/CLI and 29 TEST_ONLY
  tests. No working P2 behavior or dependencies changed; no new DB schema.
- Executed uv lock --check, uv sync --frozen, pytest -W error -ra via disposable
  real PostgreSQL runner: 125 passed, 1 production-provider skip. PostgreSQL CLI
  and dedicated teardown passed. Ruff lint/format, strict mypy, Bandit and diff
  whitespace passed. Installed quality CLI twice reproduced report bytes/hash.
- P3 DEVELOPMENT PASSED. Failures/limitations in p3-verification-report.md.
  P4 implementation follows only after this increment is committed.

2026-10-05. No secrets, DSNs or raw market rows are reproduced here.
All Git commands use the per-command option
`-c safe.directory=C:/Users/Dell/AlphaLens`; no global trust change.

| Command / bounded operation | Result |
| --- | --- |
| git branch --show-current; git status --short; git log --oneline -5 | PASS: clean p1-free-data-strategy at approved 84abd59. |
| Get-FileHash AlphaLens_Complete_Project_Documentation.docx -Algorithm SHA256 | PASS: approved hash preserved, rechecked after implementation. |
| Get-Content / rg --files / rg targeted code and documentation reads | PASS; rg needed --no-ignore to inspect installed Psycopg under ignored .venv. |
| docker info --format '{{.ServerVersion}}' | PASS: 29.6.2. |
| docker compose ls --format json; docker ps | PASS: no existing project services before this task. |
| docker image inspect postgres:17-bookworm | Initially FAILED: image absent; subsequent Compose startup pulled the official image. |
| Public documentation/metadata GETs | Open licences and uploader representations verified. API-gateway GET returned 401; stopped that authenticated interface. Public API file lists returned 200. OAI metadata-format read succeeded; exploratory identifier returned idDoesNotExist and was not used. |
| Initial Python capture attempts | FAILED closed: empty page-state KeyError, transient metadata 502, then wrong size/hash for a 200 JSON error body. No such response saved as market data. |
| Five pinned public file_downloaded?version=1 GETs using existing httpx | PASS: five exact CSVs captured with repository hash/size matches; acquisition instants and immutable raw files preserved locally. No new package or account. |
| Initial descriptive CSV inspection | FAILED on a blank volume value; corrected inspection identified the genuine missing source row without filling it. |
| git switch -c p1-real-sample-validation | PASS; no main change or merge. |
| uv run --offline --frozen python -m alphalens_data.research_sample --manifest docs/data/research-sample-manifest.json --raw-dir .local-data/p1/mendeley --output-dir .local-data/p1/mendeley/validation-v1 | PASS: 299 canonical rows, one unavailable observation, identical replay SHA256. |
| Final Python replay and comparison against preserved canonical.json | PASS: identical bytes; metadata-only research-sample-validation.json written. |
| uv run --offline --frozen ruff check . | First FAILED on five long lines; final PASS after correction. |
| uv run --offline --frozen ruff format [seven changed Python paths] | PASS: seven files unchanged. |
| uv run --offline --frozen ruff format --check . | PASS: 65 files formatted. |
| uv run --offline --frozen mypy | PASS: 31 files. |
| uv run --offline --frozen bandit -r apps/api/src ml/data/src | PASS: 911 lines, zero issues or suppressions. |
| docker compose -p alphalens-p1b config --quiet | PASS with process-only random test credentials; never printed resolved config. |
| docker compose -p alphalens-p1b up -d --wait --wait-timeout 90 postgres | PASS: PostgreSQL healthy. First pull was slow; no paid registry. |
| uv run --offline --frozen pytest -W error -ra tests/integration/test_database_connectivity.py | First FAILED: Windows async-driver incompatibility; sensitive assertion output retired with test volume and credential. |
| uv run --offline --frozen pytest -W error -ra --tb=line | Intermediate: 62 passed, 1 failed, 1 skipped; after network fix: 63 passed, 1 skipped; final date/numeric hardening run: 64 passed, 1 skipped, 0 warnings. No weakening of assertions or warning policy. |
| docker compose -p alphalens-p1b port postgres 5432 | Before bridge fix: invalid IP:0. After: 127.0.0.1:5432. |
| docker compose -p alphalens-p1b exec -T postgres psql -U alphalens -d alphalens -c 'SELECT 1, version();' | PASS inside container while host TCP was refused; identified network publication issue independently of DB health. |
| Host TCP/psycopg diagnostic | Failed connection before network fix; no database substitute. Error details redacted. |
| docker volume inspect / docker volume rm alphalens-p1b_postgres_data | Confirmed task-created Compose labels and removed the stopped disposable initial volume before rotating test credentials. No user volume removed. |
| Psycopg TEST_ONLY persistence probe | PASS: committed marker, stop/start, equal marker read, table dropped. PostgreSQL 17.11. No market/application schema created. |
| docker compose -p alphalens-p1b stop postgres; up -d --wait --wait-timeout 90 postgres | PASS for persistence verification. |
| docker compose -p alphalens-p1b down --volumes | PASS in finally blocks for isolated task project; temporary volume removed after tests. |
| docker compose ls / docker ps -a / docker volume ls filtered to alphalens-p1b | PASS: no task containers, networks or volumes left running/retained. |
| One documentation apply_patch | Rejected incorrect context atomically; corrected targeted patch succeeded. |

`uv` above means `.tools/bin/uv.exe`. Python probes use `.venv/Scripts/python.exe`;
network documentation/capture uses its already locked httpx. Docker credentials are
fresh process-only random values. No .env was written. Exact replay/reacquisition
recipe and metadata are in docs/data/research-fixture-source.md and the manifest.
Public searches were limited to this research-fixture decision/access/quote-unit
question, not a repeat of the completed NSE/provider research. Yahoo quote-page
checks returned 429 and were stopped; no Yahoo data was acquired or substituted.

Final review added a null-close future-session guard and strict decimal lexical
validation with TEST_ONLY edge checks. The last full real-PostgreSQL run was
64 passed, 1 production/live skip. A late Ruff format check caught two formatting
issues in the new Markdown Python recipe; `ruff format docs/data/research-fixture-source.md`
corrected them and the final format check passed (65 files). Final mypy and Bandit
passed (31 files / 911 lines, no findings). Raw/manifest/replay and historical-body
audits passed. Original source, provider.py, uv.lock and D01-D35 remain unchanged.

## Historical command records retained unchanged

---

# P1 free-data strategy command and research ledger

Date: 2026-10-05. Started clean on existing `p1-free-data-strategy` at
`f8400265f6e6877da4154a916d87cd163a59071d`. No branch creation, reset, restore,
discard, merge or push. The accepted paid-provider research is preserved.

Commands use `git -c safe.directory=C:/Users/Dell/AlphaLens`; no global trust was
changed. Repeated read-only commands/web queries are grouped below. Shell batches
are distinguished from the exit status of individual failed operations.

| ID | Command / operation | Actual result |
| --- | --- | --- |
| FD01 | `git ... status --short --branch`; `git ... log -1`; `Get-FileHash AlphaLens_Complete_Project_Documentation.docx -Algorithm SHA256` | PASS: expected clean branch/base, original hash matched before edits. |
| FD02 | `Get-Content -Encoding UTF8` of AGENTS.md, DECISIONS.md, product contract/roadmap, existing provider/validation/verification/log documents, pyproject.toml; `rg --files docs ml/data` | PASS: current evidence and authority inspected; focused reads followed truncated tool output. |
| FD03 | Public web search/open/find/click calls for NSE/NSE Indices reports, MCP, reference, actions, filings, indices, research policy and terms; Docker/PostgreSQL licence documentation | Research completed. 27 source IDs/locators and retrieval limitations in free-data-evaluation.md. No account, purchase, MCP handshake, market API invocation, CSV capture or normalized market records. |
| FD04 | Repeated `git ... status`, `Get-FileHash`, focused `Get-Content` and `rg -n` for universe/record contracts | PASS: source unchanged; NIFTY_500-only literal and existing schema gaps confirmed without code edits. |
| FD05 | `apply_patch` on decisions/instructions/product/roadmap; create two free-data research documents | PASS: user amendments distinguished from original specification; method/gate labelled proposals. |
| FD06 | Grouped `rg -n` / `Get-Content` for README, architecture, data contract, setup and integration tests; `git ... diff --stat` | PARTIAL: nonexistent docs/development/setup.md and tests/integration/test_postgres.py caused lookup failures; grouped shell exit 0 came from final Git operation. No implementation defect established. |
| FD07 | `rg --files docs/development tests/integration`, then `Get-Content` of actual local-setup.md and test_database_connectivity.py | PASS: corrected paths found/read; no replacement files created. |
| FD08 | Inline `.venv/Scripts/python.exe -B -` prefix helper | PASS: current-policy banners prepended to three prior data reports; original bodies preserved byte-for-byte. |
| FD09 | `apply_patch` for README, system-boundaries.md and local-setup.md | PASS: removed stale mandatory-universe/cloud implications and documented conditional Docker Desktop free eligibility. No runtime change. |
| FD10 | Focused official terms spot-checks via web find | PASS as evidence review: NSE clauses 8/9 and NSE Indices 7/12/20 support stated restrictions. No project licence obtained. |
| FD11 | `.tools/bin/uv.exe run --offline --frozen pytest -W error -ra` | PASS: 47 passed, 2 skipped, 0 warnings, 0.57 seconds; exit 0. |
| FD12 | `.tools/bin/uv.exe run --offline --frozen ruff check .` | PASS: all checks passed; exit 0. |
| FD13 | `.tools/bin/uv.exe run --offline --frozen ruff format --check .` | PASS: 60 files already formatted; exit 0. |
| FD14 | `.tools/bin/uv.exe run --offline --frozen mypy` | PASS: no issues in 27 files; exit 0. |
| FD15 | `.tools/bin/uv.exe run --offline --frozen bandit -r apps/api/src ml/data/src` | PASS: 533 lines, no issues/suppressions; exit 0. |
| FD16 | Inline `.venv/Scripts/python.exe -B -` documentation/preservation audit | PASS: 12 changed documentation files before log/report update; 132 unique-state cells, 27 source IDs, citations/links, original report bytes/D01-D25/source hash, unchanged code/lock/main, ignore rules/empty example secrets/TEST_ONLY, no adapter/data/frontend, narrow secret-pattern scan. |
| FD17 | `git ... diff --check`; `git ... status --short --branch` | PASS: no whitespace errors; only intended documentation edits/new research files. |
| FD18 | Final evidence-state review and `apply_patch` | PASS: downgraded unsupported inferences about identifiers, departures, action coverage and calendar revisions to UNKNOWN. No new source claims. |
| FD19 | Inline `.venv/Scripts/python.exe -B -` prefix helper for verification-report.md and this ledger | PASS: actual results/limits recorded; earlier report/log bodies retained as historical evidence. |
| FD20 | Final inline preservation/source/scope audit; `git ... diff --check` | PASS: exactly 14 intended documentation files; five historical report/log bodies preserved byte-for-byte, 132 matrix cells and 27 source IDs valid; source/main/code/lock unchanged; whitespace clean. |
| FD21 | `git ... add --` with the fourteen explicit paths listed below; `git ... diff --cached --check`; `git ... diff --cached --stat`; `git ... status --short --branch` | PASS: staged only intended documentation, no whitespace errors, correct branch. |

Before final resume, no Docker commands were run in the free-data strategy task.
The resume check below again found the daemon unavailable. No dependency installs,
service startup, vulnerability re-audit, real-data ingestion or later-phase
implementation occurred. The two pytest skips do not pass external-data/runtime gates.

## Final resume: reconcile index and working tree

| ID | Command / operation | Actual result |
| --- | --- | --- |
| FR01 | `git ... branch --show-current`; `git ... status`; `git ... diff`; `git ... diff --cached`; `git ... log --oneline -5` | PASS: p1-free-data-strategy, fourteen intended staged files, two newer unstaged verification/log edits, HEAD f840026. No switch/reset/restore. |
| FR02 | Focused `Get-Content -Encoding UTF8` reads of all fourteen documents; `rg -n` punctuation inspection | PASS: policy/rights/gate consistency reviewed; truncated diff output followed by focused reads. No new web research. |
| FR03 | `docker info --format '{{.ServerVersion}}'` with explicit exit propagation | FAIL / external blocker: exit 1, dockerDesktopLinuxEngine pipe absent. No container started or database substitute used. |
| FR04 | `.tools/bin/uv.exe run --offline --frozen pytest -W error -ra` | PASS: 47 passed, 2 skipped, 0 warnings, 0.71 seconds; exit 0. PostgreSQL/provider skips remain legitimate unresolved gates. |
| FR05 | `.tools/bin/uv.exe run --offline --frozen ruff check .` | PASS: all checks passed; exit 0. |
| FR06 | `.tools/bin/uv.exe run --offline --frozen ruff format --check .` | PASS: 60 files already formatted; exit 0. |
| FR07 | `.tools/bin/uv.exe run --offline --frozen mypy` | PASS: no issues in 27 source files; exit 0. |
| FR08 | `.tools/bin/uv.exe run --offline --frozen bandit -r apps/api/src ml/data/src` | PASS: 533 lines, no issues or suppressions; exit 0. |
| FR09 | Inline `.venv/Scripts/python.exe -B -` prefix-only punctuation repair; targeted `apply_patch` result updates | PASS: existing new banners corrected without touching original historical bytes; actual resume/Docker/check results recorded. No implementation/evidence change. |
| FR10 | Final inline documentation/evidence/policy/preservation audit; `git ... diff --check`; `git ... diff --cached --check` | PASS: fourteen intended files, 132 single-state cells, 27 source IDs, twelve policy checks, links/punctuation, original DOCX hash and historical bodies, unchanged code/lock/main and secret/fixture controls. Both whitespace checks exit 0. |

Current changed-file scope (fourteen files; all documentation/instructions):
AGENTS.md; DECISIONS.md; README.md; docs/architecture/system-boundaries.md;
docs/product/product-contract.md; docs/product/roadmap-and-acceptance.md;
docs/data/provider-decision.md; docs/data/provider-evaluation.md;
docs/data/p1-validation-report.md; docs/data/free-data-evaluation.md;
docs/data/free-data-strategy.md; docs/development/local-setup.md;
docs/development/verification-report.md; docs/development/command-log.md.

The final scope/preservation audit and initial staged checks passed. This results
update is restaged before the final commit. Commit hash and post-commit status are
reported in the task's final response; this file does not predict its own commit hash.

## Earlier command ledger retained verbatim

All entries below describe earlier tasks and their then-current scope/authorization.
Paid-provider questions are historical; D26-D35 govern current V1 policy.

---

# Executed command ledger

## 2026-10-04/05: P1 provider evaluation and resumed verification

Scope: public provider research and local runtime verification only. The resumed
turn began from the existing uncommitted research on `p1-provider-evaluation`.
No reset, restore, discard, merge, purchase, account, vendor message, authenticated
provider request, adapter implementation or P2 work occurred. File edits were
limited to the six research/verification documents listed below.

Git commands use the existing per-command prefix
`git -c safe.directory=C:/Users/Dell/AlphaLens`; no global trust was changed.
Python tools run through `.tools/bin/uv.exe` and the existing frozen environment.
Read-only commands and repeated document reads are grouped; substantive checks
and nonzero exits are listed separately. PASS refers only to the named check.

### Research turn before interruption

| ID | Command / operation | Actual result |
| --- | --- | --- |
| PE01 | `Get-FileHash AlphaLens_Complete_Project_Documentation.docx -Algorithm SHA256`; AGENTS.md/DECISIONS.md/documentation reads; Git status and `rg` file inventory | PASS: approved source hash matched; main clean before branching. |
| PE02 | `git ... switch -c p1-provider-evaluation` | PASS: branch created from main `9fa82284936f8b7a34f5409ba25cdce3538747b6`. |
| PE03 | `docker version` followed by `docker compose version` | PARTIAL: CLI 29.6.2 and Compose v5.3.1 reported; daemon query failed. Combined shell exit 0 came from the final Compose command, not a healthy engine. |
| PE04 | `docker info --format '{{.ServerVersion}}'` with `exit $LASTEXITCODE` | FAIL / external blocker: exit 1, dockerDesktopLinuxEngine pipe absent. |
| PE05 | `docker compose config --quiet` with process-only TEST_ONLY environment values and cleanup in `finally` | PASS: exit 0, no .env created; not a database connectivity test. |
| PE06 | Read-only DOCX extraction via `python -B -` using ZIP/XML; paragraph and roadmap-table inspections | PASS: original P1 representative-history exit gate confirmed; DOCX not written. |
| PE07 | Public web search/open/find/click operations for provider documentation, tariffs and terms | Research completed; 42 source IDs and retrieval limitations recorded in [provider-research-sources.md](../data/provider-research-sources.md). Failed/timeout URLs were not treated as evidence of non-support. |
| PE08 | `Get-Content`/`rg` reads of contracts, neutral provider, test gates and development documentation | PASS: schema gaps documented; no code changed. |
| PE09 | `.tools/bin/uv.exe run --offline --frozen pytest -W error -ra` | PASS: 47 passed, 2 skipped, 0 warnings; 0.65 seconds. PostgreSQL and live-provider gates skipped. |
| PE10 | `git ... diff --stat` and research-document reads | PASS: inspected in-progress documentation changes. |
| PE11 | Documentation-only `apply_patch` operations and inline `python -B -` reference/spacing helpers | PASS: existing research developed and source references linked; no implementation or market payload added. |

No PostgreSQL container was started, so no health/connectivity result or teardown
was possible/necessary. No database substitute was used. Public documentation
examples were read as documentation only; no example numerical data or embedded
API keys were copied into project files.

### Resume from the current working tree on 2026-10-05

| ID | Command / operation | Actual result |
| --- | --- | --- |
| PR01 | `git ... status --short --branch`; `git ... diff --stat`; `git ... diff -- docs/data/p1-validation-report.md docs/data/provider-decision.md docs/data/provider-evaluation.md docs/development/verification-report.md` | PASS: expected branch, four modified reports and untracked evidence register preserved. |
| PR02 | `Get-Content -Encoding UTF8` for AGENTS.md, DECISIONS.md, research reports/register, command log, compose.yaml, PostgreSQL test, pyproject.toml and .gitignore; `Get-FileHash ... -Algorithm SHA256` | PASS: authoritative source unchanged. Long tool output was truncated; focused `Select-Object -First/-Skip` reads completed review of the relevant sections. |
| PR03 | `docker info --format '{{.ServerVersion}}'` with explicit exit propagation | FAIL / external blocker: exit 1, same absent Linux-engine pipe. |
| PR04 | Compose validation block below | PASS: exit 0. Configuration-only TEST_ONLY scalars; process values removed; no .env or services created. |
| PR05 | `.tools/bin/uv.exe run --offline --frozen pytest -W error -ra` | PASS: 47 passed, 2 skipped, 0 warnings; 0.63 seconds. Initial process returned a session handle; polling returned exit 0. |
| PR06 | `.tools/bin/uv.exe run --offline --frozen ruff check .` | PASS: all checks passed, exit 0. |
| PR07 | `.tools/bin/uv.exe run --offline --frozen ruff format --check .` | PASS: 58 files already formatted, exit 0. |
| PR08 | `.tools/bin/uv.exe run --offline --frozen mypy` | PASS: no issues in 27 source files, exit 0. |
| PR09 | `.tools/bin/uv.exe run --offline --frozen bandit -r apps/api/src ml/data/src` | PASS: 533 lines scanned, no issues or suppressions, exit 0. |
| PR10 | Public web spot-checks of existing sources I1, N4, N5, G2, G11, E1, E7 and E12 | PASS as document review: confirmed bounded claims; added N4 reporting-basis ambiguity and selected-ratio evidence. No provider data tested or rights granted. A text search with no match was followed by direct section inspection. |
| PR11 | `rg -n` contract/fixture markers; focused verification-report reads; `git ... diff --check` | PASS: reviewed contract limitations and existing controls; no whitespace errors. |
| PR12 | Inline `python -B -` spacing helper over the four research reports | PASS: prose readability updated; existing evidence retained. |
| PR13 | First inline documentation/source/scope/secret audit via `python -B -` | FAIL: exit 1 at an incorrect audit assumption that Python fixture builders lived in tests/fixtures. Earlier assertions reached that point successfully. No repository defect or test failure established. |
| PR14 | `rg --files tests`; `rg -n 'TEST_ONLY\|TEST-ONLY\|make_test_only' tests` (regex alternation) | PASS: builders in tests/conftest.py; tests/fixtures/README.md documents fixture policy. |
| PR15 | Corrected inline audit via `python -B -` | PASS: 42 source IDs; 165 main-matrix cells with unique states; all 30 dimensions for shortlist and supplement; source references/local links; unchanged DOCX/code/decisions/lock/main; ignore rules and TEST_ONLY markers in 12 files. No narrow credential-pattern matches. |
| PR16 | Targeted documentation edits via `apply_patch` | PASS: current results, explicit unresolved schema conflict, scoped ratio/cost evidence and this ledger recorded. No data, provider or implementation files modified. |
| PR17 | Extended inline audit; `git ... diff --check`, `git ... diff --numstat`, `git ... status --short --branch` | Audit helper FAIL: exit 1, generated Python had an unterminated string because JavaScript replacement expanded a dollar expression. No repository file was written by the helper. Separate Git checks passed. |
| PR18 | Corrected extended inline audit via `python -B -` | PASS: all PR15 checks, plus each source-reference URL matches its evidence-register entry. The helper's string construction was corrected; no project implementation changed. |

PR04 used the following configuration-validation block. These scalars are
explicitly TEST_ONLY, never persisted, and are not valid connection credentials.
Compose validation does not validate a PostgreSQL URL or establish connectivity.

```powershell
$env:POSTGRES_PASSWORD = 'TEST_ONLY_CONFIGURATION_VALIDATION'
$env:ALPHALENS_DATABASE_URL = 'TEST_ONLY_CONFIGURATION_VALIDATION'
try {
  docker compose config --quiet
  $alphaComposeExit = $LASTEXITCODE
} finally {
  Remove-Item Env:POSTGRES_PASSWORD
  Remove-Item Env:ALPHALENS_DATABASE_URL
}
exit $alphaComposeExit
```

The audit checked source-reference definitions, all mandatory dimension numbers,
one allowed evidence state per matrix cell, citations for positive/partial and
explicit non-support claims, local links, the approved DOCX SHA256, exact branch
and main baseline, an allowlist of changed paths, ignored secret paths, absent
.env/data, empty example secret fields, TEST_ONLY labels and narrow credential
patterns. It is not a comprehensive secret scan or an empirical provider test.
No dependency installation or fresh pip-audit was needed for these documentation
changes; the previous vulnerability result remains explicitly historical.

Final Git operations are limited to reviewing/staging these paths, a staged diff
check, the authorized branch commit and read-only status/hash checks. Their final
outcome and commit hash are reported to the user after execution; this ledger
does not attempt to embed its own future commit hash:

- docs/data/provider-evaluation.md
- docs/data/provider-decision.md
- docs/data/p1-validation-report.md
- docs/data/provider-research-sources.md
- docs/development/verification-report.md
- docs/development/command-log.md

## Earlier foundation remediation (historical command records)

The sections below predate this P1 branch. They preserve failures and fixes from
the approved foundation baseline, not commands newly executed during research.

## Network-enabled foundation remediation

The user enabled access for dependency installation/verification only. No P2 or
provider access occurred. Current results supersede former environment blockers.

| ID | Command/check | Result |
| --- | --- | --- |
| N1 | Resume: DOCX checksum, Git status and configuration reads | PASS |
| N2 | python -m pip install --disable-pip-version-check --no-warn-script-location --target .tools uv==0.11.25 | PASS |
| N3 | Scoped Git status + Docker versions/server query | FAIL (recorded, corrected or external blocker) |
| N4 | Read bootstrap executable path and prior command ledger | FAIL (recorded, corrected or external blocker) |
| N5 | Inspect foundation code | PASS |
| N6 | uv version + initial uv lock | PASS |
| N7 | Read bootstrap executable path and prior command ledger | PASS |
| N8 | uv lock + sync --frozen | PASS |
| N9 | Git ignore and DOCX checksum checks | PASS |
| N10 | .tools/bin/uv.exe run --frozen ruff check . | FAIL (recorded, corrected or external blocker) |
| N11 | .tools/bin/uv.exe run --frozen ruff format --check . | PASS |
| N12 | .tools/bin/uv.exe run --frozen mypy | PASS |
| N13 | .tools/bin/uv.exe run --frozen bandit -r apps/api/src ml/data/src | PASS |
| N14 | .tools/bin/uv.exe run --frozen pytest -W error | PASS |
| N15 | .tools/bin/uv.exe run --frozen pip-audit --skip-editable | PASS |
| N16 | uv lock + sync --frozen | PASS |
| N17 | .tools/bin/uv.exe run --frozen ruff check . | FAIL (recorded, corrected or external blocker) |
| N18 | .tools/bin/uv.exe run --frozen ruff format --check . | FAIL (recorded, corrected or external blocker) |
| N19 | .tools/bin/uv.exe run --frozen mypy | PASS |
| N20 | .tools/bin/uv.exe run --frozen bandit -r apps/api/src ml/data/src | PASS |
| N21 | .tools/bin/uv.exe run --frozen pytest -W error | PASS |
| N22 | .tools/bin/uv.exe run --frozen ruff check --show-files . | PASS |
| N23 | .tools/bin/uv.exe run --frozen ruff format apps/api/src ml/data/src tests | PASS |
| N24 | .tools/bin/uv.exe run --frozen ruff check . | PASS |
| N25 | .tools/bin/uv.exe run --frozen ruff format --check . | PASS |
| N26 | uv lock --check + isolated exact-version inventory | PASS |
| N27 | Source/ignore/fixture/credential-pattern audit | PASS |
| N28 | Read development documents for atomic updates | PASS |

The first resume's Git status failed on ownership even though checksum/read commands
completed; per-command trust fixed it without global Git configuration changes.
The premature bootstrap-path inspection ran before pip finished and failed; the
later inspection verified .tools/bin/uv.exe. Ruff failures were corrected rather
than suppressed. Docker server queries still fail: no engine pipe exists.

Git staging/diff audit/initial commit and final status are reported to the user.
Full local verification: lint/format/mypy/Bandit/pip-audit pass; pytest 47 passed,
2 external skips, no warnings. Source DOCX unchanged. No fake provider/DB/data.


## Foundation remediation command results

These results belong to the subsequent FOUNDATION REMEDIATION ONLY request.
They supplement the historical implementation ledger below.

| ID | Command/check | Actual result |
| --- | --- | --- |
| R1 | Initial checksum, workspace, AGENTS.md, three pyproject.toml reads and git rev-parse --show-toplevel | FAIL / see report (exit 1) |
| R2 | git init --initial-branch=main | PASS |
| R3 | Python/interpreter/distribution and installed TestClient source inventory | PASS |
| R4 | Sanitized pip configuration inspection | PASS |
| R5 | git status --short --branch | PASS |
| R6 | docker --version | FAIL / see report (exit 1) |
| R7 | Get-Content -LiteralPath docs/development/local-setup.md | PASS |
| R8 | python -m pip cache list | PASS |
| R9 | Bounded TestClient source and project HTTP dependency inspection | PASS |
| R10 | Get-Content -LiteralPath tests/integration/test_api_health.py | PASS |
| R11 | python -B -m pytest -p no:cacheprovider -W error | PASS |
| R12 | docker compose config --quiet (TEST_ONLY env) | PASS |
| R13 | python -B -m pip check | PASS |
| R14 | Source, ignore, fixtures, syntax/TOML/YAML audit | FAIL / see report (exit 1) |
| R15 | Provider status CLI | EXPECTED BLOCK (exit 2) |
| R16 | git --version | PASS |
| R17 | Source, ignore, fixtures, syntax/TOML/YAML audit | PASS |

R1's final nonzero exit was expected `git rev-parse` before repository creation;
the DOCX checksum verification succeeded. R3's verbose diagnostic output was
truncated by the tool; R9 repeated only the relevant TestClient source lines and
confirmed the project explicitly requires httpx. R5's Git identity was configured;
identity values are omitted here. R14's width failure was corrected and R17 passed.
R18 (git add -- .) subsequently failed on .git/index.lock permissions in that sandbox.
No network installation was retried in this remediation while access was pending.

Network-dependent commands awaiting enabled access:
`python -m pip install --target .tools uv==0.11.25`, followed by verified
`uv lock`, `uv sync --frozen`, and vulnerability-service access for pip-audit.
Initial Git staging/diff checks and commit are recorded in the final user report.

## 23. PASS: final read-only audit

```powershell
@'
from pathlib import Path
import hashlib
root=Path('.')
skip={'.venv','.tools','.local-data','.cache','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.git'}
def show(path,prefix=''):
 entries=sorted((p for p in path.iterdir() if p.name not in skip),key=lambda p:(not p.is_dir(),p.name.lower()))
 for i,p in enumerate(entries):
  last=i==len(entries)-1
  print(prefix+('`-- ' if last else '|-- ')+p.name+('/' if p.is_dir() else ''))
  if p.is_dir(): show(p,prefix+('    ' if last else '|   '))
print('AlphaLens/')
show(root)
files=[p for p in root.rglob('*') if p.is_file() and not any(part in skip for part in p.parts)]
print('SOURCE_FILES',len(files))
print('DOCX_SHA256',hashlib.sha256(Path('AlphaLens_Complete_Project_Documentation.docx').read_bytes()).hexdigest())
'@ | python -B -
```

Result: 72 authored/source files; unchanged DOCX checksum. The full tree is in
repository-tree.md. This audit followed command 22; it is placed here to keep its
output separate from the lengthy earlier command transcripts.

A documentation patch appending this entry initially failed to match line-ending
context in captured output; this corrected edit used a stable heading. No code or
source DOCX was changed by that failed edit.


All shell commands executed during this implementation turn are listed below in order
of invocation. Independent calls may have completed in a different order. No genuine
credentials were supplied or printed. TEST_ONLY strings are constructed local/test
values. File edits used apply_patch; source extraction was read-only. Web lookups
checked official tooling/documentation, not provider data or licensed access.

PASS means that specific command completed; it does not pass unrelated external
phase gates. EXPECTED BLOCK is intentional nonzero provider absence. Failed tool
invocations are not described as passing lint/type/security checks.

## 1. PASS

```powershell
Get-ChildItem -Force | Select-Object Mode,Name,Length
rg --files -g 'AGENTS.md' -g '!node_modules' -g '!.git'
Get-FileHash -Algorithm SHA256 -LiteralPath AlphaLens_Complete_Project_Documentation.docx
@('uv','ruff','mypy','pytest','docker','git','python') | ForEach-Object { $tool = Get-Command $_ -ErrorAction SilentlyContinue; if ($tool) { [PSCustomObject]@{Tool=$_;Path=$tool.Source} } else { [PSCustomObject]@{Tool=$_;Path='NOT FOUND'} } }
python -m pip --version
```

Result:

```text
Only DOCX present. rg found no AGENTS; pip available. PowerShell formatting hid hash/tool rows; repeat needed.
rg found no pre-existing AGENTS.md (expected no matches); final shell exit was 0.
```

## 2. PASS

```powershell
@'
import sys,zipfile,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile('AlphaLens_Complete_Project_Documentation.docx') as z:
 ps=ET.fromstring(z.read('word/document.xml')).findall('.//w:p',ns)
 for i,p in enumerate(ps):
  if 669<=i<=827 or 927<=i<=955:
   s=''.join(t.text or '' for t in p.findall('.//w:t',ns))
   if s: print(f'{i} {s}')
'@ | python -B -
```

Result:

```text
Read-only roadmap, inconsistencies and open decisions review.
```

## 3. PASS

```powershell
@'
import importlib.metadata as m, sys, hashlib, pathlib, shutil
print('SOURCE_SHA256',hashlib.sha256(pathlib.Path('AlphaLens_Complete_Project_Documentation.docx').read_bytes()).hexdigest())
print('PYTHON',sys.version.split()[0])
for name in ['uv','ruff','mypy','pytest','docker','git','python']:
 print('TOOL', name, shutil.which(name) or 'NOT FOUND')
for name in ['fastapi','pydantic','pydantic-settings','httpx','pytest','ruff','mypy','psycopg','uv','pip-audit','bandit']:
 try: print('PACKAGE',name,m.version(name))
 except m.PackageNotFoundError: print('PACKAGE',name,'NOT INSTALLED')
'@ | python -B -
```

Result:

```text
SOURCE_SHA256 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a
PYTHON 3.12.4
TOOL uv NOT FOUND
TOOL ruff NOT FOUND
TOOL mypy NOT FOUND
TOOL pytest C:\Users\Dell\AppData\Roaming\Python\Python312\Scripts\pytest.EXE
TOOL docker C:\Users\Dell\AppData\Local\Programs\DockerDesktop\resources\bin\docker.EXE
TOOL git C:\Program Files\Git\cmd\git.EXE
TOOL python C:\Program Files\Python312\python.EXE
PACKAGE fastapi 0.141.1
PACKAGE pydantic 2.13.4
PACKAGE pydantic-settings 2.15.0
PACKAGE httpx 0.28.1
PACKAGE pytest 9.1.1
PACKAGE ruff NOT INSTALLED
PACKAGE mypy NOT INSTALLED
PACKAGE psycopg NOT INSTALLED
PACKAGE uv NOT INSTALLED
PACKAGE pip-audit NOT INSTALLED
PACKAGE bandit NOT INSTALLED

```

## 4. FAIL

```powershell
python -m pip install --disable-pip-version-check --no-warn-script-location --target .tools uv
```

Result:

```text
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<pip._vendor.urllib3.connection.HTTPSConnection object at 0x000001AB40FEB410>: Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions')': /simple/uv/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<pip._vendor.urllib3.connection.HTTPSConnection object at 0x000001AB40FEBC20>: Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions')': /simple/uv/
WARNING: Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<pip._vendor.urllib3.connection.HTTPSConnection object at 0x000001AB40FEBB90>: Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions')': /simple/uv/
WARNING: Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<pip._vendor.urllib3.connection.HTTPSConnection object at 0x000001AB41008290>: Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions')': /simple/uv/
WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<pip._vendor.urllib3.connection.HTTPSConnection object at 0x000001AB410082F0>: Failed to establish a new connection: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions')': /simple/uv/
ERROR: Could not find a version that satisfies the requirement uv (from versions: none)
ERROR: No matching distribution found for uv

```

## 5. PASS

```powershell
python -m pip cache list
```

Result:

```text
Cache contents:

 - metaphone-0.6-py3-none-any.whl (14 kB)

```

## 6. PASS

```powershell
@'
from pathlib import Path
for path in Path('tests').rglob('*.py'):
 text=path.read_text(encoding='utf-8')
 text=text.replace('test_only_price', 'make_test_only_price').replace('test_only_provenance', 'make_test_only_provenance')
 path.write_text(text, encoding='utf-8', newline='\n')
print('Renamed TEST-ONLY fixture builders to avoid pytest collecting helper functions.')
'@ | python -B -
```

Result:

```text
Renamed TEST-ONLY fixture builders to avoid pytest collecting helper functions.

```

## 7. PASS

```powershell
python -B -m pytest -p no:cacheprovider
```

Result:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Dell\AlphaLens
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1, html-4.2.0, metadata-3.1.1
collected 46 items

tests\contract\test_provider_contract.py ....                            [  8%]
tests\contract\test_provider_normalization.py ...                        [ 15%]
tests\integration\test_api_health.py ....                                [ 23%]
tests\integration\test_database_connectivity.py s                        [ 26%]
tests\integration\test_provider_live.py s                                [ 28%]
tests\integration\test_sample_replay.py ....                             [ 36%]
tests\unit\test_configuration.py ....                                    [ 45%]
tests\unit\test_data_validation.py ...............                       [ 78%]
tests\unit\test_log_redaction.py ..                                      [ 82%]
tests\unit\test_temporal_eligibility.py ........                         [100%]

============================== warnings summary ===============================
..\AppData\Roaming\Python\Python312\site-packages\fastapi\testclient.py:1
  C:\Users\Dell\AppData\Roaming\Python\Python312\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
SKIPPED [1] tests\integration\test_database_connectivity.py:15: Real PostgreSQL not configured: ALPHALENS_TEST_DATABASE_URL absent
SKIPPED [1] tests\integration\test_provider_live.py:8: BLOCKED: no approved vendor adapter, licensed access or historical sample
================== 44 passed, 2 skipped, 1 warning in 1.15s ===================

```

## 8. FAIL

```powershell
python -m pip install --disable-pip-version-check --no-warn-script-location --retries 0 --timeout 3 --target .tools ruff mypy bandit pip-audit "psycopg[binary]"
```

Result:

```text
ERROR: Could not find a version that satisfies the requirement ruff (from versions: none)
ERROR: No matching distribution found for ruff

```

## 9. FAIL

```powershell
docker --version
docker compose version
docker info --format '{{.ServerVersion}}'
```

Result:

```text
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.
Docker version 29.6.2, build dfc4efb
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.
Docker Compose version v5.3.1
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.

failed to connect to the docker API at npipe:////./pipe/docker_engine; check if the path is correct and if the daemon is running: open //./pipe/docker_engine: The system cannot find the file specified.

Version commands succeeded individually; docker info failed. Combined shell exit was 1.
```

## 10. FAIL

```powershell
python -m ruff check .
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named ruff

```

## 11. FAIL

```powershell
python -m ruff format --check .
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named ruff

```

## 12. FAIL

```powershell
python -m mypy
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named mypy

```

## 13. FAIL

```powershell
python -m bandit -r apps/api/src ml/data/src
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named bandit

```

## 14. FAIL

```powershell
python -m pip_audit
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named pip_audit

```

## 15. PASS

```powershell
@'
import ast,pathlib,tomllib,importlib.util
for name in ['psycopg','uvicorn','hatchling','httpx2','yaml']:
 print('MODULE',name,'AVAILABLE' if importlib.util.find_spec(name) else 'NOT AVAILABLE')
files=list(pathlib.Path('apps/api/src').rglob('*.py'))+list(pathlib.Path('ml/data/src').rglob('*.py'))+list(pathlib.Path('tests').rglob('*.py'))
for path in files:
 text=path.read_text(encoding='utf-8')
 ast.parse(text,filename=str(path))
 for n,line in enumerate(text.splitlines(),1):
  if len(line)>100: print('LONG_LINE',str(path),n,len(line))
for path in [pathlib.Path('pyproject.toml'),pathlib.Path('apps/api/pyproject.toml'),pathlib.Path('ml/data/pyproject.toml')]:
 tomllib.loads(path.read_text(encoding='utf-8'))
print('PASS: syntax for',len(files),'Python files; 3 TOML files parsed. This is NOT Ruff or mypy.')
'@ | python -B -
```

Result:

```text
MODULE psycopg NOT AVAILABLE
MODULE uvicorn AVAILABLE
MODULE hatchling NOT AVAILABLE
MODULE httpx2 NOT AVAILABLE
MODULE yaml AVAILABLE
LONG_LINE ml\data\src\alphalens_data\contracts.py 101 102
LONG_LINE ml\data\src\alphalens_data\sample_ingestion.py 73 102
LONG_LINE tests\contract\test_provider_normalization.py 15 101
LONG_LINE tests\integration\test_api_health.py 14 101
LONG_LINE tests\integration\test_api_health.py 38 102
LONG_LINE tests\integration\test_sample_replay.py 43 104
LONG_LINE tests\integration\test_sample_replay.py 46 105
LONG_LINE tests\integration\test_sample_replay.py 71 104
LONG_LINE tests\integration\test_sample_replay.py 80 106
LONG_LINE tests\integration\test_sample_replay.py 83 101
LONG_LINE tests\integration\test_sample_replay.py 85 106
LONG_LINE tests\unit\test_log_redaction.py 22 104
LONG_LINE tests\unit\test_temporal_eligibility.py 31 105
PASS: syntax for 27 Python files; 3 TOML files parsed. This is NOT Ruff or mypy.

```

## 16. PASS

```powershell
$env:POSTGRES_PASSWORD = 'TEST_ONLY_CONFIG_VALUE'
$env:ALPHALENS_DATABASE_URL = 'postgresql://test_only:TEST_ONLY_CONFIG_VALUE@postgres/test_only'
docker compose config --quiet
```

Result:

```text
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.

```

## 17. FAIL

```powershell
docker build -f infra/docker/api.Dockerfile -t alphalens-foundation:local .
```

Result:

```text
WARNING: Error loading config file: open C:\Users\Dell\.docker\config.json: Access is denied.
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/

unable to prepare context: unable to evaluate symlinks in context path: Access is denied.

```

## 18. EXPECTED BLOCK

```powershell
$env:PYTHONPATH = 'ml/data/src'
python -B -m alphalens_data.sample_ingestion
```

Result:

```text
{"capabilities": "UNKNOWN", "error_code": "PROVIDER_NOT_SELECTED", "message": "Selection, licensed access and real representative history are required.", "real_records_ingested": 0, "status": "BLOCKED"}

CLI intentionally returns 2. First PowerShell call surfaced 1; explicit exit $LASTEXITCODE in the later call confirmed 2.
```

## 19. PASS

```powershell
python -B -m pytest -p no:cacheprovider
```

Result:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Dell\AlphaLens
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1, html-4.2.0, metadata-3.1.1
collected 49 items

tests\contract\test_provider_contract.py ....                            [  8%]
tests\contract\test_provider_normalization.py ...                        [ 14%]
tests\integration\test_api_health.py ....                                [ 22%]
tests\integration\test_database_connectivity.py s                        [ 24%]
tests\integration\test_provider_live.py s                                [ 26%]
tests\integration\test_sample_replay.py ....                             [ 34%]
tests\unit\test_configuration.py .....                                   [ 44%]
tests\unit\test_data_validation.py ...............                       [ 75%]
tests\unit\test_log_redaction.py ..                                      [ 79%]
tests\unit\test_temporal_eligibility.py ..........                       [100%]

============================== warnings summary ===============================
..\AppData\Roaming\Python\Python312\site-packages\fastapi\testclient.py:1
  C:\Users\Dell\AppData\Roaming\Python\Python312\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
SKIPPED [1] tests\integration\test_database_connectivity.py:15: Real PostgreSQL not configured: ALPHALENS_TEST_DATABASE_URL absent
SKIPPED [1] tests\integration\test_provider_live.py:8: BLOCKED: no approved vendor adapter, licensed access or historical sample
================== 47 passed, 2 skipped, 1 warning in 0.58s ===================

```

## 20. PASS

```powershell
@'
import ast,pathlib,tomllib,yaml,hashlib
roots=['apps/api/src','ml/data/src','tests']
files=[p for root in roots for p in pathlib.Path(root).rglob('*.py')]
for p in files:
 text=p.read_text(encoding='utf-8')
 ast.parse(text,filename=str(p))
 assert all(len(line)<=100 for line in text.splitlines()), 'Line width >100: '+str(p)
for p in [pathlib.Path('pyproject.toml'),pathlib.Path('apps/api/pyproject.toml'),pathlib.Path('ml/data/pyproject.toml')]:
 tomllib.loads(p.read_text(encoding='utf-8'))
for name in ['compose.yaml','.github/workflows/ci.yml','.github/dependabot.yml','.pre-commit-config.yaml']:
 yaml.safe_load(pathlib.Path(name).read_text(encoding='utf-8'))
actual=hashlib.sha256(pathlib.Path('AlphaLens_Complete_Project_Documentation.docx').read_bytes()).hexdigest()
assert actual=='196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a'
assert not pathlib.Path('ml/data/src/alphalens_data/providers/selected_provider.py').exists()
assert [p.name for p in pathlib.Path('ml/data/src/alphalens_data/providers').glob('*.py')]==['__init__.py']
assert not pathlib.Path('apps/web/package.json').exists()
assert not pathlib.Path('uv.lock').exists(), 'Lockfile state changed: must verify generated lock'
assert not pathlib.Path('.local-data').exists(), 'Unexpected persisted dataset'
print('PASS: Python syntax/line widths; 3 TOML and 4 YAML parses; unchanged DOCX SHA256; no vendor/frontend/data or fake lockfile.')
print('This is NOT Ruff, mypy, secret scanning or container verification.')
'@ | python -B -
```

Result:

```text
PASS: Python syntax/line widths; 3 TOML and 4 YAML parses; unchanged DOCX SHA256; no vendor/frontend/data or fake lockfile.
This is NOT Ruff, mypy, secret scanning or container verification.

```

## 21. EXPECTED BLOCK

```powershell
$env:PYTHONPATH = 'ml/data/src'
python -B -m alphalens_data.sample_ingestion
exit $LASTEXITCODE
```

Result:

```text
{"capabilities": "UNKNOWN", "error_code": "PROVIDER_NOT_SELECTED", "message": "Selection, licensed access and real representative history are required.", "real_records_ingested": 0, "status": "BLOCKED"}

CLI intentionally returns 2. First PowerShell call surfaced 1; explicit exit $LASTEXITCODE in the later call confirmed 2.
```

## 22. FAIL

```powershell
python -m uv lock --check
```

Result:

```text
C:\Program Files\Python312\python.exe: No module named uv

```
## P2 raw-ingestion verification - 2026-10-06

- Inspected git status/branch/log; current P1 work was uncommitted. User explicitly
  chose review/verify/commit of P1 as baseline before branching.
- Baseline: 63 tests passed, 2 skipped; Ruff/mypy/Bandit and lock/frozen sync passed.
  Committed approved P1 as 3f8880c; created p2-raw-ingestion; no main merge.
- Resolved/installed free PyArrow and explicit psycopg data-package dependency;
  generated genuine uv.lock (66 packages), frozen sync (65 installed).
- Final commands: uv lock --check; uv sync --frozen; pytest -W error -ra;
  ruff check .; ruff format --check .; mypy; bandit -r apps/api/src ml/data/src;
  git diff --check. All requested implementation gates passed.
- Real PostgreSQL runner: scripts/verify_p2_postgres.py starts a dedicated local
  Compose project, applies db migration via integration test, runs full suite
  (96 passed/1 production-provider skip), CLI replay and teardown. No DSNs/secrets
  printed or committed. File CLI run twice verifies duplicate identity/replay.
- DOCX SHA256 unchanged. Details/failures/limits: p2-verification-report.md.
- P2 DEVELOPMENT PASSED; production clearance OPEN. P3 not started.
