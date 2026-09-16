$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot

function Invoke-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

Invoke-RequiredCommand docker @("compose", "config", "--quiet")
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_backend_tests.ps1"))
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_foundation.ps1"))
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_mtls.ps1"))
Invoke-RequiredCommand docker @("compose", "build", "meridian-api")
Invoke-RequiredCommand docker @("compose", "run", "--rm", "--no-deps", "meridian-api", "pytest", "-q")
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_policy.ps1"))
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_hsm.ps1"))
Invoke-RequiredCommand pwsh @("-NoProfile", "-File", (Join-Path $projectRoot "scripts\run_incident.ps1"))

Push-Location (Join-Path $projectRoot "apps\web")
try {
    Invoke-RequiredCommand npm @("run", "build")
} finally {
    Pop-Location
}

Invoke-RequiredCommand docker @("compose", "up", "-d", "meridian-api", "meridian-web")
$webHealthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:5173/api/health" -Method Get
        if ($health.status -eq "healthy") {
            $webHealthy = $true
            break
        }
    } catch {
        # Vite can still be installing dependencies or opening its port.
    }
    Start-Sleep -Seconds 1
}
if (-not $webHealthy) {
    docker compose logs --no-color meridian-web
    throw "The dashboard proxy did not report a healthy API."
}

Write-Output "FULL_STACK_CHECKS: PASS"
