$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hsmRuntime = Join-Path $projectRoot "infrastructure\step-ca\hsm-runtime"
$hsmSecrets = Join-Path $hsmRuntime "secrets"
$hsmTokens = Join-Path $hsmRuntime "tokens"
$hsmUnavailableTokens = Join-Path $hsmRuntime "tokens.unavailable"
$hsmArtifacts = Join-Path $hsmRuntime "artifacts"
$configPath = Join-Path $hsmRuntime "config\ca.json"

Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path $hsmSecrets, $hsmTokens, $hsmArtifacts | Out-Null

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

function New-RandomSecret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Ensure-SecretFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        New-RandomSecret | Set-Content -LiteralPath $Path -NoNewline
    }
}

Invoke-RequiredCommand docker @("compose", "build", "hsm-ca")

$caPasswordPath = Join-Path $hsmSecrets "password"
$hsmPinPath = Join-Path $hsmSecrets "hsm-pin"
$hsmSoPinPath = Join-Path $hsmSecrets "hsm-so-pin"
Ensure-SecretFile -Path $caPasswordPath

$slotsOutput = & docker compose run --rm --no-deps --entrypoint softhsm2-util hsm-ca --show-slots 2>&1
if ($LASTEXITCODE -ne 0) {
    $slotsOutput
    throw "Could not inspect the SoftHSM token slots."
}

$tokenExists = [bool]($slotsOutput -match "Label:\s+meridian-hsm")
if (-not $tokenExists -and (Test-Path -LiteralPath $hsmPinPath -PathType Leaf)) {
    throw "A SoftHSM PIN file exists but the meridian-hsm token does not. Move the generated hsm-runtime aside before retrying."
}
if (-not $tokenExists) {
    Ensure-SecretFile -Path $hsmPinPath
    Ensure-SecretFile -Path $hsmSoPinPath
    $soPin = Get-Content -LiteralPath $hsmSoPinPath -Raw
    $userPin = Get-Content -LiteralPath $hsmPinPath -Raw
    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "softhsm2-util", "hsm-ca",
        "--init-token", "--slot", "0", "--label", "meridian-hsm", "--so-pin", $soPin.Trim(), "--pin", $userPin.Trim()
    )
}

$pkcs11Uri = "pkcs11:module-path=/usr/lib/softhsm/libsofthsm2.so;token=meridian-hsm?pin-source=/home/step/secrets/hsm-pin"
$rootKeyName = "pkcs11:id=7331;object=meridian-hsm-root"
$intermediateKeyName = "pkcs11:id=7332;object=meridian-hsm-intermediate"

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "step", "hsm-ca",
        "ca", "init", "--name", "Project Meridian HSM Simulation", "--dns", "localhost", "--dns", "hsm-ca",
        "--address", ":9000", "--provisioner", "meridian-hsm-admin", "--deployment-type", "standalone",
        "--password-file", "/home/step/secrets/password", "--provisioner-password-file", "/home/step/secrets/password"
    )

    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "step", "hsm-ca",
        "kms", "create", "--json", "--kms", $pkcs11Uri, $rootKeyName
    )
    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "step", "hsm-ca",
        "certificate", "create", "--profile", "root-ca", "--kms", $pkcs11Uri, "--key", $rootKeyName,
        "Project Meridian HSM Root CA", "/home/step/certs/root_ca.crt", "--force"
    )
    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "step", "hsm-ca",
        "kms", "create", "--json", "--kms", $pkcs11Uri, $intermediateKeyName
    )
    Invoke-RequiredCommand docker @(
        "compose", "run", "--rm", "--no-deps", "--entrypoint", "step", "hsm-ca",
        "certificate", "create", "--profile", "intermediate-ca", "--kms", $pkcs11Uri, "--ca-kms", $pkcs11Uri,
        "--ca", "/home/step/certs/root_ca.crt", "--ca-key", $rootKeyName, "--key", $intermediateKeyName,
        "Project Meridian HSM Intermediate CA", "/home/step/certs/intermediate_ca.crt", "--force"
    )

    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $config.key = $intermediateKeyName
    $config.root = "/home/step/certs/root_ca.crt"
    $config.crt = "/home/step/certs/intermediate_ca.crt"
    $config | Add-Member -NotePropertyName kms -NotePropertyValue ([pscustomobject]@{
        type = "pkcs11"
        uri = $pkcs11Uri
    }) -Force
    $config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configPath

    "configured" | Set-Content -LiteralPath (Join-Path $hsmRuntime ".configured") -NoNewline
}

$activeConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if ($activeConfig.key -eq $intermediateKeyName) {
    foreach ($diskKey in @(
        (Join-Path $hsmRuntime "secrets\root_ca_key"),
        (Join-Path $hsmRuntime "secrets\intermediate_ca_key")
    )) {
        if (Test-Path -LiteralPath $diskKey -PathType Leaf) {
            Remove-Item -LiteralPath $diskKey -Force
        }
    }
}

# Recreate the container after restoring the bind-mounted token directory. Docker
# Desktop can retain the old directory handle across a stop/start cycle; a fresh
# container makes the restored PKCS#11 token visible deterministically.
Invoke-RequiredCommand docker @("compose", "up", "-d", "--force-recreate", "hsm-ca")
$hsmContainerId = ((& docker compose ps -a -q hsm-ca) | Select-Object -First 1).Trim()
if ([string]::IsNullOrWhiteSpace($hsmContainerId)) {
    throw "Docker Compose did not create hsm-ca."
}

$healthy = $false
for ($attempt = 1; $attempt -le 40; $attempt++) {
    $state = ((& docker inspect --format "{{.State.Status}}" $hsmContainerId 2>$null) | Select-Object -First 1)
    if ($null -ne $state) {
        $state = $state.Trim()
    }
    if ($state -eq "exited" -or $state -eq "dead") {
        docker compose logs --no-color hsm-ca
        throw "The HSM-backed CA stopped before becoming healthy."
    }
    $health = ((& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}" $hsmContainerId 2>$null) | Select-Object -First 1)
    if ($health -and $health.Trim() -eq "healthy") {
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $healthy) {
    docker compose logs --no-color hsm-ca
    throw "Timed out waiting for the HSM-backed CA."
}

Invoke-RequiredCommand docker @(
    "compose", "exec", "-T", "hsm-ca", "step", "ca", "certificate", "hsm-test",
    "/home/step/artifacts/hsm-test.crt", "/home/step/artifacts/hsm-test.key",
    "--ca-url", "https://localhost:9000", "--root", "/home/step/certs/root_ca.crt",
    "--provisioner", "meridian-hsm-admin", "--provisioner-password-file", "/home/step/secrets/password",
    "--san", "hsm-test", "--not-after", "24h", "--force"
)

$objects = & docker compose exec -T hsm-ca sh -c 'pin=$(cat /home/step/secrets/hsm-pin); pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so --token-label meridian-hsm --login --pin "$pin" --list-objects' 2>&1
$objectText = $objects -join "`n"
if ($LASTEXITCODE -ne 0 -or $objectText -notmatch "meridian-hsm-root" -or $objectText -notmatch "meridian-hsm-intermediate") {
    $objects
    throw "The expected CA key objects were not found in the SoftHSM token."
}

$privateCaKeys = Get-ChildItem -LiteralPath $hsmRuntime -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @("root_ca_key", "intermediate_ca_key") }
if ($privateCaKeys) {
    throw "A CA private-key file exists on disk in the HSM simulation runtime."
}

$tokenUnavailableObserved = $false
if (Test-Path -LiteralPath $hsmUnavailableTokens) {
    throw "The previous token-unavailable test left an unexpected archive directory."
}
docker compose stop hsm-ca | Out-Host
Move-Item -LiteralPath $hsmTokens -Destination $hsmUnavailableTokens
New-Item -ItemType Directory -Path $hsmTokens | Out-Null
try {
    docker compose up -d hsm-ca | Out-Host
    Start-Sleep -Seconds 5
    $failedState = ((& docker inspect --format "{{.State.Status}}" $hsmContainerId 2>$null) | Select-Object -First 1)
    if ($failedState -and $failedState.Trim() -ne "running") {
        $tokenUnavailableObserved = $true
    }
} finally {
    docker compose stop hsm-ca | Out-Host
    Remove-Item -LiteralPath $hsmTokens -Force
    Move-Item -LiteralPath $hsmUnavailableTokens -Destination $hsmTokens
}
if (-not $tokenUnavailableObserved) {
    docker compose logs --no-color hsm-ca
    throw "The HSM-backed CA did not fail closed when the token directory was unavailable."
}

Invoke-RequiredCommand docker @("compose", "up", "-d", "hsm-ca")
$finalContainerId = ((& docker compose ps -a -q hsm-ca) | Select-Object -First 1).Trim()
if ([string]::IsNullOrWhiteSpace($finalContainerId)) {
    throw "Docker Compose did not expose the HSM container identity after token restoration."
}
$finalHealthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $finalHealth = ((& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}" $finalContainerId 2>$null) | Select-Object -First 1)
    if ($finalHealth -and $finalHealth.Trim() -eq "healthy") {
        $finalHealthy = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $finalHealthy) {
    docker compose logs --no-color hsm-ca
    throw "The restored HSM-backed CA did not become healthy."
}
Write-Output "HSM_SIGNING_PATH: PASS"
Write-Output "NO_DISK_CA_KEY: PASS"
Write-Output "TOKEN_UNAVAILABLE: EXPECTED_FAILURE"
Write-Output "Protected-key boundary milestone passed."
