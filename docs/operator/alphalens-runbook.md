# AlphaLens private Windows runbook

Run from PowerShell in `D:\al-research\p28-worktree`. Keep the existing operator,
private configuration and Windows Credential Manager entries. These commands do
not create another account or reset a password.

## Start, inspect and stop

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\start-p33-alphalens.cmd
```

This starts the owned local PostgreSQL instance and the compiled private app.
Open <http://127.0.0.1:8017/login> and use the existing operator credentials.
The experimental workspace is <http://127.0.0.1:8017/experimental-ai-v2>.
From a second PowerShell window:

```powershell
.\scripts\windows\check-alphalens.cmd .local-data\p33-runtime\operator-config.json
.\scripts\windows\stop-p33-alphalens.cmd
```

The stop command stops the matched native app and owned PostgreSQL process.
To stop only that app while retaining PostgreSQL, use:

```powershell
.\scripts\windows\stop-alphalens.cmd .local-data\p33-runtime\operator-config.json
```

## Use the research application

Search an NSE symbol in Stock Analysis and explicitly load provider observations.
Read the provider timestamps, freshness and delayed/indicative label. Switch the
chart source to inspect the frozen archive separately. A displayed quote is not
an execution or official portfolio mark.

Experimental AI Stock Research V2 shows saved model scores, company identity,
dated technical evidence, preferences and recorded portfolio cost concentration.
Top 5/10/20 never pads unavailable securities. The page refreshes saved local
evidence every minute while visible; it does not acquire prices or train models.
Use the linked charts, Evidence Passport, historical leaders and Research Decision
Desk to investigate. Preferences filter research; they do not alter model scores.
Portfolio cost weights are distinct from market-value exposure.

Forward Evaluation shows pending, excluded, missing and unknown evidence. Zero
matured outcomes means prospective performance is not yet measurable. The entry
timestamp and five subsequent eligible sessions must genuinely occur; a missed
entry is never backdated. Accepted rankings remain unavailable until independent
research, economic and review requirements actually pass.

## Bounded manual daily workflow

```powershell
.\scripts\windows\run-v2-research.cmd .local-data\final-operational-runtime\v2-workflow.json --dry-run
```

The dry run checks local evidence and clock readiness without requesting provider
prices. After an eligible session closes, this explicit manual command permits
the guarded acquisition/reconciliation/inference sequence:

```powershell
.\scripts\windows\run-v2-research.cmd .local-data\final-operational-runtime\v2-workflow.json --collect
```

The private configuration bounds one session per run, catch-up, cooldown and
provider quotas. Current limits are 120 GETs/run, at most three runs/day and a
60-minute cooldown. Missing publication stays pending; rerun only when permitted
by the recorded cooldown. Successful replay does not redownload complete sessions.
New evidence appends immutable snapshots and forecasts; it never retrains a model
on a dashboard visit. Check Saved Research Operations for the latest state and
sanitized failure stage before retrying.

The existing `AlphaLens-Private-EOD-Watchlist` RELIANCE task remains separate at
08:30 IST. The larger V2 proposal is prepared, **not activated**. Its proposed
20:30/21:30/22:30 IST slots are conservative operational choices, not a guaranteed
provider publication time. Expanded recurring collection requires the specific
recorded approval. Both workflows require Windows running, the same operator
logged in and the original protected credential available.

```powershell
Get-ScheduledTask -TaskName AlphaLens-Private-EOD-Watchlist
.\scripts\windows\check-v2-research-task.ps1 -Config .local-data\final-operational-runtime\v2-workflow.json
```

The check prepares no task, enables no collection and requests no provider prices.
If data, clock, credentials, identity or calendar evidence fails, keep the reported
failure; inspect the named prerequisite before another bounded run. Do not edit
timestamps, feature values, model weights or receipts to clear a check.

## Back up and restore personal operational records

Use new destinations. Pause manual record edits while taking a cross-store backup.
The existing tool uses SQLite online backup and integrity/checksum manifests:

```powershell
$stamp = Get-Date -Format yyyyMMdd-HHmmss
.\scripts\windows\backup-alphalens.cmd .local-data\p33-runtime\operator-config.json ".local-data\operator-backup-$stamp"
.\scripts\windows\project-python.cmd -m alphalens_api.operations.cli restore --source ".local-data\operator-backup-$stamp" --destination ".local-data\operator-restored-$stamp"
```

Restore writes a new isolated location, verifies file integrity and removes copied
login sessions. It does not replace the running stores or alter the source backup.
Review the restored records before considering a configuration change. Existing
online-backup/isolated-restore tests cover authentication, personal FIFO records,
alerts and operations. The backup includes the configured P19 prospective store
when present; it does **not** claim to back up PostgreSQL, Windows Credential
Manager, the frozen archive or the separate V1/V2 experimental evidence/ledgers.
Keep those preserved private roots intact and keep backups out of Git/public demo.

Read-only preservation verification is available through:

```powershell
.\scripts\windows\project-python.cmd -m scripts.verify_ml_v2_preservation
```

This hashes frozen research and original alerts, checks V1 artifacts, accounts
and personal records, and writes a new private metadata receipt. It performs no
provider price request or original research rerun.
