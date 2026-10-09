param(
    [Parameter(Mandatory = $true)][string]$NodeExecutable,
    [string]$StorageRoot = 'D:\al-research\p18-runtime'
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$storagePath = [IO.Path]::GetFullPath($StorageRoot)
$dependencyPath = Join-Path $storagePath 'node_modules'
$nodePath = (Resolve-Path -LiteralPath $NodeExecutable).Path
$npmScript = Join-Path (Split-Path -Parent $nodePath) 'node_modules\npm\bin\npm-cli.js'
$versionText = & $nodePath --version
if ($LASTEXITCODE -ne 0 -or [version]$versionText.TrimStart('v') -lt [version]'22.23.3' -or [version]$versionText.TrimStart('v') -ge [version]'23.0.0') {
    throw 'Use a compatible Node 22 LTS executable (22.23.3 or later).'
}
if ($storagePath -eq [IO.Path]::GetPathRoot($storagePath) -or $storagePath -eq $projectRoot) {
    throw 'Choose a dedicated tool-storage directory, never a drive root or source directory.'
}
$linkPath = Join-Path $projectRoot 'node_modules'
if (Test-Path -LiteralPath $linkPath) {
    $existing = Get-Item -LiteralPath $linkPath
    if ($existing.LinkType -ne 'Junction' -or [IO.Path]::GetFullPath($existing.Target[0]) -ne $dependencyPath) {
        throw 'Existing node_modules has a different owner or target; preserve it and choose the existing storage location.'
    }
}
New-Item -ItemType Directory -Force -Path $storagePath, (Join-Path $storagePath 'temp') | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'package.json') -Destination (Join-Path $storagePath 'package.json')
Copy-Item -LiteralPath (Join-Path $projectRoot 'package-lock.json') -Destination (Join-Path $storagePath 'package-lock.json')
$env:Path = (Split-Path -Parent $nodePath) + ';' + $env:Path
$env:npm_config_cache = Join-Path $storagePath 'npm-cache'
$env:TEMP = Join-Path $storagePath 'temp'
$env:TMP = $env:TEMP
Push-Location -LiteralPath $storagePath
try {
    & $nodePath $npmScript ci --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Frozen frontend dependency installation failed.' }
} finally { Pop-Location }
if (-not (Test-Path -LiteralPath $linkPath)) {
    New-Item -ItemType Junction -Path $linkPath -Target $dependencyPath | Out-Null
}
Write-Output 'Frontend dependencies installed from the frozen lockfile on the selected storage drive.'
