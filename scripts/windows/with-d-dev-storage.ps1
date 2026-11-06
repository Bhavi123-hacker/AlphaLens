# Opt-in development command only. Does not edit persistent environment or production launchers.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [string[]]$CommandArguments = @()
)
$ErrorActionPreference = 'Stop'
$storageRoot = 'D:\AlphaLensStorage'
if (-not (Test-Path -LiteralPath $storageRoot -PathType Container)) {
    throw 'Prepare and verify D:\AlphaLensStorage before using this development wrapper.'
}
$selectedRoot = Get-Item -LiteralPath $storageRoot
if (($selectedRoot.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Development storage root must not be a reparse point.'
}
$settings = [ordered]@{
    TEMP = "$storageRoot\Temp\Development"
    TMP = "$storageRoot\Temp\Development"
    PIP_CACHE_DIR = "$storageRoot\Caches\pip"
    # Existing cache is already on D:. Preserve its junction and reuse its contents.
    UV_CACHE_DIR = 'D:\alphalens-uv-cache'
    NPM_CONFIG_CACHE = "$storageRoot\Caches\npm"
    npm_package_config_node_gyp_devdir = "$storageRoot\Caches\node-gyp"
    MYPY_CACHE_DIR = "$storageRoot\Caches\mypy"
    RUFF_CACHE_DIR = "$storageRoot\Caches\ruff"
    MPLCONFIGDIR = "$storageRoot\Caches\matplotlib"
    TORCH_HOME = "$storageRoot\Caches\torch"
    PYTHONPYCACHEPREFIX = "$storageRoot\pyc"
    ALPHALENS_TEST_TEMP_ROOT = "$storageRoot\Tests"
    ALPHALENS_WEB_OUTPUT_DIR = "$storageRoot\Builds\WebDevelopment"
    ALPHALENS_WEB_CACHE_DIR = "$storageRoot\Caches\vite"
}
# Keep LOCALAPPDATA unchanged: GitHub CLI also stores its device identity there.
foreach ($destination in $settings.Values) {
    $item = Get-Item -LiteralPath $destination
    if (-not $item.PSIsContainer -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Development storage directory is missing or a reparse point.'
    }
}
$original = @{}
foreach ($name in $settings.Keys) {
    $original[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    foreach ($name in $settings.Keys) {
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $global:LASTEXITCODE = 0
    & $FilePath @CommandArguments
    $commandExitCode = $global:LASTEXITCODE
    if ($commandExitCode -ne 0) { throw "Development command exited with code $commandExitCode" }
}
finally {
    foreach ($name in $original.Keys) {
        [Environment]::SetEnvironmentVariable($name, $original[$name], 'Process')
    }
}
