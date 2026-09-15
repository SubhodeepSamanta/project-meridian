$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $projectRoot "apps\api"
$venvRoot = Join-Path $backendRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$requirements = Join-Path $backendRoot "requirements.txt"

Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pythonLauncher) {
        & $pythonLauncher.Source "-3.12" "-m" "venv" $venvRoot
    } else {
        & python "-m" "venv" $venvRoot
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the backend virtual environment."
    }
}

& $venvPython "-m" "pip" "install" "--disable-pip-version-check" "-r" $requirements
if ($LASTEXITCODE -ne 0) {
    throw "Could not install backend dependencies into the virtual environment."
}

Write-Output "Backend virtual environment ready: $venvRoot"
Write-Output "Python: $venvPython"
