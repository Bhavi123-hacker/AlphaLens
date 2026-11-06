param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference = 'Stop'
$configPath = (Resolve-Path -LiteralPath $Config).Path
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$name = 'AlphaLens-Private-NSE-Market-Research'
$task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
# Verify the registered action before stopping this specific owned task.
if (-not ($task.Actions | Where-Object { $_.Arguments.Contains($configPath) -and $_.Arguments.Contains('auto --scheduled') })) {
    throw 'Expanded task does not reference the supplied approved configuration'
}
Stop-ScheduledTask -TaskName $name -ErrorAction Stop
$basePython = & (Join-Path $PSScriptRoot 'project-python.cmd') -c 'import sys; print(sys._base_executable)'
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePython)) {
    throw 'Trusted project Python identity could not be verified'
}
# Some Windows Python redirectors outlive a stopped cmd task. Reap only the
# exact configured worker module; never match the UI, RELIANCE or other Python.
$workers = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and
    $_.CommandLine -match '\-m workers\.nse_market run ' -and
    $_.CommandLine.Contains($configPath) -and
    $_.CommandLine.Contains('--scheduled') -and
    ($_.ExecutablePath.StartsWith($repo + '\.venv\', [System.StringComparison]::OrdinalIgnoreCase) -or
     $_.ExecutablePath.Equals($basePython, [System.StringComparison]::OrdinalIgnoreCase))
}
foreach ($worker in $workers) { Stop-Process -Id $worker.ProcessId -ErrorAction Stop }
[pscustomobject]@{state='OWNED_EXPANDED_TASK_STOPPED';matched_worker_processes=@($workers).Count;reservation_released=$false;original_reliance_task_modified=$false} | ConvertTo-Json -Compress
