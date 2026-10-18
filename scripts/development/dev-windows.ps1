$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $projectRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $projectRoot 'build/python-cache'

function Assert-Success([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}

if ($env:DEV_PYTHON) {
    $python = $env:DEV_PYTHON
    $managedVenv = $false
} else {
    $managedVenv = $true
    $python = Join-Path $projectRoot '.venv-dev-windows\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        . (Join-Path $projectRoot 'scripts/build/windows/ensure-windows-deps.ps1')
        & $pythonCommand @pythonArguments -m venv .venv-dev-windows
        Assert-Success 'Python virtual environment'
    }
}

$checkArgs = @()
if ($managedVenv) { $checkArgs = @('--dev') }
& $python scripts/development/check-python-deps.py @checkArgs *> $null
if ($LASTEXITCODE -ne 0) {
    if (-not $managedVenv) { throw 'DEV_PYTHON must point to Python with a compatible Kivy version installed.' }
    & $python scripts/development/install-python-deps.py --dev
    Assert-Success 'Kivy installation'
}

$env:PYTHONPATH = "$(Join-Path $projectRoot 'src/frontend');$(Join-Path $projectRoot 'src/backend')"
& $python src/frontend/main.py
Assert-Success 'Desktop app'
