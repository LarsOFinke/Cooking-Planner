$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $projectRoot

function Invoke-BuildStep([int]$Step, [string]$Name, [string]$Log, [string[]]$Command) {
    & $pythonCommand @pythonArguments scripts/build/progress.py --step $Step --total 8 `
        --name $Name --log $Log -- @Command
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

. (Join-Path $PSScriptRoot 'ensure-windows-deps.ps1')
Invoke-BuildStep -Step 1 -Name 'Build backend' -Log 'build/logs/windows-backend.log' `
    -Command @($mavenCommand, '-f', 'backend/pom.xml', 'package')
New-Item -ItemType Directory -Path build -Force | Out-Null
Copy-Item 'backend/target/cooking-planner-api-0.1.0.jar' 'build/backend.jar' -Force

$pythonTag = (& $pythonCommand @pythonArguments -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not determine the build Python version' }
$buildVenv = Join-Path $projectRoot ".build-venv-$pythonTag"
$python = Join-Path $buildVenv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    Invoke-BuildStep -Step 2 -Name 'Create build environment' -Log 'build/logs/windows-venv.log' `
        -Command (@($pythonCommand) + $pythonArguments + @('-m', 'venv', $buildVenv))
} else {
    Write-Host '[2/8] Build environment reused'
}
Invoke-BuildStep -Step 3 -Name 'Install build tools' -Log 'build/logs/windows-tools.log' `
    -Command @($python, '-m', 'pip', 'install', '-r', 'desktop/requirements-build.txt')
Invoke-BuildStep -Step 4 -Name 'Install desktop dependencies' -Log 'build/logs/windows-desktop.log' `
    -Command @($python, 'scripts/development/install-desktop-deps.py')
Invoke-BuildStep -Step 5 -Name 'Build Python wheel' -Log 'build/logs/windows-wheel.log' `
    -Command @($python, '-m', 'build', '--wheel', '--no-isolation', '--outdir', 'dist/wheels', '.')

$wheel = Get-ChildItem 'dist/wheels/cooking_planner_desktop-0.1.0-*.whl' | Select-Object -First 1
if (-not $wheel) { throw 'Cooking Planner wheel not found' }
Invoke-BuildStep -Step 6 -Name 'Install desktop wheel' -Log 'build/logs/windows-wheel-install.log' `
    -Command @($python, '-m', 'pip', 'install', '--no-deps', '--force-reinstall', $wheel.FullName)

$runtimeDir = 'build/runtime-windows'
if (Test-Path $runtimeDir) { Remove-Item $runtimeDir -Recurse -Force }
Invoke-BuildStep -Step 7 -Name 'Bundle Java runtime' -Log 'build/logs/windows-runtime.log' `
    -Command @('jlink', '--add-modules', 'ALL-MODULE-PATH', '--strip-debug', '--no-header-files', `
               '--no-man-pages', '--output', $runtimeDir)

New-Item -ItemType Directory -Path dist/windows -Force | Out-Null
Invoke-BuildStep -Step 8 -Name 'Build standalone Windows executable' `
    -Log 'build/logs/windows-executable.log' `
    -Command @($python, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', `
               '--name', 'CookingPlanner', '--distpath', 'dist/windows', `
               '--workpath', 'build/pyinstaller-windows', '--specpath', 'build', `
               '--add-binary', 'build/runtime-windows:runtime', `
               '--add-data', 'build/backend.jar:.', '--add-data', 'data:catalogs', `
               'scripts/build/frozen_entry.py')
Write-Host 'Built dist/windows/CookingPlanner.exe'
