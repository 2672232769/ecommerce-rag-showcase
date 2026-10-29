$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$env:UV_CACHE_DIR = Join-Path $projectRoot '.cache\uv'
if (-not (Test-Path -LiteralPath 'backend\.venv\Scripts\python.exe')) {
    uv venv --python 3.12 backend/.venv
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
uv pip sync --python backend/.venv/Scripts/python.exe backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
& npm.cmd ci --cache (Join-Path $projectRoot '.cache\npm') --no-fund
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
Write-Host 'Ready. Configure backend/.env, then run start_local.bat.'
