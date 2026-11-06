param(
    [Parameter(Mandatory=$true)][string]$Config,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$configPath = (Resolve-Path -LiteralPath $Config).Path
if ([System.IO.Path]::GetExtension($configPath) -ne '.json') { throw 'Private JSON configuration required' }
$allowed = [System.IO.Path]::GetFullPath((Join-Path $repo '.local-data'))
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
if (-not $output.StartsWith($allowed + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Task artifacts must remain inside this checkout private .local-data directory'
}
$ancestor = Split-Path -Parent $output
while ($ancestor.Length -ge $allowed.Length) {
    if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw 'Task artifact ancestor reparse point forbidden'
    }
    if ($ancestor -eq $allowed) { break }
    $ancestor = Split-Path -Parent $ancestor
}
if (Test-Path -LiteralPath $output) {
    if ((Get-Item -LiteralPath $output).Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'Task artifact reparse point forbidden' }
} else { New-Item -ItemType Directory -Path $output | Out-Null }
& (Join-Path $PSScriptRoot 'project-python.cmd') -c 'import sys; from pathlib import Path; from alphalens_api.auth.permissions import restrict, verify; target=Path(sys.argv[1]); restrict(target); verify(target)' $output
if ($LASTEXITCODE -ne 0) { throw 'Private task artifact permissions could not be verified' }
$xmlPath = Join-Path $output 'v2-research-task-disabled.xml'
$receiptPath = Join-Path $output 'v2-research-task-proposal.json'
if ((Test-Path -LiteralPath $xmlPath) -or (Test-Path -LiteralPath $receiptPath)) {
    throw 'Existing task preparation artifacts are immutable; use a new output directory'
}
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$escape = { param([string]$Value) [System.Security.SecurityElement]::Escape($Value) }
$command = & $escape (Join-Path $env:WINDIR 'System32/cmd.exe')
$wrapper = Join-Path $PSScriptRoot 'run-v2-research.cmd'
$arguments = & $escape ('/d /c ""' + $wrapper + '" "' + $configPath + '" --scheduled"')
$working = & $escape $repo
$principal = & $escape $sid
$tomorrow = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([datetime]::UtcNow, 'India Standard Time').Date.AddDays(1).ToString('yyyy-MM-dd')
$triggers = foreach ($slot in @('20:30:00','21:30:00','22:30:00')) {
    '<CalendarTrigger><StartBoundary>' + $tomorrow + 'T' + $slot + '+05:30</StartBoundary><Enabled>false</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>'
}
$xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
<RegistrationInfo><Description>PROPOSAL ONLY: bounded private AlphaLens V2 research; separate operator approval required; no orders</Description></RegistrationInfo>
<Triggers>$($triggers -join '')</Triggers>
<Principals><Principal id="LocalOperator"><UserId>$principal</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT30M</ExecutionTimeLimit><Enabled>false</Enabled></Settings>
<Actions Context="LocalOperator"><Exec><Command>$command</Command><Arguments>$arguments</Arguments><WorkingDirectory>$working</WorkingDirectory></Exec></Actions>
</Task>
"@
# Export only. This script has no task registration, enabling or provider calls.
[xml]$parsed = $xml
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($xmlPath, $xml, $encoding)
$receipt = [ordered]@{
    task_name='AlphaLens-Private-V2-Research'; registered=$false; enabled=$false
    cadence_ist=@('20:30','21:30','22:30'); maximum_slots_per_ist_day=3
    minimum_actual_request_cooldown_minutes=60; maximum_provider_attempts_per_run=120
    maximum_provider_attempts_per_ist_day=360; maximum_fixed_cohort=50
    catch_up_calendar_day_bound=31; oldest_first_sessions_per_run=1
    run_level='LeastPrivilege'; logon_type='InteractiveToken'; multiple_instances='IgnoreNew'
    start_when_available=$true; execution_time_limit='PT30M'; credentials_embedded=$false
    config_sha256=(Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()
    xml_sha256=(Get-FileHash -LiteralPath $xmlPath -Algorithm SHA256).Hash.ToLowerInvariant()
    requires='Exact operator cadence/cohort/quota approval plus genuine source/clock/calendar/publication/retained-replay qualification'
    publication_time_guaranteed=$false; reliance_task_modified=$false
}
[System.IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 4), $encoding)
$receipt | ConvertTo-Json -Depth 4
