# P19 development verification (D74)

Approved starting commit: `5e02e5cd1b120e200def460b3ab037fb27df9ec7`.
Branch: `p19-daily-research`. Verification performed on Windows with Python
3.12.4, Node 22.23.3 and PostgreSQL 17.11. No historical model fit, model
selection, holdout inference/evaluation or backtest was rerun.

**P19_DEVELOPMENT_PASSED. P19_LIVE_DATA_ACTIVATION = BLOCKED.**
This is software acceptance of the offline incremental worker, safe recovery,
gated adapter and read integration. It is not acceptance of a live provider,
new-session inference, complete-universe daily processing or production deployment.

## Verification results

| Check | Actual result |
|---|---|
| Windows-safe full `pytest -W error -ra` | 636 passed, 6 skipped, 1 failed, 1212.82 seconds. Failure was a new API test expecting the lexical string `101.0` instead of the exact value `101`; assertion corrected to Decimal equivalence. No financial calculation changed. |
| Final P19 unit/API tests | **49 passed**, 20.54 seconds, including the corrected API assertion and three additional identity/policy/CLI cases. |
| Actual persisted P17 research integration | All **5** opt-in cases passed separately with configured local frozen artifacts; a seven-case focused run including the corrected assertion/scheduler test passed in 36.96 seconds. Read-only holdout access; no reevaluation. |
| Repository coverage across full run and required retries/additions | **645 distinct tests passed; one production/live-provider skip** out of 646 currently collected cases. This is combined verification, not a claim that the original full invocation exited zero. |
| PostgreSQL | Real PostgreSQL 17.11 regression cases passed in the full run: disposable database creation, persistence, replay/recovery and teardown. P19 uses its independent atomic filesystem store; it does not add a competing SQL schema. |
| Frozen lock/sync | `uv lock --check` and `uv sync --frozen` passed; lock checksum unchanged. |
| Ruff / formatting | Passed across 312 Python files after final formatting/import ordering. |
| Strict mypy | Passed across 193 source files; request/preservation helpers also passed explicitly. |
| Bandit / Python dependency audit | Passed, with new worker included; no known dependency vulnerabilities. Editable project packages are intentionally skipped by pip-audit, covered by static checks. |
| Frontend unit/components | **43 passed**. |
| Frontend static/build/audit | TypeScript, ESLint, production build passed; npm audit reported zero vulnerabilities. Existing 588 kB chart-chunk advisory remains. No dependency/lock changes. |
| Actual browser integration | **5 passed**, 38.4 seconds, against running loopback API and real persisted data. Genuine stock chart/SMA200, model metrics, unresolved backtest, OOS reads and P19 blocked status verified. |
| Accessibility / visual review | Axe WCAG checks returned zero violations. Desktop and 390px mobile screenshots actually inspected; no document horizontal overflow. Dense timeline remains readable with wrapped reasons. |
| OpenAPI | Current additive schema generated at `docs/api/p19-openapi.json`; frozen P17 contract file unchanged. |
| Git whitespace | `git diff --check` passed before delivery. |

## Real bounded replay

The existing pinned 2026 native Parquet was replayed for **2026-10-06** into a
separate D-drive P19 store. This is not a new market session or a repeated P9/P10
evaluation. Raw bytes were captured through P2 and native parsing/normalization;
P3 reported **2,942 VALID**, zero quarantined. Session-only validation cannot
establish complete cross-session anomaly coverage and states that limitation.
Research identity/type assessment found 2,589 research-equity candidates,
351 known non-equity exclusions and two unknown/unusable instruments.

Features were explicitly scoped to two evidenced securities, using **400 trailing
context rows**, bounded by the P6 lookback. This is not full-universe feature or
inference coverage. Existing SMA100/SMA200 formulas produced real values, labeled
DEGRADED because actionable corporate-action evidence remains unavailable:

| Security ID | SMA100 | SMA200 |
|---|---:|---:|
| `tejhq:isin:INE002A01018` | 1297.077 | 1365.685 |
| `tejhq:isin:INE467B01029` | 2237.363 | 2527.9795000000004 |

Measured elapsed processing: **15.9557 seconds**; repeated identical request:
**0.1571 seconds**, same verified receipt. Windows process peak working set:
**183,246,848 bytes**, including imports and ingestion. This does not measure
full-universe inference. See [performance receipt](p19-performance.json).
Run: `39053e9cf4c8b1509046fc3ab6bd29c046b59a85a0d9d3c12ae05edd7b05ccbf`.

## Failure history and safeguards

An early development replay omitted P3 normalized-lineage evidence and correctly
rejected every row. The worker now supplies the existing normalized checksum
contract; the correction uses separately versioned execution/canonical identities.
The earlier failed receipt remains retained. It was never presented as valid data.
An initial browser locator matched multiple replay rows; it was made explicitly
deterministic. An initial Windows memory-measurement call failed after a successful
replay; the later correctly typed measurement above is the reported result.
An XML-parser Bandit finding was resolved by serialization-only escaped XML, without
a suppression. None of these repairs changed frozen domain policies or data.

Tests cover permission/session boundaries, official missing special-session slots,
no future identity backfill, P3 quality rejection, revision separation, crashes at
publication boundaries, kernel locks, retry limits, checksum tampering, fitted
preprocessing without fit calls, holdout-session inference rejection, policy pinning,
capture-clock-independent canonical identity and blocked CLI exit codes.

## Preservation and security

Read-only streaming SHA256 verification checked **2,485 files / 8,505,278,241
bytes** in 18.932 seconds against the approved inventory. All 152 fits, 504
backtests, 46,072,188 OOS rows, source/dataset hashes, model artifacts and frozen
evaluation/holdout reports remain unchanged. Protected code, DOCX, Python lock
and P17 OpenAPI match baseline. Main remains
`9fa82284936f8b7a34f5409ba25cdce3538747b6`.
See [preservation receipt](p19-artifact-preservation.json).

The sole CI configuration change extends Bandit to the new worker. TruffleHog
filters, exit behavior and Git-history scanning are unchanged; Trivy remains strict.
The three P18 unverified findings were traced to documented TEST_ONLY examples
and negative validation fixtures; zero verified findings, no established real
credential requiring rotation. No values are reproduced. This investigation does
not waive a strict CI failure. **44 HIGH OS container findings remain open**.
See [security review](p19-security-review.md).

## Acceptance limits

No ongoing provider passed permissions/calendar/new-release verification. Public
TejHQ metadata was observed, but no newer market-price payload was downloaded.
The latest evidenced market session remains **2026-10-06**. A real DAILY attempt
is `BLOCKED_SOURCE`; next unknown calendar dates are not guessed weekdays.
Inference, risk/ranking/signals and latest-new-session reads remain unavailable;
there is no production promotion or invented recommendation. The scheduler XML
is disabled and unregistered. P21 authentication is absent, so all services stay
loopback/local. Research reality/rights and final-vintage limitations remain explicit.

P19 development is accepted for the offline scope. Real activation requires the separately documented
provider/calendar/model compatibility gates. P20 requires a new user decision.
STOP after P19.

## Resume checkpoint and delivery review (2026-10-11)

The previous session ended on its usage limit after final verification, before
Git delivery. Its original P19 request, final command results and saved D-drive
receipts were inspected. The development branch still pointed to the exact P18
baseline, with the completed P19 implementation uncommitted. No Python/Node
worker or test was running. An older unrelated Git process and Docker processes
were left untouched; existing junctions/environments and all local evidence remain.

Already completed before resume: provider assessment; bounded P2-P6 replay and
feature parity; gated model adapter; unchanged policy snapshots; exclusive
receipts, locking and recovery; seven functional CLI commands; disabled scheduler
XML; additive API/OpenAPI; dashboard status/timeline; performance, preservation
and security reviews; the verification results above. No missing implementation
stage was inferred from an interrupted delivery. Initial checkpoint recovery
regenerated no implementation, dependency, historical fit, evaluation, backtest
or completed replay. The subsequent CI platform correction is recorded below.

Completed on resume: review of all existing P19 source/tests and the original
scope; D74 authorization/acceptance records; current README/setup/architecture
links; this checkpoint; final Git delivery review. New read-only checks verified:

| Resume check | Result |
|---|---|
| Frozen inventory | **2,485 files / 8,505,278,241 bytes**, all hashes unchanged; 40.983 seconds. See [separate resume preservation receipt](p19-resume-preservation.json). Original receipt retained. |
| Persisted P19 evidence | Six published receipts checksum-verified; zero incomplete checkpoints. The final replay receipt exactly matches all saved verify/resume/repeated-replay outputs. No new snapshot was created. |
| Contracts and policy | Current OpenAPI exactly matches saved P19 schema; P11-P14 policy snapshot/identity unchanged. Provider activation remains BLOCKED. |
| Prior automated gates | Session output confirms final 49 P19 tests, 43 frontend tests, five browser passes, static/build/audit results. Reused because source/dependencies are unchanged. No unnecessary full-suite rerun. |
| Security/CI baseline | GitHub P18 foundation run 37947866188 confirmed Python/PostgreSQL/static/audit checks passed before strict TruffleHog failure. Docker/Trivy steps were skipped in that run; the separate 44 HIGH finding receipt remains authoritative. Scanner behavior unchanged. |

The first direct invocation of the ignored resume helper used a script path and
could not resolve the root `workers` package. Running it as a module from the
repository root passed; this was an inspection-command correction, not a source
or environment change. Exact new checks:

```cmd
.venv\Scripts\python.exe -m scripts.verify_p19_preservation --run-root D:\al-research\tejhq-research-evaluation-v2-fit-parallel --output docs\development\p19-resume-preservation.json
.venv\Scripts\python.exe -m verification-local.p19_resume_verify
git diff --check
```

The ignored helper performs local assertions/read-only checks and is retained on
this workstation; normal delivery verification uses the committed worker `verify`
command documented in [P19 Windows operations](../pipeline/p19-windows-commands.md).
GitHub status for the delivered commit is reported separately from reused local
acceptance. A strict CI failure is never waived by software development acceptance.

## First P19 push and platform correction (2026-10-11)

The reviewed implementation/checkpoint was committed and pushed as
`3411e1a93d7c64fa0a812b419bff070a61cc5a97`; local/remote refs matched and the
working tree was clean. [Dashboard CI 38135181526](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38135181526)
passed its frozen-client/license checks, TypeScript, ESLint, unit tests, build and
audit. [Foundation CI 38135181535](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38135181535)
passed frozen lock/sync and Ruff, then exposed four Linux mypy errors for Windows
`msvcrt` lock symbols. Tests/security/container steps did not execute in that run.

The P19 kernel lock now selects its platform branch with `sys.platform == "win32"`,
which mypy understands when pruning Windows-only imports on Linux. Runtime
locking/unlocking operations are unchanged; no type-ignore, scanner weakening,
dependency change or historical-data mutation is introduced. Strict mypy passes
for the modified storage module with both `--platform linux` and `--platform win32`.
Ruff/format and targeted Bandit pass. The affected Windows kernel-lock, atomic
recovery and retry cases passed: **7 passed / 37 deselected, 3.79 seconds**.
The first sandboxed attempt could not access the existing D-drive test/cache paths;
the same command with approved filesystem access passed. No cache/environment was
deleted or relocated. Unrelated completed tests and browser checks are reused.
The correction is committed/pushed separately.

```powershell
.\.venv\Scripts\mypy.exe --platform linux ml/data/src/alphalens_data/daily/storage.py
.\.venv\Scripts\mypy.exe --platform win32 ml/data/src/alphalens_data/daily/storage.py
$env:ALPHALENS_TEST_TEMP_ROOT='D:/al-tests'
.\.venv\Scripts\pytest.exe tests/unit/test_p19_daily.py -k 'kernel_lock or recovery or operational_retry or retry_limit' -W error -ra --tb=short
```
