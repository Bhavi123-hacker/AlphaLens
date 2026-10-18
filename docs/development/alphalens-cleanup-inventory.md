# AlphaLens safe project cleanup inventory

Scope: `D:\al-research\p28-worktree`, branch `full-nse-consolidation` from `b1b69086a234a62aaf3f69a2508086958d9818b7`.

Reviewed inventory: `2026-10-17T11:32:01.383493+00:00`. Cleanup completed: `2026-10-17T11:32:01.937687+00:00`. Immediate after inventory: `2026-10-17T11:32:04.754477+00:00`.

## Observed storage and Git classification

These are actual regular-file sizes under the worktree, without traversing junctions or the external Git directory. Allocated bytes come from Windows `FileStandardInfo.AllocationSize`; these sums exclude directory/MFT overhead and are not a claim about the volume free-space change or deduplicated hard-link allocation.

| Snapshot/category | Files | Logical bytes | Allocated file bytes |
|---|---:|---:|---:|
| Reviewed before | 12,825 | 1,619,513,154 | 1,636,054,360 |
| Immediate after | 12,360 | 1,582,679,130 | 1,598,416,664 |
| Git tracked, before | 917 | 17,404,172 | 19,124,504 |
| Git ignored, before | 11,902 | 1,602,063,377 | 1,616,876,448 |
| Git untracked, before | 6 | 45,605 | 53,408 |
| Disposable Python caches, before | 467 | 36,910,341 | 37,719,616 |
| Non-private generated browser outputs, retained | 2 | 7,595 | 8,240 |

All private `.local-data` content was retained: **11,432 files / 1,565,141,848 logical bytes** in the reviewed snapshot. The untracked count includes new work from parallel consolidation tasks; it does not identify disposable files.

| Excluded link/metadata | Target and action |
|---|---|
| `.venv` junction | `D:\al-research\p17-api\workspace-venv-original`; target not traversed or changed. |
| `apps/web/node_modules` junction | `D:\al-research\p18-runtime\node_modules`; target not traversed or changed. |
| `.git` pointer | Points to `C:/Users/Dell/AlphaLens/.git/worktrees/p28-worktree`; pointer retained, external history not traversed or changed. |
| Original external frozen archive | `D:/al-research/tejhq-research-evaluation-v2-fit-parallel`; outside this folder inventory, not removed or moved. Its independent preservation check remains required. |

## Important retained categories

Classification supports review only. No item was deleted because its name suggested an old, duplicate, backup, archive or test file.

| Path/category | Files | Logical bytes | Decision |
|---|---:|---:|---|
| `.local-data/p30-postgres` | 3,508 | 674,781,556 | PostgreSQL binaries and live data; essential |
| `.local-data/final-security-audit` | 4,169 | 202,006,168 | Scanner evidence and isolated history diagnostic clone; retained |
| `.local-data/final-research-backup-verified` | 257 | 105,015,113 | Verified research backup; retained |
| `.local-data/final-research-backup-diagnostic` | 257 | 105,015,113 | Diagnostic backup/evidence; retained |
| `.local-data/final-research-restored-verified` | 257 | 105,015,113 | Isolated restore proof; retained |
| `.local-data/final-research-backup` | 255 | 104,984,959 | Research backup; retained |
| `.local-data/experimental-nse-v2` | 200 | 70,923,762 | Real dataset, models, forecasts and outcomes; essential |
| `.local-data/experimental-nse-v1` | 55 | 34,053,081 | Original V1 dataset/model/evaluation; essential |
| `.local-data/p31-browser-runtime` | 585 | 57,256,920 | Browser/operator fixture runtime with authentication and persisted records; retained |
| `.local-data/final-operational-web-build` | 48 | 1,845,624 | Compiled application assets; retained |
| `.local-data/ml-v2-web-build` | 48 | 1,838,585 | Prior compiled application and rollback evidence; retained |
| `.local-data/nse-universe` | 5 | 4,857,228 | New consolidation identity evidence at snapshot time; retained |

Other private builds, browser traces, historical reports, logs, credential/authentication stores, personal stores and recovery evidence were retained. They may contain private data or support reproducibility and rollback; this cleanup makes no unsupported claim that they are redundant. No quarantine was needed because ambiguous items stayed in place.

## Actual cleanup

**Removed 467 generated cache files from 35 cache roots: 36,910,341 logical bytes and 37,719,616 allocated file bytes.**

| Removed cache root | Files removed | Logical bytes removed |
|---|---:|---:|
| `.mypy_cache` | 3 | 30,515,429 |
| `.pytest_cache` | 5 | 135,250 |
| `.ruff_cache` | 52 | 41,038 |
| `apps/api/src/alphalens_api/auth/__pycache__` | 5 | 45,531 |
| `apps/api/src/alphalens_api/core/__pycache__` | 5 | 12,333 |
| `apps/api/src/alphalens_api/local/__pycache__` | 3 | 25,515 |
| `apps/api/src/alphalens_api/operations/__pycache__` | 6 | 45,192 |
| `apps/api/src/alphalens_api/__pycache__` | 23 | 306,701 |
| `backtesting/src/alphalens_backtesting/__pycache__` | 8 | 100,950 |
| `decision/src/alphalens_decision/__pycache__` | 18 | 203,276 |
| `ml/data/src/alphalens_data/canonical/__pycache__` | 11 | 119,813 |
| `ml/data/src/alphalens_data/daily/__pycache__` | 4 | 26,824 |
| `ml/data/src/alphalens_data/ingestion/__pycache__` | 9 | 49,801 |
| `ml/data/src/alphalens_data/providers/__pycache__` | 7 | 59,618 |
| `ml/data/src/alphalens_data/quality/__pycache__` | 5 | 54,846 |
| `ml/data/src/alphalens_data/universe/__pycache__` | 5 | 47,257 |
| `ml/data/src/alphalens_data/__pycache__` | 10 | 48,281 |
| `ml/evaluation/src/alphalens_evaluation/__pycache__` | 9 | 95,878 |
| `ml/features/src/alphalens_features/__pycache__` | 8 | 58,360 |
| `ml/labels/src/alphalens_labels/__pycache__` | 7 | 62,555 |
| `ml/training/src/alphalens_training/__pycache__` | 7 | 52,845 |
| `portfolio/src/alphalens_portfolio/__pycache__` | 12 | 148,078 |
| `scripts/__pycache__` | 60 | 461,107 |
| `tests/contract/__pycache__` | 2 | 9,046 |
| `tests/integration/__pycache__` | 28 | 524,317 |
| `tests/unit/__pycache__` | 82 | 2,761,281 |
| `tests/__pycache__` | 1 | 5,904 |
| `workers/alerts/__pycache__` | 5 | 67,302 |
| `workers/daily/__pycache__` | 11 | 102,476 |
| `workers/experimental_nse/__pycache__` | 8 | 127,290 |
| `workers/experimental_nse_v2/__pycache__` | 9 | 250,546 |
| `workers/intelligence/__pycache__` | 2 | 15,844 |
| `workers/personal/__pycache__` | 9 | 87,985 |
| `workers/providers/__pycache__` | 26 | 240,333 |
| `workers/__pycache__` | 2 | 1,539 |

Only `.mypy_cache`, `.pytest_cache`, `.ruff_cache` and Python `__pycache__` directories were eligible. All bytecode-cache contents were `.pyc`/`.pyo` files. Underlying Python source files, tracked files, data and build assets were not deletion targets.

Before deletion the parent engineer paused development checks and coordinated the other agents. Each absolute target and each child was verified inside the resolved worktree. Private paths, Git metadata, dependencies, parent escapes and reparse points were refused. Every Windows file passed an exclusive-access preflight. The active application and PostgreSQL processes were preserved. Deletion used direct Python file unlink/directory removal with repeated path/reparse checks; no broad recursive shell deletion, Git clean/reset, external junction traversal or history rewrite occurred.

The immediate folder logical-size decrease was 36,834,024 bytes. This is separate from the gross deleted-byte count: new receipts and concurrent source work changed the tree. Subsequent genuine data acquisition, builds and tests will grow the folder and regenerate caches. Report final delivery size separately; do not portray valuable new data as failed cleanup.

## Verification and repeatable commands

Four TEST_ONLY safety tests passed on Windows, including creation and rejection of a real junction; none was skipped in the final run. Tests reject private/escaping paths, tracked cache contents and unexpected bytecode-cache files, and verify exact removed-byte accounting while preserving source. Ruff passed. Targeted strict mypy passed. An earlier symlink test was skipped for unavailable symlink privilege, then replaced with a least-privilege junction test and passed. An initial explicit mypy invocation named the imported module twice; the corrected test-module invocation passed.

`git fsck --connectivity-only --no-dangling` passed (exit 0). `http://127.0.0.1:8017/api/v1/health/live` returned `alive` after cleanup; the original PostgreSQL processes were still running. No frontend rebuild was required by cache deletion because compiled assets and dependencies were preserved. Full application restart, preservation, browser, PostgreSQL and final CI evidence belongs in the consolidation acceptance report.

Private, ignored receipts: `.local-data/full-nse-cleanup/inventory-reviewed.json`, `removed.json`, and `inventory-after.json`. The earlier `inventory-before.json` is preliminary and is superseded by `inventory-reviewed.json` for both Git classification and allocated-byte measurements. No receipt includes file contents or secret values.

Inventory only:

```powershell
.\scripts\windows\project-python.cmd scripts\cleanup_inventory.py --output .local-data\full-nse-cleanup\inventory-delivery.json
```

Repeat removal only after stopping concurrent tests, formatters and type checks and reviewing a fresh inventory. Use new receipt filenames; existing receipts cannot be overwritten:

```powershell
.\scripts\windows\project-python.cmd scripts\cleanup_inventory.py --output .local-data\full-nse-cleanup\inventory-next.json
.\scripts\windows\project-python.cmd scripts\cleanup_inventory.py --apply-inventory .local-data\full-nse-cleanup\inventory-next.json --development-checks-stopped --output .local-data\full-nse-cleanup\removed-next.json
.\scripts\windows\project-python.cmd scripts\cleanup_inventory.py --output .local-data\full-nse-cleanup\inventory-after-next.json
```

## Entrypoint and duplicate review

The Windows wrapper files have no exact SHA-256 duplicates. `start-p30/p31/p32/p33-alphalens.cmd` bind different preserved private configurations; they delegate to the shared `start-alphalens.cmd` and `project-python.cmd`. The current `start-p33` wrapper also starts the owned PostgreSQL service. They are useful compatibility/recovery entrypoints, not unused copies. Removing them would break documented commands or recovery paths. The V2 wrapper delegates to the single V2 CLI and uses an explicit mode allowlist. No tracked source or operational entrypoint was removed or renamed without evidence.

## Final delivery snapshot

The authoritative final tree measurement will be appended after new coverage acquisition, regression tests and compilation. The completed cleanup totals above remain immutable evidence of the actual removal; final folder growth is reported separately.
