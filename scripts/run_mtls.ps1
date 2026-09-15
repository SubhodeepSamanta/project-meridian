$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $projectRoot "infrastructure\step-ca\runtime"
$serviceArtifactDirectory = Join-Path $runtimeDirectory "artifacts\services"

Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path $serviceArtifactDirectory | Out-Null

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

Invoke-RequiredCommand pwsh @(
    "-NoProfile",
    "-File",
    (Join-Path $projectRoot "scripts\run_foundation.ps1")
)

function Issue-ServiceCertificate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    Invoke-RequiredCommand docker @(
        "compose",
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "step",
        "step-ca",
        "ca",
        "certificate",
        $ServiceName,
        "/home/step/artifacts/services/$ServiceName.crt",
        "/home/step/artifacts/services/$ServiceName.key",
        "--ca-url",
        "https://step-ca:9000",
        "--root",
        "/home/step/certs/root_ca.crt",
        "--provisioner",
        "meridian-admin",
        "--provisioner-password-file",
        "/home/step/secrets/password",
        "--san",
        $ServiceName,
        "--not-after",
        "24h",
        "--force"
    )
}

Issue-ServiceCertificate -ServiceName "service-a"
Issue-ServiceCertificate -ServiceName "service-b"

Invoke-RequiredCommand docker @("compose", "up", "-d", "service-a", "service-b")

foreach ($serviceName in @("service-a", "service-b")) {
    $containerId = ((& docker compose ps -q $serviceName) | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($containerId)) {
        throw "Docker Compose did not create $serviceName."
    }

    $containerId = $containerId.Trim()
    $running = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $state = ((& docker inspect --format "{{.State.Status}}" $containerId 2>$null) | Select-Object -First 1)
        if ($null -ne $state) {
            $state = $state.Trim()
        }
        if ($state -eq "running") {
            $running = $true
            break
        }
        if ($state -eq "exited" -or $state -eq "dead") {
            & docker compose logs --no-color $serviceName
            throw "$serviceName stopped before the mTLS check."
        }
        Start-Sleep -Seconds 1
    }

    if (-not $running) {
        & docker compose logs --no-color $serviceName
        throw "Timed out waiting for $serviceName to run."
    }
}

$validMtlscode = @"
import json
import ssl
import urllib.request

context = ssl.create_default_context(cafile="/certs/ca/root_ca.crt")
context.load_cert_chain("/certs/services/service-a.crt", "/certs/services/service-a.key")
with urllib.request.urlopen("https://service-b:9444/health", context=context, timeout=5) as response:
    payload = json.loads(response.read())
assert response.status == 200
assert payload["service"] == "service-b"
print("VALID_MTLS: PASS")
"@

Invoke-RequiredCommand docker @(
    "compose",
    "exec",
    "-T",
    "service-a",
    "python",
    "-c",
    $validMtlscode
)

$invalidMtlscode = @"
import socket
import ssl

context = ssl.create_default_context(cafile="/certs/ca/root_ca.crt")
try:
    with socket.create_connection(("service-b", 9444), timeout=5) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname="service-b"):
            raw_socket.sendall(b"GET /health HTTP/1.1\r\nHost: service-b\r\nConnection: close\r\n\r\n")
            if raw_socket.recv(1):
                raise SystemExit("UNEXPECTED_MTLS_SUCCESS")
            print("INVALID_MTLS: EXPECTED_FAILURE")
except (ConnectionError, OSError, ssl.SSLError):
    print("INVALID_MTLS: EXPECTED_FAILURE")
"@

$invalidOutput = & docker compose run --rm --no-deps --entrypoint python service-a -c $invalidMtlscode 2>&1
if ($LASTEXITCODE -ne 0) {
    $invalidOutput
    throw "The expected no-client-certificate test produced an unexpected command failure."
}
$invalidOutput

Write-Output "mTLS milestone passed."
