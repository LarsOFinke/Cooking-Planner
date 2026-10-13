$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path

& (Join-Path $projectRoot 'scripts/build/windows/build-windows.ps1')
if ($LASTEXITCODE -ne 0) { throw "Windows build failed with exit code $LASTEXITCODE" }

& (Join-Path $projectRoot 'dist/windows/CookingPlanner-Setup.exe')
if ($LASTEXITCODE -ne 0) { throw "Windows installer failed with exit code $LASTEXITCODE" }
