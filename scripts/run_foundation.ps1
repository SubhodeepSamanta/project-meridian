$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $projectRoot "infrastructure\step-ca\runtime"
$artifactDirectory = Join-Path $runtimeDirectory "artifacts"
$caConfigPath = Join-Path $runtimeDirectory "config\ca.json"
$bootstrapPasswordPath = Join-Path $runtimeDirectory ".bootstrap-password"
$caPasswordPath = Join-Path $runtimeDirectory "secrets\password"

Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path $artifactDirectory | Out-Null

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

& docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but its engine is unavailable. Start Docker Desktop and run this script again."
}

$initializationRequired = -not (Test-Path -LiteralPath $caConfigPath)
if ($initializationRequired) {
    $randomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $passwordBytes = New-Object byte[] 32
        $randomGenerator.GetBytes($passwordBytes)
        $initializationPassword = [Convert]::ToBase64String($passwordBytes)
    }
    finally {
        $randomGenerator.Dispose()
    }

    Set-Content -LiteralPath $bootstrapPasswordPath -Value $initializationPassword -NoNewline
    try {
        Invoke-RequiredCommand docker @(
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "step",
            "step-ca",
            "ca",
            "init",
            "--name",
            "Project Meridian Local CA",
            "--dns",
            "localhost",
            "--dns",
            "step-ca",
            "--address",
            ":9000",
            "--provisioner",
            "meridian-admin",
            "--deployment-type",
            "standalone",
            "--with-ca-url",
            "https://localhost:9000",
            "--password-file",
            "/home/step/.bootstrap-password",
            "--provisioner-password-file",
            "/home/step/.bootstrap-password"
        )

        if (-not (Test-Path -LiteralPath $caPasswordPath)) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $caPasswordPath) | Out-Null
            Copy-Item -LiteralPath $bootstrapPasswordPath -Destination $caPasswordPath -Force
        }
    }
    finally {
        if (Test-Path -LiteralPath $bootstrapPasswordPath) {
            Remove-Item -LiteralPath $bootstrapPasswordPath -Force
        }
    }
}

Invoke-RequiredCommand docker @("compose", "up", "-d", "step-ca")

$containerId = ((& docker compose ps -q step-ca) | Select-Object -First 1)
if ([string]::IsNullOrWhiteSpace($containerId)) {
    throw "Docker Compose did not create the step-ca container."
}
$containerId = $containerId.Trim()

$healthy = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    $health = ((& docker inspect --format "{{.State.Health.Status}}" $containerId 2>$null) | Select-Object -First 1)
    if ($null -ne $health) {
        $health = $health.Trim()
    }

    if ($health -eq "healthy") {
        $healthy = $true
        break
    }

    if ($health -eq "unhealthy") {
        & docker compose logs --no-color step-ca
        throw "step-ca reported an unhealthy status."
    }

    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    & docker compose logs --no-color step-ca
    throw "Timed out waiting for step-ca to become healthy."
}

$certificateContainerPath = "/home/step/artifacts/meridian-test.crt"
$keyContainerPath = "/home/step/artifacts/meridian-test.key"

Invoke-RequiredCommand docker @(
    "compose",
    "run",
    "--rm",
    "--no-deps",
    "step-ca",
    "step",
    "ca",
    "certificate",
    "meridian-test",
    $certificateContainerPath,
    $keyContainerPath,
    "--ca-url",
    "https://step-ca:9000",
    "--root",
    "/home/step/certs/root_ca.crt",
    "--provisioner",
    "meridian-admin",
    "--provisioner-password-file",
    "/home/step/secrets/password",
    "--password-file",
    "/home/step/secrets/password",
    "--san",
    "meridian-test",
    "--not-after",
    "24h",
    "--force"
)

$certificatePath = Join-Path $artifactDirectory "meridian-test.crt"
$keyPath = Join-Path $artifactDirectory "meridian-test.key"
if (-not (Test-Path -LiteralPath $certificatePath) -or -not (Test-Path -LiteralPath $keyPath)) {
    throw "The certificate command completed without creating the expected local artifacts."
}

$openSslCheck = @"
set -eu
apk add --no-cache openssl >/dev/null
openssl x509 -in /workspace/artifacts/meridian-test.crt -noout -subject -issuer -serial -dates -fingerprint -sha256 -ext subjectAltName
openssl verify -CAfile /workspace/certs/root_ca.crt -untrusted /workspace/certs/intermediate_ca.crt /workspace/artifacts/meridian-test.crt
"@

Invoke-RequiredCommand docker @(
    "run",
    "--rm",
    "-v",
    "$runtimeDirectory`:/workspace:ro",
    "alpine:3.22",
    "sh",
    "-c",
    $openSslCheck
)

Write-Output "Foundation milestone passed."
Write-Output "Certificate: $certificatePath"
Write-Output "Private key: generated locally and excluded from Git."
