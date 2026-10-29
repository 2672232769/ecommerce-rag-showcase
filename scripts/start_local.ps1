param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$entryPath = Join-Path $projectRoot 'scripts\serve_local.py'
$runtimePath = Join-Path $projectRoot '.runtime'
$siteUrl = 'http://127.0.0.1:8018'
function Get-LocalHealth {
    # Ignore machine HTTP proxy only for this loopback health check.
    $webClient = New-Object Net.WebClient
    $webClient.Proxy = $null
    try { return ($webClient.DownloadString("$siteUrl/api/health") | ConvertFrom-Json) }
    finally { $webClient.Dispose() }
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run setup_local.bat first: missing virtual environment.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Run setup_local.bat first: missing frontend build.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'backend\.env'))) { throw 'Copy backend/.env.example to backend/.env and configure it first.' }
$health = $null
try { $health = Get-LocalHealth } catch {}
if ($health -and $health.service -eq 'ecommerce-rag-showcase') {
    Write-Host "Already running: $siteUrl"
} else {
    $occupied = Get-NetTCPConnection -LocalPort 8018 -State Listen -ErrorAction SilentlyContinue
    if ($occupied) { throw 'Port 8018 is occupied by another service. No processes were stopped.' }
    New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $runtimePath "$stamp-stdout.log"
    $stderr = Join-Path $runtimePath "$stamp-stderr.log"
    Start-Process -FilePath $pythonPath -ArgumentList ('"' + $entryPath + '"') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        try { $health = Get-LocalHealth; break } catch {}
    }
    if (-not $health -or $health.service -ne 'ecommerce-rag-showcase') { throw "Startup not ready. Check $stderr" }
    Write-Host "Started: $siteUrl"
}
Write-Host 'Sign in with ADMIN_USERNAME and the password you set during configuration.'
Write-Host "Model configured: chat=$($health.llm_configured), embedding=$($health.embedding_configured)"
Write-Host 'Stop with stop_local.bat. Documents and conversations are retained.'
if (-not $NoBrowser) { Start-Process $siteUrl }
