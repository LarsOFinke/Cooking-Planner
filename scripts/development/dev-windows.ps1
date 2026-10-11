$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $projectRoot

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
        if ($env:PYTHON_BIN) {
            & $env:PYTHON_BIN -m venv .venv-dev-windows
            Assert-Success 'Python virtual environment'
        } else {
            $created = $false
            foreach ($version in @('3.14', '3.13', '3.12', '3.11')) {
                & py "-$version" -m venv .venv-dev-windows 2>$null
                if ($LASTEXITCODE -eq 0) { $created = $true; break }
            }
            if (-not $created) { throw 'Python 3.11–3.14 is required. Set PYTHON_BIN or DEV_PYTHON.' }
        }
    }
}

& $python -c 'import kivy, sys; assert (sys.version_info[:2] < (3, 14) and kivy.__version__ == "2.3.1") or (sys.version_info[:2] == (3, 14) and kivy.__version__.startswith("3."))' *> $null
if ($LASTEXITCODE -ne 0) {
    if (-not $managedVenv) { throw 'DEV_PYTHON must point to Python with a compatible Kivy version installed.' }
    & $python scripts/development/install-desktop-deps.py
    Assert-Success 'Kivy installation'
}

$mavenArgs = @('-f', 'backend/pom.xml', '-DskipTests', 'package')
if ($env:MAVEN_REPO) { $mavenArgs += "-Dmaven.repo.local=$env:MAVEN_REPO" }
& mvn @mavenArgs
Assert-Success 'Backend build'
& $python desktop/main.py
Assert-Success 'Desktop app'
