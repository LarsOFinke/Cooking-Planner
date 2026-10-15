$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Set-Location $projectRoot
. (Join-Path $PSScriptRoot 'ensure-windows-deps.ps1')

function Invoke-BuildStep([int]$Step, [string]$Name, [string]$Log, [string[]]$Command) {
    & $pythonCommand @pythonArguments scripts/build/common/progress.py --step $Step --total 7 `
        --name $Name --log $Log -- @Command
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

$pythonTag = (& $pythonCommand @pythonArguments -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').Trim()
$buildVenv = Join-Path $projectRoot ".build-venv-$pythonTag"
$python = Join-Path $buildVenv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    Invoke-BuildStep -Step 1 -Name 'Create build environment' -Log 'build/logs/windows-venv.log' `
        -Command (@($pythonCommand) + $pythonArguments + @('-m', 'venv', $buildVenv))
} else { Write-Host '[1/7] Build environment reused' }
Invoke-BuildStep -Step 2 -Name 'Install build tools' -Log 'build/logs/windows-tools.log' `
    -Command @($python, '-m', 'pip', 'install', '-r', 'src/requirements-build.txt')
Invoke-BuildStep -Step 3 -Name 'Install app dependencies' -Log 'build/logs/windows-desktop.log' `
    -Command @($python, 'scripts/development/install-python-deps.py')
& $python scripts/build/common/clean-wheel.py
if ($LASTEXITCODE -ne 0) { throw 'Wheel build cleanup failed' }
Invoke-BuildStep -Step 4 -Name 'Build Python wheel' -Log 'build/logs/windows-wheel.log' `
    -Command @($python, '-m', 'build', '--wheel', '--no-isolation', '--outdir', 'dist/wheels', '.')
$wheel = Get-ChildItem 'dist/wheels/cooking_planner-0.1.0-*.whl' | Select-Object -First 1
if (-not $wheel) { throw 'Cooking Planner wheel not found' }
Invoke-BuildStep -Step 5 -Name 'Install app wheel' -Log 'build/logs/windows-wheel-install.log' `
    -Command @($python, '-m', 'pip', 'install', '--no-deps', '--force-reinstall', $wheel.FullName)
New-Item -ItemType Directory -Path dist/windows -Force | Out-Null
$catalogData = Join-Path $projectRoot 'data'
Invoke-BuildStep -Step 6 -Name 'Build bundled Windows executable' -Log 'build/logs/windows-executable.log' `
    -Command @($python, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', `
               '--name', 'CookingPlanner', '--distpath', 'dist/windows', `
               '--workpath', 'build/pyinstaller-windows', '--specpath', 'build', `
               '--collect-submodules', 'sqlalchemy.dialects.sqlite', `
               '--collect-submodules', 'uvicorn', '--add-data', "$catalogData;catalogs", `
               'scripts/build/common/frozen_entry.py')

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $iscc = Get-Item "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", `
                     "$env:ProgramFiles\Inno Setup 6\ISCC.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if (-not $iscc) {
    Install-WinGetPackage 'JRSoftware.InnoSetup'
    $iscc = Get-Item "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", `
                     "$env:ProgramFiles\Inno Setup 6\ISCC.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if (-not $iscc) { throw 'Inno Setup 6 compiler (ISCC.exe) is required.' }
Invoke-BuildStep -Step 7 -Name 'Build Windows installer' -Log 'build/logs/windows-installer.log' `
    -Command @($iscc.FullName, 'scripts/build/windows/cooking-planner.iss')
Write-Host 'Built dist/windows/CookingPlanner-Setup.exe'
