$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$manifestPath = Join-Path $projectRoot '.runtime\service.json'
$entryPath = Join-Path $projectRoot 'scripts\serve_local.py'
if (-not (Test-Path -LiteralPath $manifestPath)) { Write-Host 'No recorded local service.'; exit 0 }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($manifest.pid)" -ErrorAction SilentlyContinue
if (-not $processInfo) { Write-Host 'Already stopped. Data retained.'; exit 0 }
if ($manifest.entrypoint -ne $entryPath -or -not $processInfo.CommandLine -or $processInfo.CommandLine.IndexOf($entryPath, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
    throw 'Recorded PID does not belong to this project. Nothing was stopped.'
}
Stop-Process -Id $manifest.pid -ErrorAction Stop
Write-Host 'Local service stopped. Documents, vector database, accounts, and conversations retained.'
