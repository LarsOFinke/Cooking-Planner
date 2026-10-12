$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path

& (Join-Path $projectRoot 'scripts/build/build-windows.ps1')
if ($LASTEXITCODE -ne 0) { throw "Windows build failed with exit code $LASTEXITCODE" }

$installDir = Join-Path $env:LOCALAPPDATA 'Programs\CookingPlanner'
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
$command = Join-Path $installDir 'cooking-planner.exe'
Copy-Item (Join-Path $projectRoot 'dist/windows/CookingPlanner.exe') $command -Force

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = @($userPath -split ';' | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\') })
if ($entries -notcontains $installDir.TrimEnd('\')) {
    $newPath = (@($userPath, $installDir) | Where-Object { $_ }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:PATH = "$env:PATH;$installDir"
    Write-Host 'Added the install directory to your user PATH. Open a new terminal to use cooking-planner.'
}
Write-Host "Installed $command"
