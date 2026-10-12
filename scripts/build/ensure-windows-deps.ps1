# Dot-source before building. Sets $mavenCommand, $pythonCommand, and $pythonArguments.

function Install-WinGetPackage([string]$PackageId) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "WinGet is required to install $PackageId. Install App Installer from Microsoft, then retry."
    }
    Write-Host "Installing $PackageId through WinGet..."
    & winget install --id $PackageId --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw "WinGet could not install $PackageId (exit code $LASTEXITCODE)." }
}

function Find-Jdk21 {
    $homes = @($env:JAVA_HOME)
    foreach ($pattern in @(
        "$env:ProgramFiles\Microsoft\jdk-21*",
        "$env:ProgramFiles\Eclipse Adoptium\jdk-21*",
        "$env:ProgramFiles\Java\jdk-21*"
    )) {
        $homes += @(Get-Item -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    }
    $jlink = Get-Command jlink.exe -ErrorAction SilentlyContinue
    if ($jlink) { $homes += (Split-Path (Split-Path $jlink.Source -Parent) -Parent) }
    foreach ($home in $homes) {
        if (-not $home) { continue }
        $candidate = Join-Path $home 'bin\jlink.exe'
        if (-not (Test-Path $candidate)) { continue }
        $version = & $candidate --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $version -match '^21([.]|$)') { return $home }
    }
    return $null
}

function Test-Python([string]$Command, [string[]]$Arguments) {
    try {
        & $Command @Arguments -c 'import sys, venv, ensurepip; assert (3, 11) <= sys.version_info[:2] <= (3, 14)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    if ($env:PYTHON_BIN) {
        if (-not (Test-Python $env:PYTHON_BIN @())) {
            throw 'PYTHON_BIN must point to Python 3.11–3.14 with venv and pip.'
        }
        return @{ Command = $env:PYTHON_BIN; Arguments = @() }
    }
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        foreach ($version in @('3.14', '3.13', '3.12', '3.11')) {
            if (Test-Python 'py.exe' @("-$version")) {
                return @{ Command = 'py.exe'; Arguments = @("-$version") }
            }
        }
    }
    foreach ($command in @('python3.14.exe', 'python3.13.exe', 'python3.12.exe', 'python3.11.exe', 'python.exe')) {
        if ((Get-Command $command -ErrorAction SilentlyContinue) -and (Test-Python $command @())) {
            return @{ Command = $command; Arguments = @() }
        }
    }
    foreach ($candidate in @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:ProgramFiles\Python313\python.exe"
    )) {
        if ((Test-Path $candidate) -and (Test-Python $candidate @())) {
            return @{ Command = $candidate; Arguments = @() }
        }
    }
    return $null
}

$jdkHome = Find-Jdk21
if (-not $jdkHome) {
    Install-WinGetPackage 'Microsoft.OpenJDK.21'
    $jdkHome = Find-Jdk21
    if (-not $jdkHome) { throw 'JDK 21 with jlink was installed but could not be found. Open a new terminal and retry.' }
}
$env:JAVA_HOME = $jdkHome
$env:PATH = "$(Join-Path $jdkHome 'bin');$env:PATH"

$python = Find-Python
if (-not $python) {
    Install-WinGetPackage 'Python.Python.3.13'
    $python = Find-Python
    if (-not $python) { throw 'Python 3.13 was installed but could not be found. Open a new terminal and retry.' }
}
$pythonCommand = $python.Command
$pythonArguments = $python.Arguments

$maven = Get-Command mvn.cmd -ErrorAction SilentlyContinue
if ($maven) {
    $mavenCommand = $maven.Source
} else {
    $mavenVersion = '3.9.16'
    $mavenSha512 = 'ed41650d42485cfc243fad22158caf9cbb5dc408ce7a09ddb94dd42a019de929ca43065bfa450612cf12bf78b5cafa3884b96c090de326ff590448c933454af3'
    $toolsDir = Join-Path $projectRoot 'build\tools'
    $mavenHome = Join-Path $toolsDir "apache-maven-$mavenVersion"
    $mavenCommand = Join-Path $mavenHome 'bin\mvn.cmd'
    if (-not (Test-Path $mavenCommand)) {
        New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
        $archive = Join-Path $toolsDir "apache-maven-$mavenVersion-bin.zip"
        $url = "https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/$mavenVersion/apache-maven-$mavenVersion-bin.zip"
        Write-Host "Downloading Apache Maven $mavenVersion..."
        Invoke-WebRequest -Uri $url -OutFile $archive
        $actualHash = (Get-FileHash -Path $archive -Algorithm SHA512).Hash
        if ($actualHash -ne $mavenSha512) {
            Remove-Item $archive -Force
            throw 'Apache Maven download failed SHA-512 verification.'
        }
        Expand-Archive -Path $archive -DestinationPath $toolsDir -Force
        Remove-Item $archive -Force
    }
    if (-not (Test-Path $mavenCommand)) { throw 'Apache Maven could not be installed.' }
}
