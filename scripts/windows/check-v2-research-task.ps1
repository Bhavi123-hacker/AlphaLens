param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference = 'Stop'
$configPath = (Resolve-Path -LiteralPath $Config).Path
$workerOutput = & (Join-Path $PSScriptRoot 'run-v2-research.cmd') $configPath '--dry-run'
$dryRunExit = $LASTEXITCODE
$jsonLine = $workerOutput | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1
if (-not $jsonLine) { throw 'V2 worker did not return a structured readiness receipt' }
$workflow = $jsonLine | ConvertFrom-Json
if ($dryRunExit -eq 0 -and $workflow.source_requests_last_run -ne 0) {
    throw 'Dry-run unexpectedly attempted provider requests'
}
$reliance = Get-ScheduledTask -TaskName 'AlphaLens-Private-EOD-Watchlist' -ErrorAction SilentlyContinue
$v2 = Get-ScheduledTask -TaskName 'AlphaLens-Private-V2-Research' -ErrorAction SilentlyContinue
[ordered]@{
    dry_run_exit=$dryRunExit; task_registration_performed=$false; provider_requests_requested=$false
    workflow_state=[string]$workflow.state; run_id=[string]$workflow.run_id
    source_requests_last_run=$workflow.source_requests_last_run
    clock_state=[string]$workflow.clock.state
    latest_observation_date=[string]$workflow.latest_observation_date
    source_session_coverage=$workflow.source_session_coverage; eligible_vectors=$workflow.eligible_vectors
    prospective_forecasts=$workflow.prospective.forecasts; matured_outcomes=$workflow.prospective.outcomes
    reliance_task_exists=($null -ne $reliance); reliance_enabled=($null -ne $reliance -and $reliance.Settings.Enabled)
    v2_task_exists=($null -ne $v2); v2_enabled=($null -ne $v2 -and $v2.Settings.Enabled)
    machine_requirement='Same operator logged in; Windows running; original Windows Credential Manager entry available'
    unrelated_tasks_modified=$false
} | ConvertTo-Json
if ($dryRunExit -ne 0) { exit $dryRunExit }
