$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot

docker compose up -d meridian-api | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Could not start the Meridian API."
}

$baseUrl = "http://localhost:8000"
$healthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
        if ($health.status -eq "healthy") {
            $healthy = $true
            break
        }
    } catch {
        # The API may still be starting; the bounded retry is intentional.
    }
    Start-Sleep -Seconds 1
}
if (-not $healthy) {
    docker compose logs --no-color meridian-api
    throw "Timed out waiting for a healthy Meridian API."
}

$runId = [guid]::NewGuid().ToString("N").Substring(0, 8)
$identity = Invoke-RestMethod -Uri "$baseUrl/identities" -Method Post -ContentType "application/json" -Body (@{
    name = "agent-recovery-$runId"
    kind = "agent"
    owner = "meridian-incident-demo"
    purpose = "deterministic compromise and recovery demonstration"
    allowed_actions = @("read_status")
} | ConvertTo-Json)

$originalCertificate = Invoke-RestMethod -Uri "$baseUrl/identities/$($identity.id)/certificates" -Method Post -ContentType "application/json" -Body (@{
    sans = @($identity.name)
    validity = "24h"
} | ConvertTo-Json)

$incident = Invoke-RestMethod -Uri "$baseUrl/incidents/compromise" -Method Post -ContentType "application/json" -Body (@{
    identity_id = $identity.id
    reason = "synthetic certificate compromise"
} | ConvertTo-Json)

$quarantined = Invoke-RestMethod -Uri "$baseUrl/identities/$($identity.id)" -Method Get
$recovered = Invoke-RestMethod -Uri "$baseUrl/incidents/$($incident.id)/recover" -Method Post
$incidents = Invoke-RestMethod -Uri "$baseUrl/incidents" -Method Get

if ($incident.status -ne "open") {
    throw "The compromise scenario did not create an open incident."
}
if ($quarantined.identity.status -ne "quarantined" -or $quarantined.certificates[0].status -ne "revoked") {
    throw "The compromise scenario did not quarantine and revoke the original identity."
}
if ($recovered.incident.status -ne "resolved" -or $recovered.identity.status -ne "active") {
    throw "The recovery scenario did not resolve the incident and reactivate the identity."
}
if ($recovered.certificate.status -ne "active" -or $recovered.certificate.fingerprint -eq $originalCertificate.fingerprint) {
    throw "The recovery scenario did not create a distinct replacement certificate."
}
if (($incidents | Where-Object { $_.id -eq $incident.id }).status -ne "resolved") {
    throw "The resolved incident was not visible in the incident inventory."
}

Write-Output "COMPROMISE_CONTAINMENT: PASS"
Write-Output "CERTIFICATE_REPLACEMENT: PASS"
Write-Output "RECOVERY_EVIDENCE: PASS"
Write-Output "Incident and recovery milestone passed."
