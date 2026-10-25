# Isolated collector preparation and reversible cutover

Prepared on 24 October; verification continued on 25 October 2026. This document
does not authorize a scheduled-task change or an additional provider request.

The preserved shared collector still has 41 advisory records in three packages:
certifi2026.7.22 (fixed2026.10.19), filelock4.0.10 (fixed4.2.1), and Pillow12.3.0
(fixed13.0.0). The isolated candidate uses certifi2026.10.19, filelock4.2.4 and
Pillow13.0.0 from the unchanged frozen lock. Its installed-distribution audit
reports zero known advisories. Advisory records are not unique CVE counts.

Both `AlphaLens-Private-NSE-Market-Research` and the original
`AlphaLens-Private-EOD-Watchlist` currently reach the shared `.venv` through their
existing wrappers. Neither definition, principal, trigger nor environment was
changed. The RELIANCE task is outside the proposed cutover.

The separate copy-mode candidate is
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe`.
`scripts/prepare_nse_collector_runtime.py` created it offline with pinned uv0.11.25
and `uv sync --frozen`; source lock and original installed-package metadata were
unchanged. Installation, audit and regression results are separate gates.
The live collector remains **BLOCKED_SECURITY**; adopting the replacement is
**BLOCKED_APPROVAL**, even after offline tests pass.

The prepared wrapper `scripts/windows/run-nse-collector-isolated.cmd` pins this
checkout's imports, retains CPU thread guards and invokes the existing launcher.
It has no task-registration capability. Its single argument must be the existing
protected 500-stock configuration. Executing it with that configuration would
request collection; it was not executed during this campaign.

## Approval-scoped future procedure

Only after explicit approval to replace this one task's interpreter/action, run
from this worktree. Do not use `Start-ScheduledTask` as a verification shortcut.
The code below is a future operator procedure, not an executed change.

```powershell
$repo = 'D:\al-research\p28-worktree'
$taskName = 'AlphaLens-Private-NSE-Market-Research'
$backup = Join-Path $repo '.local-data\production-readiness-20261024\approved-cutover-original.xml'
if (Test-Path -LiteralPath $backup) { throw 'Use a fresh backup filename' }
$task = Get-ScheduledTask -TaskName $taskName
if ($task.State -eq 'Running') { throw 'Wait for the existing bounded run to finish' }
$originalAction = $task.Actions
$xml = Export-ScheduledTask -TaskName $taskName
[IO.File]::WriteAllText($backup, $xml, [Text.UTF8Encoding]::new($false))
Get-FileHash -LiteralPath $backup -Algorithm SHA256
$arguments = '/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-collector-isolated.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json""'
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $arguments -WorkingDirectory $repo
Set-ScheduledTask -TaskName $taskName -Action $action
```

Re-export the resulting task and compare its XML: only the action may differ.
Keep the same principal, credential targets, triggers20:30/21:30/22:30 IST,
500 identities,250/run,600 reserved/run,1800/day,60-minute cooldown and31-day
catch-up. Preserve all active reservations and immutable checkpoints. Never
clear a consumed reservation to obtain another run. Wait for the next already
authorized trigger; require independent clock acceptance, bounded actual GETs,
durable terminal receipt, accepted per-security evidence, publication and
idempotent forecast lineage before claiming successful live cutover.

If that approved change fails, restore the in-memory original action in the
same session:

```powershell
Set-ScheduledTask -TaskName $taskName -Action $originalAction
```

After a new shell session, reconstruct only the original action from the saved
XML; do not recreate or overwrite the complete task/principal:

```powershell
[xml]$saved = Get-Content -LiteralPath $backup -Raw
$exec = $saved.Task.Actions.Exec
$rollback = New-ScheduledTaskAction -Execute ([string]$exec.Command) -Argument ([string]$exec.Arguments) -WorkingDirectory ([string]$exec.WorkingDirectory)
Set-ScheduledTask -TaskName $taskName -Action $rollback
```

Verify the restored XML against the original backup. Rollback restores the old
advisories, so it is operational recovery rather than security clearance. Retain
both runtimes, configs, logs and evidence; no deletion or production migration is
part of this procedure. The private8041 application continues using its separate
patched app runtime.
