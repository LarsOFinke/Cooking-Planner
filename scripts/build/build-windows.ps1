$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $projectRoot

function Assert-Success([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}

. (Join-Path $PSScriptRoot 'ensure-windows-deps.ps1')
& $mavenCommand -f backend/pom.xml package
Assert-Success 'Maven package'
New-Item -ItemType Directory -Path build -Force | Out-Null
Copy-Item 'backend/target/cooking-planner-api-0.1.0.jar' 'build/backend.jar' -Force

& $pythonCommand @pythonArguments -m venv .build-venv
Assert-Success 'Python virtual environment'
$python = Join-Path $projectRoot '.build-venv\Scripts\python.exe'
& $python -m pip install -r desktop/requirements-build.txt
Assert-Success 'Build dependencies'
& $python scripts/development/install-desktop-deps.py
Assert-Success 'Kivy installation'
& $python -m build --wheel --no-isolation --outdir dist/wheels .
Assert-Success 'Wheel build'

$wheel = Get-ChildItem 'dist/wheels/cooking_planner_desktop-0.1.0-*.whl' | Select-Object -First 1
if (-not $wheel) { throw 'Cooking Planner wheel not found' }
& $python -m pip install --no-deps --force-reinstall $wheel.FullName
Assert-Success 'Wheel installation'

$runtimeDir = 'build/runtime-windows'
if (Test-Path $runtimeDir) { Remove-Item $runtimeDir -Recurse -Force }
& jlink --add-modules ALL-MODULE-PATH --strip-debug --no-header-files --no-man-pages --output $runtimeDir
Assert-Success 'Java runtime build'

New-Item -ItemType Directory -Path dist/windows -Force | Out-Null
& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name CookingPlanner --distpath dist/windows --workpath build/pyinstaller-windows --specpath build `
    --add-binary 'build/runtime-windows:runtime' `
    --add-data 'build/backend.jar:.' `
    --add-data 'data:catalogs' `
    scripts/build/frozen_entry.py
Assert-Success 'Windows executable build'
Write-Host 'Built dist/windows/CookingPlanner.exe'
