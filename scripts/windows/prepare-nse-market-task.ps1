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
    throw 'Task proposal artifacts must remain inside this checkout private .local-data directory'
}
$ancestor = $output
while ($ancestor.Length -ge $allowed.Length) {
    if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw 'Task artifact reparse points are forbidden'
    }
    if ($ancestor -eq $allowed) { break }
    $ancestor = Split-Path -Parent $ancestor
}
if (Test-Path -LiteralPath $output) { throw 'Task proposal output must be a new private directory' }
$json = & (Join-Path $PSScriptRoot 'project-python.cmd') -c 'import json,sys; from pathlib import Path; from workers.nse_market.operational import configured,policy,readiness; c=configured(Path(sys.argv[1])); print(json.dumps(dict(policy=policy(c),readiness=readiness(c),enabled=c.recurring_acquisition_enabled)))' $configPath
if ($LASTEXITCODE -ne 0) { throw 'Protected cohort/configuration validation failed' }
$checked = $json | ConvertFrom-Json
if ($checked.enabled) { throw 'Preparation requires recurring acquisition disabled' }
if (-not $checked.readiness.running_user_matches -or -not $checked.readiness.protected_credential_available) {
    throw 'Current operator or protected credential readiness failed'
}
New-Item -ItemType Directory -Path $output | Out-Null
& (Join-Path $PSScriptRoot 'project-python.cmd') -c 'import sys; from pathlib import Path; from alphalens_api.auth.permissions import restrict,verify; p=Path(sys.argv[1]); restrict(p); verify(p)' $output
if ($LASTEXITCODE -ne 0) { throw 'Private output permissions could not be verified' }
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$escape = { param([string]$Value) [System.Security.SecurityElement]::Escape($Value) }
$command = & $escape (Join-Path $env:WINDIR 'System32/cmd.exe')
$wrapper = Join-Path $PSScriptRoot 'run-nse-market.cmd'
$arguments = & $escape ('/d /c ""' + $wrapper + '" "' + $configPath + '" auto --scheduled"')
$working = & $escape $repo
$principal = & $escape $sid
$tomorrow = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([datetime]::UtcNow, 'India Standard Time').Date.AddDays(1).ToString('yyyy-MM-dd')
$triggers = foreach ($slot in $checked.policy.cadence_ist) {
    '<CalendarTrigger><StartBoundary>' + $tomorrow + 'T' + $slot + ':00+05:30</StartBoundary><Enabled>false</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>'
}
$xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
<RegistrationInfo><Description>PROPOSAL ONLY: bounded private AlphaLens NSE research; exact scope/cadence/quota approval required; no orders</Description></RegistrationInfo>
<Triggers>$($triggers -join '')</Triggers>
<Principals><Principal id="LocalOperator"><UserId>$principal</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT30M</ExecutionTimeLimit><Enabled>false</Enabled></Settings>
<Actions Context="LocalOperator"><Exec><Command>$command</Command><Arguments>$arguments</Arguments><WorkingDirectory>$working</WorkingDirectory></Exec></Actions>
</Task>
"@
[xml]$parsed = $xml
$encoding = New-Object System.Text.UTF8Encoding($false)
$xmlPath = Join-Path $output 'nse-market-task-disabled.xml'
[System.IO.File]::WriteAllText($xmlPath, $xml, $encoding)
$receipt = [ordered]@{
    task_name='AlphaLens-Private-NSE-Market-Research'; registered=$false; enabled=$false
    cadence_ist=$checked.policy.cadence_ist; maximum_attempts_per_ist_day=$checked.policy.max_runs_per_day
    minimum_actual_cooldown_minutes=$checked.policy.cooldown_minutes
    maximum_provider_attempts_per_run=$checked.policy.max_requests_per_run
    maximum_provider_attempts_per_day=$checked.policy.max_requests_per_day
    fixed_scope=$checked.policy.expected_securities; maximum_stocks_per_run=$checked.policy.max_stocks_per_run
    policy_sha256=$checked.policy.policy_sha256; start_when_available=$true
    run_level='LeastPrivilege'; logon_type='InteractiveToken'; multiple_instances='IgnoreNew'
    execution_time_limit='PT30M'; credentials_embedded=$false; publication_time_guaranteed=$false
    original_reliance_task_modified=$false; registration_performed=$false
    config_sha256=(Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()
    xml_sha256=(Get-FileHash -LiteralPath $xmlPath -Algorithm SHA256).Hash.ToLowerInvariant()
    requires='Explicit user approval of this exact policy, then independent clock/source/session/publication qualification at each collecting run'
}
[System.IO.File]::WriteAllText((Join-Path $output 'nse-market-task-proposal.json'), ($receipt | ConvertTo-Json -Depth 5), $encoding)
$receipt | ConvertTo-Json -Depth 5
