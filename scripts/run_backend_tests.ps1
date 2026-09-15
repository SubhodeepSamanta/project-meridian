$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $projectRoot "apps\api"
$venvPython = Join-Path $backendRoot ".venv\Scripts\python.exe"

Set-Location -LiteralPath $projectRoot
& pwsh -NoProfile -File (Join-Path $projectRoot "scripts\setup_backend_venv.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Backend virtual-environment setup failed."
}

& $venvPython "-m" "pytest" (Join-Path $backendRoot "tests") "-q"
if ($LASTEXITCODE -ne 0) {
    throw "Backend tests failed in the virtual environment."
}

Write-Output "BACKEND_VENV_TESTS: PASS"
