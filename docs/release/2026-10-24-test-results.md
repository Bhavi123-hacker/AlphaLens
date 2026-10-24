# Release verification â€” 24 October 2026

Working branch: `alphalens-master-completion`, baseline
`da4382242371c17ebdf2cecc620541931b91e313`. Implementation checkpoint and final
delivery reference are recorded in the completion report. Commands run from the
D: worktree; private reports, credentials and market observations remain ignored.

## Executed checks

| Check / exact command or path | Result and limits |
|---|---|
| `.local-data/completion-runtime/venv/Scripts/python.exe -m scripts.verify_completion_release --output .local-data/completion-release-regression-20261024c` | **1582 passed,9 skipped,1248.94s**; pytest exit0 and owned PostgreSQL stop exit0. New disposable PostgreSQL17 cluster, not production migrations. Private `result.json` and `pytest.log` retained. |
| `python -m pytest -q -W error tests/integration/test_p17_real_research.py`, with four `ALPHALENS_TEST_REAL_*` roots read from existing config | **5 passed,17.20s** against actual frozen history/features/OOS reports and all474 unresolved summaries. Reads only; no fit, holdout evaluation or backtest execution. These separately verify five cases skipped by the generic suite. |
| `python -m pytest -q -W error tests/unit/test_saved_nse_market.py tests/integration/test_saved_nse_market_api.py tests/integration/test_nse_market_api.py tests/unit/test_saved_nse_workflow_verifier.py tests/unit/test_completion_preservation.py` | **37 passed,33.70s**, including late published-view no-rescan/corruption coverage. Overlaps generic regression; do not add counts as independent cases. |
| `python -m pytest -q -W error tests/unit/test_p22_operations.py tests/integration/test_p22_api.py tests/integration/test_p24_local.py` | **36 passed,9.64s** after the late monitoring-scope clarification and deterministic corruption-fixture timestamps. |
| Supported Node22 npm `test -- --maxWorkers=1` in isolated candidate frontend | **119 passed /24 files**,81.51s; explicit Windows30s interaction/hook deadlines. No removed assertions or tests. |
| Scoped frontend monitoring rerun after scope copy change | **7 passed /2 files**; existing operations and NSE operations components. |
| Candidate `npm run typecheck`, `npm run lint`, `npm run build`, `npm audit --audit-level=high` | Exit0 for all. Final scope-only build/lint receipts are retained separately in `frontend-scoped-verification.json`. |
| `python -m mypy --no-incremental` | **404 source files**, exit0. Later explicit-package-bases check over10 changed files/scripts/tests also exit0. |
| `python -m ruff check` over API/data/features/labels/training/evaluation/backtesting/decision/portfolio/workers/tests and new scripts | Exit0. `ruff format --check`:410 files already formatted at checkpoint; final changed-file formatting and `git diff --check` retained. |
| CI-target Bandit and isolated Python dependency audit | Passed; exact vulnerability results and preserved-environment failures in security report. No ignore lists or severity weakening. |
| Actual compatible model replay, `python -m scripts.verify_saved_nse_workflow ... --output .local-data/completion/saved-nse-workflow-final-20261024.json` | **302 rebuilt vectors /302 model scores, maximum absolute differences0**; deterministic Top5/10/20 and all20 selected source/feature/target/history matches. No new forecast, fit or outcome write. |
| Genuine HTTP smoke over `http://127.0.0.1:8041` before/after cooperative restart | Anonymous saved API401; login200; PostgreSQL ready200; saved price/history/research/evaluation200; Top20 returned; provider refresh503 while disabled. Original data/config preserved. |
| Compiled private browser, `completion-saved.spec.ts` | **1 passed**,25.5s overall: actual saved search, Top5/10/20, rationale, chart/volume, forecast history, pending outcomes and mobile overflow. API market responses were not mocked; provider/external requests prohibited. |
| Compiled private browser, `completion-offline.spec.ts` | **2 passed**, separate explicit TEST_ONLY responses: pending acquisition/quota/metrics distinction and failed-backend sign-in behavior. Not live-market evidence. |
| `python -m scripts.verify_completion_preservation --run-root D:/al-research/tejhq-research-evaluation-v2-fit-parallel --alerts-database D:/al-research/p20-runtime/alerts/alerts.sqlite3 --output .local-data/completion-20261024/frozen-preservation-final.json` | **2485 files /8505278241 bytes and47 original alerts verified** against immutable inventory/digest. Read-only; no estimator operations. |
| Original runtime baseline versus final read-only SQLite/model/config hashes | **201 items unchanged**; separate original private preservation receipt also retained. |
| Windows task export versus saved baseline SHA256 | Both expanded500 and original RELIANCE/watchlist definitions unchanged. No task start/registration/configuration action. |

The generic suite's nine skips are five unconfigured local frozen-read tests,
two separately unconfigured research-sample tests, one blocked live-provider test,
and one optional PyTorch environment test. The five frozen-read cases subsequently
passed with explicit real roots. No skip is a live-source, GPU or production pass.

## End-to-end acceptance

**COMPLETE_VERIFIED for dated saved experimental evidence:** real retained NSE
candles â†’ regenerated compatible features â†’ pinned model numerical inference â†’
deterministic risk Top5/10/20 â†’ compiled authenticated dashboard â†’ original forecast
history â†’ read-only qualified-outcome evaluation. Zero qualified matured outcomes
means null accuracy. This is not a newly published current prediction batch.

The source view contains500 configured securities and448230 verified observations.
Only248 securities have21 October, the latest retained session. The saved302 scores
use19 October observations. The original633 records represent602 unique decisions;
no new forecasts or outcome records were appended in this campaign.

## Failures retained and corrected

- An inherited generic regression attempt had stopped at38%; it is not counted.
- The first release harness invocation used an incorrect filesystem-helper keyword;
  corrected before a cluster started. Its generated disposable password file was
  removed; no original secret/store was touched.
- The next generic run stopped during collection on a new test's cross-directory
  fixture import. An independent local fixture corrected it; final generic run
  and clean cluster shutdown passed.
- Original frontend runs failed three5s interaction deadlines under cold Windows
  startup. The final run retains assertions with bounded30s Windows deadlines.
- The first genuine browser test assumed RELIANCE text matched a single company.
  Saved search legitimately returned multiple identities. The test now selects
  the exact RELIANCE symbol while preserving broad search behavior; rerun passed.
- A targeted corruption test could paginate the corrupt row when consecutive
  Windows clock ticks were equal. Explicit ordered TEST_ONLY timestamps remove
  random-ID dependence while retaining corruption rejection;36-case rerun passed.
- Full mypy initially caught nullable/Any annotations; corrected. A later direct
  script invocation duplicated namespace module names; `--explicit-package-bases`
  corrected the invocation, with10 files passing.
- A second derived publication succeeded but writing its separate audit receipt
  refused an existing filename. The original receipt was preserved, and the new
  immutable publication was read/verified under a distinct receipt.
- The immediate first restart probe preceded listener readiness and was refused.
  After actual LOCAL_PROCESS_READY, the complete HTTP path passed again.

Fresh code-image CI Trivy passed with0 HIGH/CRITICAL, and the frontend CI passed119 tests plus4 synthetic-demo browser cases. Full-history secret acceptance remains independent; final foundation results are recorded in the CI receipt. No full green release is inferred from individual job passes. No live provider request, scheduler change, public
deployment, paid resource or real order was used to obtain these results.

## Code-checkpoint GitHub verification

- Frontend40089744561 on876dcee: SUCCESS,119 tests and4 actual synthetic-demo browser cases; generated API/license checks, types/lint/build/audit also passed.
- Foundation40089744569: SUCCESS,1579 Linux/PostgreSQL17 tests /13 skips in251.63s, static/dependency gates and strict container. Fresh image artifact has0 HIGH/0 CRITICAL, created24Oct11:25:33UTC.
- The successful876dcee secret scan covers only2 chunks /176 bytes of notice changes. The first implementation scan40089709456 freshly failed with3 unverified findings. Historical-secret acceptance remains blocked; no detector/policy was suppressed.
- The final delivery browser rerun passed all3 private-app cases together in19.9s.

See [the exact CI scope and results](2026-10-24-github-verification.md). Final documentation-only commits do not change the tested code image.
