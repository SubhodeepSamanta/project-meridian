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

function New-DemoIdentity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string[]]$AllowedActions
    )

    return Invoke-RestMethod -Uri "$baseUrl/identities" -Method Post -ContentType "application/json" -Body (@{
        name = $Name
        kind = "agent"
        owner = "meridian-policy-demo"
        purpose = "deterministic policy and approval demonstration"
        allowed_actions = $AllowedActions
    } | ConvertTo-Json)
}

function New-DemoCertificate {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$Identity
    )

    return Invoke-RestMethod -Uri "$baseUrl/identities/$($Identity.id)/certificates" -Method Post -ContentType "application/json" -Body (@{
        sans = @($Identity.name)
        validity = "24h"
    } | ConvertTo-Json)
}

$alpha = New-DemoIdentity -Name "agent-alpha-$runId" -AllowedActions @("read_status", "rotate_certificate")
$beta = New-DemoIdentity -Name "agent-beta-$runId" -AllowedActions @("read_status")
$alphaCertificate = New-DemoCertificate -Identity $alpha
$betaCertificate = New-DemoCertificate -Identity $beta

$allowed = Invoke-RestMethod -Uri "$baseUrl/identities/$($alpha.id)/actions" -Method Post -ContentType "application/json" -Body (@{
    action = "read_status"
    target = "service-a"
    certificate_fingerprint = $alphaCertificate.fingerprint
} | ConvertTo-Json)

$denied = Invoke-RestMethod -Uri "$baseUrl/identities/$($beta.id)/actions" -Method Post -ContentType "application/json" -Body (@{
    action = "delete_data"
    target = "service-a"
    certificate_fingerprint = $betaCertificate.fingerprint
} | ConvertTo-Json)

$pending = Invoke-RestMethod -Uri "$baseUrl/identities/$($alpha.id)/actions" -Method Post -ContentType "application/json" -Body (@{
    action = "rotate_certificate"
    target = $alpha.name
    certificate_fingerprint = $alphaCertificate.fingerprint
} | ConvertTo-Json)

$approved = Invoke-RestMethod -Uri "$baseUrl/actions/$($pending.id)/approve" -Method Post

if ($allowed.decision -ne "allow") {
    throw "The allowed low-risk action did not allow."
}
if ($denied.decision -ne "deny") {
    throw "The unauthorized action did not deny."
}
if ($pending.decision -ne "approval_required" -or $pending.approval_status -ne "pending") {
    throw "The high-risk action did not enter the approval state."
}
if ($approved.decision -ne "allow" -or $approved.approval_status -ne "approved") {
    throw "The approved high-risk action did not complete."
}

Write-Output "ALLOWED_ACTION: PASS"
Write-Output "UNAUTHORIZED_ACTION: EXPECTED_DENIAL"
Write-Output "HIGH_RISK_APPROVAL: PASS"
Write-Output "Policy and agent milestone passed."
