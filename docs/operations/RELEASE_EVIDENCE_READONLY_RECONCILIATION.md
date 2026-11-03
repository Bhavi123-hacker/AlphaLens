# AlphaLens: Read-only release-evidence reconciliation

This checks **current accessible evidence** separately from **historical committed attestations**. It does not collect market data, modify SQLite databases, register tasks, or change Private V1. Only the optional report-output argument writes a file.

## Local Windows verification

In PowerShell (from the actual repository worktree):

```powershell
Set-Location 'D:\al-research\p28-worktree'
$python = 'python'
$ledger = '.\data\forecasts\matured_outcomes_ledger.db'

# Keep a byte-for-byte baseline hash; verify this path exists first.
if (Test-Path $ledger) { Get-FileHash $ledger -Algorithm SHA256 }

& $python scripts\reconcile_release_evidence.py --root . --ledger $ledger --check-windows-task

# Recheck the hash: reconciliation must not change the database.
if (Test-Path $ledger) { Get-FileHash $ledger -Algorithm SHA256 }

# Inspect the V2 Task Scheduler registration (READ ONLY).
schtasks /query /tn "AlphaLens-Daily-Settlement-V2" /fo LIST /v
```

The reconciliation command prints four evidence sections:

- **attestation**: 8,169 searchable equities = 3,214 NSE + 4,955 BSE; 451,468 accepted candles and 498 stocks in the November 2 completed session as stated in the committed release attestation. This is *historical attestation evidence*, not a live disk scan.
- **ledger**: reads the actual matured-outcomes SQLite database with `mode=ro`, checks SQLite integrity, counts settled outcomes, distinct dates/securities, and flags missing hashes or unqualified benchmark sources. `LOCAL_LEDGER_NOT_AVAILABLE` means the 601 claimed outcomes could not be independently verified in this environment.
- **market_view**: inspects the local immutable market-view snapshot, not the complete durable database.
- **daily_settlement_task**: queries Task Scheduler on Windows when requested; never installs or enables the task.

For a local V2 workflow dry run, only **after confirming the as-of market date and source files**:

```powershell
python scripts\daily_settlement_workflow.py --as-of-session 2026-11-02 --dry-run
```

This `--dry-run` path does **not** invoke settlement, but it can write a daily-settlement receipt JSON file under `docs/ml`. Do not run `--stage settle` if your purpose is read-only verification.

## Operational caveats

- The daily-settlement workflow's weekday check does **not** establish official NSE trading-holiday status. Cross-check the actual session calendar and data receipt before enabling a schedule.
- The Task Scheduler specification is `UNREGISTERED_PENDING_OPERATOR_APPROVAL` in source. CI cannot confirm the real Windows task registration.
- A report listing 450,970 candles is the older October baseline; the committed November 2 release attestation reports 451,468. Keep the observation dates attached to counts.
- `FULL_UNIVERSE_V2_COMPLETE` is still gated by authorized historical data for additional NSE/BSE stocks and genuine per-model prospective acceptance; do not promote from this read-only audit alone.
