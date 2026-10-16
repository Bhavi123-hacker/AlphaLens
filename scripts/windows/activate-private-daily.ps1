param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$configPath = (Resolve-Path -LiteralPath $Config).Path
$statusRoot = Split-Path -Parent $configPath
$xmlPath = Join-Path $statusRoot 'daily-task-enabled.xml'
$taskName = 'AlphaLens-Private-EOD-Watchlist'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'Existing task must be reviewed; no automatic replacement' }
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& (Join-Path $PSScriptRoot 'project-python.cmd') -m workers.providers.automation --config $configPath --export-task $xmlPath --enable-prepared-task --principal-sid $sid
if ($LASTEXITCODE -ne 0) { throw 'Independent source, clock and zero-request replay prerequisites failed' }
Register-ScheduledTask -TaskName $taskName -Xml ([System.IO.File]::ReadAllText($xmlPath)) | Out-Null
$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
if ($task.Settings.Enabled -ne $true -or $task.Principal.RunLevel -ne 'Limited' -or $task.Principal.LogonType -ne 'Interactive') { throw 'Least privilege task readback failed' }
$status = @{ name=$taskName; enabled=$true; state=[string]$task.State; next_run=$info.NextRunTime.ToString('o'); run_level=[string]$task.Principal.RunLevel; logon_type=[string]$task.Principal.LogonType; schedule='08:30 Asia/Kolkata; prior dated sessions only'; publication_guarantee=$false }
$status | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $statusRoot 'daily-task-status.json') -Encoding UTF8
$status | ConvertTo-Json
