# Dot-source before building. Sets $pythonCommand and $pythonArguments.

function Install-WinGetPackage([string]$PackageId) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "WinGet is required to install $PackageId. Install App Installer from Microsoft, then retry."
    }
    & winget install --id $PackageId --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw "WinGet could not install $PackageId." }
}

function Test-Python([string]$Command, [string[]]$Arguments) {
    try {
        & $Command @Arguments -c 'import sys, venv, ensurepip; assert (3, 11) <= sys.version_info[:2] <= (3, 14)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python {
    if ($env:PYTHON_BIN) {
        if (-not (Test-Python $env:PYTHON_BIN @())) { throw 'PYTHON_BIN must be Python 3.11–3.14 with venv.' }
        return @{ Command = $env:PYTHON_BIN; Arguments = @() }
    }
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        foreach ($version in @('3.13', '3.12', '3.11', '3.14')) {
            if (Test-Python 'py.exe' @("-$version")) {
                return @{ Command = 'py.exe'; Arguments = @("-$version") }
            }
        }
    }
    foreach ($command in @('python3.13.exe', 'python3.12.exe', 'python3.11.exe', 'python3.14.exe', 'python.exe')) {
        if ((Get-Command $command -ErrorAction SilentlyContinue) -and (Test-Python $command @())) {
            return @{ Command = $command; Arguments = @() }
        }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Install-WinGetPackage 'Python.Python.3.13'
    $python = Find-Python
    if (-not $python) { throw 'Python was installed but could not be found. Open a new terminal and retry.' }
}
$pythonCommand = $python.Command
$pythonArguments = $python.Arguments
