param(
    [string]$BaseUrl = "http://127.0.0.1",
    [string]$AdminToken = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [bool]$Admin = $false
    )

    $Headers = @{}
    if ($Admin -and $AdminToken) {
        $Headers["x-cloud-admin-token"] = $AdminToken
    }

    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers
    }

    return Invoke-RestMethod `
        -Method $Method `
        -Uri $Url `
        -Headers $Headers `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 20)
}

Write-Host "1. health"
Invoke-Json GET "$BaseUrl/health" | ConvertTo-Json -Depth 20

Write-Host "2. readiness"
Invoke-Json GET "$BaseUrl/cloud/ops/readiness" | ConvertTo-Json -Depth 20

Write-Host "3. cloud ready"
Invoke-Json GET "$BaseUrl/cloud/ready" | ConvertTo-Json -Depth 20

Write-Host "4. limits"
Invoke-Json GET "$BaseUrl/cloud/limits" | ConvertTo-Json -Depth 20

Write-Host "5. chat"
Invoke-Json POST "$BaseUrl/chat" @{
    user_id = "smoke"
    username = "smoke"
    text = "云端冒烟测试"
} | ConvertTo-Json -Depth 20

if ($AdminToken) {
    Write-Host "6. admin config snapshot"
    Invoke-Json GET "$BaseUrl/cloud/ops/config-snapshot" $null $true | ConvertTo-Json -Depth 20

    Write-Host "7. gpu health"
    Invoke-Json GET "$BaseUrl/cloud/gpu/health" $null $true | ConvertTo-Json -Depth 20
}

Write-Host "smoke test completed"